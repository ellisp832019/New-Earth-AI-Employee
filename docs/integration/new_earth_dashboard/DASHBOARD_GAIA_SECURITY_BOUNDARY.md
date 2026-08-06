# Dashboard GAIA Security Boundary

## Main Rule

The Dashboard may consume GAIA as a read-only local backend and embedded workspace. It must not become another GAIA backend.

## Risks and Controls

| Risk | Control |
| --- | --- |
| Direct GAIA SQLite access | Use only the official GAIA HTTP client and backend routes |
| Direct runtime file access | Do not read GAIA runtime files from the Dashboard repo |
| Duplicated permission decisions | Keep permissions and trust decisions in GAIA and the Dashboard's own access model only |
| Duplicated receipt verification | Treat GAIA as source of truth and only consume verification results |
| Unprotected action execution | Keep the embedded module read-only; no action execution route in Dashboard |
| Unsafe backend URL configuration | Restrict to loopback/local config and validate host/port input |
| External network exposure | Prefer loopback by default; no cloud fallback unless explicitly designed later |
| Private draft leakage | Do not surface GAIA draft/private data outside the read-only module contract |
| Signing-key exposure | Never expose private signing material; summaries only |
| Untrusted HTML rendering | Render text, not raw HTML; sanitize any markdown or rich text content |
| Arbitrary path handling | Canonicalize and validate paths before any file access |
| Unsupported cloud fallback | Keep cloud fallback disabled by default and feature-flagged if ever introduced |

## Required Controls for Phase B

- The embedded GAIA route must stay read-only.
- The Dashboard must never return private keys from GAIA.
- The Dashboard must treat backend connectivity failures as degraded state, not fatal app errors.
- Any cached GAIA state must be clearly labeled as stale.
- Any future deep link to the standalone control centre must remain an explicit user action.
