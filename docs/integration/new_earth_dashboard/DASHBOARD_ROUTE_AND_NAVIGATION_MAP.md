# Dashboard Route and Navigation Map

## Shell Model

- Desktop uses a left sidebar inside `AppShell`.
- Mobile uses bottom navigation inside `AppShell`.
- The main app uses `StatefulShellRoute.indexedStack`.
- `WorkspaceShell` and `WorkspaceFrame` keep the inner page chrome consistent.

## Primary Branches

| Route family | Role | Notes |
| --- | --- | --- |
| `/dashboard` | Home | Dashboard summary and quick actions |
| `/assets` | Work | Asset and capture workflows |
| `/treasury` | Work | Treasury flows behind local gates |
| `/projects-intelligence` | Work | Projects and repo bridge surfaces |
| `/tasks` | Work | Task workflow |
| `/planner` | Work | Daily plan and review |
| `/more` | Support | Directory of supporting modules and tools |
| `/users-devices` | Control | Security and access management |
| `/voice` | Support | Voice assistant / voice intelligence |
| `/modules/*` | Registry | Module hub and module package routes |
| `/module-packages/:moduleId` | Package | Module package shell |
| `/security-lock` | Guard | Locked session route |
| `/startup` | Guard | Startup gate route |

## Nested Navigation

- Dashboard has `/dashboard/search`.
- Assets contains nested routes for equipment, parts, low stock, repair summary, project summary, locations, bin map, QR lifecycle, evidence, valuation, QR labels, QR studio, print queue, scan lookup, inventory session, conflicts, quick capture, suppliers, maintenance, reorder list, orders, and visual capture.
- Treasury contains nested decisions, budget pots, monthly summary, settings, and wizard routes.
- Projects intelligence contains repo bridge and workspace subroutes.
- Module package routes resolve to `/module-packages/:moduleId`.
- Voice and security use route guards and resume links.

## Deep-Link Support

- `AppLaunchRoute` parses `--launch-route=` and `--route=` launch arguments.
- `SecurityRoutePolicy` preserves resume routes after lock.
- Module launches can be routed per module via `ModuleWindowService`.

## Safest Future GAIA Route

Recommended future landing route: `/more/ai-employee`

Rationale:

- It fits the existing "More" support area.
- It avoids introducing a new top-level tab.
- It leaves space for a future redirect alias such as `/gaia` if product naming later prefers that.
