"""Probe runner for extracting dynamic meta-features from short training runs."""
from __future__ import annotations

import gc
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import torch
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainerCallback,
    TrainerControl,
    TrainerState,
    TrainingArguments,
    set_seed,
)

from .data import tokenize_dataset
from .llm_data import load_llm_dataset
from .meta_features import (
    DynamicProbeFeatures,
    MetaFeatureVector,
    StaticConfigFeatures,
    StaticDatasetFeatures,
    extract_static_config_features,
    extract_static_dataset_features,
)
from .models import CausalLMFullConfig


class GradientNormCallback(TrainerCallback):
    """Callback that captures gradient norms during training."""

    def __init__(self) -> None:
        self.grad_norms: list[float] = []

    def on_step_end(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        model=None,
        **kwargs,
    ) -> None:
        if model is None:
            return
        total_norm = 0.0
        for p in model.parameters():
            if p.grad is not None:
                total_norm += p.grad.data.norm(2).item() ** 2
        total_norm = total_norm**0.5
        self.grad_norms.append(total_norm)


def _prepare_tokenizer(config: CausalLMFullConfig) -> tuple[AutoTokenizer, bool]:
    """Prepare tokenizer, adding pad token if needed."""
    tokenizer = AutoTokenizer.from_pretrained(
        config.model.pretrained_model_name,
        trust_remote_code=config.model.trust_remote_code,
    )
    tokenizer.padding_side = "right"
    added_pad_token = False
    if tokenizer.pad_token is None:
        if config.model.pad_token_override:
            added_tokens = tokenizer.add_special_tokens(
                {"pad_token": config.model.pad_token_override}
            )
            added_pad_token = added_tokens > 0
        else:
            tokenizer.pad_token = tokenizer.eos_token
    return tokenizer, added_pad_token


def _apply_probe_lora(model: AutoModelForCausalLM) -> AutoModelForCausalLM:
    """Always apply LoRA for probing - much faster than full model training."""
    lora_config = LoraConfig(
        task_type="CAUSAL_LM",
        r=8,
        lora_alpha=16,
        lora_dropout=0.0,
        bias="none",
        target_modules=["q_proj", "v_proj"],
    )
    model.enable_input_require_grads()
    return get_peft_model(model, lora_config)


def _build_llm_data_config(config: CausalLMFullConfig, csv_path: Path):
    """Convert CausalLMFullConfig to LLMDataConfig for dataset loading."""
    from .llm_config import LLMDataConfig

    return LLMDataConfig(
        csv_path=csv_path,
        question_field=config.data.question_field,
        answer_field=config.data.answer_field,
        system_prompt=config.data.system_prompt,
        template=config.data.template,
        validation_split=config.data.validation_split,
        seed=config.data.seed,
        max_length=config.data.max_length,
    )


def _extract_probe_features(
    log_history: list[dict],
    grad_norms: list[float],
    probe_steps: int,
) -> DynamicProbeFeatures:
    """Extract dynamic features from probe training logs."""
    # Get loss values from log history
    losses = [entry["loss"] for entry in log_history if "loss" in entry]

    if len(losses) < 2:
        # Not enough data points
        return DynamicProbeFeatures(
            probe_steps=probe_steps,
            probe_initial_loss=losses[0] if losses else 0.0,
            probe_final_loss=losses[-1] if losses else 0.0,
            probe_loss_slope=0.0,
            probe_loss_variance=0.0,
            probe_grad_norm_mean=np.mean(grad_norms) if grad_norms else 0.0,
            probe_grad_norm_std=np.std(grad_norms) if grad_norms else 0.0,
        )

    # Calculate loss slope via linear regression
    x = np.arange(len(losses))
    slope, _ = np.polyfit(x, losses, 1)

    return DynamicProbeFeatures(
        probe_steps=probe_steps,
        probe_initial_loss=losses[0],
        probe_final_loss=losses[-1],
        probe_loss_slope=float(slope),
        probe_loss_variance=float(np.var(losses)),
        probe_grad_norm_mean=float(np.mean(grad_norms)) if grad_norms else 0.0,
        probe_grad_norm_std=float(np.std(grad_norms)) if grad_norms else 0.0,
    )


def run_probe(
    config: CausalLMFullConfig,
    csv_path: Path,
    probe_steps: int = 10,
    experiment_id: str = "probe",
) -> MetaFeatureVector:
    """Run a short training probe and extract meta-features.

    Args:
        config: The training configuration to probe
        csv_path: Path to the training CSV
        probe_steps: Number of training steps for the probe
        experiment_id: ID to assign to the resulting feature vector

    Returns:
        MetaFeatureVector with static and dynamic features
    """
    set_seed(config.data.seed)

    # Load tokenizer
    tokenizer, added_pad_token = _prepare_tokenizer(config)

    # Extract static dataset features
    text_fields = (config.data.question_field, config.data.answer_field)
    static_dataset = extract_static_dataset_features(
        csv_path=csv_path,
        text_fields=text_fields,
        separator="\n",
        tokenizer=tokenizer,
        max_length=config.data.max_length,
    )

    # Extract static config features
    static_config = extract_static_config_features(config)

    # Load and tokenize dataset
    llm_data_config = _build_llm_data_config(config, csv_path)
    raw_splits = load_llm_dataset(llm_data_config)
    tokenized = tokenize_dataset(
        dataset=raw_splits,
        tokenizer=tokenizer,
        max_length=config.data.max_length,
    )

    # Load model - force CPU for probes to avoid MPS memory issues with sequential runs
    model = AutoModelForCausalLM.from_pretrained(
        config.model.pretrained_model_name,
        trust_remote_code=config.model.trust_remote_code,
        device_map="cpu",
        torch_dtype=torch.float32,
    )
    if added_pad_token:
        model.resize_token_embeddings(len(tokenizer))
    if config.training.gradient_checkpointing:
        model.config.use_cache = False
    model = _apply_probe_lora(model)

    # Setup data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    # Setup gradient norm callback
    grad_callback = GradientNormCallback()

    # Run probe in temp directory - force CPU to avoid MPS issues with sequential runs
    with TemporaryDirectory() as tmpdir:
        training_args = TrainingArguments(
            output_dir=tmpdir,
            per_device_train_batch_size=config.training.per_device_train_batch_size,
            per_device_eval_batch_size=config.training.per_device_eval_batch_size,
            learning_rate=config.training.learning_rate,
            weight_decay=config.training.weight_decay,
            warmup_ratio=config.training.warmup_ratio,
            gradient_accumulation_steps=config.training.gradient_accumulation_steps,
            max_steps=probe_steps,
            logging_steps=1,  # Log every step for probe
            save_strategy="no",
            report_to=[],
            bf16=False,  # CPU doesn't support bf16
            fp16=False,  # Force fp32 for CPU
            dataloader_pin_memory=False,
            use_cpu=True,
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized["train"],
            eval_dataset=tokenized["test"],
            tokenizer=tokenizer,
            data_collator=data_collator,
            callbacks=[grad_callback],
        )

        trainer.train()

        # Extract dynamic features
        dynamic_features = _extract_probe_features(
            log_history=trainer.state.log_history,
            grad_norms=grad_callback.grad_norms,
            probe_steps=probe_steps,
        )

    # Explicit cleanup to prevent memory accumulation across multiple probes
    del trainer
    del model
    del tokenized
    del data_collator
    del tokenizer
    gc.collect()

    # Combine all features into MetaFeatureVector
    return MetaFeatureVector(
        experiment_id=experiment_id,
        # Static dataset features
        n_samples=static_dataset.n_samples,
        avg_text_length=static_dataset.avg_text_length,
        vocab_size=static_dataset.vocab_size,
        type_token_ratio=static_dataset.type_token_ratio,
        oov_rate=static_dataset.oov_rate,
        avg_sequence_length=static_dataset.avg_sequence_length,
        max_sequence_length=static_dataset.max_sequence_length,
        truncation_rate=static_dataset.truncation_rate,
        # Static config features
        learning_rate=static_config.learning_rate,
        num_epochs=static_config.num_epochs,
        batch_size=static_config.batch_size,
        gradient_accumulation_steps=static_config.gradient_accumulation_steps,
        warmup_ratio=static_config.warmup_ratio,
        weight_decay=static_config.weight_decay,
        max_length=static_config.max_length,
        lora_enabled=static_config.lora_enabled,
        lora_r=static_config.lora_r,
        lora_alpha=static_config.lora_alpha,
        model_name=static_config.model_name,
        # Dynamic probe features
        probe_steps=dynamic_features.probe_steps,
        probe_initial_loss=dynamic_features.probe_initial_loss,
        probe_final_loss=dynamic_features.probe_final_loss,
        probe_loss_slope=dynamic_features.probe_loss_slope,
        probe_loss_variance=dynamic_features.probe_loss_variance,
        probe_grad_norm_mean=dynamic_features.probe_grad_norm_mean,
        probe_grad_norm_std=dynamic_features.probe_grad_norm_std,
    )
