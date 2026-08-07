# Detector Rules

B2 detectors are conservative and deterministic.

## Supported change classes

- `snapshot_delta`
- `health_transition`
- `branch_change`
- `head_change`
- `working_tree_change`
- `upstream_divergence`
- `important_path_change`
- `evidence_freshness_change`
- `configuration_change`

## Higher-level evidence

B2 does not fabricate findings for unsupported evidence. The following remain not evaluated unless a reliable structured source exists:

- `release_drift`
- `contract_drift`
- `documentation_drift`
- `dependency_drift`
- `test_regression`
- `untracked_work`

## Deterministic outputs

- change direction is one of improved, degraded, changed, unchanged, unknown;
- severity maps to documented rules only;
- confidence stays high, medium, low, or unknown;
- same semantic evidence produces the same findings.
