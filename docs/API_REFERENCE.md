# API Reference

Start the service:

```powershell
.\scripts\start_api.ps1
```

Open `http://127.0.0.1:8765/docs` for interactive OpenAPI documentation.

## Endpoints

- `GET /health`
- `GET /projects`
- `GET /projects/{project_id}`
- `POST /projects/{project_id}/scan`
- `GET /projects/{project_id}/snapshots`
- `GET /projects/{project_id}/snapshots/latest`
- `GET /projects/{project_id}/documents`
- `GET /projects/{project_id}/search?q=...`
- `POST /projects/{project_id}/reports/foundation?format=markdown`
- `GET /audit/events`

The API binds to loopback by default. Do not expose it to a network until authentication, transport security and deployment hardening are implemented.
