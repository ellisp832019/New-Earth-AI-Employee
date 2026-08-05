from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from gaia.output_workspace import (
    OutputActionCreateRequest,
    OutputWorkspaceService,
    PathSafetyError,
    PermissionDeniedError,
    PermissionManifestCreateRequest,
    PermissionManifestDecisionRequest,
)


def _service(settings, monkeypatch: pytest.MonkeyPatch, cwd: Path) -> OutputWorkspaceService:
    monkeypatch.chdir(cwd)
    return OutputWorkspaceService(settings)


def _create_enabled_manifest(service: OutputWorkspaceService) -> str:
    manifest = service.create_permission_manifest(
        PermissionManifestCreateRequest(
            name="Approved outputs",
            description="Allow GAIA-owned workspace writes",
            allowed_action_types=["create_output_file", "update_output_file"],
            allowed_target_roots=["workspace/approved_outputs"],
            allowed_file_extensions=[".md", ".txt"],
            maximum_file_size=50_000,
            overwrite_policy="backup_then_replace",
            backup_requirement=True,
            rollback_requirement=True,
            approval_requirement=True,
            risk_ceiling="medium",
            enabled=True,
        )
    )
    return manifest.manifest_id


def test_default_deny_and_bad_targets(settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = _service(settings, monkeypatch, tmp_path)
    manifest_id = service.create_permission_manifest(
        PermissionManifestCreateRequest(
            name="Disabled",
            allowed_action_types=["create_output_file"],
            allowed_target_roots=["workspace/approved_outputs"],
            allowed_file_extensions=[".md"],
        )
    ).manifest_id
    with pytest.raises(PermissionDeniedError):
        service.create_action(
            OutputActionCreateRequest(
                action_type="create_output_file",
                title="Blocked",
                project_id="sample",
                manifest_id=manifest_id,
                target_path="workspace/approved_outputs/blocked.md",
                content="blocked",
            )
        )

    enabled_manifest = _create_enabled_manifest(service)
    with pytest.raises(PathSafetyError):
        service.create_action(
            OutputActionCreateRequest(
                action_type="create_output_file",
                title="MicroGrow denied",
                project_id="sample",
                manifest_id=enabled_manifest,
                target_path=r"..\..\MicroGrow V1\blocked.md",
                content="blocked",
            )
        )

    with pytest.raises(PathSafetyError):
        service.create_action(
            OutputActionCreateRequest(
                action_type="create_output_file",
                title="Traversal denied",
                project_id="sample",
                manifest_id=enabled_manifest,
                target_path="workspace/approved_outputs/../escape.md",
                content="blocked",
            )
        )

    with pytest.raises(PathSafetyError):
        service.create_action(
            OutputActionCreateRequest(
                action_type="create_output_file",
                title="UNC denied",
                project_id="sample",
                manifest_id=enabled_manifest,
                target_path=r"\\server\share\escape.md",
                content="blocked",
            )
        )


def test_execute_backup_and_rollback(settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = _service(settings, monkeypatch, tmp_path)
    manifest_id = _create_enabled_manifest(service)
    target = tmp_path / "workspace" / "approved_outputs" / "update.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("original content", encoding="utf-8")
    action = service.create_action(
        OutputActionCreateRequest(
            action_type="update_output_file",
            title="Update file",
            project_id="sample",
            manifest_id=manifest_id,
            target_path="workspace/approved_outputs/update.md",
            content="updated content",
        )
    )
    approval = service.request_approval(action.action_id)
    approved = service.approve_action(action.action_id, reviewer="Peter", decision_reason="Approved")
    assert approved.status == "approved_for_manual_use"
    action, receipt = service.execute_action(action.action_id, confirmation_token=action.action_id, operator="Peter")
    assert action.status == "completed"
    assert receipt.rollback_available is True
    assert target.read_text(encoding="utf-8") == "updated content"
    rollback_action, rollback = service.rollback_action(action.action_id, confirmation_token=action.action_id, operator="Peter")
    assert rollback.status == "executed"
    assert rollback_action.status == "rolled_back"
    assert target.read_text(encoding="utf-8") == "original content"
    assert service.get_receipt(receipt.receipt_id).receipt_id == receipt.receipt_id
    assert approval.approval_id == approved.approval_id


def test_manifest_version_change_invalidates_approval(settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = _service(settings, monkeypatch, tmp_path)
    manifest_id = _create_enabled_manifest(service)
    action = service.create_action(
        OutputActionCreateRequest(
            action_type="create_output_file",
            title="Versioned",
            project_id="sample",
            manifest_id=manifest_id,
            target_path="workspace/approved_outputs/versioned.md",
            content="hello",
        )
    )
    service.request_approval(action.action_id)
    service.approve_action(action.action_id, reviewer="Peter", decision_reason="Approved")
    manifest = service.get_permission_manifest(manifest_id)
    service.update_permission_manifest(
        manifest_id,
        PermissionManifestDecisionRequest(version=manifest.manifest_version, reviewer="Peter", review_notes="Updated", enabled=True),
    )
    with pytest.raises(PermissionDeniedError):
        service.execute_action(action.action_id, confirmation_token=action.action_id, operator="Peter")


def test_expired_approval_fails(settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = _service(settings, monkeypatch, tmp_path)
    manifest_id = _create_enabled_manifest(service)
    action = service.create_action(
        OutputActionCreateRequest(
            action_type="create_output_file",
            title="Expired",
            project_id="sample",
            manifest_id=manifest_id,
            target_path="workspace/approved_outputs/expired.md",
            content="expired",
            expiry_timestamp=datetime.now(UTC) - timedelta(days=1),
        )
    )
    service.request_approval(action.action_id)
    with pytest.raises(PermissionDeniedError):
        service.approve_action(action.action_id, reviewer="Peter", decision_reason="Approved")
