$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Set-Location $root\packages\gaia_dashboard_module
flutter pub get
flutter analyze
flutter test
Set-Location $root\examples\gaia_dashboard_host
flutter pub get
flutter analyze
flutter test
