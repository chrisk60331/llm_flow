"""Benchmark-related Pydantic models."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, PositiveFloat, PositiveInt

from .enums import BenchmarkStatus


class Benchmark(BaseModel):
    id: str
    name: str
    question: str
    gold_answer: str
    max_new_tokens: int = 128
    temperature: float = 0.7
    top_p: float = 0.9
    created_at: datetime


class BenchmarkCreateRequest(BaseModel):
    name: str = Field(description="Name for this benchmark")
    question: str = Field(description="The question to ask the model")
    gold_answer: str = Field(description="The expected/gold standard answer")
    max_new_tokens: PositiveInt = Field(default=128, description="Maximum tokens to generate")
    temperature: PositiveFloat = Field(default=0.7, description="Sampling temperature")
    top_p: PositiveFloat = Field(default=0.9, description="Top-p sampling parameter")


class BenchmarkUpdateRequest(BaseModel):
    name: str | None = Field(default=None, description="Name for this benchmark")
    question: str | None = Field(default=None, description="The question to ask the model")
    gold_answer: str | None = Field(default=None, description="The expected/gold standard answer")
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
    experiment_id: str
    question: str
    gold_answer: str
    model_answer: str
    bleu_score: float
    rouge_score: float
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
    question: str
    model_name: str
    dataset_filename: str
    bleu_score: float
    rouge_score: float
    learning_rate: float
    num_epochs: float
    batch_size: int
    lora_r: int | None = None
    lora_alpha: int | None = None
    started_at: datetime
    completed_at: datetime | None = None


class EvaluationComparisonResponse(BaseModel):
    evaluations: list[EvaluationComparisonItem]

