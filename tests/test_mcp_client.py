from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from gaia.mcp.client import (
    EXPECTED_BASELINE_ID,
    EXPECTED_BUNDLE_FORMAT,
    EXPECTED_BUNDLE_ID,
    McpClientConfig,
    McpClientError,
    McpClientResponse,
    McpClientRuntime,
    McpTransport,
)


def _bundle(tmp_path: Path, **changes: Any) -> Path:
    root = tmp_path / "bundle"
    files: dict[str, dict[str, Any]] = {
        "contracts/identities/gaia.yaml": {"client_id": "gaia-mcp-client", "owner_system_id": "gaia"},
        "contracts/identities/neos.yaml": {"server_id": "neos-engineering-read-server", "owner_system_id": "neos", "transport": "stdio", "bind_scope": "local-only"},
        "contracts/tools/health.yaml": {"id": "neos.health.read", "operation": "health.read", "server_id": "neos-engineering-read-server", "read_only": True, "side_effects": False},
        "contracts/tools/summary.yaml": {"id": "neos.project.summary.read", "operation": "project.read", "server_id": "neos-engineering-read-server", "read_only": True, "side_effects": False},
        "contracts/manifests/neos.yaml": {"id": "neos.engineering.read.manifest", "server_id": "neos-engineering-read-server", "tool_ids": ["neos.health.read", "neos.project.summary.read"]},
        "contracts/policies/allow.yaml": {"id": "allow", "effect": "allow", "subject": {"id": "gaia-mcp-client"}, "server_ids": ["neos-engineering-read-server"], "tool_ids": ["neos.health.read", "neos.project.summary.read"]},
    }
    files["contracts/identities/gaia.yaml"].update(changes.pop("gaia", {}))
    files["contracts/identities/neos.yaml"].update(changes.pop("neos", {}))
    files["contracts/tools/health.yaml"].update(changes.pop("health", {}))
    files["contracts/tools/summary.yaml"].update(changes.pop("summary", {}))
    files["contracts/manifests/neos.yaml"].update(changes.pop("manifest", {}))
    files["contracts/policies/allow.yaml"].update(changes.pop("policy", {}))
    for relative, value in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    registry = {"clients": [{"client_id": "gaia-mcp-client"}]}
    (root / "registry").mkdir()
    (root / "registry/mcp.yaml").write_text(yaml.safe_dump(registry), encoding="utf-8")
    schema = root / "schemas/example.json"
    schema.parent.mkdir()
    schema.write_text("{}", encoding="utf-8")
    contract_paths = list(files)
    payloads = ["registry/mcp.yaml", "schemas/example.json", *contract_paths]
    hashes = {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in payloads}
    (root / "hashes").mkdir()
    (root / "hashes/SHA256SUMS.txt").write_text("".join(f"{digest}  {path}\n" for path, digest in sorted(hashes.items())), encoding="utf-8")
    content_root = hashlib.sha256("".join(f"{path}  {hashes[path]}\n" for path in sorted(hashes)).encode()).hexdigest()
    manifest = {"bundle_id": EXPECTED_BUNDLE_ID, "bundle_format_version": EXPECTED_BUNDLE_FORMAT, "contract_baseline_id": EXPECTED_BASELINE_ID, "registry_path": "registry/mcp.yaml", "schema_paths": ["schemas/example.json"], "contract_paths": contract_paths, "hash_algorithm": "SHA-256", "content_root_hash": content_root, "read_only": True}
    (root / "bundle-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def _runtime(bundle: Path, transport: McpTransport | None = None, **kwargs: Any) -> McpClientRuntime:
    return McpClientRuntime(
        McpClientConfig(bundle, enabled=True, executable="neos", arguments=("--mcp-stdio",), **kwargs),
        transport=transport,
    )


class _FakeTransport:
    def __init__(self, status: str = "success", result: Any = None, error: dict[str, Any] | None = None):
        self.status = status
        self.result = result
        self.error = error
        self.requests: list[Any] = []

    def execute(self, request: Any) -> McpClientResponse:
        self.requests.append(request)
        return McpClientResponse(request.correlation_id, request.operation_id, self.status, self.result, self.error)


def _provider_script(tmp_path: Path, response: str, *, delay: float = 0.0) -> Path:
    script = tmp_path / "provider.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(
        "import os\n"
        "import sys\n"
        "import time\n"
        "sys.stderr.write('diagnostic only\\n')\n"
        f"time.sleep({delay})\n"
        "sys.stdin.readline()\n"
        f"sys.stdout.write({response!r} + '\\n')\n"
        "sys.stdout.flush()\n",
        encoding="utf-8",
    )
    return script


def test_disabled_by_default_and_explicit_enable(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    with pytest.raises(McpClientError, match="MCP_CLIENT_DISABLED"):
        McpClientRuntime(McpClientConfig(bundle, executable="neos")).initialize()
    _runtime(bundle).initialize()


def test_bundle_pins_and_identities_fail_closed(tmp_path: Path) -> None:
    for index, (changes, code) in enumerate([({"bundle_id": "wrong"}, "MCP_BUNDLE_INVALID"), ({"bundle_format_version": "2"}, "MCP_BUNDLE_INVALID"), ({"contract_baseline_id": "wrong"}, "MCP_BASELINE_MISMATCH")]):
        bundle = _bundle(tmp_path / f"manifest-{index}")
        manifest_path = bundle / "bundle-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest.update(changes)
        manifest_path.write_text(json.dumps(manifest))
        with pytest.raises(McpClientError, match=code):
            _runtime(bundle).initialize()
    with pytest.raises(McpClientError, match="MCP_CLIENT_IDENTITY_INVALID"):
        _runtime(_bundle(tmp_path / "gaia", gaia={"client_id": "other"})).initialize()
    with pytest.raises(McpClientError, match="MCP_SERVER_IDENTITY_INVALID"):
        _runtime(_bundle(tmp_path / "neos", neos={"server_id": "other"})).initialize()


def test_operations_are_declared_exposed_and_allowed(tmp_path: Path) -> None:
    runtime = _runtime(_bundle(tmp_path))
    runtime.initialize()
    health = runtime.prepare_request("c1", "neos.health.read")
    summary = runtime.prepare_request("c2", "neos.project.summary.read", {"project_id": "demo"})
    assert health.as_mapping()["correlation_id"] == "c1"
    assert summary.as_mapping()["arguments"] == {"project_id": "demo"}
    with pytest.raises(McpClientError, match="MCP_OPERATION_NOT_ALLOWED"):
        runtime.prepare_request("c3", "neos.unknown.read")
    with pytest.raises(McpClientError, match="MCP_WRITE_OPERATION_REJECTED"):
        runtime.prepare_request("c4", "neos.project.delete")


def test_response_parser_preserves_states_and_rejects_mismatch(tmp_path: Path) -> None:
    runtime = _runtime(_bundle(tmp_path))
    runtime.initialize()
    request = runtime.prepare_request("c1", "neos.health.read")
    response = json.loads('{"correlation_id":"c1","operation_id":"neos.health.read","status":"partial","result":{"x":1},"error":{"code":"E"}}')
    parsed = McpClientResponse.parse(response, request)
    assert parsed and parsed.status == "partial" and parsed.error == {"code": "E"}
    for key, code in (("correlation_id", "MCP_CORRELATION_MISMATCH"), ("operation_id", "MCP_CORRELATION_MISMATCH")):
        bad = response.copy()
        bad[key] = "wrong"
        with pytest.raises(McpClientError, match=code):
            McpClientResponse.parse(bad, request)
    with pytest.raises(McpClientError, match="MCP_RESPONSE_INVALID"):
        McpClientResponse.parse({"status": "success"}, request)


def test_live_health_uses_fake_transport_and_preserves_request_and_health_truth(tmp_path: Path) -> None:
    transport = _FakeTransport(result={"status": "degraded"})
    runtime = _runtime(_bundle(tmp_path), transport=transport)
    runtime.initialize()
    request = runtime.prepare_request("c1", "neos.health.read")
    response = runtime.execute(request)
    assert transport.requests[0].as_mapping() == {
        "correlation_id": "c1",
        "client_id": "gaia-mcp-client",
        "operation_id": "neos.health.read",
        "arguments": {},
    }
    assert response.result == {"status": "degraded"}


@pytest.mark.parametrize("status", ["success", "unknown", "unavailable"])
def test_health_states_are_preserved(tmp_path: Path, status: str) -> None:
    runtime = _runtime(_bundle(tmp_path), transport=_FakeTransport(result={"status": status}))
    runtime.initialize()
    response = runtime.execute(runtime.prepare_request("c1", "neos.health.read"))
    assert response.result == {"status": status}


def test_controlled_neos_error_is_preserved_for_health_and_summary(tmp_path: Path) -> None:
    transport = _FakeTransport(status="error", error={"code": "HEALTH_READ_FAILED"})
    runtime = _runtime(_bundle(tmp_path), transport=transport)
    runtime.initialize()
    response = runtime.execute(runtime.prepare_request("c1", "neos.health.read"))
    assert response.status == "error"
    assert response.error == {"code": "HEALTH_READ_FAILED"}
    summary = runtime.prepare_request("c2", "neos.project.summary.read", {"project_id": "demo"})
    assert runtime.execute(summary).error == {"code": "HEALTH_READ_FAILED"}


def test_project_summary_requires_exact_valid_project_id(tmp_path: Path) -> None:
    runtime = _runtime(_bundle(tmp_path), transport=_FakeTransport(result={"status": "success", "project_id": "demo"}))
    runtime.initialize()
    for arguments in (None, {}, {"project_id": ""}, {"project_id": "../secret"}, {"project_id": "demo", "extra": "x"}, {"project_id": 1}):
        with pytest.raises(McpClientError, match="MCP_OPERATION_NOT_ALLOWED"):
            runtime.prepare_request("c1", "neos.project.summary.read", arguments)
    response = runtime.execute(runtime.prepare_request("c2", "neos.project.summary.read", {"project_id": "demo"}))
    assert response.result == {"status": "success", "project_id": "demo"}


def test_project_summary_requires_declaration_exposure_and_allowlist(tmp_path: Path) -> None:
    for index, changes in enumerate((
        {"summary": {"id": "neos.project.summary.other"}},
        {"manifest": {"tool_ids": ["neos.health.read"]}},
        {"policy": {"tool_ids": ["neos.health.read"]}},
    )):
        runtime = _runtime(_bundle(tmp_path / str(index), **changes), transport=_FakeTransport())
        runtime.initialize()
        with pytest.raises(McpClientError, match="MCP_OPERATION_NOT_ALLOWED"):
            runtime.prepare_request("c1", "neos.project.summary.read", {"project_id": "demo"})


@pytest.mark.parametrize("status", ["partial", "stale", "unknown", "unavailable"])
def test_project_summary_truth_states_are_preserved(tmp_path: Path, status: str) -> None:
    transport = _FakeTransport(status=status, result={"status": status})
    runtime = _runtime(_bundle(tmp_path), transport=transport)
    runtime.initialize()
    response = runtime.execute(runtime.prepare_request("c1", "neos.project.summary.read", {"project_id": "demo"}))
    assert response.status == status
    assert response.result == {"status": status}


def test_unknown_project_is_controlled_and_not_empty_success(tmp_path: Path) -> None:
    transport = _FakeTransport(status="unknown", error={"code": "PROJECT_NOT_FOUND"})
    runtime = _runtime(_bundle(tmp_path), transport=transport)
    runtime.initialize()
    response = runtime.execute(runtime.prepare_request("c1", "neos.project.summary.read", {"project_id": "missing"}))
    assert response.status == "unknown"
    assert response.result is None
    assert response.error == {"code": "PROJECT_NOT_FOUND"}


def test_stdio_transport_sends_one_request_uses_stderr_only_as_diagnostic_and_cleans_up(tmp_path: Path) -> None:
    response = json.dumps({"correlation_id": "c1", "operation_id": "neos.health.read", "status": "success", "result": {"status": "healthy"}})
    script = _provider_script(tmp_path, response)
    config = McpClientConfig(_bundle(tmp_path / "bundle"), enabled=True, executable=sys.executable, arguments=(str(script),))
    runtime = McpClientRuntime(config)
    runtime.initialize()
    result = runtime.execute(runtime.prepare_request("c1", "neos.health.read"))
    assert result.result == {"status": "healthy"}


def test_stdio_failures_are_controlled_and_time_bounded(tmp_path: Path) -> None:
    missing = McpClientConfig(_bundle(tmp_path / "missing"), enabled=True, executable=str(tmp_path / "missing.exe"))
    runtime = McpClientRuntime(missing)
    runtime.initialize()
    with pytest.raises(McpClientError, match="MCP_PROVIDER_START_FAILED"):
        runtime.execute(runtime.prepare_request("c1", "neos.health.read"))

    timeout_script = _provider_script(tmp_path / "timeout", json.dumps({}), delay=1.0)
    timeout = McpClientConfig(
        _bundle(tmp_path / "timeout-bundle"),
        enabled=True,
        executable=sys.executable,
        arguments=(str(timeout_script),),
        request_timeout_seconds=0.05,
        overall_deadline_seconds=0.1,
    )
    timeout_runtime = McpClientRuntime(timeout)
    timeout_runtime.initialize()
    with pytest.raises(McpClientError, match="MCP_REQUEST_TIMEOUT"):
        timeout_runtime.execute(timeout_runtime.prepare_request("c2", "neos.health.read"))


def test_malformed_and_empty_stdio_responses_are_rejected(tmp_path: Path) -> None:
    for index, response in enumerate(("not-json", "")):
        script = _provider_script(tmp_path / f"response-{index}", response)
        config = McpClientConfig(_bundle(tmp_path / f"bundle-{index}"), enabled=True, executable=sys.executable, arguments=(str(script),))
        runtime = McpClientRuntime(config)
        runtime.initialize()
        with pytest.raises(McpClientError, match="MCP_RESPONSE_INVALID"):
            runtime.execute(runtime.prepare_request(f"c{index}", "neos.health.read"))


def test_transport_safety_and_no_retries_are_explicit(tmp_path: Path) -> None:
    with pytest.raises(McpClientError, match="MCP_PROVIDER_NOT_CONFIGURED"):
        McpClientRuntime(McpClientConfig(_bundle(tmp_path / "bad"), enabled=True)).initialize()
    with pytest.raises(McpClientError, match="MCP_PROVIDER_NOT_CONFIGURED"):
        McpClientRuntime(McpClientConfig(_bundle(tmp_path / "retry"), enabled=True, executable="neos", retries=True)).initialize()
    assert McpClientConfig(_bundle(tmp_path / "timeouts"), executable="neos").overall_deadline_seconds == 5.0
