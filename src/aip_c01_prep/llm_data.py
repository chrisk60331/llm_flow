from __future__ import annotations

from typing import Iterable

import pandas as pd
from datasets import Dataset, DatasetDict

from .llm_config import LLMDataConfig


def _assert_columns(frame: pd.DataFrame, config: LLMDataConfig) -> None:
    columns = {config.question_field, config.answer_field}
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        msg = f"Columns {missing} were not found in {config.csv_path}"
        raise KeyError(msg)


def _format_rows(
    rows: Iterable[dict[str, object]],
    config: LLMDataConfig,
) -> list[str]:
    formatted_rows = []
    for row in rows:
        formatted_rows.append(
            config.template.format(
                system_prompt=config.system_prompt,
                question=str(row[config.question_field]),
                answer=str(row[config.answer_field]),
            )
        )
    return formatted_rows


def load_llm_dataset(config: LLMDataConfig) -> DatasetDict:
    """Read the CSV and return HF dataset splits for causal LM."""
    frame = pd.read_csv(config.csv_path)
    _assert_columns(frame, config)
    formatted = _format_rows(frame.to_dict(orient="records"), config)
    dataset = Dataset.from_dict({"text": formatted})
    return dataset.train_test_split(test_size=config.validation_split, seed=config.seed)

