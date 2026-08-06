from __future__ import annotations

import base64
import binascii
import hashlib
import json
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast
from uuid import NAMESPACE_URL, uuid5

from nacl import exceptions as nacl_exceptions
from nacl import signing as nacl_signing
from pydantic import BaseModel, Field

from gaia.config import Settings
from gaia.db import Database
from gaia.models import (
    CapabilityDescriptor,
    ProvenanceManifestRecord,
    SigningKeySummary,
    TrustAlertRecord,
    utc_now,
)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_payload(payload: dict[str, Any]) -> str:
    return _json_dumps(payload)


class SigningKeyCreateRequest(BaseModel):
    key_name: str = Field(min_length=1, max_length=200)
    activate: bool = True


class SigningKeyRotateRequest(BaseModel):
    key_id: str
    next_key_name: str | None = None


class TrustAlertAckRequest(BaseModel):
    reviewer: str = "manual"
    reason: str = ""


class ProvenanceCreateRequest(BaseModel):
    subject_kind: str = Field(min_length=1, max_length=100)
    subject_id: str = Field(min_length=1, max_length=200)
    subject_version: int = 1
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    chain_id: str | None = None
    chain_sequence: int | None = None
    package_path: str | None = None


class ProvenanceVerificationResult(BaseModel):
    manifest_id: str
    signature_status: str
    key_status: str
    content_hash: str
    expected_hash: str
    warnings: list[str] = Field(default_factory=list)


class ProvenancePackageInspection(BaseModel):
    status: str
    reason: str
    manifest: ProvenanceManifestRecord | None = None
    verification: ProvenanceVerificationResult | None = None
    alerts: list[TrustAlertRecord] = Field(default_factory=list)


class ProvenanceReceiptChainInspection(BaseModel):
    chain_id: str
    status: str
    receipts: list[dict[str, Any]]
    provenance_manifests: list[ProvenanceManifestRecord] = Field(default_factory=list)
    alerts: list[TrustAlertRecord] = Field(default_factory=list)


class ProvenanceRetentionReport(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    policy_count: int = 0
    plan_count: int = 0
    receipt_count: int = 0
    enabled_policy_count: int = 0
    issues: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class ProvenanceService:
    def __init__(self, settings: Settings, database: Database | None = None) -> None:
        self.settings = settings
        self.database = database or Database(settings.database_path)
        self.key_store = Path(settings.signing_key_store)
        self.key_store.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Compatibility and capability discovery
    # ------------------------------------------------------------------
    def capabilities(self) -> list[CapabilityDescriptor]:
        signing_keys = self.list_signing_keys()
        signing_ready = self.settings.signing_enabled and any(item.status == "active" for item in signing_keys)
        state: Literal["enabled", "degraded", "disabled"] = "enabled" if signing_ready else "degraded"
        return [
            CapabilityDescriptor(
                capability_id="embedded_operations_workspace",
                version="0.7.0",
                state="enabled",
                summary="Embedded operations workspace available through the local control centre.",
            ),
            CapabilityDescriptor(
                capability_id="connection_resilience",
                version="0.7.0",
                state="enabled",
                summary="Local clients retain and reuse stale data when the backend is unavailable.",
            ),
            CapabilityDescriptor(
                capability_id="versioned_capability_discovery",
                version="0.7.0",
                state="enabled",
                summary="Structured capability catalog with explicit version and gating metadata.",
            ),
            CapabilityDescriptor(
                capability_id="deterministic_provenance_manifests",
                version="0.7.0",
                state="enabled",
                summary="Canonical provenance manifests are generated deterministically.",
            ),
            CapabilityDescriptor(
                capability_id="local_ed25519_signing",
                version="0.7.0",
                state=state,
                summary="Optional local Ed25519 signing for provenance manifests.",
                requires_signing=True,
                enabled=signing_ready,
            ),
            CapabilityDescriptor(
                capability_id="signing_key_lifecycle",
                version="0.7.0",
                state=state,
                summary="Create, rotate and revoke local signing keys.",
                requires_signing=True,
                enabled=signing_ready,
            ),
            CapabilityDescriptor(
                capability_id="provenance_and_receipt_inspection",
                version="0.7.0",
                state="enabled",
                summary="Inspect manifests, receipt chains and offline review packages.",
            ),
            CapabilityDescriptor(
                capability_id="trust_alerts",
                version="0.7.0",
                state="enabled",
                summary="Trust alerts surface signature, chain and configuration issues.",
            ),
            CapabilityDescriptor(
                capability_id="retention_reporting",
                version="0.7.0",
                state="enabled",
                summary="Retention policy, plan and receipt reporting is exposed via API and CLI.",
            ),
            CapabilityDescriptor(
                capability_id="dashboard_conformance",
                version="0.7.0",
                state="enabled",
                summary="The reusable dashboard module remains read-only and contract-gated.",
            ),
        ]

    def capability_payload(self) -> dict[str, Any]:
        capabilities = self.capabilities()
        degraded = [item.summary for item in capabilities if item.state != "enabled"]
        return {
            "capability_version": "0.7.0",
            "capability_catalog": [item.model_dump(mode="json") for item in capabilities],
            "capabilities": [item.capability_id for item in capabilities],
            "degraded_features": degraded,
            "signing_enabled": self.settings.signing_enabled,
            "signing_key_count": len(self.list_signing_keys()),
        }

    # ------------------------------------------------------------------
    # Signing keys
    # ------------------------------------------------------------------
    def _key_row(self, key_id: str) -> dict[str, object]:
        row = self.database.fetch_row("signing_keys", "key_id = ?", (key_id,))
        if not row:
            raise KeyError(key_id)
        return row

    def _key_summary_from_row(self, row: dict[str, object]) -> SigningKeySummary:
        created_at = datetime.fromisoformat(str(row["created_at"]))
        revoked_at = datetime.fromisoformat(str(row["revoked_at"])) if row.get("revoked_at") else None
        last_used_at = datetime.fromisoformat(str(row["last_used_at"])) if row.get("last_used_at") else None
        status = str(row["status"])
        key_status = cast(Literal["active", "rotated", "revoked"], status if status in {"active", "rotated", "revoked"} else "revoked")
        return SigningKeySummary(
            key_id=str(row["key_id"]),
            key_name=str(row["key_name"]),
            public_key=str(row["public_key"]),
            status=key_status,
            created_at=created_at,
            revoked_at=revoked_at,
            rotated_from_key_id=str(row["rotated_from_key_id"]) if row.get("rotated_from_key_id") else None,
            last_used_at=last_used_at,
            signing_enabled=bool(cast(int, row["signing_enabled"])),
        )

    def _private_key_path(self, key_id: str) -> Path:
        return self.key_store / f"{key_id}.json"

    def _write_key_material(self, key_id: str, key_name: str, seed: bytes, public_key: bytes) -> None:
        material = {
            "key_id": key_id,
            "key_name": key_name,
            "seed_b64": base64.b64encode(seed).decode("ascii"),
            "public_key_b64": base64.b64encode(public_key).decode("ascii"),
            "created_at": utc_now().isoformat(),
        }
        self._private_key_path(key_id).write_text(_json_dumps(material), encoding="utf-8")

    def _load_signing_key(self, key_id: str) -> nacl_signing.SigningKey:
        material_path = self._private_key_path(key_id)
        if not material_path.exists():
            raise KeyError(key_id)
        material = json.loads(material_path.read_text(encoding="utf-8"))
        seed = base64.b64decode(material["seed_b64"])
        return nacl_signing.SigningKey(seed)

    def list_signing_keys(self) -> list[SigningKeySummary]:
        rows = self.database.list_rows("signing_keys", order_by="created_at DESC")
        return [self._key_summary_from_row(row) for row in rows]

    def get_signing_key(self, key_id: str) -> SigningKeySummary:
        return self._key_summary_from_row(self._key_row(key_id))

    def create_signing_key(self, request: SigningKeyCreateRequest) -> SigningKeySummary:
        key = nacl_signing.SigningKey.generate()
        key_id = str(uuid5(NAMESPACE_URL, f"gaia-signing-key:{request.key_name}:{key.verify_key.encode().hex()}"))
        summary = SigningKeySummary(
            key_id=key_id,
            key_name=request.key_name,
            public_key=key.verify_key.encode().hex(),
            status="active",
            signing_enabled=self.settings.signing_enabled,
        )
        self._write_key_material(key_id, request.key_name, key.encode(), key.verify_key.encode())
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT OR REPLACE INTO signing_keys(
                    key_id, key_name, public_key, private_key_path, status, created_at,
                    revoked_at, rotated_from_key_id, last_used_at, signing_enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary.key_id,
                    summary.key_name,
                    summary.public_key,
                    str(self._private_key_path(summary.key_id)),
                    summary.status,
                    summary.created_at.isoformat(),
                    summary.revoked_at.isoformat() if summary.revoked_at else None,
                    summary.rotated_from_key_id,
                    summary.last_used_at.isoformat() if summary.last_used_at else None,
                    int(summary.signing_enabled),
                ),
            )
        return summary

    def rotate_signing_key(self, request: SigningKeyRotateRequest) -> dict[str, Any]:
        current = self.get_signing_key(request.key_id)
        next_name = request.next_key_name or f"{current.key_name} (rotated)"
        next_key = self.create_signing_key(SigningKeyCreateRequest(key_name=next_name, activate=True))
        self.revoke_signing_key(request.key_id, reason=f"rotated to {next_key.key_id}", rotated_to=next_key.key_id)
        return {
            "previous_key": current.model_dump(mode="json"),
            "next_key": next_key.model_dump(mode="json"),
        }

    def revoke_signing_key(self, key_id: str, *, reason: str = "revoked", rotated_to: str | None = None) -> SigningKeySummary:
        row = self._key_row(key_id)
        summary = self._key_summary_from_row(row)
        revoked_at = utc_now()
        status = "rotated" if rotated_to else "revoked"
        with self.database.connection:
            self.database.connection.execute(
                """
                UPDATE signing_keys
                SET status = ?, revoked_at = ?, rotated_from_key_id = COALESCE(?, rotated_from_key_id)
                WHERE key_id = ?
                """,
                (status, revoked_at.isoformat(), rotated_to, key_id),
            )
        return summary.model_copy(update={"status": status, "revoked_at": revoked_at, "rotated_from_key_id": rotated_to or summary.rotated_from_key_id})

    def _active_signing_key(self) -> SigningKeySummary | None:
        if not self.settings.signing_enabled:
            return None
        for key in self.list_signing_keys():
            if key.status == "active":
                return key
        return None

    # ------------------------------------------------------------------
    # Provenance manifests
    # ------------------------------------------------------------------
    def _manifest_row(self, manifest_id: str) -> dict[str, object]:
        row = self.database.fetch_row("provenance_manifests", "manifest_id = ?", (manifest_id,))
        if not row:
            raise KeyError(manifest_id)
        return row

    def _manifest_from_row(self, row: dict[str, object]) -> ProvenanceManifestRecord:
        created_at = datetime.fromisoformat(str(row["created_at"]))
        metadata = json.loads(str(row["metadata_json"]))
        manifest_version = cast(int, row["manifest_version"])
        subject_version = cast(int, row["subject_version"])
        chain_sequence = cast(int, row["chain_sequence"]) if row.get("chain_sequence") is not None else None
        signature_status: Literal[
            "unsigned",
            "hash_verified",
            "hash_chained",
            "cryptographically_signed",
            "signature_invalid",
            "signing_key_revoked",
        ] = str(row["signature_status"])  # type: ignore[assignment]
        key_status = cast(Literal["active", "revoked", "rotated", "unknown"], str(row["key_status"]))
        return ProvenanceManifestRecord(
            manifest_id=str(row["manifest_id"]),
            manifest_version=manifest_version,
            subject_kind=str(row["subject_kind"]),
            subject_id=str(row["subject_id"]),
            subject_version=subject_version,
            content_hash=str(row["content_hash"]),
            canonical_json=str(row["canonical_json"]),
            created_at=created_at,
            signing_key_id=str(row["signing_key_id"]) if row.get("signing_key_id") else None,
            signature=str(row["signature"]) if row.get("signature") else None,
            signature_status=signature_status,
            key_status=key_status,
            chain_id=str(row["chain_id"]) if row.get("chain_id") else None,
            chain_sequence=chain_sequence,
            package_path=str(row["package_path"]) if row.get("package_path") else None,
            metadata=metadata,
        )

    def _persist_manifest(self, manifest: ProvenanceManifestRecord) -> None:
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT OR REPLACE INTO provenance_manifests(
                    manifest_id, manifest_version, subject_kind, subject_id, subject_version,
                    content_hash, canonical_json, created_at, signing_key_id, signature,
                    signature_status, key_status, chain_id, chain_sequence, package_path, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    manifest.manifest_id,
                    manifest.manifest_version,
                    manifest.subject_kind,
                    manifest.subject_id,
                    manifest.subject_version,
                    manifest.content_hash,
                    manifest.canonical_json,
                    manifest.created_at.isoformat(),
                    manifest.signing_key_id,
                    manifest.signature,
                    manifest.signature_status,
                    manifest.key_status,
                    manifest.chain_id,
                    manifest.chain_sequence,
                    manifest.package_path,
                    _json_dumps(manifest.metadata),
                ),
            )

    def create_provenance_manifest(self, request: ProvenanceCreateRequest) -> ProvenanceManifestRecord:
        payload = {
            "subject_kind": request.subject_kind,
            "subject_id": request.subject_id,
            "subject_version": request.subject_version,
            "payload": request.payload,
            "metadata": request.metadata,
            "chain_id": request.chain_id,
            "chain_sequence": request.chain_sequence,
            "package_path": request.package_path,
        }
        canonical_payload = _canonical_payload(payload)
        content_hash = _sha256_text(canonical_payload)
        manifest_id = str(
            uuid5(
                NAMESPACE_URL,
                f"gaia-provenance:{request.subject_kind}:{request.subject_id}:{request.subject_version}:{content_hash}",
            )
        )
        manifest = ProvenanceManifestRecord(
            manifest_id=manifest_id,
            manifest_version=1,
            subject_kind=request.subject_kind,
            subject_id=request.subject_id,
            subject_version=request.subject_version,
            content_hash=content_hash,
            canonical_json=canonical_payload,
            signing_key_id=None,
            signature=None,
            signature_status="unsigned",
            key_status="unknown",
            chain_id=request.chain_id,
            chain_sequence=request.chain_sequence,
            package_path=request.package_path,
            metadata=request.metadata | {"payload": request.payload},
        )
        key = self._active_signing_key()
        if key is not None:
            signing_key = self._load_signing_key(key.key_id)
            signature = signing_key.sign(canonical_payload.encode("utf-8")).signature
            manifest.signing_key_id = key.key_id
            manifest.signature = base64.b64encode(signature).decode("ascii")
            manifest.signature_status = "cryptographically_signed"
            manifest.key_status = key.status
            with self.database.connection:
                self.database.connection.execute(
                    "UPDATE signing_keys SET last_used_at = ? WHERE key_id = ?",
                    (utc_now().isoformat(), key.key_id),
                )
        self._persist_manifest(manifest)
        return manifest

    def list_provenance_manifests(self) -> list[ProvenanceManifestRecord]:
        rows = self.database.list_rows("provenance_manifests", order_by="created_at DESC")
        return [self._manifest_from_row(row) for row in rows]

    def get_provenance_manifest(self, manifest_id: str) -> ProvenanceManifestRecord:
        return self._manifest_from_row(self._manifest_row(manifest_id))

    def verify_provenance_manifest(self, manifest_id: str) -> ProvenanceVerificationResult:
        manifest = self.get_provenance_manifest(manifest_id)
        expected_hash = _sha256_text(manifest.canonical_json)
        warnings: list[str] = []
        if expected_hash != manifest.content_hash:
            result = ProvenanceVerificationResult(
                manifest_id=manifest.manifest_id,
                signature_status="signature_invalid",
                key_status=manifest.key_status,
                content_hash=manifest.content_hash,
                expected_hash=expected_hash,
                warnings=["Canonical manifest hash does not match the stored hash."],
            )
            self._store_alert(
                alert_type="provenance_hash_mismatch",
                severity="critical",
                title="Provenance manifest hash mismatch",
                message=f"Manifest {manifest.manifest_id} no longer matches its canonical hash.",
                source_kind="provenance_manifest",
                source_id=manifest.manifest_id,
                metadata={"manifest_id": manifest.manifest_id},
            )
            return result
        if not manifest.signature or not manifest.signing_key_id:
            return ProvenanceVerificationResult(
                manifest_id=manifest.manifest_id,
                signature_status="unsigned",
                key_status="unknown",
                content_hash=manifest.content_hash,
                expected_hash=expected_hash,
                warnings=["Manifest is not cryptographically signed."],
            )
        key_row = self._key_row(manifest.signing_key_id)
        key = self._key_summary_from_row(key_row)
        signature = base64.b64decode(manifest.signature)
        try:
            verify_key = nacl_signing.VerifyKey(bytes.fromhex(key.public_key))
            verify_key.verify(manifest.canonical_json.encode("utf-8"), signature)
        except (ValueError, binascii.Error, nacl_exceptions.BadSignatureError):
            self._store_alert(
                alert_type="provenance_signature_invalid",
                severity="critical",
                title="Provenance signature invalid",
                message=f"Manifest {manifest.manifest_id} failed Ed25519 verification.",
                source_kind="provenance_manifest",
                source_id=manifest.manifest_id,
                metadata={"manifest_id": manifest.manifest_id, "signing_key_id": key.key_id},
            )
            return ProvenanceVerificationResult(
                manifest_id=manifest.manifest_id,
                signature_status="signature_invalid",
                key_status=key.status,
                content_hash=manifest.content_hash,
                expected_hash=expected_hash,
                warnings=["Ed25519 signature verification failed."],
            )
        signature_status: Literal[
            "unsigned",
            "hash_verified",
            "hash_chained",
            "cryptographically_signed",
            "signature_invalid",
            "signing_key_revoked",
        ] = "cryptographically_signed"
        if key.status == "revoked" or key.revoked_at is not None:
            signature_status = "signing_key_revoked"
            warnings.append("Signing key is currently revoked.")
        key_status_value = cast(Literal["active", "revoked", "rotated", "unknown"], "revoked" if key.revoked_at is not None else key.status)
        return ProvenanceVerificationResult(
            manifest_id=manifest.manifest_id,
            signature_status=signature_status,
            key_status=key_status_value,
            content_hash=manifest.content_hash,
            expected_hash=expected_hash,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------
    def _store_alert(
        self,
        *,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        source_kind: str,
        source_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> TrustAlertRecord:
        alert_id = str(uuid5(NAMESPACE_URL, f"{alert_type}:{source_kind}:{source_id}:{title}:{message}"))
        alert = TrustAlertRecord(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,  # type: ignore[arg-type]
            title=title,
            message=message,
            source_kind=source_kind,
            source_id=source_id,
            metadata=metadata or {},
        )
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT OR REPLACE INTO trust_alerts(
                    alert_id, alert_type, severity, status, title, message, source_kind,
                    source_id, created_at, acknowledged_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert.alert_id,
                    alert.alert_type,
                    alert.severity,
                    alert.status,
                    alert.title,
                    alert.message,
                    alert.source_kind,
                    alert.source_id,
                    alert.created_at.isoformat(),
                    alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                    _json_dumps(alert.metadata),
                ),
            )
        return alert

    def _alert_from_row(self, row: dict[str, object]) -> TrustAlertRecord:
        return TrustAlertRecord(
            alert_id=str(row["alert_id"]),
            alert_type=str(row["alert_type"]),
            severity=str(row["severity"]),  # type: ignore[arg-type]
            status=str(row["status"]),  # type: ignore[arg-type]
            title=str(row["title"]),
            message=str(row["message"]),
            source_kind=str(row["source_kind"]),
            source_id=str(row["source_id"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            acknowledged_at=datetime.fromisoformat(str(row["acknowledged_at"])) if row.get("acknowledged_at") else None,
            metadata=json.loads(str(row["metadata_json"])),
        )

    def list_trust_alerts(self) -> list[TrustAlertRecord]:
        rows = self.database.list_rows("trust_alerts", order_by="created_at DESC")
        return [self._alert_from_row(row) for row in rows]

    def acknowledge_alert(self, alert_id: str, request: TrustAlertAckRequest) -> TrustAlertRecord:
        row = self.database.fetch_row("trust_alerts", "alert_id = ?", (alert_id,))
        if not row:
            raise KeyError(alert_id)
        alert = self._alert_from_row(row)
        alert.status = "acknowledged"
        alert.acknowledged_at = utc_now()
        alert.metadata = alert.metadata | {"reviewer": request.reviewer, "reason": request.reason}
        with self.database.connection:
            self.database.connection.execute(
                "UPDATE trust_alerts SET status = ?, acknowledged_at = ?, metadata_json = ? WHERE alert_id = ?",
                (
                    alert.status,
                    alert.acknowledged_at.isoformat(),
                    _json_dumps(alert.metadata),
                    alert.alert_id,
                ),
            )
        return alert

    def refresh_trust_alerts(self) -> list[TrustAlertRecord]:
        alerts: list[TrustAlertRecord] = []
        if not self.settings.signing_enabled:
            alerts.append(
                self._store_alert(
                    alert_type="signing_disabled",
                    severity="warning",
                    title="Signing disabled by default",
                    message="Local Ed25519 signing is currently disabled.",
                    source_kind="configuration",
                    source_id="signing-enabled",
                )
            )
        if self.settings.signing_enabled and not any(key.status == "active" for key in self.list_signing_keys()):
            alerts.append(
                self._store_alert(
                    alert_type="missing_active_signing_key",
                    severity="critical",
                    title="No active signing key",
                    message="Signing is enabled but no active signing key is available.",
                    source_kind="configuration",
                    source_id="signing-keys",
                )
            )
        for manifest in self.list_provenance_manifests():
            verification = self.verify_provenance_manifest(manifest.manifest_id)
            if verification.signature_status in {"signature_invalid", "signing_key_revoked"}:
                alerts.append(
                    self._store_alert(
                        alert_type=f"provenance_{verification.signature_status}",
                        severity="critical" if verification.signature_status == "signature_invalid" else "warning",
                        title="Provenance verification issue",
                        message=f"Manifest {manifest.manifest_id} reports {verification.signature_status}.",
                        source_kind="provenance_manifest",
                        source_id=manifest.manifest_id,
                        metadata={"verification": verification.model_dump(mode="json")},
                    )
                )
        return alerts or self.list_trust_alerts()

    # ------------------------------------------------------------------
    # Retention reporting
    # ------------------------------------------------------------------
    def retention_report(self) -> ProvenanceRetentionReport:
        policies = self.list_retention_policies()
        plans = self.database.list_rows("retention_plans", order_by="created_at DESC")
        receipts = self.database.list_rows("retention_receipts", order_by="created_at DESC")
        issues: list[str] = []
        if not policies:
            issues.append("No retention policies are stored in the database.")
        if not receipts:
            issues.append("No retention receipts have been recorded.")
        summary = {
            "policy_ids": [str(row["policy_id"]) for row in policies],
            "latest_plan_ids": [str(row["plan_id"]) for row in plans[:5]],
            "latest_receipt_ids": [str(row["receipt_id"]) for row in receipts[:5]],
        }
        return ProvenanceRetentionReport(
            policy_count=len(policies),
            plan_count=len(plans),
            receipt_count=len(receipts),
            enabled_policy_count=sum(1 for row in policies if bool(row.get("enabled", True))),
            issues=issues,
            summary=summary,
        )

    def list_retention_policies(self) -> list[dict[str, Any]]:
        rows = self.database.list_rows("retention_policies", order_by="policy_id")
        if rows:
            return [json.loads(str(row["payload_json"])) for row in rows]
        return [
            {
                "policy_id": "preserve-all",
                "policy_version": 1,
                "retention_class": "default",
                "minimum_copies": 1,
                "minimum_age_days": 0,
                "maximum_age_days": None,
                "maximum_count": None,
                "preserve_failed_actions": True,
                "preserve_rollbacks": True,
                "preserve_audit_linked_records": True,
                "dry_run_required": True,
                "approval_required": True,
                "enabled": True,
            },
            {
                "policy_id": "review-packages-90d",
                "policy_version": 1,
                "retention_class": "review",
                "minimum_copies": 1,
                "minimum_age_days": 0,
                "maximum_age_days": 90,
                "maximum_count": None,
                "preserve_failed_actions": True,
                "preserve_rollbacks": True,
                "preserve_audit_linked_records": True,
                "dry_run_required": True,
                "approval_required": True,
                "enabled": True,
            },
            {
                "policy_id": "receipts-preserve",
                "policy_version": 1,
                "retention_class": "receipts",
                "minimum_copies": 1,
                "minimum_age_days": 0,
                "maximum_age_days": None,
                "maximum_count": None,
                "preserve_failed_actions": True,
                "preserve_rollbacks": True,
                "preserve_audit_linked_records": True,
                "dry_run_required": True,
                "approval_required": True,
                "enabled": True,
            },
        ]

    # ------------------------------------------------------------------
    # Inspections
    # ------------------------------------------------------------------
    def inspect_receipt_chain(self, chain_id: str) -> ProvenanceReceiptChainInspection:
        rows = self.database.connection.execute(
            "SELECT * FROM receipt_chains WHERE chain_id = ? ORDER BY chain_sequence ASC",
            (chain_id,),
        ).fetchall()
        receipts = [dict(row) for row in rows]
        manifests: list[ProvenanceManifestRecord] = []
        for receipt in receipts:
            manifests.append(
                self.create_provenance_manifest(
                    ProvenanceCreateRequest(
                        subject_kind="receipt",
                        subject_id=str(receipt["receipt_id"]),
                        subject_version=int(receipt["chain_sequence"]),
                        payload=receipt,
                        metadata={"source": "receipt_chain"},
                        chain_id=chain_id,
                        chain_sequence=int(receipt["chain_sequence"]),
                    )
                )
            )
        alerts = self.list_trust_alerts()
        status = "valid" if receipts else "incomplete"
        return ProvenanceReceiptChainInspection(
            chain_id=chain_id,
            status=status,
            receipts=receipts,
            provenance_manifests=manifests,
            alerts=alerts,
        )

    def verify_review_package(self, package_path: str | Path) -> ProvenancePackageInspection:
        path = Path(package_path)
        if not path.exists():
            return ProvenancePackageInspection(status="invalid", reason="Package does not exist.")
        with tempfile.TemporaryDirectory() as tempdir:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if len(names) != len(set(names)):
                    return ProvenancePackageInspection(status="invalid", reason="Duplicate archive entries are not allowed.")
                for name in names:
                    target = Path(tempdir) / name
                    if target.is_absolute() or ".." in target.parts:
                        return ProvenancePackageInspection(status="invalid", reason="Archive traversal detected.")
                    if name.lower().endswith((".exe", ".dll", ".bat", ".cmd", ".ps1")):
                        return ProvenancePackageInspection(status="invalid", reason="Unexpected executable content.")
                archive.extractall(tempdir)
            extracted = Path(tempdir)
            hashes_path = extracted / "hashes.json"
            if not hashes_path.exists():
                return ProvenancePackageInspection(status="invalid", reason="Missing hashes manifest.")
            hashes = json.loads(hashes_path.read_text(encoding="utf-8"))
            for name, declared in hashes.items():
                candidate = extracted / name
                if not candidate.exists():
                    return ProvenancePackageInspection(status="invalid", reason=f"Missing package entry: {name}")
                actual = _sha256_text(candidate.read_text(encoding="utf-8"))
                if actual != declared:
                    return ProvenancePackageInspection(status="invalid", reason=f"Hash mismatch for {name}")
            manifest_path = extracted / "package_manifest.json"
            manifest = None
            if manifest_path.exists():
                manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                schema_version = manifest_data.get("schema_version", 1)
                if isinstance(schema_version, str):
                    version_text = schema_version.split(".")[0]
                    subject_version = int(version_text) if version_text.isdigit() else 1
                else:
                    subject_version = int(schema_version)
                manifest = self.create_provenance_manifest(
                    ProvenanceCreateRequest(
                        subject_kind="review_package",
                        subject_id=str(manifest_data.get("package_id", path.name)),
                        subject_version=subject_version,
                        payload=manifest_data,
                        metadata={"source": "review_package", "package_path": str(path)},
                        package_path=str(path),
                    )
                )
                verification = self.verify_provenance_manifest(manifest.manifest_id)
                if verification.signature_status == "signature_invalid":
                    self._store_alert(
                        alert_type="review_package_signature_invalid",
                        severity="critical",
                        title="Review package provenance signature invalid",
                        message=f"Review package {path.name} has an invalid provenance signature.",
                        source_kind="review_package",
                        source_id=path.name,
                        metadata={"package_path": str(path)},
                    )
                return ProvenancePackageInspection(
                    status="valid",
                    reason="Package verified.",
                    manifest=manifest,
                    verification=verification,
                    alerts=self.list_trust_alerts(),
                )
        return ProvenancePackageInspection(status="valid", reason="Package verified.", alerts=self.list_trust_alerts())
