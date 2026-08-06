# GAIA v0.6 Action Template Proof

Action templates are now exposed through:

- `GET /action-templates`
- `GET /action-templates/{template_id}`
- `POST /action-templates/{template_id}/propose`
- `POST /action-templates/{template_id}/preview`

CLI coverage:

- `gaia templates list`
- `gaia templates show`
- `gaia templates propose`
- `gaia templates preview`

Templates are versioned and do not contain executable commands.
