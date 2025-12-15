"""Database connection and initialization."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pandas as pd

from ..models import ExperimentType

DB_PATH = Path("data/aip_prep.db")
UPLOAD_DIR = Path("data/uploads")
PLUGINS_DIR = Path("data/plugins")


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

            CREATE TABLE IF NOT EXISTS plugins (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                symbols_json TEXT NOT NULL,
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
                max_new_tokens INTEGER NOT NULL DEFAULT 128,
                temperature REAL NOT NULL DEFAULT 0.7,
                top_p REAL NOT NULL DEFAULT 0.9,
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
    _migrate_experiments_add_custom_lightning_fields()
    _migrate_benchmark_evals_add_rouge()
    _migrate_benchmarks_add_inference_settings()
    _scan_existing_uploads()
    _scan_existing_plugins()


def _migrate_experiments_add_custom_lightning_fields() -> None:
    """Add custom-lightning plugin selection columns to experiments table if missing."""
    with get_connection() as conn:
        cursor = conn.execute("PRAGMA table_info(experiments)")
        columns = {row["name"] for row in cursor.fetchall()}

        # These are NULL for non-custom-lightning experiments.
        if "lightning_module_plugin_id" not in columns:
            conn.execute("ALTER TABLE experiments ADD COLUMN lightning_module_plugin_id TEXT")
        if "lightning_module_class_name" not in columns:
            conn.execute("ALTER TABLE experiments ADD COLUMN lightning_module_class_name TEXT")
        if "dataloaders_plugin_id" not in columns:
            conn.execute("ALTER TABLE experiments ADD COLUMN dataloaders_plugin_id TEXT")
        if "dataloaders_function_name" not in columns:
            conn.execute("ALTER TABLE experiments ADD COLUMN dataloaders_function_name TEXT")
        conn.commit()


def _migrate_experiments_to_config_id() -> None:
    """Migrate old experiments with embedded config to new config_id schema."""
    with get_connection() as conn:
        # Check current schema
        cursor = conn.execute("PRAGMA table_info(experiments)")
        columns = {row["name"] for row in cursor.fetchall()}
        
        has_old_config = "config" in columns
        has_new_config_id = "config_id" in columns
        
        if has_old_config and not has_new_config_id:
            # Old schema only - need full migration
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


def _migrate_benchmarks_add_inference_settings() -> None:
    """Add max_new_tokens, temperature, top_p columns to benchmarks if they don't exist."""
    with get_connection() as conn:
        cursor = conn.execute("PRAGMA table_info(benchmarks)")
        columns = {row["name"] for row in cursor.fetchall()}
        if "max_new_tokens" not in columns:
            conn.execute("ALTER TABLE benchmarks ADD COLUMN max_new_tokens INTEGER NOT NULL DEFAULT 128")
        if "temperature" not in columns:
            conn.execute("ALTER TABLE benchmarks ADD COLUMN temperature REAL NOT NULL DEFAULT 0.7")
        if "top_p" not in columns:
            conn.execute("ALTER TABLE benchmarks ADD COLUMN top_p REAL NOT NULL DEFAULT 0.9")
        conn.commit()


def _scan_existing_uploads() -> None:
    """Scan data/uploads for CSV files and add missing ones to the database."""
    # Import here to avoid circular import
    from .dataset_store import list_datasets, save_dataset
    from ..models import DatasetInfo
    
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


def _scan_existing_plugins() -> None:
    """Scan data/plugins for uploaded plugin .py files and add missing ones to the database."""
    import hashlib
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

    for path in PLUGINS_DIR.glob("*.py"):
        # Expected filename: <plugin_id>_<kind>_<original_filename>.py
        parts = path.name.split("_", 2)
        if len(parts) != 3:
            continue
        plugin_id, kind_str, original = parts
        if kind_str not in {"lightning_module", "dataloaders"}:
            continue

        try:
            content = path.read_bytes()
            sha256 = hashlib.sha256(content).hexdigest()
            uploaded_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()

            with get_connection() as conn:
                existing = conn.execute(
                    "SELECT 1 FROM plugins WHERE id = ?",
                    (plugin_id,),
                ).fetchone()
                if existing:
                    continue

                conn.execute(
                    """
                    INSERT INTO plugins (id, name, kind, filename, path, sha256, symbols_json, uploaded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plugin_id,
                        Path(original).stem,
                        kind_str,
                        original,
                        str(path),
                        sha256,
                        "{}",
                        uploaded_at,
                    ),
                )
                conn.commit()
        except Exception:
            continue

