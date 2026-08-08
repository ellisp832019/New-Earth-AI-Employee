# Release Handoff

After the B8 pull request is merged, the human operator should:

1. Update local `main`.
2. Verify the working tree is clean.
3. Verify the merged `main` SHA matches the GitHub merged SHA.
4. Rerun release readiness if policy requires it.
5. Verify release metadata is still `0.9.0`.
6. Create the annotated tag `gaia-v0.9.0` on the exact merged SHA.
7. Push only that tag.
8. Create the GitHub release from the prepared v0.9.0 release notes.
9. Verify the tag and release point to the same commit.
10. Perform the post-release smoke and health checks.

## Boundary

- Do not execute these release steps during B8 branch work.
- Do not tag or publish the release from this branch.
- Do not modify the external Dashboard or MicroGrow repositories.
