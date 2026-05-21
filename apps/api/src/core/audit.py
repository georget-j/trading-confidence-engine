"""Audit log persistence.

Every pipeline run produces an AuditLog. Writing it to disk gives us a
reproducible record we can replay, diff, and use as a regression seed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from src.core.schemas import AuditEntry, AuditLog


def new_audit_log(request_id: UUID) -> AuditLog:
    return AuditLog(request_id=request_id)


def record(log: AuditLog, stage: str, payload: dict[str, Any]) -> None:
    """Append a stage entry to the in-memory audit log.

    `stage` is constrained by the Literal in AuditEntry.stage.
    """
    log.entries.append(AuditEntry(stage=stage, payload=payload))  # type: ignore[arg-type]


def write_to_disk(log: AuditLog, directory: Path) -> Path:
    """Serialize an audit log as JSON. Returns the path written."""
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{log.request_id}.json"
    target.write_text(log.model_dump_json(indent=2))
    return target
