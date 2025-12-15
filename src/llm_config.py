from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Literal

import yaml
from pydantic import (
    BaseModel,
    Field,
    PositiveFloat,
    PositiveInt,
    model_validator,
)


class LLMDataConfig(BaseModel):
    """Configuration for turning Q&A rows into causal LM prompts."""

    csv_path: Path = Field(description="Absolute path to the training CSV.")
    question_field: str = Field(
        default="question",
        description="Column containing the user prompt.",
    )
    answer_field: str = Field(
        default="answer_tolkien",
        description="Column containing the desired assistant response.",
    )
    system_prompt: str = Field(
        description="Instruction injected ahead of every conversation.",
    )
    template: str = Field(
        description=(
            "Python format string with {system_prompt}, {question}, {answer} placeholders."
        ),
    )
    validation_split: PositiveFloat = Field(
        default=0.2, description="Fraction of rows reserved for evaluation."
    )
    seed: PositiveInt = Field(default=42, description="Reproducibility seed.")
    max_length: PositiveInt = Field(
        default=512,
        description="Tokenizer max_length for truncation/padding.",
    )

    _required_tokens: ClassVar[tuple[str, ...]] = (
        "{system_prompt}",
        "{question}",
        "{answer}",
    )

    @model_validator(mode="after")
    def _validate(self) -> "LLMDataConfig":
        if not self.csv_path.exists():
            msg = f"csv_path={self.csv_path} does not exist."
            raise FileNotFoundError(msg)
        if not 0 < self.validation_split < 1:
            msg = "validation_split must be inside (0, 1)."
            raise ValueError(msg)
        missing_tokens = [
            token for token in self._required_tokens if token not in self.template
        ]
        if missing_tokens:
            msg = f"template is missing tokens: {missing_tokens}"
            raise ValueError(msg)
        return self


class LLMModelConfig(BaseModel):
    """LLM-centric parameters."""

    pretrained_model_name: str = Field(
        default="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        description="HF repo id or local path for the base model.",
    )
    trust_remote_code: bool = Field(
        default=False,
        description="Set true when the model repo ships custom code.",
    )
    pad_token_override: str | None = Field(
        default=None,
        description="Optional token to register as pad_token when the tokenizer lacks one.",
    )


class LLMPeftConfig(BaseModel):
    """Optional LoRA/PEFT adapters."""

    enabled: bool = Field(
        default=False,
        description="Toggle to wrap the base model with PEFT adapters.",
    )
    r: PositiveInt = Field(default=8, description="LoRA rank.")
    lora_alpha: PositiveInt = Field(default=16, description="LoRA scaling factor.")
    lora_dropout: float = Field(default=0.05, description="Dropout applied to LoRA.")
    bias: Literal["none", "lora_only", "all"] = Field(default="none")
    target_modules: tuple[str, ...] = Field(
        default=("q_proj", "k_proj", "v_proj", "o_proj"),
        description="Module names that should receive LoRA adapters.",
    )


class LLMTrainingConfig(BaseModel):
    """Trainer hyper-parameters for causal LM fine-tuning."""

    output_dir: Path = Field(
        default=Path("artifacts/tinyllama-saas"),
        description="Directory where Trainer will write checkpoints.",
    )
    num_train_epochs: PositiveFloat = Field(default=3.0)
    per_device_train_batch_size: PositiveInt = Field(default=1)
    per_device_eval_batch_size: PositiveInt = Field(default=1)
    learning_rate: PositiveFloat = Field(default=2e-5)
    weight_decay: float = Field(default=0.0)
    warmup_ratio: float = Field(default=0.03)
    logging_steps: PositiveInt = Field(default=10)
    eval_steps: PositiveInt = Field(default=50)
    save_steps: PositiveInt = Field(default=200)
    save_total_limit: PositiveInt = Field(default=2)
    gradient_accumulation_steps: PositiveInt = Field(default=8)
    max_steps: int = Field(
        default=-1,
        description="Optional early stop; keep -1 to disable.",
    )
    lr_scheduler_type: str = Field(default="cosine")
    gradient_checkpointing: bool = Field(default=True)
    bf16: bool = Field(default=False)
    fp16: bool = Field(default=False)
    early_stopping_patience: int | None = Field(
        default=3,
        description="Stop after N evals with no improvement. None to disable.",
    )
    early_stopping_metric: str = Field(default="eval_loss")
    early_stopping_greater_is_better: bool = Field(default=False)
    auto_evaluate: bool = Field(
        default=False,
        description="Run all available benchmarks after experiment completes.",
    )

    @model_validator(mode="after")
    def _validate_paths(self) -> "LLMTrainingConfig":
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.warmup_ratio < 0:
            msg = "warmup_ratio cannot be negative."
            raise ValueError(msg)
        return self


class LLMExperimentConfig(BaseModel):
    """Top-level config surfaced to the CLI for LLM training."""

    data: LLMDataConfig
    model: LLMModelConfig
    training: LLMTrainingConfig
    peft: LLMPeftConfig | None = Field(
        default=None,
        description="Optional PEFT adapter settings.",
    )

    _expected_root_keys: ClassVar[tuple[str, ...]] = ("data", "model", "training")

    @classmethod
    def from_yaml(cls, path: Path) -> "LLMExperimentConfig":
        if not path.exists():
            msg = f"Config file {path} is missing."
            raise FileNotFoundError(msg)
        with path.open("r", encoding="utf-8") as handle:
            payload: dict[str, Any] = yaml.safe_load(handle)
        missing = [k for k in cls._expected_root_keys if k not in payload]
        if missing:
            msg = f"Config is missing keys: {missing}"
            raise ValueError(msg)
        return cls.model_validate(payload)

