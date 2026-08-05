# Release Process

## Required checks

- Clean working tree
- Full test suite
- Ruff
- mypy
- `python -m compileall src`
- Public-repository security review
- Documentation review
- Validation evidence captured

## Release steps

1. Finish the scoped work on a development branch.
2. Run the validation and quality checks.
3. Confirm the MicroGrow read-only proof still holds.
4. Commit intentionally.
5. Create an annotated tag.
6. Push without force.
7. Open a pull request into `main`.
8. Merge only after acceptance.

## Tagging

- Use annotated tags for validated releases.
- Keep the tag message descriptive and release-focused.

## Notes

- Do not publish runtime databases.
- Do not publish logs or private evidence.
- Do not force push published history.
