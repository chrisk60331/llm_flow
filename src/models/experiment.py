"""Experiment-related Pydantic models."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .config import CausalLMFullConfig, MaskedLMFullConfig
from .enums import ExperimentStatus, ExperimentType


class ExperimentResult(BaseModel):
    id: str
    experiment_type: ExperimentType
    status: ExperimentStatus
    dataset_id: str
    dataset_filename: str | None = None
    config_id: str
    config: MaskedLMFullConfig | CausalLMFullConfig | None = None  # Populated on read
    config_name: str | None = None  # Populated on read
    started_at: datetime
    completed_at: datetime | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    output_dir: str | None = None
    error: str | None = None
    # Auto-evaluation progress tracking
    auto_eval_total: int = Field(default=0, description="Total benchmarks to evaluate")
    auto_eval_completed: int = Field(default=0, description="Benchmarks completed so far")
    auto_eval_current: str | None = Field(default=None, description="Name of benchmark currently running")


class ExperimentListResponse(BaseModel):
    experiments: list[ExperimentResult]


class ExperimentStartResponse(BaseModel):
    experiment_id: str
    status: ExperimentStatus
    message: str


# --- Experiment Comparison Models ---


class ExperimentComparisonItem(BaseModel):
    experiment_id: str
    experiment_type: ExperimentType
    dataset_filename: str | None
    started_at: datetime
    status: ExperimentStatus
    config: dict[str, Any]
    bleu_scores: list[float] = Field(default_factory=list)
    rouge_scores: list[float] = Field(default_factory=list)
    eval_loss: float | None = None


class ExperimentComparisonResponse(BaseModel):
    experiments: list[ExperimentComparisonItem]
    config_diff: dict[str, dict[str, Any]]

