$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root\packages\gaia_dashboard_module
flutter pub get
flutter analyze
flutter test
