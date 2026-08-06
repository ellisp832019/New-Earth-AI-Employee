# GAIA v0.6 Publication Safety Proof

GAIA v0.6 is not tagged or released from this branch.

## Current safety posture

- v0.5.1 remains the published stable release baseline.
- The v0.6 branch is intended for review only.
- MicroGrow remains read-only for this milestone.
- The separate New Earth Dashboard repository remains untouched.
- PR #6 is open against `main`, and the replacement Windows validation run now progresses past the OpenAPI export after the Python resolution fix.
- The Windows validation scripts also tolerate GitHub runner Flutter output that includes a non-JSON `Resolving...` preamble before the machine-readable version payload.
- Detached-HEAD Git state is now handled intentionally in `scripts/version_status.ps1`, so PR checkouts and other detached states report a stable `gitRefState` instead of failing on empty branch output.
- SHA reporting remains mandatory; the status helper fails clearly if `git rev-parse HEAD` does not produce a commit hash.
- The branch has not been merged, tagged, or published.
