"""Benchmark and evaluation storage operations."""
from __future__ import annotations

import json
from datetime import datetime

from ..models import Benchmark, BenchmarkEvalResult, BenchmarkStatus, BenchmarkType
from .database import get_connection


# --- Benchmark operations ---


def save_benchmark(benchmark: Benchmark) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO benchmarks 
            (id, name, benchmark_type, spec_json, question, gold_answer, max_new_tokens, temperature, top_p, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                benchmark.id,
                benchmark.name,
                benchmark.benchmark_type.value,
                json.dumps(benchmark.spec),
                benchmark.question,
                benchmark.gold_answer,
                benchmark.max_new_tokens,
                benchmark.temperature,
                benchmark.top_p,
                benchmark.created_at.isoformat(),
            ),
        )
        conn.commit()


def get_benchmark(benchmark_id: str) -> Benchmark | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM benchmarks WHERE id = ?", (benchmark_id,)).fetchone()
        if not row:
            return None
        spec = {}
        try:
            spec = json.loads(row["spec_json"] or "{}")
        except Exception:
            spec = {}
        benchmark_type = BenchmarkType.CAUSAL_LM_QA
        if "benchmark_type" in row.keys() and row["benchmark_type"]:
            benchmark_type = BenchmarkType(row["benchmark_type"])
        return Benchmark(
            id=row["id"],
            name=row["name"],
            benchmark_type=benchmark_type,
            spec=spec,
            question=row["question"],
            gold_answer=row["gold_answer"],
            max_new_tokens=row["max_new_tokens"],
            temperature=row["temperature"],
            top_p=row["top_p"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


def list_benchmarks() -> list[Benchmark]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM benchmarks ORDER BY created_at DESC").fetchall()
        results: list[Benchmark] = []
        for row in rows:
            spec = {}
            try:
                spec = json.loads(row["spec_json"] or "{}")
            except Exception:
                spec = {}
            benchmark_type = BenchmarkType.CAUSAL_LM_QA
            if "benchmark_type" in row.keys() and row["benchmark_type"]:
                benchmark_type = BenchmarkType(row["benchmark_type"])
            results.append(
                Benchmark(
                    id=row["id"],
                    name=row["name"],
                    benchmark_type=benchmark_type,
                    spec=spec,
                    question=row["question"],
                    gold_answer=row["gold_answer"],
                    max_new_tokens=row["max_new_tokens"],
                    temperature=row["temperature"],
                    top_p=row["top_p"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return results


def delete_benchmark(benchmark_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM benchmarks WHERE id = ?", (benchmark_id,))
        conn.commit()
        return cursor.rowcount > 0


# --- Benchmark Eval operations ---


def save_benchmark_eval(eval_result: BenchmarkEvalResult) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO benchmark_evals
            (id, benchmark_id, benchmark_name, benchmark_type, experiment_id, question, gold_answer, model_answer, bleu_score, rouge_score, primary_score, metrics_json, num_runs, run_scores_json, status, started_at, completed_at, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                eval_result.id,
                eval_result.benchmark_id,
                eval_result.benchmark_name,
                eval_result.benchmark_type.value,
                eval_result.experiment_id,
                eval_result.question,
                eval_result.gold_answer,
                eval_result.model_answer,
                eval_result.bleu_score,
                eval_result.rouge_score,
                float(eval_result.primary_score),
                json.dumps(eval_result.metrics),
                int(eval_result.num_runs),
                json.dumps([rs.model_dump() for rs in eval_result.run_scores]),
                eval_result.status.value,
                eval_result.started_at.isoformat(),
                eval_result.completed_at.isoformat() if eval_result.completed_at else None,
                eval_result.error,
            ),
        )
        conn.commit()


def get_benchmark_eval(eval_id: str) -> BenchmarkEvalResult | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM benchmark_evals WHERE id = ?", (eval_id,)).fetchone()
        if not row:
            return None
        metrics = {}
        try:
            metrics = json.loads(row["metrics_json"] or "{}")
        except Exception:
            metrics = {}
        run_scores = []
        try:
            raw = json.loads(row["run_scores_json"] or "[]")
            if isinstance(raw, list):
                run_scores = raw
        except Exception:
            run_scores = []
        benchmark_type = BenchmarkType.CAUSAL_LM_QA
        if "benchmark_type" in row.keys() and row["benchmark_type"]:
            benchmark_type = BenchmarkType(row["benchmark_type"])
        return BenchmarkEvalResult(
            id=row["id"],
            benchmark_id=row["benchmark_id"],
            benchmark_name=row["benchmark_name"],
            benchmark_type=benchmark_type,
            experiment_id=row["experiment_id"],
            question=row["question"],
            gold_answer=row["gold_answer"],
            model_answer=row["model_answer"],
            bleu_score=row["bleu_score"],
            rouge_score=row["rouge_score"] or 0.0,
            primary_score=float(row["primary_score"] or 0.0),
            metrics=metrics,
            num_runs=int(row["num_runs"] or 1),
            run_scores=run_scores,  # pydantic will coerce into BenchmarkRunScore
            status=BenchmarkStatus(row["status"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            error=row["error"],
        )


def list_benchmark_evals() -> list[BenchmarkEvalResult]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM benchmark_evals ORDER BY started_at DESC").fetchall()
        results: list[BenchmarkEvalResult] = []
        for row in rows:
            metrics = {}
            try:
                metrics = json.loads(row["metrics_json"] or "{}")
            except Exception:
                metrics = {}
            run_scores = []
            try:
                raw = json.loads(row["run_scores_json"] or "[]")
                if isinstance(raw, list):
                    run_scores = raw
            except Exception:
                run_scores = []
            benchmark_type = BenchmarkType.CAUSAL_LM_QA
            if "benchmark_type" in row.keys() and row["benchmark_type"]:
                benchmark_type = BenchmarkType(row["benchmark_type"])
            results.append(
                BenchmarkEvalResult(
                    id=row["id"],
                    benchmark_id=row["benchmark_id"],
                    benchmark_name=row["benchmark_name"],
                    benchmark_type=benchmark_type,
                    experiment_id=row["experiment_id"],
                    question=row["question"],
                    gold_answer=row["gold_answer"],
                    model_answer=row["model_answer"],
                    bleu_score=row["bleu_score"],
                    rouge_score=row["rouge_score"] or 0.0,
                    primary_score=float(row["primary_score"] or 0.0),
                    metrics=metrics,
                    num_runs=int(row["num_runs"] or 1),
                    run_scores=run_scores,
                    status=BenchmarkStatus(row["status"]),
                    started_at=datetime.fromisoformat(row["started_at"]),
                    completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                    error=row["error"],
                )
            )
        return results


def list_benchmark_evals_by_benchmark(benchmark_id: str) -> list[BenchmarkEvalResult]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM benchmark_evals WHERE benchmark_id = ? ORDER BY started_at DESC",
            (benchmark_id,),
        ).fetchall()
        results: list[BenchmarkEvalResult] = []
        for row in rows:
            metrics = {}
            try:
                metrics = json.loads(row["metrics_json"] or "{}")
            except Exception:
                metrics = {}
            run_scores = []
            try:
                raw = json.loads(row["run_scores_json"] or "[]")
                if isinstance(raw, list):
                    run_scores = raw
            except Exception:
                run_scores = []
            benchmark_type = BenchmarkType.CAUSAL_LM_QA
            if "benchmark_type" in row.keys() and row["benchmark_type"]:
                benchmark_type = BenchmarkType(row["benchmark_type"])
            results.append(
                BenchmarkEvalResult(
                    id=row["id"],
                    benchmark_id=row["benchmark_id"],
                    benchmark_name=row["benchmark_name"],
                    benchmark_type=benchmark_type,
                    experiment_id=row["experiment_id"],
                    question=row["question"],
                    gold_answer=row["gold_answer"],
                    model_answer=row["model_answer"],
                    bleu_score=row["bleu_score"],
                    rouge_score=row["rouge_score"] or 0.0,
                    primary_score=float(row["primary_score"] or 0.0),
                    metrics=metrics,
                    num_runs=int(row["num_runs"] or 1),
                    run_scores=run_scores,
                    status=BenchmarkStatus(row["status"]),
                    started_at=datetime.fromisoformat(row["started_at"]),
                    completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                    error=row["error"],
                )
            )
        return results


def delete_benchmark_eval(eval_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM benchmark_evals WHERE id = ?", (eval_id,))
        conn.commit()
        return cursor.rowcount > 0

