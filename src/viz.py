from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

import plotly.graph_objects as go


def _collect_series(
    log_history: Iterable[Mapping[str, float]],
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    train_loss: list[tuple[int, float]] = []
    eval_loss: list[tuple[int, float]] = []
    for entry in log_history:
        step_raw = entry.get("step")
        if step_raw is None:
            continue
        step = int(step_raw)
        if "loss" in entry:
            train_loss.append((step, float(entry["loss"])))
        if "eval_loss" in entry:
            eval_loss.append((step, float(entry["eval_loss"])))
    return train_loss, eval_loss


def save_loss_curve(
    log_history: Iterable[Mapping[str, float]],
    output_path: Path,
    title: str,
) -> Path:
    """
    Persist a Plotly HTML chart showing train/eval loss curves.

    Raises:
        ValueError: If no loss metrics exist in the log history.
    """

    train_loss, eval_loss = _collect_series(log_history)
    if not train_loss and not eval_loss:
        msg = "Log history does not contain loss metrics."
        raise ValueError(msg)
    figure = go.Figure()
    if train_loss:
        figure.add_trace(
            go.Scatter(
                x=[point[0] for point in train_loss],
                y=[point[1] for point in train_loss],
                mode="lines+markers",
                name="train_loss",
            )
        )
    if eval_loss:
        figure.add_trace(
            go.Scatter(
                x=[point[0] for point in eval_loss],
                y=[point[1] for point in eval_loss],
                mode="lines+markers",
                name="eval_loss",
            )
        )
    figure.update_layout(
        title=title,
        xaxis_title="Global Step",
        yaxis_title="Loss",
        template="plotly_white",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(str(output_path), include_plotlyjs="cdn", full_html=True)
    return output_path

