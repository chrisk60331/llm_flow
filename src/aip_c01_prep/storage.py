"""SQLite storage for persistent data."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pandas as pd

from .models import (
    Benchmark,
    BenchmarkEvalResult,
    BenchmarkStatus,
    DatasetInfo,
    ExperimentResult,
    ExperimentStatus,
    ExperimentType,
)

DB_PATH = Path("data/aip_prep.db")
UPLOAD_DIR = Path("data/uploads")


def _ensure_db_dir() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS datasets (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                columns TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                experiment_type TEXT NOT NULL,
                status TEXT NOT NULL,
                dataset_id TEXT NOT NULL,
                dataset_filename TEXT,
                config TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                metrics TEXT,
                output_dir TEXT,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS benchmarks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                question TEXT NOT NULL,
                gold_answer TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS benchmark_evals (
                id TEXT PRIMARY KEY,
                benchmark_id TEXT NOT NULL,
                benchmark_name TEXT NOT NULL,
                experiment_id TEXT NOT NULL,
                question TEXT NOT NULL,
                gold_answer TEXT NOT NULL,
                model_answer TEXT NOT NULL,
                bleu_score REAL NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                error TEXT
            );
        """)
        conn.commit()
    _scan_existing_uploads()


def _scan_existing_uploads() -> None:
    """Scan data/uploads for CSV files and add missing ones to the database."""
    if not UPLOAD_DIR.exists():
        return

    existing_ids = {d.id for d in list_datasets()}

    for path in UPLOAD_DIR.glob("*.csv"):
        parts = path.stem.split("_", 1)
        if len(parts) != 2:
            continue

        dataset_id, original_filename = parts
        if dataset_id in existing_ids:
            continue

        try:
            frame = pd.read_csv(path)
            info = DatasetInfo(
                id=dataset_id,
                filename=f"{original_filename}.csv",
                path=str(path),
                columns=list(frame.columns),
                row_count=len(frame),
                uploaded_at=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
            )
            save_dataset(info)
        except Exception:
            continue


# --- Dataset operations ---


def save_dataset(info: DatasetInfo) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO datasets (id, filename, path, columns, row_count, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                info.id,
                info.filename,
                info.path,
                json.dumps(info.columns),
                info.row_count,
                info.uploaded_at.isoformat(),
            ),
        )
        conn.commit()


def get_dataset(dataset_id: str) -> DatasetInfo | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        if not row:
            return None
        return DatasetInfo(
            id=row["id"],
            filename=row["filename"],
            path=row["path"],
            columns=json.loads(row["columns"]),
            row_count=row["row_count"],
            uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
        )


def list_datasets() -> list[DatasetInfo]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM datasets ORDER BY uploaded_at DESC").fetchall()
        return [
            DatasetInfo(
                id=row["id"],
                filename=row["filename"],
                path=row["path"],
                columns=json.loads(row["columns"]),
                row_count=row["row_count"],
                uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
            )
            for row in rows
        ]


def delete_dataset(dataset_id: str) -> DatasetInfo | None:
    info = get_dataset(dataset_id)
    if info:
        with get_connection() as conn:
            conn.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
            conn.commit()
    return info


# --- Experiment operations ---


def _serialize_config(config) -> str:
    return json.dumps(config.model_dump())


def _deserialize_config(config_str: str, exp_type: ExperimentType):
    from .models import CausalLMFullConfig, MaskedLMFullConfig

    data = json.loads(config_str)
    if exp_type == ExperimentType.CAUSAL_LM:
        return CausalLMFullConfig(**data)
    return MaskedLMFullConfig(**data)


def save_experiment(exp: ExperimentResult) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO experiments
            (id, experiment_type, status, dataset_id, dataset_filename, config, started_at, completed_at, metrics, output_dir, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exp.id,
                exp.experiment_type.value,
                exp.status.value,
                exp.dataset_id,
                exp.dataset_filename,
                _serialize_config(exp.config),
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
        return ExperimentResult(
            id=row["id"],
            experiment_type=exp_type,
            status=ExperimentStatus(row["status"]),
            dataset_id=row["dataset_id"],
            dataset_filename=row["dataset_filename"],
            config=_deserialize_config(row["config"], exp_type),
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            metrics=json.loads(row["metrics"]) if row["metrics"] else {},
            output_dir=row["output_dir"],
            error=row["error"],
        )


def list_experiments() -> list[ExperimentResult]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM experiments ORDER BY started_at DESC").fetchall()
        results = []
        for row in rows:
            exp_type = ExperimentType(row["experiment_type"])
            results.append(
                ExperimentResult(
                    id=row["id"],
                    experiment_type=exp_type,
                    status=ExperimentStatus(row["status"]),
                    dataset_id=row["dataset_id"],
                    dataset_filename=row["dataset_filename"],
                    config=_deserialize_config(row["config"], exp_type),
                    started_at=datetime.fromisoformat(row["started_at"]),
                    completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                    metrics=json.loads(row["metrics"]) if row["metrics"] else {},
                    output_dir=row["output_dir"],
                    error=row["error"],
                )
            )
        return results


# --- Benchmark operations ---


def save_benchmark(benchmark: Benchmark) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO benchmarks (id, name, question, gold_answer, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                benchmark.id,
                benchmark.name,
                benchmark.question,
                benchmark.gold_answer,
                benchmark.created_at.isoformat(),
            ),
        )
        conn.commit()


def get_benchmark(benchmark_id: str) -> Benchmark | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM benchmarks WHERE id = ?", (benchmark_id,)).fetchone()
        if not row:
            return None
        return Benchmark(
            id=row["id"],
            name=row["name"],
            question=row["question"],
            gold_answer=row["gold_answer"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


def list_benchmarks() -> list[Benchmark]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM benchmarks ORDER BY created_at DESC").fetchall()
        return [
            Benchmark(
                id=row["id"],
                name=row["name"],
                question=row["question"],
                gold_answer=row["gold_answer"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]


def delete_benchmark(benchmark_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM benchmarks WHERE id = ?", (benchmark_id,))
        conn.commit()
        return cursor.rowcount > 0


# --- Benchmark Eval operations ---


def save_benchmark_eval(eval_result: BenchmarkEvalResult) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO benchmark_evals
            (id, benchmark_id, benchmark_name, experiment_id, question, gold_answer, model_answer, bleu_score, status, started_at, completed_at, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                eval_result.id,
                eval_result.benchmark_id,
                eval_result.benchmark_name,
                eval_result.experiment_id,
                eval_result.question,
                eval_result.gold_answer,
                eval_result.model_answer,
                eval_result.bleu_score,
                eval_result.status.value,
                eval_result.started_at.isoformat(),
                eval_result.completed_at.isoformat() if eval_result.completed_at else None,
                eval_result.error,
            ),
        )
        conn.commit()


def get_benchmark_eval(eval_id: str) -> BenchmarkEvalResult | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM benchmark_evals WHERE id = ?", (eval_id,)).fetchone()
        if not row:
            return None
        return BenchmarkEvalResult(
            id=row["id"],
            benchmark_id=row["benchmark_id"],
            benchmark_name=row["benchmark_name"],
            experiment_id=row["experiment_id"],
            question=row["question"],
            gold_answer=row["gold_answer"],
            model_answer=row["model_answer"],
            bleu_score=row["bleu_score"],
            status=BenchmarkStatus(row["status"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            error=row["error"],
        )


def list_benchmark_evals() -> list[BenchmarkEvalResult]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM benchmark_evals ORDER BY started_at DESC").fetchall()
        return [
            BenchmarkEvalResult(
                id=row["id"],
                benchmark_id=row["benchmark_id"],
                benchmark_name=row["benchmark_name"],
                experiment_id=row["experiment_id"],
                question=row["question"],
                gold_answer=row["gold_answer"],
                model_answer=row["model_answer"],
                bleu_score=row["bleu_score"],
                status=BenchmarkStatus(row["status"]),
                started_at=datetime.fromisoformat(row["started_at"]),
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                error=row["error"],
            )
            for row in rows
        ]


def list_benchmark_evals_by_benchmark(benchmark_id: str) -> list[BenchmarkEvalResult]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM benchmark_evals WHERE benchmark_id = ? ORDER BY started_at DESC",
            (benchmark_id,),
        ).fetchall()
        return [
            BenchmarkEvalResult(
                id=row["id"],
                benchmark_id=row["benchmark_id"],
                benchmark_name=row["benchmark_name"],
                experiment_id=row["experiment_id"],
                question=row["question"],
                gold_answer=row["gold_answer"],
                model_answer=row["model_answer"],
                bleu_score=row["bleu_score"],
                status=BenchmarkStatus(row["status"]),
                started_at=datetime.fromisoformat(row["started_at"]),
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                error=row["error"],
            )
            for row in rows
        ]
