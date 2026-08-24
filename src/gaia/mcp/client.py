from __future__ import annotations

import hashlib
import json
import queue
import re
import subprocess
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

EXPECTED_BUNDLE_ID = "new-earth-mcp-contract-bundle-v1"
EXPECTED_BUNDLE_FORMAT = "1.0.0"
EXPECTED_BASELINE_ID = "NE-MCP-READONLY-V1-DECLARATIVE-2026-08-21"
EXPECTED_CLIENT_ID = "gaia-mcp-client"
EXPECTED_SERVER_ID = "neos-engineering-read-server"
EXPECTED_OPERATIONS = frozenset({"neos.health.read", "neos.project.summary.read"})
EXPECTED_PROVIDER_TRANSPORT = "stdio"
EXPECTED_PROVIDER_SCOPE = "local-only"
REQUEST_TIMEOUT_SECONDS = 3.0
OVERALL_DEADLINE_SECONDS = 5.0
STARTUP_TIMEOUT_SECONDS = 1.0
RETRIES_ENABLED = False
_WRITE_LIKE_TOKENS = frozenset(
    {"create", "update", "delete", "write", "mutate", "shell", "commit", "push", "merge", "execute", "actuate"}
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SHELL_TOKENS = re.compile(r"[\r\n;&|<>`]")
_RECOGNIZED_STATUSES = frozenset({"success", "error", "rejected", "unknown", "unavailable", "partial", "not_implemented"})


class McpClientError(RuntimeError):
    """Controlled, user-safe GAIA MCP client failure."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class McpClientConfig:
    bundle_path: Path
    enabled: bool = False
    executable: str | None = None
    arguments: tuple[str, ...] = ()
    startup_timeout_seconds: float = STARTUP_TIMEOUT_SECONDS
    request_timeout_seconds: float = REQUEST_TIMEOUT_SECONDS
    overall_deadline_seconds: float = OVERALL_DEADLINE_SECONDS
    retries: bool = RETRIES_ENABLED

    def validate(self) -> None:
        if not self.executable or not self.executable.strip() or _SHELL_TOKENS.search(self.executable):
            raise McpClientError("MCP_PROVIDER_NOT_CONFIGURED", "Provider executable must be explicit and shell-free")
        if any(not isinstance(item, str) or not item or _SHELL_TOKENS.search(item) for item in self.arguments):
            raise McpClientError("MCP_PROVIDER_NOT_CONFIGURED", "Provider arguments must be structured and shell-free")
        if self.startup_timeout_seconds <= 0 or self.request_timeout_seconds <= 0 or self.overall_deadline_seconds <= 0:
            raise McpClientError("MCP_PROVIDER_NOT_CONFIGURED", "Timeouts must be positive")
        if self.retries:
            raise McpClientError("MCP_PROVIDER_NOT_CONFIGURED", "Automatic retries are disabled")


@dataclass(frozen=True)
class McpClientRequest:
    correlation_id: str
    operation_id: str
    arguments: dict[str, Any]
    client_id: str = EXPECTED_CLIENT_ID

    def as_mapping(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "client_id": self.client_id,
            "operation_id": self.operation_id,
            "arguments": self.arguments,
        }

    def as_stdio_line(self) -> str:
        return json.dumps(self.as_mapping(), sort_keys=True, separators=(",", ":")) + "\n"


@dataclass(frozen=True)
class McpClientResponse:
    correlation_id: str
    operation_id: str
    status: str
    result: Any = None
    error: dict[str, Any] | None = None

    @classmethod
    def parse(cls, value: Mapping[str, Any], request: McpClientRequest) -> McpClientResponse:
        if not isinstance(value, Mapping):
            raise McpClientError("MCP_RESPONSE_INVALID", "Response must be an object")
        correlation_id = value.get("correlation_id")
        operation_id = value.get("operation_id")
        status = value.get("status")
        if not all(isinstance(item, str) and item.strip() for item in (correlation_id, operation_id, status)):
            raise McpClientError("MCP_RESPONSE_INVALID", "Response identity and status are required")
        if not isinstance(correlation_id, str) or not isinstance(operation_id, str) or not isinstance(status, str):
            raise McpClientError("MCP_RESPONSE_INVALID", "Response identity and status are required")
        if correlation_id != request.correlation_id:
            raise McpClientError("MCP_CORRELATION_MISMATCH", "Response correlation does not match request")
        if operation_id != request.operation_id:
            raise McpClientError("MCP_CORRELATION_MISMATCH", "Response operation does not match request")
        if status not in _RECOGNIZED_STATUSES:
            raise McpClientError("MCP_RESPONSE_INVALID", "Response status is not recognized")
        error = value.get("error")
        if error is not None and not isinstance(error, dict):
            raise McpClientError("MCP_RESPONSE_INVALID", "Response error must be an object or null")
        return cls(correlation_id, operation_id, status, value.get("result"), error)

    @classmethod
    def parse_stdio_line(cls, line: str, request: McpClientRequest) -> McpClientResponse:
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise McpClientError("MCP_RESPONSE_INVALID", "Response is not valid JSON") from exc
        if not isinstance(value, Mapping):
            raise McpClientError("MCP_RESPONSE_INVALID", "Response must be an object")
        return cls.parse(value, request)


class McpTransport(Protocol):
    """Injectable transport boundary for deterministic tests and local stdio."""

    def execute(self, request: McpClientRequest) -> McpClientResponse:
        ...


class McpStdioTransport:
    """Run one trusted local provider command and close its process after one response."""

    def __init__(self, config: McpClientConfig):
        self.config = config

    def execute(self, request: McpClientRequest) -> McpClientResponse:
        executable = self.config.executable
        if executable is None:
            raise McpClientError("MCP_PROVIDER_NOT_CONFIGURED", "Provider executable is missing")
        command = [executable, *self.config.arguments]
        started_at = time.monotonic()
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
            )
        except (OSError, ValueError) as exc:
            raise McpClientError("MCP_PROVIDER_START_FAILED", "NEOS MCP provider could not be started") from exc

        output: queue.Queue[str | BaseException] = queue.Queue(maxsize=1)

        def read_response() -> None:
            try:
                if process.stdout is None:
                    output.put(McpClientError("MCP_RESPONSE_INVALID", "Provider stdout is unavailable"))
                    return
                output.put(process.stdout.readline())
            except BaseException as exc:  # noqa: BLE001 - marshal reader failure to caller
                output.put(exc)

        def drain_stderr() -> None:
            if process.stderr is not None:
                process.stderr.read(4096)

        response_thread = threading.Thread(target=read_response, daemon=True)
        stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
        response_thread.start()
        stderr_thread.start()
        try:
            startup_elapsed = time.monotonic() - started_at
            if startup_elapsed > self.config.startup_timeout_seconds or process.poll() is not None:
                raise McpClientError("MCP_PROVIDER_START_FAILED", "NEOS MCP provider exited during startup")
            if process.stdin is None:
                raise McpClientError("MCP_PROVIDER_START_FAILED", "Provider stdin is unavailable")
            try:
                process.stdin.write(request.as_stdio_line())
                process.stdin.flush()
            except (OSError, ValueError) as exc:
                raise McpClientError("MCP_PROVIDER_START_FAILED", "MCP request could not be sent") from exc
            remaining = min(
                self.config.request_timeout_seconds,
                self.config.overall_deadline_seconds - (time.monotonic() - started_at),
            )
            if remaining <= 0:
                raise McpClientError("MCP_REQUEST_TIMEOUT", "MCP overall deadline expired")
            try:
                line = output.get(timeout=remaining)
            except queue.Empty as exc:
                raise McpClientError("MCP_REQUEST_TIMEOUT", "NEOS MCP request timed out") from exc
            if isinstance(line, BaseException):
                if isinstance(line, McpClientError):
                    raise line
                raise McpClientError("MCP_RESPONSE_INVALID", "Provider response could not be read") from line
            if not line:
                raise McpClientError("MCP_RESPONSE_INVALID", "Provider returned an empty response")
            return McpClientResponse.parse_stdio_line(line, request)
        finally:
            if process.stdin is not None:
                process.stdin.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=min(1.0, self.config.overall_deadline_seconds))
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
            response_thread.join(timeout=0.2)
            stderr_thread.join(timeout=0.2)


def _read_object(path: Path, code: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) if path.suffix in {".yaml", ".yml"} else json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise McpClientError(code, f"Invalid contract file: {path.name}") from exc
    if not isinstance(value, dict):
        raise McpClientError(code, f"Contract must be an object: {path.name}")
    return value


def _safe_path(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise McpClientError("MCP_BUNDLE_INVALID", "Bundle contains an unsafe path")
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise McpClientError("MCP_BUNDLE_INVALID", "Bundle path escapes root") from exc
    return path


@dataclass(frozen=True)
class McpContractBundle:
    root: Path
    manifest: dict[str, Any]
    registry: dict[str, Any]
    contracts: tuple[dict[str, Any], ...]

    @classmethod
    def load(cls, bundle_path: Path) -> McpContractBundle:
        root = bundle_path.expanduser().resolve()
        if not root.is_dir():
            raise McpClientError("MCP_BUNDLE_INVALID", "Installed contract bundle is missing")
        manifest = _read_object(root / "bundle-manifest.json", "MCP_BUNDLE_INVALID")
        if manifest.get("bundle_id") != EXPECTED_BUNDLE_ID:
            raise McpClientError("MCP_BUNDLE_INVALID", "Unexpected contract bundle ID")
        if manifest.get("bundle_format_version") != EXPECTED_BUNDLE_FORMAT:
            raise McpClientError("MCP_BUNDLE_INVALID", "Unsupported contract bundle format")
        if manifest.get("contract_baseline_id") != EXPECTED_BASELINE_ID:
            raise McpClientError("MCP_BASELINE_MISMATCH", "Contract baseline does not match frozen baseline")
        if manifest.get("read_only") is not True or manifest.get("hash_algorithm") != "SHA-256":
            raise McpClientError("MCP_BUNDLE_INVALID", "Bundle must declare SHA-256 read-only content")
        registry_path = _safe_path(root, manifest.get("registry_path"))
        if not registry_path.is_file() or not isinstance(manifest.get("contract_paths"), list) or not isinstance(manifest.get("schema_paths"), list):
            raise McpClientError("MCP_BUNDLE_INVALID", "Bundle registry or contracts are missing")
        registry = _read_object(registry_path, "MCP_BUNDLE_INVALID")
        contracts: list[dict[str, Any]] = []
        for relative in manifest["contract_paths"]:
            path = _safe_path(root, relative)
            if not path.is_file():
                raise McpClientError("MCP_BUNDLE_INVALID", f"Missing contract: {relative}")
            contracts.append(_read_object(path, "MCP_BUNDLE_INVALID"))
        loaded = cls(root, manifest, registry, tuple(contracts))
        loaded._verify_hashes()
        loaded._validate_identities()
        return loaded

    def _verify_hashes(self) -> None:
        hashes_path = self.root / "hashes/SHA256SUMS.txt"
        expected_root = self.manifest.get("content_root_hash")
        if not hashes_path.is_file() or not isinstance(expected_root, str) or not _SHA256.fullmatch(expected_root):
            raise McpClientError("MCP_BUNDLE_INVALID", "Bundle hashes are missing")
        entries: dict[str, str] = {}
        try:
            hash_lines = hashes_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise McpClientError("MCP_BUNDLE_INVALID", "Bundle hashes cannot be read") from exc
        for line in hash_lines:
            digest, separator, relative = line.partition("  ")
            if not separator or not _SHA256.fullmatch(digest) or relative in entries:
                raise McpClientError("MCP_BUNDLE_INVALID", "Bundle hash listing is invalid")
            _safe_path(self.root, relative)
            entries[relative] = digest
        expected_paths = {str(self.manifest["registry_path"]), *(str(item) for item in self.manifest["schema_paths"]), *(str(item) for item in self.manifest["contract_paths"])}
        if set(entries) != expected_paths:
            raise McpClientError("MCP_BUNDLE_INVALID", "Bundle hash listing does not match manifest")
        actual_paths = {
            path.relative_to(self.root).as_posix()
            for path in self.root.rglob("*")
            if path.is_file() and path.name not in {"bundle-manifest.json", "SHA256SUMS.txt"}
        }
        if actual_paths != expected_paths:
            raise McpClientError("MCP_BUNDLE_INVALID", "Bundle files do not match manifest")
        for relative, digest in entries.items():
            actual = hashlib.sha256(_safe_path(self.root, relative).read_bytes()).hexdigest()
            if actual != digest:
                raise McpClientError("MCP_BUNDLE_INVALID", f"Bundle hash mismatch: {relative}")
        root_hash = hashlib.sha256("".join(f"{path}  {entries[path]}\n" for path in sorted(entries)).encode()).hexdigest()
        if root_hash != expected_root:
            raise McpClientError("MCP_BUNDLE_INVALID", "Bundle content root hash does not match")

    def _validate_identities(self) -> None:
        client = next((item for item in self.contracts if item.get("client_id") == EXPECTED_CLIENT_ID), None)
        if client is None or client.get("owner_system_id") != "gaia":
            raise McpClientError("MCP_CLIENT_IDENTITY_INVALID", "Canonical GAIA client declaration is missing")
        server = next((item for item in self.contracts if item.get("server_id") == EXPECTED_SERVER_ID), None)
        if server is None or server.get("owner_system_id") != "neos" or server.get("transport") != EXPECTED_PROVIDER_TRANSPORT or server.get("bind_scope") != EXPECTED_PROVIDER_SCOPE:
            raise McpClientError("MCP_SERVER_IDENTITY_INVALID", "Canonical NEOS server declaration is invalid")
        registry_clients = {item.get("client_id") for item in self.registry.get("clients", []) if isinstance(item, dict)}
        if EXPECTED_CLIENT_ID not in registry_clients:
            raise McpClientError("MCP_CLIENT_IDENTITY_INVALID", "GAIA client is not registered")

    def operation_contract(self, operation_id: str) -> dict[str, Any] | None:
        return next((item for item in self.contracts if item.get("id") == operation_id and "operation" in item), None)

    def operation_is_exposed(self, operation_id: str) -> bool:
        return any(operation_id in item.get("tool_ids", []) and item.get("server_id") == EXPECTED_SERVER_ID for item in self.contracts)

    def operation_is_allowed(self, operation_id: str) -> bool:
        return any(
            isinstance(item.get("subject"), dict)
            and item.get("effect") == "allow"
            and item.get("subject", {}).get("id") == EXPECTED_CLIENT_ID
            and EXPECTED_SERVER_ID in item.get("server_ids", [])
            and operation_id in item.get("tool_ids", [])
            for item in self.contracts
        )


class McpClientRuntime:
    """Bundle-backed GAIA client with one-shot health-only live invocation."""

    def __init__(self, config: McpClientConfig, transport: McpTransport | None = None):
        self.config = config
        self.transport = transport or McpStdioTransport(config)
        self.bundle: McpContractBundle | None = None

    def initialize(self) -> None:
        if not self.config.enabled:
            raise McpClientError("MCP_CLIENT_DISABLED", "GAIA MCP client is disabled")
        self.config.validate()
        self.bundle = McpContractBundle.load(self.config.bundle_path)

    def prepare_request(self, correlation_id: str, operation_id: str, arguments: Mapping[str, Any] | None = None) -> McpClientRequest:
        if self.bundle is None:
            raise McpClientError("MCP_CLIENT_DISABLED", "GAIA MCP client is not initialized")
        if not isinstance(correlation_id, str) or not correlation_id.strip() or not isinstance(operation_id, str) or not operation_id.strip():
            raise McpClientError("MCP_OPERATION_NOT_ALLOWED", "Correlation and operation IDs are required")
        contract = self.bundle.operation_contract(operation_id)
        if operation_id not in EXPECTED_OPERATIONS or contract is None:
            if any(token in operation_id.lower().split(".") for token in _WRITE_LIKE_TOKENS):
                raise McpClientError("MCP_WRITE_OPERATION_REJECTED", "Write-like operations are forbidden")
            raise McpClientError("MCP_OPERATION_NOT_ALLOWED", "Operation is not authorized")
        if contract.get("read_only") is not True or contract.get("side_effects") is not False:
            raise McpClientError("MCP_WRITE_OPERATION_REJECTED", "Operation is not read-only")
        if not self.bundle.operation_is_exposed(operation_id):
            raise McpClientError("MCP_OPERATION_NOT_ALLOWED", "Operation is not exposed by NEOS")
        if not self.bundle.operation_is_allowed(operation_id):
            raise McpClientError("MCP_OPERATION_NOT_ALLOWED", "Operation is not allowed for GAIA")
        if arguments is not None and not isinstance(arguments, Mapping):
            raise McpClientError("MCP_OPERATION_NOT_ALLOWED", "Arguments must be an object")
        return McpClientRequest(correlation_id, operation_id, dict(arguments or {}))

    def execute(self, request: McpClientRequest) -> McpClientResponse:
        if self.bundle is None:
            raise McpClientError("MCP_CLIENT_DISABLED", "GAIA MCP client is not initialized")
        if request.operation_id != "neos.health.read":
            raise McpClientError("MCP_OPERATION_NOT_ENABLED", "Only neos.health.read is live-enabled in MCP-02G")
        return self.transport.execute(request)
