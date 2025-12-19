"""Compute target models for remote SSH execution."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ComputeTargetCreate(BaseModel):
    """Request to create a new compute target."""

    name: str = Field(..., description="Human-readable name for this compute target")
    ssh_host: str = Field(..., description="SSH hostname or IP address")
    ssh_port: int = Field(default=22, description="SSH port")
    ssh_user: str = Field(..., description="SSH username")
    auth_type: Literal["key", "password"] = Field(
        ..., description="Authentication method"
    )
    ssh_key_path: str | None = Field(
        default=None, description="Path to SSH private key file (for key auth)"
    )
    ssh_password: str | None = Field(
        default=None, description="SSH password (for password auth)"
    )
    remote_work_dir: str = Field(
        default="~/evalledger", description="Remote directory for code and artifacts"
    )


class ComputeTarget(ComputeTargetCreate):
    """Stored compute target with metadata."""

    id: str
    created_at: datetime
    active: bool = True
    last_tested_at: datetime | None = None
    status: Literal["unknown", "connected", "failed", "provisioned"] = "unknown"
    status_message: str | None = None


class ComputeTargetListResponse(BaseModel):
    """Response containing list of compute targets."""

    targets: list[ComputeTarget]


class ComputeTargetTestResponse(BaseModel):
    """Response from testing a compute target connection."""

    success: bool
    message: str
    python_version: str | None = None

