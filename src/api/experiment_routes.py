"""Experiment API routes."""
from __future__ import annotations

import json
import subprocess
import sys
import time
import shutil
import uuid
from pathlib import Path
from threading import Thread

from fastapi import APIRouter, HTTPException

from ..callbacks import stop_registry, progress_registry
from ..config import DataConfig, ExperimentConfig, ModelConfig, TrainingConfig
from ..llm_config import (
    LLMDataConfig,
    LLMExperimentConfig,
    LLMModelConfig,
    LLMPeftConfig,
    LLMTrainingConfig,
)
from ..llm_training import run_llm_training
from ..models import (
    BenchmarkEvalResult,
    BenchmarkStatus,
    BenchmarkType,
    CausalLMFullConfig,
    CausalLMRequest,
    ConfigRecord,
    CustomLightningRequest,
    ExperimentComparisonItem,
    ExperimentComparisonResponse,
    ExperimentListResponse,
    ExperimentResult,
    ExperimentStartResponse,
    ExperimentStatus,
    ExperimentType,
    MaskedLMFullConfig,
    MaskedLMRequest,
    PluginKind,
)
from ..remote_runner import run_experiment_remote
from ..storage import (
    get_compute_target,
    get_config,
    get_dataset,
    get_experiment,
    list_experiments,
    delete_experiment as storage_delete_experiment,
    list_benchmark_evals,
    list_benchmarks,
    save_benchmark_eval,
    save_config,
    save_experiment,
    config_name_exists,
    get_plugin,
)
from ..training import run_training
from .helpers import ARTIFACTS_DIR, generate_friendly_name, now
from .benchmark_routes import _run_benchmark_eval_sync

router = APIRouter(tags=["experiments"])


def _run_all_benchmarks_for_experiment(experiment_id: str) -> None:
    """Run all available benchmarks for a completed experiment, serially."""
    from ..models import Benchmark
    from ..storage import get_benchmark
    
    benchmarks = list_benchmarks()
    if not benchmarks:
        return
    
    experiment = get_experiment(experiment_id)
    if not experiment:
        return

    if experiment.experiment_type == ExperimentType.CAUSAL_LM:
        benchmarks = [b for b in benchmarks if b.benchmark_type == BenchmarkType.CAUSAL_LM_QA]
    elif experiment.experiment_type == ExperimentType.MASKED_LM:
        benchmarks = [b for b in benchmarks if b.benchmark_type == BenchmarkType.MASKED_LM_FILL_MASK]
    elif experiment.experiment_type == ExperimentType.CUSTOM_LIGHTNING:
        benchmarks = [
            b
            for b in benchmarks
            if b.benchmark_type
            in {BenchmarkType.CUSTOM_LIGHTNING_SIN_REGRESSION, BenchmarkType.CUSTOM_LIGHTNING_PLUGIN}
        ]
    else:
        benchmarks = []
    if not benchmarks:
        return
    
    experiment.status = ExperimentStatus.EVALUATING
    experiment.auto_eval_total = len(benchmarks)
    experiment.auto_eval_completed = 0
    experiment.auto_eval_current = benchmarks[0].name if benchmarks else None
    save_experiment(experiment)
    
    for i, benchmark in enumerate(benchmarks):
        experiment.auto_eval_current = benchmark.name
        save_experiment(experiment)
        
        eval_id = str(uuid.uuid4())
        eval_result = BenchmarkEvalResult(
            id=eval_id,
            benchmark_id=benchmark.id,
            benchmark_name=benchmark.name,
            benchmark_type=benchmark.benchmark_type,
            experiment_id=experiment_id,
            question=benchmark.question,
            gold_answer=benchmark.gold_answer,
            model_answer="",
            bleu_score=0.0,
            rouge_score=0.0,
            primary_score=0.0,
            metrics={},
            status=BenchmarkStatus.PENDING,
            started_at=now(),
        )
        save_benchmark_eval(eval_result)
        
        _run_benchmark_eval_sync(eval_id, benchmark, experiment)
        
        experiment.auto_eval_completed = i + 1
        save_experiment(experiment)
    
    experiment.status = ExperimentStatus.COMPLETED
    experiment.auto_eval_current = None
    save_experiment(experiment)


def _run_masked_lm_experiment(experiment_id: str, request: MaskedLMRequest, config_id: str) -> None:
    exp = get_experiment(experiment_id)
    output_dir = ARTIFACTS_DIR / f"masked_lm_{experiment_id}"
    exp.status = ExperimentStatus.RUNNING
    exp.output_dir = str(output_dir)
    save_experiment(exp)

    dataset_info = get_dataset(request.dataset_id)
    config_record = get_config(config_id)
    cfg = config_record.config
    auto_evaluate = getattr(cfg.training, "auto_evaluate", False)

    config = ExperimentConfig(
        data=DataConfig(
            csv_path=Path(dataset_info.path),
            text_fields=cfg.data.text_fields,
            separator=cfg.data.separator,
            validation_split=cfg.data.validation_split,
            seed=cfg.data.seed,
            max_length=cfg.data.max_length,
        ),
        model=ModelConfig(
            pretrained_model_name=cfg.model.pretrained_model_name,
            freeze_embedding=cfg.model.freeze_embedding,
            freeze_encoder_layers=cfg.model.freeze_encoder_layers,
        ),
        training=TrainingConfig(
            output_dir=output_dir,
            num_train_epochs=cfg.training.num_train_epochs,
            per_device_train_batch_size=cfg.training.per_device_train_batch_size,
            per_device_eval_batch_size=cfg.training.per_device_eval_batch_size,
            learning_rate=cfg.training.learning_rate,
            weight_decay=cfg.training.weight_decay,
            warmup_ratio=cfg.training.warmup_ratio,
            logging_steps=cfg.training.logging_steps,
            eval_steps=cfg.training.eval_steps,
            save_steps=cfg.training.save_steps,
            save_total_limit=cfg.training.save_total_limit,
            gradient_accumulation_steps=cfg.training.gradient_accumulation_steps,
            max_steps=cfg.training.max_steps,
            early_stopping_patience=cfg.training.early_stopping_patience,
            early_stopping_metric=cfg.training.early_stopping_metric,
            early_stopping_greater_is_better=cfg.training.early_stopping_greater_is_better,
            auto_evaluate=auto_evaluate,
        ),
    )

    try:
        _, metrics = run_training(config, experiment_id=experiment_id)
        if stop_registry.get(experiment_id):
            exp.status = ExperimentStatus.STOPPED
        else:
            exp.status = ExperimentStatus.COMPLETED
        exp.metrics = metrics
    except Exception as e:
        exp.status = ExperimentStatus.FAILED
        exp.error = str(e)
    finally:
        exp.completed_at = now()
        stop_registry.pop(experiment_id, None)
        save_experiment(exp)
    
    if auto_evaluate and exp.status == ExperimentStatus.COMPLETED:
        _run_all_benchmarks_for_experiment(experiment_id)


def _run_causal_lm_experiment(experiment_id: str, request: CausalLMRequest, config_id: str) -> None:
    exp = get_experiment(experiment_id)
    output_dir = ARTIFACTS_DIR / f"causal_lm_{experiment_id}"
    exp.status = ExperimentStatus.RUNNING
    exp.output_dir = str(output_dir)
    save_experiment(exp)

    dataset_info = get_dataset(request.dataset_id)
    config_record = get_config(config_id)
    cfg = config_record.config
    auto_evaluate = getattr(cfg.training, "auto_evaluate", False)

    peft_config = None
    if cfg.peft.enabled:
        peft_config = LLMPeftConfig(
            enabled=True,
            r=cfg.peft.r,
            lora_alpha=cfg.peft.lora_alpha,
            lora_dropout=cfg.peft.lora_dropout,
            bias=cfg.peft.bias,
            target_modules=cfg.peft.target_modules,
        )

    config = LLMExperimentConfig(
        data=LLMDataConfig(
            csv_path=Path(dataset_info.path),
            question_field=cfg.data.question_field,
            answer_field=cfg.data.answer_field,
            system_prompt=cfg.data.system_prompt,
            template=cfg.data.template,
            validation_split=cfg.data.validation_split,
            seed=cfg.data.seed,
            max_length=cfg.data.max_length,
        ),
        model=LLMModelConfig(
            pretrained_model_name=cfg.model.pretrained_model_name,
            trust_remote_code=cfg.model.trust_remote_code,
            pad_token_override=cfg.model.pad_token_override,
        ),
        training=LLMTrainingConfig(
            output_dir=output_dir,
            num_train_epochs=cfg.training.num_train_epochs,
            per_device_train_batch_size=cfg.training.per_device_train_batch_size,
            per_device_eval_batch_size=cfg.training.per_device_eval_batch_size,
            learning_rate=cfg.training.learning_rate,
            weight_decay=cfg.training.weight_decay,
            warmup_ratio=cfg.training.warmup_ratio,
            logging_steps=cfg.training.logging_steps,
            eval_steps=cfg.training.eval_steps,
            save_steps=cfg.training.save_steps,
            save_total_limit=cfg.training.save_total_limit,
            gradient_accumulation_steps=cfg.training.gradient_accumulation_steps,
            max_steps=cfg.training.max_steps,
            lr_scheduler_type=cfg.training.lr_scheduler_type,
            gradient_checkpointing=cfg.training.gradient_checkpointing,
            bf16=cfg.training.bf16,
            fp16=cfg.training.fp16,
            early_stopping_patience=cfg.training.early_stopping_patience,
            early_stopping_metric=cfg.training.early_stopping_metric,
            early_stopping_greater_is_better=cfg.training.early_stopping_greater_is_better,
            auto_evaluate=auto_evaluate,
        ),
        peft=peft_config,
    )

    try:
        _, metrics = run_llm_training(config, experiment_id=experiment_id)
        if stop_registry.get(experiment_id):
            exp.status = ExperimentStatus.STOPPED
        else:
            exp.status = ExperimentStatus.COMPLETED
        exp.metrics = metrics
    except Exception as e:
        exp.status = ExperimentStatus.FAILED
        exp.error = str(e)
    finally:
        exp.completed_at = now()
        stop_registry.pop(experiment_id, None)
        save_experiment(exp)
    
    if auto_evaluate and exp.status == ExperimentStatus.COMPLETED:
        _run_all_benchmarks_for_experiment(experiment_id)


def _repo_root() -> Path:
    # src/api/experiment_routes.py -> repo root is two levels up
    return Path(__file__).resolve().parents[2]


def _run_custom_lightning_experiment(
    experiment_id: str,
    request: CustomLightningRequest,
    config_id: str,
) -> None:
    exp = get_experiment(experiment_id)
    output_dir = ARTIFACTS_DIR / f"custom_lightning_{experiment_id}"
    exp.status = ExperimentStatus.RUNNING
    exp.output_dir = str(output_dir)
    save_experiment(exp)

    dataset_info = get_dataset(request.dataset_id)
    if not dataset_info:
        exp.status = ExperimentStatus.FAILED
        exp.error = "Dataset not found"
        exp.completed_at = now()
        save_experiment(exp)
        return

    lightning_plugin = get_plugin(request.lightning_module_plugin_id)
    if not lightning_plugin:
        exp.status = ExperimentStatus.FAILED
        exp.error = "LightningModule plugin not found"
        exp.completed_at = now()
        save_experiment(exp)
        return
    if lightning_plugin.kind != PluginKind.LIGHTNING_MODULE:
        exp.status = ExperimentStatus.FAILED
        exp.error = "Selected Lightning plugin has wrong kind"
        exp.completed_at = now()
        save_experiment(exp)
        return

    dl_plugin = get_plugin(request.dataloaders_plugin_id)
    if not dl_plugin:
        exp.status = ExperimentStatus.FAILED
        exp.error = "Dataloaders plugin not found"
        exp.completed_at = now()
        save_experiment(exp)
        return
    if dl_plugin.kind != PluginKind.DATALOADERS:
        exp.status = ExperimentStatus.FAILED
        exp.error = "Selected dataloaders plugin has wrong kind"
        exp.completed_at = now()
        save_experiment(exp)
        return
    if request.dataloaders_function_name != "build_dataloaders":
        exp.status = ExperimentStatus.FAILED
        exp.error = "dataloaders_function_name must be build_dataloaders"
        exp.completed_at = now()
        save_experiment(exp)
        return

    discovered_classes = set(lightning_plugin.symbols.get("lightning_modules", []))
    if request.lightning_module_class_name not in discovered_classes:
        exp.status = ExperimentStatus.FAILED
        exp.error = "Selected LightningModule class not present in plugin symbols"
        exp.completed_at = now()
        save_experiment(exp)
        return

    discovered_fns = set(dl_plugin.symbols.get("functions", []))
    if request.dataloaders_function_name not in discovered_fns:
        exp.status = ExperimentStatus.FAILED
        exp.error = "Selected dataloaders function not present in plugin symbols"
        exp.completed_at = now()
        save_experiment(exp)
        return

    # Keep payload JSON-serializable (no datetimes).
    dataset_payload = {
        "id": dataset_info.id,
        "filename": dataset_info.filename,
        "path": dataset_info.path,
        "columns": list(dataset_info.columns),
        "row_count": int(dataset_info.row_count),
    }
    cfg_payload = {
        "training": request.config.training.model_dump(),
        "cfg": request.config.cfg,
    }

    payload = {
        "experiment_id": experiment_id,
        "output_dir": str(output_dir),
        "config": cfg_payload,
        "dataset": dataset_payload,
        "lightning_module_path": lightning_plugin.path,
        "lightning_module_class_name": request.lightning_module_class_name,
        "dataloaders_path": dl_plugin.path,
        "dataloaders_function_name": request.dataloaders_function_name,
    }

    # Check for remote execution
    if request.compute_target_id:
        compute_target = get_compute_target(request.compute_target_id)
        if not compute_target:
            exp.status = ExperimentStatus.FAILED
            exp.error = "Compute target not found"
            exp.completed_at = now()
            save_experiment(exp)
            return

        try:
            plugin_paths = [lightning_plugin.path, dl_plugin.path]
            success, metrics, error = run_experiment_remote(
                target=compute_target,
                experiment_id=experiment_id,
                payload=payload,
                dataset_path=dataset_info.path,
                plugin_paths=plugin_paths,
            )

            if success:
                exp.status = ExperimentStatus.COMPLETED
                exp.metrics = metrics
            else:
                exp.status = ExperimentStatus.FAILED
                exp.error = error or "Remote execution failed"
        except Exception as e:
            exp.status = ExperimentStatus.FAILED
            exp.error = str(e)
        finally:
            exp.completed_at = now()
            save_experiment(exp)
        return

    # Local execution
    output_dir.mkdir(parents=True, exist_ok=True)
    payload_path = output_dir / "runner_payload.json"
    payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    proc = subprocess.Popen(
        [sys.executable, "-m", "src.custom_lightning_runner", str(payload_path)],
        cwd=str(_repo_root()),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    stopped = False
    try:
        while proc.poll() is None:
            if stop_registry.get(experiment_id):
                stopped = True
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()
                break
            time.sleep(0.5)

        stdout, stderr = proc.communicate(timeout=1)
        if stdout:
            (output_dir / "runner_stdout.txt").write_text(stdout, encoding="utf-8")
        if stderr:
            (output_dir / "runner_stderr.txt").write_text(stderr, encoding="utf-8")

        if stopped:
            exp.status = ExperimentStatus.STOPPED
            exp.metrics = {}
            return

        if proc.returncode != 0:
            exp.status = ExperimentStatus.FAILED
            err_path = output_dir / "runner_error.txt"
            exp.error = err_path.read_text(encoding="utf-8") if err_path.exists() else "Runner failed"
            return

        metrics_path = output_dir / "metrics.json"
        if not metrics_path.exists():
            exp.status = ExperimentStatus.FAILED
            exp.error = "Runner completed but metrics.json is missing"
            return

        exp.status = ExperimentStatus.COMPLETED
        exp.metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except Exception as e:
        exp.status = ExperimentStatus.FAILED
        exp.error = str(e)
    finally:
        exp.completed_at = now()
        stop_registry.pop(experiment_id, None)
        save_experiment(exp)


def _resolve_or_create_config(
    config_id: str | None,
    config: MaskedLMFullConfig | CausalLMFullConfig | None,
    config_name: str | None,
    exp_type: ExperimentType,
) -> str:
    """Resolve existing config_id or create a new config record."""
    if config_id:
        existing = get_config(config_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Config not found")
        return config_id
    
    if not config:
        raise HTTPException(status_code=400, detail="Either config_id or config must be provided")
    
    name = config_name or generate_friendly_name()
    if config_name_exists(name):
        name = f"{name}-{uuid.uuid4().hex[:4]}"
    
    record = ConfigRecord(
        id=str(uuid.uuid4()),
        name=name,
        experiment_type=exp_type,
        config=config,
        created_at=now(),
    )
    save_config(record)
    return record.id


@router.post("/experiments/masked-lm", response_model=ExperimentStartResponse)
def start_masked_lm_experiment(request: MaskedLMRequest) -> ExperimentStartResponse:
    dataset_info = get_dataset(request.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")

    config_id = _resolve_or_create_config(
        request.config_id,
        request.config,
        request.config_name,
        ExperimentType.MASKED_LM,
    )

    experiment_id = str(uuid.uuid4())
    exp = ExperimentResult(
        id=experiment_id,
        experiment_type=ExperimentType.MASKED_LM,
        status=ExperimentStatus.PENDING,
        dataset_id=request.dataset_id,
        dataset_filename=dataset_info.filename,
        config_id=config_id,
        started_at=now(),
    )
    save_experiment(exp)

    thread = Thread(target=_run_masked_lm_experiment, args=(experiment_id, request, config_id))
    thread.start()

    return ExperimentStartResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.PENDING,
        message="Masked LM experiment started",
    )


@router.post("/experiments/causal-lm", response_model=ExperimentStartResponse)
def start_causal_lm_experiment(request: CausalLMRequest) -> ExperimentStartResponse:
    dataset_info = get_dataset(request.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")

    config_id = _resolve_or_create_config(
        request.config_id,
        request.config,
        request.config_name,
        ExperimentType.CAUSAL_LM,
    )

    experiment_id = str(uuid.uuid4())
    exp = ExperimentResult(
        id=experiment_id,
        experiment_type=ExperimentType.CAUSAL_LM,
        status=ExperimentStatus.PENDING,
        dataset_id=request.dataset_id,
        dataset_filename=dataset_info.filename,
        config_id=config_id,
        started_at=now(),
    )
    save_experiment(exp)

    thread = Thread(target=_run_causal_lm_experiment, args=(experiment_id, request, config_id))
    thread.start()

    return ExperimentStartResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.PENDING,
        message="Causal LM experiment started",
    )


@router.post("/experiments/custom-lightning", response_model=ExperimentStartResponse)
def start_custom_lightning_experiment(request: CustomLightningRequest) -> ExperimentStartResponse:
    dataset_info = get_dataset(request.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")

    name = generate_friendly_name()
    if config_name_exists(name):
        name = f"{name}-{uuid.uuid4().hex[:4]}"

    record = ConfigRecord(
        id=str(uuid.uuid4()),
        name=name,
        experiment_type=ExperimentType.CUSTOM_LIGHTNING,
        config=request.config,
        created_at=now(),
    )
    save_config(record)

    experiment_id = str(uuid.uuid4())
    exp = ExperimentResult(
        id=experiment_id,
        experiment_type=ExperimentType.CUSTOM_LIGHTNING,
        status=ExperimentStatus.PENDING,
        dataset_id=request.dataset_id,
        dataset_filename=dataset_info.filename,
        config_id=record.id,
        started_at=now(),
        lightning_module_plugin_id=request.lightning_module_plugin_id,
        lightning_module_class_name=request.lightning_module_class_name,
        dataloaders_plugin_id=request.dataloaders_plugin_id,
        dataloaders_function_name=request.dataloaders_function_name,
    )
    save_experiment(exp)

    thread = Thread(
        target=_run_custom_lightning_experiment,
        args=(experiment_id, request, record.id),
    )
    thread.start()

    return ExperimentStartResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.PENDING,
        message="Custom Lightning experiment started",
    )


@router.get("/experiments", response_model=ExperimentListResponse)
def list_all_experiments() -> ExperimentListResponse:
    return ExperimentListResponse(experiments=list_experiments())


@router.get("/experiments/{experiment_id}", response_model=ExperimentResult)
def get_experiment_by_id(experiment_id: str) -> ExperimentResult:
    exp = get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@router.get("/experiments/{experiment_id}/progress")
def get_experiment_progress(experiment_id: str) -> dict:
    """Get live training progress for an experiment (updated every step)."""
    exp = get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if exp.experiment_type == ExperimentType.CUSTOM_LIGHTNING and exp.output_dir:
        p = Path(exp.output_dir) / "progress.json"
        if p.exists():
            payload = json.loads(p.read_text(encoding="utf-8"))
            return {
                "global_step": int(payload.get("global_step", 0) or 0),
                "epoch": int(payload.get("epoch", 0) or 0),
                "max_steps": 0,
            }
        return {"global_step": 0, "epoch": 0, "max_steps": 0}

    progress = progress_registry.get(experiment_id, {})
    return {
        "global_step": progress.get("global_step", 0),
        "epoch": progress.get("epoch", 0),
        "max_steps": progress.get("max_steps", 0),
    }


@router.get("/experiments/{experiment_id}/logs")
def get_experiment_logs(experiment_id: str) -> dict:
    exp = get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if not exp.output_dir:
        return {"logs": []}

    output_path = Path(exp.output_dir)

    logs_path = output_path / "training_logs.json"
    if logs_path.exists():
        import json
        with logs_path.open() as f:
            return {"logs": json.load(f)}

    for checkpoint_dir in sorted(output_path.glob("checkpoint-*"), reverse=True):
        state_path = checkpoint_dir / "trainer_state.json"
        if state_path.exists():
            import json
            with state_path.open() as f:
                state = json.load(f)
                return {"logs": state.get("log_history", [])}

    return {"logs": []}


@router.delete("/experiments/{experiment_id}")
def delete_experiment(experiment_id: str) -> dict[str, str]:
    exp = storage_delete_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if exp.output_dir:
        output_path = Path(exp.output_dir)
        if output_path.exists():
            shutil.rmtree(output_path)
    return {"status": "deleted", "experiment_id": experiment_id}


@router.post("/experiments/{experiment_id}/stop")
def stop_experiment(experiment_id: str) -> dict[str, str]:
    exp = get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if exp.status != ExperimentStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Experiment is not running")
    stop_registry[experiment_id] = True
    return {"status": "stop_requested", "experiment_id": experiment_id}


def _flatten_config(config: dict, prefix: str = "") -> dict[str, any]:
    """Flatten a nested config dict to dot-separated keys."""
    flat = {}
    for key, val in config.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(val, dict):
            flat.update(_flatten_config(val, full_key))
        else:
            flat[full_key] = val
    return flat


def _compute_config_diff(experiments: list[ExperimentComparisonItem]) -> dict[str, dict[str, list]]:
    """Compute config differences across experiments."""
    if len(experiments) < 2:
        return {}

    all_flat = [_flatten_config(exp.config) for exp in experiments]
    all_keys = set()
    for flat in all_flat:
        all_keys.update(flat.keys())

    diff = {}
    for key in sorted(all_keys):
        values = [flat.get(key) for flat in all_flat]
        unique_vals = set(str(v) for v in values)
        if len(unique_vals) > 1:
            diff[key] = {exp.experiment_id: flat.get(key) for exp, flat in zip(experiments, all_flat)}

    return diff


@router.post("/experiments/compare", response_model=ExperimentComparisonResponse)
def compare_experiments(experiment_ids: list[str]) -> ExperimentComparisonResponse:
    """Compare configs of multiple experiments."""
    experiments = []
    for exp_id in experiment_ids:
        exp = get_experiment(exp_id)
        if not exp:
            raise HTTPException(status_code=404, detail=f"Experiment {exp_id} not found")

        evals = list_benchmark_evals()
        completed_evals = [e for e in evals if e.experiment_id == exp_id and e.status == BenchmarkStatus.COMPLETED]
        bleu_scores = [e.bleu_score for e in completed_evals]
        rouge_scores = [e.rouge_score for e in completed_evals]

        experiments.append(
            ExperimentComparisonItem(
                experiment_id=exp.id,
                experiment_type=exp.experiment_type,
                dataset_filename=exp.dataset_filename,
                started_at=exp.started_at,
                status=exp.status,
                config=exp.config.model_dump(),
                bleu_scores=bleu_scores,
                rouge_scores=rouge_scores,
                eval_loss=exp.metrics.get("eval_loss"),
            )
        )

    config_diff = _compute_config_diff(experiments)

    return ExperimentComparisonResponse(experiments=experiments, config_diff=config_diff)


# Export for use in autotune_routes
def run_causal_lm_experiment_sync(experiment_id: str, dataset_id: str, config_id: str) -> None:
    """Run causal LM experiment synchronously."""
    exp = get_experiment(experiment_id)
    output_dir = ARTIFACTS_DIR / f"causal_lm_{experiment_id}"
    exp.status = ExperimentStatus.RUNNING
    exp.output_dir = str(output_dir)
    save_experiment(exp)

    dataset_info = get_dataset(dataset_id)
    config_record = get_config(config_id)
    cfg = config_record.config

    peft_config = None
    if cfg.peft.enabled:
        peft_config = LLMPeftConfig(
            enabled=True,
            r=cfg.peft.r,
            lora_alpha=cfg.peft.lora_alpha,
            lora_dropout=cfg.peft.lora_dropout,
            bias=cfg.peft.bias,
            target_modules=cfg.peft.target_modules,
        )

    config = LLMExperimentConfig(
        data=LLMDataConfig(
            csv_path=Path(dataset_info.path),
            question_field=cfg.data.question_field,
            answer_field=cfg.data.answer_field,
            system_prompt=cfg.data.system_prompt,
            template=cfg.data.template,
            validation_split=cfg.data.validation_split,
            seed=cfg.data.seed,
            max_length=cfg.data.max_length,
        ),
        model=LLMModelConfig(
            pretrained_model_name=cfg.model.pretrained_model_name,
            trust_remote_code=cfg.model.trust_remote_code,
            pad_token_override=cfg.model.pad_token_override,
        ),
        training=LLMTrainingConfig(
            output_dir=output_dir,
            num_train_epochs=cfg.training.num_train_epochs,
            per_device_train_batch_size=cfg.training.per_device_train_batch_size,
            per_device_eval_batch_size=cfg.training.per_device_eval_batch_size,
            learning_rate=cfg.training.learning_rate,
            weight_decay=cfg.training.weight_decay,
            warmup_ratio=cfg.training.warmup_ratio,
            logging_steps=cfg.training.logging_steps,
            eval_steps=cfg.training.eval_steps,
            save_steps=cfg.training.save_steps,
            save_total_limit=cfg.training.save_total_limit,
            gradient_accumulation_steps=cfg.training.gradient_accumulation_steps,
            max_steps=cfg.training.max_steps,
            lr_scheduler_type=cfg.training.lr_scheduler_type,
            gradient_checkpointing=cfg.training.gradient_checkpointing,
            bf16=cfg.training.bf16,
            fp16=cfg.training.fp16,
            early_stopping_patience=cfg.training.early_stopping_patience,
            early_stopping_metric=cfg.training.early_stopping_metric,
            early_stopping_greater_is_better=cfg.training.early_stopping_greater_is_better,
        ),
        peft=peft_config,
    )

    try:
        _, metrics = run_llm_training(config, experiment_id=experiment_id)
        if stop_registry.get(experiment_id):
            exp.status = ExperimentStatus.STOPPED
        else:
            exp.status = ExperimentStatus.COMPLETED
        exp.metrics = metrics
    except Exception as e:
        exp.status = ExperimentStatus.FAILED
        exp.error = str(e)
    finally:
        exp.completed_at = now()
        stop_registry.pop(experiment_id, None)
        save_experiment(exp)

