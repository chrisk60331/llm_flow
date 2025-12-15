"""Meta-learning API routes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..meta_features import MetaFeatureVector
from ..models import BenchmarkStatus, CausalLMFullConfig, ExperimentStatus
from ..optimizer import SearchSpace, optimize_config, quick_sensitivity_analysis
from ..predictor import PerformancePredictor
from ..explainer import PredictionExplainer
from ..probe import run_probe
from ..storage import (
    delete_meta_features,
    get_experiment,
    get_dataset,
    get_meta_features,
    get_optimization_job,
    list_benchmark_evals,
    list_meta_features,
    save_meta_features,
    save_optimization_job,
    OptimizationJob,
    OptimizationStatus,
)
from ..synthetic_meta import generate_synthetic_features
from .helpers import now

router = APIRouter(prefix="/meta", tags=["meta"])

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
            pass
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


@router.post("/generate-synthetic", response_model=MetaSyntheticResponse)
def generate_synthetic_data(request: MetaSyntheticRequest) -> MetaSyntheticResponse:
    """Generate synthetic meta-features for predictor bootstrapping."""
    synthetic = generate_synthetic_features(n=request.n_samples, seed=request.seed)
    
    for f in synthetic:
        save_meta_features(f)
    
    return MetaSyntheticResponse(
        count=len(synthetic),
        message=f"Generated {len(synthetic)} synthetic meta-feature vectors",
    )


@router.delete("/synthetic")
def clear_synthetic_data() -> dict:
    """Remove all synthetic meta-features from storage."""
    all_features = list_meta_features()
    removed = 0
    for f in all_features:
        if f.is_synthetic:
            delete_meta_features(f.experiment_id)
            removed += 1
    return {"removed": removed, "message": f"Removed {removed} synthetic features"}


@router.post("/extract/{experiment_id}", response_model=MetaFeatureVector)
def extract_meta_features(experiment_id: str) -> MetaFeatureVector:
    """Extract and store meta-features for a completed experiment."""
    exp = get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if exp.status != ExperimentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Experiment not completed")

    dataset_info = get_dataset(exp.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")

    evals = list_benchmark_evals()
    bleu_scores = [e.bleu_score for e in evals if e.experiment_id == experiment_id and e.status == BenchmarkStatus.COMPLETED]
    final_bleu = sum(bleu_scores) / len(bleu_scores) if bleu_scores else None

    features = run_probe(
        config=exp.config,
        csv_path=Path(dataset_info.path),
        probe_steps=10,
        experiment_id=experiment_id,
    )

    features.final_eval_loss = exp.metrics.get("eval_loss")
    features.final_bleu_score = final_bleu

    save_meta_features(features)
    return features


@router.post("/probe", response_model=MetaProbeResponse)
def run_meta_probe(request: MetaProbeRequest) -> MetaProbeResponse:
    """Run a short probe to extract meta-features without full training."""
    dataset_info = get_dataset(request.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")

    probe_id = f"probe_{uuid.uuid4()}"
    features = run_probe(
        config=request.config,
        csv_path=Path(dataset_info.path),
        probe_steps=request.probe_steps,
        experiment_id=probe_id,
    )

    save_meta_features(features)

    return MetaProbeResponse(
        features=features,
        message=f"Probe completed with {request.probe_steps} steps",
    )


@router.get("/features", response_model=MetaFeaturesListResponse)
def list_all_meta_features() -> MetaFeaturesListResponse:
    """List all stored meta-feature vectors."""
    return MetaFeaturesListResponse(features=list_meta_features())


@router.get("/features/{experiment_id}", response_model=MetaFeatureVector)
def get_meta_features_by_id(experiment_id: str) -> MetaFeatureVector:
    """Get meta-features for a specific experiment."""
    features = get_meta_features(experiment_id)
    if not features:
        raise HTTPException(status_code=404, detail="Meta-features not found")
    return features


@router.post("/train-predictor", response_model=MetaTrainResponse)
def train_predictor(request: MetaTrainRequest) -> MetaTrainResponse:
    """Train the GBM predictor on stored meta-features."""
    global _predictor

    features = list_meta_features()
    
    if not request.include_synthetic:
        features = [f for f in features if not f.is_synthetic]
    
    if len(features) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 5 experiments with results, got {len(features)}",
        )

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


@router.post("/predict", response_model=MetaPredictResponse)
def predict_performance(request: MetaPredictRequest) -> MetaPredictResponse:
    """Predict performance for a new config using the trained predictor."""
    predictor = _get_predictor()
    if predictor.model is None:
        raise HTTPException(
            status_code=400,
            detail="Predictor not trained. Call /meta/train-predictor first.",
        )

    dataset_info = get_dataset(request.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")

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


@router.get("/explain/{experiment_id}", response_model=MetaExplainResponse)
def explain_prediction(experiment_id: str) -> MetaExplainResponse:
    """Get SHAP explanation for a prediction."""
    predictor = _get_predictor()
    if predictor.model is None:
        raise HTTPException(
            status_code=400,
            detail="Predictor not trained. Call /meta/train-predictor first.",
        )

    features = get_meta_features(experiment_id)
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


@router.get("/feature-importance")
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
    job = get_optimization_job(job_id)
    if not job:
        return
    
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


@router.post("/optimize", response_model=OptimizeStartResponse)
def start_optimization(request: OptimizeRequest) -> OptimizeStartResponse:
    """Start config optimization as a background job."""
    predictor = _get_predictor()
    if predictor.model is None:
        raise HTTPException(
            status_code=400,
            detail="Predictor not trained. Call /meta/train-predictor first.",
        )
    
    dataset_info = get_dataset(request.dataset_id)
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    job_id = str(uuid.uuid4())
    job = OptimizationJob(
        id=job_id,
        dataset_id=request.dataset_id,
        status=OptimizationStatus.PENDING,
        started_at=datetime.now(timezone.utc),
    )
    save_optimization_job(job)
    
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


@router.get("/optimize/{job_id}", response_model=OptimizeStatusResponse)
def get_optimization_status(job_id: str) -> OptimizeStatusResponse:
    """Get status of an optimization job."""
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


@router.post("/sensitivity", response_model=dict)
def analyze_sensitivity(request: SensitivityRequest) -> dict:
    """Analyze how changing hyperparameters would affect predictions."""
    predictor = _get_predictor()
    if predictor.model is None:
        raise HTTPException(
            status_code=400,
            detail="Predictor not trained. Call /meta/train-predictor first.",
        )
    
    features = get_meta_features(request.experiment_id)
    if not features:
        raise HTTPException(status_code=404, detail="Meta-features not found")
    
    sensitivity = quick_sensitivity_analysis(features, predictor)
    prediction = predictor.predict(features)
    
    return {
        "experiment_id": request.experiment_id,
        "current_prediction": prediction,
        "sensitivity": sensitivity,
    }

