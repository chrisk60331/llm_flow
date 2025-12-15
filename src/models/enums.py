"""Enum types for the application."""
from enum import Enum


class ExperimentType(str, Enum):
    MASKED_LM = "masked_lm"
    CAUSAL_LM = "causal_lm"


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


class AutoTuneStatus(str, Enum):
    PENDING = "pending"
    PROBING = "probing"
    TRAINING = "training"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"

