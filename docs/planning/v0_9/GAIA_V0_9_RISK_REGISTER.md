# GAIA v0.9 Risk Register

| Risk | Impact | Likelihood | Mitigation |
| --- | --- | --- | --- |
| Recommendations become opaque | High | Medium | Keep scoring deterministic and expose rationale. |
| Multi-project support weakens isolation | High | Medium | Enforce allowlists, canonical paths, and project-level permissions. |
| Work packages drift into autonomous execution | High | Low | Keep approval and execution boundaries separate. |
| Dashboard summaries leak execution authority | High | Low | Keep Dashboard read-only. |
| Docs drift from implementation state | Medium | Medium | Update planning docs and release notes together. |
| v0.8 compatibility breaks | High | Low | Preserve backward-aware versioning and avoid silent semantic changes. |
| Stale evidence misleads prioritisation | Medium | Medium | Surface freshness, expiry, and confidence. |
