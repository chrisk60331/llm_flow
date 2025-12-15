"""AutoTune API routes."""
from __future__ import annotations

import uuid
from pathlib import Path
from threading import Thread

import pandas as pd
from fastapi import APIRouter, HTTPException

from ..models import (
    AutoTuneCandidate,
    AutoTuneJob,
    AutoTuneListResponse,
    AutoTuneRequest,
    AutoTuneStartResponse,
    AutoTuneStatus,
    AutoTuneStatusResponse,
    Benchmark,
    BenchmarkEvalResult,
    BenchmarkStatus,
    CausalLMDataConfig,
    CausalLMFullConfig,
    CausalLMModelConfig,
    CausalLMPeftConfig,
    CausalLMTrainingConfig,
    ConfigRecord,
    ExperimentResult,
    ExperimentStatus,
    ExperimentType,
)
from ..optimizer import optimize_config
from ..storage import (
    delete_autotune_job as storage_delete_autotune_job,
    get_autotune_job,
    get_benchmark,
    get_config,
    get_dataset,
    get_experiment,
    list_autotune_jobs,
    save_autotune_job,
    save_benchmark,
    save_benchmark_eval,
    save_config,
    save_experiment,
    get_benchmark_eval,
)
from .helpers import now
from .meta_routes import _get_predictor
from .benchmark_routes import _run_benchmark_eval_sync
from .experiment_routes import run_causal_lm_experiment_sync

router = APIRouter(prefix="/autotune", tags=["autotune"])


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


def _run_autotune_job(job_id: str, request: AutoTuneRequest) -> None:
    """Background worker that orchestrates the full autotune pipeline."""
    job = get_autotune_job(job_id)
    if not job:
        return
    
    dataset_info = get_dataset(request.dataset_id)
    if not dataset_info:
        job.status = AutoTuneStatus.FAILED
        job.error = "Dataset not found"
        job.completed_at = now()
        save_autotune_job(job)
        return
    
    csv_path = Path(dataset_info.path)
    
    if request.base_config_id:
        config_record = get_config(request.base_config_id)
        if not config_record:
            job.status = AutoTuneStatus.FAILED
            job.error = "Base config not found"
            job.completed_at = now()
            save_autotune_job(job)
            return
        base_config = config_record.config
    else:
        base_config = _get_default_base_config(request.question_field, request.answer_field)
    
    try:
        # Phase 1: Probing
        job.status = AutoTuneStatus.PROBING
        job.phase_message = "Running probes to predict best configs..."
        save_autotune_job(job)
        
        predictor = _get_predictor()
        if predictor.model is None:
            job.status = AutoTuneStatus.FAILED
            job.error = "Predictor not trained. Generate synthetic data and train first."
            job.completed_at = now()
            save_autotune_job(job)
            return
        
        candidates = optimize_config(
            base_config=base_config,
            csv_path=csv_path,
            predictor=predictor,
            probe_steps=request.probe_steps,
            max_candidates=request.top_k * 3,
        )
        
        top_candidates = candidates[:request.top_k]
        
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
        save_autotune_job(job)
        
        # Phase 2: Training
        job.status = AutoTuneStatus.TRAINING
        save_autotune_job(job)
        
        for i, candidate in enumerate(job.candidates):
            job.current_training_idx = i
            job.phase_message = f"Training model {i+1}/{len(job.candidates)} (LR={candidate.learning_rate:.0e}, LoRA r={candidate.lora_r})"
            save_autotune_job(job)
            
            config = _build_candidate_config(base_config, candidate)
            
            config_name = f"autotune_{job_id[:8]}_rank{candidate.rank}"
            config_record = ConfigRecord(
                id=str(uuid.uuid4()),
                name=config_name,
                experiment_type=ExperimentType.CAUSAL_LM,
                config=config,
                created_at=now(),
            )
            save_config(config_record)
            
            experiment_id = str(uuid.uuid4())
            exp = ExperimentResult(
                id=experiment_id,
                experiment_type=ExperimentType.CAUSAL_LM,
                status=ExperimentStatus.PENDING,
                dataset_id=request.dataset_id,
                dataset_filename=dataset_info.filename,
                config_id=config_record.id,
                started_at=now(),
            )
            save_experiment(exp)
            
            run_causal_lm_experiment_sync(experiment_id, request.dataset_id, config_record.id)
            
            candidate.experiment_id = experiment_id
            save_autotune_job(job)
        
        # Phase 3: Evaluation
        job.status = AutoTuneStatus.EVALUATING
        save_autotune_job(job)
        
        benchmark = get_benchmark(job.benchmark_id)
        
        for i, candidate in enumerate(job.candidates):
            if not candidate.experiment_id:
                continue
            
            exp = get_experiment(candidate.experiment_id)
            if not exp or exp.status != ExperimentStatus.COMPLETED:
                continue
            
            job.current_eval_idx = i
            job.phase_message = f"Evaluating model {i+1}/{len(job.candidates)}"
            save_autotune_job(job)
            
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
                started_at=now(),
            )
            save_benchmark_eval(eval_result)
            
            _run_benchmark_eval_sync(eval_id, benchmark, exp)
            
            eval_result = get_benchmark_eval(eval_id)
            candidate.eval_id = eval_id
            candidate.actual_bleu = eval_result.bleu_score if eval_result.status == BenchmarkStatus.COMPLETED else None
            save_autotune_job(job)
        
        # Re-rank by actual BLEU
        job.candidates.sort(key=lambda c: c.actual_bleu or 0, reverse=True)
        for i, c in enumerate(job.candidates):
            c.rank = i + 1
        
        job.status = AutoTuneStatus.COMPLETED
        job.phase_message = f"Complete! Best BLEU: {job.candidates[0].actual_bleu:.2f}" if job.candidates and job.candidates[0].actual_bleu else "Complete!"
        job.completed_at = now()
        save_autotune_job(job)
        
    except Exception as e:
        job.status = AutoTuneStatus.FAILED
        job.error = str(e)
        job.completed_at = now()
        save_autotune_job(job)


@router.post("/run", response_model=AutoTuneStartResponse)
def start_autotune(request: AutoTuneRequest) -> AutoTuneStartResponse:
    """Start the autotune fine-tuning pipeline."""
    dataset_info = get_dataset(request.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    benchmark_id = request.benchmark_id
    if not benchmark_id:
        if request.benchmark_question and request.benchmark_answer:
            benchmark_id = str(uuid.uuid4())
            benchmark = Benchmark(
                id=benchmark_id,
                name=f"autotune_{benchmark_id[:8]}",
                question=request.benchmark_question,
                gold_answer=request.benchmark_answer,
                created_at=now(),
            )
            save_benchmark(benchmark)
        elif request.benchmark_row_idx is not None:
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
                created_at=now(),
            )
            save_benchmark(benchmark)
        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide benchmark_id, benchmark_question+answer, or benchmark_row_idx"
            )
    else:
        if not get_benchmark(benchmark_id):
            raise HTTPException(status_code=404, detail="Benchmark not found")
    
    predictor = _get_predictor()
    if predictor.model is None:
        raise HTTPException(
            status_code=400,
            detail="Predictor not trained. Generate synthetic data and train first via /meta/generate-synthetic and /meta/train-predictor",
        )
    
    job_id = str(uuid.uuid4())
    job = AutoTuneJob(
        id=job_id,
        dataset_id=request.dataset_id,
        benchmark_id=benchmark_id,
        base_config_id=request.base_config_id,
        status=AutoTuneStatus.PENDING,
        phase_message="Starting AutoTune...",
        top_k=request.top_k,
        started_at=now(),
    )
    save_autotune_job(job)
    
    thread = Thread(target=_run_autotune_job, args=(job_id, request), daemon=True)
    thread.start()
    
    return AutoTuneStartResponse(
        job_id=job_id,
        status=AutoTuneStatus.PENDING,
        message=f"AutoTune started. Training {request.top_k} configs. Poll /autotune/{job_id} for status.",
    )


@router.get("/{job_id}", response_model=AutoTuneStatusResponse)
def get_autotune_status(job_id: str) -> AutoTuneStatusResponse:
    """Get status of an autotune job."""
    job = get_autotune_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="AutoTune job not found")
    
    return AutoTuneStatusResponse(
        job=job,
        message=job.phase_message or job.status.value,
    )


@router.get("", response_model=AutoTuneListResponse)
def list_all_autotune_jobs() -> AutoTuneListResponse:
    """List all autotune jobs."""
    return AutoTuneListResponse(jobs=list_autotune_jobs())


@router.delete("/{job_id}")
def delete_autotune_job(job_id: str) -> dict[str, str]:
    """Delete an autotune job."""
    if not storage_delete_autotune_job(job_id):
        raise HTTPException(status_code=404, detail="AutoTune job not found")
    return {"status": "deleted", "job_id": job_id}

