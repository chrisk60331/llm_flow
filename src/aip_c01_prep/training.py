from __future__ import annotations

from transformers import (
    AutoModelForMaskedLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
    set_seed,
)

from .callbacks import StreamingLogsCallback
from .config import ExperimentConfig
from .data import load_dataset, tokenize_dataset
from .viz import save_loss_curve


def _freeze_layers(model: AutoModelForMaskedLM, config: ExperimentConfig) -> None:
    """Freeze embeddings and the requested number of transformer layers."""
    distilbert = model.distilbert
    if config.model.freeze_embedding:
        for param in distilbert.embeddings.parameters():
            param.requires_grad = False
    if config.model.freeze_encoder_layers:
        for layer in distilbert.transformer.layer[: config.model.freeze_encoder_layers]:
            for param in layer.parameters():
                param.requires_grad = False


def _build_training_arguments(config: ExperimentConfig) -> TrainingArguments:
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
        report_to=[],
    )


def run_training(config: ExperimentConfig) -> tuple[Trainer, dict[str, float]]:
    """Run a Trainer.fit cycle and return trainer plus metrics."""
    set_seed(config.data.seed)
    raw_splits = load_dataset(config.data)
    tokenizer = AutoTokenizer.from_pretrained(config.model.pretrained_model_name)
    tokenized = tokenize_dataset(
        dataset=raw_splits,
        tokenizer=tokenizer,
        max_length=config.data.max_length,
    )
    model = AutoModelForMaskedLM.from_pretrained(config.model.pretrained_model_name)
    _freeze_layers(model, config)
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer, mlm_probability=0.15
    )
    logs_path = config.training.output_dir / "training_logs.json"
    streaming_callback = StreamingLogsCallback(logs_path)
    trainer = Trainer(
        model=model,
        args=_build_training_arguments(config),
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        tokenizer=tokenizer,
        data_collator=data_collator,
        callbacks=[streaming_callback],
    )
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
        title=f"{config.model.pretrained_model_name} MLM Loss",
    )
    return trainer, {**train_metrics.metrics, **eval_metrics}

