# Validation Evidence

Recorded on August 7, 2026.

## Backend

- `python -m ruff check src tests`: passed
- `python -m mypy src\gaia`: passed
- `python -m pytest -q`: passed

## Flutter / Windows

- `flutter analyze`: passed
- `flutter test`: passed
- `flutter build windows --release`: passed

## Repository checks

- `powershell -File .\scripts\release_readiness.ps1`: passed
- `powershell -File .\scripts\validate_dashboard_conformance.ps1`: passed
- `powershell -File .\scripts\validate_integration_contract.ps1`: passed
- `contracts/openapi/gaia-v1.json` regenerated from the live app schema: passed

## External-repo safety

- MicroGrow V1 read-only proof: passed
- New Earth Dashboard read-only proof: passed

## Notes

- `apps/gaia_windows/pubspec.lock` updated after `flutter pub get`.
- No build outputs, executables, runtime databases, caches, or `.dart_tool` directories were committed.
