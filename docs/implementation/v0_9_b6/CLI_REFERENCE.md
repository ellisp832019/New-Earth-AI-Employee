# CLI Reference

B6 adds a GAIA CLI surface that mirrors the Project Officer API.

## Root group

- `gaia project-officer ...`

## Commands

### Discovery and inspection

- `gaia project-officer capabilities`
- `gaia project-officer portfolio`
- `gaia project-officer projects`
- `gaia project-officer health <project-id>`
- `gaia project-officer health-snapshots <project-id>`
- `gaia project-officer health-snapshot <snapshot-id>`
- `gaia project-officer change-portfolio`
- `gaia project-officer changes <project-id>`
- `gaia project-officer change <finding-id>`
- `gaia project-officer recent-changes`
- `gaia project-officer recommendation-portfolio`
- `gaia project-officer recommendations`
- `gaia project-officer recommendation <recommendation-id>`
- `gaia project-officer work-packages`

### Work-package inspection

- `gaia project-officer work-package show <work-package-id>`
- `gaia project-officer work-package summary <work-package-id>`
- `gaia project-officer work-package prompt <work-package-id>`
- `gaia project-officer work-package revisions <work-package-id>`
- `gaia project-officer work-package revision <revision-id>`
- `gaia project-officer work-package approval-decisions <work-package-id>`
- `gaia project-officer work-package handoffs <work-package-id>`
- `gaia project-officer work-package outcomes <work-package-id>`

### Lifecycle commands

- `gaia project-officer work-package submit-for-review <work-package-id>`
- `gaia project-officer work-package approve <work-package-id>`
- `gaia project-officer work-package reject <work-package-id>`
- `gaia project-officer work-package expire <work-package-id>`
- `gaia project-officer work-package handoff <work-package-id>`
- `gaia project-officer work-package outcome <work-package-id>`

## Output behavior

- Inspection commands print JSON or JSON-like model payloads.
- Lifecycle commands call the same local Project Officer service that backs the API.
- The CLI does not add execution, shell, branch, or target-repository write capability.
