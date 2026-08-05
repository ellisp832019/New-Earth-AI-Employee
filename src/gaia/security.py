from __future__ import annotations

import os
from pathlib import Path

from gaia.models import ProjectConfig


class PathSecurityError(PermissionError):
    """Raised when a requested path violates the project security policy."""


def _normcase(path: Path) -> str:
    return os.path.normcase(str(path))


def resolve_project_path(project: ProjectConfig, requested: str | Path) -> Path:
    root = project.root.expanduser().resolve(strict=True)
    raw = Path(requested)
    candidate = raw if raw.is_absolute() else root / raw
    candidate = candidate.expanduser().resolve(strict=True)

    root_case = _normcase(root)
    candidate_case = _normcase(candidate)
    try:
        common = os.path.commonpath([root_case, candidate_case])
    except ValueError as exc:
        raise PathSecurityError("Path is on a different drive or root") from exc
    if common != root_case:
        raise PathSecurityError("Path escapes the registered project root")

    relative = candidate.relative_to(root)
    for part in relative.parts[:-1] if candidate.is_file() else relative.parts:
        if part.lower() in {name.lower() for name in project.excluded_directories}:
            raise PathSecurityError(f"Path is inside excluded directory: {part}")

    if candidate.is_file():
        if candidate.name.lower() in {name.lower() for name in project.excluded_filenames}:
            raise PathSecurityError("Filename is explicitly excluded")
        if candidate.suffix.lower() not in project.approved_extensions:
            raise PathSecurityError(f"File extension is not approved: {candidate.suffix}")

    return candidate


def is_secret_bearing_filename(name: str) -> bool:
    lower = name.lower()
    secret_tokens = (
        ".env",
        "credential",
        "secret",
        "private_key",
        "id_rsa",
        "id_ed25519",
        "token",
        "apikey",
        "api_key",
    )
    return any(token in lower for token in secret_tokens)
