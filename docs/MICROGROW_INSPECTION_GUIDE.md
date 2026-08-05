# MicroGrow Inspection Guide

## Capture the initial state manually

Before the first scan:

```powershell
cd "D:\Dev\Projects\MicroGrow V1"
git status
git branch --show-current
git rev-parse HEAD
```

Return to GAIA:

```powershell
cd "D:\Dev\Projects\New-Earth-AI-Employee"
.\.venv\Scripts\Activate.ps1
gaia project scan microgrow-v1
gaia project snapshot microgrow-v1
gaia project report microgrow-v1 --output data\reports\MICROGROW_FOUNDATION_REPORT.md
```

## What the first report proves

It proves the repository identity, Git state, document inventory, configured important-path presence and scan warnings at a specific time.

It does not yet prove that planned features are implemented. Feature classification will be added by the evidence-analysis stage after local model integration.

## Useful searches

```powershell
gaia project search microgrow-v1 "release readiness"
gaia project search microgrow-v1 "experimental"
gaia project search microgrow-v1 "future version"
gaia project search microgrow-v1 "PlatformIO build verification"
gaia project search microgrow-v1 "user guide"
```
