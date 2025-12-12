from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

import typer

from .config import ExperimentConfig
from .llm_config import LLMExperimentConfig
from .llm_training import run_llm_training
from .training import run_training

app = typer.Typer()


def _load_payload(config_path: Path) -> dict[str, Any]:
    """Return the raw YAML payload as a dictionary."""
    path = config_path.resolve()
    if not path.exists():
        msg = f"Config file {path} is missing."
        raise FileNotFoundError(msg)
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        msg = "Config root must be a mapping."
        raise ValueError(msg)
    return payload


def _looks_like_llm_config(payload: dict[str, Any]) -> bool:
    """Heuristic that flags configs meant for causal LLM runs."""
    data_section = payload.get("data")
    if not isinstance(data_section, dict):
        return False
    return {"system_prompt", "template"} <= set(data_section)


@app.command()
def train(config_path: Path) -> None:
    """
    Fine-tune the provided config. Detects masked vs causal LLM automatically.

    Example:
        uv run python -m aip_c01_prep.cli train configs/local_example.yaml
        uv run python -m aip_c01_prep.cli train configs/tinyllama_example.yaml
    """

    payload = _load_payload(config_path)
    if _looks_like_llm_config(payload):
        config = LLMExperimentConfig.model_validate(payload)
        _, metrics = run_llm_training(config)
    else:
        config = ExperimentConfig.model_validate(payload)
        _, metrics = run_training(config)
    typer.echo(metrics)


@app.command()
def train_llm(config_path: Path) -> None:
    """
    Fine-tune the configured causal LLM on the SaaS CSV.

    Example:
        uv run python -m aip_c01_prep.cli train-llm configs/tinyllama_example.yaml
    """

    config = LLMExperimentConfig.from_yaml(config_path.resolve())
    _, metrics = run_llm_training(config)
    typer.echo(metrics)

if __name__ == "__main__":
    app()

