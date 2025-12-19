"""Compute target storage operations."""
from __future__ import annotations

from datetime import datetime, timezone

from ..models import ComputeTarget
from .database import get_connection


def save_compute_target(target: ComputeTarget) -> None:
    """Insert a compute target. Compute targets are immutable (except status/active)."""
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT 1 FROM compute_targets WHERE id = ?",
            (target.id,),
        ).fetchone()
        if existing:
            raise ValueError(f"Compute target already exists: {target.id}")

        conn.execute(
            """
            INSERT INTO compute_targets
            (id, name, ssh_host, ssh_port, ssh_user, auth_type, ssh_key_path, ssh_password,
             remote_work_dir, created_at, active, last_tested_at, status, status_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                1 if target.active else 0,
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


def list_compute_targets(*, include_inactive: bool = False) -> list[ComputeTarget]:
    """List compute targets."""
    with get_connection() as conn:
        if include_inactive:
            rows = conn.execute(
                "SELECT * FROM compute_targets ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM compute_targets WHERE active = 1 ORDER BY created_at DESC"
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


def set_compute_target_active(target_id: str, *, active: bool) -> None:
    """Set compute target active flag."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE compute_targets SET active = ? WHERE id = ?",
            (1 if active else 0, target_id),
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
        active=bool(row["active"]),
        last_tested_at=(
            datetime.fromisoformat(row["last_tested_at"])
            if row["last_tested_at"]
            else None
        ),
        status=row["status"],
        status_message=row["status_message"],
    )

