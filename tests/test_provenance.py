from __future__ import annotations

from pathlib import Path

from gaia.db import Database
from gaia.provenance import ProvenanceCreateRequest
from gaia.trust import GAIATrustService


def _service(settings, enabled: bool, tmp_path: Path) -> GAIATrustService:
    override = settings.model_copy(
        update={
            "signing_enabled": enabled,
            "signing_key_store": tmp_path / "signing-keys",
        }
    )
    return GAIATrustService(override, Database(override.database_path))


def test_provenance_signing_verification_and_determinism(settings, tmp_path: Path) -> None:
    service = _service(settings, True, tmp_path)
    try:
        key = service.create_signing_key("Primary signing key")
        assert "private_key_path" not in key

        request = ProvenanceCreateRequest(
            subject_kind="receipt",
            subject_id="receipt-123",
            subject_version=1,
            payload={"alpha": 1, "beta": [1, 2, 3]},
        )
        first = service.create_provenance_manifest(request)
        second = service.create_provenance_manifest(request)
        assert first["manifest_id"] == second["manifest_id"]
        assert first["content_hash"] == second["content_hash"]
        assert first["signature_status"] == "cryptographically_signed"

        verification = service.verify_provenance_manifest(first["manifest_id"])
        assert verification["signature_status"] == "cryptographically_signed"
    finally:
        service.database.close()


def test_altered_manifest_wrong_key_and_revocation(settings, tmp_path: Path) -> None:
    service = _service(settings, True, tmp_path)
    try:
        primary = service.create_signing_key("Primary")
        request = ProvenanceCreateRequest(subject_kind="action", subject_id="action-1", payload={"value": "ok"})
        manifest = service.create_provenance_manifest(request)

        service.database.connection.execute(
            "UPDATE provenance_manifests SET content_hash = ? WHERE manifest_id = ?",
            ("deadbeef", manifest["manifest_id"]),
        )
        service.database.connection.commit()
        altered = service.verify_provenance_manifest(manifest["manifest_id"])
        assert altered["signature_status"] == "signature_invalid"

        service.database.connection.execute(
            "UPDATE provenance_manifests SET content_hash = ?, canonical_json = ? WHERE manifest_id = ?",
            (manifest["content_hash"], manifest["canonical_json"], manifest["manifest_id"]),
        )
        service.database.connection.commit()

        secondary = service.create_signing_key("Secondary")
        service.database.connection.execute(
            "UPDATE provenance_manifests SET signing_key_id = ? WHERE manifest_id = ?",
            (secondary["key_id"], manifest["manifest_id"]),
        )
        service.database.connection.commit()
        wrong_key = service.verify_provenance_manifest(manifest["manifest_id"])
        assert wrong_key["signature_status"] == "signature_invalid"

        service.database.connection.execute(
            "UPDATE provenance_manifests SET signing_key_id = ? WHERE manifest_id = ?",
            (primary["key_id"], manifest["manifest_id"]),
        )
        service.database.connection.commit()
        service.revoke_signing_key(primary["key_id"], reason="rotated")
        revoked = service.verify_provenance_manifest(manifest["manifest_id"])
        assert revoked["signature_status"] == "signing_key_revoked"
        assert revoked["key_status"] == "revoked"
    finally:
        service.database.close()


def test_trust_alerts_and_retention_report(settings, tmp_path: Path) -> None:
    service = _service(settings, False, tmp_path)
    try:
        alerts = service.refresh_trust_alerts()
        assert any(alert["alert_type"] == "signing_disabled" for alert in alerts)

        report = service.retention_report()
        assert report["policy_count"] >= 1
        assert report["enabled_policy_count"] >= 1
    finally:
        service.database.close()


def test_versioned_capabilities_expose_provenance(settings, tmp_path: Path) -> None:
    service = _service(settings, False, tmp_path)
    try:
        payload = service.provenance.capability_payload()
        assert payload["capability_version"] == "0.7.0"
        assert "embedded_operations_workspace" in payload["capabilities"]
        assert any(item["capability_id"] == "local_ed25519_signing" for item in payload["capability_catalog"])
    finally:
        service.database.close()
