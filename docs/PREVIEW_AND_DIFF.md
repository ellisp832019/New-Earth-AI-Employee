# Preview and Diff

GAIA previews are deterministic write proposals that must not execute code.

## Required preview details

- target path relative to an allowed root
- current hash
- proposed hash
- unified diff
- line counts
- newline style
- encoding
- truncation warning
- target existence
- target changed since preview

Preview freshness matters. If the target changes after preview, execution must fail closed.
