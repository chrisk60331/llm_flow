"""Benchmark and evaluation API routes."""
from __future__ import annotations

import logging
import json
import subprocess
import sys
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
    BenchmarkType,
    BenchmarkUpdateRequest,
    EvaluationComparisonItem,
    EvaluationComparisonResponse,
    ExperimentResult,
    ExperimentStatus,
    ExperimentType,
    PluginKind,
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
    get_plugin,
)
from .helpers import now

router = APIRouter(tags=["benchmarks"])


@router.post("/benchmarks", response_model=Benchmark)
def create_benchmark(request: BenchmarkCreateRequest) -> Benchmark:
    benchmark_id = str(uuid.uuid4())
    if request.benchmark_type == BenchmarkType.CAUSAL_LM_QA:
        if not request.question.strip() or not request.gold_answer.strip():
            raise HTTPException(status_code=400, detail="question and gold_answer are required for causal_lm_qa")
    if request.benchmark_type == BenchmarkType.MASKED_LM_FILL_MASK:
        if "[MASK]" not in request.question and "<mask>" not in request.question:
            raise HTTPException(status_code=400, detail="masked_lm_fill_mask requires a mask token ([MASK] or <mask>) in question")
        if not request.gold_answer.strip():
            raise HTTPException(status_code=400, detail="gold_answer is required for masked_lm_fill_mask")
    if request.benchmark_type == BenchmarkType.CUSTOM_LIGHTNING_SIN_REGRESSION:
        spec = request.spec or {}
        if spec.get("task") != "sin":
            raise HTTPException(status_code=400, detail='custom_lightning_sin_regression requires spec.task == "sin"')
        for k in ("x_min", "x_max", "n_points"):
            if k not in spec:
                raise HTTPException(status_code=400, detail=f"custom_lightning_sin_regression requires spec.{k}")
    if request.benchmark_type == BenchmarkType.CUSTOM_LIGHTNING_PLUGIN:
        spec = request.spec or {}
        if "benchmark_plugin_id" not in spec:
            raise HTTPException(status_code=400, detail="custom_lightning_plugin requires spec.benchmark_plugin_id")
        if "benchmark_function_name" not in spec:
            raise HTTPException(status_code=400, detail="custom_lightning_plugin requires spec.benchmark_function_name")
        plugin_id = str(spec["benchmark_plugin_id"])
        fn_name = str(spec["benchmark_function_name"])
        plugin = get_plugin(plugin_id)
        if not plugin or plugin.kind != PluginKind.BENCHMARK:
            raise HTTPException(status_code=400, detail="benchmark_plugin_id does not refer to a benchmark plugin")
        discovered = set((plugin.symbols or {}).get("functions", []) or [])
        if fn_name not in discovered:
            raise HTTPException(status_code=400, detail="benchmark_function_name not found in plugin symbols")
    benchmark = Benchmark(
        id=benchmark_id,
        name=request.name,
        benchmark_type=request.benchmark_type,
        spec=request.spec,
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
    
    if request.benchmark_type is not None and request.benchmark_type != benchmark.benchmark_type:
        raise HTTPException(status_code=400, detail="benchmark_type is immutable once created")

    if request.name is not None:
        benchmark.name = request.name
    if request.question is not None:
        benchmark.question = request.question
    if request.gold_answer is not None:
        benchmark.gold_answer = request.gold_answer
    if request.spec is not None:
        benchmark.spec = request.spec
    if request.max_new_tokens is not None:
        benchmark.max_new_tokens = request.max_new_tokens
    if request.temperature is not None:
        benchmark.temperature = request.temperature
    if request.top_p is not None:
        benchmark.top_p = request.top_p

    if benchmark.benchmark_type == BenchmarkType.CAUSAL_LM_QA:
        if not benchmark.question.strip() or not benchmark.gold_answer.strip():
            raise HTTPException(status_code=400, detail="question and gold_answer are required for causal_lm_qa")
    if benchmark.benchmark_type == BenchmarkType.MASKED_LM_FILL_MASK:
        if "[MASK]" not in benchmark.question and "<mask>" not in benchmark.question:
            raise HTTPException(status_code=400, detail="masked_lm_fill_mask requires a mask token ([MASK] or <mask>) in question")
        if not benchmark.gold_answer.strip():
            raise HTTPException(status_code=400, detail="gold_answer is required for masked_lm_fill_mask")
    if benchmark.benchmark_type == BenchmarkType.CUSTOM_LIGHTNING_SIN_REGRESSION:
        if (benchmark.spec or {}).get("task") != "sin":
            raise HTTPException(status_code=400, detail='custom_lightning_sin_regression requires spec.task == "sin"')
    if benchmark.benchmark_type == BenchmarkType.CUSTOM_LIGHTNING_PLUGIN:
        spec = benchmark.spec or {}
        if "benchmark_plugin_id" not in spec:
            raise HTTPException(status_code=400, detail="custom_lightning_plugin requires spec.benchmark_plugin_id")
        if "benchmark_function_name" not in spec:
            raise HTTPException(status_code=400, detail="custom_lightning_plugin requires spec.benchmark_function_name")
        plugin_id = str(spec["benchmark_plugin_id"])
        fn_name = str(spec["benchmark_function_name"])
        plugin = get_plugin(plugin_id)
        if not plugin or plugin.kind != PluginKind.BENCHMARK:
            raise HTTPException(status_code=400, detail="benchmark_plugin_id does not refer to a benchmark plugin")
        discovered = set((plugin.symbols or {}).get("functions", []) or [])
        if fn_name not in discovered:
            raise HTTPException(status_code=400, detail="benchmark_function_name not found in plugin symbols")
    
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
        if benchmark.benchmark_type == BenchmarkType.CAUSAL_LM_QA:
            if experiment.experiment_type != ExperimentType.CAUSAL_LM:
                raise ValueError("causal_lm_qa benchmarks require a completed causal_lm experiment")

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
                run_scores.append(
                    BenchmarkRunScore(
                        run_number=run_num,
                        model_answer=model_answer,
                        bleu_score=bleu,
                        rouge_score=rouge,
                    )
                )

            eval_result.run_scores = run_scores
            eval_result.model_answer = run_scores[-1].model_answer
            eval_result.bleu_score = sum(r.bleu_score for r in run_scores) / len(run_scores)
            eval_result.rouge_score = sum(r.rouge_score for r in run_scores) / len(run_scores)
            eval_result.primary_score = float(eval_result.rouge_score)
            eval_result.metrics = {"bleu": eval_result.bleu_score, "rouge_l": eval_result.rouge_score}
            eval_result.status = BenchmarkStatus.COMPLETED

        elif benchmark.benchmark_type == BenchmarkType.MASKED_LM_FILL_MASK:
            if experiment.experiment_type != ExperimentType.MASKED_LM:
                raise ValueError("masked_lm_fill_mask benchmarks require a completed masked_lm experiment")

            import torch
            from transformers import AutoModelForMaskedLM, AutoTokenizer

            model_path = Path(experiment.output_dir)
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForMaskedLM.from_pretrained(model_path)
            model.eval()

            if tokenizer.mask_token is None or tokenizer.mask_token_id is None:
                raise ValueError("Tokenizer has no mask_token; cannot run masked_lm_fill_mask")

            prompt = benchmark.question.replace("[MASK]", tokenizer.mask_token).replace("<mask>", tokenizer.mask_token)
            encoded = tokenizer(prompt, return_tensors="pt")
            input_ids = encoded["input_ids"]

            mask_positions = (input_ids == tokenizer.mask_token_id).nonzero(as_tuple=False)
            if mask_positions.numel() == 0:
                raise ValueError("No mask token found after normalization")
            if mask_positions.shape[0] != 1:
                raise ValueError("masked_lm_fill_mask supports exactly 1 mask token")

            with torch.no_grad():
                logits = model(**encoded).logits  # [B, T, V]
            b, t = int(mask_positions[0][0]), int(mask_positions[0][1])
            vocab_logits = logits[b, t, :]
            topk = 10
            top_ids = torch.topk(vocab_logits, k=topk).indices.tolist()
            top_tokens = [tokenizer.decode([i]).strip() for i in top_ids]

            gold = benchmark.gold_answer.strip()
            top1 = top_tokens[0] if top_tokens else ""
            top1_correct = 1.0 if top1 == gold else 0.0
            top10_correct = 1.0 if gold in top_tokens else 0.0

            eval_result.model_answer = top1
            eval_result.bleu_score = 0.0
            eval_result.rouge_score = 0.0
            eval_result.primary_score = float(top1_correct)
            eval_result.metrics = {
                "gold": gold,
                "top1": top1,
                "top10": top_tokens,
                "top1_correct": top1_correct,
                "top10_correct": top10_correct,
            }
            eval_result.status = BenchmarkStatus.COMPLETED

        elif benchmark.benchmark_type == BenchmarkType.CUSTOM_LIGHTNING_SIN_REGRESSION:
            if experiment.experiment_type != ExperimentType.CUSTOM_LIGHTNING:
                raise ValueError("custom_lightning_sin_regression benchmarks require a completed custom_lightning experiment")
            if not experiment.output_dir:
                raise ValueError("Experiment has no output_dir")

            out_dir = Path(experiment.output_dir)
            ckpt_path = out_dir / "model.ckpt"
            if not ckpt_path.exists():
                raise ValueError("Custom Lightning experiment is missing model.ckpt (re-run training)")

            if not experiment.lightning_module_plugin_id or not experiment.lightning_module_class_name:
                raise ValueError("Custom Lightning experiment is missing lightning module provenance")

            plugin = get_plugin(experiment.lightning_module_plugin_id)
            if not plugin or plugin.kind != PluginKind.LIGHTNING_MODULE:
                raise ValueError("LightningModule plugin not found")

            spec = benchmark.spec or {}
            payload = {
                "output_dir": str(out_dir),
                "config": (experiment.config.model_dump() if experiment.config else {}),
                "lightning_module_path": plugin.path,
                "lightning_module_class_name": experiment.lightning_module_class_name,
                "checkpoint_path": str(ckpt_path),
                "x_min": float(spec["x_min"]),
                "x_max": float(spec["x_max"]),
                "n_points": int(spec["n_points"]),
            }
            payload_path = out_dir / f"benchmark_payload_{eval_id}.json"
            payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            proc = subprocess.Popen(
                [sys.executable, "-m", "src.custom_lightning_sin_benchmark_runner", str(payload_path)],
                cwd=str(Path(__file__).resolve().parents[2]),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = proc.communicate(timeout=120)
            if stdout:
                (out_dir / f"benchmark_stdout_{eval_id}.txt").write_text(stdout, encoding="utf-8")
            if stderr:
                (out_dir / f"benchmark_stderr_{eval_id}.txt").write_text(stderr, encoding="utf-8")
            if proc.returncode != 0:
                raise ValueError(f"Benchmark runner failed (exit={proc.returncode})")

            metrics_path = out_dir / "benchmark_metrics.json"
            if not metrics_path.exists():
                raise ValueError("Benchmark runner completed but benchmark_metrics.json is missing")

            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            mse = float(metrics["mse"])

            eval_result.model_answer = ""
            eval_result.bleu_score = 0.0
            eval_result.rouge_score = 0.0
            eval_result.primary_score = mse
            eval_result.metrics = metrics
            eval_result.status = BenchmarkStatus.COMPLETED

        elif benchmark.benchmark_type == BenchmarkType.CUSTOM_LIGHTNING_PLUGIN:
            if experiment.experiment_type != ExperimentType.CUSTOM_LIGHTNING:
                raise ValueError("custom_lightning_plugin benchmarks require a completed custom_lightning experiment")
            if not experiment.output_dir:
                raise ValueError("Experiment has no output_dir")
            if not experiment.lightning_module_plugin_id or not experiment.lightning_module_class_name:
                raise ValueError("Custom Lightning experiment is missing lightning module provenance")

            out_dir = Path(experiment.output_dir)
            ckpt_path = out_dir / "model.ckpt"
            if not ckpt_path.exists():
                raise ValueError("Custom Lightning experiment is missing model.ckpt (re-run training)")

            lm_plugin = get_plugin(experiment.lightning_module_plugin_id)
            if not lm_plugin or lm_plugin.kind != PluginKind.LIGHTNING_MODULE:
                raise ValueError("LightningModule plugin not found")

            spec = benchmark.spec or {}
            benchmark_plugin_id = str(spec["benchmark_plugin_id"])
            benchmark_function_name = str(spec["benchmark_function_name"])

            bm_plugin = get_plugin(benchmark_plugin_id)
            if not bm_plugin or bm_plugin.kind != PluginKind.BENCHMARK:
                raise ValueError("Benchmark plugin not found")

            payload = {
                "output_dir": str(out_dir),
                "config": (experiment.config.model_dump() if experiment.config else {}),
                "lightning_module_path": lm_plugin.path,
                "lightning_module_class_name": experiment.lightning_module_class_name,
                "checkpoint_path": str(ckpt_path),
                "benchmark_plugin_path": bm_plugin.path,
                "benchmark_function_name": benchmark_function_name,
                "benchmark_spec": spec,
            }
            payload_path = out_dir / f"benchmark_plugin_payload_{eval_id}.json"
            payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            proc = subprocess.Popen(
                [sys.executable, "-m", "src.custom_lightning_plugin_benchmark_runner", str(payload_path)],
                cwd=str(Path(__file__).resolve().parents[2]),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = proc.communicate(timeout=120)
            if stdout:
                (out_dir / f"benchmark_plugin_stdout_{eval_id}.txt").write_text(stdout, encoding="utf-8")
            if stderr:
                (out_dir / f"benchmark_plugin_stderr_{eval_id}.txt").write_text(stderr, encoding="utf-8")
            if proc.returncode != 0:
                raise ValueError(f"Benchmark runner failed (exit={proc.returncode})")

            metrics_path = out_dir / "benchmark_plugin_metrics.json"
            if not metrics_path.exists():
                raise ValueError("Benchmark runner completed but benchmark_plugin_metrics.json is missing")

            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            if not isinstance(metrics, dict):
                raise ValueError("benchmark_plugin_metrics.json must be a JSON object")
            if "primary_score" not in metrics:
                raise ValueError("benchmark_plugin_metrics.json must contain primary_score")
            if "metrics" not in metrics:
                raise ValueError("benchmark_plugin_metrics.json must contain metrics")
            if not isinstance(metrics.get("metrics"), dict):
                raise ValueError("benchmark_plugin_metrics.json.metrics must be a JSON object")
            extra_keys = set(metrics.keys()) - {"primary_score", "metrics"}
            if extra_keys:
                raise ValueError(
                    "benchmark_plugin_metrics.json must only contain keys: primary_score, metrics"
                )

            eval_result.model_answer = ""
            eval_result.bleu_score = 0.0
            eval_result.rouge_score = 0.0
            eval_result.primary_score = float(metrics["primary_score"])
            eval_result.metrics = metrics["metrics"]
            eval_result.status = BenchmarkStatus.COMPLETED

        else:
            raise ValueError(f"Unsupported benchmark_type: {benchmark.benchmark_type}")
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
        benchmark_type=benchmark.benchmark_type,
        experiment_id=request.experiment_id,
        question=benchmark.question,
        gold_answer=benchmark.gold_answer,
        model_answer="",
        bleu_score=0.0,
        rouge_score=0.0,
        primary_score=0.0,
        metrics={},
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


@router.get("/evaluations/by-benchmark/{benchmark_id}", response_model=BenchmarkEvalListResponse)
def list_evaluations_by_benchmark(benchmark_id: str) -> BenchmarkEvalListResponse:
    """Legacy alias used by the Flask UI."""
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
        model_name = "unknown"
        learning_rate = None
        num_epochs = None
        batch_size = None
        lora_r = None
        lora_alpha = None

        if exp.experiment_type == ExperimentType.CAUSAL_LM and cfg is not None:
            model_name = cfg.model.pretrained_model_name
            learning_rate = cfg.training.learning_rate
            num_epochs = cfg.training.num_train_epochs
            batch_size = cfg.training.per_device_train_batch_size
            if hasattr(cfg, "peft") and cfg.peft and cfg.peft.enabled:
                lora_r = cfg.peft.r
                lora_alpha = cfg.peft.lora_alpha
        elif exp.experiment_type == ExperimentType.MASKED_LM and cfg is not None:
            model_name = cfg.model.pretrained_model_name
            learning_rate = cfg.training.learning_rate
            num_epochs = cfg.training.num_train_epochs
            batch_size = cfg.training.per_device_train_batch_size
        elif exp.experiment_type == ExperimentType.CUSTOM_LIGHTNING:
            model_name = exp.lightning_module_class_name or "custom_lightning"
            if cfg is not None and isinstance(getattr(cfg, "cfg", None), dict):
                user_cfg = cfg.cfg
                if "lr" in user_cfg:
                    learning_rate = float(user_cfg["lr"])
                if "batch_size" in user_cfg:
                    batch_size = int(user_cfg["batch_size"])
        items.append(
            EvaluationComparisonItem(
                eval_id=ev.id,
                experiment_id=ev.experiment_id,
                benchmark_name=ev.benchmark_name,
                benchmark_type=ev.benchmark_type,
                question=ev.question,
                model_name=model_name,
                dataset_filename=exp.dataset_filename or "unknown",
                bleu_score=ev.bleu_score,
                rouge_score=ev.rouge_score,
                primary_score=float(ev.primary_score or 0.0),
                learning_rate=learning_rate,
                num_epochs=num_epochs,
                batch_size=batch_size,
                lora_r=lora_r,
                lora_alpha=lora_alpha,
                started_at=ev.started_at,
                completed_at=ev.completed_at,
            )
        )
    def _sort_key(item: EvaluationComparisonItem):
        if item.benchmark_type == BenchmarkType.CUSTOM_LIGHTNING_SIN_REGRESSION:
            return (0, float(item.primary_score or 0.0))
        return (1, -float(item.rouge_score or 0.0))

    items.sort(key=_sort_key)
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
    _run_benchmark_eval(eval_id=eval_id, benchmark=benchmark, experiment=experiment, num_runs=1)

