from __future__ import annotations

import json
from pathlib import Path

from gaia.models import RepositorySnapshot


def foundation_report_markdown(snapshot: RepositorySnapshot) -> str:
    git = snapshot.git
    important = "\n".join(
        f"- `{path}`: {'present' if present else 'missing'}"
        for path, present in snapshot.important_paths.items()
    )
    extension_rows = "\n".join(
        f"| `{extension or '[none]'}` | {count} |"
        for extension, count in sorted(snapshot.counts_by_extension.items())
    ) or "| — | 0 |"
    warnings = "\n".join(f"- {warning}" for warning in [*git.warnings, *snapshot.scan_warnings]) or "- None"
    recent = "\n".join(f"- `{item}`" for item in git.recent_commits[:10]) or "- None available"
    status = "clean" if git.is_clean else "contains changes"
    return f"""# GAIA Foundation Report — {snapshot.project_name}

Generated: `{snapshot.created_at.isoformat()}`  
Snapshot ID: `{snapshot.snapshot_id}`

## Repository identity

- Project ID: `{snapshot.project_id}`
- Root: `{snapshot.project_root}`
- Git root: `{git.repository_root}`
- Branch: `{git.branch or 'unknown'}`
- Commit: `{git.commit_sha or 'unknown'}`
- Working tree: **{status}**
- Ahead / behind: `{git.ahead if git.ahead is not None else 'unknown'} / {git.behind if git.behind is not None else 'unknown'}`
- Tracked files: `{git.tracked_file_count}`

## Document inventory

- Documents discovered: `{snapshot.document_count}`
- Indexed: `{snapshot.indexed_count}`
- Skipped: `{snapshot.skipped_count}`
- Failed: `{snapshot.failed_count}`

| Extension | Count |
|---|---:|
{extension_rows}

## Important paths

{important}

## Recent commits

{recent}

## Working-tree evidence

- Changed files: `{len(git.changed_files)}`
- Untracked files: `{len(git.untracked_files)}`

## Warnings

{warnings}

## Interpretation boundary

This is a deterministic foundation report generated from Git metadata, configured path checks and the local document index. It does not claim that a feature is complete, safe or release-ready. Those conclusions require an evidence-based analysis workflow in a later GAIA stage.
"""


def foundation_report_json(snapshot: RepositorySnapshot) -> str:
    return json.dumps(snapshot.model_dump(mode="json"), indent=2, sort_keys=True)


def write_report(snapshot: RepositorySnapshot, output: Path, format_name: str) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    content = foundation_report_json(snapshot) if format_name == "json" else foundation_report_markdown(snapshot)
    output.write_text(content, encoding="utf-8")
    return output
