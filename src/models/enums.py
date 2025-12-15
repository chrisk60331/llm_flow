"""Enum types for the application."""
from enum import Enum


class ExperimentType(str, Enum):
    MASKED_LM = "masked_lm"
    CAUSAL_LM = "causal_lm"
    CUSTOM_LIGHTNING = "custom_lightning"


class ExperimentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class BenchmarkStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BenchmarkType(str, Enum):
    CAUSAL_LM_QA = "causal_lm_qa"
    MASKED_LM_FILL_MASK = "masked_lm_fill_mask"
    CUSTOM_LIGHTNING_SIN_REGRESSION = "custom_lightning_sin_regression"
    CUSTOM_LIGHTNING_PLUGIN = "custom_lightning_plugin"


class AutoTuneStatus(str, Enum):
    PENDING = "pending"
    PROBING = "probing"
    TRAINING = "training"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"

