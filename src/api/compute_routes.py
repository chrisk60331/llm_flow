"""Compute target API routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from ..models import (
    ComputeTarget,
    ComputeTargetCreate,
    ComputeTargetListResponse,
    ComputeTargetTestResponse,
)
from ..ssh_client import test_connection
from ..storage import (
    delete_compute_target,
    get_compute_target,
    list_compute_targets,
    save_compute_target,
    update_compute_target_status,
)
from .helpers import now

router = APIRouter(prefix="/compute", tags=["compute"])


@router.get("/targets", response_model=ComputeTargetListResponse)
def list_targets() -> ComputeTargetListResponse:
    """List all compute targets."""
    return ComputeTargetListResponse(targets=list_compute_targets())


@router.post("/targets", response_model=ComputeTarget)
def create_target(request: ComputeTargetCreate) -> ComputeTarget:
    """Create a new compute target."""
    if request.auth_type == "key" and not request.ssh_key_path:
        raise HTTPException(
            status_code=400,
            detail="ssh_key_path is required for key authentication",
        )
    if request.auth_type == "password" and not request.ssh_password:
        raise HTTPException(
            status_code=400,
            detail="ssh_password is required for password authentication",
        )

    target = ComputeTarget(
        id=str(uuid.uuid4()),
        name=request.name,
        ssh_host=request.ssh_host,
        ssh_port=request.ssh_port,
        ssh_user=request.ssh_user,
        auth_type=request.auth_type,
        ssh_key_path=request.ssh_key_path,
        ssh_password=request.ssh_password,
        remote_work_dir=request.remote_work_dir,
        created_at=now(),
        status="unknown",
    )
    save_compute_target(target)
    return target


@router.get("/targets/{target_id}", response_model=ComputeTarget)
def get_target(target_id: str) -> ComputeTarget:
    """Get a compute target by ID."""
    target = get_compute_target(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Compute target not found")
    return target


@router.delete("/targets/{target_id}")
def delete_target(target_id: str) -> dict[str, str]:
    """Delete a compute target."""
    target = delete_compute_target(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Compute target not found")
    return {"status": "deleted", "target_id": target_id}


@router.post("/targets/{target_id}/test", response_model=ComputeTargetTestResponse)
def test_target_connection(target_id: str) -> ComputeTargetTestResponse:
    """Test SSH connection to a compute target."""
    target = get_compute_target(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Compute target not found")

    success, message, python_version = test_connection(target)

    status = "connected" if success else "failed"
    update_compute_target_status(target_id, status, message)

    return ComputeTargetTestResponse(
        success=success,
        message=message,
        python_version=python_version,
    )

