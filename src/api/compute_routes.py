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


@router.post("/targets/{target_id}/provision")
def provision_target(target_id: str) -> dict:
    """Provision a compute target by installing dependencies and syncing code.
    
    Steps:
    1. Install uv if not present
    2. Create virtual environment
    3. Sync pyproject.toml and install dependencies
    4. Sync source code
    """
    from ..ssh_client import SSHClient
    from pathlib import Path
    
    target = get_compute_target(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Compute target not found")

    repo_root = Path(__file__).resolve().parents[2]
    remote_work_dir = target.remote_work_dir
    logs = []

    try:
        with SSHClient(target) as client:
            # Create work directory
            logs.append("Creating work directory...")
            client.mkdir_p(remote_work_dir)

            # Check/install uv
            logs.append("Checking for uv...")
            exit_code, stdout, _ = client.run_command("which uv || echo 'not found'")
            if "not found" in stdout or exit_code != 0:
                logs.append("Installing uv...")
                exit_code, stdout, stderr = client.run_command(
                    "curl -LsSf https://astral.sh/uv/install.sh | sh",
                    timeout=120,
                )
                if exit_code != 0:
                    raise HTTPException(status_code=500, detail=f"Failed to install uv: {stderr}")
                logs.append("uv installed successfully")
            else:
                logs.append("uv already installed")

            # Sync pyproject.toml
            logs.append("Syncing pyproject.toml...")
            pyproject_path = repo_root / "pyproject.toml"
            if pyproject_path.exists():
                client.upload_file(pyproject_path, f"{remote_work_dir}/pyproject.toml")
                logs.append("pyproject.toml uploaded")
            else:
                logs.append("Warning: pyproject.toml not found locally")

            # Create venv and install dependencies
            logs.append("Creating virtual environment and installing dependencies...")
            # Use $HOME/.local/bin/uv in case it's not in PATH yet
            uv_cmd = "~/.local/bin/uv"
            exit_code, stdout, stderr = client.run_command(
                f"cd {remote_work_dir} && ({uv_cmd} venv .venv 2>/dev/null || {uv_cmd} venv .venv) && "
                f"{uv_cmd} pip install -e . 2>&1",
                timeout=600,
            )
            if exit_code != 0:
                # Try with plain uv if ~/.local/bin/uv doesn't work
                exit_code, stdout, stderr = client.run_command(
                    f"cd {remote_work_dir} && (uv venv .venv 2>/dev/null || uv venv .venv) && "
                    f"uv pip install -e . 2>&1",
                    timeout=600,
                )
                if exit_code != 0:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create venv/install deps: {stderr or stdout}",
                    )
            logs.append("Dependencies installed")

            # Sync source code
            logs.append("Syncing source code...")
            src_dir = repo_root / "src"
            if src_dir.exists():
                client.upload_directory(src_dir, f"{remote_work_dir}/src")
                logs.append("Source code synced")
            else:
                logs.append("Warning: src directory not found locally")

            # Create data directories
            logs.append("Creating data directories...")
            client.mkdir_p(f"{remote_work_dir}/data/uploads")
            client.mkdir_p(f"{remote_work_dir}/data/plugins")
            client.mkdir_p(f"{remote_work_dir}/artifacts")
            logs.append("Data directories created")

            # Verify installation
            logs.append("Verifying installation...")
            exit_code, stdout, stderr = client.run_command(
                f"cd {remote_work_dir} && .venv/bin/python -c 'import pydantic; print(pydantic.__version__)'",
                timeout=30,
            )
            if exit_code == 0:
                logs.append(f"Pydantic version: {stdout.strip()}")
            else:
                logs.append(f"Warning: Could not verify pydantic: {stderr}")

        update_compute_target_status(target_id, "provisioned", "Environment provisioned successfully")
        
        return {
            "success": True,
            "message": "Environment provisioned successfully",
            "logs": logs,
        }

    except HTTPException:
        raise
    except Exception as e:
        update_compute_target_status(target_id, "failed", f"Provisioning failed: {e}")
        raise HTTPException(status_code=500, detail=f"Provisioning failed: {e}")

