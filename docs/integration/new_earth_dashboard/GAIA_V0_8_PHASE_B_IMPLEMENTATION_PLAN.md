# GAIA v0.8 Phase B Implementation Plan

## Stage 1: Integration Foundation and Feature Flag

- Likely files: Dashboard app settings, feature flag plumbing, route constants, basic shell hook.
- Acceptance: route is hidden by default and no GAIA code is reachable unless enabled.
- Tests: config and gating tests.
- Safety checks: no backend calls yet.
- Rollback point: remove flag and route registration.

## Stage 2: Official Client and Module Dependency

- Likely files: Dashboard `pubspec.yaml`, dependency lockfile, adapter provider, import wiring.
- Acceptance: Dashboard can create the GAIA client and render the module package in a local test harness.
- Tests: package build, client smoke tests.
- Safety checks: pin release versions.
- Rollback point: revert dependency declarations.

## Stage 3: Route, Navigation and Shell Integration

- Likely files: `lib/core/routing/app_router.dart`, `lib/core/routing/route_names.dart`, `lib/features/more/presentation/more_screen.dart`, shell widget tests.
- Acceptance: GAIA route opens from the `More` area and fits the desktop/mobile shell.
- Tests: route tests, widget tests.
- Safety checks: keep deep links explicit.
- Rollback point: hide the route and remove the menu tile.

## Stage 4: Compatibility, Capability and Connection State

- Likely files: adapter controller, status widgets, banner copy, diagnostics panel.
- Acceptance: the dashboard shows compatibility, capability catalog, and degraded state.
- Tests: offline/failure-state tests.
- Safety checks: fail closed on incompatible or unreachable backend.
- Rollback point: preserve last good state only.

## Stage 5: Embedded Operations Workspace

- Likely files: dashboard-owned wrapper around `gaia_dashboard_module`.
- Acceptance: the embedded workspace renders read-only and does not expose write actions.
- Tests: read-only module tests, keyboard navigation checks.
- Safety checks: no direct action execution.
- Rollback point: fall back to link-out only.

## Stage 6: Trust Alerts, Provenance and Retention Summaries

- Likely files: GAIA surface screens, tabs, summary cards, detail lists.
- Acceptance: trust alerts, provenance summaries, and retention summaries are visible and read-only.
- Tests: alert/provenance tests.
- Safety checks: no key material or write controls.
- Rollback point: disable the details panes.

## Stage 7: Deep Links to the Dedicated Control Centre

- Likely files: link-outs, command palette entries, help copy.
- Acceptance: users can jump to the standalone GAIA control centre explicitly.
- Tests: route and deep-link tests.
- Safety checks: no automatic cross-launch.
- Rollback point: remove the link-outs.

## Stage 8: Conformance Tests and Failure-State Tests

- Likely files: Dashboard tests, GAIA release validation scripts, host example tests.
- Acceptance: incompatible and offline cases are covered.
- Tests: widget, route, and CLI/script checks.
- Safety checks: keep the module read-only.
- Rollback point: keep the route disabled.

## Stage 9: Windows and Supported-Platform Validation

- Likely files: Windows app, platform-specific wrappers, build scripts.
- Acceptance: Windows build succeeds and the shell remains stable.
- Tests: `flutter analyze`, `flutter test`, `flutter build windows`.
- Safety checks: confirm no platform-specific path leakage.
- Rollback point: revert the route registration.

## Stage 10: Documentation, Proof and Release Readiness

- Likely files: docs, release notes, proof artifacts, checklist scripts.
- Acceptance: all audit docs and validation artifacts are complete.
- Tests: full release-readiness run.
- Safety checks: verify read-only boundary and no repo bleed-through.
- Rollback point: stop before merge and keep the integration branch isolated.
