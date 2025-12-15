"""Subprocess runner for untrusted custom Lightning training.

This module is meant to be executed in a separate process. It imports user-uploaded
python files by *path* and runs training with Lightning, writing JSON artifacts
that the API can poll/read.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from lightning.pytorch.callbacks import Callback
except Exception:  # pragma: no cover
    # Fallback for environments where `lightning.pytorch` import paths differ.
    from lightning.pytorch.callbacks.callback import Callback  # type: ignore


@dataclass(frozen=True)
class RunnerPayload:
    experiment_id: str
    output_dir: str
    config: dict
    dataset: dict | None
    lightning_module_path: str
    lightning_module_class_name: str
    dataloaders_path: str
    dataloaders_function_name: str


def _fail(msg: str) -> None:
    raise RuntimeError(msg)


def _load_module_from_path(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        _fail(f"Failed to load module spec for path={path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _to_jsonable(val: Any) -> Any:
    try:
        import torch

        if isinstance(val, torch.Tensor):
            if val.numel() == 1:
                return float(val.detach().cpu().item())
            return val.detach().cpu().tolist()
    except Exception:
        pass
    if isinstance(val, (int, float, str, bool)) or val is None:
        return val
    if isinstance(val, dict):
        return {str(k): _to_jsonable(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_to_jsonable(v) for v in val]
    return str(val)


class _JsonArtifactsCallback(Callback):
    """Lightning callback writing training_logs.json + progress.json."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.logs_path = output_dir / "training_logs.json"
        self.progress_path = output_dir / "progress.json"
        self._log_history: list[dict[str, Any]] = []

    def _write_progress(self, trainer) -> None:
        payload = {
            "global_step": int(getattr(trainer, "global_step", 0) or 0),
            "epoch": int(getattr(trainer, "current_epoch", 0) or 0),
        }
        self.progress_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _append_log(self, trainer, stage: str) -> None:
        metrics = getattr(trainer, "callback_metrics", {}) or {}
        row = {"stage": stage, "step": int(trainer.global_step), "epoch": float(trainer.current_epoch)}
        for k, v in metrics.items():
            row[str(k)] = _to_jsonable(v)
        self._log_history.append(row)
        self.logs_path.write_text(json.dumps(self._log_history, indent=2), encoding="utf-8")

    # Lightning callback hooks
    def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx) -> None:  # noqa: ANN001
        self._write_progress(trainer)

    def on_train_epoch_end(self, trainer, pl_module) -> None:  # noqa: ANN001
        self._append_log(trainer, stage="train_epoch_end")

    def on_validation_epoch_end(self, trainer, pl_module) -> None:  # noqa: ANN001
        self._append_log(trainer, stage="val_epoch_end")

    def on_test_epoch_end(self, trainer, pl_module) -> None:  # noqa: ANN001
        self._append_log(trainer, stage="test_epoch_end")

    def on_exception(self, trainer, pl_module, exception) -> None:  # noqa: ANN001
        # Ensure we write out *something* even when training crashes.
        self._write_progress(trainer)
        row = {
            "stage": "exception",
            "step": int(getattr(trainer, "global_step", 0) or 0),
            "epoch": float(getattr(trainer, "current_epoch", 0) or 0),
            "exception": str(exception),
        }
        self._log_history.append(row)
        self.logs_path.write_text(json.dumps(self._log_history, indent=2), encoding="utf-8")


def _run(payload: RunnerPayload) -> dict[str, Any]:
    # Import lightning only inside the subprocess runner logic.
    try:
        import lightning.pytorch as pl
    except Exception:
        import lightning as pl  # type: ignore
    from lightning.pytorch.utilities.model_helpers import is_overridden

    output_dir = Path(payload.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lightning_module_file = Path(payload.lightning_module_path)
    dataloaders_file = Path(payload.dataloaders_path)
    if not lightning_module_file.exists():
        _fail(f"lightning_module_path does not exist: {lightning_module_file}")
    if not dataloaders_file.exists():
        _fail(f"dataloaders_path does not exist: {dataloaders_file}")

    lm_mod = _load_module_from_path("uploaded_lightning_module", lightning_module_file)
    dl_mod = _load_module_from_path("uploaded_dataloaders", dataloaders_file)

    if not hasattr(lm_mod, payload.lightning_module_class_name):
        _fail(f"LightningModule class not found: {payload.lightning_module_class_name}")
    lm_cls = getattr(lm_mod, payload.lightning_module_class_name)

    if not hasattr(dl_mod, payload.dataloaders_function_name):
        _fail(f"Dataloader function not found: {payload.dataloaders_function_name}")
    build_dataloaders = getattr(dl_mod, payload.dataloaders_function_name)

    # Enforce __init__(cfg: dict) contract (fail fast)
    try:
        module = lm_cls(payload.config)
    except TypeError as e:
        _fail(f"Failed to instantiate LightningModule with cfg dict: {e}")

    dls = build_dataloaders(payload.config, payload.dataset)
    if not isinstance(dls, dict):
        _fail("build_dataloaders must return dict[str, DataLoader]")
    if "train" not in dls:
        _fail('build_dataloaders must return a dict containing key "train"')

    cb = _JsonArtifactsCallback(output_dir)
    train_cfg = payload.config.get("training", {}) if isinstance(payload.config, dict) else {}

    trainer = pl.Trainer(
        default_root_dir=str(output_dir),
        max_epochs=int(train_cfg.get("max_epochs", 1)),
        accelerator=str(train_cfg.get("accelerator", "auto")),
        devices=train_cfg.get("devices", "auto"),
        precision=str(train_cfg.get("precision", "32")),
        log_every_n_steps=int(train_cfg.get("log_every_n_steps", 10)),
        callbacks=[cb],
        enable_checkpointing=False,
        logger=False,
    )

    trainer.fit(model=module, train_dataloaders=dls["train"], val_dataloaders=dls.get("val"))

    # Persist a checkpoint for downstream evaluation (benchmarks, analysis).
    ckpt_path = output_dir / "model.ckpt"
    trainer.save_checkpoint(str(ckpt_path))

    metrics: dict[str, Any] = {}
    if dls.get("val") is not None:
        out = trainer.validate(model=module, dataloaders=dls["val"], verbose=False)
        metrics["validate"] = _to_jsonable(out)
    if dls.get("test") is not None:
        if not is_overridden("test_step", module):
            _fail('Test dataloader was provided but your LightningModule does not implement test_step(). Either add test_step() or omit the "test" dataloader.')
        out = trainer.test(model=module, dataloaders=dls["test"], verbose=False)
        metrics["test"] = _to_jsonable(out)

    metrics["callback_metrics"] = _to_jsonable(getattr(trainer, "callback_metrics", {}) or {})
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main() -> None:
    if len(sys.argv) != 2:
        _fail("Usage: python -m src.custom_lightning_runner <payload_json_path>")
    payload_path = Path(sys.argv[1])
    if not payload_path.exists():
        _fail(f"payload_json_path does not exist: {payload_path}")

    raw = json.loads(payload_path.read_text(encoding="utf-8"))
    payload = RunnerPayload(**raw)

    try:
        _run(payload)
    except Exception as e:
        out_dir = Path(payload.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "runner_error.txt").write_text(str(e), encoding="utf-8")
        raise


if __name__ == "__main__":
    main()


