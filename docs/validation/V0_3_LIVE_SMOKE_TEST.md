# GAIA v0.3 Live Smoke Test

## Smoke-test plan

- Start the local GAIA backend on loopback.
- Launch the Windows app through `flutter run -d windows --release`.
- Allow the app to run briefly.
- Confirm the backend responds on `http://127.0.0.1:8000`.
- Confirm the Windows app remains alive during the smoke window.
- Stop the app cleanly.

## Smoke-test result

- Backend health check succeeded.
- Backend version reported: `0.3.0`.
- Release-mode Windows app launched successfully through Flutter.
- The `gaia_windows` process remained running during the smoke window.
- The app was stopped cleanly after the smoke window.

## Notes

- The smoke test is intentionally loopback-only.
- It avoids arbitrary command construction and does not touch MicroGrow.
- The live smoke helper is `scripts/test_gaia_windows_live.ps1`.
- Full manual click-through validation is still pending separate review.
