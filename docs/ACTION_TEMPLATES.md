# Action Templates

GAIA action templates are versioned, deterministic and non-executable descriptors for safe output proposals.

## Template fields

- template ID
- template version
- action type
- required inputs
- optional inputs
- target pattern
- extension
- risk
- approval requirement
- preview renderer
- retention class
- enabled state

Templates must not contain shell commands, PowerShell, Git commands or arbitrary filesystem roots.
