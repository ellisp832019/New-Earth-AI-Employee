# New Earth Dashboard and GAIA Integration Contract

## 1. Product Boundaries

- GAIA Windows Control Centre is the standalone engineering, diagnostics, evidence and audit console for the GAIA AI employee.
- New Earth Dashboard is the organisation-wide command centre for business, project, finance, assets, meetings, research and engineering modules.
- The two products are related, but they are not the same product.

## 2. Repository Boundaries

- The GAIA backend, schema, project registry, retrieval engine and release assets live in `New-Earth-AI-Employee`.
- The New Earth Dashboard must not assume it owns GAIA backend state or GAIA data stores.
- The standalone Windows app must remain functional without the New Earth Dashboard repository.

## 3. Backend Ownership

- The Python/FastAPI GAIA backend remains the source of truth for model providers, retrieval, evidence, project registry, repository snapshots, conversational runs, permissions, security policy and audit events.
- The New Earth Dashboard must call the GAIA local API rather than reimplement backend behaviour.

## 4. API Ownership

- GAIA owns the local API contract and response schemas.
- Dashboard integration must use the published GAIA API and must not bypass it with direct database access.
- Compatibility checks are required before enabling an embedded GAIA module.

## 5. Data Ownership

- GAIA owns the SQLite database, snapshots, documents, runs and audit records created by the backend.
- The New Earth Dashboard must not read GAIA SQLite databases directly.
- The dashboard may consume API results, summaries and derived views only.

## 6. Project-Registry Ownership

- Project definitions, allowlists, excluded directories and access policy remain GAIA-managed.
- The dashboard must not maintain a second project registry.

## 7. Evidence Ownership

- Evidence generation, evidence ranking and snippet selection remain GAIA-managed.
- The dashboard may display evidence returned by GAIA, but must not replace the evidence pipeline.

## 8. Audit Ownership

- Audit events are GAIA-owned records.
- The dashboard may review audit output, but must not invent or overwrite audit history.

## 9. Permission Ownership

- GAIA owns permission evaluation and read-only boundaries.
- The dashboard must not bypass GAIA permissions or infer write access from UI embedding.

## 10. Version-Compatibility Expectations

- The desktop app and dashboard integrations should check GAIA API version compatibility before enabling embedded workflows.
- Unknown or incompatible versions must surface a clear degraded state.

## 11. Authentication Assumptions for Local-Only Operation

- Local-first operation assumes loopback-only access by default.
- No cloud identity is required for the standalone control centre.
- If a future embedded dashboard adds authentication, it must layer on top of GAIA without replacing GAIA ownership.

## 12. Error and Degraded-Mode Handling

- Backend unavailability, incompatible versions, missing models and timeout conditions must degrade safely.
- The UI should present a plain-language summary, safe technical detail and a retry path.
- Raw stack traces should not be exposed to normal users.

## 13. Reusable Flutter Component Strategy

- Shared reusable parts may include typed models, the backend client abstraction, read-only badges, evidence cards, snapshot cards, run summaries, warning banners and the Codex draft viewer.
- Components should only be extracted when they create a stable boundary and do not introduce dependency cycles.

## 14. Standalone-Console Guarantees

- The GAIA Windows Control Centre must remain independently usable.
- It must not depend on the New Earth Dashboard repository or backend.
- It must continue to connect directly to the local GAIA backend.

## 15. New Earth Dashboard Embedding Strategy

- Any future embedded GAIA module should consume the same local API and reuse compatible UI components where practical.
- Embedding must not transfer backend ownership to the dashboard.

## 16. Upgrade and Rollback Behaviour

- GAIA API changes must remain versioned and backward-aware where practical.
- If an embedded dashboard cannot confirm compatibility, it must remain disabled or operate in read-only degraded mode.
- Rollback should restore the previous GAIA client or dashboard package without changing backend ownership.

## 17. Future Approval-Centre Integration

- Approval workflows belong in GAIA, not in the dashboard.
- The dashboard may present approval state, but it must not create approval truth independently.

## 18. Prohibited Duplication

- Do not duplicate retrieval logic.
- Do not duplicate evidence databases.
- Do not duplicate project registries.
- Do not duplicate permission systems.
- Do not duplicate agent-run storage.
- Do not duplicate audit records.
- Do not duplicate provider routing.
- Do not duplicate prompt-injection policy.
- Do not duplicate approval state.
- Do not duplicate model configuration.

## Contract Summary

- The GAIA backend stays in `New-Earth-AI-Employee`.
- The standalone GAIA Windows app stays functional.
- The New Earth Dashboard calls the GAIA local API.
- The New Earth Dashboard does not read GAIA SQLite databases directly.
- The New Earth Dashboard does not implement a second retrieval engine.
- The New Earth Dashboard does not bypass GAIA permissions.
- The New Earth Dashboard does not directly operate MicroGrow through GAIA v0.3.
- UI embedding does not transfer backend ownership.
- API version compatibility must be checked before enabling an embedded GAIA module.
