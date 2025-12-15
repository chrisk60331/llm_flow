"""Custom training callbacks for streaming logs and stopping."""
from __future__ import annotations

import json
from pathlib import Path

from transformers import TrainerCallback, TrainerControl, TrainerState, TrainingArguments

# Global registry for manual stop requests (experiment_id -> should_stop)
stop_registry: dict[str, bool] = {}

# Global registry for live progress (experiment_id -> progress_dict)
progress_registry: dict[str, dict] = {}


class StreamingLogsCallback(TrainerCallback):
    """Callback that writes training logs incrementally to a JSON file."""

    def __init__(self, output_path: Path, experiment_id: str | None = None) -> None:
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.experiment_id = experiment_id

    def on_log(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs,
    ) -> None:
        with self.output_path.open("w") as f:
            json.dump(state.log_history, f, indent=2)
    
    def on_step_end(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs,
    ) -> None:
        # Update live progress for real-time UI updates
        if self.experiment_id:
            progress_registry[self.experiment_id] = {
                "global_step": state.global_step,
                "epoch": state.epoch,
                "max_steps": state.max_steps,
            }


class StopCheckCallback(TrainerCallback):
    """Callback that checks for manual stop requests."""

    def __init__(self, experiment_id: str) -> None:
        self.experiment_id = experiment_id

    def on_step_end(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs,
    ) -> None:
        if stop_registry.get(self.experiment_id):
            control.should_training_stop = True

