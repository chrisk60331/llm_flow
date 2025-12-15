"""Configuration-related Pydantic models."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, PositiveFloat, PositiveInt

from .custom_lightning import CustomLightningFullConfig
from .enums import ExperimentType


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
    early_stopping_patience: int | None = Field(default=None)
    early_stopping_metric: str = Field(default="eval_loss")
    early_stopping_greater_is_better: bool = Field(default=False)
    auto_evaluate: bool = Field(
        default=False,
        description="Run all available benchmarks after experiment completes",
    )


class MaskedLMFullConfig(BaseModel):
    data: MaskedLMDataConfig = Field(default_factory=MaskedLMDataConfig)
    model: MaskedLMModelConfig = Field(default_factory=MaskedLMModelConfig)
    training: MaskedLMTrainingConfig = Field(default_factory=MaskedLMTrainingConfig)


class MaskedLMRequest(BaseModel):
    dataset_id: str = Field(description="ID of uploaded dataset to use")
    config_id: str | None = Field(default=None, description="ID of existing config to use")
    config: MaskedLMFullConfig | None = Field(default=None, description="Config to create (creates new config record)")
    config_name: str | None = Field(default=None, description="Optional name for new config")


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
    early_stopping_patience: int | None = Field(default=None)
    early_stopping_metric: str = Field(default="eval_loss")
    early_stopping_greater_is_better: bool = Field(default=False)
    auto_evaluate: bool = Field(
        default=False,
        description="Run all available benchmarks after experiment completes",
    )


class CausalLMFullConfig(BaseModel):
    data: CausalLMDataConfig = Field(default_factory=CausalLMDataConfig)
    model: CausalLMModelConfig = Field(default_factory=CausalLMModelConfig)
    training: CausalLMTrainingConfig = Field(default_factory=CausalLMTrainingConfig)
    peft: CausalLMPeftConfig = Field(default_factory=CausalLMPeftConfig)


class CausalLMRequest(BaseModel):
    dataset_id: str = Field(description="ID of uploaded dataset to use")
    config_id: str | None = Field(default=None, description="ID of existing config to use")
    config: CausalLMFullConfig | None = Field(default=None, description="Config to create (creates new config record)")
    config_name: str | None = Field(default=None, description="Optional name for new config")


# --- Config Record Models (DB-stored configs) ---


class ConfigRecord(BaseModel):
    """A stored configuration in the database."""
    id: str
    name: str
    experiment_type: ExperimentType
    config: MaskedLMFullConfig | CausalLMFullConfig | CustomLightningFullConfig
    created_at: datetime


class ConfigWithMetrics(BaseModel):
    """Config record with associated experiment metrics."""
    id: str
    name: str
    experiment_type: ExperimentType
    config: MaskedLMFullConfig | CausalLMFullConfig | CustomLightningFullConfig
    created_at: datetime
    experiment_count: int = 0
    min_eval_loss: float | None = None
    avg_bleu: float | None = None


class ConfigListResponse(BaseModel):
    configs: list[ConfigWithMetrics]


class ConfigCreateRequest(BaseModel):
    name: str | None = None
    config: MaskedLMFullConfig | CausalLMFullConfig | CustomLightningFullConfig

