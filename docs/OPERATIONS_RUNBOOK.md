# Operations Runbook

## First-run checklist

- [ ] Repository extracted to the intended path.
- [ ] MicroGrow path confirmed.
- [ ] Python environment created.
- [ ] Automated tests pass.
- [ ] `gaia doctor` reviewed.
- [ ] Pre-scan MicroGrow status captured.
- [ ] Scan completed.
- [ ] Snapshot created.
- [ ] Foundation report generated.
- [ ] Post-scan MicroGrow status matches pre-scan state.
- [ ] Generated data checked for unexpected secrets.

## Recovery

The SQLite database and generated reports are disposable evidence products. Stop GAIA, archive them if required, remove `data\gaia.db`, then rerun the scan and snapshot commands.

Never recover from an error by weakening path controls or enabling unrestricted commands.
