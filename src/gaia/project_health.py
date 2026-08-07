from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from gaia.audit import AuditRecorder
from gaia.config import Settings
from gaia.db import Database
from gaia.git_inspector import GitInspectionError, GitInspector
from gaia.models import (
    ProjectConfig,
    ProjectHealthEvidenceReference,
    ProjectHealthPortfolio,
    ProjectHealthPortfolioEntry,
    ProjectHealthSnapshot,
    ProjectHealthStatus,
    RepositorySnapshot,
    utc_now,
)

_STATUS_ORDER = {"blocked": 0, "attention": 1, "healthy": 2, "unknown": 3}


class ProjectHealthService:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        audit: AuditRecorder,
        git: GitInspector | None = None,
    ) -> None:
        self.settings = settings
        self.database = database
        self.audit = audit
        self.git = git or GitInspector(settings.git_timeout_seconds, settings.max_git_output_bytes)

    def get_project(self, project_id: str) -> ProjectConfig:
        try:
            return self.settings.projects[project_id]
        except KeyError as exc:
            raise KeyError(f"Unknown project: {project_id}") from exc

    def capture_project_health(self, project_id: str) -> ProjectHealthSnapshot:
        project = self.get_project(project_id)
        captured_at = utc_now()

        try:
            normalized = self._normalize_project_health(project, captured_at)
            snapshot = self._build_snapshot(project, captured_at, normalized)
            self.database.insert_project_health_snapshot(snapshot)
            event = self.audit.record(
                category="project_health",
                operation="capture",
                project_id=project_id,
                outcome="success",
                metadata={
                    "snapshot_id": snapshot.snapshot_id,
                    "normalized_status": snapshot.normalized_status,
                    "content_fingerprint": snapshot.content_fingerprint,
                },
            )
            snapshot.audit_event_id = event.event_id
            self.database.update_project_health_snapshot_audit_event(snapshot.snapshot_id, event.event_id)
            return snapshot
        except Exception as exc:
            self.audit.record(
                category="project_health",
                operation="capture",
                project_id=project_id,
                outcome="failure",
                metadata={"error": str(exc)},
                error_classification=type(exc).__name__,
            )
            raise

    def get_project_health_snapshot(self, snapshot_id: str) -> ProjectHealthSnapshot | None:
        return self.database.get_project_health_snapshot(snapshot_id)

    def list_project_health_snapshots(self, project_id: str) -> list[ProjectHealthSnapshot]:
        self.get_project(project_id)
        return self.database.list_project_health_snapshots(project_id)

    def latest_project_health_snapshot(self, project_id: str) -> ProjectHealthSnapshot | None:
        self.get_project(project_id)
        return self.database.latest_project_health_snapshot(project_id)

    def capture_all_enabled_project_health(self) -> list[ProjectHealthSnapshot]:
        snapshots = []
        for project in self.enabled_projects():
            snapshots.append(self.capture_project_health(project.project_id))
        return snapshots

    def enabled_projects(self) -> list[ProjectConfig]:
        return [project for project in self.settings.projects.values() if project.enabled]

    def portfolio_view(self) -> ProjectHealthPortfolio:
        entries: list[ProjectHealthPortfolioEntry] = []
        projects_without_snapshots: list[str] = []
        counts: Counter[str] = Counter()
        latest_ids: dict[str, str] = {}
        for project in sorted(self.enabled_projects(), key=lambda item: item.project_id):
            snapshot = self.latest_project_health_snapshot(project.project_id)
            if snapshot is None:
                projects_without_snapshots.append(project.project_id)
                entries.append(
                    ProjectHealthPortfolioEntry(
                        project_id=project.project_id,
                        project_name=project.name,
                        project_root=str(project.root),
                        enabled=project.enabled,
                        repository_type=project.repository_type,
                        normalized_status="unknown",
                        evidence_freshness="unknown",
                    )
                )
                counts["unknown"] += 1
                continue

            counts[snapshot.normalized_status] += 1
            latest_ids[project.project_id] = snapshot.snapshot_id
            entries.append(
                ProjectHealthPortfolioEntry(
                    project_id=project.project_id,
                    project_name=project.name,
                    project_root=str(project.root),
                    enabled=project.enabled,
                    repository_type=project.repository_type,
                    latest_snapshot_id=snapshot.snapshot_id,
                    latest_capture_timestamp=snapshot.capture_timestamp,
                    normalized_status=snapshot.normalized_status,
                    snapshot_count=len(self.list_project_health_snapshots(project.project_id)),
                    evidence_freshness=str(
                        snapshot.normalized_payload.get("configured_evidence", {}).get("evidence_freshness", {}).get(
                            "state", "unknown"
                        )
                    ),
                    reason_codes=list(snapshot.reason_codes),
                    latest_snapshot=snapshot,
                )
            )
        return ProjectHealthPortfolio(
            generated_at=utc_now(),
            enabled_project_count=len(entries),
            projects=entries,
            projects_without_snapshots=projects_without_snapshots,
            counts_by_status=dict(sorted(counts.items(), key=lambda item: _STATUS_ORDER.get(item[0], 99))),
            latest_snapshot_ids=latest_ids,
        )

    def _build_snapshot(
        self,
        project: ProjectConfig,
        captured_at: datetime,
        normalized: dict[str, Any],
    ) -> ProjectHealthSnapshot:
        snapshot = ProjectHealthSnapshot(
            project_id=project.project_id,
            project_name=project.name,
            project_root=str(project.root),
            project_configuration_fingerprint=project.config_fingerprint(),
            capture_timestamp=captured_at,
            normalized_status=normalized["normalized_status"],
            reason_codes=normalized["reason_codes"],
            explanations=normalized["explanations"],
            blocking_conditions=normalized["blocking_conditions"],
            attention_conditions=normalized["attention_conditions"],
            unknown_fields=normalized["unknown_fields"],
            evidence_references=[
                ProjectHealthEvidenceReference(**item) for item in normalized["evidence_references"]
            ],
            normalized_payload=normalized,
            provenance_reference=normalized["provenance_reference"],
        )
        snapshot.content_fingerprint = _fingerprint_project_health(snapshot)
        return snapshot

    def _normalize_project_health(self, project: ProjectConfig, captured_at: datetime) -> dict[str, Any]:
        project_root = project.root
        root_exists = False
        root_accessible = False
        canonical_root = str(project_root)
        canonical_valid = False
        try:
            root_exists = project_root.exists()
            root_accessible = root_exists and os.access(project_root, os.R_OK | os.X_OK)
            canonical_valid = project_root.is_absolute() and project_root.resolve(strict=False) == project_root
        except OSError:
            root_exists = False
            root_accessible = False
            canonical_valid = False

        repo_snapshot = self.database.latest_snapshot(project.project_id)
        repository_evidence_reference = _evidence_reference(repo_snapshot)
        latest_scan_reference = repository_evidence_reference["evidence_id"]

        if not project.enabled:
            return _payload(
                project,
                captured_at,
                root_exists=root_exists,
                root_accessible=root_accessible,
                canonical_valid=canonical_valid,
                git_state=None,
                status="blocked",
                reason_codes=["project_disabled"],
                explanations=["The project is disabled in the canonical registry."],
                blocking_conditions=["Project is disabled."],
                attention_conditions=[],
                unknown_fields=["repository_state", "working_tree_state", "snapshot_freshness"],
                evidence_references=_compact_references(
                    [
                        _build_reference(
                            "project_config",
                            project.project_id,
                            "Canonical project registry record",
                            details={"enabled": project.enabled},
                        )
                    ]
                ),
                latest_repository_snapshot=repo_snapshot,
                latest_scan_reference=latest_scan_reference,
                provenance_reference=repository_evidence_reference["evidence_id"],
            )

        if not canonical_valid:
            return _payload(
                project,
                captured_at,
                root_exists=root_exists,
                root_accessible=root_accessible,
                canonical_valid=canonical_valid,
                git_state=None,
                status="blocked",
                reason_codes=["canonical_path_invalid"],
                explanations=["The configured project root is not a canonical absolute path."],
                blocking_conditions=["Canonical path validation failed."],
                attention_conditions=[],
                unknown_fields=["repository_state", "working_tree_state", "snapshot_freshness"],
                evidence_references=_compact_references(
                    [
                        _build_reference(
                            "project_config",
                            project.project_id,
                            "Canonical project registry record",
                            details={"root": canonical_root},
                        )
                    ]
                ),
                latest_repository_snapshot=repo_snapshot,
                latest_scan_reference=latest_scan_reference,
                provenance_reference=repository_evidence_reference["evidence_id"],
            )

        if not root_exists:
            return _payload(
                project,
                captured_at,
                root_exists=False,
                root_accessible=False,
                canonical_valid=True,
                git_state=None,
                status="blocked",
                reason_codes=["project_root_missing"],
                explanations=["The configured project root does not exist."],
                blocking_conditions=["Project root is unavailable."],
                attention_conditions=[],
                unknown_fields=["repository_state", "working_tree_state", "snapshot_freshness"],
                evidence_references=_compact_references(
                    [
                        _build_reference(
                            "project_config",
                            project.project_id,
                            "Canonical project registry record",
                            details={"root": canonical_root},
                        )
                    ]
                ),
                latest_repository_snapshot=repo_snapshot,
                latest_scan_reference=latest_scan_reference,
                provenance_reference=repository_evidence_reference["evidence_id"],
            )

        if not root_accessible:
            return _payload(
                project,
                captured_at,
                root_exists=True,
                root_accessible=False,
                canonical_valid=True,
                git_state=None,
                status="blocked",
                reason_codes=["project_root_inaccessible"],
                explanations=["The configured project root is not readable or traversable."],
                blocking_conditions=["Project root is inaccessible."],
                attention_conditions=[],
                unknown_fields=["repository_state", "working_tree_state", "snapshot_freshness"],
                evidence_references=_compact_references(
                    [
                        _build_reference(
                            "project_config",
                            project.project_id,
                            "Canonical project registry record",
                            details={"root": canonical_root},
                        )
                    ]
                ),
                latest_repository_snapshot=repo_snapshot,
                latest_scan_reference=latest_scan_reference,
                provenance_reference=repository_evidence_reference["evidence_id"],
            )

        git_state = None
        git_error = None
        if project.repository_type.lower() == "git":
            try:
                git_state = self.git.inspect(project.root)
            except (GitInspectionError, FileNotFoundError, OSError) as exc:
                git_error = str(exc)
        else:
            git_error = f"Repository type '{project.repository_type}' does not require Git inspection."

        if project.repository_type.lower() == "git" and git_state is None:
            return _payload(
                project,
                captured_at,
                root_exists=True,
                root_accessible=True,
                canonical_valid=True,
                git_state=None,
                status="blocked",
                reason_codes=["git_inspection_failed"],
                explanations=[git_error or "Git inspection failed."],
                blocking_conditions=["Git repository inspection could not be completed safely."],
                attention_conditions=[],
                unknown_fields=["branch_state", "ahead_behind_state", "working_tree_state"],
                evidence_references=_compact_references(
                    [
                        _build_reference(
                            "project_config",
                            project.project_id,
                            "Canonical project registry record",
                            details={"repository_type": project.repository_type},
                        )
                    ]
                ),
                latest_repository_snapshot=repo_snapshot,
                latest_scan_reference=latest_scan_reference,
                provenance_reference=repository_evidence_reference["evidence_id"],
            )

        latest_scan = repo_snapshot
        freshness_state, freshness_details = _freshness_state(project, captured_at, latest_scan)

        status: ProjectHealthStatus = "healthy"
        reason_codes: list[str] = ["project_root_available", "canonical_path_valid", "repository_inspected"]
        explanations: list[str] = [
            "The configured project root exists and passed canonical path validation.",
            "Read-only inspection of the repository state succeeded.",
        ]
        blocking_conditions: list[str] = []
        attention_conditions: list[str] = []
        unknown_fields: list[str] = []

        git_payload: dict[str, Any] = {}
        if git_state is not None:
            git_payload = {
                "repository_root": git_state.repository_root,
                "branch": git_state.branch,
                "detached_head": git_state.detached_head,
                "commit_sha": git_state.commit_sha,
                "upstream_name": git_state.upstream_name,
                "ahead": git_state.ahead,
                "behind": git_state.behind,
                "is_clean": git_state.is_clean,
                "tracked_modifications_count": git_state.tracked_modifications_count,
                "untracked_item_count": git_state.untracked_item_count,
                "tracked_file_count": git_state.tracked_file_count,
            }
            if not git_state.is_clean:
                status = "attention"
                reason_codes.append("working_tree_dirty")
                attention_conditions.append("Working tree contains tracked or untracked changes.")
            if git_state.detached_head:
                status = "attention" if status == "healthy" else status
                reason_codes.append("detached_head")
                attention_conditions.append("Repository is in a detached HEAD state.")
            if git_state.ahead is not None or git_state.behind is not None:
                if (git_state.ahead or 0) > 0 or (git_state.behind or 0) > 0:
                    status = "attention" if status == "healthy" else status
                    reason_codes.append("branch_divergence")
                    attention_conditions.append("Configured branch diverges from its upstream.")

        required_paths = list(project.health_rules.get("required_paths") or project.important_paths)
        path_presence = {
            path: (project.root / path).exists()
            for path in required_paths
            if _safe_relative_path(path)
        }
        missing_paths = [path for path, exists in path_presence.items() if not exists]
        if missing_paths:
            status = "attention" if status == "healthy" else status
            reason_codes.append("important_paths_missing")
            attention_conditions.append("One or more required project paths are missing.")

        if freshness_state == "stale":
            status = "attention" if status == "healthy" else status
            reason_codes.append("evidence_stale")
            attention_conditions.append("Existing repository evidence is stale.")
        if freshness_state == "unknown":
            unknown_fields.append("evidence_freshness")

        release_rules = dict(project.release_rules)
        if git_state is not None and git_state.upstream_name is None:
            reason_codes.append("no_upstream")
            if release_rules.get("assume_unknown_when_no_upstream", True):
                if status == "healthy":
                    status = "unknown"
                unknown_fields.append("upstream_state")
                explanations.append("No upstream branch is configured, so branch divergence cannot be assessed.")
            else:
                status = "attention" if status == "healthy" else status
                attention_conditions.append("No upstream branch is configured.")
        if release_rules.get("require_release_branch") and git_state is not None and git_state.branch is None:
            status = "blocked"
            reason_codes.append("release_branch_required")
            blocking_conditions.append("A release branch is required but not present.")

        if status == "healthy" and not git_payload:
            status = "unknown"
            reason_codes.append("repository_state_not_evaluated")
            unknown_fields.append("repository_state")

        evidence_references = _compact_references(
            [
                _build_reference(
                    "project_config",
                    project.project_id,
                    "Canonical project registry record",
                    details={"config_fingerprint": project.config_fingerprint()},
                ),
                _build_reference(
                    "repository_snapshot",
                    latest_scan.snapshot_id if latest_scan else None,
                    "Latest repository snapshot",
                    freshness=freshness_state,
                    details={"snapshot_count": len(self.database.list_snapshots(project.project_id)) if latest_scan else 0},
                )
                if latest_scan
                else _build_reference(
                    "repository_snapshot",
                    None,
                    "No repository snapshot is available",
                    freshness="unknown",
                    details={},
                ),
            ]
        )

        payload = _payload(
            project,
            captured_at,
            root_exists=root_exists,
            root_accessible=root_accessible,
            canonical_valid=True,
            git_state=git_state,
            status=status,
            reason_codes=reason_codes,
            explanations=explanations,
            blocking_conditions=blocking_conditions,
            attention_conditions=attention_conditions,
            unknown_fields=unknown_fields,
            evidence_references=evidence_references,
            latest_repository_snapshot=latest_scan,
            latest_scan_reference=latest_scan_reference,
            provenance_reference=repository_evidence_reference["evidence_id"],
            path_presence=path_presence,
            missing_paths=missing_paths,
            freshness_state=freshness_state,
            freshness_details=freshness_details,
            git_error=git_error,
            git_payload=git_payload,
        )
        if status == "healthy" and release_rules.get("assume_unknown_when_no_upstream") and "no_upstream" in reason_codes:
            payload["normalized_status"] = "unknown"
        return payload


def _payload(
    project: ProjectConfig,
    captured_at: datetime,
    *,
    root_exists: bool,
    root_accessible: bool,
    canonical_valid: bool,
    git_state: Any,
    status: ProjectHealthStatus,
    reason_codes: list[str],
    explanations: list[str],
    blocking_conditions: list[str],
    attention_conditions: list[str],
    unknown_fields: list[str],
    evidence_references: list[dict[str, Any]],
    latest_repository_snapshot: RepositorySnapshot | None,
    latest_scan_reference: str | None,
    provenance_reference: str | None,
    path_presence: dict[str, bool] | None = None,
    missing_paths: list[str] | None = None,
    freshness_state: str = "unknown",
    freshness_details: dict[str, Any] | None = None,
    git_error: str | None = None,
    git_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "project": {
            "project_id": project.project_id,
            "name": project.name,
            "root": str(project.root),
            "enabled": project.enabled,
            "repository_type": project.repository_type,
            "inspection_access": project.inspection_access,
            "output_access": project.output_access,
            "sensitivity": project.sensitivity,
            "approved_extensions": sorted(project.approved_extensions),
            "excluded_directories": sorted(project.excluded_directories),
            "excluded_filenames": sorted(project.excluded_filenames),
            "important_paths": list(project.important_paths),
        },
        "repository_availability": {
            "root_exists": root_exists,
            "root_accessible": root_accessible,
            "canonical_path_valid": canonical_valid,
            "git_repository_detected": git_state is not None,
        },
        "git_state": git_payload
        if git_payload is not None
        else {
            "repository_root": str(project.root),
            "branch": None,
            "detached_head": None,
            "commit_sha": None,
            "upstream_name": None,
            "ahead": None,
            "behind": None,
            "is_clean": None,
            "tracked_modifications_count": None,
            "untracked_item_count": None,
            "tracked_file_count": None,
            "error": git_error,
        },
        "configured_evidence": {
            "required_paths": list(project.health_rules.get("required_paths") or project.important_paths),
            "required_paths_present": path_presence or {},
            "missing_important_paths": missing_paths or [],
            "latest_gaia_scan_reference": latest_scan_reference,
            "latest_gaia_repository_snapshot_reference": latest_repository_snapshot.snapshot_id if latest_repository_snapshot else None,
            "evidence_freshness": freshness_details
            or {
                "state": freshness_state,
                "age_hours": None,
                "threshold_hours": project.health_rules.get("evidence_freshness_hours", 24),
            },
        },
        "classification": {
            "normalized_status": status,
            "reason_codes": reason_codes,
            "explanations": explanations,
            "blocking_conditions": blocking_conditions,
            "attention_conditions": attention_conditions,
            "unknown_fields": unknown_fields,
        },
        "provenance": {
            "capture_source": "project_health_service",
            "evidence_references": evidence_references,
            "audit_reference": provenance_reference,
        },
    }
    payload["normalized_status"] = status
    payload["reason_codes"] = reason_codes
    payload["explanations"] = explanations
    payload["blocking_conditions"] = blocking_conditions
    payload["attention_conditions"] = attention_conditions
    payload["unknown_fields"] = unknown_fields
    payload["evidence_references"] = evidence_references
    payload["provenance_reference"] = provenance_reference
    payload["repository_reference"] = latest_repository_snapshot.snapshot_id if latest_repository_snapshot else None
    payload["latest_scan_reference"] = latest_scan_reference
    return payload


def _fingerprint_project_health(snapshot: ProjectHealthSnapshot) -> str:
    canonical = json.dumps(
        {
            "project_id": snapshot.project_id,
            "project_configuration_fingerprint": snapshot.project_configuration_fingerprint,
            "normalized_status": snapshot.normalized_status,
            "reason_codes": snapshot.reason_codes,
            "explanations": snapshot.explanations,
            "blocking_conditions": snapshot.blocking_conditions,
            "attention_conditions": snapshot.attention_conditions,
            "unknown_fields": snapshot.unknown_fields,
            "evidence_references": [item.model_dump(mode="json") for item in snapshot.evidence_references],
            "normalized_payload": snapshot.normalized_payload,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_reference(
    kind: str,
    evidence_id: str | None,
    description: str,
    *,
    freshness: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "evidence_kind": kind,
        "evidence_id": evidence_id,
        "description": description,
        "freshness": freshness,
        "details": details or {},
    }


def _compact_references(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if item["evidence_id"] is not None or item["details"]]


def _evidence_reference(snapshot: RepositorySnapshot | None) -> dict[str, Any]:
    if snapshot is None:
        return {
            "evidence_id": None,
            "description": "No repository snapshot is available",
        }
    return {
        "evidence_id": snapshot.snapshot_id,
        "description": "Latest repository snapshot",
    }


def _freshness_state(
    project: ProjectConfig,
    captured_at: datetime,
    latest_repository_snapshot: RepositorySnapshot | None,
) -> tuple[str, dict[str, Any]]:
    if latest_repository_snapshot is None:
        return "unknown", {
            "state": "unknown",
            "age_hours": None,
            "threshold_hours": project.health_rules.get("evidence_freshness_hours", 24),
        }
    threshold_hours = int(project.health_rules.get("evidence_freshness_hours", 24))
    age = captured_at - latest_repository_snapshot.created_at
    if not isinstance(age, timedelta):
        return "unknown", {
            "state": "unknown",
            "age_hours": None,
            "threshold_hours": threshold_hours,
        }
    age_hours = round(age.total_seconds() / 3600, 3)
    state = "fresh" if age <= timedelta(hours=threshold_hours) else "stale"
    return state, {
        "state": state,
        "age_hours": age_hours,
        "threshold_hours": threshold_hours,
        "snapshot_id": latest_repository_snapshot.snapshot_id,
        "captured_at": latest_repository_snapshot.created_at.isoformat(),
    }


def _safe_relative_path(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts
