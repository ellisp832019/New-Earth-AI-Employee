from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest

from gaia.models import (
    ProjectRecommendation,
    WorkPackageApprovalState,
    WorkPackageRecord,
    WorkPackageRevisionRecord,
)
from gaia.service import ProjectService
from tests.test_programme_intelligence import (
    _analyse_shared_contract_change,
    _build_settings,
    _seed_release_graph,
    _service_for,
)

FIXED_TIMESTAMP = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


def _stable_id(prefix: str, value: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"gaia:{prefix}:{value}"))


def _seed_work_package(
    service: ProjectService,
    project_id: str,
    *,
    title: str,
    objective: str,
    approval_state: WorkPackageApprovalState = "approved",
) -> WorkPackageRecord:
    work_package_id = _stable_id("programme-package-work-package", f"{project_id}:{title}")
    revision_id = _stable_id("programme-package-work-package-revision", f"{project_id}:{title}")
    health = service.latest_project_health_snapshot(project_id)
    project = service.get_project(project_id)
    recommendation_id = _stable_id("programme-package-recommendation", f"{project_id}:{title}")
    recommendation = ProjectRecommendation(
        recommendation_id=recommendation_id,
        project_id=project_id,
        recommendation_type="review_project_configuration_change",
        recommendation_policy_version="gaia-v0.10-c5",
        lifecycle_state="active",
        priority_tier="P4",
        title=title,
        concise_summary=objective,
        rationale=objective,
        why_it_matters=objective,
        why_it_received_this_score=objective,
        evidence_freshness="fresh",
        evidence_fingerprints=[health.content_fingerprint if health is not None else _stable_id("health-fingerprint", project_id)],
        source_snapshot_ids=[health.snapshot_id if health is not None else _stable_id("health-snapshot", project_id)],
    )
    recommendation.semantic_fingerprint = _stable_id("recommendation-semantic", f"{project_id}:{title}")
    recommendation.content_fingerprint = _stable_id("recommendation-content", f"{project_id}:{title}")
    service.database.insert_project_recommendation(recommendation)
    package = WorkPackageRecord(
        work_package_id=work_package_id,
        project_id=project_id,
        title=title,
        objective=objective,
        approval_state=approval_state,
        gate_state="open",
        staleness_state="fresh",
        source_recommendation_id=recommendation.recommendation_id,
        source_recommendation_semantic_fingerprint=recommendation.semantic_fingerprint,
        source_recommendation_content_fingerprint=recommendation.content_fingerprint,
        source_recommendation_policy_version=recommendation.recommendation_policy_version,
        current_revision_id=revision_id,
        current_revision_number=1,
        created_timestamp=FIXED_TIMESTAMP,
        updated_timestamp=FIXED_TIMESTAMP,
        package_fingerprint=_stable_id("package-fingerprint", project_id),
        semantic_fingerprint=_stable_id("package-semantic", project_id),
        content_fingerprint=_stable_id("package-content", project_id),
        prompt_template_version="gaia-v0.9-b4-prompt-v1",
        prompt_content_fingerprint=_stable_id("prompt-content", project_id),
        generator_version="gaia-v0.9-b4-work-package-builder-v1",
        project_configuration_fingerprint=project.config_fingerprint(),
        source_health_snapshot_ids=[health.snapshot_id if health is not None else _stable_id("health-snapshot", project_id)],
        source_health_snapshot_fingerprints=[health.content_fingerprint if health is not None else _stable_id("health-fingerprint", project_id)],
    )
    revision = WorkPackageRevisionRecord(
        revision_id=revision_id,
        work_package_id=work_package_id,
        project_id=project_id,
        revision_number=1,
        title=title,
        objective=objective,
        approval_state=approval_state,
        gate_state="open",
        staleness_state="fresh",
        created_timestamp=FIXED_TIMESTAMP,
        package_fingerprint=package.package_fingerprint,
        semantic_fingerprint=package.semantic_fingerprint,
        content_fingerprint=package.content_fingerprint,
        prompt_content_fingerprint=package.prompt_content_fingerprint,
    )
    service.database.insert_work_package(package)
    service.database.insert_work_package_revision(revision)
    return package


def _seed_reviewable_work_packages(service: ProjectService, order: list[str]) -> None:
    for project_id in order:
        _seed_work_package(service, project_id, title=f"{project_id} coordination", objective=f"Coordinate {project_id} delivery")


def test_programme_packages_is_deterministic_across_insertion_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _build_settings(tmp_path, alpha_missing_path=False)

    service_a, database_a = _service_for(config, tmp_path, monkeypatch, db_name="packages-a.db")
    try:
        _seed_release_graph(service_a, relationship_order=["alpha", "beta"])
        impact_a = _analyse_shared_contract_change(service_a)
        _seed_reviewable_work_packages(service_a, ["alpha", "beta", "shared"])
        portfolio_a = service_a.programme_packages(change_impact_results=[impact_a])
    finally:
        database_a.close()

    service_b, database_b = _service_for(config, tmp_path, monkeypatch, db_name="packages-b.db")
    try:
        _seed_release_graph(service_b, relationship_order=["beta", "alpha"])
        impact_b = _analyse_shared_contract_change(service_b)
        _seed_reviewable_work_packages(service_b, ["shared", "beta", "alpha"])
        portfolio_b = service_b.programme_packages(change_impact_results=[impact_b])
    finally:
        database_b.close()

    assert portfolio_a.package_fingerprint == portfolio_b.package_fingerprint
    assert [package.programme_package_id for package in portfolio_a.programme_packages] == [
        package.programme_package_id for package in portfolio_b.programme_packages
    ]
    assert len(portfolio_a.programme_packages) == 1
    package = portfolio_a.programme_packages[0]
    assert package.package_state == "approved"
    assert package.projects_involved == ["shared", "alpha", "beta"]
    assert [item.project_id for item in package.project_work_packages] == ["shared", "alpha", "beta"]
    assert len(package.revision_history) == 1
    assert package.revision_history[0].revision_number == 1


def test_programme_packages_revision_history_advances_when_input_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _build_settings(tmp_path, alpha_missing_path=False)
    service, database = _service_for(config, tmp_path, monkeypatch, db_name="packages-revision.db")
    try:
        _seed_release_graph(service, relationship_order=["alpha", "beta"])
        impact = _analyse_shared_contract_change(service)
        _seed_reviewable_work_packages(service, ["alpha", "beta", "shared"])

        first = service.programme_packages(change_impact_results=[impact])
        assert first.programme_packages[0].current_revision_number == 1

        beta_package = service.get_work_package(_stable_id("programme-package-work-package", "beta:beta coordination"))
        assert beta_package is not None
        service.database.update_work_package_state(
            beta_package.work_package_id,
            approval_state="handed_off",
            current_revision_id=_stable_id("programme-package-work-package-revision", "beta:beta coordination:v2"),
            current_revision_number=2,
            updated_timestamp=FIXED_TIMESTAMP,
        )

        second = service.programme_packages(change_impact_results=[impact])
        package = second.programme_packages[0]
        assert package.current_revision_number == 2
        assert len(package.revision_history) == 2
        assert [revision.revision_number for revision in package.revision_history] == [1, 2]
    finally:
        database.close()
