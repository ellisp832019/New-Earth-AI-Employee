# CLI Reference

GAIA ships a Typer CLI for local control and validation.

## Common Commands

- `gaia doctor`
- `gaia project scan <project-id>`
- `gaia project snapshot <project-id>`
- `gaia project report <project-id>`
- `gaia ask <project-id> "<question>"`

## v0.5 Commands

- `gaia permissions list`
- `gaia permissions show <manifest-id>`
- `gaia permissions validate <manifest-id>`
- `gaia permissions create`
- `gaia permissions review <manifest-id>`
- `gaia actions list`
- `gaia actions show <action-id>`
- `gaia actions preview <action-id>`
- `gaia actions request-approval <action-id>`
- `gaia actions approve <action-id>`
- `gaia actions execute <action-id>`
- `gaia actions rollback <action-id>`
- `gaia actions cancel <action-id>`
- `gaia receipts list`
- `gaia receipts show <receipt-id>`

## Usage Notes

- The CLI mirrors the same safety model as the API.
- Path safety, manifest enforcement, and explicit confirmation are not optional.
