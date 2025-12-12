"""Pydantic models for API requests and responses."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, PositiveFloat, PositiveInt


class ExperimentType(str, Enum):
    MASKED_LM = "masked_lm"
    CAUSAL_LM = "causal_lm"


class ExperimentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# --- Dataset Models ---


class DatasetInfo(BaseModel):
    id: str
    filename: str
    path: str
    columns: list[str]
    row_count: int
    uploaded_at: datetime


class DatasetListResponse(BaseModel):
    datasets: list[DatasetInfo]


# --- Config File Models ---


class ConfigFileInfo(BaseModel):
    name: str
    path: str
    experiment_type: ExperimentType
    model_name: str
    dataset_path: str


class ConfigFileListResponse(BaseModel):
    configs: list[ConfigFileInfo]


# --- Masked LM Config Models ---


class MaskedLMDataConfig(BaseModel):
    text_fields: tuple[str, ...] = Field(
        default=("question", "answer_tolkien"),
        description="Columns to concatenate for training",
    )
    separator: str = Field(default="\n\n")
    validation_split: PositiveFloat = Field(default=0.2)
    seed: PositiveInt = Field(default=42)
    max_length: PositiveInt = Field(default=256)


class MaskedLMModelConfig(BaseModel):
    pretrained_model_name: str = Field(default="distilbert-base-uncased")
    freeze_embedding: bool = Field(default=False)
    freeze_encoder_layers: int = Field(default=0, ge=0, le=6)


class MaskedLMTrainingConfig(BaseModel):
    num_train_epochs: PositiveFloat = Field(default=3.0)
    per_device_train_batch_size: PositiveInt = Field(default=8)
    per_device_eval_batch_size: PositiveInt = Field(default=8)
    learning_rate: PositiveFloat = Field(default=5e-5)
    weight_decay: float = Field(default=0.01)
    warmup_ratio: float = Field(default=0.0, ge=0.0)
    logging_steps: PositiveInt = Field(default=10)
    eval_steps: PositiveInt = Field(default=50)
    save_steps: PositiveInt = Field(default=200)
    save_total_limit: PositiveInt = Field(default=2)
    gradient_accumulation_steps: PositiveInt = Field(default=1)
    max_steps: int = Field(default=-1)


class MaskedLMFullConfig(BaseModel):
    data: MaskedLMDataConfig = Field(default_factory=MaskedLMDataConfig)
    model: MaskedLMModelConfig = Field(default_factory=MaskedLMModelConfig)
    training: MaskedLMTrainingConfig = Field(default_factory=MaskedLMTrainingConfig)


class MaskedLMRequest(BaseModel):
    dataset_id: str = Field(description="ID of uploaded dataset to use")
    config: MaskedLMFullConfig = Field(default_factory=MaskedLMFullConfig)


# --- Causal LM Config Models ---


class CausalLMDataConfig(BaseModel):
    question_field: str = Field(default="question")
    answer_field: str = Field(default="answer_tolkien")
    system_prompt: str = Field(
        default="You are an AI assistant.",
        description="System prompt for the model",
    )
    template: str = Field(
        default="<|system|>\n{system_prompt}\n</s>\n<|user|>\n{question}\n</s>\n<|assistant|>\n{answer}\n</s>",
        description="Template with {system_prompt}, {question}, {answer}",
    )
    validation_split: PositiveFloat = Field(default=0.2)
    seed: PositiveInt = Field(default=42)
    max_length: PositiveInt = Field(default=512)


class CausalLMModelConfig(BaseModel):
    pretrained_model_name: str = Field(default="TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    trust_remote_code: bool = Field(default=False)
    pad_token_override: str | None = Field(default="</s>")


class CausalLMPeftConfig(BaseModel):
    enabled: bool = Field(default=False)
    r: PositiveInt = Field(default=8)
    lora_alpha: PositiveInt = Field(default=16)
    lora_dropout: float = Field(default=0.05)
    bias: Literal["none", "lora_only", "all"] = Field(default="none")
    target_modules: tuple[str, ...] = Field(
        default=("q_proj", "k_proj", "v_proj", "o_proj")
    )


class CausalLMTrainingConfig(BaseModel):
    num_train_epochs: PositiveFloat = Field(default=3.0)
    per_device_train_batch_size: PositiveInt = Field(default=1)
    per_device_eval_batch_size: PositiveInt = Field(default=1)
    learning_rate: PositiveFloat = Field(default=2e-5)
    weight_decay: float = Field(default=0.0)
    warmup_ratio: float = Field(default=0.03, ge=0.0)
    logging_steps: PositiveInt = Field(default=10)
    eval_steps: PositiveInt = Field(default=50)
    save_steps: PositiveInt = Field(default=200)
    save_total_limit: PositiveInt = Field(default=2)
    gradient_accumulation_steps: PositiveInt = Field(default=8)
    max_steps: int = Field(default=-1)
    lr_scheduler_type: str = Field(default="cosine")
    gradient_checkpointing: bool = Field(default=True)
    bf16: bool = Field(default=False)
    fp16: bool = Field(default=True)


class CausalLMFullConfig(BaseModel):
    data: CausalLMDataConfig = Field(default_factory=CausalLMDataConfig)
    model: CausalLMModelConfig = Field(default_factory=CausalLMModelConfig)
    training: CausalLMTrainingConfig = Field(default_factory=CausalLMTrainingConfig)
    peft: CausalLMPeftConfig = Field(default_factory=CausalLMPeftConfig)


class CausalLMRequest(BaseModel):
    dataset_id: str = Field(description="ID of uploaded dataset to use")
    config: CausalLMFullConfig = Field(default_factory=CausalLMFullConfig)


# --- Experiment Result Models ---


class ExperimentResult(BaseModel):
    id: str
    experiment_type: ExperimentType
    status: ExperimentStatus
    dataset_id: str
    dataset_filename: str | None = None
    config: MaskedLMFullConfig | CausalLMFullConfig
    started_at: datetime
    completed_at: datetime | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    output_dir: str | None = None
    error: str | None = None


class ExperimentListResponse(BaseModel):
    experiments: list[ExperimentResult]


class ExperimentStartResponse(BaseModel):
    experiment_id: str
    status: ExperimentStatus
    message: str


# --- Benchmark Models ---


class BenchmarkStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Benchmark(BaseModel):
    id: str
    name: str
    question: str
    gold_answer: str
    created_at: datetime


class BenchmarkCreateRequest(BaseModel):
    name: str = Field(description="Name for this benchmark")
    question: str = Field(description="The question to ask the model")
    gold_answer: str = Field(description="The expected/gold standard answer")


class BenchmarkListResponse(BaseModel):
    benchmarks: list[Benchmark]


class BenchmarkEvalResult(BaseModel):
    id: str
    benchmark_id: str
    benchmark_name: str
    experiment_id: str
    question: str
    gold_answer: str
    model_answer: str
    bleu_score: float
    status: BenchmarkStatus
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


class BenchmarkEvalRequest(BaseModel):
    experiment_id: str = Field(description="Experiment ID to evaluate")
    max_new_tokens: PositiveInt = Field(default=128)
    temperature: PositiveFloat = Field(default=0.7)
    top_p: PositiveFloat = Field(default=0.9)


class BenchmarkEvalStartResponse(BaseModel):
    eval_id: str
    status: BenchmarkStatus
    message: str


class BenchmarkEvalListResponse(BaseModel):
    evaluations: list[BenchmarkEvalResult]


# --- Evaluation Comparison Models ---


class EvaluationComparisonItem(BaseModel):
    eval_id: str
    experiment_id: str
    benchmark_name: str
    question: str
    model_name: str
    dataset_filename: str
    bleu_score: float
    learning_rate: float
    num_epochs: float
    batch_size: int
    lora_r: int | None = None
    lora_alpha: int | None = None
    completed_at: datetime | None = None


class EvaluationComparisonResponse(BaseModel):
    evaluations: list[EvaluationComparisonItem]
