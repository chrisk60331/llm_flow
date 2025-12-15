import numpy as np
import torch


def run_benchmark(cfg: dict, lightning_module, spec: dict) -> dict:
    if not hasattr(lightning_module, "model"):
        raise RuntimeError("LightningModule must have attribute .model for this benchmark")
    model = lightning_module.model
    if not callable(model):
        raise RuntimeError("LightningModule.model must be callable")

    x_min = float(spec["x_min"])
    x_max = float(spec["x_max"])
    n_points = int(spec["n_points"])
    if n_points < 2:
        raise RuntimeError("spec.n_points must be >= 2")
    if not (x_max > x_min):
        raise RuntimeError("spec.x_max must be > spec.x_min")

    x = np.linspace(x_min, x_max, n_points, dtype=np.float32).reshape(-1, 1)
    x_t = torch.from_numpy(x)
    y_true = torch.sin(x_t)

    lightning_module.eval()
    with torch.no_grad():
        y_pred = model(x_t)

    if not isinstance(y_pred, torch.Tensor):
        raise RuntimeError("model(x) must return a torch.Tensor")
    if y_pred.shape != y_true.shape:
        raise RuntimeError(f"y_pred shape {tuple(y_pred.shape)} != y_true shape {tuple(y_true.shape)}")

    mse = torch.mean((y_pred - y_true) ** 2).item()
    mae = torch.mean(torch.abs(y_pred - y_true)).item()

    return {
        "primary_score": float(mse),
        "metrics": {
            "mse": float(mse),
            "mae": float(mae),
            "x_min": x_min,
            "x_max": x_max,
            "n_points": n_points,
        },
    }