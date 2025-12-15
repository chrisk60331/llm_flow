from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import yaml
from pydantic import BaseModel, Field, PositiveFloat, PositiveInt, model_validator


class DataConfig(BaseModel):
    """Configuration for turning the CSV into a masked-language-model dataset."""

    csv_path: Path = Field(description="Absolute path to the training CSV.")
    text_fields: tuple[str, ...] = Field(
        default=("question", "answer_tolkien"),
        description="Ordered columns that will be concatenated before tokenization.",
    )
    separator: str = Field(
        default="\n\n",
        description="Literal inserted between text fields before tokenization.",
    )
    validation_split: PositiveFloat = Field(
        default=0.2, description="Fraction of rows reserved for evaluation."
    )
    seed: PositiveInt = Field(default=42, description="Reproducibility seed.")
    max_length: PositiveInt = Field(
        default=256, description="Tokenizer max_length for truncation/padding."
    )

    @model_validator(mode="after")
    def _validate_split(self) -> "DataConfig":
        if not 0 < self.validation_split < 1:
            msg = "validation_split must be inside (0, 1)."
            raise ValueError(msg)
        if not self.csv_path.exists():
            msg = f"csv_path={self.csv_path} does not exist."
            raise FileNotFoundError(msg)
        return self


class ModelConfig(BaseModel):
    """Model-centric knobs."""

    pretrained_model_name: str = Field(
        default="distilbert-base-uncased", description="HF repo id or local path."
    )
    freeze_embedding: bool = Field(
        default=False,
        description="If true, embedding layer parameters stay frozen.",
    )
    freeze_encoder_layers: int = Field(
        default=0,
        description="Number of lowest DistilBERT transformer layers to freeze.",
    )

    @model_validator(mode="after")
    def _validate_freeze_layers(self) -> "ModelConfig":
        if self.freeze_encoder_layers < 0 or self.freeze_encoder_layers > 6:
            msg = "freeze_encoder_layers must be between 0 and 6 for DistilBERT."
            raise ValueError(msg)
        return self


class TrainingConfig(BaseModel):
    """Trainer hyper-parameters."""

    output_dir: Path = Field(
        default=Path("artifacts/models"),
        description="Directory where Trainer will write checkpoints.",
    )
    num_train_epochs: PositiveFloat = Field(default=3.0)
    per_device_train_batch_size: PositiveInt = Field(default=8)
    per_device_eval_batch_size: PositiveInt = Field(default=8)
    learning_rate: PositiveFloat = Field(default=5e-5)
    weight_decay: float = Field(default=0.01)
    warmup_ratio: float = Field(default=0.0)
    logging_steps: PositiveInt = Field(default=10)
    eval_steps: PositiveInt = Field(default=50)
    save_steps: PositiveInt = Field(default=200)
    save_total_limit: PositiveInt = Field(default=2)
    gradient_accumulation_steps: PositiveInt = Field(default=1)
    max_steps: int = Field(
        default=-1,
        description="Optional early stop; keep -1 to disable.",
    )
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
    def _validate_paths(self) -> "TrainingConfig":
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.warmup_ratio < 0:
            msg = "warmup_ratio cannot be negative."
            raise ValueError(msg)
        return self


class ExperimentConfig(BaseModel):
    """Top-level config surfaced to the CLI."""

    data: DataConfig
    model: ModelConfig
    training: TrainingConfig

    _expected_root_keys: ClassVar[tuple[str, ...]] = ("data", "model", "training")

    @classmethod
    def from_yaml(cls, path: Path) -> "ExperimentConfig":
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

