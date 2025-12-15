"""Meta features storage operations."""
from __future__ import annotations

from datetime import datetime, timezone

from ..meta_features import MetaFeatureVector
from .database import get_connection


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

