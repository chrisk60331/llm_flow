"""Config storage operations."""
from __future__ import annotations

import json
from datetime import datetime

from ..models import (
    CausalLMFullConfig,
    ConfigRecord,
    ConfigWithMetrics,
    ExperimentType,
    MaskedLMFullConfig,
)
from .database import get_connection


def _deserialize_config(config_str: str, exp_type: ExperimentType) -> MaskedLMFullConfig | CausalLMFullConfig:
    data = json.loads(config_str)
    if exp_type == ExperimentType.CAUSAL_LM:
        return CausalLMFullConfig(**data)
    return MaskedLMFullConfig(**data)


def _serialize_config(config: MaskedLMFullConfig | CausalLMFullConfig) -> str:
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
        config_rows = conn.execute("SELECT * FROM configs ORDER BY created_at DESC").fetchall()
        
        results = []
        for row in config_rows:
            config_id = row["id"]
            exp_type = ExperimentType(row["experiment_type"])
            
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

