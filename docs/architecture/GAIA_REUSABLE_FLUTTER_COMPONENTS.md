# GAIA Reusable Flutter Components

## Reusable Now

- Typed API models.
- Backend client abstraction.
- Read-only status chips.
- Evidence cards.
- Snapshot cards.
- Run summaries.
- Warning banners.
- Codex draft viewer.

## Reusable Later

- Project selector widgets.
- Compatibility-state indicators.
- First-run checklist cards.
- Settings form patterns.
- Empty-state panels.

## GAIA-Console-Only

- Backend process management.
- Local backend bootstrap controls.
- First-run recovery flow.
- MicroGrow-specific project emphasis.

## New Earth Dashboard-Specific

- Organization-wide navigation.
- Business/project/finance dashboards.
- Dashboard-owned layout shells.
- Cross-module portfolio views.

## API Dependencies

- The reusable layer should depend on the GAIA local API contract only.
- It must not reach into GAIA database internals.

## State-Management Dependencies

- Current controller/state patterns are specific to the GAIA console.
- Future extraction should preserve the backend client boundary and avoid coupling to UI shell details.

## Migration Path

1. Keep the current standalone GAIA app self-contained.
2. Extract only stable model and client abstractions when another consumer actually needs them.
3. Promote reusable widgets into a shared package only after the embedded dashboard contract is accepted.
4. Keep console-only process management and first-run repair logic in the GAIA app.
