# GAIA Integration Gap Matrix

| Requirement | Current Dashboard support | GAIA requirement | Compatibility | Gap | Risk | Proposed solution | Affected files | Validation | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Flutter/Dart app host | Yes | Flutter packages | Good | None | Low | Use direct package dependencies | `pubspec.yaml`, `lib/app.dart` | `flutter analyze` | 1 |
| Official GAIA client | No | Use `gaia_integration_client` | Partial | New dependency | Medium | Add package as pinned dependency | `pubspec.yaml`, adapter layer | Widget and client tests | 2 |
| Embedded module | No | Use `gaia_dashboard_module` | Partial | New route surface | Medium | Add read-only embedded route | `lib/core/routing/app_router.dart`, `lib/features/more/presentation/more_screen.dart` | Route and smoke tests | 3 |
| Navigation entry | No | Add GAIA entry point | Partial | No current GAIA route | Medium | Add support route under `More` | `route_names.dart`, `more_screen.dart` | Navigation tests | 3 |
| Compatibility gate | Partial | Surface compatibility state | Partial | No GAIA-specific gate | Medium | Build dashboard-owned adapter state | GAIA adapter controller | Failure-state tests | 4 |
| Capability gating | Partial | Read capability catalog | Partial | No GAIA catalog UI | Medium | Render catalog and disabled features | GAIA adapter UI | Widget tests | 4 |
| Stale-data UX | Partial | Show stale cache clearly | Partial | No GAIA stale cache state | Medium | Carry cached snapshots and stale labels | GAIA adapter state | Offline tests | 4 |
| Trust alerts | No | Show trust alerts | Gap | New surface | Medium | Read alerts only, no write actions | GAIA module route | Trust alert tests | 6 |
| Provenance summaries | No | Show provenance and receipt summaries | Gap | New surface | Medium | Read-only inspection views | GAIA module route | Provenance tests | 6 |
| Signing lifecycle | No | Keep signing keys hidden from Dashboard | Gap | Strong boundary needed | High | Do not expose private keys; read summaries only | Backend only | Boundary tests | 1-6 |
| Keyboard navigation | Yes | Preserve accessible navigation | Good | Ensure new route is keyboard reachable | Low | Use existing shell and tab order | App shell / GAIA route | Keyboard smoke tests | 3-8 |
| Responsive layout | Yes | Keep desktop/mobile parity | Good | Ensure GAIA module fits shell | Low | Reuse `WorkspaceShell` patterns | UI shell | Layout tests | 3-8 |
| Windows build | Yes | Must keep Windows green | Good | None if route is additive | Medium | Validate Windows app after integration | Root app + GAIA route | Windows build | 9 |
| Web build | Partial | Must not regress web shell | Partial | Future route may need guards | Medium | Keep route shell responsive and read-only | Root app | Web build | 9 |
| Conformance tests | No direct package | Verify official GAIA package behavior | Partial | No Dashboard-owned conformance harness | Medium | Reuse GAIA tests plus dashboard smoke tests | GAIA repo + Dashboard repo | Release readiness | 8-10 |
