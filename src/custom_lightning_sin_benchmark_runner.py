"""Subprocess runner for custom-lightning sin(x) regression benchmark evaluation.

Loads an uploaded LightningModule class by path, restores weights from a saved
Lightning checkpoint, and computes MSE/MAE against sin(x) on a fixed grid.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BenchmarkPayload:
    output_dir: str
    config: dict
    lightning_module_path: str
    lightning_module_class_name: str
    checkpoint_path: str
    x_min: float
    x_max: float
    n_points: int


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


def _run(payload: BenchmarkPayload) -> dict[str, Any]:
    try:
        import torch
    except Exception as e:  # pragma: no cover
        _fail(f"torch is required for regression benchmark: {e}")

    output_dir = Path(payload.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lm_path = Path(payload.lightning_module_path)
    ckpt_path = Path(payload.checkpoint_path)
    if not lm_path.exists():
        _fail(f"lightning_module_path does not exist: {lm_path}")
    if not ckpt_path.exists():
        _fail(f"checkpoint_path does not exist: {ckpt_path}")

    if payload.n_points <= 1:
        _fail("n_points must be >= 2")
    if not (payload.x_max > payload.x_min):
        _fail("x_max must be > x_min")

    lm_mod = _load_module_from_path("uploaded_lightning_module_for_benchmark", lm_path)
    if not hasattr(lm_mod, payload.lightning_module_class_name):
        _fail(f"LightningModule class not found: {payload.lightning_module_class_name}")
    lm_cls = getattr(lm_mod, payload.lightning_module_class_name)

    try:
        module = lm_cls(payload.config)
    except TypeError as e:
        _fail(f"Failed to instantiate LightningModule with cfg dict: {e}")

    ckpt = torch.load(str(ckpt_path), map_location="cpu")
    if not isinstance(ckpt, dict) or "state_dict" not in ckpt:
        _fail("Checkpoint is missing 'state_dict'")
    module.load_state_dict(ckpt["state_dict"], strict=True)
    module.eval()

    # Evaluate on a deterministic grid
    x = torch.linspace(float(payload.x_min), float(payload.x_max), int(payload.n_points), dtype=torch.float32).view(-1, 1)
    y_true = torch.sin(x)
    with torch.no_grad():
        y_pred = module(x)
    if not isinstance(y_pred, torch.Tensor):
        _fail("Model forward must return a torch.Tensor")
    if y_pred.shape != y_true.shape:
        _fail(f"Prediction shape {tuple(y_pred.shape)} does not match target shape {tuple(y_true.shape)}")

    mse = torch.mean((y_pred - y_true) ** 2)
    mae = torch.mean(torch.abs(y_pred - y_true))

    return {
        "mse": _to_jsonable(mse),
        "mae": _to_jsonable(mae),
        "rmse": math.sqrt(float(mse.detach().cpu().item())),
        "n_points": int(payload.n_points),
        "x_min": float(payload.x_min),
        "x_max": float(payload.x_max),
    }


def main() -> None:
    if len(sys.argv) != 2:
        _fail("Usage: python -m src.custom_lightning_sin_benchmark_runner <payload_json_path>")
    payload_path = Path(sys.argv[1])
    if not payload_path.exists():
        _fail(f"payload_json_path does not exist: {payload_path}")

    raw = json.loads(payload_path.read_text(encoding="utf-8"))
    payload = BenchmarkPayload(**raw)

    out_dir = Path(payload.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "benchmark_metrics.json"

    metrics = _run(payload)
    out_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()


