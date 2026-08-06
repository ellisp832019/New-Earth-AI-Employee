# Dashboard State and Data Flow Map

## Current Ownership Model

| State | Owner | Pattern |
| --- | --- | --- |
| App database | `appDatabaseProvider` | Riverpod provider over Drift database |
| Database readiness | `databaseReadyProvider` | `FutureProvider<void>` |
| Theme mode | `appThemeModeProvider` | Derived from stored settings |
| Security session | `securitySessionProvider` | Riverpod `Notifier` with router bridge |
| Dashboard snapshot | `dashboardSnapshotProvider` | `FutureProvider<DashboardSnapshot>` |
| Module registry | `moduleHubModulesProvider` | Riverpod `Notifier` |
| Dock layout | `dockLayoutStateProvider` | Riverpod `Notifier` |
| Module UI state | `ModuleHubStateRepository` | JSON file under `modules/module_hub_state.json` |
| Command deck recent actions | `commandPaletteRecentActionsProvider` | Local file read from runtime JSONL |
| Voice session / audit logs | Voice-specific providers | Riverpod state plus Drift tables |

## Data Flow Patterns

- Feature controllers watch `databaseReadyProvider` before reading persistent data.
- Repositories own the reads and writes, not the widgets.
- Many screens render from `FutureProvider` snapshots and local repositories.
- Router state is driven by `go_router` plus explicit session redirect logic.
- Desktop shell state is shared through `DesktopPresenceController`.

## GAIA Integration Ownership Recommendation

The GAIA integration client should be owned by a dashboard-scoped adapter or controller, not by the global app shell.

Recommended ownership:

- A dedicated provider creates the `GaiaIntegrationClient`.
- A feature controller owns refresh, cache, stale-data state, and error state.
- The provider or controller disposes the underlying `http.Client` when the surface closes.
- The adapter should keep backend compatibility, capabilities, trust alerts, and retention summaries together so the UI can fail closed.

## GAIA State Buckets

These states should live together in the GAIA surface:

- backend connection
- compatibility
- capability catalog
- cached summaries
- trust alerts
- stale-data state
- refresh state

## Boundary Recommendation

- Do not push GAIA state into the global dashboard database.
- Do not persist GAIA package responses in Dashboard-owned SQLite unless the adapter explicitly needs a cache and the cache contract is documented.
- Keep GAIA refresh logic local to the GAIA route tree.
