from __future__ import annotations

import hashlib
import json
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from gaia.config import Settings
from gaia.db import Database
from gaia.models import utc_now
from gaia.output_workspace import OutputActionCreateRequest, OutputWorkspaceService

CompatibilityStatus = Literal[
    "compatible",
    "compatible_with_warnings",
    "client_too_old",
    "backend_too_old",
    "contract_mismatch",
    "unavailable",
    "timeout",
    "malformed_response",
]

ReceiptVerificationStatus = Literal[
    "valid",
    "invalid",
    "incomplete",
    "unsupported_version",
    "missing_predecessor",
    "hash_mismatch",
]


def _json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_record(payload: dict[str, Any]) -> str:
    return _json_dumps(payload)


class ActionTemplate(BaseModel):
    template_id: str
    template_version: int = 1
    title: str
    description: str
    permitted_action_type: str
    required_inputs: list[str] = Field(default_factory=list)
    optional_inputs: list[str] = Field(default_factory=list)
    target_path_pattern: str
    allowed_extension: str
    risk_level: str = "low"
    approval_required: bool = True
    preview_renderer: str = "markdown"
    retention_class: str = "standard"
    enabled: bool = True


class ReceiptChainRecord(BaseModel):
    chain_id: str
    receipt_id: str
    chain_sequence: int
    receipt_content_hash: str
    previous_receipt_hash: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    verification_status: ReceiptVerificationStatus = "valid"


class ReceiptVerificationRecord(BaseModel):
    receipt_id: str
    chain_id: str | None = None
    chain_sequence: int | None = None
    status: ReceiptVerificationStatus
    previous_receipt_hash: str | None = None
    receipt_content_hash: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ReviewPackageRecord(BaseModel):
    package_id: str = Field(default_factory=lambda: str(uuid4()))
    action_id: str
    receipt_id: str | None = None
    chain_id: str | None = None
    package_path: str
    manifest: dict[str, Any]
    hashes: dict[str, str]
    created_at: datetime = Field(default_factory=utc_now)
    verification_status: ReceiptVerificationStatus = "valid"


class RetentionPolicy(BaseModel):
    policy_id: str
    policy_version: int = 1
    retention_class: str
    minimum_copies: int = 1
    minimum_age_days: int = 0
    maximum_age_days: int | None = None
    maximum_count: int | None = None
    preserve_failed_actions: bool = True
    preserve_rollbacks: bool = True
    preserve_audit_linked_records: bool = True
    dry_run_required: bool = True
    approval_required: bool = True
    enabled: bool = True


class RetentionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    policy_id: str
    plan_hash: str
    approved_hash: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    payload: dict[str, Any]
    status: str = "dry_run"


class RetentionReceipt(BaseModel):
    receipt_id: str = Field(default_factory=lambda: str(uuid4()))
    plan_id: str
    created_at: datetime = Field(default_factory=utc_now)
    payload: dict[str, Any]


def builtin_action_templates() -> list[ActionTemplate]:
    return [
        ActionTemplate(
            template_id="export_draft_markdown",
            title="Export Draft Markdown",
            description="Export a draft revision to markdown in a GAIA-owned output path.",
            permitted_action_type="export_draft",
            required_inputs=["draft_id", "target_path"],
            optional_inputs=["revision"],
            target_path_pattern=r"workspace/approved_outputs/**/*.md",
            allowed_extension=".md",
            retention_class="export",
        ),
        ActionTemplate(
            template_id="export_report_markdown",
            title="Export Report Markdown",
            description="Export a foundation report as markdown.",
            permitted_action_type="export_report",
            required_inputs=["project_id", "target_path"],
            target_path_pattern=r"workspace/exports/**/*.md",
            allowed_extension=".md",
            retention_class="report",
        ),
        ActionTemplate(
            template_id="export_daily_brief_markdown",
            title="Export Daily Brief Markdown",
            description="Export the latest daily brief as markdown.",
            permitted_action_type="export_daily_brief",
            required_inputs=["project_id", "target_path"],
            target_path_pattern=r"workspace/exports/**/*.md",
            allowed_extension=".md",
            retention_class="brief",
        ),
        ActionTemplate(
            template_id="export_receipt_json",
            title="Export Receipt JSON",
            description="Export a receipt as JSON for offline review.",
            permitted_action_type="create_generated_document",
            required_inputs=["receipt_id", "target_path"],
            target_path_pattern=r"workspace/exports/**/*.json",
            allowed_extension=".json",
            retention_class="review",
        ),
        ActionTemplate(
            template_id="export_receipt_markdown",
            title="Export Receipt Markdown",
            description="Export a receipt summary as markdown.",
            permitted_action_type="create_generated_document",
            required_inputs=["receipt_id", "target_path"],
            target_path_pattern=r"workspace/exports/**/*.md",
            allowed_extension=".md",
            retention_class="review",
        ),
        ActionTemplate(
            template_id="create_generated_document",
            title="Create Generated Document",
            description="Create a GAIA-owned generated document from a deterministic source.",
            permitted_action_type="create_generated_document",
            required_inputs=["target_path", "content"],
            target_path_pattern=r"workspace/approved_outputs/**/*",
            allowed_extension=".txt",
            retention_class="generated",
        ),
        ActionTemplate(
            template_id="update_generated_document",
            title="Update Generated Document",
            description="Update an existing generated document with a new version.",
            permitted_action_type="update_output_file",
            required_inputs=["target_path", "content"],
            target_path_pattern=r"workspace/approved_outputs/**/*",
            allowed_extension=".txt",
            retention_class="generated",
        ),
        ActionTemplate(
            template_id="create_review_package",
            title="Create Review Package",
            description="Create a deterministic offline review package for an approved action.",
            permitted_action_type="create_generated_document",
            required_inputs=["action_id"],
            target_path_pattern=r"workspace/review_packages/**/*",
            allowed_extension=".zip",
            retention_class="review",
        ),
        ActionTemplate(
            template_id="rollback_generated_document",
            title="Rollback Generated Document",
            description="Rollback a generated document using the dedicated GAIA boundary.",
            permitted_action_type="rollback_output_file",
            required_inputs=["action_id"],
            target_path_pattern=r"workspace/rollback/**/*",
            allowed_extension=".txt",
            retention_class="rollback",
        ),
    ]


def builtin_retention_policies() -> list[RetentionPolicy]:
    return [
        RetentionPolicy(policy_id="preserve-all", retention_class="default"),
        RetentionPolicy(policy_id="review-packages-90d", retention_class="review", maximum_age_days=90),
        RetentionPolicy(policy_id="receipts-preserve", retention_class="receipts"),
    ]


class GAIATrustService:
    def __init__(self, settings: Settings, database: Database | None = None) -> None:
        self.settings = settings
        self.database = database or Database(settings.database_path)
        self.workspace = OutputWorkspaceService(settings, self.database)

    # ------------------------------------------------------------------
    # Compatibility
    # ------------------------------------------------------------------
    def compatibility(self) -> dict[str, Any]:
        backend_version = __import__("gaia").__version__
        warnings: list[str] = []
        status: CompatibilityStatus = "compatible"
        if backend_version.startswith("0.6"):
            warnings.append("Backend and client should stay on matching 0.6.x versions.")
            status = "compatible_with_warnings"
        return {
            "backend_product_version": backend_version,
            "minimum_supported_api_version": "0.6.0",
            "maximum_tested_api_version": "0.6.0",
            "integration_contract_version": "gaia-v2",
            "client_package_version": "0.6.0",
            "backend_version": backend_version,
            "status": status,
            "loopback_only": True,
            "capabilities": [
                "project_summaries",
                "task_proposals",
                "draft_creation",
                "approvals",
                "daily_briefs",
                "action_summaries",
                "receipt_verification",
                "offline_packages",
                "retention_policies",
                "action_templates",
            ],
            "degraded_features": [] if status == "compatible" else warnings,
            "deprecation_warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Action templates
    # ------------------------------------------------------------------
    def list_action_templates(self) -> list[ActionTemplate]:
        rows = self.database.connection.execute("SELECT * FROM action_templates ORDER BY template_id").fetchall()
        if rows:
            return [ActionTemplate.model_validate_json(row["payload_json"]) for row in rows]
        return builtin_action_templates()

    def get_action_template(self, template_id: str) -> ActionTemplate:
        for template in self.list_action_templates():
            if template.template_id == template_id:
                return template
        raise KeyError(template_id)

    def _persist_template(self, template: ActionTemplate) -> None:
        with self.database.connection:
            self.database.connection.execute(
                "INSERT OR REPLACE INTO action_templates(template_id, template_version, payload_json) VALUES (?, ?, ?)",
                (template.template_id, template.template_version, template.model_dump_json()),
            )

    def seed_templates(self) -> None:
        if self.database.connection.execute("SELECT COUNT(*) FROM action_templates").fetchone()[0]:
            return
        for template in builtin_action_templates():
            self._persist_template(template)

    def template_preview(self, template_id: str, request: OutputActionCreateRequest) -> dict[str, Any]:
        template = self.get_action_template(template_id)
        if request.action_type != template.permitted_action_type:
            raise ValueError("Template does not permit the requested action type.")
        action = self.workspace.create_action(request)
        return {
            "template": template.model_dump(mode="json"),
            "action": action.model_dump(mode="json"),
            "preview": action.preview,
            "diff": action.diff,
        }

    def template_propose(self, template_id: str, request: OutputActionCreateRequest) -> dict[str, Any]:
        return self.template_preview(template_id, request)

    # ------------------------------------------------------------------
    # Receipt chains
    # ------------------------------------------------------------------
    def _receipt_row(self, receipt_id: str) -> Any:
        row = self.database.connection.execute(
            "SELECT * FROM execution_receipts WHERE receipt_id = ?",
            (receipt_id,),
        ).fetchone()
        if not row:
            raise KeyError(receipt_id)
        return row

    def _receipt_payload(self, row: Any) -> dict[str, Any]:
        item = dict(row)
        item["warnings"] = json.loads(item.pop("warnings_json"))
        return item

    def _receipt_content_hash(self, payload: dict[str, Any]) -> str:
        return _sha256_text(_canonical_record(payload))

    def _chain_members(self, chain_id: str) -> list[dict[str, Any]]:
        rows = self.database.connection.execute(
            "SELECT * FROM receipt_chains WHERE chain_id = ? ORDER BY chain_sequence ASC",
            (chain_id,),
        ).fetchall()
        if rows:
            return [dict(row) for row in rows]
        rows = self.database.connection.execute(
            "SELECT * FROM execution_receipts WHERE chain_id = ? ORDER BY chain_sequence ASC",
            (chain_id,),
        ).fetchall()
        return [self._receipt_payload(row) for row in rows]

    def list_receipt_chains(self) -> list[dict[str, Any]]:
        rows = self.database.connection.execute(
            "SELECT chain_id, COUNT(*) AS receipt_count, MAX(chain_sequence) AS max_sequence FROM execution_receipts "
            "WHERE chain_id IS NOT NULL GROUP BY chain_id ORDER BY MAX(timestamp) DESC"
        ).fetchall()
        chains: list[dict[str, Any]] = []
        for row in rows:
            chain_id = str(row["chain_id"])
            chains.append(
                {
                    "chain_id": chain_id,
                    "receipt_count": int(row["receipt_count"]),
                    "max_sequence": int(row["max_sequence"] or 0),
                    "latest_receipt": self._chain_members(chain_id)[-1] if self._chain_members(chain_id) else None,
                }
            )
        return chains

    def get_receipt_chain(self, chain_id: str) -> dict[str, Any]:
        members = self._chain_members(chain_id)
        if not members:
            raise KeyError(chain_id)
        return {"chain_id": chain_id, "receipts": members}

    def verify_receipt(self, receipt_id: str) -> ReceiptVerificationRecord:
        row = self._receipt_row(receipt_id)
        payload = self._receipt_payload(row)
        chain_id = payload.get("chain_id")
        chain_sequence = payload.get("chain_sequence")
        receipt_content_hash = payload.get("receipt_content_hash")
        previous_receipt_hash = payload.get("previous_receipt_hash")
        warnings: list[str] = []
        if not chain_id or not chain_sequence or not receipt_content_hash:
            return ReceiptVerificationRecord(
                receipt_id=receipt_id,
                chain_id=chain_id,
                chain_sequence=chain_sequence,
                status="incomplete",
                previous_receipt_hash=previous_receipt_hash,
                receipt_content_hash=receipt_content_hash,
                warnings=["Receipt is missing chain metadata."],
            )
        canonical = dict(payload)
        canonical.pop("receipt_content_hash", None)
        canonical.pop("verification_status", None)
        expected = self._receipt_content_hash(canonical)
        if expected != receipt_content_hash:
            return ReceiptVerificationRecord(
                receipt_id=receipt_id,
                chain_id=chain_id,
                chain_sequence=int(chain_sequence),
                status="hash_mismatch",
                previous_receipt_hash=previous_receipt_hash,
                receipt_content_hash=receipt_content_hash,
                warnings=["Receipt content hash does not match the canonical payload."],
            )
        if int(chain_sequence) > 1:
            predecessor = self.database.connection.execute(
                "SELECT receipt_content_hash FROM execution_receipts WHERE chain_id = ? AND chain_sequence = ?",
                (chain_id, int(chain_sequence) - 1),
            ).fetchone()
            if not predecessor:
                return ReceiptVerificationRecord(
                    receipt_id=receipt_id,
                    chain_id=chain_id,
                    chain_sequence=int(chain_sequence),
                    status="missing_predecessor",
                    previous_receipt_hash=previous_receipt_hash,
                    receipt_content_hash=receipt_content_hash,
                    warnings=["Previous chain member is missing."],
                )
            if str(predecessor["receipt_content_hash"]) != str(previous_receipt_hash):
                return ReceiptVerificationRecord(
                    receipt_id=receipt_id,
                    chain_id=chain_id,
                    chain_sequence=int(chain_sequence),
                    status="hash_mismatch",
                    previous_receipt_hash=previous_receipt_hash,
                    receipt_content_hash=receipt_content_hash,
                    warnings=["Previous receipt hash does not match the predecessor record."],
                )
        return ReceiptVerificationRecord(
            receipt_id=receipt_id,
            chain_id=chain_id,
            chain_sequence=int(chain_sequence),
            status="valid",
            previous_receipt_hash=previous_receipt_hash,
            receipt_content_hash=receipt_content_hash,
            warnings=warnings,
        )

    def verify_chain(self, chain_id: str) -> dict[str, Any]:
        receipts = self._chain_members(chain_id)
        if not receipts:
            return {"chain_id": chain_id, "status": "incomplete", "receipts": []}
        verifications = [self.verify_receipt(str(receipt["receipt_id"])) for receipt in receipts]
        status = "valid" if all(item.status == "valid" for item in verifications) else "incomplete"
        if any(item.status == "hash_mismatch" for item in verifications):
            status = "hash_mismatch"
        elif any(item.status == "missing_predecessor" for item in verifications):
            status = "missing_predecessor"
        return {
            "chain_id": chain_id,
            "status": status,
            "receipts": [item.model_dump(mode="json") for item in verifications],
        }

    def record_receipt_chain(self, receipt: Any) -> ReceiptChainRecord:
        chain_id = receipt.manifest_id
        prev = self.database.connection.execute(
            "SELECT chain_sequence, receipt_content_hash FROM receipt_chains WHERE chain_id = ? ORDER BY chain_sequence DESC LIMIT 1",
            (chain_id,),
        ).fetchone()
        chain_sequence = int(prev["chain_sequence"]) + 1 if prev else 1
        payload = {
            "receipt_id": receipt.receipt_id,
            "action_id": receipt.action_id,
            "approval_id": receipt.approval_id,
            "manifest_id": receipt.manifest_id,
            "manifest_version": receipt.manifest_version,
            "source_draft_id": receipt.source_draft_id,
            "source_draft_revision": receipt.source_draft_revision,
            "target_path": receipt.target_path,
            "previous_hash": receipt.previous_hash,
            "resulting_hash": receipt.resulting_hash,
            "backup_path": receipt.backup_path,
            "timestamp": receipt.timestamp.isoformat(),
            "operator": receipt.operator,
            "result": receipt.result,
            "warnings": receipt.warnings,
            "rollback_available": int(receipt.rollback_available),
            "chain_id": chain_id,
            "chain_sequence": chain_sequence,
            "previous_receipt_hash": prev["receipt_content_hash"] if prev else None,
        }
        receipt_content_hash = self._receipt_content_hash(payload)
        record = ReceiptChainRecord(
            chain_id=chain_id,
            receipt_id=receipt.receipt_id,
            chain_sequence=chain_sequence,
            receipt_content_hash=receipt_content_hash,
            previous_receipt_hash=payload["previous_receipt_hash"],
            verification_status="valid",
        )
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT OR REPLACE INTO receipt_chains(
                    chain_id, receipt_id, chain_sequence, receipt_content_hash,
                    previous_receipt_hash, created_at, verification_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.chain_id,
                    record.receipt_id,
                    record.chain_sequence,
                    record.receipt_content_hash,
                    record.previous_receipt_hash,
                    record.created_at.isoformat(),
                    record.verification_status,
                ),
            )
            self.database.connection.execute(
                """
                UPDATE execution_receipts
                SET chain_id = ?, chain_sequence = ?, previous_receipt_hash = ?, receipt_content_hash = ?, verification_status = ?
                WHERE receipt_id = ?
                """,
                (
                    record.chain_id,
                    record.chain_sequence,
                    record.previous_receipt_hash,
                    record.receipt_content_hash,
                    record.verification_status,
                    record.receipt_id,
                ),
            )
        return record

    # ------------------------------------------------------------------
    # Review packages
    # ------------------------------------------------------------------
    def create_review_package(self, action_id: str) -> ReviewPackageRecord:
        action = self.workspace.get_action(action_id)
        receipt = self.workspace.list_receipts(limit=1)
        latest_receipt = receipt[0] if receipt else None
        manifest = {
            "package_id": str(uuid4()),
            "schema_version": "0.6.0",
            "action_id": action.action_id,
            "receipt_id": latest_receipt.receipt_id if latest_receipt else None,
            "chain_id": latest_receipt.chain_id if latest_receipt else None,
            "created_at": "1980-01-01T00:00:00Z",
        }
        hashes: dict[str, str] = {}
        entries: dict[str, str] = {
            "package_manifest.json": _json_dumps(manifest),
            "hashes.json": "{}",
            "action.json": action.model_dump_json(),
            "preview.md": action.preview,
            "preview.diff": action.diff,
            "source_metadata.json": _json_dumps({"action_id": action.action_id, "manifest_id": action.manifest_id}),
            "verification_instructions.md": "Verify the declared hashes and receipt chain before trust.",
        }
        if latest_receipt:
            entries["receipt.json"] = _json_dumps(latest_receipt.model_dump(mode="json"))
            chain_id = latest_receipt.chain_id
            chain = self.get_receipt_chain(chain_id) if chain_id else None
            if chain:
                entries["receipt_chain.json"] = _json_dumps(chain)
        for name, content in entries.items():
            hashes[name] = _sha256_text(content)
        entries["hashes.json"] = _json_dumps(hashes)

        review_dir = Path("workspace/review_packages")
        review_dir.mkdir(parents=True, exist_ok=True)
        package_path = review_dir / f"{action.action_id}.gaia-review.zip"
        with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(entries):
                info = zipfile.ZipInfo(name)
                info.date_time = (1980, 1, 1, 0, 0, 0)
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, entries[name])

        record = ReviewPackageRecord(
            action_id=action.action_id,
            receipt_id=latest_receipt.receipt_id if latest_receipt else None,
            chain_id=getattr(latest_receipt, "chain_id", None),
            package_path=str(package_path),
            manifest=manifest,
            hashes=hashes,
        )
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT OR REPLACE INTO review_packages(
                    package_id, action_id, receipt_id, chain_id, package_path, manifest_json,
                    hashes_json, created_at, verification_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.package_id,
                    record.action_id,
                    record.receipt_id,
                    record.chain_id,
                    record.package_path,
                    _json_dumps(record.manifest),
                    _json_dumps(record.hashes),
                    record.created_at.isoformat(),
                    record.verification_status,
                ),
            )
        return record

    def verify_review_package(self, package_path: str | Path) -> dict[str, Any]:
        path = Path(package_path)
        if not path.exists():
            return {"status": "invalid", "reason": "Package does not exist."}
        with tempfile.TemporaryDirectory() as tempdir:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if len(names) != len(set(names)):
                    return {"status": "invalid", "reason": "Duplicate archive entries are not allowed."}
                for name in names:
                    target = Path(tempdir) / name
                    if target.is_absolute() or ".." in target.parts:
                        return {"status": "invalid", "reason": "Archive traversal detected."}
                    if name.lower().endswith((".exe", ".dll", ".bat", ".cmd", ".ps1")):
                        return {"status": "invalid", "reason": "Unexpected executable content."}
                archive.extractall(tempdir)
            extracted = Path(tempdir)
            hashes_path = extracted / "hashes.json"
            if not hashes_path.exists():
                return {"status": "invalid", "reason": "Missing hashes manifest."}
            hashes = json.loads(hashes_path.read_text(encoding="utf-8"))
            for name, declared in hashes.items():
                candidate = extracted / name
                if not candidate.exists():
                    return {"status": "invalid", "reason": f"Missing package entry: {name}"}
                actual = _sha256_text(candidate.read_text(encoding="utf-8"))
                if actual != declared:
                    return {"status": "invalid", "reason": f"Hash mismatch for {name}"}
        return {"status": "valid", "reason": "Package verified."}

    # ------------------------------------------------------------------
    # Retention
    # ------------------------------------------------------------------
    def list_retention_policies(self) -> list[RetentionPolicy]:
        rows = self.database.connection.execute("SELECT * FROM retention_policies ORDER BY policy_id").fetchall()
        if rows:
            return [RetentionPolicy.model_validate_json(row["payload_json"]) for row in rows]
        return builtin_retention_policies()

    def seed_retention_policies(self) -> None:
        if self.database.connection.execute("SELECT COUNT(*) FROM retention_policies").fetchone()[0]:
            return
        with self.database.connection:
            for policy in builtin_retention_policies():
                self.database.connection.execute(
                    "INSERT OR REPLACE INTO retention_policies(policy_id, policy_version, payload_json) VALUES (?, ?, ?)",
                    (policy.policy_id, policy.policy_version, policy.model_dump_json()),
                )

    def retention_status(self) -> dict[str, Any]:
        return {
            "policies": [policy.model_dump(mode="json") for policy in self.list_retention_policies()],
            "plans": self.list_retention_plans(),
            "receipts": self.list_retention_receipts(),
        }

    def list_retention_plans(self) -> list[dict[str, Any]]:
        rows = self.database.connection.execute("SELECT * FROM retention_plans ORDER BY created_at DESC").fetchall()
        plans = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            plans.append(item)
        return plans

    def list_retention_receipts(self) -> list[dict[str, Any]]:
        rows = self.database.connection.execute("SELECT * FROM retention_receipts ORDER BY created_at DESC").fetchall()
        receipts = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            receipts.append(item)
        return receipts

    def plan_retention(self, policy_id: str) -> RetentionPlan:
        policy = next((item for item in self.list_retention_policies() if item.policy_id == policy_id), None)
        if policy is None:
            raise KeyError(policy_id)
        payload = {
            "policy_id": policy.policy_id,
            "policy_version": policy.policy_version,
            "deletions": [],
            "dry_run": True,
        }
        plan_hash = _sha256_text(_json_dumps(payload))
        plan = RetentionPlan(policy_id=policy.policy_id, plan_hash=plan_hash, payload=payload, status="dry_run")
        with self.database.connection:
            self.database.connection.execute(
                """
                INSERT OR REPLACE INTO retention_plans(plan_id, policy_id, plan_hash, approved_hash, created_at, payload_json, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.plan_id,
                    plan.policy_id,
                    plan.plan_hash,
                    plan.approved_hash,
                    plan.created_at.isoformat(),
                    _json_dumps(plan.payload),
                    plan.status,
                ),
            )
        return plan

    def apply_retention(self, plan_id: str, approved_hash: str, confirm: bool = False) -> RetentionReceipt:
        row = self.database.connection.execute("SELECT * FROM retention_plans WHERE plan_id = ?", (plan_id,)).fetchone()
        if not row:
            raise KeyError(plan_id)
        payload = json.loads(str(row["payload_json"]))
        if str(row["plan_hash"]) != approved_hash or not confirm:
            raise PermissionError("Retention plan must be approved and confirmed.")
        receipt = RetentionReceipt(plan_id=plan_id, payload={"applied": False, "plan": payload})
        with self.database.connection:
            self.database.connection.execute(
                "UPDATE retention_plans SET approved_hash = ?, status = ? WHERE plan_id = ?",
                (approved_hash, "approved", plan_id),
            )
            self.database.connection.execute(
                "INSERT OR REPLACE INTO retention_receipts(receipt_id, plan_id, created_at, payload_json) VALUES (?, ?, ?, ?)",
                (receipt.receipt_id, receipt.plan_id, receipt.created_at.isoformat(), _json_dumps(receipt.payload)),
            )
        return receipt
