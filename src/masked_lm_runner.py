"""Standalone runner for masked LM experiments.

Can be invoked via subprocess for both local and remote execution:
    python -m src.masked_lm_runner /path/to/payload.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m src.masked_lm_runner <payload_path>", file=sys.stderr)
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

    from .config import DataConfig, ExperimentConfig, ModelConfig, TrainingConfig
    from .training import run_training

    data_cfg = cfg["data"]
    model_cfg = cfg["model"]
    training_cfg = cfg["training"]

    config = ExperimentConfig(
        data=DataConfig(
            csv_path=Path(dataset["path"]),
            text_fields=data_cfg.get("text_fields", ["question", "answer"]),
            separator=data_cfg.get("separator", "\n\n"),
            validation_split=data_cfg.get("validation_split", 0.2),
            seed=data_cfg.get("seed", 42),
            max_length=data_cfg.get("max_length", 256),
        ),
        model=ModelConfig(
            pretrained_model_name=model_cfg.get("pretrained_model_name", "distilbert-base-uncased"),
            freeze_embedding=model_cfg.get("freeze_embedding", False),
            freeze_encoder_layers=model_cfg.get("freeze_encoder_layers", 0),
        ),
        training=TrainingConfig(
            output_dir=output_dir,
            num_train_epochs=training_cfg.get("num_train_epochs", 3),
            per_device_train_batch_size=training_cfg.get("per_device_train_batch_size", 8),
            per_device_eval_batch_size=training_cfg.get("per_device_eval_batch_size", 8),
            learning_rate=training_cfg.get("learning_rate", 5e-5),
            weight_decay=training_cfg.get("weight_decay", 0.01),
            warmup_ratio=training_cfg.get("warmup_ratio", 0.0),
            logging_steps=training_cfg.get("logging_steps", 10),
            eval_steps=training_cfg.get("eval_steps", 50),
            save_steps=training_cfg.get("save_steps", 200),
            save_total_limit=training_cfg.get("save_total_limit", 2),
            gradient_accumulation_steps=training_cfg.get("gradient_accumulation_steps", 1),
            max_steps=training_cfg.get("max_steps", -1),
            early_stopping_patience=training_cfg.get("early_stopping_patience"),
            early_stopping_metric=training_cfg.get("early_stopping_metric", "eval_loss"),
            early_stopping_greater_is_better=training_cfg.get("early_stopping_greater_is_better", False),
        ),
    )

    try:
        _, metrics = run_training(config, experiment_id=experiment_id)
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

