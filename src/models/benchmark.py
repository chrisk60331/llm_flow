"""Benchmark-related Pydantic models."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, PositiveFloat, PositiveInt

from .enums import BenchmarkStatus, BenchmarkType


class Benchmark(BaseModel):
    id: str
    name: str
    benchmark_type: BenchmarkType = Field(default=BenchmarkType.CAUSAL_LM_QA)
    spec: dict[str, Any] = Field(default_factory=dict, description="Type-specific benchmark spec blob.")
    question: str = ""
    gold_answer: str = ""
    max_new_tokens: int = 128
    temperature: float = 0.7
    top_p: float = 0.9
    created_at: datetime


class BenchmarkCreateRequest(BaseModel):
    name: str = Field(description="Name for this benchmark")
    benchmark_type: BenchmarkType = Field(default=BenchmarkType.CAUSAL_LM_QA)
    spec: dict[str, Any] = Field(default_factory=dict, description="Type-specific benchmark spec blob.")
    question: str = Field(default="", description="The question to ask the model (type-dependent)")
    gold_answer: str = Field(default="", description="The expected/gold standard answer (type-dependent)")
    max_new_tokens: PositiveInt = Field(default=128, description="Maximum tokens to generate")
    temperature: PositiveFloat = Field(default=0.7, description="Sampling temperature")
    top_p: PositiveFloat = Field(default=0.9, description="Top-p sampling parameter")


class BenchmarkUpdateRequest(BaseModel):
    name: str | None = Field(default=None, description="Name for this benchmark")
    benchmark_type: BenchmarkType | None = Field(default=None, description="Benchmark type (immutable once created)")
    spec: dict[str, Any] | None = Field(default=None, description="Type-specific benchmark spec blob.")
    question: str | None = Field(default=None, description="The question to ask the model (type-dependent)")
    gold_answer: str | None = Field(default=None, description="The expected/gold standard answer (type-dependent)")
    max_new_tokens: PositiveInt | None = Field(default=None, description="Maximum tokens to generate")
    temperature: PositiveFloat | None = Field(default=None, description="Sampling temperature")
    top_p: PositiveFloat | None = Field(default=None, description="Top-p sampling parameter")


class BenchmarkListResponse(BaseModel):
    benchmarks: list[Benchmark]


class BenchmarkRunScore(BaseModel):
    run_number: int
    model_answer: str
    bleu_score: float
    rouge_score: float


class BenchmarkEvalResult(BaseModel):
    id: str
    benchmark_id: str
    benchmark_name: str
    benchmark_type: BenchmarkType = Field(default=BenchmarkType.CAUSAL_LM_QA)
    experiment_id: str
    question: str
    gold_answer: str
    model_answer: str
    bleu_score: float
    rouge_score: float
    primary_score: float = 0.0
    metrics: dict[str, Any] = Field(default_factory=dict)
    num_runs: int = 1
    run_scores: list[BenchmarkRunScore] = Field(default_factory=list)
    status: BenchmarkStatus
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


class BenchmarkEvalRequest(BaseModel):
    experiment_id: str = Field(description="Experiment ID to evaluate")
    max_new_tokens: PositiveInt = Field(default=128)
    temperature: PositiveFloat = Field(default=0.7)
    top_p: PositiveFloat = Field(default=0.9)
    num_runs: PositiveInt = Field(default=1, description="Number of times to run evaluation and average scores")


class BenchmarkEvalStartResponse(BaseModel):
    eval_id: str
    status: BenchmarkStatus
    message: str


class BenchmarkEvalListResponse(BaseModel):
    evaluations: list[BenchmarkEvalResult]


# --- Evaluation Comparison Models ---


class EvaluationComparisonItem(BaseModel):
    eval_id: str
    experiment_id: str
    benchmark_name: str
    benchmark_type: BenchmarkType = Field(default=BenchmarkType.CAUSAL_LM_QA)
    question: str
    model_name: str
    dataset_filename: str
    bleu_score: float
    rouge_score: float
    primary_score: float = 0.0
    learning_rate: float | None = None
    num_epochs: float | None = None
    batch_size: int | None = None
    lora_r: int | None = None
    lora_alpha: int | None = None
    started_at: datetime
    completed_at: datetime | None = None


class EvaluationComparisonResponse(BaseModel):
    evaluations: list[EvaluationComparisonItem]

