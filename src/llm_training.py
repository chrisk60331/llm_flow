from __future__ import annotations

from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
    set_seed,
)

from .callbacks import StopCheckCallback, StreamingLogsCallback
from .data import tokenize_dataset
from .llm_config import LLMExperimentConfig
from .llm_data import load_llm_dataset
from .viz import save_loss_curve


def _prepare_tokenizer(config: LLMExperimentConfig) -> tuple[AutoTokenizer, bool]:
    tokenizer = AutoTokenizer.from_pretrained(
        config.model.pretrained_model_name,
        trust_remote_code=config.model.trust_remote_code,
    )
    tokenizer.padding_side = "right"
    added_pad_token = False
    if tokenizer.pad_token is None:
        if config.model.pad_token_override is None:
            msg = (
                "Tokenizer is missing a pad_token. "
                "Set model.pad_token_override to an explicit value."
            )
            raise ValueError(msg)
        added_tokens = tokenizer.add_special_tokens(
            {"pad_token": config.model.pad_token_override}
        )
        added_pad_token = added_tokens > 0
    return tokenizer, added_pad_token


def _build_training_arguments(config: LLMExperimentConfig) -> TrainingArguments:
    train_cfg = config.training
    return TrainingArguments(
        output_dir=str(train_cfg.output_dir),
        per_device_train_batch_size=train_cfg.per_device_train_batch_size,
        per_device_eval_batch_size=train_cfg.per_device_eval_batch_size,
        num_train_epochs=train_cfg.num_train_epochs,
        learning_rate=train_cfg.learning_rate,
        weight_decay=train_cfg.weight_decay,
        warmup_ratio=train_cfg.warmup_ratio,
        logging_steps=train_cfg.logging_steps,
        eval_strategy="steps",
        eval_steps=train_cfg.eval_steps,
        save_strategy="steps",
        save_steps=train_cfg.save_steps,
        save_total_limit=train_cfg.save_total_limit,
        gradient_accumulation_steps=train_cfg.gradient_accumulation_steps,
        max_steps=train_cfg.max_steps,
        lr_scheduler_type=train_cfg.lr_scheduler_type,
        gradient_checkpointing=train_cfg.gradient_checkpointing,
        bf16=train_cfg.bf16,
        fp16=train_cfg.fp16,
        report_to=[],
        load_best_model_at_end=train_cfg.early_stopping_patience is not None,
        metric_for_best_model=train_cfg.early_stopping_metric,
        greater_is_better=train_cfg.early_stopping_greater_is_better,
    )


def _apply_lora_if_enabled(model: AutoModelForCausalLM, config: LLMExperimentConfig):
    """Wrap the base model with LoRA adapters when requested."""
    peft_cfg = config.peft
    if not peft_cfg or not peft_cfg.enabled:
        return model
    lora_config = LoraConfig(
        task_type="CAUSAL_LM",
        r=peft_cfg.r,
        lora_alpha=peft_cfg.lora_alpha,
        lora_dropout=peft_cfg.lora_dropout,
        bias=peft_cfg.bias,
        target_modules=list(peft_cfg.target_modules),
    )
    model.enable_input_require_grads()
    wrapped = get_peft_model(model, lora_config)
    wrapped.print_trainable_parameters()
    return wrapped


def run_llm_training(
    config: LLMExperimentConfig,
    experiment_id: str | None = None,
) -> tuple[Trainer, dict[str, float]]:
    """Fine-tune the configured LLM with causal language modeling."""
    set_seed(config.data.seed)
    raw_splits = load_llm_dataset(config.data)
    tokenizer, added_pad_token = _prepare_tokenizer(config)
    tokenized = tokenize_dataset(
        dataset=raw_splits,
        tokenizer=tokenizer,
        max_length=config.data.max_length,
    )
    model = AutoModelForCausalLM.from_pretrained(
        config.model.pretrained_model_name,
        trust_remote_code=config.model.trust_remote_code,
    )
    if added_pad_token:
        model.resize_token_embeddings(len(tokenizer))
    if config.training.gradient_checkpointing:
        model.config.use_cache = False
    model = _apply_lora_if_enabled(model, config)
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )
    logs_path = config.training.output_dir / "training_logs.json"
    callbacks = [StreamingLogsCallback(logs_path, experiment_id=experiment_id)]
    if config.training.early_stopping_patience is not None:
        callbacks.append(
            EarlyStoppingCallback(
                early_stopping_patience=config.training.early_stopping_patience
            )
        )
    if experiment_id is not None:
        callbacks.append(StopCheckCallback(experiment_id))
    trainer = Trainer(
        model=model,
        args=_build_training_arguments(config),
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        tokenizer=tokenizer,
        data_collator=data_collator,
        callbacks=callbacks,
    )
    # Run initial evaluation at step 0 for baseline comparison
    initial_eval = trainer.evaluate()
    trainer.state.log_history.insert(0, {"step": 0, "epoch": 0.0, "eval_loss": initial_eval["eval_loss"]})
    train_metrics = trainer.train()
    eval_metrics = trainer.evaluate()
    trainer.save_model()

    plot_path = (
        config.training.output_dir
        / "plots"
        / f"{config.model.pretrained_model_name.replace('/', '_')}_loss.html"
    )
    save_loss_curve(
        log_history=trainer.state.log_history,
        output_path=plot_path,
        title=f"{config.model.pretrained_model_name} Causal LM Loss",
    )
    return trainer, {**train_metrics.metrics, **eval_metrics}

