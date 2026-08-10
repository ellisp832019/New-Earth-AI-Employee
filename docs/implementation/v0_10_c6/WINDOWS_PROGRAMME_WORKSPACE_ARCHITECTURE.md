# Windows Programme Workspace Architecture

The C6 Windows workspace is a read-only shell over canonical backend programme services.

## Source of Truth

- `src/gaia/programme_registry.py`
- `src/gaia/dependency_graph.py`
- `src/gaia/change_impact.py`
- `src/gaia/programme_intelligence.py`
- `src/gaia/programme_packages.py`
- `src/gaia/project_officer.py`

## Windows App Integration

- `apps/gaia_windows/lib/src/controller.dart` now carries a single programme-workspace payload;
- `apps/gaia_windows/lib/src/programme_workspace.dart` renders the nested workspace pages;
- `apps/gaia_windows/lib/src/screens.dart` adds the top-level Programme Intelligence destination;
- `apps/gaia_windows/lib/src/backend_api.dart` calls the internal workspace payload route.

## Backend Payload

- overview and counts;
- architecture registry entities and relationships;
- dependency graph snapshot and findings;
- impact analyses derived from current recommendations;
- change proposal review records;
- roadmap, release train, and programme package portfolios;
- decisions, trust alerts, and provenance evidence.

## Design Rule

Flutter renders data only. It does not recalculate roadmap, dependency, impact, package, or approval logic.
