"""Custom training callbacks for streaming logs."""
from __future__ import annotations

import json
from pathlib import Path

from transformers import TrainerCallback, TrainerControl, TrainerState, TrainingArguments


class StreamingLogsCallback(TrainerCallback):
    """Callback that writes training logs incrementally to a JSON file."""

    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def on_log(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs,
    ) -> None:
        with self.output_path.open("w") as f:
            json.dump(state.log_history, f, indent=2)
