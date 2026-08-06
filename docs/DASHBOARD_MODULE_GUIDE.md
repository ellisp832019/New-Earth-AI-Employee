# GAIA Dashboard Module Guide

`packages/gaia_dashboard_module` is the reusable read-mostly Flutter surface intended for future embedding in the New Earth Dashboard.

## What it does

- connects through `gaia_integration_client`;
- renders compatibility and degraded-mode states;
- surfaces project, task, approval, brief, receipt and trust summaries;
- keeps output execution out of the embedded module boundary.

## What it does not do

- it does not access SQLite directly;
- it does not read MicroGrow directly;
- it does not execute GAIA output actions;
- it does not perform rollback or retention deletes.

## Safe embedding rule

If a backend is incompatible or unavailable, the module must fail closed and keep the host usable.
