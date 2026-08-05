from __future__ import annotations

import hashlib
import os
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from gaia.models import DocumentRecord, ProjectConfig
from gaia.security import PathSecurityError, is_secret_bearing_filename, resolve_project_path


class DocumentScanner:
    def __init__(self, max_file_bytes: int = 2_000_000) -> None:
        self.max_file_bytes = max_file_bytes

    def scan(self, project: ProjectConfig, tracked_files: set[str] | None = None) -> list[DocumentRecord]:
        root = project.root.resolve(strict=True)
        records: list[DocumentRecord] = []
        for path in self._walk(root, project):
            relative = path.relative_to(root).as_posix()
            try:
                safe_path = resolve_project_path(project, path)
            except PathSecurityError:
                continue
            stat = safe_path.stat()
            sha256 = _hash_file(safe_path)
            modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
            tracked = relative in tracked_files if tracked_files is not None else None
            if stat.st_size > self.max_file_bytes:
                records.append(
                    DocumentRecord(
                        project_id=project.project_id,
                        relative_path=relative,
                        extension=safe_path.suffix.lower(),
                        size_bytes=stat.st_size,
                        modified_utc=modified,
                        sha256=sha256,
                        tracked=tracked,
                        indexing_status="skipped",
                        warning=f"File exceeds configured limit of {self.max_file_bytes} bytes",
                    )
                )
                continue
            try:
                content = safe_path.read_text(encoding="utf-8", errors="strict")
                warning = None
            except UnicodeDecodeError:
                try:
                    content = safe_path.read_text(encoding="utf-8", errors="replace")
                    warning = "Invalid UTF-8 bytes were replaced"
                except OSError as exc:
                    records.append(
                        DocumentRecord(
                            project_id=project.project_id,
                            relative_path=relative,
                            extension=safe_path.suffix.lower(),
                            size_bytes=stat.st_size,
                            modified_utc=modified,
                            sha256=sha256,
                            tracked=tracked,
                            indexing_status="failed",
                            warning=f"Read failed: {type(exc).__name__}",
                        )
                    )
                    continue
            except OSError as exc:
                records.append(
                    DocumentRecord(
                        project_id=project.project_id,
                        relative_path=relative,
                        extension=safe_path.suffix.lower(),
                        size_bytes=stat.st_size,
                        modified_utc=modified,
                        sha256=sha256,
                        tracked=tracked,
                        indexing_status="failed",
                        warning=f"Read failed: {type(exc).__name__}",
                    )
                )
                continue

            records.append(
                DocumentRecord(
                    project_id=project.project_id,
                    relative_path=relative,
                    extension=safe_path.suffix.lower(),
                    size_bytes=stat.st_size,
                    modified_utc=modified,
                    sha256=sha256,
                    tracked=tracked,
                    indexing_status="indexed",
                    warning=warning,
                    content=content,
                )
            )
        return records

    def _walk(self, root: Path, project: ProjectConfig) -> Iterable[Path]:
        excluded_dirs = {name.lower() for name in project.excluded_directories}
        excluded_files = {name.lower() for name in project.excluded_filenames}
        for current, dirs, files in os.walk(root, followlinks=False):
            current_path = Path(current)
            dirs[:] = [
                directory
                for directory in dirs
                if directory.lower() not in excluded_dirs
                and not (current_path / directory).is_symlink()
            ]
            for filename in files:
                path = current_path / filename
                if path.is_symlink():
                    continue
                if filename.lower() in excluded_files or is_secret_bearing_filename(filename):
                    continue
                if path.suffix.lower() not in project.approved_extensions:
                    continue
                yield path


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
