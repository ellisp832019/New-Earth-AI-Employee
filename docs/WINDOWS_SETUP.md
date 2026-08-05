# Windows Setup

## Requirements

- Windows 11 or supported Windows 10;
- Git for Windows;
- Python 3.11, 3.12 or the compatible interpreter available on the machine;
- PowerShell;
- the MicroGrow repository, normally at `D:\Dev\Projects\MicroGrow V1`.

## Install

```powershell
cd "D:\Dev\Projects\New-Earth-AI-Employee"
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_windows.ps1
```

The script deliberately does not depend on the `py` launcher.

When multiple Python installations exist:

```powershell
.\scripts\setup_windows.ps1 -Python "C:\Users\ellis\AppData\Local\Programs\Python\Python312\python.exe"
```

If the machine only has a newer compatible interpreter, point `-Python` at that executable instead. The current validation run in this workspace used Python 3.14.4 because no 3.11/3.12 installation was present.

## Activate

```powershell
.\.venv\Scripts\Activate.ps1
```

## Verify

```powershell
gaia doctor
.\scripts\run_tests.ps1
```

## Change the MicroGrow path

Edit `config\projects.yaml`. Preserve doubled backslashes or use a single-quoted YAML value.
