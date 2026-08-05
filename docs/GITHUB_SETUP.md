# GitHub Setup

Repository URL: `https://github.com/ellisp832019/New-Earth-AI-Employee.git`

Remote name: `origin`

## Branch structure

- `main`: stable validated releases only
- `gaia-v0.1`: preserved validated read-only foundation
- `gaia-v0.2-local-conversational-agent`: active v0.2 development branch

## Verify the remote

```powershell
git remote -v
git remote get-url origin
git branch -vv
git ls-remote --heads origin
git ls-remote --tags origin
```

## Normal push workflow

```powershell
git push -u origin gaia-v0.2-local-conversational-agent
git push -u origin main
git push -u origin gaia-v0.1
git push origin gaia-v0.1.0
```

## Authentication guidance

- Use Git Credential Manager or browser sign-in.
- Do not store personal access tokens in source files or commit history.
- If authentication fails, sign in through the browser and retry `git push`.

## Avoid leaking runtime data

- Keep `data\gaia.db` untracked.
- Keep `data\reports\*` untracked.
- Keep logs, caches and virtual environments untracked.
- Never commit MicroGrow content copied into GAIA.

## Open the repository on GitHub

- Visit the repository URL above in a browser.
- Open the `Branches` dropdown to inspect `main`, `gaia-v0.1`, and `gaia-v0.2-local-conversational-agent`.
- Open the `Tags` page to inspect `gaia-v0.1.0`.
