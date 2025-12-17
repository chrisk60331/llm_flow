"""AutoTune-related Pydantic models."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .enums import AutoTuneStatus


class AutoTuneCandidate(BaseModel):
    """A config candidate with prediction and results."""
    rank: int
    learning_rate: float
    lora_r: int
    batch_size: int
    num_epochs: int
    predicted_bleu: float
    experiment_id: str | None = None
    eval_id: str | None = None
    actual_bleu: float | None = None


class AutoTuneJob(BaseModel):
    """Tracks the full autotune pipeline state."""
    id: str
    dataset_id: str
    benchmark_id: str
    base_config_id: str | None = None
    status: AutoTuneStatus
    phase_message: str = ""
    top_k: int = 5
    candidates: list[AutoTuneCandidate] = Field(default_factory=list)
    current_training_idx: int = 0
    current_eval_idx: int = 0
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


class AutoTuneRequest(BaseModel):
    """Request to start autotune."""
    dataset_id: str
    benchmark_id: str | None = None  # If None, create from dataset
    benchmark_row_idx: int | None = None  # Row to use for benchmark if creating
    benchmark_question: str | None = None  # Manual question if no benchmark_id
    benchmark_answer: str | None = None  # Manual answer if no benchmark_id
    base_config_id: str | None = None  # Existing config to use as template
    question_field: str = "question"
    answer_field: str = "answer"
    top_k: int = Field(default=5, ge=1, le=10)
    probe_steps: int = Field(default=5, ge=1, le=50)
    compute_target_id: str | None = Field(default=None, description="Optional compute target for remote execution")


class AutoTuneStartResponse(BaseModel):
    job_id: str
    status: AutoTuneStatus
    message: str


class AutoTuneStatusResponse(BaseModel):
    job: AutoTuneJob
    message: str


class AutoTuneListResponse(BaseModel):
    jobs: list[AutoTuneJob]

