"""Benchmark and evaluation API routes."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from threading import Thread

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

from ..benchmark import compute_bleu_score, compute_rouge_l_score, generate_response, load_model_and_tokenizer
from ..models import (
    Benchmark,
    BenchmarkCreateRequest,
    BenchmarkEvalListResponse,
    BenchmarkEvalRequest,
    BenchmarkEvalResult,
    BenchmarkEvalStartResponse,
    BenchmarkListResponse,
    BenchmarkRunScore,
    BenchmarkStatus,
    BenchmarkUpdateRequest,
    EvaluationComparisonItem,
    EvaluationComparisonResponse,
    ExperimentResult,
    ExperimentStatus,
)
from ..storage import (
    delete_benchmark as storage_delete_benchmark,
    delete_benchmark_eval as storage_delete_benchmark_eval,
    get_benchmark,
    get_benchmark_eval,
    get_experiment,
    list_benchmark_evals,
    list_benchmark_evals_by_benchmark,
    list_benchmarks,
    save_benchmark,
    save_benchmark_eval,
)
from .helpers import now

router = APIRouter(tags=["benchmarks"])


@router.post("/benchmarks", response_model=Benchmark)
def create_benchmark(request: BenchmarkCreateRequest) -> Benchmark:
    benchmark_id = str(uuid.uuid4())
    benchmark = Benchmark(
        id=benchmark_id,
        name=request.name,
        question=request.question,
        gold_answer=request.gold_answer,
        max_new_tokens=request.max_new_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
        created_at=now(),
    )
    save_benchmark(benchmark)
    return benchmark


@router.get("/benchmarks", response_model=BenchmarkListResponse)
def list_all_benchmarks() -> BenchmarkListResponse:
    return BenchmarkListResponse(benchmarks=list_benchmarks())


@router.get("/benchmarks/{benchmark_id}", response_model=Benchmark)
def get_benchmark_by_id(benchmark_id: str) -> Benchmark:
    benchmark = get_benchmark(benchmark_id)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return benchmark


@router.put("/benchmarks/{benchmark_id}", response_model=Benchmark)
def update_benchmark(benchmark_id: str, request: BenchmarkUpdateRequest) -> Benchmark:
    benchmark = get_benchmark(benchmark_id)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    
    if request.name is not None:
        benchmark.name = request.name
    if request.question is not None:
        benchmark.question = request.question
    if request.gold_answer is not None:
        benchmark.gold_answer = request.gold_answer
    if request.max_new_tokens is not None:
        benchmark.max_new_tokens = request.max_new_tokens
    if request.temperature is not None:
        benchmark.temperature = request.temperature
    if request.top_p is not None:
        benchmark.top_p = request.top_p
    
    save_benchmark(benchmark)
    return benchmark


@router.delete("/benchmarks/{benchmark_id}")
def delete_benchmark(benchmark_id: str) -> dict[str, str]:
    if not storage_delete_benchmark(benchmark_id):
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return {"status": "deleted", "benchmark_id": benchmark_id}


def _run_benchmark_eval(
    eval_id: str,
    benchmark: Benchmark,
    experiment: ExperimentResult,
    num_runs: int,
) -> None:
    eval_result = get_benchmark_eval(eval_id)
    eval_result.status = BenchmarkStatus.RUNNING
    eval_result.num_runs = num_runs
    save_benchmark_eval(eval_result)

    try:
        model_path = Path(experiment.output_dir)
        model, tokenizer = load_model_and_tokenizer(model_path)

        run_scores: list[BenchmarkRunScore] = []
        for run_num in range(1, num_runs + 1):
            model_answer = generate_response(
                model=model,
                tokenizer=tokenizer,
                prompt=benchmark.question,
                max_new_tokens=benchmark.max_new_tokens,
                temperature=benchmark.temperature,
                top_p=benchmark.top_p,
            )
            bleu = compute_bleu_score(model_answer, benchmark.gold_answer)
            rouge = compute_rouge_l_score(model_answer, benchmark.gold_answer)
            run_scores.append(BenchmarkRunScore(
                run_number=run_num,
                model_answer=model_answer,
                bleu_score=bleu,
                rouge_score=rouge,
            ))

        eval_result.run_scores = run_scores
        eval_result.model_answer = run_scores[-1].model_answer
        eval_result.bleu_score = sum(r.bleu_score for r in run_scores) / len(run_scores)
        eval_result.rouge_score = sum(r.rouge_score for r in run_scores) / len(run_scores)
        eval_result.status = BenchmarkStatus.COMPLETED
    except Exception as e:
        eval_result.status = BenchmarkStatus.FAILED
        eval_result.error = str(e)
    finally:
        eval_result.completed_at = now()
        save_benchmark_eval(eval_result)


@router.post("/benchmarks/{benchmark_id}/evaluate", response_model=BenchmarkEvalStartResponse)
def start_benchmark_evaluation(benchmark_id: str, request: BenchmarkEvalRequest) -> BenchmarkEvalStartResponse:
    benchmark = get_benchmark(benchmark_id)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    experiment = get_experiment(request.experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if experiment.status != ExperimentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Experiment has not completed")
    if not experiment.output_dir:
        raise HTTPException(status_code=400, detail="Experiment has no output directory")

    model_path = Path(experiment.output_dir)
    if not model_path.exists():
        raise HTTPException(status_code=400, detail=f"Model path '{experiment.output_dir}' not found")

    eval_id = str(uuid.uuid4())
    eval_result = BenchmarkEvalResult(
        id=eval_id,
        benchmark_id=benchmark_id,
        benchmark_name=benchmark.name,
        experiment_id=request.experiment_id,
        question=benchmark.question,
        gold_answer=benchmark.gold_answer,
        model_answer="",
        bleu_score=0.0,
        rouge_score=0.0,
        num_runs=request.num_runs,
        status=BenchmarkStatus.PENDING,
        started_at=now(),
    )
    save_benchmark_eval(eval_result)

    thread = Thread(target=_run_benchmark_eval, args=(eval_id, benchmark, experiment, request.num_runs))
    thread.start()

    return BenchmarkEvalStartResponse(
        eval_id=eval_id,
        status=BenchmarkStatus.PENDING,
        message="Benchmark evaluation started",
    )


@router.get("/benchmarks/{benchmark_id}/evaluations", response_model=BenchmarkEvalListResponse)
def list_benchmark_evaluations(benchmark_id: str) -> BenchmarkEvalListResponse:
    benchmark = get_benchmark(benchmark_id)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return BenchmarkEvalListResponse(evaluations=list_benchmark_evals_by_benchmark(benchmark_id))


@router.get("/evaluations", response_model=BenchmarkEvalListResponse)
def list_all_evaluations() -> BenchmarkEvalListResponse:
    return BenchmarkEvalListResponse(evaluations=list_benchmark_evals())


@router.get("/evaluations/compare", response_model=EvaluationComparisonResponse)
def compare_evaluations() -> EvaluationComparisonResponse:
    evals = list_benchmark_evals()
    items = []
    for ev in evals:
        if ev.status != BenchmarkStatus.COMPLETED:
            continue
        exp = get_experiment(ev.experiment_id)
        if not exp:
            continue
        cfg = exp.config
        model_name = cfg.model.pretrained_model_name
        learning_rate = cfg.training.learning_rate
        num_epochs = cfg.training.num_train_epochs
        batch_size = cfg.training.per_device_train_batch_size
        lora_r = None
        lora_alpha = None
        if hasattr(cfg, "peft") and cfg.peft and cfg.peft.enabled:
            lora_r = cfg.peft.r
            lora_alpha = cfg.peft.lora_alpha
        items.append(
            EvaluationComparisonItem(
                eval_id=ev.id,
                experiment_id=ev.experiment_id,
                benchmark_name=ev.benchmark_name,
                question=ev.question,
                model_name=model_name,
                dataset_filename=exp.dataset_filename or "unknown",
                bleu_score=ev.bleu_score,
                rouge_score=ev.rouge_score,
                learning_rate=learning_rate,
                num_epochs=num_epochs,
                batch_size=batch_size,
                lora_r=lora_r,
                lora_alpha=lora_alpha,
                started_at=ev.started_at,
                completed_at=ev.completed_at,
            )
        )
    items.sort(key=lambda x: x.rouge_score, reverse=True)
    return EvaluationComparisonResponse(evaluations=items)


@router.get("/evaluations/{eval_id}", response_model=BenchmarkEvalResult)
def get_evaluation(eval_id: str) -> BenchmarkEvalResult:
    eval_result = get_benchmark_eval(eval_id)
    if not eval_result:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return eval_result


@router.delete("/evaluations/{eval_id}")
def delete_evaluation(eval_id: str) -> dict[str, str]:
    if not storage_delete_benchmark_eval(eval_id):
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return {"status": "deleted", "eval_id": eval_id}


# Exported for use in experiment_routes and autotune_routes
def _run_benchmark_eval_sync(eval_id: str, benchmark: Benchmark, experiment: ExperimentResult) -> None:
    """Run benchmark evaluation synchronously."""
    logger.info(f"Benchmark eval {eval_id}: Starting evaluation for experiment {experiment.id}")
    eval_result = get_benchmark_eval(eval_id)
    eval_result.status = BenchmarkStatus.RUNNING
    save_benchmark_eval(eval_result)

    try:
        model_path = Path(experiment.output_dir)
        logger.info(f"Benchmark eval {eval_id}: Loading model from {model_path}")
        model, tokenizer = load_model_and_tokenizer(model_path)

        logger.info(f"Benchmark eval {eval_id}: Generating response")
        model_answer = generate_response(
            model=model,
            tokenizer=tokenizer,
            prompt=benchmark.question,
            max_new_tokens=benchmark.max_new_tokens,
            temperature=benchmark.temperature,
            top_p=benchmark.top_p,
        )
        logger.info(f"Benchmark eval {eval_id}: Model answer length={len(model_answer)}")

        bleu_score = compute_bleu_score(model_answer, benchmark.gold_answer)
        rouge_score = compute_rouge_l_score(model_answer, benchmark.gold_answer)
        logger.info(f"Benchmark eval {eval_id}: BLEU={bleu_score:.2f}, ROUGE={rouge_score:.2f}")

        eval_result.model_answer = model_answer
        eval_result.bleu_score = bleu_score
        eval_result.rouge_score = rouge_score
        eval_result.status = BenchmarkStatus.COMPLETED
    except Exception as e:
        logger.exception(f"Benchmark eval {eval_id}: Failed with error: {e}")
        eval_result.status = BenchmarkStatus.FAILED
        eval_result.error = str(e)
    finally:
        eval_result.completed_at = now()
        save_benchmark_eval(eval_result)

