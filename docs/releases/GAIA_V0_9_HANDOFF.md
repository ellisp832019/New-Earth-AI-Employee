# GAIA v0.9 Handoff

## What Has Been Completed

- B1 through B7 are fully accepted and documented.
- PR #19 merged the Windows stability blocker repair.
- Version-controlled release metadata was reconciled to `0.9.0`.
- OpenAPI contract generation was regenerated from the live backend.
- Cross-repository acceptance evidence was captured for the Dashboard and MicroGrow baselines.
- Release validation passed on the current branch.

## What Peter Should Do Next

1. Review and merge the B8 pull request.
2. Update local `main` after merge.
3. Verify the merge commit SHA on `main`.
4. Confirm the working tree is clean.
5. Verify release metadata remains on `0.9.0`.
6. Create the annotated tag `gaia-v0.9.0` on the exact merged SHA.
7. Push only that tag.
8. Create the GitHub release from `GAIA_V0_9_0_RELEASE_NOTES.md`.
9. Verify the tag and release point to the same commit.
10. Perform the post-release smoke and health checks.

## Boundary

- Do not tag during B8 branch work.
- Do not publish the GitHub release during B8 branch work.
- Do not modify Dashboard or MicroGrow from this repository.
