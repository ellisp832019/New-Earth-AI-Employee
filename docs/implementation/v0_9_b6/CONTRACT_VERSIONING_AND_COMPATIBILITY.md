# Contract Versioning and Compatibility

B6 is additive.

## Versioning facts

- repository version remains `0.8.0`;
- the older `/integration/v1/compatibility` payload remains available;
- the new Project Officer catalog reports `api_version = 0.9.0`, `contract_version = gaia-v3`, and `capability_version = 0.9.0`.

## Compatibility guarantees

- existing API routes were not removed;
- existing response semantics were preserved for v0.8 consumers;
- the Dashboard module remains on the read-only path and does not need to adopt the new Project Officer routes;
- the Windows B5 workspace remains compatible because B6 only exposes the same planning state through a versioned API and CLI layer.

## OpenAPI

The exported OpenAPI snapshot was regenerated after the B6 routes were merged so the contract matches the live application.
