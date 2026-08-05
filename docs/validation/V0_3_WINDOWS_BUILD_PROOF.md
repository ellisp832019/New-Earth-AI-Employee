# GAIA v0.3 Windows Build Proof

## Debug build

- Command: `flutter build windows --debug`
- Result: success
- Output: `apps\gaia_windows\build\windows\x64\runner\Debug\gaia_windows.exe`

## Release build

- Command: `flutter build windows --release`
- Result: success
- Output: `apps\gaia_windows\build\windows\x64\runner\Release\gaia_windows.exe`

## Notes

- The app bootstraps the GAIA control centre shell and connects to the local backend on `127.0.0.1:8000`.
- Windows desktop support was enabled before building.
