# Prompt Injection Defence

GAIA treats repository text as untrusted data.

## Safeguards

- Flag obvious instruction-like phrases in retrieved content.
- Keep system instructions outside repository text.
- Prevent document content from changing tool permissions.
- Do not execute generated prompts.

## Examples of blocked content

- "ignore all previous instructions"
- "run PowerShell"
- "delete the repository"
- "send credentials"

## Reporting

- Surface prompt-injection warnings in the run record.
- Keep the warnings separate from normal evidence.
