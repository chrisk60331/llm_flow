"""Standalone runner for causal LM experiments.

Can be invoked via subprocess for both local and remote execution:
    python -m src.causal_lm_runner /path/to/payload.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m src.causal_lm_runner <payload_path>", file=sys.stderr)
        sys.exit(1)

    payload_path = Path(sys.argv[1])
    if not payload_path.exists():
        print(f"Payload file not found: {payload_path}", file=sys.stderr)
        sys.exit(1)

    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    experiment_id = payload["experiment_id"]
    output_dir = Path(payload["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = payload["config"]
    dataset = payload["dataset"]
    peft_cfg = payload.get("peft")

    from .llm_config import (
        LLMDataConfig,
        LLMExperimentConfig,
        LLMModelConfig,
        LLMPeftConfig,
        LLMTrainingConfig,
    )
    from .llm_training import run_llm_training

    peft_config = None
    if peft_cfg and peft_cfg.get("enabled"):
        peft_config = LLMPeftConfig(
            enabled=True,
            r=peft_cfg.get("r", 8),
            lora_alpha=peft_cfg.get("lora_alpha", 16),
            lora_dropout=peft_cfg.get("lora_dropout", 0.05),
            bias=peft_cfg.get("bias", "none"),
            target_modules=peft_cfg.get("target_modules"),
        )

    data_cfg = cfg["data"]
    model_cfg = cfg["model"]
    training_cfg = cfg["training"]

    config = LLMExperimentConfig(
        data=LLMDataConfig(
            csv_path=Path(dataset["path"]),
            question_field=data_cfg.get("question_field", "question"),
            answer_field=data_cfg.get("answer_field", "answer"),
            system_prompt=data_cfg.get("system_prompt", "You are an AI assistant."),
            template=data_cfg.get("template"),
            validation_split=data_cfg.get("validation_split", 0.2),
            seed=data_cfg.get("seed", 42),
            max_length=data_cfg.get("max_length", 512),
        ),
        model=LLMModelConfig(
            pretrained_model_name=model_cfg.get("pretrained_model_name", "TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
            trust_remote_code=model_cfg.get("trust_remote_code", False),
            pad_token_override=model_cfg.get("pad_token_override"),
        ),
        training=LLMTrainingConfig(
            output_dir=output_dir,
            num_train_epochs=training_cfg.get("num_train_epochs", 3),
            per_device_train_batch_size=training_cfg.get("per_device_train_batch_size", 1),
            per_device_eval_batch_size=training_cfg.get("per_device_eval_batch_size", 1),
            learning_rate=training_cfg.get("learning_rate", 2e-5),
            weight_decay=training_cfg.get("weight_decay", 0.0),
            warmup_ratio=training_cfg.get("warmup_ratio", 0.03),
            logging_steps=training_cfg.get("logging_steps", 10),
            eval_steps=training_cfg.get("eval_steps", 50),
            save_steps=training_cfg.get("save_steps", 200),
            save_total_limit=training_cfg.get("save_total_limit", 2),
            gradient_accumulation_steps=training_cfg.get("gradient_accumulation_steps", 8),
            max_steps=training_cfg.get("max_steps", -1),
            lr_scheduler_type=training_cfg.get("lr_scheduler_type", "cosine"),
            gradient_checkpointing=training_cfg.get("gradient_checkpointing", True),
            bf16=training_cfg.get("bf16", False),
            fp16=training_cfg.get("fp16", True),
            early_stopping_patience=training_cfg.get("early_stopping_patience"),
            early_stopping_metric=training_cfg.get("early_stopping_metric", "eval_loss"),
            early_stopping_greater_is_better=training_cfg.get("early_stopping_greater_is_better", False),
        ),
        peft=peft_config,
    )

    try:
        _, metrics = run_llm_training(config, experiment_id=experiment_id)
        metrics_path = output_dir / "metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        print(f"Training completed. Metrics saved to {metrics_path}")
    except Exception as e:
        error_path = output_dir / "error.txt"
        error_path.write_text(str(e), encoding="utf-8")
        print(f"Training failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

