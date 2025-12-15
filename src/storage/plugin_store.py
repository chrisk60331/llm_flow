"""Plugin storage operations."""
from __future__ import annotations

import json
from datetime import datetime

from ..models import PluginKind, PluginRecord
from .database import get_connection


def save_plugin(plugin: PluginRecord) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO plugins
            (id, name, kind, filename, path, sha256, symbols_json, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plugin.id,
                plugin.name,
                plugin.kind.value,
                plugin.filename,
                plugin.path,
                plugin.sha256,
                json.dumps(plugin.symbols),
                plugin.uploaded_at.isoformat(),
            ),
        )
        conn.commit()


def get_plugin(plugin_id: str) -> PluginRecord | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM plugins WHERE id = ?", (plugin_id,)).fetchone()
        if not row:
            return None
        return PluginRecord(
            id=row["id"],
            name=row["name"],
            kind=PluginKind(row["kind"]),
            filename=row["filename"],
            path=row["path"],
            sha256=row["sha256"],
            symbols=json.loads(row["symbols_json"]) if row["symbols_json"] else {},
            uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
        )


def list_plugins() -> list[PluginRecord]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM plugins ORDER BY uploaded_at DESC"
        ).fetchall()
        return [
            PluginRecord(
                id=row["id"],
                name=row["name"],
                kind=PluginKind(row["kind"]),
                filename=row["filename"],
                path=row["path"],
                sha256=row["sha256"],
                symbols=json.loads(row["symbols_json"]) if row["symbols_json"] else {},
                uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
            )
            for row in rows
        ]


def delete_plugin(plugin_id: str) -> PluginRecord | None:
    plugin = get_plugin(plugin_id)
    if not plugin:
        return None
    with get_connection() as conn:
        conn.execute("DELETE FROM plugins WHERE id = ?", (plugin_id,))
        conn.commit()
    return plugin


