# Integration Client Architecture

B6 extends the official Dart integration client with thin wrappers for the new Project Officer contract.

## Package shape

- package: `packages/gaia_integration_client`
- transport: `package:http`
- style: synchronous wrappers around JSON HTTP calls
- compatibility goal: preserve all existing v0.8 client methods

## What changed

- `GaiaCapabilityDescriptor` now parses `authority_level`.
- The low-level error parser preserves structured `detail.message` payloads from the B6 API.
- New B6 methods were added for:
  - Project Officer capabilities
  - portfolio and project health
  - change findings and recent changes
  - recommendations and recommendation portfolio
  - work packages, revisions, approvals, handoffs, outcomes
  - lifecycle transitions

## Design rule

The client does not implement Project Officer business logic. It only serializes requests, deserializes responses, and preserves compatibility with older consumers such as the Dashboard module.
