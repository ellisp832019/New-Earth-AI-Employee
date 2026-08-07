# Validation Evidence

Recorded on August 7, 2026.

## Backend

- `py -3.14 -m ruff check src tests`: passed
- `py -3.14 -m mypy src\gaia`: passed
- `py -3.14 -m pytest`: passed, 105 tests

## Flutter / Windows

- `flutter analyze`: passed
- `flutter test`: passed, 2 widget tests
- `flutter build windows --release`: passed, produced `apps\gaia_windows\build\windows\x64\runner\Release\gaia_windows.exe`
- Windows smoke test: passed via `scripts\test_gaia_windows_live.ps1`

## Release artifact

- `gaia_windows.exe` SHA-256: `7B1C6B9C02857B8BE42EDD5D11A3D4F0F6AEA37E60057E25A18AEE54CC2ED273`

## Repository checks

- `powershell -File .\scripts\release_readiness.ps1`: passed
- `powershell -File .\scripts\validate_dashboard_conformance.ps1`: passed
- `powershell -File .\scripts\validate_integration_contract.ps1`: passed
- `contracts/openapi/gaia-v1.json` regenerated from the live app schema: passed

## External-repo safety

- MicroGrow V1 read-only proof: passed
- New Earth Dashboard read-only proof: passed

## Notes

- `py -3.14` was used for the backend validation because the local Windows launcher exposed the active Python 3.14 interpreter reliably.
- `apps/gaia_windows/pubspec.lock` updated after `flutter pub get`.
- No build outputs, executables, runtime databases, caches, or `.dart_tool` directories were committed.
