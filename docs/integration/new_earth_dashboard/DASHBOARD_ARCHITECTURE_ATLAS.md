# Dashboard Architecture Atlas

## Entry Points

- `lib/main.dart` boots Flutter, the desktop window wrapper, and `ProviderScope`.
- `lib/app.dart` builds `MaterialApp.router`, the desktop shell, hotkeys, security session tracking, and dock overlays.
- `lib/core/routing/app_router.dart` defines the route tree.
- `lib/core/database/app_database.dart` defines the Drift database and migration path.

## Shell Structure

- `AppShell` provides the desktop/mobile application shell.
- `WorkspaceShell` provides the shared framed inner shell for feature pages.
- `WorkspaceFrame` provides the common card-like content container.
- `ModuleWorkspaceShell` adds module-specific selection and launch controls.

## Main Feature Areas

| Area | Status | Notes |
| --- | --- | --- |
| Dashboard home | Active | Local daily plan, focus, Top 3, and summary cards |
| Assets | Active | Large read-write feature area with labels, inventory, orders, and capture flows |
| Treasury | Active | Local-first financial and ritual views behind local gates |
| Projects / Tasks / Planner | Active | Core planning workflow |
| More screen | Active | Supporting modules and tools directory |
| Users and Devices | Active | Security and access control surfaces |
| Voice | Active | Voice assistant, voice intelligence, startup gate, and audit trails |
| Module Hub | Foundational | Registry, enablement, docking, and module shell controls |
| Company Command Centre | Active | Read-only / read-mostly company workspace |
| Knowledge Library | Active | Local document catalogue and exports |
| Omega Knowledge Engine | Active | Read-only local module |
| Omega Engineering Studio | Active | Engineering workspace with its own route family |
| Launchpad | Active | Campaign / launch planning surface |
| Meeting System | Active | Meeting capture, review, and bundle flows |
| Security Lock | Foundational | Session guard and route policy boundary |
| Generated artifacts | Generated | `app_database.g.dart`, `pubspec.lock`, build outputs |

## Incomplete or Unclear Areas

- The module system is active, but several module features still depend on local file stores and inferred manifests.
- There is no dashboard-local GAIA integration yet.
- Repo-local CI workflows were not found in `.github/workflows`.

## Classification Summary

- Active: Dashboard shell, routing, feature workflows, tests.
- Foundational: routing policy, module hub, security lock, persistence layer.
- Generated: Drift codegen, lockfiles, build artifacts.
- Legacy: old route aliases and compatibility helpers.
- Incomplete: module registry evolution, future integration points.
