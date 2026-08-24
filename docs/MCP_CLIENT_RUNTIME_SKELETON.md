# GAIA MCP Client Runtime

MCP-02F established the GAIA-owned, local-only consumer boundary for the frozen Platform Core MCP contract bundle. MCP-02G adds the first bounded live read: `neos.health.read`. Platform Core owns identities, contracts, and policy declarations; NEOS owns the read-only provider; GAIA consumes the declarations. This slice changes GAIA only.

## Boundary

GAIA requires an explicit installed `new-earth-mcp-contract-bundle-v1` directory with format `1.0.0` and baseline `NE-MCP-READONLY-V1-DECLARATIVE-2026-08-21`. A Platform Core checkout is not required. The bundle is verified, including its SHA-256 listing, before use.

The canonical GAIA client is `gaia-mcp-client`. The canonical NEOS server is `neos-engineering-read-server`, and the declared transport is local-only stdio. The current allowlist is `neos.health.read` and `neos.project.summary.read`; each must be declared, exposed by NEOS, read-only, and allowed for GAIA by the frozen bundle declarations.

## Runtime Safety

The client is disabled by default and requires explicit enablement. Enablement does not enable execution. MCP-02F only validates and prepares one JSON object per line, preserving `correlation_id`, `operation_id`, and `arguments`; response parsing preserves `status`, `result`, and `error` and rejects correlation or operation mismatches.

Provider configuration is structured as an executable plus argument list. Shell execution, arbitrary shell strings, URLs, network MCP, listeners, retries, write operations, approval workflows, and Command Centre changes are unsupported. Startup, request, and overall deadline policy is approximately 1 second, 3 seconds, and 5 seconds respectively.

## Live Health Read

When the client is enabled and the bundle and declarations validate, GAIA launches the trusted configured provider directly with a structured argument vector. The current NEOS entry point is:

`neos mcp-provider --bundle <installed-bundle> --enable`

The provider receives exactly one JSON request line and GAIA reads exactly one JSON response line. The request preserves `correlation_id`, `operation_id`, and `arguments`; the response is validated for matching IDs, recognized status, and controlled result/error structure. Provider stderr is captured separately as bounded diagnostics and is never protocol data.

The one-shot provider process has an approximately 1-second startup boundary, a 3-second request timeout, and a 5-second overall deadline. Retries are disabled. stdin, stdout, and stderr are closed in cleanup, and a still-running provider is terminated and then killed if necessary. Start, timeout, empty-response, malformed-response, and process failures become controlled GAIA client errors.

Both declared read operations are now live-enabled through the same transport. `neos.project.summary.read` requires exactly one `project_id` argument matching the frozen NEOS project identifier shape; it is never interpreted as a path, URL, shell input, SQL fragment, or command. Provider truth such as partial, stale, unknown, unavailable, not-found, and error states is returned without fabrication. No MCP write operation, approval workflow, network transport, URL endpoint, shell command, Command Centre change, Platform Core change, or NEOS change is present.

The next slice is MCP-02I: GAIA MCP runtime policy enforcement.
