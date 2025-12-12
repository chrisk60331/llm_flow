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

from .config import DataConfig, ExperimentConfig, ModelConfig, TrainingConfig
from .llm_config import (
    LLMDataConfig,
    LLMExperimentConfig,
    LLMModelConfig,
    LLMPeftConfig,
    LLMTrainingConfig,
)
from .llm_training import run_llm_training
from .benchmark import compute_bleu_score, generate_response, load_model_and_tokenizer
from .models import (
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
    ConfigFileInfo,
    ConfigFileListResponse,
    DatasetInfo,
    DatasetListResponse,
    EvaluationComparisonItem,
    EvaluationComparisonResponse,
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
from . import storage

UPLOAD_DIR = Path("data/uploads")
ARTIFACTS_DIR = Path("artifacts")
CONFIGS_DIR = Path("configs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.init_db()
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


# --- Config File Endpoints ---


def _detect_config_type(payload: dict) -> ExperimentType:
    data_section = payload.get("data", {})
    if "system_prompt" in data_section and "template" in data_section:
        return ExperimentType.CAUSAL_LM
    return ExperimentType.MASKED_LM


@app.get("/configs", response_model=ConfigFileListResponse)
def list_configs() -> ConfigFileListResponse:
    configs = []
    if CONFIGS_DIR.exists():
        for path in CONFIGS_DIR.glob("*.yaml"):
            with path.open("r") as f:
                payload = yaml.safe_load(f) or {}
            exp_type = _detect_config_type(payload)
            model_name = payload.get("model", {}).get("pretrained_model_name", "unknown")
            dataset_path = payload.get("data", {}).get("csv_path", "unknown")
            configs.append(
                ConfigFileInfo(
                    name=path.stem,
                    path=str(path),
                    experiment_type=exp_type,
                    model_name=model_name,
                    dataset_path=dataset_path,
                )
            )
    return ConfigFileListResponse(configs=configs)


@app.get("/configs/{config_name}")
def get_config(config_name: str) -> dict:
    path = CONFIGS_DIR / f"{config_name}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Config not found")
    with path.open("r") as f:
        payload = yaml.safe_load(f) or {}
    payload["_experiment_type"] = _detect_config_type(payload).value
    return payload


@app.get("/configs/by-type/{experiment_type}", response_model=ConfigFileListResponse)
def list_configs_by_type(experiment_type: str) -> ConfigFileListResponse:
    target_type = ExperimentType(experiment_type)
    configs = []
    if CONFIGS_DIR.exists():
        for path in CONFIGS_DIR.glob("*.yaml"):
            with path.open("r") as f:
                payload = yaml.safe_load(f) or {}
            exp_type = _detect_config_type(payload)
            if exp_type == target_type:
                model_name = payload.get("model", {}).get("pretrained_model_name", "unknown")
                dataset_path = payload.get("data", {}).get("csv_path", "unknown")
                configs.append(
                    ConfigFileInfo(
                        name=path.stem,
                        path=str(path),
                        experiment_type=exp_type,
                        model_name=model_name,
                        dataset_path=dataset_path,
                    )
                )
    return ConfigFileListResponse(configs=configs)


@app.post("/configs/{config_name}")
def save_config(config_name: str, payload: dict) -> dict:
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    path = CONFIGS_DIR / f"{config_name}.yaml"
    payload.pop("_experiment_type", None)
    with path.open("w") as f:
        yaml.dump(payload, f, default_flow_style=False)
    return {"status": "saved", "path": str(path)}


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


def _run_masked_lm_experiment(experiment_id: str, request: MaskedLMRequest) -> None:
    exp = storage.get_experiment(experiment_id)
    output_dir = ARTIFACTS_DIR / f"masked_lm_{experiment_id}"
    exp.status = ExperimentStatus.RUNNING
    exp.output_dir = str(output_dir)
    storage.save_experiment(exp)

    dataset_info = storage.get_dataset(request.dataset_id)
    cfg = request.config

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
        ),
    )

    try:
        _, metrics = run_training(config)
        exp.status = ExperimentStatus.COMPLETED
        exp.metrics = metrics
    except Exception as e:
        exp.status = ExperimentStatus.FAILED
        exp.error = str(e)
    finally:
        exp.completed_at = _now()
        storage.save_experiment(exp)


def _run_causal_lm_experiment(experiment_id: str, request: CausalLMRequest) -> None:
    exp = storage.get_experiment(experiment_id)
    output_dir = ARTIFACTS_DIR / f"causal_lm_{experiment_id}"
    exp.status = ExperimentStatus.RUNNING
    exp.output_dir = str(output_dir)
    storage.save_experiment(exp)

    dataset_info = storage.get_dataset(request.dataset_id)
    cfg = request.config

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
        ),
        peft=peft_config,
    )

    try:
        _, metrics = run_llm_training(config)
        exp.status = ExperimentStatus.COMPLETED
        exp.metrics = metrics
    except Exception as e:
        exp.status = ExperimentStatus.FAILED
        exp.error = str(e)
    finally:
        exp.completed_at = _now()
        storage.save_experiment(exp)


# --- Experiment Endpoints ---


@app.post("/experiments/masked-lm", response_model=ExperimentStartResponse)
def start_masked_lm_experiment(request: MaskedLMRequest) -> ExperimentStartResponse:
    dataset_info = storage.get_dataset(request.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")

    experiment_id = str(uuid.uuid4())
    exp = ExperimentResult(
        id=experiment_id,
        experiment_type=ExperimentType.MASKED_LM,
        status=ExperimentStatus.PENDING,
        dataset_id=request.dataset_id,
        dataset_filename=dataset_info.filename,
        config=request.config,
        started_at=_now(),
    )
    storage.save_experiment(exp)

    thread = Thread(target=_run_masked_lm_experiment, args=(experiment_id, request))
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

    experiment_id = str(uuid.uuid4())
    exp = ExperimentResult(
        id=experiment_id,
        experiment_type=ExperimentType.CAUSAL_LM,
        status=ExperimentStatus.PENDING,
        dataset_id=request.dataset_id,
        dataset_filename=dataset_info.filename,
        config=request.config,
        started_at=_now(),
    )
    storage.save_experiment(exp)

    thread = Thread(target=_run_causal_lm_experiment, args=(experiment_id, request))
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
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
        )

        bleu_score = compute_bleu_score(model_answer, benchmark.gold_answer)

        eval_result.model_answer = model_answer
        eval_result.bleu_score = bleu_score
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
                learning_rate=learning_rate,
                num_epochs=num_epochs,
                batch_size=batch_size,
                lora_r=lora_r,
                lora_alpha=lora_alpha,
                completed_at=ev.completed_at,
            )
        )
    items.sort(key=lambda x: x.bleu_score, reverse=True)
    return EvaluationComparisonResponse(evaluations=items)


@app.get("/evaluations/{eval_id}", response_model=BenchmarkEvalResult)
def get_evaluation(eval_id: str) -> BenchmarkEvalResult:
    eval_result = storage.get_benchmark_eval(eval_id)
    if not eval_result:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return eval_result
