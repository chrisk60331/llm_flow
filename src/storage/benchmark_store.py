"""Benchmark and evaluation storage operations."""
from __future__ import annotations

from datetime import datetime

from ..models import Benchmark, BenchmarkEvalResult, BenchmarkStatus
from .database import get_connection


# --- Benchmark operations ---


def save_benchmark(benchmark: Benchmark) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO benchmarks 
            (id, name, question, gold_answer, max_new_tokens, temperature, top_p, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                benchmark.id,
                benchmark.name,
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
        return Benchmark(
            id=row["id"],
            name=row["name"],
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
        return [
            Benchmark(
                id=row["id"],
                name=row["name"],
                question=row["question"],
                gold_answer=row["gold_answer"],
                max_new_tokens=row["max_new_tokens"],
                temperature=row["temperature"],
                top_p=row["top_p"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]


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
            (id, benchmark_id, benchmark_name, experiment_id, question, gold_answer, model_answer, bleu_score, rouge_score, status, started_at, completed_at, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                eval_result.id,
                eval_result.benchmark_id,
                eval_result.benchmark_name,
                eval_result.experiment_id,
                eval_result.question,
                eval_result.gold_answer,
                eval_result.model_answer,
                eval_result.bleu_score,
                eval_result.rouge_score,
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
        return BenchmarkEvalResult(
            id=row["id"],
            benchmark_id=row["benchmark_id"],
            benchmark_name=row["benchmark_name"],
            experiment_id=row["experiment_id"],
            question=row["question"],
            gold_answer=row["gold_answer"],
            model_answer=row["model_answer"],
            bleu_score=row["bleu_score"],
            rouge_score=row["rouge_score"] or 0.0,
            status=BenchmarkStatus(row["status"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            error=row["error"],
        )


def list_benchmark_evals() -> list[BenchmarkEvalResult]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM benchmark_evals ORDER BY started_at DESC").fetchall()
        return [
            BenchmarkEvalResult(
                id=row["id"],
                benchmark_id=row["benchmark_id"],
                benchmark_name=row["benchmark_name"],
                experiment_id=row["experiment_id"],
                question=row["question"],
                gold_answer=row["gold_answer"],
                model_answer=row["model_answer"],
                bleu_score=row["bleu_score"],
                rouge_score=row["rouge_score"] or 0.0,
                status=BenchmarkStatus(row["status"]),
                started_at=datetime.fromisoformat(row["started_at"]),
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                error=row["error"],
            )
            for row in rows
        ]


def list_benchmark_evals_by_benchmark(benchmark_id: str) -> list[BenchmarkEvalResult]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM benchmark_evals WHERE benchmark_id = ? ORDER BY started_at DESC",
            (benchmark_id,),
        ).fetchall()
        return [
            BenchmarkEvalResult(
                id=row["id"],
                benchmark_id=row["benchmark_id"],
                benchmark_name=row["benchmark_name"],
                experiment_id=row["experiment_id"],
                question=row["question"],
                gold_answer=row["gold_answer"],
                model_answer=row["model_answer"],
                bleu_score=row["bleu_score"],
                rouge_score=row["rouge_score"] or 0.0,
                status=BenchmarkStatus(row["status"]),
                started_at=datetime.fromisoformat(row["started_at"]),
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                error=row["error"],
            )
            for row in rows
        ]


def delete_benchmark_eval(eval_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM benchmark_evals WHERE id = ?", (eval_id,))
        conn.commit()
        return cursor.rowcount > 0

