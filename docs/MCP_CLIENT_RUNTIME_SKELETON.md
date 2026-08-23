# GAIA MCP Client Runtime Skeleton

MCP-02F establishes the GAIA-owned, local-only consumer boundary for the frozen Platform Core MCP contract bundle. Platform Core owns identities, contracts, and policy declarations; NEOS owns the read-only provider; GAIA consumes the declarations. This slice does not change either repository and does not launch NEOS.

## Boundary

GAIA requires an explicit installed `new-earth-mcp-contract-bundle-v1` directory with format `1.0.0` and baseline `NE-MCP-READONLY-V1-DECLARATIVE-2026-08-21`. A Platform Core checkout is not required. The bundle is verified, including its SHA-256 listing, before use.

The canonical GAIA client is `gaia-mcp-client`. The canonical NEOS server is `neos-engineering-read-server`, and the declared transport is local-only stdio. The current allowlist is `neos.health.read` and `neos.project.summary.read`; each must be declared, exposed by NEOS, read-only, and allowed for GAIA by the frozen bundle declarations.

## Runtime Safety

The client is disabled by default and requires explicit enablement. Enablement does not enable execution. MCP-02F only validates and prepares one JSON object per line, preserving `correlation_id`, `operation_id`, and `arguments`; response parsing preserves `status`, `result`, and `error` and rejects correlation or operation mismatches.

Provider configuration is structured as an executable plus argument list. Shell execution, arbitrary shell strings, URLs, network MCP, listeners, retries, write operations, approval workflows, and Command Centre changes are unsupported. Startup, request, and overall deadline policy is approximately 1 second, 3 seconds, and 5 seconds respectively.

The injectable transport seam currently fails closed with `MCP_TRANSPORT_NOT_IMPLEMENTED`. No live NEOS process, health read, or project-summary read is executed in MCP-02F. MCP-02G may add the controlled health-read invocation.
