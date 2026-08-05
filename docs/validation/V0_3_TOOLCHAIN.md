# GAIA v0.3 Toolchain

## Flutter

- `flutter --version`: Flutter 3.41.7 stable
- `dart --version`: Dart SDK 3.11.5
- `flutter config --enable-windows-desktop`: succeeded
- `flutter devices`: Windows desktop available

## Python

- System interpreter: `C:\Users\ellis\AppData\Local\Programs\Python\Python314\python.exe`
- Project venv: `.venv\Scripts\python.exe`
- Package validation ran successfully in the venv

## Validation commands

- `flutter pub get`
- `flutter analyze`
- `flutter test`
- `flutter build windows --debug`
- `flutter build windows --release`
- `python -m compileall src tests`
- `python -m ruff check src tests`
- `python -m mypy src\gaia`
- `python -m pytest`

## Notes

- The Windows client targets the local backend on `127.0.0.1:8000`.
- The existing API service still defaults to `8765` for the standalone backend path.
