# Dashboard Technology and Build Map

## Technology Stack

| Area | Observed stack |
| --- | --- |
| Application framework | Flutter |
| Language | Dart |
| Primary state management | Riverpod (`flutter_riverpod`) |
| Routing | `go_router` with `StatefulShellRoute.indexedStack` |
| Persistence | Drift over SQLite |
| Local file access | `dart:io`, `path`, `path_provider` |
| Desktop windowing | `window_manager`, `tray_manager`, `hotkey_manager` |
| Voice stack | `speech_to_text` plus local desktop bridge helpers |
| PDF / print tooling | `pdf`, `printing`, `pdfrx`, `archive`, `xml`, `qr_flutter` |
| Testing | `flutter_test` and feature-level widget/repository tests |
| Build system | Flutter CLI / Dart pub, plus repo scripts |
| Config | `pubspec.yaml`, `analysis_options.yaml`, `app_database.dart`, local JSON/file stores |

## Platform Targets

- Android source tree present.
- iOS source tree is expected in a Flutter app layout.
- Web source tree present.
- Windows source tree present.
- Linux and macOS support is present in the app shell and desktop windowing layer.

## Packaging and Release

- `version: 1.0.0+1` in the root `pubspec.yaml`.
- Assets are declared in `pubspec.yaml`.
- Root app entry is `lib/main.dart`.
- Analyzer config is in `analysis_options.yaml`.
- No repo-local `.github/workflows` files were found in the dashboard root during this audit.

## Build Commands

- `flutter pub get`
- `flutter analyze`
- `flutter test`
- `flutter run`
- `flutter build windows`
- `flutter build web`

## Notes

The repository is a monorepo-style dashboard workspace. The main app is at the repo root and the feature modules are grouped under `lib/features/`.
