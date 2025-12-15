"""Optimization and AutoTune job storage operations."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..models import AutoTuneCandidate, AutoTuneJob, AutoTuneStatus
from .database import get_connection


# --- Optimization Jobs ---


class OptimizationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OptimizationJob:
    id: str
    dataset_id: str
    status: OptimizationStatus
    started_at: datetime
    completed_at: datetime | None = None
    candidates: list[dict] | None = None
    best_config: dict | None = None
    message: str | None = None
    error: str | None = None


def save_optimization_job(job: OptimizationJob) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO optimization_jobs
            (id, dataset_id, status, started_at, completed_at, candidates, best_config, message, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                job.dataset_id,
                job.status.value,
                job.started_at.isoformat(),
                job.completed_at.isoformat() if job.completed_at else None,
                json.dumps(job.candidates) if job.candidates else None,
                json.dumps(job.best_config) if job.best_config else None,
                job.message,
                job.error,
            ),
        )
        conn.commit()


def get_optimization_job(job_id: str) -> OptimizationJob | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM optimization_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        if not row:
            return None
        return OptimizationJob(
            id=row["id"],
            dataset_id=row["dataset_id"],
            status=OptimizationStatus(row["status"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            candidates=json.loads(row["candidates"]) if row["candidates"] else None,
            best_config=json.loads(row["best_config"]) if row["best_config"] else None,
            message=row["message"],
            error=row["error"],
        )


def list_optimization_jobs() -> list[OptimizationJob]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM optimization_jobs ORDER BY started_at DESC"
        ).fetchall()
        return [
            OptimizationJob(
                id=row["id"],
                dataset_id=row["dataset_id"],
                status=OptimizationStatus(row["status"]),
                started_at=datetime.fromisoformat(row["started_at"]),
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                candidates=json.loads(row["candidates"]) if row["candidates"] else None,
                best_config=json.loads(row["best_config"]) if row["best_config"] else None,
                message=row["message"],
                error=row["error"],
            )
            for row in rows
        ]


# --- AutoTune Jobs ---


def save_autotune_job(job: AutoTuneJob) -> None:
    with get_connection() as conn:
        candidates_json = json.dumps([c.model_dump() for c in job.candidates]) if job.candidates else None
        conn.execute(
            """
            INSERT OR REPLACE INTO autopilot_jobs
            (id, dataset_id, benchmark_id, base_config_id, status, phase_message, top_k,
             candidates, current_training_idx, current_eval_idx, started_at, completed_at, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                job.dataset_id,
                job.benchmark_id,
                job.base_config_id,
                job.status.value,
                job.phase_message,
                job.top_k,
                candidates_json,
                job.current_training_idx,
                job.current_eval_idx,
                job.started_at.isoformat(),
                job.completed_at.isoformat() if job.completed_at else None,
                job.error,
            ),
        )
        conn.commit()


def get_autotune_job(job_id: str) -> AutoTuneJob | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM autopilot_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        if not row:
            return None
        candidates = []
        if row["candidates"]:
            candidates = [AutoTuneCandidate(**c) for c in json.loads(row["candidates"])]
        return AutoTuneJob(
            id=row["id"],
            dataset_id=row["dataset_id"],
            benchmark_id=row["benchmark_id"],
            base_config_id=row["base_config_id"],
            status=AutoTuneStatus(row["status"]),
            phase_message=row["phase_message"] or "",
            top_k=row["top_k"],
            candidates=candidates,
            current_training_idx=row["current_training_idx"] or 0,
            current_eval_idx=row["current_eval_idx"] or 0,
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            error=row["error"],
        )


def list_autotune_jobs() -> list[AutoTuneJob]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM autopilot_jobs ORDER BY started_at DESC"
        ).fetchall()
        results = []
        for row in rows:
            candidates = []
            if row["candidates"]:
                candidates = [AutoTuneCandidate(**c) for c in json.loads(row["candidates"])]
            results.append(
                AutoTuneJob(
                    id=row["id"],
                    dataset_id=row["dataset_id"],
                    benchmark_id=row["benchmark_id"],
                    base_config_id=row["base_config_id"],
                    status=AutoTuneStatus(row["status"]),
                    phase_message=row["phase_message"] or "",
                    top_k=row["top_k"],
                    candidates=candidates,
                    current_training_idx=row["current_training_idx"] or 0,
                    current_eval_idx=row["current_eval_idx"] or 0,
                    started_at=datetime.fromisoformat(row["started_at"]),
                    completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                    error=row["error"],
                )
            )
        return results


def delete_autotune_job(job_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM autopilot_jobs WHERE id = ?", (job_id,))
        conn.commit()
        return cursor.rowcount > 0

