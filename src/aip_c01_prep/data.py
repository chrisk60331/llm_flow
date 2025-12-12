from __future__ import annotations

from typing import Callable

import pandas as pd
from datasets import Dataset, DatasetDict
from transformers import PreTrainedTokenizerBase

from .config import DataConfig


def build_text_column(frame: pd.DataFrame, config: DataConfig) -> pd.Series:
    """Join the requested columns with the configured separator."""
    missing = [col for col in config.text_fields if col not in frame.columns]
    if missing:
        msg = f"Columns {missing} were not found in {config.csv_path}"
        raise KeyError(msg)
    return frame[list(config.text_fields)].astype(str).agg(
        config.separator.join, axis=1
    )


def load_dataset(config: DataConfig) -> DatasetDict:
    """Load the CSV and return HF dataset splits."""
    frame = pd.read_csv(config.csv_path)
    frame["text"] = build_text_column(frame, config)
    dataset = Dataset.from_pandas(frame[["text"]], preserve_index=False)
    return dataset.train_test_split(test_size=config.validation_split, seed=config.seed)


def tokenize_dataset(
    dataset: DatasetDict,
    tokenizer: PreTrainedTokenizerBase,
    max_length: int,
) -> DatasetDict:
    """Tokenize both splits with truncation/padding."""
    tokenization_fn: Callable[[dict[str, list[str]]], dict[str, list[list[int]]]] = (
        lambda samples: tokenizer(
            samples["text"],
            truncation=True,
            padding="max_length",
            max_length=max_length,
        )
    )
    return dataset.map(tokenization_fn, batched=True, remove_columns=["text"])

