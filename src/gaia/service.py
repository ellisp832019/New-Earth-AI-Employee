from __future__ import annotations

from collections import Counter

from gaia.audit import AuditRecorder
from gaia.change_intelligence import ChangeIntelligenceService
from gaia.config import Settings
from gaia.db import Database
from gaia.git_inspector import GitInspector
from gaia.models import (
    ProjectChangeComparison,
    ProjectChangeFinding,
    ProjectChangePortfolio,
    ProjectConfig,
    ProjectHealthPortfolio,
    ProjectHealthSnapshot,
    ProjectRecommendation,
    ProjectRecommendationPortfolio,
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
    ArchitectureRegistryService,
    ArchitectureRelationshipRecord,
    ArchitectureRelationshipRevisionRecord,
    ArchitectureRelationshipType,
    ProjectContractRecord,
    ProjectContractRevisionRecord,
    ProjectContractService,
)
from gaia.project_health import ProjectHealthService
from gaia.recommendations import RecommendationService
from gaia.reports import foundation_report_json, foundation_report_markdown
from gaia.scanner import DocumentScanner
from gaia.work_packages import WorkPackageService


class ProjectService:
    def __init__(self, settings: Settings, database: Database | None = None) -> None:
        self.settings = settings
        self.database = database or Database(settings.database_path)
        self.audit = AuditRecorder(self.database)
        self.git = GitInspector(settings.git_timeout_seconds, settings.max_git_output_bytes)
        self.project_health_service = ProjectHealthService(settings, self.database, self.audit, self.git)
        self.change_intelligence_service = ChangeIntelligenceService(settings, self.database, self.audit)
        self.recommendation_service = RecommendationService(settings, self.database, self.audit)
        self.work_package_service = WorkPackageService(settings, self.database, self.audit)
        self.project_contract_service = ProjectContractService(settings, self.database, self.audit)
        self.architecture_registry_service = ArchitectureRegistryService(settings, self.database, self.audit)
        self.project_contract_service.bootstrap_from_settings()
        self.architecture_registry_service.bootstrap_from_settings()
        self.scanner = DocumentScanner(settings.max_file_bytes)

    def get_project(self, project_id: str) -> ProjectConfig:
        try:
            return self.settings.projects[project_id]
        except KeyError as exc:
            raise KeyError(f"Unknown project: {project_id}") from exc

    def scan(self, project_id: str) -> list[dict[str, object]]:
        project = self.get_project(project_id)
        before = self.git.inspect(project.root)
        tracked = self.git.tracked_files(project.root)
        try:
            records = self.scanner.scan(project, tracked)
            after = self.git.inspect(project.root)
            if before.model_dump() != after.model_dump():
                self.audit.record(
                    category="safety",
                    operation="read_only_integrity_check",
                    project_id=project_id,
                    outcome="failure",
                    metadata={"message": "Repository state changed during scan"},
                    error_classification="RepositoryStateChanged",
                )
                raise RuntimeError("Repository state changed during read-only scan")
            self.database.replace_documents(project_id, records)
            self.audit.record(
                category="documents",
                operation="scan",
                project_id=project_id,
                outcome="success",
                metadata={"document_count": len(records)},
            )
            return [record.model_dump(mode="json", exclude={"content"}) for record in records]
        except Exception as exc:
            self.audit.record(
                category="documents",
                operation="scan",
                project_id=project_id,
                outcome="failure",
                metadata={"error": str(exc)},
                error_classification=type(exc).__name__,
            )
            raise

    def snapshot(self, project_id: str) -> RepositorySnapshot:
        project = self.get_project(project_id)
        git_state = self.git.inspect(project.root)
        rows = self.database.list_documents(project_id)
        counts = Counter(str(row["extension"]) for row in rows)
        statuses = Counter(str(row["indexing_status"]) for row in rows)
        warnings = [str(row["warning"]) for row in rows if row.get("warning")]
        important_paths = {
            important: (project.root / important).exists() for important in project.important_paths
        }
        snapshot = RepositorySnapshot(
            project_id=project_id,
            project_name=project.name,
            project_root=str(project.root),
            git=git_state,
            document_count=len(rows),
            indexed_count=statuses.get("indexed", 0),
            skipped_count=statuses.get("skipped", 0),
            failed_count=statuses.get("failed", 0),
            counts_by_extension=dict(counts),
            scan_warnings=warnings[:100],
            important_paths=important_paths,
        )
        self.database.insert_snapshot(snapshot)
        self.audit.record(
            category="repository",
            operation="snapshot",
            project_id=project_id,
            outcome="success",
            metadata={"snapshot_id": snapshot.snapshot_id},
        )
        return snapshot

    def search(
        self,
        project_id: str,
        query: str,
        limit: int = 20,
        path_prefix: str | None = None,
        extension: str | None = None,
    ) -> list[SearchResult]:
        self.get_project(project_id)
        results = self.database.search(
            project_id, query, limit=limit, path_prefix=path_prefix, extension=extension
        )
        self.audit.record(
            category="documents",
            operation="search",
            project_id=project_id,
            outcome="success",
            metadata={"query_length": len(query), "result_count": len(results)},
        )
        return results

    def foundation_report(self, project_id: str, format_name: str = "markdown") -> str:
        snapshot = self.database.latest_snapshot(project_id) or self.snapshot(project_id)
        self.audit.record(
            category="reports",
            operation="foundation_report",
            project_id=project_id,
            outcome="success",
            metadata={"snapshot_id": snapshot.snapshot_id, "format": format_name},
        )
        return foundation_report_json(snapshot) if format_name == "json" else foundation_report_markdown(snapshot)

    def project_health(self, project_id: str) -> ProjectHealthSnapshot:
        return self.project_health_service.capture_project_health(project_id)

    def project_health_snapshot(self, snapshot_id: str) -> ProjectHealthSnapshot | None:
        return self.project_health_service.get_project_health_snapshot(snapshot_id)

    def project_health_snapshots(self, project_id: str) -> list[ProjectHealthSnapshot]:
        return self.project_health_service.list_project_health_snapshots(project_id)

    def latest_project_health_snapshot(self, project_id: str) -> ProjectHealthSnapshot | None:
        return self.project_health_service.latest_project_health_snapshot(project_id)

    def project_health_portfolio(self) -> ProjectHealthPortfolio:
        return self.project_health_service.portfolio_view()

    def compare_project_health_snapshots(
        self, previous_snapshot_id: str, current_snapshot_id: str
    ) -> ProjectChangeComparison:
        return self.change_intelligence_service.compare_snapshots(previous_snapshot_id, current_snapshot_id)

    def compare_latest_project_health(self, project_id: str) -> ProjectChangeComparison | None:
        return self.change_intelligence_service.compare_latest_project_health(project_id)

    def get_project_change_comparison(self, comparison_id: str) -> ProjectChangeComparison | None:
        return self.change_intelligence_service.get_change_comparison(comparison_id)

    def list_project_change_findings(self, project_id: str) -> list[ProjectChangeFinding]:
        return self.change_intelligence_service.list_project_change_findings(project_id)

    def latest_project_change_findings(self, project_id: str) -> list[ProjectChangeFinding]:
        return self.change_intelligence_service.latest_project_change_findings(project_id)

    def recent_project_change_findings(self, limit: int = 50) -> list[ProjectChangeFinding]:
        return self.change_intelligence_service.recent_project_change_findings(limit)

    def project_change_portfolio(self) -> ProjectChangePortfolio:
        return self.change_intelligence_service.portfolio_change_view()

    def generate_project_recommendations(self, project_id: str) -> list[ProjectRecommendation]:
        return self.recommendation_service.generate_project_recommendations(project_id)

    def project_recommendations(self, project_id: str) -> list[ProjectRecommendation]:
        return self.recommendation_service.generate_project_recommendations(project_id)

    def list_project_recommendations(self, project_id: str) -> list[ProjectRecommendation]:
        return self.recommendation_service.list_project_recommendations(project_id)

    def get_project_recommendation(self, recommendation_id: str) -> ProjectRecommendation | None:
        return self.recommendation_service.get_recommendation(recommendation_id)

    def recommendation_queue(self, project_id: str | None = None) -> list[ProjectRecommendation]:
        return self.recommendation_service.recommendation_queue(project_id)

    def project_recommendation_portfolio(self) -> ProjectRecommendationPortfolio:
        return self.recommendation_service.project_recommendation_portfolio()

    def generate_work_package(self, recommendation_id: str) -> WorkPackageRecord:
        return self.work_package_service.generate_work_package(recommendation_id)

    def work_packages(
        self,
        *,
        project_id: str | None = None,
        approval_state: str | None = None,
        staleness_state: str | None = None,
    ) -> list[WorkPackageRecord]:
        return self.work_package_service.list_work_packages(
            project_id=project_id,
            approval_state=approval_state,
            staleness_state=staleness_state,
        )

    def get_work_package(self, work_package_id: str) -> WorkPackageRecord | None:
        return self.work_package_service.get_work_package(work_package_id)

    def work_package_revisions(self, work_package_id: str) -> list[WorkPackageRevisionRecord]:
        return self.work_package_service.list_work_package_revisions(work_package_id)

    def work_package_approval_decisions(self, work_package_id: str) -> list[WorkPackageApprovalDecisionRecord]:
        return self.work_package_service.list_work_package_approval_decisions(work_package_id)

    def work_package_handoffs(self, work_package_id: str) -> list[WorkPackageHandoffRecord]:
        return self.work_package_service.list_work_package_handoffs(work_package_id)

    def work_package_outcomes(self, work_package_id: str) -> list[WorkPackageOutcomeRecord]:
        return self.work_package_service.list_work_package_outcomes(work_package_id)

    def work_package_submit_for_review(self, work_package_id: str, revision_number: int, *, actor: str = "manual") -> WorkPackageRecord:
        return self.work_package_service.submit_for_review(work_package_id, revision_number=revision_number, actor=actor)

    def work_package_approve(
        self,
        work_package_id: str,
        revision_number: int,
        *,
        actor: str,
        human_note: str | None = None,
    ) -> WorkPackageRecord:
        return self.work_package_service.approve_work_package(
            work_package_id,
            revision_number=revision_number,
            actor=actor,
            human_note=human_note,
        )

    def work_package_reject(
        self,
        work_package_id: str,
        revision_number: int,
        *,
        actor: str,
        human_note: str | None = None,
    ) -> WorkPackageRecord:
        return self.work_package_service.reject_work_package(
            work_package_id,
            revision_number=revision_number,
            actor=actor,
            human_note=human_note,
        )

    def work_package_handoff(
        self,
        work_package_id: str,
        revision_number: int,
        *,
        approved_by: str,
        next_manual_action: str = "Copy the approved Codex prompt into Codex.",
        rollback_reference: str = "Return to the recorded baseline commit or last approved revision.",
    ) -> WorkPackageRecord:
        return self.work_package_service.handoff_work_package(
            work_package_id,
            revision_number=revision_number,
            approved_by=approved_by,
            next_manual_action=next_manual_action,
            rollback_reference=rollback_reference,
        )

    def work_package_record_outcome(
        self,
        work_package_id: str,
        revision_number: int,
        *,
        outcome: str,
        actor: str,
        note: str | None = None,
    ) -> WorkPackageRecord:
        return self.work_package_service.record_outcome(
            work_package_id,
            revision_number=revision_number,
            outcome=outcome,  # type: ignore[arg-type]
            actor=actor,
            note=note,
        )

    def revise_work_package(
        self,
        work_package_id: str,
        *,
        change_reason: str,
        field_updates: dict[str, object] | None = None,
        actor: str = "manual",
    ) -> WorkPackageRecord:
        return self.work_package_service.revise_work_package(
            work_package_id,
            change_reason=change_reason,
            field_updates=field_updates,
            actor=actor,
        )

    def detect_work_package_staleness(self, work_package_id: str) -> WorkPackageRecord:
        return self.work_package_service.detect_staleness(work_package_id)

    def expire_work_package(self, work_package_id: str, reason: str) -> WorkPackageRecord:
        return self.work_package_service.expire_work_package(work_package_id, reason=reason)

    def render_work_package_prompt(self, work_package_id: str, revision_number: int | None = None) -> str:
        return self.work_package_service.render_codex_prompt(work_package_id, revision_number=revision_number)

    def work_package_summary(self, work_package_id: str) -> dict[str, object]:
        return self.work_package_service.render_summary(work_package_id)

    def project_contract(self, project_id: str) -> ProjectContractRecord | None:
        return self.project_contract_service.get_project_contract(project_id)

    def project_contract_revision(self, revision_id: str) -> ProjectContractRevisionRecord | None:
        return self.project_contract_service.get_contract_revision(revision_id)

    def project_contract_revisions(self, project_id: str) -> list[ProjectContractRevisionRecord]:
        return self.project_contract_service.list_contract_revisions(project_id)

    def current_project_contract(self, project_id: str) -> ProjectContractRecord | None:
        return self.project_contract_service.current_approved_contract(project_id)

    def architecture_entities(
        self,
        *,
        project_id: str | None = None,
        kind: ArchitectureEntityKind | None = None,
    ) -> list[ArchitectureEntityRecord]:
        if project_id is not None:
            return self.architecture_registry_service.list_entities_by_project(project_id)
        if kind is not None:
            return self.architecture_registry_service.list_entities_by_kind(kind)
        return self.architecture_registry_service.list_entities()

    def architecture_entity(self, entity_id: str) -> ArchitectureEntityRecord | None:
        return self.architecture_registry_service.get_entity(entity_id)

    def architecture_entity_revision(self, revision_id: str) -> ArchitectureEntityRevisionRecord | None:
        return self.architecture_registry_service.get_entity_revision(revision_id)

    def architecture_entity_revisions(self, entity_id: str) -> list[ArchitectureEntityRevisionRecord]:
        return self.architecture_registry_service.list_entity_revisions(entity_id)

    def architecture_relationships(
        self,
        *,
        source_entity_id: str | None = None,
        target_entity_id: str | None = None,
        relationship_type: ArchitectureRelationshipType | None = None,
    ) -> list[ArchitectureRelationshipRecord]:
        if source_entity_id is not None:
            return self.architecture_registry_service.list_relationships_by_source(source_entity_id)
        if target_entity_id is not None:
            return self.architecture_registry_service.list_relationships_by_target(target_entity_id)
        if relationship_type is not None:
            return self.architecture_registry_service.list_relationships_by_type(relationship_type)
        return self.architecture_registry_service.list_relationships()

    def architecture_relationship(self, relationship_id: str) -> ArchitectureRelationshipRecord | None:
        return self.architecture_registry_service.get_relationship(relationship_id)

    def architecture_relationship_revision(self, revision_id: str) -> ArchitectureRelationshipRevisionRecord | None:
        return self.architecture_registry_service.get_relationship_revision(revision_id)

    def architecture_relationship_revisions(self, relationship_id: str) -> list[ArchitectureRelationshipRevisionRecord]:
        return self.architecture_registry_service.list_relationship_revisions(relationship_id)
