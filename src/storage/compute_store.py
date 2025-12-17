"""Compute target storage operations."""
from __future__ import annotations

from datetime import datetime, timezone

from ..models import ComputeTarget
from .database import get_connection


def save_compute_target(target: ComputeTarget) -> None:
    """Save or update a compute target."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO compute_targets
            (id, name, ssh_host, ssh_port, ssh_user, auth_type, ssh_key_path, ssh_password,
             remote_work_dir, created_at, last_tested_at, status, status_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                target.id,
                target.name,
                target.ssh_host,
                target.ssh_port,
                target.ssh_user,
                target.auth_type,
                target.ssh_key_path,
                target.ssh_password,
                target.remote_work_dir,
                target.created_at.isoformat(),
                target.last_tested_at.isoformat() if target.last_tested_at else None,
                target.status,
                target.status_message,
            ),
        )
        conn.commit()


def get_compute_target(target_id: str) -> ComputeTarget | None:
    """Get a compute target by ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM compute_targets WHERE id = ?", (target_id,)
        ).fetchone()
        if not row:
            return None
        return _row_to_compute_target(row)


def list_compute_targets() -> list[ComputeTarget]:
    """List all compute targets."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM compute_targets ORDER BY created_at DESC"
        ).fetchall()
        return [_row_to_compute_target(row) for row in rows]


def delete_compute_target(target_id: str) -> ComputeTarget | None:
    """Delete a compute target by ID. Returns the deleted target or None."""
    target = get_compute_target(target_id)
    if not target:
        return None
    with get_connection() as conn:
        conn.execute("DELETE FROM compute_targets WHERE id = ?", (target_id,))
        conn.commit()
    return target


def update_compute_target_status(
    target_id: str,
    status: str,
    status_message: str | None = None,
) -> None:
    """Update the status of a compute target after a connection test."""
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE compute_targets
            SET status = ?, status_message = ?, last_tested_at = ?
            WHERE id = ?
            """,
            (status, status_message, datetime.now(timezone.utc).isoformat(), target_id),
        )
        conn.commit()


def _row_to_compute_target(row) -> ComputeTarget:
    """Convert a database row to a ComputeTarget model."""
    return ComputeTarget(
        id=row["id"],
        name=row["name"],
        ssh_host=row["ssh_host"],
        ssh_port=row["ssh_port"],
        ssh_user=row["ssh_user"],
        auth_type=row["auth_type"],
        ssh_key_path=row["ssh_key_path"],
        ssh_password=row["ssh_password"],
        remote_work_dir=row["remote_work_dir"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_tested_at=(
            datetime.fromisoformat(row["last_tested_at"])
            if row["last_tested_at"]
            else None
        ),
        status=row["status"],
        status_message=row["status_message"],
    )

