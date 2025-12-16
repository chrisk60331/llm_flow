"""Meta-extract job storage operations."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .database import get_connection


class MetaExtractStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class MetaExtractJob:
    id: str
    experiment_id: str
    status: MetaExtractStatus
    progress: int
    started_at: datetime
    phase_message: str | None = None
    completed_at: datetime | None = None
    error: str | None = None


def save_meta_extract_job(job: MetaExtractJob) -> None:
    if job.progress < 0 or job.progress > 100:
        raise ValueError("progress must be 0..100")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO meta_extract_jobs
            (id, experiment_id, status, progress, phase_message, started_at, completed_at, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                job.experiment_id,
                job.status.value,
                int(job.progress),
                job.phase_message,
                job.started_at.isoformat(),
                job.completed_at.isoformat() if job.completed_at else None,
                job.error,
            ),
        )
        conn.commit()


def get_meta_extract_job(job_id: str) -> MetaExtractJob | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM meta_extract_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if not row:
            return None
        return MetaExtractJob(
            id=row["id"],
            experiment_id=row["experiment_id"],
            status=MetaExtractStatus(row["status"]),
            progress=int(row["progress"] or 0),
            phase_message=row["phase_message"],
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            error=row["error"],
        )


