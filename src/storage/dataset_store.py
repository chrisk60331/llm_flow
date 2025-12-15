"""Dataset storage operations."""
from __future__ import annotations

import json
from datetime import datetime

from ..models import DatasetInfo
from .database import get_connection


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

