# Project Registry Implementation

The project registry now stores multiple approved project entries in `config/projects.yaml`.

## Registry scope

- `gaia`: this repository, read-only, used for self-inspection and health tracking;
- `microgrow-v1`: the external MicroGrow V1 repository, still the original source boundary;
- `new-earth-command-dashboard`: the external dashboard repository, tracked read-only for evidence only.

## Registry fields

Each project record now supports:

- `enabled`
- `repository_type`
- `inspection_access`
- `output_access`
- `sensitivity`
- `health_rules`
- `release_rules`
- `approval_requirements`
- `metadata`

## Safety rules

- project roots are canonicalized and compared after resolution;
- duplicate canonical roots are rejected at load time;
- the public API still exposes the compact project shape;
- internal registry metadata remains available to the service layer and health model.
