"""Config API routes."""
from __future__ import annotations

import uuid
from pathlib import Path

import yaml
from fastapi import APIRouter, File, HTTPException, UploadFile

from ..models import (
    CausalLMDataConfig,
    CausalLMFullConfig,
    CausalLMModelConfig,
    CausalLMPeftConfig,
    CausalLMTrainingConfig,
    ConfigCreateRequest,
    ConfigListResponse,
    ConfigRecord,
    ExperimentType,
    MaskedLMDataConfig,
    MaskedLMFullConfig,
    MaskedLMModelConfig,
    MaskedLMTrainingConfig,
)
from ..storage import (
    config_name_exists,
    delete_config as storage_delete_config,
    get_config,
    list_configs_with_metrics,
    save_config,
)
from .helpers import generate_friendly_name, now

router = APIRouter(tags=["configs"])


def _detect_config_type(payload: dict) -> ExperimentType:
    data_section = payload.get("data", {})
    if "system_prompt" in data_section or "template" in data_section:
        return ExperimentType.CAUSAL_LM
    return ExperimentType.MASKED_LM


@router.get("/configs", response_model=ConfigListResponse)
def list_configs() -> ConfigListResponse:
    """List all configs from database with associated metrics."""
    return ConfigListResponse(configs=list_configs_with_metrics())


@router.get("/configs/by-type/{experiment_type}", response_model=ConfigListResponse)
def list_configs_by_type(experiment_type: str) -> ConfigListResponse:
    """List configs filtered by experiment type."""
    target_type = ExperimentType(experiment_type)
    all_configs = list_configs_with_metrics()
    filtered = [c for c in all_configs if c.experiment_type == target_type]
    return ConfigListResponse(configs=filtered)


@router.get("/configs/{config_id}", response_model=ConfigRecord)
def get_config_by_id(config_id: str) -> ConfigRecord:
    """Get a single config by ID."""
    config = get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.post("/configs", response_model=ConfigRecord)
def create_config(request: ConfigCreateRequest) -> ConfigRecord:
    """Create a new config in the database."""
    if isinstance(request.config, CausalLMFullConfig):
        exp_type = ExperimentType.CAUSAL_LM
    else:
        exp_type = ExperimentType.MASKED_LM
    
    name = request.name or generate_friendly_name()
    
    if config_name_exists(name):
        name = f"{name}-{uuid.uuid4().hex[:4]}"
    
    record = ConfigRecord(
        id=str(uuid.uuid4()),
        name=name,
        experiment_type=exp_type,
        config=request.config,
        created_at=now(),
    )
    save_config(record)
    return record


@router.post("/configs/upload", response_model=ConfigRecord)
def upload_config(file: UploadFile = File(...), name: str | None = None) -> ConfigRecord:
    """Upload a YAML config file and create a config record."""
    if not file.filename or not file.filename.endswith((".yaml", ".yml")):
        raise HTTPException(status_code=400, detail="Only YAML files are supported")
    
    content = file.file.read().decode("utf-8")
    payload = yaml.safe_load(content) or {}
    
    exp_type = _detect_config_type(payload)
    
    if exp_type == ExperimentType.CAUSAL_LM:
        config = CausalLMFullConfig(
            data=CausalLMDataConfig(**payload.get("data", {})),
            model=CausalLMModelConfig(**payload.get("model", {})),
            training=CausalLMTrainingConfig(**payload.get("training", {})),
            peft=CausalLMPeftConfig(**payload.get("peft", {})) if payload.get("peft") else CausalLMPeftConfig(),
        )
    else:
        config = MaskedLMFullConfig(
            data=MaskedLMDataConfig(**payload.get("data", {})),
            model=MaskedLMModelConfig(**payload.get("model", {})),
            training=MaskedLMTrainingConfig(**payload.get("training", {})),
        )
    
    config_name = name or Path(file.filename).stem or generate_friendly_name()
    
    if config_name_exists(config_name):
        config_name = f"{config_name}-{uuid.uuid4().hex[:4]}"
    
    record = ConfigRecord(
        id=str(uuid.uuid4()),
        name=config_name,
        experiment_type=exp_type,
        config=config,
        created_at=now(),
    )
    save_config(record)
    return record


@router.delete("/configs/{config_id}")
def delete_config(config_id: str) -> dict[str, str]:
    """Delete a config from the database."""
    config = storage_delete_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"status": "deleted", "config_id": config_id}

