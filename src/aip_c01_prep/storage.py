"""SQLite storage for persistent data."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Generator

import pandas as pd

from .meta_features import MetaFeatureVector
from .models import (
    AutoTuneCandidate,
    AutoTuneJob,
    AutoTuneStatus,
    Benchmark,
    BenchmarkEvalResult,
    BenchmarkStatus,
    CausalLMFullConfig,
    ConfigRecord,
    ConfigWithMetrics,
    DatasetInfo,
    ExperimentResult,
    ExperimentStatus,
    ExperimentType,
    MaskedLMFullConfig,
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

            CREATE TABLE IF NOT EXISTS configs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                experiment_type TEXT NOT NULL,
                config_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                experiment_type TEXT NOT NULL,
                status TEXT NOT NULL,
                dataset_id TEXT NOT NULL,
                dataset_filename TEXT,
                config_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                metrics TEXT,
                output_dir TEXT,
                error TEXT,
                FOREIGN KEY (config_id) REFERENCES configs(id)
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
                rouge_score REAL NOT NULL DEFAULT 0.0,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS meta_features (
                experiment_id TEXT PRIMARY KEY,
                features TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS optimization_jobs (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                candidates TEXT,
                best_config TEXT,
                message TEXT,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS autopilot_jobs (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                benchmark_id TEXT NOT NULL,
                base_config_id TEXT,
                status TEXT NOT NULL,
                phase_message TEXT,
                top_k INTEGER NOT NULL,
                candidates TEXT,
                current_training_idx INTEGER DEFAULT 0,
                current_eval_idx INTEGER DEFAULT 0,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                error TEXT
            );
        """)
        conn.commit()
    _migrate_experiments_to_config_id()
    _migrate_benchmark_evals_add_rouge()
    _scan_existing_uploads()


def _migrate_experiments_to_config_id() -> None:
    """Migrate old experiments with embedded config to new config_id schema."""
    import uuid
    with get_connection() as conn:
        # Check current schema
        cursor = conn.execute("PRAGMA table_info(experiments)")
        columns = {row["name"] for row in cursor.fetchall()}
        
        has_old_config = "config" in columns
        has_new_config_id = "config_id" in columns
        
        if has_old_config and not has_new_config_id:
            # Old schema only - need full migration
            # SQLite doesn't support DROP COLUMN easily, so we recreate the table
            
            # Get all existing experiments
            rows = conn.execute("SELECT * FROM experiments").fetchall()
            
            # Drop old table and create new one
            conn.execute("DROP TABLE experiments")
            conn.execute("""
                CREATE TABLE experiments (
                    id TEXT PRIMARY KEY,
                    experiment_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    dataset_id TEXT NOT NULL,
                    dataset_filename TEXT,
                    config_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    metrics TEXT,
                    output_dir TEXT,
                    error TEXT,
                    FOREIGN KEY (config_id) REFERENCES configs(id)
                )
            """)
            
            # Migrate data
            for row in rows:
                exp_id = row["id"]
                exp_type = ExperimentType(row["experiment_type"])
                config_json = row["config"]
                
                if not config_json:
                    continue
                
                # Create a config record for this experiment
                config_id = str(uuid.uuid4())
                config_name = f"migrated_{exp_id[:8]}"
                
                conn.execute(
                    """
                    INSERT OR IGNORE INTO configs (id, name, experiment_type, config_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (config_id, config_name, exp_type.value, config_json, datetime.now(timezone.utc).isoformat()),
                )
                
                # Insert experiment with new schema
                conn.execute(
                    """
                    INSERT INTO experiments 
                    (id, experiment_type, status, dataset_id, dataset_filename, config_id, started_at, completed_at, metrics, output_dir, error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        row["experiment_type"],
                        row["status"],
                        row["dataset_id"],
                        row["dataset_filename"],
                        config_id,
                        row["started_at"],
                        row["completed_at"],
                        row["metrics"],
                        row["output_dir"],
                        row["error"],
                    ),
                )
            
            conn.commit()
        
        elif has_old_config and has_new_config_id:
            # Both columns exist (partial migration) - need to complete migration
            # Get experiments that still have old config but no config_id
            rows = conn.execute(
                "SELECT * FROM experiments WHERE config_id IS NULL AND config IS NOT NULL"
            ).fetchall()
            
            for row in rows:
                exp_id = row["id"]
                exp_type = ExperimentType(row["experiment_type"])
                config_json = row["config"]
                
                if not config_json:
                    continue
                
                config_id = str(uuid.uuid4())
                config_name = f"migrated_{exp_id[:8]}"
                
                conn.execute(
                    """
                    INSERT OR IGNORE INTO configs (id, name, experiment_type, config_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (config_id, config_name, exp_type.value, config_json, datetime.now(timezone.utc).isoformat()),
                )
                
                conn.execute(
                    "UPDATE experiments SET config_id = ? WHERE id = ?",
                    (config_id, exp_id),
                )
            
            conn.commit()
            
            # Now recreate the table without the old config column
            rows = conn.execute("SELECT * FROM experiments").fetchall()
            
            conn.execute("DROP TABLE experiments")
            conn.execute("""
                CREATE TABLE experiments (
                    id TEXT PRIMARY KEY,
                    experiment_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    dataset_id TEXT NOT NULL,
                    dataset_filename TEXT,
                    config_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    metrics TEXT,
                    output_dir TEXT,
                    error TEXT,
                    FOREIGN KEY (config_id) REFERENCES configs(id)
                )
            """)
            
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO experiments 
                    (id, experiment_type, status, dataset_id, dataset_filename, config_id, started_at, completed_at, metrics, output_dir, error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        row["experiment_type"],
                        row["status"],
                        row["dataset_id"],
                        row["dataset_filename"],
                        row["config_id"],
                        row["started_at"],
                        row["completed_at"],
                        row["metrics"],
                        row["output_dir"],
                        row["error"],
                    ),
                )
            
            conn.commit()


def _migrate_benchmark_evals_add_rouge() -> None:
    """Add rouge_score column to benchmark_evals if it doesn't exist."""
    with get_connection() as conn:
        cursor = conn.execute("PRAGMA table_info(benchmark_evals)")
        columns = {row["name"] for row in cursor.fetchall()}
        if "rouge_score" not in columns:
            conn.execute("ALTER TABLE benchmark_evals ADD COLUMN rouge_score REAL NOT NULL DEFAULT 0.0")
            conn.commit()


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


# --- Config operations ---


def _deserialize_config(config_str: str, exp_type: ExperimentType):
    data = json.loads(config_str)
    if exp_type == ExperimentType.CAUSAL_LM:
        return CausalLMFullConfig(**data)
    return MaskedLMFullConfig(**data)


def _serialize_config(config) -> str:
    return json.dumps(config.model_dump())


def save_config(config: ConfigRecord) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO configs (id, name, experiment_type, config_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                config.id,
                config.name,
                config.experiment_type.value,
                json.dumps(config.config.model_dump()),
                config.created_at.isoformat(),
            ),
        )
        conn.commit()


def get_config(config_id: str) -> ConfigRecord | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM configs WHERE id = ?", (config_id,)).fetchone()
        if not row:
            return None
        exp_type = ExperimentType(row["experiment_type"])
        return ConfigRecord(
            id=row["id"],
            name=row["name"],
            experiment_type=exp_type,
            config=_deserialize_config(row["config_json"], exp_type),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


def get_config_by_name(name: str) -> ConfigRecord | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM configs WHERE name = ?", (name,)).fetchone()
        if not row:
            return None
        exp_type = ExperimentType(row["experiment_type"])
        return ConfigRecord(
            id=row["id"],
            name=row["name"],
            experiment_type=exp_type,
            config=_deserialize_config(row["config_json"], exp_type),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


def list_configs() -> list[ConfigRecord]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM configs ORDER BY created_at DESC").fetchall()
        results = []
        for row in rows:
            exp_type = ExperimentType(row["experiment_type"])
            results.append(
                ConfigRecord(
                    id=row["id"],
                    name=row["name"],
                    experiment_type=exp_type,
                    config=_deserialize_config(row["config_json"], exp_type),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return results


def list_configs_with_metrics() -> list[ConfigWithMetrics]:
    """List all configs with their associated experiment metrics."""
    with get_connection() as conn:
        # Get all configs
        config_rows = conn.execute("SELECT * FROM configs ORDER BY created_at DESC").fetchall()
        
        results = []
        for row in config_rows:
            config_id = row["id"]
            exp_type = ExperimentType(row["experiment_type"])
            
            # Get experiment count and avg train loss for this config
            exp_stats = conn.execute(
                """
                SELECT 
                    COUNT(*) as count,
                    AVG(CASE WHEN json_extract(metrics, '$.eval_loss') IS NOT NULL 
                        THEN CAST(json_extract(metrics, '$.eval_loss') AS REAL) END) as avg_loss
                FROM experiments 
                WHERE config_id = ? AND status = 'completed'
                """,
                (config_id,),
            ).fetchone()
            
            # Get avg BLEU from evaluations for experiments using this config
            bleu_stats = conn.execute(
                """
                SELECT AVG(be.bleu_score) as avg_bleu
                FROM benchmark_evals be
                JOIN experiments e ON be.experiment_id = e.id
                WHERE e.config_id = ? AND be.status = 'completed'
                """,
                (config_id,),
            ).fetchone()
            
            results.append(
                ConfigWithMetrics(
                    id=config_id,
                    name=row["name"],
                    experiment_type=exp_type,
                    config=_deserialize_config(row["config_json"], exp_type),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    experiment_count=exp_stats["count"] or 0,
                    avg_train_loss=exp_stats["avg_loss"],
                    avg_bleu=bleu_stats["avg_bleu"] if bleu_stats else None,
                )
            )
        return results


def delete_config(config_id: str) -> ConfigRecord | None:
    config = get_config(config_id)
    if config:
        with get_connection() as conn:
            conn.execute("DELETE FROM configs WHERE id = ?", (config_id,))
            conn.commit()
    return config


def config_name_exists(name: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM configs WHERE name = ?", (name,)).fetchone()
        return row is not None


# --- Experiment operations ---


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
        
        # Load config record
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
            (id, benchmark_id, benchmark_name, experiment_id, question, gold_answer, model_answer, bleu_score, rouge_score, status, started_at, completed_at, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                eval_result.rouge_score,
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
            rouge_score=row["rouge_score"] or 0.0,
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
                rouge_score=row["rouge_score"] or 0.0,
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
                rouge_score=row["rouge_score"] or 0.0,
                status=BenchmarkStatus(row["status"]),
                started_at=datetime.fromisoformat(row["started_at"]),
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                error=row["error"],
            )
            for row in rows
        ]


def delete_benchmark_eval(eval_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM benchmark_evals WHERE id = ?", (eval_id,))
        conn.commit()
        return cursor.rowcount > 0


# --- Meta Features operations ---


def save_meta_features(features: MetaFeatureVector) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO meta_features (experiment_id, features, created_at)
            VALUES (?, ?, ?)
            """,
            (
                features.experiment_id,
                features.model_dump_json(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()


def get_meta_features(experiment_id: str) -> MetaFeatureVector | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM meta_features WHERE experiment_id = ?",
            (experiment_id,),
        ).fetchone()
        if not row:
            return None
        return MetaFeatureVector.model_validate_json(row["features"])


def list_meta_features() -> list[MetaFeatureVector]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM meta_features ORDER BY created_at DESC"
        ).fetchall()
        return [MetaFeatureVector.model_validate_json(row["features"]) for row in rows]


def delete_meta_features(experiment_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM meta_features WHERE experiment_id = ?",
            (experiment_id,),
        )
        conn.commit()
        return cursor.rowcount > 0


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
