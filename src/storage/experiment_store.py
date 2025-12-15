"""Experiment storage operations."""
from __future__ import annotations

import json
from datetime import datetime

from ..models import ExperimentResult, ExperimentStatus, ExperimentType
from .config_store import _deserialize_config, get_config
from .database import get_connection


def save_experiment(exp: ExperimentResult) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO experiments
            (id, experiment_type, status, dataset_id, dataset_filename, config_id, started_at, completed_at, metrics, output_dir, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exp.id,
                exp.experiment_type.value,
                exp.status.value,
                exp.dataset_id,
                exp.dataset_filename,
                exp.config_id,
                exp.started_at.isoformat(),
                exp.completed_at.isoformat() if exp.completed_at else None,
                json.dumps(exp.metrics) if exp.metrics else None,
                exp.output_dir,
                exp.error,
            ),
        )
        conn.commit()


def get_experiment(experiment_id: str) -> ExperimentResult | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM experiments WHERE id = ?", (experiment_id,)).fetchone()
        if not row:
            return None
        exp_type = ExperimentType(row["experiment_type"])
        config_id = row["config_id"]
        
        config_record = get_config(config_id) if config_id else None
        
        return ExperimentResult(
            id=row["id"],
            experiment_type=exp_type,
            status=ExperimentStatus(row["status"]),
            dataset_id=row["dataset_id"],
            dataset_filename=row["dataset_filename"],
            config_id=config_id,
            config=config_record.config if config_record else None,
            config_name=config_record.name if config_record else None,
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            metrics=json.loads(row["metrics"]) if row["metrics"] else {},
            output_dir=row["output_dir"],
            error=row["error"],
        )


def list_experiments() -> list[ExperimentResult]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT e.*, c.name as config_name, c.config_json
            FROM experiments e
            LEFT JOIN configs c ON e.config_id = c.id
            ORDER BY e.started_at DESC
            """
        ).fetchall()
        results = []
        for row in rows:
            exp_type = ExperimentType(row["experiment_type"])
            config = _deserialize_config(row["config_json"], exp_type) if row["config_json"] else None
            results.append(
                ExperimentResult(
                    id=row["id"],
                    experiment_type=exp_type,
                    status=ExperimentStatus(row["status"]),
                    dataset_id=row["dataset_id"],
                    dataset_filename=row["dataset_filename"],
                    config_id=row["config_id"],
                    config=config,
                    config_name=row["config_name"],
                    started_at=datetime.fromisoformat(row["started_at"]),
                    completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                    metrics=json.loads(row["metrics"]) if row["metrics"] else {},
                    output_dir=row["output_dir"],
                    error=row["error"],
                )
            )
        return results


def delete_experiment(experiment_id: str) -> ExperimentResult | None:
    exp = get_experiment(experiment_id)
    if exp:
        with get_connection() as conn:
            conn.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))
            conn.commit()
    return exp

