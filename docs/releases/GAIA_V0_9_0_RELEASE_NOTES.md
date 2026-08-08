# GAIA v0.9.0 Release Notes

GAIA v0.9.0 is the final planned v0.9 release candidate for the local-first GAIA project officer workflow.

## Highlights

- multi-project registry and project health;
- snapshot comparison, drift, and stale-evidence detection;
- deterministic recommendation ranking and dependency-aware prioritisation;
- human-reviewable work packages with exact revision tracking;
- explicit approval and handoff records that do not execute work automatically;
- Windows Project Officer Workspace for review, approval, and handoff preparation;
- versioned API, CLI, and integration-client support for the Project Officer surfaces;
- read-only New Earth Dashboard summaries;
- contract-based compatibility handling;
- Windows stability repair from PR #19;
- provenance and cross-repository acceptance evidence.

## Acceptance Summary

- B1 through B7 are accepted and documented in the implementation evidence package.
- Dashboard B7B is accepted at main SHA `0d15afcc0a9bc46c5486485f199c5e42f67ac469`.
- The Windows stability release blocker from PR #19 was merged at `2b8b27780d924d63455f5072c208f5d415133a92`.
- The live Windows Control Centre now reports compatibility from the explicit integration contract and no longer relies on stale v0.5-only wording.

## Versioning

- GAIA backend version: `0.9.0`.
- Windows app version: `0.9.0+1`.
- Official integration client version: `0.9.0`.
- Official dashboard module version: `0.9.0`.
- Example host version: `0.9.0`.

## Safety

- GAIA v0.9.0 does not autonomously execute approved work packages.
- The Dashboard remains read-only.
- MicroGrow remains read-only.
- Release publication is deferred until the merged release SHA is tagged and published by the human operator.
