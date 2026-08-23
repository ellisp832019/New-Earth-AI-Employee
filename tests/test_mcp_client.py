from __future__ import annotations

import hashlib
import json
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
    files["contracts/manifests/neos.yaml"].update(changes.pop("manifest", {}))
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


def _runtime(bundle: Path, **kwargs: Any) -> McpClientRuntime:
    return McpClientRuntime(McpClientConfig(bundle, enabled=True, executable="neos", arguments=("--mcp-stdio",), **kwargs))


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


def test_transport_is_not_executed_and_safety_policy_is_explicit(tmp_path: Path) -> None:
    runtime = _runtime(_bundle(tmp_path))
    runtime.initialize()
    with pytest.raises(McpClientError, match="MCP_TRANSPORT_NOT_IMPLEMENTED"):
        runtime.execute(runtime.prepare_request("c1", "neos.health.read"))
    with pytest.raises(McpClientError, match="MCP_PROVIDER_NOT_CONFIGURED"):
        McpClientRuntime(McpClientConfig(_bundle(tmp_path / "bad"), enabled=True)).initialize()
    with pytest.raises(McpClientError, match="MCP_PROVIDER_NOT_CONFIGURED"):
        McpClientRuntime(McpClientConfig(_bundle(tmp_path / "retry"), enabled=True, executable="neos", retries=True)).initialize()
