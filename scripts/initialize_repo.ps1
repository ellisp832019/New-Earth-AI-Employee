$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Git is not installed or not on PATH." }
if (-not (Test-Path ".git")) {
    git init
    git checkout -b develop
    git add .
    git commit -m "feat(gaia): add read-only project inspection foundation"
    Write-Host "Git repository initialised on develop." -ForegroundColor Green
} else {
    Write-Host "Git repository already exists. No changes made." -ForegroundColor Yellow
    git status
}
