# Prompt Injection Boundary

B4 treats all evidence as structured input, not as instructions.

## Boundary controls

- free-text evidence is summarized into package fields;
- structured evidence is embedded as JSON for inspection only;
- prompt text contains an explicit human-review STOP marker;
- the package never gains execution authority from prompt content;
- the service does not make repository writes outside the GAIA database.

## Reviewer expectation

Humans must inspect the package before anything is handed off to Codex.
