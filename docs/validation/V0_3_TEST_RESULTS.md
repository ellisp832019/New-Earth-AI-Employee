# GAIA v0.3 Test Results

## Flutter client

- `flutter analyze`: passed with no issues
- `flutter test`: passed
- `flutter build windows --debug`: passed, produced `build\windows\x64\runner\Debug\gaia_windows.exe`
- `flutter build windows --release`: passed, produced `build\windows\x64\runner\Release\gaia_windows.exe`
- Live release-mode smoke test: passed through `flutter run -d windows --release`

## Python backend

- `python -m compileall src tests`: passed
- `python -m ruff check src tests`: passed
- `python -m mypy src\gaia`: passed
- `python -m pytest`: 40 passed, 1 warning

## Warning noted

- The pytest run surfaced the existing Starlette/httpx deprecation warning from the bundled test client stack.

## Notes

- The Windows desktop app remains read-only and uses the existing GAIA evidence and reporting APIs.
- The backend reported version `0.3.0` during the smoke run.
