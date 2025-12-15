"""Config optimizer using meta-learning predictions."""
from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from .meta_features import MetaFeatureVector
from .predictor import PerformancePredictor
from .probe import run_probe

logger = logging.getLogger(__name__)


class SearchSpace(BaseModel):
    """Defines the hyperparameter search space."""
    
    # Reduced defaults for faster probing on CPU/MPS
    learning_rates: list[float] = [2e-5, 5e-5, 1e-4]
    lora_r_values: list[int] = [8, 16]
    batch_sizes: list[int] = [1, 2]
    num_epochs: list[int] = [1, 2]


@dataclass
class ConfigCandidate:
    """A config candidate with its predicted performance."""
    
    learning_rate: float
    lora_r: int
    batch_size: int
    num_epochs: int
    predicted_bleu: float
    features: MetaFeatureVector
    rank: int = 0


def optimize_config(
    base_config,
    csv_path: Path,
    predictor: PerformancePredictor,
    search_space: SearchSpace | None = None,
    probe_steps: int = 10,
    max_candidates: int = 20,
) -> list[ConfigCandidate]:
    """Find optimal config using grid search with predictions.
    
    Args:
        base_config: Base CausalLMFullConfig to vary
        csv_path: Path to dataset CSV
        predictor: Trained performance predictor
        search_space: Hyperparameter ranges to explore
        probe_steps: Steps per probe run
        max_candidates: Maximum configs to evaluate
        
    Returns:
        List of ConfigCandidate sorted by predicted BLEU (best first)
    """
    space = search_space or SearchSpace()
    
    # Generate all combinations
    combinations = list(itertools.product(
        space.learning_rates,
        space.lora_r_values,
        space.batch_sizes,
        space.num_epochs,
    ))
    
    # Limit to max_candidates (sample evenly if too many)
    if len(combinations) > max_candidates:
        step = len(combinations) // max_candidates
        combinations = combinations[::step][:max_candidates]
    
    candidates = []
    total = len(combinations)
    
    for i, (lr, lora_r, batch_size, epochs) in enumerate(combinations):
        logger.info(f"Probe {i+1}/{total}: LR={lr:.0e}, LoRA r={lora_r}, batch={batch_size}, epochs={epochs}")
        
        # Create modified config
        config = _modify_config(base_config, lr, lora_r, batch_size, epochs)
        
        # Run probe
        experiment_id = f"optimize_{i}"
        features = run_probe(
            config=config,
            csv_path=csv_path,
            probe_steps=probe_steps,
            experiment_id=experiment_id,
        )
        
        # Predict performance
        predicted_bleu = predictor.predict(features)
        logger.info(f"  -> Predicted BLEU: {predicted_bleu:.4f}")
        
        candidates.append(ConfigCandidate(
            learning_rate=lr,
            lora_r=lora_r,
            batch_size=batch_size,
            num_epochs=epochs,
            predicted_bleu=predicted_bleu,
            features=features,
        ))
    
    # Sort by predicted BLEU (descending)
    candidates.sort(key=lambda c: c.predicted_bleu, reverse=True)
    
    # Assign ranks
    for i, c in enumerate(candidates):
        c.rank = i + 1
    
    return candidates


def quick_sensitivity_analysis(
    features: MetaFeatureVector,
    predictor: PerformancePredictor,
) -> dict[str, dict]:
    """Analyze sensitivity of prediction to config changes.
    
    Uses the predictor to estimate impact of changing each hyperparameter.
    
    Args:
        features: Current meta-features
        predictor: Trained predictor
        
    Returns:
        Dict mapping param names to sensitivity info
    """
    from .explainer import PredictionExplainer
    
    explainer = PredictionExplainer(predictor)
    shap_values = explainer.explain(features)
    base_prediction = predictor.predict(features)
    
    # Focus on tunable hyperparameters
    tunable = [
        "learning_rate", "num_epochs", "batch_size", 
        "gradient_accumulation_steps", "warmup_ratio",
        "lora_r", "lora_alpha", "lora_enabled",
    ]
    
    results = {}
    for param in tunable:
        if param in shap_values:
            shap_val = shap_values[param]
            current_val = features.to_feature_dict().get(param, 0)
            
            # Interpret direction
            if shap_val > 0:
                recommendation = "Current value is helping. Consider keeping or increasing."
            else:
                recommendation = "Current value is hurting. Consider decreasing or changing."
            
            results[param] = {
                "current_value": current_val,
                "shap_value": shap_val,
                "impact": "positive" if shap_val > 0 else "negative",
                "magnitude": abs(shap_val),
                "recommendation": recommendation,
            }
    
    # Sort by magnitude
    results = dict(sorted(
        results.items(), 
        key=lambda x: x[1]["magnitude"], 
        reverse=True
    ))
    
    return results


def _modify_config(base_config, lr: float, lora_r: int, batch_size: int, epochs: int):
    """Create a modified copy of the config with new hyperparameters."""
    # Deep copy by re-creating from dict
    config_dict = base_config.model_dump()
    
    config_dict["training"]["learning_rate"] = lr
    config_dict["training"]["per_device_train_batch_size"] = batch_size
    config_dict["training"]["num_train_epochs"] = epochs
    
    if config_dict.get("peft", {}).get("enabled", False):
        config_dict["peft"]["r"] = lora_r
        config_dict["peft"]["lora_alpha"] = lora_r * 2
    
    # Re-create config object
    from .models import CausalLMFullConfig
    return CausalLMFullConfig(**config_dict)

