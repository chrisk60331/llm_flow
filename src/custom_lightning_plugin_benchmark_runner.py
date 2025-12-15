"""Subprocess runner for custom-lightning *plugin* benchmarks.

Loads an uploaded LightningModule by path, restores weights from a Lightning
checkpoint, then calls a user-provided benchmark plugin function:

    run_benchmark(cfg: dict, module: LightningModule, spec: dict) -> dict

The function must return a JSON-serializable dict containing:
  - primary_score: float
  - (optional) any additional fields under "metrics" or at the top-level
"""

from __future__ import annotations

import importlib.util
import json
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
    benchmark_plugin_path: str
    benchmark_function_name: str
    benchmark_spec: dict


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
    import torch

    if isinstance(val, torch.Tensor):
        if val.numel() == 1:
            return float(val.detach().cpu().item())
        return val.detach().cpu().tolist()
    if isinstance(val, (int, float, str, bool)) or val is None:
        return val
    if isinstance(val, dict):
        return {str(k): _to_jsonable(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_to_jsonable(v) for v in val]
    return str(val)


def _run(payload: BenchmarkPayload) -> dict[str, Any]:
    import torch

    output_dir = Path(payload.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lm_path = Path(payload.lightning_module_path)
    ckpt_path = Path(payload.checkpoint_path)
    bm_path = Path(payload.benchmark_plugin_path)
    if not lm_path.exists():
        _fail(f"lightning_module_path does not exist: {lm_path}")
    if not ckpt_path.exists():
        _fail(f"checkpoint_path does not exist: {ckpt_path}")
    if not bm_path.exists():
        _fail(f"benchmark_plugin_path does not exist: {bm_path}")

    lm_mod = _load_module_from_path("uploaded_lightning_module_for_plugin_benchmark", lm_path)
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

    bm_mod = _load_module_from_path("uploaded_benchmark_plugin", bm_path)
    if not hasattr(bm_mod, payload.benchmark_function_name):
        _fail(f"Benchmark function not found: {payload.benchmark_function_name}")
    run_benchmark = getattr(bm_mod, payload.benchmark_function_name)

    out = run_benchmark(payload.config, module, payload.benchmark_spec)
    if not isinstance(out, dict):
        _fail("run_benchmark must return a dict")
    if "primary_score" not in out:
        _fail("run_benchmark output must contain key 'primary_score'")

    out = _to_jsonable(out)
    out["primary_score"] = float(out["primary_score"])
    return out


def main() -> None:
    if len(sys.argv) != 2:
        _fail("Usage: python -m src.custom_lightning_plugin_benchmark_runner <payload_json_path>")
    payload_path = Path(sys.argv[1])
    if not payload_path.exists():
        _fail(f"payload_json_path does not exist: {payload_path}")

    raw = json.loads(payload_path.read_text(encoding="utf-8"))
    payload = BenchmarkPayload(**raw)

    out_dir = Path(payload.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "benchmark_plugin_metrics.json"

    metrics = _run(payload)
    out_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()


