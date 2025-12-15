"""FastAPI application with core logic for experiments."""
from __future__ import annotations

import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread

import pandas as pd
import yaml
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from .config import DataConfig, ExperimentConfig, ModelConfig, TrainingConfig
from .llm_config import (
    LLMDataConfig,
    LLMExperimentConfig,
    LLMModelConfig,
    LLMPeftConfig,
    LLMTrainingConfig,
)
from .llm_training import run_llm_training
from .callbacks import stop_registry
from .benchmark import compute_bleu_score, compute_rouge_l_score, generate_response, load_model_and_tokenizer
from .models import (
    AutoTuneCandidate,
    AutoTuneJob,
    AutoTuneListResponse,
    AutoTuneRequest,
    AutoTuneStartResponse,
    AutoTuneStatus,
    AutoTuneStatusResponse,
    Benchmark,
    BenchmarkCreateRequest,
    BenchmarkEvalListResponse,
    BenchmarkEvalRequest,
    BenchmarkEvalResult,
    BenchmarkEvalStartResponse,
    BenchmarkListResponse,
    BenchmarkStatus,
    CausalLMDataConfig,
    CausalLMFullConfig,
    CausalLMModelConfig,
    CausalLMPeftConfig,
    CausalLMRequest,
    CausalLMTrainingConfig,
    ConfigCreateRequest,
    ConfigFileInfo,
    ConfigFileListResponse,
    ConfigListResponse,
    ConfigRecord,
    ConfigWithMetrics,
    DatasetInfo,
    DatasetListResponse,
    EvaluationComparisonItem,
    EvaluationComparisonResponse,
    ExperimentComparisonItem,
    ExperimentComparisonResponse,
    ExperimentListResponse,
    ExperimentResult,
    ExperimentStartResponse,
    ExperimentStatus,
    ExperimentType,
    MaskedLMDataConfig,
    MaskedLMFullConfig,
    MaskedLMModelConfig,
    MaskedLMRequest,
    MaskedLMTrainingConfig,
)
from .training import run_training
from .meta_features import MetaFeatureVector, extract_static_config_features, extract_static_dataset_features
from .synthetic_meta import generate_synthetic_features
from .probe import run_probe
from .predictor import PerformancePredictor
from .explainer import PredictionExplainer
from .optimizer import SearchSpace, optimize_config, quick_sensitivity_analysis
from . import storage

UPLOAD_DIR = Path("data/uploads")
ARTIFACTS_DIR = Path("artifacts")
CONFIGS_DIR = Path("configs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def _seed_default_configs() -> None:
    """Seed default configs from YAML files if they don't exist in DB."""
    if not CONFIGS_DIR.exists():
        return
    
    for path in CONFIGS_DIR.glob("*.yaml"):
        config_name = path.stem
        
        # Skip if already exists
        if storage.config_name_exists(config_name):
            continue
        
        try:
            with path.open("r") as f:
                payload = yaml.safe_load(f) or {}
            
            exp_type = _detect_config_type(payload)
            
            if exp_type == ExperimentType.CAUSAL_LM:
                config = CausalLMFullConfig(
                    data=CausalLMDataConfig(**payload.get("data", {})),
                    model=CausalLMModelConfig(**payload.get("model", {})),
                    training=CausalLMTrainingConfig(**payload.get("training", {})),
                    peft=CausalLMPeftConfig(**payload.get("peft", {})) if payload.get("peft") else CausalLMPeftConfig(),
                )
            else:
                config = MaskedLMFullConfig(
                    data=MaskedLMDataConfig(**payload.get("data", {})),
                    model=MaskedLMModelConfig(**payload.get("model", {})),
                    training=MaskedLMTrainingConfig(**payload.get("training", {})),
                )
            
            record = ConfigRecord(
                id=str(uuid.uuid4()),
                name=config_name,
                experiment_type=exp_type,
                config=config,
                created_at=_now(),
            )
            storage.save_config(record)
        except Exception:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.init_db()
    _seed_default_configs()
    yield


app = FastAPI(
    title="AIP-C01 Prep API",
    description="API for dataset management and ML experiment runs",
    version="0.1.0",
    lifespan=lifespan,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


# --- Config Endpoints ---


def _detect_config_type(payload: dict) -> ExperimentType:
    data_section = payload.get("data", {})
    if "system_prompt" in data_section or "template" in data_section:
        return ExperimentType.CAUSAL_LM
    return ExperimentType.MASKED_LM


def _generate_friendly_name() -> str:
    """Generate a friendly config name."""
    import random
    adjectives = ["swift", "bright", "calm", "bold", "keen", "warm", "cool", "quick"]
    nouns = ["falcon", "tiger", "river", "peak", "storm", "wave", "flame", "frost"]
    return f"{random.choice(adjectives)}-{random.choice(nouns)}-{uuid.uuid4().hex[:4]}"


@app.get("/configs", response_model=ConfigListResponse)
def list_configs() -> ConfigListResponse:
    """List all configs from database with associated metrics."""
    return ConfigListResponse(configs=storage.list_configs_with_metrics())


@app.get("/configs/by-type/{experiment_type}", response_model=ConfigListResponse)
def list_configs_by_type(experiment_type: str) -> ConfigListResponse:
    """List configs filtered by experiment type."""
    target_type = ExperimentType(experiment_type)
    all_configs = storage.list_configs_with_metrics()
    filtered = [c for c in all_configs if c.experiment_type == target_type]
    return ConfigListResponse(configs=filtered)


@app.get("/configs/{config_id}", response_model=ConfigRecord)
def get_config(config_id: str) -> ConfigRecord:
    """Get a single config by ID."""
    config = storage.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@app.post("/configs", response_model=ConfigRecord)
def create_config(request: ConfigCreateRequest) -> ConfigRecord:
    """Create a new config in the database."""
    # Determine experiment type from config
    if isinstance(request.config, CausalLMFullConfig):
        exp_type = ExperimentType.CAUSAL_LM
    else:
        exp_type = ExperimentType.MASKED_LM
    
    # Generate name if not provided
    name = request.name or _generate_friendly_name()
    
    # Ensure name is unique
    if storage.config_name_exists(name):
        name = f"{name}-{uuid.uuid4().hex[:4]}"
    
    record = ConfigRecord(
        id=str(uuid.uuid4()),
        name=name,
        experiment_type=exp_type,
        config=request.config,
        created_at=_now(),
    )
    storage.save_config(record)
    return record


@app.post("/configs/upload", response_model=ConfigRecord)
def upload_config(file: UploadFile = File(...), name: str | None = None) -> ConfigRecord:
    """Upload a YAML config file and create a config record."""
    if not file.filename or not file.filename.endswith((".yaml", ".yml")):
        raise HTTPException(status_code=400, detail="Only YAML files are supported")
    
    content = file.file.read().decode("utf-8")
    payload = yaml.safe_load(content) or {}
    
    exp_type = _detect_config_type(payload)
    
    # Parse config based on type
    if exp_type == ExperimentType.CAUSAL_LM:
        config = CausalLMFullConfig(
            data=CausalLMDataConfig(**payload.get("data", {})),
            model=CausalLMModelConfig(**payload.get("model", {})),
            training=CausalLMTrainingConfig(**payload.get("training", {})),
            peft=CausalLMPeftConfig(**payload.get("peft", {})) if payload.get("peft") else CausalLMPeftConfig(),
        )
    else:
        config = MaskedLMFullConfig(
            data=MaskedLMDataConfig(**payload.get("data", {})),
            model=MaskedLMModelConfig(**payload.get("model", {})),
            training=MaskedLMTrainingConfig(**payload.get("training", {})),
        )
    
    # Use provided name, filename, or generate one
    config_name = name or Path(file.filename).stem or _generate_friendly_name()
    
    # Ensure name is unique
    if storage.config_name_exists(config_name):
        config_name = f"{config_name}-{uuid.uuid4().hex[:4]}"
    
    record = ConfigRecord(
        id=str(uuid.uuid4()),
        name=config_name,
        experiment_type=exp_type,
        config=config,
        created_at=_now(),
    )
    storage.save_config(record)
    return record


@app.delete("/configs/{config_id}")
def delete_config(config_id: str) -> dict[str, str]:
    """Delete a config from the database."""
    config = storage.delete_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"status": "deleted", "config_id": config_id}


# --- Dataset Endpoints ---


@app.post("/datasets/upload", response_model=DatasetInfo)
def upload_dataset(file: UploadFile = File(...)) -> DatasetInfo:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    dataset_id = str(uuid.uuid4())
    dest_path = UPLOAD_DIR / f"{dataset_id}_{file.filename}"

    with dest_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    frame = pd.read_csv(dest_path)
    info = DatasetInfo(
        id=dataset_id,
        filename=file.filename,
        path=str(dest_path),
        columns=list(frame.columns),
        row_count=len(frame),
        uploaded_at=_now(),
    )
    storage.save_dataset(info)
    return info


@app.get("/datasets", response_model=DatasetListResponse)
def list_datasets() -> DatasetListResponse:
    return DatasetListResponse(datasets=storage.list_datasets())


@app.get("/datasets/{dataset_id}", response_model=DatasetInfo)
def get_dataset(dataset_id: str) -> DatasetInfo:
    info = storage.get_dataset(dataset_id)
    if not info:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return info


@app.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: str) -> dict[str, str]:
    info = storage.delete_dataset(dataset_id)
    if not info:
        raise HTTPException(status_code=404, detail="Dataset not found")
    path = Path(info.path)
    if path.exists():
        path.unlink()
    return {"status": "deleted", "dataset_id": dataset_id}


# --- Experiment Execution ---


def _run_all_benchmarks_for_experiment(experiment_id: str) -> None:
    """Run all available benchmarks for a completed experiment, serially."""
    benchmarks = storage.list_benchmarks()
    if not benchmarks:
        return
    
    experiment = storage.get_experiment(experiment_id)
    
    # Set status to EVALUATING and initialize progress
    experiment.status = ExperimentStatus.EVALUATING
    experiment.auto_eval_total = len(benchmarks)
    experiment.auto_eval_completed = 0
    experiment.auto_eval_current = benchmarks[0].name if benchmarks else None
    storage.save_experiment(experiment)
    
    for i, benchmark in enumerate(benchmarks):
        # Update current benchmark being evaluated
        experiment.auto_eval_current = benchmark.name
        storage.save_experiment(experiment)
        
        eval_id = str(uuid.uuid4())
        eval_result = BenchmarkEvalResult(
            id=eval_id,
            benchmark_id=benchmark.id,
            benchmark_name=benchmark.name,
            experiment_id=experiment_id,
            question=benchmark.question,
            gold_answer=benchmark.gold_answer,
            model_answer="",
            bleu_score=0.0,
            rouge_score=0.0,
            status=BenchmarkStatus.PENDING,
            started_at=_now(),
        )
        storage.save_benchmark_eval(eval_result)
        
        # Run synchronously (serial execution)
        _run_benchmark_eval_sync(eval_id, benchmark, experiment)
        
        # Update progress
        experiment.auto_eval_completed = i + 1
        storage.save_experiment(experiment)
    
    # All done - set to completed
    experiment.status = ExperimentStatus.COMPLETED
    experiment.auto_eval_current = None
    storage.save_experiment(experiment)


def _run_masked_lm_experiment(experiment_id: str, request: MaskedLMRequest, config_id: str) -> None:
    exp = storage.get_experiment(experiment_id)
    output_dir = ARTIFACTS_DIR / f"masked_lm_{experiment_id}"
    exp.status = ExperimentStatus.RUNNING
    exp.output_dir = str(output_dir)
    storage.save_experiment(exp)

    dataset_info = storage.get_dataset(request.dataset_id)
    config_record = storage.get_config(config_id)
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
        exp.completed_at = _now()
        stop_registry.pop(experiment_id, None)
        storage.save_experiment(exp)
    
    # Auto-evaluate if enabled and experiment completed successfully
    if auto_evaluate and exp.status == ExperimentStatus.COMPLETED:
        _run_all_benchmarks_for_experiment(experiment_id)


def _run_causal_lm_experiment(experiment_id: str, request: CausalLMRequest, config_id: str) -> None:
    exp = storage.get_experiment(experiment_id)
    output_dir = ARTIFACTS_DIR / f"causal_lm_{experiment_id}"
    exp.status = ExperimentStatus.RUNNING
    exp.output_dir = str(output_dir)
    storage.save_experiment(exp)

    dataset_info = storage.get_dataset(request.dataset_id)
    config_record = storage.get_config(config_id)
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
        exp.completed_at = _now()
        stop_registry.pop(experiment_id, None)
        storage.save_experiment(exp)
    
    # Auto-evaluate if enabled and experiment completed successfully
    if auto_evaluate and exp.status == ExperimentStatus.COMPLETED:
        _run_all_benchmarks_for_experiment(experiment_id)


# --- Experiment Endpoints ---


def _resolve_or_create_config(
    config_id: str | None,
    config: MaskedLMFullConfig | CausalLMFullConfig | None,
    config_name: str | None,
    exp_type: ExperimentType,
) -> str:
    """Resolve existing config_id or create a new config record."""
    if config_id:
        existing = storage.get_config(config_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Config not found")
        return config_id
    
    if not config:
        raise HTTPException(status_code=400, detail="Either config_id or config must be provided")
    
    # Create new config record
    name = config_name or _generate_friendly_name()
    if storage.config_name_exists(name):
        name = f"{name}-{uuid.uuid4().hex[:4]}"
    
    record = ConfigRecord(
        id=str(uuid.uuid4()),
        name=name,
        experiment_type=exp_type,
        config=config,
        created_at=_now(),
    )
    storage.save_config(record)
    return record.id


@app.post("/experiments/masked-lm", response_model=ExperimentStartResponse)
def start_masked_lm_experiment(request: MaskedLMRequest) -> ExperimentStartResponse:
    dataset_info = storage.get_dataset(request.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Resolve or create config
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
        started_at=_now(),
    )
    storage.save_experiment(exp)

    thread = Thread(target=_run_masked_lm_experiment, args=(experiment_id, request, config_id))
    thread.start()

    return ExperimentStartResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.PENDING,
        message="Masked LM experiment started",
    )


@app.post("/experiments/causal-lm", response_model=ExperimentStartResponse)
def start_causal_lm_experiment(request: CausalLMRequest) -> ExperimentStartResponse:
    dataset_info = storage.get_dataset(request.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Resolve or create config
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
        started_at=_now(),
    )
    storage.save_experiment(exp)

    thread = Thread(target=_run_causal_lm_experiment, args=(experiment_id, request, config_id))
    thread.start()

    return ExperimentStartResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.PENDING,
        message="Causal LM experiment started",
    )


@app.get("/experiments", response_model=ExperimentListResponse)
def list_experiments() -> ExperimentListResponse:
    return ExperimentListResponse(experiments=storage.list_experiments())


@app.get("/experiments/{experiment_id}", response_model=ExperimentResult)
def get_experiment(experiment_id: str) -> ExperimentResult:
    exp = storage.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@app.get("/experiments/{experiment_id}/logs")
def get_experiment_logs(experiment_id: str) -> dict:
    exp = storage.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if not exp.output_dir:
        return {"logs": []}

    output_path = Path(exp.output_dir)

    # Try training_logs.json first
    logs_path = output_path / "training_logs.json"
    if logs_path.exists():
        import json
        with logs_path.open() as f:
            return {"logs": json.load(f)}

    # Fall back to trainer_state.json in checkpoints
    for checkpoint_dir in sorted(output_path.glob("checkpoint-*"), reverse=True):
        state_path = checkpoint_dir / "trainer_state.json"
        if state_path.exists():
            import json
            with state_path.open() as f:
                state = json.load(f)
                return {"logs": state.get("log_history", [])}

    return {"logs": []}


@app.delete("/experiments/{experiment_id}")
def delete_experiment(experiment_id: str) -> dict[str, str]:
    exp = storage.delete_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    # Clean up artifacts directory if it exists
    if exp.output_dir:
        output_path = Path(exp.output_dir)
        if output_path.exists():
            shutil.rmtree(output_path)
    return {"status": "deleted", "experiment_id": experiment_id}


@app.post("/experiments/{experiment_id}/stop")
def stop_experiment(experiment_id: str) -> dict[str, str]:
    exp = storage.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if exp.status != ExperimentStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Experiment is not running")
    stop_registry[experiment_id] = True
    return {"status": "stop_requested", "experiment_id": experiment_id}


# --- Benchmark Endpoints ---


@app.post("/benchmarks", response_model=Benchmark)
def create_benchmark(request: BenchmarkCreateRequest) -> Benchmark:
    benchmark_id = str(uuid.uuid4())
    benchmark = Benchmark(
        id=benchmark_id,
        name=request.name,
        question=request.question,
        gold_answer=request.gold_answer,
        created_at=_now(),
    )
    storage.save_benchmark(benchmark)
    return benchmark


@app.get("/benchmarks", response_model=BenchmarkListResponse)
def list_benchmarks() -> BenchmarkListResponse:
    return BenchmarkListResponse(benchmarks=storage.list_benchmarks())


@app.get("/benchmarks/{benchmark_id}", response_model=Benchmark)
def get_benchmark(benchmark_id: str) -> Benchmark:
    benchmark = storage.get_benchmark(benchmark_id)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return benchmark


@app.delete("/benchmarks/{benchmark_id}")
def delete_benchmark(benchmark_id: str) -> dict[str, str]:
    if not storage.delete_benchmark(benchmark_id):
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return {"status": "deleted", "benchmark_id": benchmark_id}


def _run_benchmark_eval(
    eval_id: str,
    benchmark: Benchmark,
    experiment: ExperimentResult,
    request: BenchmarkEvalRequest,
) -> None:
    from src.models import BenchmarkRunScore
    
    eval_result = storage.get_benchmark_eval(eval_id)
    eval_result.status = BenchmarkStatus.RUNNING
    eval_result.num_runs = request.num_runs
    storage.save_benchmark_eval(eval_result)

    try:
        model_path = Path(experiment.output_dir)
        model, tokenizer = load_model_and_tokenizer(model_path)

        run_scores: list[BenchmarkRunScore] = []
        for run_num in range(1, request.num_runs + 1):
            model_answer = generate_response(
                model=model,
                tokenizer=tokenizer,
                prompt=benchmark.question,
                max_new_tokens=request.max_new_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
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
        eval_result.completed_at = _now()
        storage.save_benchmark_eval(eval_result)


@app.post("/benchmarks/{benchmark_id}/evaluate", response_model=BenchmarkEvalStartResponse)
def start_benchmark_evaluation(benchmark_id: str, request: BenchmarkEvalRequest) -> BenchmarkEvalStartResponse:
    benchmark = storage.get_benchmark(benchmark_id)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    experiment = storage.get_experiment(request.experiment_id)
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
        started_at=_now(),
    )
    storage.save_benchmark_eval(eval_result)

    thread = Thread(target=_run_benchmark_eval, args=(eval_id, benchmark, experiment, request))
    thread.start()

    return BenchmarkEvalStartResponse(
        eval_id=eval_id,
        status=BenchmarkStatus.PENDING,
        message="Benchmark evaluation started",
    )


@app.get("/benchmarks/{benchmark_id}/evaluations", response_model=BenchmarkEvalListResponse)
def list_benchmark_evaluations(benchmark_id: str) -> BenchmarkEvalListResponse:
    benchmark = storage.get_benchmark(benchmark_id)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return BenchmarkEvalListResponse(evaluations=storage.list_benchmark_evals_by_benchmark(benchmark_id))


@app.get("/evaluations", response_model=BenchmarkEvalListResponse)
def list_all_evaluations() -> BenchmarkEvalListResponse:
    return BenchmarkEvalListResponse(evaluations=storage.list_benchmark_evals())


@app.get("/evaluations/compare", response_model=EvaluationComparisonResponse)
def compare_evaluations() -> EvaluationComparisonResponse:
    evals = storage.list_benchmark_evals()
    items = []
    for ev in evals:
        if ev.status != BenchmarkStatus.COMPLETED:
            continue
        exp = storage.get_experiment(ev.experiment_id)
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


@app.get("/evaluations/{eval_id}", response_model=BenchmarkEvalResult)
def get_evaluation(eval_id: str) -> BenchmarkEvalResult:
    eval_result = storage.get_benchmark_eval(eval_id)
    if not eval_result:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return eval_result


@app.delete("/evaluations/{eval_id}")
def delete_evaluation(eval_id: str) -> dict[str, str]:
    if not storage.delete_benchmark_eval(eval_id):
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return {"status": "deleted", "eval_id": eval_id}


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


@app.post("/experiments/compare", response_model=ExperimentComparisonResponse)
def compare_experiments(experiment_ids: list[str]) -> ExperimentComparisonResponse:
    """Compare configs of multiple experiments."""
    experiments = []
    for exp_id in experiment_ids:
        exp = storage.get_experiment(exp_id)
        if not exp:
            raise HTTPException(status_code=404, detail=f"Experiment {exp_id} not found")

        evals = storage.list_benchmark_evals()
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


# --- Meta-Learning Endpoints ---

# Global predictor instance (loaded on demand)
_predictor: PerformancePredictor | None = None


def _get_predictor() -> PerformancePredictor:
    """Get or load the performance predictor."""
    global _predictor
    if _predictor is None:
        _predictor = PerformancePredictor()
        try:
            _predictor.load()
        except FileNotFoundError:
            pass  # No trained model yet
    return _predictor


class MetaProbeRequest(BaseModel):
    """Request to run a probe and extract meta-features."""
    dataset_id: str
    config: CausalLMFullConfig
    probe_steps: int = 10


class MetaProbeResponse(BaseModel):
    """Response from probe run."""
    features: MetaFeatureVector
    message: str


class MetaFeaturesListResponse(BaseModel):
    """List of stored meta-feature vectors."""
    features: list[MetaFeatureVector]


class MetaTrainRequest(BaseModel):
    """Request to train the predictor."""
    target: str = "final_bleu_score"
    include_synthetic: bool = True


class MetaTrainResponse(BaseModel):
    """Response from predictor training."""
    metrics: dict[str, float]
    message: str


class MetaPredictRequest(BaseModel):
    """Request to predict performance."""
    dataset_id: str
    config: CausalLMFullConfig
    probe_steps: int = 10


class MetaPredictResponse(BaseModel):
    """Response from performance prediction."""
    predicted_performance: float
    features: MetaFeatureVector
    message: str


class MetaExplainResponse(BaseModel):
    """Response from SHAP explanation."""
    experiment_id: str
    prediction: float
    top_drivers: list[dict]
    shap_values: dict[str, float]


class MetaSyntheticRequest(BaseModel):
    """Request to generate synthetic training data."""
    n_samples: int = 100
    seed: int = 42


class MetaSyntheticResponse(BaseModel):
    """Response from synthetic data generation."""
    count: int
    message: str


@app.post("/meta/generate-synthetic", response_model=MetaSyntheticResponse)
def generate_synthetic_data(request: MetaSyntheticRequest) -> MetaSyntheticResponse:
    """Generate synthetic meta-features for predictor bootstrapping.
    
    Creates synthetic training data based on domain knowledge about
    fine-tuning success factors. This allows the predictor to work
    before enough real experiments have been collected.
    """
    synthetic = generate_synthetic_features(n=request.n_samples, seed=request.seed)
    
    for f in synthetic:
        storage.save_meta_features(f)
    
    return MetaSyntheticResponse(
        count=len(synthetic),
        message=f"Generated {len(synthetic)} synthetic meta-feature vectors",
    )


@app.delete("/meta/synthetic")
def clear_synthetic_data() -> dict:
    """Remove all synthetic meta-features from storage."""
    all_features = storage.list_meta_features()
    removed = 0
    for f in all_features:
        if f.is_synthetic:
            storage.delete_meta_features(f.experiment_id)
            removed += 1
    return {"removed": removed, "message": f"Removed {removed} synthetic features"}


@app.post("/meta/extract/{experiment_id}", response_model=MetaFeatureVector)
def extract_meta_features(experiment_id: str) -> MetaFeatureVector:
    """Extract and store meta-features for a completed experiment."""
    exp = storage.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if exp.status != ExperimentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Experiment not completed")

    dataset_info = storage.get_dataset(exp.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get BLEU score from benchmark evals if available
    evals = storage.list_benchmark_evals()
    bleu_scores = [e.bleu_score for e in evals if e.experiment_id == experiment_id and e.status == BenchmarkStatus.COMPLETED]
    final_bleu = sum(bleu_scores) / len(bleu_scores) if bleu_scores else None

    # Run probe to get full features
    features = run_probe(
        config=exp.config,
        csv_path=Path(dataset_info.path),
        probe_steps=10,
        experiment_id=experiment_id,
    )

    # Update with actual results
    features.final_eval_loss = exp.metrics.get("eval_loss")
    features.final_bleu_score = final_bleu

    storage.save_meta_features(features)
    return features


@app.post("/meta/probe", response_model=MetaProbeResponse)
def run_meta_probe(request: MetaProbeRequest) -> MetaProbeResponse:
    """Run a short probe to extract meta-features without full training."""
    dataset_info = storage.get_dataset(request.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")

    probe_id = f"probe_{uuid.uuid4()}"
    features = run_probe(
        config=request.config,
        csv_path=Path(dataset_info.path),
        probe_steps=request.probe_steps,
        experiment_id=probe_id,
    )

    storage.save_meta_features(features)

    return MetaProbeResponse(
        features=features,
        message=f"Probe completed with {request.probe_steps} steps",
    )


@app.get("/meta/features", response_model=MetaFeaturesListResponse)
def list_meta_features() -> MetaFeaturesListResponse:
    """List all stored meta-feature vectors."""
    return MetaFeaturesListResponse(features=storage.list_meta_features())


@app.get("/meta/features/{experiment_id}", response_model=MetaFeatureVector)
def get_meta_features(experiment_id: str) -> MetaFeatureVector:
    """Get meta-features for a specific experiment."""
    features = storage.get_meta_features(experiment_id)
    if not features:
        raise HTTPException(status_code=404, detail="Meta-features not found")
    return features


@app.post("/meta/train-predictor", response_model=MetaTrainResponse)
def train_predictor(request: MetaTrainRequest) -> MetaTrainResponse:
    """Train the GBM predictor on stored meta-features."""
    global _predictor

    features = storage.list_meta_features()
    
    # Filter synthetic if not included
    if not request.include_synthetic:
        features = [f for f in features if not f.is_synthetic]
    
    if len(features) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 5 experiments with results, got {len(features)}",
        )

    # Filter to those with target values
    valid_features = [f for f in features if getattr(f, request.target) is not None]
    if len(valid_features) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 5 experiments with {request.target} set, got {len(valid_features)}",
        )

    predictor = PerformancePredictor()
    metrics = predictor.fit(valid_features, target=request.target)
    predictor.save()

    _predictor = predictor
    
    synthetic_count = sum(1 for f in valid_features if f.is_synthetic)
    real_count = len(valid_features) - synthetic_count

    return MetaTrainResponse(
        metrics=metrics,
        message=f"Predictor trained on {len(valid_features)} experiments ({real_count} real, {synthetic_count} synthetic)",
    )


@app.post("/meta/predict", response_model=MetaPredictResponse)
def predict_performance(request: MetaPredictRequest) -> MetaPredictResponse:
    """Predict performance for a new config using the trained predictor."""
    predictor = _get_predictor()
    if predictor.model is None:
        raise HTTPException(
            status_code=400,
            detail="Predictor not trained. Call /meta/train-predictor first.",
        )

    dataset_info = storage.get_dataset(request.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Run probe to get features
    probe_id = f"predict_{uuid.uuid4()}"
    features = run_probe(
        config=request.config,
        csv_path=Path(dataset_info.path),
        probe_steps=request.probe_steps,
        experiment_id=probe_id,
    )

    prediction = predictor.predict(features)

    return MetaPredictResponse(
        predicted_performance=prediction,
        features=features,
        message=f"Predicted {predictor.target_name}: {prediction:.4f}",
    )


@app.get("/meta/explain/{experiment_id}", response_model=MetaExplainResponse)
def explain_prediction(experiment_id: str) -> MetaExplainResponse:
    """Get SHAP explanation for a prediction."""
    predictor = _get_predictor()
    if predictor.model is None:
        raise HTTPException(
            status_code=400,
            detail="Predictor not trained. Call /meta/train-predictor first.",
        )

    features = storage.get_meta_features(experiment_id)
    if not features:
        raise HTTPException(status_code=404, detail="Meta-features not found")

    explainer = PredictionExplainer(predictor)
    prediction = predictor.predict(features)
    shap_values = explainer.explain(features)
    top_drivers = explainer.get_top_drivers(features, n=5)

    return MetaExplainResponse(
        experiment_id=experiment_id,
        prediction=prediction,
        top_drivers=top_drivers,
        shap_values=shap_values,
    )


@app.get("/meta/feature-importance")
def get_feature_importance() -> dict[str, float]:
    """Get feature importance from the trained predictor."""
    predictor = _get_predictor()
    if predictor.model is None:
        raise HTTPException(
            status_code=400,
            detail="Predictor not trained. Call /meta/train-predictor first.",
        )
    return predictor.feature_importance()


class OptimizeRequest(BaseModel):
    """Request to optimize config for a dataset."""
    dataset_id: str
    config: CausalLMFullConfig
    search_space: SearchSpace | None = None
    probe_steps: int = 10
    max_candidates: int = 12


class ConfigCandidateResponse(BaseModel):
    """A config candidate with predicted performance."""
    rank: int
    learning_rate: float
    lora_r: int
    batch_size: int
    num_epochs: int
    predicted_bleu: float


class OptimizeStartResponse(BaseModel):
    """Response when optimization job is started."""
    job_id: str
    message: str


class OptimizeStatusResponse(BaseModel):
    """Response with optimization job status."""
    job_id: str
    status: str
    started_at: str
    completed_at: str | None = None
    candidates: list[ConfigCandidateResponse] | None = None
    best_config: dict | None = None
    message: str | None = None
    error: str | None = None


def _run_optimization_job(
    job_id: str,
    dataset_path: Path,
    config: CausalLMFullConfig,
    search_space: SearchSpace | None,
    probe_steps: int,
    max_candidates: int,
) -> None:
    """Background worker for optimization job."""
    from .storage import OptimizationJob, OptimizationStatus, save_optimization_job, get_optimization_job
    
    job = get_optimization_job(job_id)
    if not job:
        return
    
    # Update to running
    job.status = OptimizationStatus.RUNNING
    save_optimization_job(job)
    
    try:
        predictor = _get_predictor()
        
        candidates = optimize_config(
            base_config=config,
            csv_path=dataset_path,
            predictor=predictor,
            search_space=search_space,
            probe_steps=probe_steps,
            max_candidates=max_candidates,
        )
        
        # Build results
        candidate_dicts = [
            {
                "rank": c.rank,
                "learning_rate": c.learning_rate,
                "lora_r": c.lora_r,
                "batch_size": c.batch_size,
                "num_epochs": c.num_epochs,
                "predicted_bleu": c.predicted_bleu,
            }
            for c in candidates
        ]
        
        best = candidates[0] if candidates else None
        best_config = {}
        if best:
            best_config = {
                "learning_rate": best.learning_rate,
                "lora_r": best.lora_r,
                "batch_size": best.batch_size,
                "num_epochs": best.num_epochs,
            }
        
        # Update job with results
        job.status = OptimizationStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        job.candidates = candidate_dicts
        job.best_config = best_config
        job.message = f"Evaluated {len(candidates)} configs. Best predicted BLEU: {candidates[0].predicted_bleu:.2f}" if candidates else "No candidates evaluated"
        save_optimization_job(job)
        
    except Exception as e:
        job.status = OptimizationStatus.FAILED
        job.completed_at = datetime.now(timezone.utc)
        job.error = str(e)
        save_optimization_job(job)


@app.post("/meta/optimize", response_model=OptimizeStartResponse)
def start_optimization(request: OptimizeRequest) -> OptimizeStartResponse:
    """Start config optimization as a background job.
    
    Returns immediately with a job ID. Poll /meta/optimize/{job_id} for status.
    """
    from .storage import OptimizationJob, OptimizationStatus, save_optimization_job
    
    predictor = _get_predictor()
    if predictor.model is None:
        raise HTTPException(
            status_code=400,
            detail="Predictor not trained. Call /meta/train-predictor first.",
        )
    
    dataset_info = storage.get_dataset(request.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Create job
    job_id = str(uuid.uuid4())
    job = OptimizationJob(
        id=job_id,
        dataset_id=request.dataset_id,
        status=OptimizationStatus.PENDING,
        started_at=datetime.now(timezone.utc),
    )
    save_optimization_job(job)
    
    # Start background thread
    thread = Thread(
        target=_run_optimization_job,
        args=(
            job_id,
            Path(dataset_info.path),
            request.config,
            request.search_space,
            request.probe_steps,
            request.max_candidates,
        ),
        daemon=True,
    )
    thread.start()
    
    return OptimizeStartResponse(
        job_id=job_id,
        message=f"Optimization started. Poll /meta/optimize/{job_id} for status.",
    )


@app.get("/meta/optimize/{job_id}", response_model=OptimizeStatusResponse)
def get_optimization_status(job_id: str) -> OptimizeStatusResponse:
    """Get status of an optimization job."""
    from .storage import get_optimization_job
    
    job = get_optimization_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Optimization job not found")
    
    candidates = None
    if job.candidates:
        candidates = [
            ConfigCandidateResponse(
                rank=c["rank"],
                learning_rate=c["learning_rate"],
                lora_r=c["lora_r"],
                batch_size=c["batch_size"],
                num_epochs=c["num_epochs"],
                predicted_bleu=c["predicted_bleu"],
            )
            for c in job.candidates
        ]
    
    return OptimizeStatusResponse(
        job_id=job.id,
        status=job.status.value,
        started_at=job.started_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        candidates=candidates,
        best_config=job.best_config,
        message=job.message,
        error=job.error,
    )


class SensitivityRequest(BaseModel):
    """Request for sensitivity analysis."""
    experiment_id: str


@app.post("/meta/sensitivity", response_model=dict)
def analyze_sensitivity(request: SensitivityRequest) -> dict:
    """Analyze how changing hyperparameters would affect predictions.
    
    Uses SHAP values to estimate the impact of each tunable parameter.
    """
    predictor = _get_predictor()
    if predictor.model is None:
        raise HTTPException(
            status_code=400,
            detail="Predictor not trained. Call /meta/train-predictor first.",
        )
    
    features = storage.get_meta_features(request.experiment_id)
    if not features:
        raise HTTPException(status_code=404, detail="Meta-features not found")
    
    sensitivity = quick_sensitivity_analysis(features, predictor)
    prediction = predictor.predict(features)
    
    return {
        "experiment_id": request.experiment_id,
        "current_prediction": prediction,
        "sensitivity": sensitivity,
    }


# --- AutoTune Endpoints ---


def _get_default_base_config(question_field: str, answer_field: str) -> CausalLMFullConfig:
    """Create a sensible default config for autotune."""
    return CausalLMFullConfig(
        data=CausalLMDataConfig(
            question_field=question_field,
            answer_field=answer_field,
            system_prompt="You are a helpful AI assistant.",
            validation_split=0.2,
            max_length=512,
        ),
        model=CausalLMModelConfig(
            pretrained_model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            trust_remote_code=False,
            pad_token_override="</s>",
        ),
        training=CausalLMTrainingConfig(
            num_train_epochs=2,
            per_device_train_batch_size=2,
            per_device_eval_batch_size=2,
            learning_rate=1e-4,
            warmup_ratio=0.03,
            gradient_accumulation_steps=4,
            gradient_checkpointing=True,
            fp16=True,
            logging_steps=10,
            eval_steps=50,
            save_steps=100,
            early_stopping_patience=3,
        ),
        peft=CausalLMPeftConfig(
            enabled=True,
            r=8,
            lora_alpha=16,
            lora_dropout=0.05,
        ),
    )


def _run_autotune_job(job_id: str, request: AutoTuneRequest) -> None:
    """Background worker that orchestrates the full autotune pipeline."""
    import time
    
    job = storage.get_autotune_job(job_id)
    if not job:
        return
    
    dataset_info = storage.get_dataset(request.dataset_id)
    if not dataset_info:
        job.status = AutoTuneStatus.FAILED
        job.error = "Dataset not found"
        job.completed_at = _now()
        storage.save_autotune_job(job)
        return
    
    csv_path = Path(dataset_info.path)
    
    # Get base config
    if request.base_config_id:
        config_record = storage.get_config(request.base_config_id)
        if not config_record:
            job.status = AutoTuneStatus.FAILED
            job.error = "Base config not found"
            job.completed_at = _now()
            storage.save_autotune_job(job)
            return
        base_config = config_record.config
    else:
        base_config = _get_default_base_config(request.question_field, request.answer_field)
    
    try:
        # Phase 1: Probing
        job.status = AutoTuneStatus.PROBING
        job.phase_message = "Running probes to predict best configs..."
        storage.save_autotune_job(job)
        
        predictor = _get_predictor()
        if predictor.model is None:
            job.status = AutoTuneStatus.FAILED
            job.error = "Predictor not trained. Generate synthetic data and train first."
            job.completed_at = _now()
            storage.save_autotune_job(job)
            return
        
        # Run optimizer to get top candidates
        candidates = optimize_config(
            base_config=base_config,
            csv_path=csv_path,
            predictor=predictor,
            probe_steps=request.probe_steps,
            max_candidates=request.top_k * 3,  # Evaluate more, pick top_k
        )
        
        top_candidates = candidates[:request.top_k]
        
        # Convert to AutoTuneCandidate
        job.candidates = [
            AutoTuneCandidate(
                rank=c.rank,
                learning_rate=c.learning_rate,
                lora_r=c.lora_r,
                batch_size=c.batch_size,
                num_epochs=c.num_epochs,
                predicted_bleu=c.predicted_bleu,
            )
            for c in top_candidates
        ]
        storage.save_autotune_job(job)
        
        # Phase 2: Training
        job.status = AutoTuneStatus.TRAINING
        storage.save_autotune_job(job)
        
        for i, candidate in enumerate(job.candidates):
            job.current_training_idx = i
            job.phase_message = f"Training model {i+1}/{len(job.candidates)} (LR={candidate.learning_rate:.0e}, LoRA r={candidate.lora_r})"
            storage.save_autotune_job(job)
            
            # Build config for this candidate
            config = _build_candidate_config(base_config, candidate)
            
            # Create config record
            config_name = f"autotune_{job_id[:8]}_rank{candidate.rank}"
            config_record = ConfigRecord(
                id=str(uuid.uuid4()),
                name=config_name,
                experiment_type=ExperimentType.CAUSAL_LM,
                config=config,
                created_at=_now(),
            )
            storage.save_config(config_record)
            
            # Start experiment
            experiment_id = str(uuid.uuid4())
            exp = ExperimentResult(
                id=experiment_id,
                experiment_type=ExperimentType.CAUSAL_LM,
                status=ExperimentStatus.PENDING,
                dataset_id=request.dataset_id,
                dataset_filename=dataset_info.filename,
                config_id=config_record.id,
                started_at=_now(),
            )
            storage.save_experiment(exp)
            
            # Run training synchronously (sequential)
            _run_causal_lm_experiment_sync(experiment_id, request.dataset_id, config_record.id)
            
            # Update candidate with experiment_id
            candidate.experiment_id = experiment_id
            storage.save_autotune_job(job)
        
        # Phase 3: Evaluation
        job.status = AutoTuneStatus.EVALUATING
        storage.save_autotune_job(job)
        
        benchmark = storage.get_benchmark(job.benchmark_id)
        
        for i, candidate in enumerate(job.candidates):
            if not candidate.experiment_id:
                continue
            
            exp = storage.get_experiment(candidate.experiment_id)
            if not exp or exp.status != ExperimentStatus.COMPLETED:
                continue
            
            job.current_eval_idx = i
            job.phase_message = f"Evaluating model {i+1}/{len(job.candidates)}"
            storage.save_autotune_job(job)
            
            # Run benchmark evaluation synchronously
            eval_id = str(uuid.uuid4())
            eval_result = BenchmarkEvalResult(
                id=eval_id,
                benchmark_id=benchmark.id,
                benchmark_name=benchmark.name,
                experiment_id=candidate.experiment_id,
                question=benchmark.question,
                gold_answer=benchmark.gold_answer,
                model_answer="",
                bleu_score=0.0,
                rouge_score=0.0,
                status=BenchmarkStatus.PENDING,
                started_at=_now(),
            )
            storage.save_benchmark_eval(eval_result)
            
            # Run eval synchronously
            _run_benchmark_eval_sync(eval_id, benchmark, exp)
            
            # Get result
            eval_result = storage.get_benchmark_eval(eval_id)
            candidate.eval_id = eval_id
            candidate.actual_bleu = eval_result.bleu_score if eval_result.status == BenchmarkStatus.COMPLETED else None
            storage.save_autotune_job(job)
        
        # Re-rank by actual BLEU
        job.candidates.sort(key=lambda c: c.actual_bleu or 0, reverse=True)
        for i, c in enumerate(job.candidates):
            c.rank = i + 1
        
        job.status = AutoTuneStatus.COMPLETED
        job.phase_message = f"Complete! Best BLEU: {job.candidates[0].actual_bleu:.2f}" if job.candidates and job.candidates[0].actual_bleu else "Complete!"
        job.completed_at = _now()
        storage.save_autotune_job(job)
        
    except Exception as e:
        job.status = AutoTuneStatus.FAILED
        job.error = str(e)
        job.completed_at = _now()
        storage.save_autotune_job(job)


def _build_candidate_config(base_config: CausalLMFullConfig, candidate: AutoTuneCandidate) -> CausalLMFullConfig:
    """Build a full config from base config and candidate hyperparams."""
    config_dict = base_config.model_dump()
    config_dict["training"]["learning_rate"] = candidate.learning_rate
    config_dict["training"]["per_device_train_batch_size"] = candidate.batch_size
    config_dict["training"]["num_train_epochs"] = candidate.num_epochs
    if config_dict.get("peft", {}).get("enabled", False):
        config_dict["peft"]["r"] = candidate.lora_r
        config_dict["peft"]["lora_alpha"] = candidate.lora_r * 2
    return CausalLMFullConfig(**config_dict)


def _run_causal_lm_experiment_sync(experiment_id: str, dataset_id: str, config_id: str) -> None:
    """Run causal LM experiment synchronously."""
    exp = storage.get_experiment(experiment_id)
    output_dir = ARTIFACTS_DIR / f"causal_lm_{experiment_id}"
    exp.status = ExperimentStatus.RUNNING
    exp.output_dir = str(output_dir)
    storage.save_experiment(exp)

    dataset_info = storage.get_dataset(dataset_id)
    config_record = storage.get_config(config_id)
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
        exp.completed_at = _now()
        stop_registry.pop(experiment_id, None)
        storage.save_experiment(exp)


def _run_benchmark_eval_sync(eval_id: str, benchmark: Benchmark, experiment: ExperimentResult) -> None:
    """Run benchmark evaluation synchronously."""
    eval_result = storage.get_benchmark_eval(eval_id)
    eval_result.status = BenchmarkStatus.RUNNING
    storage.save_benchmark_eval(eval_result)

    try:
        model_path = Path(experiment.output_dir)
        model, tokenizer = load_model_and_tokenizer(model_path)

        model_answer = generate_response(
            model=model,
            tokenizer=tokenizer,
            prompt=benchmark.question,
            max_new_tokens=128,
            temperature=0.7,
            top_p=0.9,
        )

        bleu_score = compute_bleu_score(model_answer, benchmark.gold_answer)
        rouge_score = compute_rouge_l_score(model_answer, benchmark.gold_answer)

        eval_result.model_answer = model_answer
        eval_result.bleu_score = bleu_score
        eval_result.rouge_score = rouge_score
        eval_result.status = BenchmarkStatus.COMPLETED
    except Exception as e:
        eval_result.status = BenchmarkStatus.FAILED
        eval_result.error = str(e)
    finally:
        eval_result.completed_at = _now()
        storage.save_benchmark_eval(eval_result)


@app.post("/autotune/run", response_model=AutoTuneStartResponse)
def start_autotune(request: AutoTuneRequest) -> AutoTuneStartResponse:
    """Start the autotune fine-tuning pipeline.
    
    This will:
    1. Run probes to predict best configs
    2. Train top_k models sequentially with early stopping
    3. Evaluate each on the benchmark
    4. Return ranked results
    """
    # Validate dataset
    dataset_info = storage.get_dataset(request.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Create or get benchmark
    benchmark_id = request.benchmark_id
    if not benchmark_id:
        # Create benchmark from dataset or manual input
        if request.benchmark_question and request.benchmark_answer:
            # Manual benchmark
            benchmark_id = str(uuid.uuid4())
            benchmark = Benchmark(
                id=benchmark_id,
                name=f"autotune_{benchmark_id[:8]}",
                question=request.benchmark_question,
                gold_answer=request.benchmark_answer,
                created_at=_now(),
            )
            storage.save_benchmark(benchmark)
        elif request.benchmark_row_idx is not None:
            # Create from dataset row
            df = pd.read_csv(dataset_info.path)
            if request.benchmark_row_idx >= len(df):
                raise HTTPException(status_code=400, detail=f"Row index {request.benchmark_row_idx} out of range")
            row = df.iloc[request.benchmark_row_idx]
            question = str(row.get(request.question_field, ""))
            answer = str(row.get(request.answer_field, ""))
            if not question or not answer:
                raise HTTPException(status_code=400, detail="Could not extract question/answer from row")
            
            benchmark_id = str(uuid.uuid4())
            benchmark = Benchmark(
                id=benchmark_id,
                name=f"autotune_{benchmark_id[:8]}",
                question=question,
                gold_answer=answer,
                created_at=_now(),
            )
            storage.save_benchmark(benchmark)
        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide benchmark_id, benchmark_question+answer, or benchmark_row_idx"
            )
    else:
        # Validate existing benchmark
        if not storage.get_benchmark(benchmark_id):
            raise HTTPException(status_code=404, detail="Benchmark not found")
    
    # Validate predictor is trained
    predictor = _get_predictor()
    if predictor.model is None:
        raise HTTPException(
            status_code=400,
            detail="Predictor not trained. Generate synthetic data and train first via /meta/generate-synthetic and /meta/train-predictor",
        )
    
    # Create job
    job_id = str(uuid.uuid4())
    job = AutoTuneJob(
        id=job_id,
        dataset_id=request.dataset_id,
        benchmark_id=benchmark_id,
        base_config_id=request.base_config_id,
        status=AutoTuneStatus.PENDING,
        phase_message="Starting AutoTune...",
        top_k=request.top_k,
        started_at=_now(),
    )
    storage.save_autotune_job(job)
    
    # Start background thread
    thread = Thread(target=_run_autotune_job, args=(job_id, request), daemon=True)
    thread.start()
    
    return AutoTuneStartResponse(
        job_id=job_id,
        status=AutoTuneStatus.PENDING,
        message=f"AutoTune started. Training {request.top_k} configs. Poll /autotune/{job_id} for status.",
    )


@app.get("/autotune/{job_id}", response_model=AutoTuneStatusResponse)
def get_autotune_status(job_id: str) -> AutoTuneStatusResponse:
    """Get status of an autotune job."""
    job = storage.get_autotune_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="AutoTune job not found")
    
    return AutoTuneStatusResponse(
        job=job,
        message=job.phase_message or job.status.value,
    )


@app.get("/autotune", response_model=AutoTuneListResponse)
def list_autotune_jobs() -> AutoTuneListResponse:
    """List all autotune jobs."""
    return AutoTuneListResponse(jobs=storage.list_autotune_jobs())


@app.delete("/autotune/{job_id}")
def delete_autotune_job(job_id: str) -> dict[str, str]:
    """Delete an autotune job."""
    if not storage.delete_autotune_job(job_id):
        raise HTTPException(status_code=404, detail="AutoTune job not found")
    return {"status": "deleted", "job_id": job_id}
