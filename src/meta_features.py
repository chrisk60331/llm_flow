"""Meta-feature extraction for fine-tuning performance prediction."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field
from transformers import AutoTokenizer


class StaticDatasetFeatures(BaseModel):
    """Features extracted from the dataset before training."""

    n_samples: int = Field(description="Number of rows in dataset")
    avg_text_length: float = Field(description="Mean character length of text")
    vocab_size: int = Field(description="Unique whitespace-split tokens")
    type_token_ratio: float = Field(description="vocab_size / total_tokens")
    oov_rate: float = Field(description="Fraction of tokens not in model vocab")
    avg_sequence_length: float = Field(description="Mean tokenized sequence length")
    max_sequence_length: int = Field(description="Max tokenized sequence length")
    truncation_rate: float = Field(description="Fraction of samples exceeding max_length")


class StaticConfigFeatures(BaseModel):
    """Features extracted from the training config."""

    learning_rate: float
    num_epochs: float
    batch_size: int
    gradient_accumulation_steps: int
    warmup_ratio: float
    weight_decay: float
    max_length: int
    lora_enabled: bool
    lora_r: int | None = None
    lora_alpha: int | None = None
    model_name: str


class DynamicProbeFeatures(BaseModel):
    """Features captured from a short probe training run."""

    probe_steps: int = Field(description="Number of steps in probe run")
    probe_initial_loss: float = Field(description="Loss at step 0")
    probe_final_loss: float = Field(description="Loss at final probe step")
    probe_loss_slope: float = Field(description="Linear regression slope of loss")
    probe_loss_variance: float = Field(description="Variance of loss over probe")
    probe_grad_norm_mean: float = Field(description="Mean gradient norm")
    probe_grad_norm_std: float = Field(description="Std of gradient norms")


class MetaFeatureVector(BaseModel):
    """Complete meta-feature vector for a fine-tuning run."""

    experiment_id: str
    is_synthetic: bool = False
    # Static dataset features
    n_samples: int
    avg_text_length: float
    vocab_size: int
    type_token_ratio: float
    oov_rate: float
    avg_sequence_length: float
    max_sequence_length: int
    truncation_rate: float
    # Static config features
    learning_rate: float
    num_epochs: float
    batch_size: int
    gradient_accumulation_steps: int
    warmup_ratio: float
    weight_decay: float
    max_length: int
    lora_enabled: bool
    lora_r: int | None = None
    lora_alpha: int | None = None
    model_name: str
    # Dynamic probe features
    probe_steps: int
    probe_initial_loss: float
    probe_final_loss: float
    probe_loss_slope: float
    probe_loss_variance: float
    probe_grad_norm_mean: float
    probe_grad_norm_std: float
    # Target metrics (filled after full training)
    final_eval_loss: float | None = None
    final_bleu_score: float | None = None
    final_rouge_score: float | None = None

    def feature_names(self) -> list[str]:
        """Return names of features used for prediction (excludes id and targets)."""
        exclude = {"experiment_id", "is_synthetic", "final_eval_loss", "final_bleu_score", "final_rouge_score"}
        return [k for k in self.model_fields if k not in exclude]

    def to_feature_dict(self) -> dict[str, float | int | bool]:
        """Return feature values as a dict for prediction."""
        exclude = {"experiment_id", "is_synthetic", "final_eval_loss", "final_bleu_score", "final_rouge_score", "model_name"}
        data = self.model_dump()
        result = {}
        for k, v in data.items():
            if k in exclude:
                continue
            # Use 0 for None values (e.g., lora_r/lora_alpha when LoRA disabled)
            result[k] = v if v is not None else 0
        return result


def extract_static_dataset_features(
    csv_path: Path,
    text_fields: tuple[str, ...],
    separator: str,
    tokenizer: AutoTokenizer,
    max_length: int,
) -> StaticDatasetFeatures:
    """Extract static features from a dataset CSV."""
    df = pd.read_csv(csv_path)
    n_samples = len(df)

    # Concatenate text fields
    texts = df[list(text_fields)].astype(str).agg(separator.join, axis=1).tolist()

    # Character-level stats
    text_lengths = [len(t) for t in texts]
    avg_text_length = sum(text_lengths) / n_samples

    # Token-level stats (whitespace split for vocab diversity)
    all_tokens = []
    for text in texts:
        all_tokens.extend(text.split())
    total_tokens = len(all_tokens)
    unique_tokens = set(all_tokens)
    vocab_size = len(unique_tokens)
    type_token_ratio = vocab_size / total_tokens if total_tokens > 0 else 0.0

    # OOV rate using model tokenizer
    tokenizer_vocab = set(tokenizer.get_vocab().keys())
    oov_count = sum(1 for t in unique_tokens if t not in tokenizer_vocab)
    oov_rate = oov_count / vocab_size if vocab_size > 0 else 0.0

    # Tokenized sequence lengths
    tokenized = tokenizer(texts, truncation=False, padding=False)
    seq_lengths = [len(ids) for ids in tokenized["input_ids"]]
    avg_sequence_length = sum(seq_lengths) / n_samples
    max_sequence_length = max(seq_lengths)
    truncation_rate = sum(1 for l in seq_lengths if l > max_length) / n_samples

    return StaticDatasetFeatures(
        n_samples=n_samples,
        avg_text_length=avg_text_length,
        vocab_size=vocab_size,
        type_token_ratio=type_token_ratio,
        oov_rate=oov_rate,
        avg_sequence_length=avg_sequence_length,
        max_sequence_length=max_sequence_length,
        truncation_rate=truncation_rate,
    )


def extract_static_config_features(
    config,
) -> StaticConfigFeatures:
    """Extract static features from a CausalLMFullConfig or LLMExperimentConfig."""
    # Handle both API config (CausalLMFullConfig) and CLI config (LLMExperimentConfig)
    if hasattr(config, "training"):
        training = config.training
        data = config.data
        model = config.model
        peft = getattr(config, "peft", None)
    else:
        training = config.training
        data = config.data
        model = config.model
        peft = getattr(config, "peft", None)

    lora_enabled = peft.enabled if peft else False
    lora_r = peft.r if peft and peft.enabled else None
    lora_alpha = peft.lora_alpha if peft and peft.enabled else None

    return StaticConfigFeatures(
        learning_rate=training.learning_rate,
        num_epochs=training.num_train_epochs,
        batch_size=training.per_device_train_batch_size,
        gradient_accumulation_steps=training.gradient_accumulation_steps,
        warmup_ratio=training.warmup_ratio,
        weight_decay=training.weight_decay,
        max_length=data.max_length,
        lora_enabled=lora_enabled,
        lora_r=lora_r,
        lora_alpha=lora_alpha,
        model_name=model.pretrained_model_name,
    )
