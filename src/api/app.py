"""FastAPI application initialization."""
from __future__ import annotations

from contextlib import asynccontextmanager

import yaml
from fastapi import FastAPI

from ..models import (
    CausalLMDataConfig,
    CausalLMFullConfig,
    CausalLMModelConfig,
    CausalLMPeftConfig,
    CausalLMTrainingConfig,
    ConfigRecord,
    ExperimentType,
    MaskedLMDataConfig,
    MaskedLMFullConfig,
    MaskedLMModelConfig,
    MaskedLMTrainingConfig,
)
from ..storage import init_db, config_name_exists, save_config
from .helpers import CONFIGS_DIR, now


def _detect_config_type(payload: dict) -> ExperimentType:
    data_section = payload.get("data", {})
    if "system_prompt" in data_section or "template" in data_section:
        return ExperimentType.CAUSAL_LM
    return ExperimentType.MASKED_LM


def _seed_default_configs() -> None:
    """Seed default configs from YAML files if they don't exist in DB."""
    import uuid
    
    if not CONFIGS_DIR.exists():
        return
    
    for path in CONFIGS_DIR.glob("*.yaml"):
        config_name = path.stem
        
        if config_name_exists(config_name):
            continue
        
        try:
            with path.open("r") as f:
                payload = yaml.safe_load(f) or {}
            
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
            
            record = ConfigRecord(
                id=str(uuid.uuid4()),
                name=config_name,
                experiment_type=exp_type,
                config=config,
                created_at=now(),
            )
            save_config(record)
        except Exception:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _seed_default_configs()
    yield


app = FastAPI(
    title="AIP-C01 Prep API",
    description="API for dataset management and ML experiment runs",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


# Import and include routers
from .config_routes import router as config_router
from .dataset_routes import router as dataset_router
from .experiment_routes import router as experiment_router
from .benchmark_routes import router as benchmark_router
from .meta_routes import router as meta_router
from .autotune_routes import router as autotune_router

app.include_router(config_router)
app.include_router(dataset_router)
app.include_router(experiment_router)
app.include_router(benchmark_router)
app.include_router(meta_router)
app.include_router(autotune_router)

