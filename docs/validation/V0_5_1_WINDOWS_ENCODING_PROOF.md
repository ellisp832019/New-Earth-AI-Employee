# GAIA v0.5.1 Windows Encoding Proof

## Fix

- `scripts/version_status.ps1` now uses `flutter --version --machine` instead of decorative human-readable output.

## Reported Fields

- `pythonPackageVersion`
- `flutterVersion`
- `flutterChannel`
- `dartVersion`
- `frameworkRevision`
- `gitBranch`
- `gitSha`
- `backendOwnershipState`
- `backendCompatibility`
- `backendVersion`

## Result

The status script no longer depends on Unicode glyphs in Flutter's human-readable banner output.
