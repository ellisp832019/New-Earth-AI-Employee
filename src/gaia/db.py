from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from gaia.conversation import AgentRunRecord
from gaia.models import (
    AuditEvent,
    DocumentRecord,
    ProjectChangeComparison,
    ProjectChangeFinding,
    ProjectHealthSnapshot,
    ProjectRecommendation,
    RepositorySnapshot,
    SearchResult,
    WorkPackageApprovalDecisionRecord,
    WorkPackageHandoffRecord,
    WorkPackageOutcomeRecord,
    WorkPackageRecord,
    WorkPackageRevisionRecord,
)
from gaia.programme_registry import (
    ArchitectureEntityKind,
    ArchitectureEntityRecord,
    ArchitectureEntityRevisionRecord,
    ArchitectureRelationshipRecord,
    ArchitectureRelationshipRevisionRecord,
    ArchitectureRelationshipType,
    ProgrammeProvenanceRecord,
    ProjectContractRecord,
    ProjectContractRevisionRecord,
)


class Database:
    SCHEMA_VERSION = 12

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.fts5_available = False
        self.initialise()

    def close(self) -> None:
        self.connection.close()

    def initialise(self) -> None:
        self.connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS documents (
                project_id TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                extension TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                modified_utc TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                tracked INTEGER,
                indexing_status TEXT NOT NULL,
                warning TEXT,
                scanned_at TEXT NOT NULL,
                content TEXT,
                PRIMARY KEY(project_id, relative_path)
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS project_health_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                project_id TEXT NOT NULL,
                project_name TEXT NOT NULL,
                project_root TEXT NOT NULL,
                project_configuration_fingerprint TEXT NOT NULL,
                capture_timestamp TEXT NOT NULL,
                normalized_status TEXT NOT NULL,
                normalized_payload_json TEXT NOT NULL,
                content_fingerprint TEXT NOT NULL,
                provenance_reference TEXT,
                audit_event_id TEXT
            );
            CREATE TABLE IF NOT EXISTS project_change_comparisons (
                comparison_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                detector_version TEXT NOT NULL,
                project_id TEXT NOT NULL,
                comparison_kind TEXT NOT NULL,
                previous_snapshot_id TEXT NOT NULL,
                current_snapshot_id TEXT NOT NULL,
                previous_snapshot_fingerprint TEXT NOT NULL,
                current_snapshot_fingerprint TEXT NOT NULL,
                capture_timestamp TEXT NOT NULL,
                comparison_status TEXT NOT NULL,
                meaningful_change_detected INTEGER NOT NULL,
                finding_count INTEGER NOT NULL,
                finding_ids_json TEXT NOT NULL,
                detector_outcomes_json TEXT NOT NULL,
                normalized_payload_json TEXT NOT NULL,
                provenance_reference TEXT,
                audit_event_id TEXT,
                content_fingerprint TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS project_change_findings (
                finding_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                comparison_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                finding_type TEXT NOT NULL,
                change_class TEXT NOT NULL,
                severity TEXT NOT NULL,
                direction TEXT NOT NULL,
                confidence TEXT NOT NULL,
                status TEXT NOT NULL,
                capture_timestamp TEXT NOT NULL,
                previous_snapshot_id TEXT NOT NULL,
                current_snapshot_id TEXT NOT NULL,
                previous_snapshot_fingerprint TEXT NOT NULL,
                current_snapshot_fingerprint TEXT NOT NULL,
                reason_codes_json TEXT NOT NULL,
                explanation TEXT NOT NULL,
                evidence_references_json TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                normalized_payload_json TEXT NOT NULL,
                detector_version TEXT NOT NULL,
                provenance_reference TEXT,
                audit_event_id TEXT,
                content_fingerprint TEXT NOT NULL,
                FOREIGN KEY(comparison_id) REFERENCES project_change_comparisons(comparison_id)
            );
            CREATE TABLE IF NOT EXISTS project_recommendations (
                recommendation_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                recommendation_policy_version TEXT NOT NULL,
                project_id TEXT NOT NULL,
                recommendation_type TEXT NOT NULL,
                created_timestamp TEXT NOT NULL,
                updated_timestamp TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL,
                priority_tier TEXT NOT NULL,
                deterministic_score INTEGER NOT NULL,
                urgency_category TEXT NOT NULL,
                effort_category TEXT NOT NULL,
                reversibility_category TEXT NOT NULL,
                score_breakdown_json TEXT NOT NULL,
                title TEXT NOT NULL,
                concise_summary TEXT NOT NULL,
                rationale TEXT NOT NULL,
                why_it_matters TEXT NOT NULL,
                why_it_received_this_score TEXT NOT NULL,
                reasons_to_proceed_json TEXT NOT NULL,
                reasons_not_to_proceed_json TEXT NOT NULL,
                blockers_json TEXT NOT NULL,
                dependencies_json TEXT NOT NULL,
                uncertainty TEXT NOT NULL,
                source_finding_ids_json TEXT NOT NULL,
                source_comparison_ids_json TEXT NOT NULL,
                source_snapshot_ids_json TEXT NOT NULL,
                evidence_fingerprints_json TEXT NOT NULL,
                evidence_freshness TEXT NOT NULL,
                evidence_references_json TEXT NOT NULL,
                semantic_fingerprint TEXT NOT NULL,
                content_fingerprint TEXT NOT NULL,
                provenance_reference TEXT,
                audit_event_id TEXT,
                supersedes_recommendation_id TEXT,
                superseded_by_recommendation_id TEXT,
                normalized_payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS project_recommendation_evidence_links (
                recommendation_id TEXT NOT NULL,
                evidence_kind TEXT NOT NULL,
                evidence_identity TEXT NOT NULL,
                evidence_id TEXT,
                description TEXT NOT NULL,
                freshness TEXT,
                details_json TEXT NOT NULL,
                PRIMARY KEY(recommendation_id, evidence_kind, description, evidence_identity),
                FOREIGN KEY(recommendation_id) REFERENCES project_recommendations(recommendation_id)
            );
            CREATE TABLE IF NOT EXISTS project_recommendation_dependencies (
                recommendation_id TEXT NOT NULL,
                depends_on_recommendation_id TEXT NOT NULL,
                dependency_type TEXT NOT NULL,
                reason TEXT NOT NULL,
                PRIMARY KEY(recommendation_id, depends_on_recommendation_id, dependency_type),
                FOREIGN KEY(recommendation_id) REFERENCES project_recommendations(recommendation_id)
            );
            CREATE TABLE IF NOT EXISTS project_contracts (
                contract_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL UNIQUE,
                current_revision_id TEXT,
                current_revision_number INTEGER NOT NULL,
                approved_revision_id TEXT,
                approved_revision_number INTEGER,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                content_fingerprint TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                freshness_state TEXT NOT NULL,
                normalized_payload_json TEXT NOT NULL,
                FOREIGN KEY(current_revision_id) REFERENCES project_contract_revisions(revision_id)
            );
            CREATE TABLE IF NOT EXISTS project_contract_revisions (
                revision_id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                revision_number INTEGER NOT NULL,
                previous_revision_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                semantic_fingerprint TEXT NOT NULL,
                content_fingerprint TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                evidence_references_json TEXT NOT NULL,
                freshness_state TEXT NOT NULL,
                supersedes_revision_id TEXT,
                normalized_payload_json TEXT NOT NULL,
                FOREIGN KEY(contract_id) REFERENCES project_contracts(contract_id),
                FOREIGN KEY(previous_revision_id) REFERENCES project_contract_revisions(revision_id),
                UNIQUE(project_id, semantic_fingerprint),
                UNIQUE(contract_id, revision_number)
            );
            CREATE TABLE IF NOT EXISTS architecture_entities (
                entity_id TEXT PRIMARY KEY,
                identity_key TEXT NOT NULL,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                owning_project_or_domain TEXT,
                repository TEXT,
                source_reference TEXT,
                current_revision_id TEXT,
                current_revision_number INTEGER NOT NULL,
                status TEXT NOT NULL,
                freshness_state TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                content_fingerprint TEXT NOT NULL,
                normalized_payload_json TEXT NOT NULL,
                UNIQUE(kind, identity_key),
                FOREIGN KEY(current_revision_id) REFERENCES architecture_entity_revisions(revision_id)
            );
            CREATE TABLE IF NOT EXISTS architecture_entity_revisions (
                revision_id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                identity_key TEXT NOT NULL,
                revision_number INTEGER NOT NULL,
                previous_revision_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                semantic_fingerprint TEXT NOT NULL,
                content_fingerprint TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                evidence_references_json TEXT NOT NULL,
                freshness_state TEXT NOT NULL,
                supersedes_revision_id TEXT,
                normalized_payload_json TEXT NOT NULL,
                FOREIGN KEY(entity_id) REFERENCES architecture_entities(entity_id),
                FOREIGN KEY(previous_revision_id) REFERENCES architecture_entity_revisions(revision_id),
                UNIQUE(entity_id, revision_number),
                UNIQUE(identity_key, semantic_fingerprint)
            );
            CREATE TABLE IF NOT EXISTS architecture_relationships (
                relationship_id TEXT PRIMARY KEY,
                identity_key TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                source_entity_id TEXT NOT NULL,
                target_entity_id TEXT NOT NULL,
                current_revision_id TEXT,
                current_revision_number INTEGER NOT NULL,
                status TEXT NOT NULL,
                freshness_state TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                content_fingerprint TEXT NOT NULL,
                normalized_payload_json TEXT NOT NULL,
                UNIQUE(relationship_type, source_entity_id, target_entity_id),
                FOREIGN KEY(current_revision_id) REFERENCES architecture_relationship_revisions(revision_id)
            );
            CREATE TABLE IF NOT EXISTS architecture_relationship_revisions (
                revision_id TEXT PRIMARY KEY,
                relationship_id TEXT NOT NULL,
                identity_key TEXT NOT NULL,
                revision_number INTEGER NOT NULL,
                previous_revision_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                semantic_fingerprint TEXT NOT NULL,
                content_fingerprint TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                evidence_references_json TEXT NOT NULL,
                freshness_state TEXT NOT NULL,
                supersedes_revision_id TEXT,
                normalized_payload_json TEXT NOT NULL,
                FOREIGN KEY(relationship_id) REFERENCES architecture_relationships(relationship_id),
                FOREIGN KEY(previous_revision_id) REFERENCES architecture_relationship_revisions(revision_id),
                UNIQUE(relationship_id, revision_number),
                UNIQUE(identity_key, semantic_fingerprint)
            );
            CREATE TABLE IF NOT EXISTS work_packages (
                work_package_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                project_id TEXT NOT NULL,
                source_recommendation_id TEXT NOT NULL,
                source_recommendation_semantic_fingerprint TEXT NOT NULL,
                source_recommendation_content_fingerprint TEXT NOT NULL,
                source_recommendation_policy_version TEXT NOT NULL,
                current_revision_number INTEGER NOT NULL,
                current_revision_id TEXT,
                title TEXT NOT NULL,
                approval_state TEXT NOT NULL,
                gate_state TEXT NOT NULL,
                staleness_state TEXT NOT NULL,
                created_timestamp TEXT NOT NULL,
                updated_timestamp TEXT NOT NULL,
                expiry_timestamp TEXT,
                package_fingerprint TEXT NOT NULL,
                semantic_fingerprint TEXT NOT NULL,
                content_fingerprint TEXT NOT NULL,
                prompt_template_version TEXT NOT NULL,
                prompt_content_fingerprint TEXT NOT NULL,
                generator_version TEXT NOT NULL,
                project_configuration_fingerprint TEXT NOT NULL,
                source_health_snapshot_ids_json TEXT NOT NULL,
                source_health_snapshot_fingerprints_json TEXT NOT NULL,
                audit_reference TEXT,
                normalized_payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS work_package_revisions (
                revision_id TEXT PRIMARY KEY,
                work_package_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                revision_number INTEGER NOT NULL,
                previous_revision_id TEXT,
                approval_state_at_creation TEXT NOT NULL,
                change_reason TEXT NOT NULL,
                changed_fields_json TEXT NOT NULL,
                created_timestamp TEXT NOT NULL,
                package_fingerprint TEXT NOT NULL,
                semantic_fingerprint TEXT NOT NULL,
                content_fingerprint TEXT NOT NULL,
                prompt_content_fingerprint TEXT NOT NULL,
                audit_reference TEXT,
                normalized_payload_json TEXT NOT NULL,
                FOREIGN KEY(work_package_id) REFERENCES work_packages(work_package_id),
                UNIQUE(work_package_id, revision_number)
            );
            CREATE TABLE IF NOT EXISTS work_package_evidence_links (
                work_package_id TEXT NOT NULL,
                revision_id TEXT NOT NULL,
                evidence_kind TEXT NOT NULL,
                evidence_identity TEXT NOT NULL,
                evidence_id TEXT,
                description TEXT NOT NULL,
                freshness TEXT,
                details_json TEXT NOT NULL,
                PRIMARY KEY(work_package_id, revision_id, evidence_kind, evidence_identity, description),
                FOREIGN KEY(work_package_id) REFERENCES work_packages(work_package_id),
                FOREIGN KEY(revision_id) REFERENCES work_package_revisions(revision_id)
            );
            CREATE TABLE IF NOT EXISTS work_package_approval_decisions (
                decision_id TEXT PRIMARY KEY,
                work_package_id TEXT NOT NULL,
                revision_id TEXT NOT NULL,
                revision_number INTEGER NOT NULL,
                project_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                actor TEXT NOT NULL,
                decision_timestamp TEXT NOT NULL,
                evidence_fingerprint TEXT NOT NULL,
                human_note TEXT,
                audit_reference TEXT,
                previous_state TEXT NOT NULL,
                next_state TEXT NOT NULL,
                normalized_payload_json TEXT NOT NULL,
                FOREIGN KEY(work_package_id) REFERENCES work_packages(work_package_id),
                FOREIGN KEY(revision_id) REFERENCES work_package_revisions(revision_id)
            );
            CREATE TABLE IF NOT EXISTS work_package_handoffs (
                handoff_id TEXT PRIMARY KEY,
                work_package_id TEXT NOT NULL,
                revision_id TEXT NOT NULL,
                revision_number INTEGER NOT NULL,
                project_id TEXT NOT NULL,
                approval_decision_id TEXT NOT NULL,
                approved_by TEXT NOT NULL,
                approved_at TEXT NOT NULL,
                prompt_fingerprint TEXT NOT NULL,
                next_manual_action TEXT NOT NULL,
                rollback_reference TEXT NOT NULL,
                source_evidence_ids_json TEXT NOT NULL,
                source_evidence_fingerprints_json TEXT NOT NULL,
                audit_reference TEXT,
                normalized_payload_json TEXT NOT NULL,
                FOREIGN KEY(work_package_id) REFERENCES work_packages(work_package_id),
                FOREIGN KEY(revision_id) REFERENCES work_package_revisions(revision_id),
                FOREIGN KEY(approval_decision_id) REFERENCES work_package_approval_decisions(decision_id)
            );
            CREATE TABLE IF NOT EXISTS work_package_outcomes (
                outcome_id TEXT PRIMARY KEY,
                work_package_id TEXT NOT NULL,
                revision_id TEXT NOT NULL,
                revision_number INTEGER NOT NULL,
                project_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                actor TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                note TEXT,
                evidence_fingerprint TEXT NOT NULL,
                audit_reference TEXT,
                normalized_payload_json TEXT NOT NULL,
                FOREIGN KEY(work_package_id) REFERENCES work_packages(work_package_id),
                FOREIGN KEY(revision_id) REFERENCES work_package_revisions(revision_id)
            );
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                operation TEXT NOT NULL,
                project_id TEXT,
                outcome TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                error_classification TEXT
            );
            CREATE TABLE IF NOT EXISTS agent_runs (
                run_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                question TEXT NOT NULL,
                question_category TEXT NOT NULL,
                snapshot_id TEXT,
                retrieval_queries_json TEXT NOT NULL,
                selected_evidence_json TEXT NOT NULL,
                provider TEXT NOT NULL,
                model_name TEXT,
                start_timestamp TEXT NOT NULL,
                finish_timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                structured_answer_json TEXT NOT NULL,
                confidence TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                prompt_injection_warnings_json TEXT NOT NULL,
                safe_error TEXT,
                usage_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                project_id TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                category TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_identifier TEXT,
                source_agent_run_id TEXT,
                evidence_references_json TEXT NOT NULL,
                dependency_task_ids_json TEXT NOT NULL,
                blocker_description TEXT,
                assigned_to TEXT,
                due_date TEXT,
                completion_criteria TEXT NOT NULL,
                completion_evidence_json TEXT NOT NULL,
                approval_requirement INTEGER NOT NULL,
                tags_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                version INTEGER NOT NULL,
                manual_override_reason TEXT
            );
            CREATE TABLE IF NOT EXISTS task_history (
                history_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT NOT NULL,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS drafts (
                draft_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                draft_type TEXT NOT NULL,
                project_id TEXT NOT NULL,
                source_task_id TEXT,
                source_agent_run_id TEXT,
                current_revision INTEGER NOT NULL,
                current_content_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                evidence_references_json TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                approval_requirement INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS draft_revisions (
                revision_id TEXT PRIMARY KEY,
                draft_id TEXT NOT NULL,
                revision_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                author TEXT NOT NULL,
                change_reason TEXT NOT NULL,
                UNIQUE(draft_id, revision_number)
            );
            CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY,
                request_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                project_id TEXT NOT NULL,
                source_task_id TEXT,
                source_draft_id TEXT,
                requesting_source TEXT NOT NULL,
                proposed_action TEXT NOT NULL,
                exact_target_description TEXT NOT NULL,
                write_boundary TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                preview_summary TEXT NOT NULL,
                approved_content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expiry_timestamp TEXT,
                status TEXT NOT NULL,
                reviewer TEXT,
                decision_timestamp TEXT,
                decision_reason TEXT,
                audit_references_json TEXT NOT NULL,
                invalidation_reason TEXT,
                version INTEGER NOT NULL,
                action_id TEXT,
                action_type TEXT,
                manifest_id TEXT,
                manifest_version INTEGER,
                canonical_target TEXT,
                previous_content_hash TEXT,
                proposed_content_hash TEXT,
                approval_binding_hash TEXT,
                approval_scope TEXT
            );
            CREATE TABLE IF NOT EXISTS daily_briefs (
                brief_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                repository_snapshot_json TEXT NOT NULL,
                verified_facts_json TEXT NOT NULL,
                inferences_json TEXT NOT NULL,
                recommendations_json TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                unknowns_json TEXT NOT NULL,
                markdown TEXT NOT NULL,
                source_task_ids_json TEXT NOT NULL,
                source_approval_ids_json TEXT NOT NULL,
                source_run_ids_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS permission_manifests (
                manifest_id TEXT PRIMARY KEY,
                manifest_version INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                allowed_action_types_json TEXT NOT NULL,
                allowed_target_roots_json TEXT NOT NULL,
                allowed_file_extensions_json TEXT NOT NULL,
                denied_path_patterns_json TEXT NOT NULL,
                maximum_file_size INTEGER NOT NULL,
                overwrite_policy TEXT NOT NULL,
                backup_requirement INTEGER NOT NULL,
                rollback_requirement INTEGER NOT NULL,
                approval_requirement INTEGER NOT NULL,
                risk_ceiling TEXT NOT NULL,
                expiry_timestamp TEXT,
                creation_source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                reviewed_by TEXT,
                reviewed_at TEXT,
                review_notes TEXT
            );
            CREATE TABLE IF NOT EXISTS output_actions (
                action_id TEXT PRIMARY KEY,
                action_type TEXT NOT NULL,
                title TEXT NOT NULL,
                project_id TEXT NOT NULL,
                source_task_id TEXT,
                source_draft_id TEXT,
                source_draft_revision INTEGER,
                source_approval_id TEXT,
                manifest_id TEXT NOT NULL,
                manifest_version INTEGER NOT NULL,
                canonical_target TEXT NOT NULL,
                proposed_content TEXT NOT NULL,
                previous_content_hash TEXT,
                proposed_content_hash TEXT NOT NULL,
                preview TEXT NOT NULL,
                diff TEXT NOT NULL,
                risk TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expiry_timestamp TEXT,
                execution_time TEXT,
                execution_receipt_id TEXT,
                approval_id TEXT,
                approval_binding_hash TEXT,
                approval_status TEXT,
                approval_decision_timestamp TEXT,
                approval_reviewer TEXT,
                approval_reason TEXT,
                denial_reason TEXT,
                backup_path TEXT,
                rollback_available INTEGER NOT NULL,
                operator TEXT,
                warnings_json TEXT NOT NULL,
                result TEXT
            );
            CREATE TABLE IF NOT EXISTS action_previews (
                preview_id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                preview TEXT NOT NULL,
                diff TEXT NOT NULL,
                previous_content_hash TEXT,
                proposed_content_hash TEXT NOT NULL,
                target_path TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS execution_receipts (
                receipt_id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL,
                approval_id TEXT,
                manifest_id TEXT NOT NULL,
                manifest_version INTEGER NOT NULL,
                source_draft_id TEXT,
                source_draft_revision INTEGER,
                target_path TEXT NOT NULL,
                previous_hash TEXT,
                resulting_hash TEXT NOT NULL,
                backup_path TEXT,
                timestamp TEXT NOT NULL,
                operator TEXT NOT NULL,
                result TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                rollback_available INTEGER NOT NULL,
                chain_id TEXT,
                chain_sequence INTEGER,
                previous_receipt_hash TEXT,
                receipt_content_hash TEXT,
                verification_status TEXT
            );
            CREATE TABLE IF NOT EXISTS output_backups (
                backup_id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL,
                target_path TEXT NOT NULL,
                backup_path TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                verified INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rollback_records (
                rollback_id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL,
                receipt_id TEXT,
                target_path TEXT NOT NULL,
                backup_path TEXT NOT NULL,
                previous_hash TEXT,
                resulting_hash TEXT,
                created_at TEXT NOT NULL,
                executed_at TEXT,
                status TEXT NOT NULL,
                reason TEXT
            );
            CREATE TABLE IF NOT EXISTS action_templates (
                template_id TEXT PRIMARY KEY,
                template_version INTEGER NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS receipt_chains (
                chain_id TEXT NOT NULL,
                receipt_id TEXT NOT NULL,
                chain_sequence INTEGER NOT NULL,
                receipt_content_hash TEXT NOT NULL,
                previous_receipt_hash TEXT,
                created_at TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                PRIMARY KEY(chain_id, chain_sequence)
            );
            CREATE TABLE IF NOT EXISTS review_packages (
                package_id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL,
                receipt_id TEXT,
                chain_id TEXT,
                package_path TEXT NOT NULL,
                manifest_json TEXT NOT NULL,
                hashes_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                verification_status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS retention_policies (
                policy_id TEXT PRIMARY KEY,
                policy_version INTEGER NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS retention_plans (
                plan_id TEXT PRIMARY KEY,
                policy_id TEXT NOT NULL,
                plan_hash TEXT NOT NULL,
                approved_hash TEXT,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS retention_receipts (
                receipt_id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS package_verifications (
                verification_id TEXT PRIMARY KEY,
                package_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS signing_keys (
                key_id TEXT PRIMARY KEY,
                key_name TEXT NOT NULL,
                public_key TEXT NOT NULL,
                private_key_path TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                revoked_at TEXT,
                rotated_from_key_id TEXT,
                last_used_at TEXT,
                signing_enabled INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS provenance_manifests (
                manifest_id TEXT PRIMARY KEY,
                manifest_version INTEGER NOT NULL,
                subject_kind TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                subject_version INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                canonical_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                signing_key_id TEXT,
                signature TEXT,
                signature_status TEXT NOT NULL,
                key_status TEXT NOT NULL,
                chain_id TEXT,
                chain_sequence INTEGER,
                package_path TEXT,
                metadata_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS trust_alerts (
                alert_id TEXT PRIMARY KEY,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                source_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                acknowledged_at TEXT,
                metadata_json TEXT NOT NULL
            );
            """
        )
        try:
            self.connection.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(project_id, relative_path, content)"
            )
            self.fts5_available = True
        except sqlite3.OperationalError:
            self.fts5_available = False
        self._ensure_columns(
            "approvals",
            {
                "action_id": "TEXT",
                "action_type": "TEXT",
                "manifest_id": "TEXT",
                "manifest_version": "INTEGER",
                "canonical_target": "TEXT",
                "previous_content_hash": "TEXT",
                "proposed_content_hash": "TEXT",
                "approval_binding_hash": "TEXT",
                "approval_scope": "TEXT",
            },
        )
        self._ensure_columns(
            "execution_receipts",
            {
                "chain_id": "TEXT",
                "chain_sequence": "INTEGER",
                "previous_receipt_hash": "TEXT",
                "receipt_content_hash": "TEXT",
                "verification_status": "TEXT",
            },
        )
        self._ensure_columns(
            "signing_keys",
            {
                "rotated_from_key_id": "TEXT",
                "last_used_at": "TEXT",
                "signing_enabled": "INTEGER",
                "revoked_at": "TEXT",
            },
        )
        self._ensure_columns(
            "provenance_manifests",
            {
                "signature": "TEXT",
                "signing_key_id": "TEXT",
                "chain_id": "TEXT",
                "chain_sequence": "INTEGER",
                "package_path": "TEXT",
            },
        )
        self._ensure_columns(
            "trust_alerts",
            {
                "acknowledged_at": "TEXT",
            },
        )
        self._ensure_indexes(
            [
                "CREATE INDEX IF NOT EXISTS idx_project_health_snapshots_project_id ON project_health_snapshots(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_health_snapshots_capture_timestamp ON project_health_snapshots(capture_timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_project_health_snapshots_project_timestamp ON project_health_snapshots(project_id, capture_timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_project_health_snapshots_normalized_status ON project_health_snapshots(normalized_status)",
                "CREATE INDEX IF NOT EXISTS idx_project_health_snapshots_content_fingerprint ON project_health_snapshots(content_fingerprint)",
                "CREATE INDEX IF NOT EXISTS idx_project_change_comparisons_project_id ON project_change_comparisons(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_change_comparisons_capture_timestamp ON project_change_comparisons(capture_timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_project_change_comparisons_project_timestamp ON project_change_comparisons(project_id, capture_timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_project_change_comparisons_content_fingerprint ON project_change_comparisons(content_fingerprint)",
                "CREATE INDEX IF NOT EXISTS idx_project_change_findings_project_id ON project_change_findings(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_change_findings_comparison_id ON project_change_findings(comparison_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_change_findings_change_class ON project_change_findings(change_class)",
                "CREATE INDEX IF NOT EXISTS idx_project_change_findings_severity ON project_change_findings(severity)",
                "CREATE INDEX IF NOT EXISTS idx_project_change_findings_capture_timestamp ON project_change_findings(capture_timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_project_change_findings_current_snapshot_id ON project_change_findings(current_snapshot_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_change_findings_content_fingerprint ON project_change_findings(content_fingerprint)",
                "CREATE INDEX IF NOT EXISTS idx_project_recommendations_project_id ON project_recommendations(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_recommendations_policy_version ON project_recommendations(recommendation_policy_version)",
                "CREATE INDEX IF NOT EXISTS idx_project_recommendations_priority_tier ON project_recommendations(priority_tier)",
                "CREATE INDEX IF NOT EXISTS idx_project_recommendations_lifecycle_state ON project_recommendations(lifecycle_state)",
                "CREATE INDEX IF NOT EXISTS idx_project_recommendations_created_timestamp ON project_recommendations(created_timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_project_recommendations_semantic_fingerprint ON project_recommendations(semantic_fingerprint)",
                "CREATE INDEX IF NOT EXISTS idx_project_recommendations_content_fingerprint ON project_recommendations(content_fingerprint)",
                "CREATE INDEX IF NOT EXISTS idx_project_recommendation_evidence_links_recommendation_id ON project_recommendation_evidence_links(recommendation_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_recommendation_dependencies_recommendation_id ON project_recommendation_dependencies(recommendation_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_recommendation_dependencies_depends_on ON project_recommendation_dependencies(depends_on_recommendation_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_contracts_project_id ON project_contracts(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_contracts_status ON project_contracts(status)",
                "CREATE INDEX IF NOT EXISTS idx_project_contracts_current_revision_id ON project_contracts(current_revision_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_contract_revisions_project_id ON project_contract_revisions(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_contract_revisions_revision_number ON project_contract_revisions(project_id, revision_number DESC)",
                "CREATE INDEX IF NOT EXISTS idx_project_contract_revisions_semantic_fingerprint ON project_contract_revisions(project_id, semantic_fingerprint)",
                "CREATE INDEX IF NOT EXISTS idx_architecture_entities_kind ON architecture_entities(kind)",
                "CREATE INDEX IF NOT EXISTS idx_architecture_entities_project ON architecture_entities(owning_project_or_domain)",
                "CREATE INDEX IF NOT EXISTS idx_architecture_entities_current_revision_id ON architecture_entities(current_revision_id)",
                "CREATE INDEX IF NOT EXISTS idx_architecture_entity_revisions_entity_id ON architecture_entity_revisions(entity_id)",
                "CREATE INDEX IF NOT EXISTS idx_architecture_entity_revisions_revision_number ON architecture_entity_revisions(entity_id, revision_number DESC)",
                "CREATE INDEX IF NOT EXISTS idx_architecture_entity_revisions_identity_key ON architecture_entity_revisions(identity_key)",
                "CREATE INDEX IF NOT EXISTS idx_architecture_relationships_source_entity_id ON architecture_relationships(source_entity_id)",
                "CREATE INDEX IF NOT EXISTS idx_architecture_relationships_target_entity_id ON architecture_relationships(target_entity_id)",
                "CREATE INDEX IF NOT EXISTS idx_architecture_relationships_type ON architecture_relationships(relationship_type)",
                "CREATE INDEX IF NOT EXISTS idx_architecture_relationships_current_revision_id ON architecture_relationships(current_revision_id)",
                "CREATE INDEX IF NOT EXISTS idx_architecture_relationship_revisions_relationship_id ON architecture_relationship_revisions(relationship_id)",
                "CREATE INDEX IF NOT EXISTS idx_architecture_relationship_revisions_revision_number ON architecture_relationship_revisions(relationship_id, revision_number DESC)",
                "CREATE INDEX IF NOT EXISTS idx_architecture_relationship_revisions_identity_key ON architecture_relationship_revisions(identity_key)",
                "CREATE INDEX IF NOT EXISTS idx_work_packages_project_id ON work_packages(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_work_packages_semantic_fingerprint ON work_packages(semantic_fingerprint)",
                "CREATE INDEX IF NOT EXISTS idx_work_packages_source_recommendation_id ON work_packages(source_recommendation_id)",
                "CREATE INDEX IF NOT EXISTS idx_work_packages_approval_state ON work_packages(approval_state)",
                "CREATE INDEX IF NOT EXISTS idx_work_packages_staleness_state ON work_packages(staleness_state)",
                "CREATE INDEX IF NOT EXISTS idx_work_package_revisions_package_id ON work_package_revisions(work_package_id)",
                "CREATE INDEX IF NOT EXISTS idx_work_package_revisions_revision_number ON work_package_revisions(work_package_id, revision_number DESC)",
                "CREATE INDEX IF NOT EXISTS idx_work_package_evidence_links_package_revision ON work_package_evidence_links(work_package_id, revision_id)",
                "CREATE INDEX IF NOT EXISTS idx_work_package_approval_decisions_package_id ON work_package_approval_decisions(work_package_id)",
                "CREATE INDEX IF NOT EXISTS idx_work_package_approval_decisions_revision_id ON work_package_approval_decisions(revision_id)",
                "CREATE INDEX IF NOT EXISTS idx_work_package_handoffs_package_id ON work_package_handoffs(work_package_id)",
                "CREATE INDEX IF NOT EXISTS idx_work_package_outcomes_package_id ON work_package_outcomes(work_package_id)",
            ]
        )
        self.connection.commit()
        self.connection.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")
        self.connection.commit()

    def _ensure_columns(self, table: str, columns: dict[str, str]) -> None:
        existing = {
            str(row["name"])
            for row in self.connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for name, type_name in columns.items():
            if name not in existing:
                self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {type_name}")

    def _ensure_indexes(self, statements: Iterable[str]) -> None:
        for statement in statements:
            self.connection.execute(statement)

    def replace_documents(self, project_id: str, records: Iterable[DocumentRecord]) -> None:
        records = list(records)
        with self.connection:
            self.connection.execute("DELETE FROM documents WHERE project_id = ?", (project_id,))
            if self.fts5_available:
                self.connection.execute("DELETE FROM documents_fts WHERE project_id = ?", (project_id,))
            for record in records:
                self.connection.execute(
                    """
                    INSERT INTO documents (
                        project_id, relative_path, extension, size_bytes, modified_utc,
                        sha256, tracked, indexing_status, warning, scanned_at, content
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.project_id,
                        record.relative_path,
                        record.extension,
                        record.size_bytes,
                        record.modified_utc.isoformat(),
                        record.sha256,
                        None if record.tracked is None else int(record.tracked),
                        record.indexing_status,
                        record.warning,
                        record.scanned_at.isoformat(),
                        record.content,
                    ),
                )
                if self.fts5_available and record.content and record.indexing_status == "indexed":
                    self.connection.execute(
                        "INSERT INTO documents_fts(project_id, relative_path, content) VALUES (?, ?, ?)",
                        (record.project_id, record.relative_path, record.content),
                    )

    def list_documents(self, project_id: str) -> list[dict[str, object]]:
        rows = self.connection.execute(
            "SELECT * FROM documents WHERE project_id = ? ORDER BY relative_path", (project_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def search(
        self,
        project_id: str,
        query: str,
        *,
        limit: int = 20,
        path_prefix: str | None = None,
        extension: str | None = None,
    ) -> list[SearchResult]:
        limit = max(1, min(limit, 100))
        if self.fts5_available:
            sql = (
                "SELECT relative_path, snippet(documents_fts, 2, '[', ']', ' ... ', 18) AS snippet, "
                "bm25(documents_fts) AS score FROM documents_fts "
                "WHERE project_id = ? AND documents_fts MATCH ?"
            )
            params: list[object] = [project_id, query]
            if path_prefix:
                sql += " AND relative_path LIKE ? ESCAPE '\\'"
                params.append(f"{_escape_like(path_prefix)}%")
            sql += " ORDER BY score LIMIT ?"
            params.append(limit)
            try:
                rows = self.connection.execute(sql, params).fetchall()
                results = []
                for row in rows:
                    ext = Path(row["relative_path"]).suffix.lower()
                    if extension and ext != extension.lower():
                        continue
                    results.append(
                        SearchResult(
                            relative_path=row["relative_path"],
                            extension=ext,
                            snippet=row["snippet"] or "",
                            score=float(row["score"]),
                        )
                    )
                return results[:limit]
            except sqlite3.OperationalError:
                pass

        sql = (
            "SELECT relative_path, extension, content FROM documents "
            "WHERE project_id = ? AND content LIKE ? ESCAPE '\\'"
        )
        params = [project_id, f"%{_escape_like(query)}%"]
        if path_prefix:
            sql += " AND relative_path LIKE ? ESCAPE '\\'"
            params.append(f"{_escape_like(path_prefix)}%")
        if extension:
            sql += " AND extension = ?"
            params.append(extension.lower())
        sql += " ORDER BY relative_path LIMIT ?"
        params.append(limit)
        rows = self.connection.execute(sql, params).fetchall()
        return [
            SearchResult(
                relative_path=row["relative_path"],
                extension=row["extension"],
                snippet=_make_snippet(row["content"] or "", query),
            )
            for row in rows
        ]

    def insert_snapshot(self, snapshot: RepositorySnapshot) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT OR REPLACE INTO snapshots(snapshot_id, project_id, created_at, payload_json) VALUES (?, ?, ?, ?)",
                (
                    snapshot.snapshot_id,
                    snapshot.project_id,
                    snapshot.created_at.isoformat(),
                    snapshot.model_dump_json(),
                ),
            )

    def list_snapshots(self, project_id: str) -> list[RepositorySnapshot]:
        rows = self.connection.execute(
            "SELECT payload_json FROM snapshots WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
        return [RepositorySnapshot.model_validate_json(row["payload_json"]) for row in rows]

    def latest_snapshot(self, project_id: str) -> RepositorySnapshot | None:
        row = self.connection.execute(
            "SELECT payload_json FROM snapshots WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        return RepositorySnapshot.model_validate_json(row["payload_json"]) if row else None

    def insert_project_health_snapshot(self, snapshot: ProjectHealthSnapshot) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO project_health_snapshots(
                    snapshot_id, schema_version, project_id, project_name, project_root,
                    project_configuration_fingerprint, capture_timestamp, normalized_status,
                    normalized_payload_json, content_fingerprint, provenance_reference, audit_event_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.snapshot_id,
                    snapshot.schema_version,
                    snapshot.project_id,
                    snapshot.project_name,
                    snapshot.project_root,
                    snapshot.project_configuration_fingerprint,
                    snapshot.capture_timestamp.isoformat(),
                    snapshot.normalized_status,
                    snapshot.model_dump_json(),
                    snapshot.content_fingerprint,
                    snapshot.provenance_reference,
                    snapshot.audit_event_id,
                ),
            )

    def update_project_health_snapshot_audit_event(self, snapshot_id: str, audit_event_id: str) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE project_health_snapshots SET audit_event_id = ? WHERE snapshot_id = ?",
                (audit_event_id, snapshot_id),
            )

    def get_project_health_snapshot(self, snapshot_id: str) -> ProjectHealthSnapshot | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM project_health_snapshots WHERE snapshot_id = ?",
            (snapshot_id,),
        ).fetchone()
        return ProjectHealthSnapshot.model_validate_json(row["normalized_payload_json"]) if row else None

    def list_project_health_snapshots(self, project_id: str) -> list[ProjectHealthSnapshot]:
        rows = self.connection.execute(
            "SELECT normalized_payload_json FROM project_health_snapshots WHERE project_id = ? ORDER BY capture_timestamp DESC, snapshot_id DESC",
            (project_id,),
        ).fetchall()
        return [ProjectHealthSnapshot.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def latest_project_health_snapshot(self, project_id: str) -> ProjectHealthSnapshot | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM project_health_snapshots WHERE project_id = ? ORDER BY capture_timestamp DESC, snapshot_id DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        return ProjectHealthSnapshot.model_validate_json(row["normalized_payload_json"]) if row else None

    def list_latest_project_health_snapshots(self) -> list[ProjectHealthSnapshot]:
        rows = self.connection.execute(
            """
            SELECT project_id, MAX(capture_timestamp) AS capture_timestamp
            FROM project_health_snapshots
            GROUP BY project_id
            ORDER BY project_id
            """
        ).fetchall()
        snapshots: list[ProjectHealthSnapshot] = []
        for row in rows:
            project_id = str(row["project_id"])
            snapshot = self.latest_project_health_snapshot(project_id)
            if snapshot is not None:
                snapshots.append(snapshot)
        return snapshots

    def insert_project_change_comparison(self, comparison: ProjectChangeComparison) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR IGNORE INTO project_change_comparisons(
                    comparison_id, schema_version, detector_version, project_id, comparison_kind,
                    previous_snapshot_id, current_snapshot_id, previous_snapshot_fingerprint,
                    current_snapshot_fingerprint, capture_timestamp, comparison_status,
                    meaningful_change_detected, finding_count, finding_ids_json, detector_outcomes_json,
                    normalized_payload_json, provenance_reference, audit_event_id, content_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    comparison.comparison_id,
                    comparison.schema_version,
                    comparison.detector_version,
                    comparison.project_id,
                    comparison.comparison_kind,
                    comparison.previous_snapshot_id,
                    comparison.current_snapshot_id,
                    comparison.previous_snapshot_fingerprint,
                    comparison.current_snapshot_fingerprint,
                    comparison.capture_timestamp.isoformat(),
                    comparison.comparison_status,
                    int(comparison.meaningful_change_detected),
                    comparison.finding_count,
                    json.dumps(comparison.finding_ids, default=str, sort_keys=True),
                    json.dumps(comparison.detector_outcomes, default=str, sort_keys=True),
                    comparison.model_dump_json(),
                    comparison.provenance_reference,
                    comparison.audit_event_id,
                    comparison.content_fingerprint,
                ),
            )

    def update_project_change_comparison_audit_event(self, comparison_id: str, audit_event_id: str) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE project_change_comparisons SET audit_event_id = ? WHERE comparison_id = ?",
                (audit_event_id, comparison_id),
            )

    def get_project_change_comparison(self, comparison_id: str) -> ProjectChangeComparison | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM project_change_comparisons WHERE comparison_id = ?",
            (comparison_id,),
        ).fetchone()
        return ProjectChangeComparison.model_validate_json(row["normalized_payload_json"]) if row else None

    def list_project_change_comparisons(self, project_id: str) -> list[ProjectChangeComparison]:
        rows = self.connection.execute(
            "SELECT normalized_payload_json FROM project_change_comparisons WHERE project_id = ? ORDER BY capture_timestamp DESC, comparison_id DESC",
            (project_id,),
        ).fetchall()
        return [ProjectChangeComparison.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def latest_project_change_comparison(self, project_id: str) -> ProjectChangeComparison | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM project_change_comparisons WHERE project_id = ? ORDER BY capture_timestamp DESC, comparison_id DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        return ProjectChangeComparison.model_validate_json(row["normalized_payload_json"]) if row else None

    def insert_project_change_finding(self, finding: ProjectChangeFinding) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR IGNORE INTO project_change_findings(
                    finding_id, schema_version, comparison_id, project_id, finding_type, change_class,
                    severity, direction, confidence, status, capture_timestamp, previous_snapshot_id,
                    current_snapshot_id, previous_snapshot_fingerprint, current_snapshot_fingerprint,
                    reason_codes_json, explanation, evidence_references_json, evidence_json,
                    normalized_payload_json, detector_version, provenance_reference, audit_event_id,
                    content_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    finding.finding_id,
                    finding.schema_version,
                    finding.comparison_id,
                    finding.project_id,
                    finding.finding_type,
                    finding.change_class,
                    finding.severity,
                    finding.direction,
                    finding.confidence,
                    finding.status,
                    finding.capture_timestamp.isoformat(),
                    finding.previous_snapshot_id,
                    finding.current_snapshot_id,
                    finding.previous_snapshot_fingerprint,
                    finding.current_snapshot_fingerprint,
                    json.dumps(finding.reason_codes, default=str, sort_keys=True),
                    finding.explanation,
                    json.dumps([item.model_dump(mode="json") for item in finding.evidence_references], default=str, sort_keys=True),
                    json.dumps(finding.evidence, default=str, sort_keys=True),
                    finding.model_dump_json(),
                    finding.detector_version,
                    finding.provenance_reference,
                    finding.audit_event_id,
                    finding.content_fingerprint,
                ),
            )

    def update_project_change_finding_audit_event(self, finding_id: str, audit_event_id: str) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE project_change_findings SET audit_event_id = ? WHERE finding_id = ?",
                (audit_event_id, finding_id),
            )

    def get_project_change_finding(self, finding_id: str) -> ProjectChangeFinding | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM project_change_findings WHERE finding_id = ?",
            (finding_id,),
        ).fetchone()
        return ProjectChangeFinding.model_validate_json(row["normalized_payload_json"]) if row else None

    def list_project_change_findings(self, project_id: str) -> list[ProjectChangeFinding]:
        rows = self.connection.execute(
            "SELECT normalized_payload_json FROM project_change_findings WHERE project_id = ? ORDER BY capture_timestamp DESC, finding_id DESC",
            (project_id,),
        ).fetchall()
        return [ProjectChangeFinding.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def list_project_change_findings_by_comparison(self, comparison_id: str) -> list[ProjectChangeFinding]:
        rows = self.connection.execute(
            "SELECT normalized_payload_json FROM project_change_findings WHERE comparison_id = ? ORDER BY severity, capture_timestamp DESC, finding_id DESC",
            (comparison_id,),
        ).fetchall()
        return [ProjectChangeFinding.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def latest_project_change_findings(self, project_id: str) -> list[ProjectChangeFinding]:
        row = self.connection.execute(
            """
            SELECT comparison_id
            FROM project_change_comparisons
            WHERE project_id = ? AND meaningful_change_detected = 1
            ORDER BY capture_timestamp DESC, comparison_id DESC
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()
        if row is None:
            return []
        return self.list_project_change_findings_by_comparison(str(row["comparison_id"]))

    def recent_project_change_findings(self, project_ids: list[str], limit: int = 50) -> list[ProjectChangeFinding]:
        if not project_ids:
            return []
        placeholders = ",".join("?" for _ in project_ids)
        rows = self.connection.execute(
            f"""
            SELECT normalized_payload_json
            FROM project_change_findings
            WHERE project_id IN ({placeholders})
            ORDER BY capture_timestamp DESC, project_id ASC, finding_id DESC
            LIMIT ?
            """,
            [*project_ids, max(1, min(limit, 1000))],
        ).fetchall()
        return [ProjectChangeFinding.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def insert_project_recommendation(self, recommendation: ProjectRecommendation) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO project_recommendations(
                    recommendation_id, schema_version, recommendation_policy_version, project_id,
                    recommendation_type, created_timestamp, updated_timestamp, lifecycle_state,
                    priority_tier, deterministic_score, urgency_category, effort_category,
                    reversibility_category, score_breakdown_json, title, concise_summary,
                    rationale, why_it_matters, why_it_received_this_score, reasons_to_proceed_json,
                    reasons_not_to_proceed_json, blockers_json, dependencies_json, uncertainty,
                    source_finding_ids_json, source_comparison_ids_json, source_snapshot_ids_json,
                    evidence_fingerprints_json, evidence_freshness, evidence_references_json,
                    semantic_fingerprint, content_fingerprint, provenance_reference, audit_event_id,
                    supersedes_recommendation_id, superseded_by_recommendation_id, normalized_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recommendation.recommendation_id,
                    recommendation.schema_version,
                    recommendation.recommendation_policy_version,
                    recommendation.project_id,
                    recommendation.recommendation_type,
                    recommendation.created_timestamp.isoformat(),
                    recommendation.updated_timestamp.isoformat(),
                    recommendation.lifecycle_state,
                    recommendation.priority_tier,
                    recommendation.deterministic_score,
                    recommendation.score_breakdown.urgency_category,
                    recommendation.score_breakdown.effort_category,
                    recommendation.score_breakdown.reversibility_category,
                    recommendation.score_breakdown.model_dump_json(),
                    recommendation.title,
                    recommendation.concise_summary,
                    recommendation.rationale,
                    recommendation.why_it_matters,
                    recommendation.why_it_received_this_score,
                    json.dumps(recommendation.reasons_to_proceed, default=str, sort_keys=True),
                    json.dumps(recommendation.reasons_not_to_proceed, default=str, sort_keys=True),
                    json.dumps([item.model_dump(mode="json") for item in recommendation.blockers], default=str, sort_keys=True),
                    json.dumps(recommendation.dependencies, default=str, sort_keys=True),
                    recommendation.uncertainty,
                    json.dumps(recommendation.source_finding_ids, default=str, sort_keys=True),
                    json.dumps(recommendation.source_comparison_ids, default=str, sort_keys=True),
                    json.dumps(recommendation.source_snapshot_ids, default=str, sort_keys=True),
                    json.dumps(recommendation.evidence_fingerprints, default=str, sort_keys=True),
                    recommendation.evidence_freshness,
                    json.dumps([item.model_dump(mode="json") for item in recommendation.evidence_references], default=str, sort_keys=True),
                    recommendation.semantic_fingerprint,
                    recommendation.content_fingerprint,
                    recommendation.provenance_reference,
                    recommendation.audit_event_id,
                    recommendation.supersedes_recommendation_id,
                    recommendation.superseded_by_recommendation_id,
                    recommendation.model_dump_json(),
                ),
            )
            self.connection.execute(
                "DELETE FROM project_recommendation_evidence_links WHERE recommendation_id = ?",
                (recommendation.recommendation_id,),
            )
            self.connection.execute(
                "DELETE FROM project_recommendation_dependencies WHERE recommendation_id = ?",
                (recommendation.recommendation_id,),
            )
            for evidence in recommendation.evidence_references:
                self.connection.execute(
                    """
                    INSERT INTO project_recommendation_evidence_links(
                        recommendation_id, evidence_kind, evidence_identity, evidence_id, description, freshness, details_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        recommendation.recommendation_id,
                        evidence.evidence_kind,
                        evidence.evidence_id or "",
                        evidence.evidence_id,
                        evidence.description,
                        evidence.freshness,
                        json.dumps(evidence.details, default=str, sort_keys=True),
                    ),
                )
            for dependency_id in recommendation.dependencies:
                self.connection.execute(
                    """
                    INSERT INTO project_recommendation_dependencies(
                        recommendation_id, depends_on_recommendation_id, dependency_type, reason
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        recommendation.recommendation_id,
                        dependency_id,
                        "higher_order_condition",
                        "Recommendation ordering requires the dependency to be handled first.",
                    ),
                )

    def update_project_recommendation_audit_event(self, recommendation_id: str, audit_event_id: str) -> None:
        recommendation = self.get_project_recommendation(recommendation_id)
        if recommendation is None:
            return
        recommendation.audit_event_id = audit_event_id
        self.insert_project_recommendation(recommendation)

    def update_project_recommendation_state(
        self,
        recommendation_id: str,
        *,
        lifecycle_state: str | None = None,
        superseded_by_recommendation_id: str | None = None,
        updated_timestamp: datetime | None = None,
    ) -> None:
        if lifecycle_state is None and superseded_by_recommendation_id is None and updated_timestamp is None:
            return
        recommendation = self.get_project_recommendation(recommendation_id)
        if recommendation is None:
            return
        updated = recommendation.model_copy(
            update={
                **({"lifecycle_state": lifecycle_state} if lifecycle_state is not None else {}),
                **({"superseded_by_recommendation_id": superseded_by_recommendation_id} if superseded_by_recommendation_id is not None else {}),
                **({"updated_timestamp": updated_timestamp} if updated_timestamp is not None else {}),
            }
        )
        self.insert_project_recommendation(updated)

    def get_project_recommendation(self, recommendation_id: str) -> ProjectRecommendation | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM project_recommendations WHERE recommendation_id = ?",
            (recommendation_id,),
        ).fetchone()
        return ProjectRecommendation.model_validate_json(row["normalized_payload_json"]) if row else None

    def get_project_recommendation_by_semantic(
        self,
        project_id: str,
        semantic_fingerprint: str,
    ) -> ProjectRecommendation | None:
        row = self.connection.execute(
            """
            SELECT normalized_payload_json
            FROM project_recommendations
            WHERE project_id = ? AND semantic_fingerprint = ?
            ORDER BY created_timestamp DESC, recommendation_id DESC
            LIMIT 1
            """,
            (project_id, semantic_fingerprint),
        ).fetchone()
        return ProjectRecommendation.model_validate_json(row["normalized_payload_json"]) if row else None

    def list_project_recommendations(self, project_id: str) -> list[ProjectRecommendation]:
        rows = self.connection.execute(
            """
            SELECT normalized_payload_json
            FROM project_recommendations
            WHERE project_id = ?
            ORDER BY updated_timestamp DESC, priority_tier, deterministic_score DESC, recommendation_id DESC
            """,
            (project_id,),
        ).fetchall()
        return [ProjectRecommendation.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def list_project_recommendations_by_state(
        self,
        project_id: str,
        lifecycle_states: list[str],
    ) -> list[ProjectRecommendation]:
        if not lifecycle_states:
            return []
        placeholders = ",".join("?" for _ in lifecycle_states)
        rows = self.connection.execute(
            f"""
            SELECT normalized_payload_json
            FROM project_recommendations
            WHERE project_id = ? AND lifecycle_state IN ({placeholders})
            ORDER BY updated_timestamp DESC, priority_tier, deterministic_score DESC, recommendation_id DESC
            """,
            [project_id, *lifecycle_states],
        ).fetchall()
        return [ProjectRecommendation.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def list_recommendations_for_projects(self, project_ids: list[str]) -> list[ProjectRecommendation]:
        if not project_ids:
            return []
        placeholders = ",".join("?" for _ in project_ids)
        rows = self.connection.execute(
            f"""
            SELECT normalized_payload_json
            FROM project_recommendations
            WHERE project_id IN ({placeholders})
            ORDER BY updated_timestamp DESC, priority_tier, deterministic_score DESC, recommendation_id DESC
            """,
            project_ids,
        ).fetchall()
        return [ProjectRecommendation.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def upsert_project_contract(self, contract: ProjectContractRecord) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO project_contracts(
                    contract_id, project_id, current_revision_id, current_revision_number,
                    approved_revision_id, approved_revision_number, status, created_at,
                    updated_at, content_fingerprint, provenance_json, freshness_state,
                    normalized_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    contract.contract_id,
                    contract.project_id,
                    contract.current_revision_id,
                    contract.current_revision_number,
                    contract.approved_revision_id,
                    contract.approved_revision_number,
                    contract.status,
                    contract.created_at,
                    contract.updated_at,
                    contract.content_fingerprint,
                    contract.provenance.model_dump_json(),
                    contract.freshness_state,
                    contract.model_dump_json(),
                ),
            )

    def get_project_contract(self, project_id: str) -> ProjectContractRecord | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM project_contracts WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        return ProjectContractRecord.model_validate_json(row["normalized_payload_json"]) if row else None

    def get_project_contract_by_id(self, contract_id: str) -> ProjectContractRecord | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM project_contracts WHERE contract_id = ?",
            (contract_id,),
        ).fetchone()
        return ProjectContractRecord.model_validate_json(row["normalized_payload_json"]) if row else None

    def insert_project_contract_revision(self, revision: ProjectContractRevisionRecord) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO project_contract_revisions(
                    revision_id, contract_id, project_id, revision_number, previous_revision_id,
                    status, created_at, created_by, semantic_fingerprint, content_fingerprint,
                    provenance_json, evidence_references_json, freshness_state,
                    supersedes_revision_id, normalized_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    revision.revision_id,
                    revision.contract_id,
                    revision.project_id,
                    revision.revision_number,
                    revision.previous_revision_id,
                    revision.status,
                    revision.created_at,
                    revision.created_by,
                    revision.semantic_fingerprint,
                    revision.content_fingerprint,
                    revision.provenance.model_dump_json(),
                    json.dumps([item.model_dump(mode="json") for item in revision.evidence_references], default=str, sort_keys=True),
                    revision.freshness_state,
                    revision.supersedes_revision_id,
                    revision.model_dump_json(),
                ),
            )

    def update_project_contract_revision_provenance(
        self,
        revision_id: str,
        provenance: ProgrammeProvenanceRecord,
    ) -> None:
        revision = self.get_project_contract_revision(revision_id)
        if revision is None:
            return
        updated = revision.model_copy(update={"provenance": provenance, "normalized_payload": {}})
        updated.normalized_payload = updated.model_dump(mode="json")
        self.insert_project_contract_revision(updated)

    def get_project_contract_revision(self, revision_id: str) -> ProjectContractRevisionRecord | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM project_contract_revisions WHERE revision_id = ?",
            (revision_id,),
        ).fetchone()
        return ProjectContractRevisionRecord.model_validate_json(row["normalized_payload_json"]) if row else None

    def get_project_contract_revision_by_semantic(
        self,
        project_id: str,
        semantic_fingerprint: str,
    ) -> ProjectContractRevisionRecord | None:
        row = self.connection.execute(
            """
            SELECT normalized_payload_json
            FROM project_contract_revisions
            WHERE project_id = ? AND semantic_fingerprint = ?
            ORDER BY revision_number DESC, revision_id DESC
            LIMIT 1
            """,
            (project_id, semantic_fingerprint),
        ).fetchone()
        return ProjectContractRevisionRecord.model_validate_json(row["normalized_payload_json"]) if row else None

    def list_project_contract_revisions(self, project_id: str) -> list[ProjectContractRevisionRecord]:
        rows = self.connection.execute(
            """
            SELECT normalized_payload_json
            FROM project_contract_revisions
            WHERE project_id = ?
            ORDER BY revision_number DESC, created_at DESC, revision_id DESC
            """,
            (project_id,),
        ).fetchall()
        return [ProjectContractRevisionRecord.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def next_project_contract_revision_number(self, project_id: str) -> int:
        row = self.connection.execute(
            "SELECT COALESCE(MAX(revision_number), 0) AS max_revision FROM project_contract_revisions WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        return int(row["max_revision"] or 0) + 1

    def upsert_architecture_entity(self, entity: ArchitectureEntityRecord) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO architecture_entities(
                    entity_id, identity_key, kind, name, owning_project_or_domain, repository,
                    source_reference, current_revision_id, current_revision_number, status,
                    freshness_state, provenance_json, content_fingerprint, normalized_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entity.entity_id,
                    entity.identity_key,
                    entity.kind,
                    entity.name,
                    entity.owning_project_or_domain,
                    entity.repository,
                    entity.source_reference,
                    entity.current_revision_id,
                    entity.current_revision_number,
                    entity.status,
                    entity.freshness_state,
                    entity.provenance.model_dump_json(),
                    entity.content_fingerprint,
                    entity.model_dump_json(),
                ),
            )

    def get_architecture_entity(self, entity_id: str) -> ArchitectureEntityRecord | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM architecture_entities WHERE entity_id = ?",
            (entity_id,),
        ).fetchone()
        return ArchitectureEntityRecord.model_validate_json(row["normalized_payload_json"]) if row else None

    def get_architecture_entity_by_identity_key(self, identity_key: str) -> ArchitectureEntityRecord | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM architecture_entities WHERE identity_key = ?",
            (identity_key,),
        ).fetchone()
        return ArchitectureEntityRecord.model_validate_json(row["normalized_payload_json"]) if row else None

    def insert_architecture_entity_revision(self, revision: ArchitectureEntityRevisionRecord) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO architecture_entity_revisions(
                    revision_id, entity_id, identity_key, revision_number, previous_revision_id,
                    status, created_at, created_by, semantic_fingerprint, content_fingerprint,
                    provenance_json, evidence_references_json, freshness_state, supersedes_revision_id,
                    normalized_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    revision.revision_id,
                    revision.entity_id,
                    revision.content.identity_key,
                    revision.revision_number,
                    revision.previous_revision_id,
                    revision.status,
                    revision.created_at,
                    revision.created_by,
                    revision.semantic_fingerprint,
                    revision.content_fingerprint,
                    revision.provenance.model_dump_json(),
                    json.dumps([item.model_dump(mode="json") for item in revision.evidence_references], default=str, sort_keys=True),
                    revision.freshness_state,
                    revision.supersedes_revision_id,
                    revision.model_dump_json(),
                ),
            )

    def update_architecture_entity_revision_provenance(
        self,
        revision_id: str,
        provenance: ProgrammeProvenanceRecord,
    ) -> None:
        revision = self.get_architecture_entity_revision(revision_id)
        if revision is None:
            return
        updated = revision.model_copy(update={"provenance": provenance, "normalized_payload": {}})
        updated.normalized_payload = updated.model_dump(mode="json")
        self.insert_architecture_entity_revision(updated)

    def get_architecture_entity_revision(self, revision_id: str) -> ArchitectureEntityRevisionRecord | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM architecture_entity_revisions WHERE revision_id = ?",
            (revision_id,),
        ).fetchone()
        return ArchitectureEntityRevisionRecord.model_validate_json(row["normalized_payload_json"]) if row else None

    def get_architecture_entity_revision_by_semantic(
        self,
        identity_key: str,
        semantic_fingerprint: str,
    ) -> ArchitectureEntityRevisionRecord | None:
        row = self.connection.execute(
            """
            SELECT normalized_payload_json
            FROM architecture_entity_revisions
            WHERE identity_key = ? AND semantic_fingerprint = ?
            ORDER BY revision_number DESC, revision_id DESC
            LIMIT 1
            """,
            (identity_key, semantic_fingerprint),
        ).fetchone()
        return ArchitectureEntityRevisionRecord.model_validate_json(row["normalized_payload_json"]) if row else None

    def list_architecture_entities(
        self,
        *,
        project_id: str | None = None,
        kind: ArchitectureEntityKind | None = None,
    ) -> list[ArchitectureEntityRecord]:
        clauses = []
        params: list[object] = []
        if project_id is not None:
            clauses.append("owning_project_or_domain = ?")
            params.append(project_id)
        if kind is not None:
            clauses.append("kind = ?")
            params.append(kind)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            f"""
            SELECT normalized_payload_json
            FROM architecture_entities
            {where}
            ORDER BY kind, identity_key
            """,
            params,
        ).fetchall()
        return [ArchitectureEntityRecord.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def list_architecture_entity_revisions(self, entity_id: str) -> list[ArchitectureEntityRevisionRecord]:
        rows = self.connection.execute(
            """
            SELECT normalized_payload_json
            FROM architecture_entity_revisions
            WHERE entity_id = ?
            ORDER BY revision_number DESC, created_at DESC, revision_id DESC
            """,
            (entity_id,),
        ).fetchall()
        return [ArchitectureEntityRevisionRecord.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def next_architecture_entity_revision_number(self, entity_id: str) -> int:
        row = self.connection.execute(
            "SELECT COALESCE(MAX(revision_number), 0) AS max_revision FROM architecture_entity_revisions WHERE entity_id = ?",
            (entity_id,),
        ).fetchone()
        return int(row["max_revision"] or 0) + 1

    def upsert_architecture_relationship(self, relationship: ArchitectureRelationshipRecord) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO architecture_relationships(
                    relationship_id, identity_key, relationship_type, source_entity_id,
                    target_entity_id, current_revision_id, current_revision_number, status,
                    freshness_state, provenance_json, content_fingerprint, normalized_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    relationship.relationship_id,
                    relationship.identity_key,
                    relationship.relationship_type,
                    relationship.source_entity_id,
                    relationship.target_entity_id,
                    relationship.current_revision_id,
                    relationship.current_revision_number,
                    relationship.status,
                    relationship.freshness_state,
                    relationship.provenance.model_dump_json(),
                    relationship.content_fingerprint,
                    relationship.model_dump_json(),
                ),
            )

    def get_architecture_relationship(self, relationship_id: str) -> ArchitectureRelationshipRecord | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM architecture_relationships WHERE relationship_id = ?",
            (relationship_id,),
        ).fetchone()
        return ArchitectureRelationshipRecord.model_validate_json(row["normalized_payload_json"]) if row else None

    def get_architecture_relationship_by_identity_key(self, identity_key: str) -> ArchitectureRelationshipRecord | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM architecture_relationships WHERE identity_key = ?",
            (identity_key,),
        ).fetchone()
        return ArchitectureRelationshipRecord.model_validate_json(row["normalized_payload_json"]) if row else None

    def insert_architecture_relationship_revision(self, revision: ArchitectureRelationshipRevisionRecord) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO architecture_relationship_revisions(
                    revision_id, relationship_id, identity_key, revision_number, previous_revision_id,
                    status, created_at, created_by, semantic_fingerprint, content_fingerprint,
                    provenance_json, evidence_references_json, freshness_state, supersedes_revision_id,
                    normalized_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    revision.revision_id,
                    revision.relationship_id,
                    revision.content.identity_key,
                    revision.revision_number,
                    revision.previous_revision_id,
                    revision.status,
                    revision.created_at,
                    revision.created_by,
                    revision.semantic_fingerprint,
                    revision.content_fingerprint,
                    revision.provenance.model_dump_json(),
                    json.dumps([item.model_dump(mode="json") for item in revision.evidence_references], default=str, sort_keys=True),
                    revision.freshness_state,
                    revision.supersedes_revision_id,
                    revision.model_dump_json(),
                ),
            )

    def update_architecture_relationship_revision_provenance(
        self,
        revision_id: str,
        provenance: ProgrammeProvenanceRecord,
    ) -> None:
        revision = self.get_architecture_relationship_revision(revision_id)
        if revision is None:
            return
        updated = revision.model_copy(update={"provenance": provenance, "normalized_payload": {}})
        updated.normalized_payload = updated.model_dump(mode="json")
        self.insert_architecture_relationship_revision(updated)

    def get_architecture_relationship_revision(self, revision_id: str) -> ArchitectureRelationshipRevisionRecord | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM architecture_relationship_revisions WHERE revision_id = ?",
            (revision_id,),
        ).fetchone()
        return ArchitectureRelationshipRevisionRecord.model_validate_json(row["normalized_payload_json"]) if row else None

    def get_architecture_relationship_revision_by_semantic(
        self,
        identity_key: str,
        semantic_fingerprint: str,
    ) -> ArchitectureRelationshipRevisionRecord | None:
        row = self.connection.execute(
            """
            SELECT normalized_payload_json
            FROM architecture_relationship_revisions
            WHERE identity_key = ? AND semantic_fingerprint = ?
            ORDER BY revision_number DESC, revision_id DESC
            LIMIT 1
            """,
            (identity_key, semantic_fingerprint),
        ).fetchone()
        return ArchitectureRelationshipRevisionRecord.model_validate_json(row["normalized_payload_json"]) if row else None

    def list_architecture_relationships(
        self,
        *,
        source_entity_id: str | None = None,
        target_entity_id: str | None = None,
        relationship_type: ArchitectureRelationshipType | None = None,
    ) -> list[ArchitectureRelationshipRecord]:
        clauses = []
        params: list[object] = []
        if source_entity_id is not None:
            clauses.append("source_entity_id = ?")
            params.append(source_entity_id)
        if target_entity_id is not None:
            clauses.append("target_entity_id = ?")
            params.append(target_entity_id)
        if relationship_type is not None:
            clauses.append("relationship_type = ?")
            params.append(relationship_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            f"""
            SELECT normalized_payload_json
            FROM architecture_relationships
            {where}
            ORDER BY relationship_type, source_entity_id, target_entity_id
            """,
            params,
        ).fetchall()
        return [ArchitectureRelationshipRecord.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def list_architecture_relationship_revisions(self, relationship_id: str) -> list[ArchitectureRelationshipRevisionRecord]:
        rows = self.connection.execute(
            """
            SELECT normalized_payload_json
            FROM architecture_relationship_revisions
            WHERE relationship_id = ?
            ORDER BY revision_number DESC, created_at DESC, revision_id DESC
            """,
            (relationship_id,),
        ).fetchall()
        return [ArchitectureRelationshipRevisionRecord.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def next_architecture_relationship_revision_number(self, relationship_id: str) -> int:
        row = self.connection.execute(
            "SELECT COALESCE(MAX(revision_number), 0) AS max_revision FROM architecture_relationship_revisions WHERE relationship_id = ?",
            (relationship_id,),
        ).fetchone()
        return int(row["max_revision"] or 0) + 1

    def insert_work_package(self, package: WorkPackageRecord) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO work_packages(
                    work_package_id, schema_version, project_id, source_recommendation_id,
                    source_recommendation_semantic_fingerprint, source_recommendation_content_fingerprint,
                    source_recommendation_policy_version, current_revision_number, current_revision_id,
                    title, approval_state, gate_state, staleness_state, created_timestamp,
                    updated_timestamp, expiry_timestamp, package_fingerprint, semantic_fingerprint,
                    content_fingerprint, prompt_template_version, prompt_content_fingerprint,
                    generator_version, project_configuration_fingerprint, source_health_snapshot_ids_json,
                    source_health_snapshot_fingerprints_json, audit_reference, normalized_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    package.work_package_id,
                    package.schema_version,
                    package.project_id,
                    package.source_recommendation_id,
                    package.source_recommendation_semantic_fingerprint,
                    package.source_recommendation_content_fingerprint,
                    package.source_recommendation_policy_version,
                    package.current_revision_number,
                    package.current_revision_id,
                    package.title,
                    package.approval_state,
                    package.gate_state,
                    package.staleness_state,
                    package.created_timestamp.isoformat(),
                    package.updated_timestamp.isoformat(),
                    package.expiry_timestamp.isoformat() if package.expiry_timestamp else None,
                    package.package_fingerprint,
                    package.semantic_fingerprint,
                    package.content_fingerprint,
                    package.prompt_template_version,
                    package.prompt_content_fingerprint,
                    package.generator_version,
                    package.project_configuration_fingerprint,
                    json.dumps(package.source_health_snapshot_ids, default=str, sort_keys=True),
                    json.dumps(package.source_health_snapshot_fingerprints, default=str, sort_keys=True),
                    package.audit_reference,
                    package.model_dump_json(),
                ),
            )

    def insert_work_package_revision(self, revision: WorkPackageRevisionRecord) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO work_package_revisions(
                    revision_id, work_package_id, project_id, revision_number, previous_revision_id,
                    approval_state_at_creation, change_reason, changed_fields_json, created_timestamp,
                    package_fingerprint, semantic_fingerprint, content_fingerprint, prompt_content_fingerprint,
                    audit_reference, normalized_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    revision.revision_id,
                    revision.work_package_id,
                    revision.project_id,
                    revision.revision_number,
                    revision.previous_revision_id,
                    revision.approval_state_at_creation,
                    revision.change_reason,
                    json.dumps(revision.changed_fields, default=str, sort_keys=True),
                    revision.created_timestamp.isoformat(),
                    revision.package_fingerprint,
                    revision.semantic_fingerprint,
                    revision.content_fingerprint,
                    revision.prompt_content_fingerprint,
                    revision.audit_reference,
                    revision.model_dump_json(),
                ),
            )
            self.connection.execute(
                "DELETE FROM work_package_evidence_links WHERE work_package_id = ? AND revision_id = ?",
                (revision.work_package_id, revision.revision_id),
            )
            for evidence in revision.evidence_references:
                self.connection.execute(
                    """
                    INSERT INTO work_package_evidence_links(
                        work_package_id, revision_id, evidence_kind, evidence_identity, evidence_id,
                        description, freshness, details_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        revision.work_package_id,
                        revision.revision_id,
                        evidence.evidence_kind,
                        evidence.evidence_id or "",
                        evidence.evidence_id,
                        evidence.description,
                        evidence.freshness,
                        json.dumps(evidence.details, default=str, sort_keys=True),
                    ),
                )

    def insert_work_package_approval_decision(self, decision: WorkPackageApprovalDecisionRecord) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO work_package_approval_decisions(
                    decision_id, work_package_id, revision_id, revision_number, project_id,
                    decision, actor, decision_timestamp, evidence_fingerprint, human_note,
                    audit_reference, previous_state, next_state, normalized_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.decision_id,
                    decision.work_package_id,
                    decision.revision_id,
                    decision.revision_number,
                    decision.project_id,
                    decision.decision,
                    decision.actor,
                    decision.decision_timestamp.isoformat(),
                    decision.evidence_fingerprint,
                    decision.human_note,
                    decision.audit_reference,
                    decision.previous_state,
                    decision.next_state,
                    decision.model_dump_json(),
                ),
            )

    def insert_work_package_handoff(self, handoff: WorkPackageHandoffRecord) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO work_package_handoffs(
                    handoff_id, work_package_id, revision_id, revision_number, project_id,
                    approval_decision_id, approved_by, approved_at, prompt_fingerprint,
                    next_manual_action, rollback_reference, source_evidence_ids_json,
                    source_evidence_fingerprints_json, audit_reference, normalized_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    handoff.handoff_id,
                    handoff.work_package_id,
                    handoff.revision_id,
                    handoff.revision_number,
                    handoff.project_id,
                    handoff.approval_decision_id,
                    handoff.approved_by,
                    handoff.approved_at.isoformat(),
                    handoff.prompt_fingerprint,
                    handoff.next_manual_action,
                    handoff.rollback_reference,
                    json.dumps(handoff.source_evidence_ids, default=str, sort_keys=True),
                    json.dumps(handoff.source_evidence_fingerprints, default=str, sort_keys=True),
                    handoff.audit_reference,
                    handoff.model_dump_json(),
                ),
            )

    def insert_work_package_outcome(self, outcome: WorkPackageOutcomeRecord) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO work_package_outcomes(
                    outcome_id, work_package_id, revision_id, revision_number, project_id, outcome,
                    actor, recorded_at, note, evidence_fingerprint, audit_reference, normalized_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    outcome.outcome_id,
                    outcome.work_package_id,
                    outcome.revision_id,
                    outcome.revision_number,
                    outcome.project_id,
                    outcome.outcome,
                    outcome.actor,
                    outcome.recorded_at.isoformat(),
                    outcome.note,
                    outcome.evidence_fingerprint,
                    outcome.audit_reference,
                    outcome.model_dump_json(),
                ),
            )

    def update_work_package_state(
        self,
        work_package_id: str,
        *,
        approval_state: str | None = None,
        gate_state: str | None = None,
        staleness_state: str | None = None,
        current_revision_id: str | None = None,
        current_revision_number: int | None = None,
        updated_timestamp: datetime | None = None,
        expiry_timestamp: datetime | None = None,
        audit_reference: str | None = None,
    ) -> None:
        package = self.get_work_package(work_package_id)
        if package is None:
            return
        updated = package.model_copy(
            update={
                **({"approval_state": approval_state} if approval_state is not None else {}),
                **({"gate_state": gate_state} if gate_state is not None else {}),
                **({"staleness_state": staleness_state} if staleness_state is not None else {}),
                **({"current_revision_id": current_revision_id} if current_revision_id is not None else {}),
                **({"current_revision_number": current_revision_number} if current_revision_number is not None else {}),
                **({"updated_timestamp": updated_timestamp} if updated_timestamp is not None else {}),
                **({"expiry_timestamp": expiry_timestamp} if expiry_timestamp is not None else {}),
                **({"audit_reference": audit_reference} if audit_reference is not None else {}),
            }
        )
        self.insert_work_package(updated)

    def update_work_package_audit_reference(self, work_package_id: str, audit_reference: str) -> None:
        package = self.get_work_package(work_package_id)
        if package is None:
            return
        package.audit_reference = audit_reference
        self.insert_work_package(package)

    def get_work_package(self, work_package_id: str) -> WorkPackageRecord | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM work_packages WHERE work_package_id = ?",
            (work_package_id,),
        ).fetchone()
        return WorkPackageRecord.model_validate_json(row["normalized_payload_json"]) if row else None

    def get_work_package_by_semantic(self, project_id: str, semantic_fingerprint: str) -> WorkPackageRecord | None:
        row = self.connection.execute(
            """
            SELECT normalized_payload_json
            FROM work_packages
            WHERE project_id = ? AND semantic_fingerprint = ?
            ORDER BY current_revision_number DESC, updated_timestamp DESC
            LIMIT 1
            """,
            (project_id, semantic_fingerprint),
        ).fetchone()
        return WorkPackageRecord.model_validate_json(row["normalized_payload_json"]) if row else None

    def list_work_packages(
        self,
        project_id: str | None = None,
        approval_state: str | None = None,
        staleness_state: str | None = None,
    ) -> list[WorkPackageRecord]:
        clauses = []
        params: list[object] = []
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if approval_state:
            clauses.append("approval_state = ?")
            params.append(approval_state)
        if staleness_state:
            clauses.append("staleness_state = ?")
            params.append(staleness_state)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            f"""
            SELECT normalized_payload_json
            FROM work_packages
            {where}
            ORDER BY updated_timestamp DESC, current_revision_number DESC, work_package_id DESC
            """,
            params,
        ).fetchall()
        return [WorkPackageRecord.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def get_work_package_revision(self, revision_id: str) -> WorkPackageRevisionRecord | None:
        row = self.connection.execute(
            "SELECT normalized_payload_json FROM work_package_revisions WHERE revision_id = ?",
            (revision_id,),
        ).fetchone()
        return WorkPackageRevisionRecord.model_validate_json(row["normalized_payload_json"]) if row else None

    def list_work_package_revisions(self, work_package_id: str) -> list[WorkPackageRevisionRecord]:
        rows = self.connection.execute(
            """
            SELECT normalized_payload_json
            FROM work_package_revisions
            WHERE work_package_id = ?
            ORDER BY revision_number DESC, created_timestamp DESC
            """,
            (work_package_id,),
        ).fetchall()
        return [WorkPackageRevisionRecord.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def list_work_package_approval_decisions(self, work_package_id: str) -> list[WorkPackageApprovalDecisionRecord]:
        rows = self.connection.execute(
            """
            SELECT normalized_payload_json
            FROM work_package_approval_decisions
            WHERE work_package_id = ?
            ORDER BY decision_timestamp DESC, decision_id DESC
            """,
            (work_package_id,),
        ).fetchall()
        return [WorkPackageApprovalDecisionRecord.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def list_work_package_handoffs(self, work_package_id: str) -> list[WorkPackageHandoffRecord]:
        rows = self.connection.execute(
            """
            SELECT normalized_payload_json
            FROM work_package_handoffs
            WHERE work_package_id = ?
            ORDER BY approved_at DESC, handoff_id DESC
            """,
            (work_package_id,),
        ).fetchall()
        return [WorkPackageHandoffRecord.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def list_work_package_outcomes(self, work_package_id: str) -> list[WorkPackageOutcomeRecord]:
        rows = self.connection.execute(
            """
            SELECT normalized_payload_json
            FROM work_package_outcomes
            WHERE work_package_id = ?
            ORDER BY recorded_at DESC, outcome_id DESC
            """,
            (work_package_id,),
        ).fetchall()
        return [WorkPackageOutcomeRecord.model_validate_json(row["normalized_payload_json"]) for row in rows]

    def insert_audit_event(self, event: AuditEvent) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO audit_events(
                    event_id, timestamp, category, operation, project_id,
                    outcome, metadata_json, error_classification
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.timestamp.isoformat(),
                    event.category,
                    event.operation,
                    event.project_id,
                    event.outcome,
                    json.dumps(event.metadata, default=str, sort_keys=True),
                    event.error_classification,
                ),
            )

    def list_audit_events(self, limit: int = 100) -> list[dict[str, object]]:
        rows = self.connection.execute(
            "SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT ?", (max(1, min(limit, 1000)),)
        ).fetchall()
        events = []
        for row in rows:
            item = dict(row)
            item["metadata"] = json.loads(str(item.pop("metadata_json")))
            events.append(item)
        return events

    def insert_agent_run(self, run: AgentRunRecord) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO agent_runs(
                    run_id, project_id, question, question_category, snapshot_id,
                    retrieval_queries_json, selected_evidence_json, provider, model_name,
                    start_timestamp, finish_timestamp, status, structured_answer_json,
                    confidence, warnings_json, prompt_injection_warnings_json, safe_error, usage_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.project_id,
                    run.question,
                    run.question_category,
                    run.snapshot_id,
                    json.dumps(run.retrieval_queries, default=str, sort_keys=True),
                    json.dumps([item.model_dump(mode="json") for item in run.selected_evidence], default=str, sort_keys=True),
                    run.provider,
                    run.model_name,
                    run.start_timestamp.isoformat(),
                    run.finish_timestamp.isoformat(),
                    run.status,
                    json.dumps(run.structured_answer, default=str, sort_keys=True),
                    run.confidence,
                    json.dumps(run.warnings, default=str, sort_keys=True),
                    json.dumps(run.prompt_injection_warnings, default=str, sort_keys=True),
                    run.safe_error,
                    json.dumps(run.usage, default=str, sort_keys=True),
                ),
            )

    def list_agent_runs(self, limit: int = 100) -> list[dict[str, object]]:
        rows = self.connection.execute(
            "SELECT * FROM agent_runs ORDER BY start_timestamp DESC LIMIT ?", (max(1, min(limit, 1000)),)
        ).fetchall()
        return [self._row_to_agent_run_dict(row) for row in rows]

    def get_agent_run(self, run_id: str) -> dict[str, object] | None:
        row = self.connection.execute("SELECT * FROM agent_runs WHERE run_id = ?", (run_id,)).fetchone()
        return self._row_to_agent_run_dict(row) if row else None

    def _row_to_agent_run_dict(self, row: sqlite3.Row) -> dict[str, object]:
        item = dict(row)
        item["retrieval_queries"] = json.loads(str(item.pop("retrieval_queries_json")))
        item["selected_evidence"] = json.loads(str(item.pop("selected_evidence_json")))
        item["structured_answer"] = json.loads(str(item.pop("structured_answer_json")))
        item["warnings"] = json.loads(str(item.pop("warnings_json")))
        item["prompt_injection_warnings"] = json.loads(str(item.pop("prompt_injection_warnings_json")))
        item["usage"] = json.loads(str(item.pop("usage_json")))
        return item

    def list_rows(self, table: str, *, order_by: str | None = None) -> list[dict[str, object]]:
        sql = f"SELECT * FROM {table}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        rows = self.connection.execute(sql).fetchall()
        return [dict(row) for row in rows]

    def fetch_row(self, table: str, where: str, params: tuple[object, ...]) -> dict[str, object] | None:
        row = self.connection.execute(f"SELECT * FROM {table} WHERE {where}", params).fetchone()
        return dict(row) if row else None


def _make_snippet(content: str, query: str, radius: int = 120) -> str:
    lower = content.lower()
    index = lower.find(query.lower())
    if index < 0:
        return content[: radius * 2].replace("\n", " ")
    start = max(0, index - radius)
    end = min(len(content), index + len(query) + radius)
    return content[start:end].replace("\n", " ")


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
