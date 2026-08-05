from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from gaia.output_workspace import (
    OutputActionCreateRequest,
    OutputWorkspaceService,
    PermissionDeniedError,
    PermissionManifestCreateRequest,
)
from gaia.trust import GAIATrustService


def _workspace(settings, monkeypatch: pytest.MonkeyPatch, cwd: Path) -> OutputWorkspaceService:
    monkeypatch.chdir(cwd)
    return OutputWorkspaceService(settings)


def _manifest(service: OutputWorkspaceService) -> str:
    return service.create_permission_manifest(
        PermissionManifestCreateRequest(
            name="Trust outputs",
            allowed_action_types=["create_output_file", "update_output_file"],
            allowed_target_roots=["workspace/approved_outputs"],
            allowed_file_extensions=[".md", ".txt"],
            maximum_file_size=50_000,
            overwrite_policy="backup_then_replace",
            rollback_requirement=True,
            approval_requirement=True,
            risk_ceiling="medium",
            enabled=True,
        )
    ).manifest_id


def test_receipt_chain_tamper_detection(settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = _workspace(settings, monkeypatch, tmp_path)
    manifest_id = _manifest(service)
    target = tmp_path / "workspace" / "approved_outputs" / "chain.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("original", encoding="utf-8")
    action = service.create_action(
        OutputActionCreateRequest(
            action_type="update_output_file",
            title="Chain",
            project_id="sample",
            manifest_id=manifest_id,
            target_path="workspace/approved_outputs/chain.md",
            content="updated",
        )
    )
    service.request_approval(action.action_id)
    service.approve_action(action.action_id)
    action, receipt = service.execute_action(action.action_id, confirmation_token=action.action_id)

    trust = GAIATrustService(settings, service.database)
    assert trust.verify_receipt(receipt.receipt_id).status == "valid"

    service.database.connection.execute(
        "UPDATE execution_receipts SET resulting_hash = ? WHERE receipt_id = ?",
        ("tampered", receipt.receipt_id),
    )
    service.database.connection.commit()

    verification = trust.verify_receipt(receipt.receipt_id)
    assert verification.status == "hash_mismatch"


def test_review_package_rejects_traversal(settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = _workspace(settings, monkeypatch, tmp_path)
    bad_zip = tmp_path / "bad.gaia-review.zip"
    with zipfile.ZipFile(bad_zip, "w") as archive:
        archive.writestr("../evil.txt", "nope")
    trust = GAIATrustService(settings, service.database)
    result = trust.verify_review_package(bad_zip)
    assert result["status"] == "invalid"


def test_stale_preview_blocks_execution(settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = _workspace(settings, monkeypatch, tmp_path)
    manifest_id = _manifest(service)
    target = tmp_path / "workspace" / "approved_outputs" / "stale.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("before", encoding="utf-8")
    action = service.create_action(
        OutputActionCreateRequest(
            action_type="update_output_file",
            title="Stale",
            project_id="sample",
            manifest_id=manifest_id,
            target_path="workspace/approved_outputs/stale.md",
            content="after",
        )
    )
    service.request_approval(action.action_id)
    service.approve_action(action.action_id)
    target.write_text("changed externally", encoding="utf-8")
    with pytest.raises(PermissionDeniedError):
        service.execute_action(action.action_id, confirmation_token=action.action_id)


def test_retention_defaults_to_preserve(settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = _workspace(settings, monkeypatch, tmp_path)
    trust = GAIATrustService(settings, service.database)
    policies = trust.list_retention_policies()
    assert any(policy.policy_id == "preserve-all" and policy.enabled for policy in policies)
