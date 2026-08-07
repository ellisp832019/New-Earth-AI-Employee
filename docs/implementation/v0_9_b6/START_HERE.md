# GAIA v0.9 B6 API, CLI and Integration-Client Compatibility

B6 turns the B1-B5 Project Officer capabilities into stable, versioned, documented operator and integration surfaces.

## What B6 actually adds

- a `ProjectOfficerService` compatibility layer over the existing planning and work-package services;
- `/integration/v1/project-officer/*` FastAPI routes for portfolio, health, change intelligence, recommendations, work packages, and lifecycle actions;
- Project Officer CLI commands for inspection and lifecycle state changes;
- Dart integration-client support for the new B6 endpoints;
- OpenAPI coverage for the new contract surface;
- compatibility-preserving changes only, with no new execution path.

## What B6 does not add

- no Codex execution;
- no target-repository writes;
- no shell execution;
- no new Dashboard write path;
- no MicroGrow writes;
- no release version bump.

## Read next

1. [API Architecture](API_ARCHITECTURE.md)
2. [Project Officer API Reference](PROJECT_OFFICER_API_REFERENCE.md)
3. [Capability Discovery](CAPABILITY_DISCOVERY.md)
4. [CLI Reference](CLI_REFERENCE.md)
5. [Integration Client Architecture](INTEGRATION_CLIENT_ARCHITECTURE.md)
6. [Contract Versioning and Compatibility](CONTRACT_VERSIONING_AND_COMPATIBILITY.md)
7. [Error Model](ERROR_MODEL.md)
8. [Authority and Execution Boundary](AUTHORITY_AND_EXECUTION_BOUNDARY.md)
9. [Backward Compatibility Evidence](BACKWARD_COMPATIBILITY_EVIDENCE.md)
10. [Validation Evidence](VALIDATION_EVIDENCE.md)
11. [Handoff to B7](HANDOFF_TO_B7.md)
