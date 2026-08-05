# Project Registry

Projects are declared in `config/projects.yaml`.

```yaml
projects:
  microgrow-v1:
    name: MicroGrow V1
    root: 'D:\Dev\Projects\MicroGrow V1'
    access: read_only
    approved_extensions:
      - .md
      - .json
    excluded_directories:
      - .git
      - build
    excluded_filenames:
      - .env
    important_paths:
      - README.md
      - docs/project_control
```

Only `read_only` is accepted in v0.1. Do not add write access by changing YAML alone; future writes require a separate approval subsystem and separate tools.
