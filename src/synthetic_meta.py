"""Synthetic meta-feature generation for predictor bootstrapping."""
from __future__ import annotations

import random
import uuid
from math import log10

from .meta_features import MetaFeatureVector


def generate_synthetic_features(n: int = 100, seed: int = 42) -> list[MetaFeatureVector]:
    """Generate synthetic meta-features with plausible BLEU relationships.
    
    Encodes domain knowledge about fine-tuning success factors:
    - More training samples → better performance
    - Steeper loss slope → model is learning
    - Lower loss variance → stable training
    - Moderate learning rates → sweet spot
    - High truncation → losing context
    
    Args:
        n: Number of synthetic samples to generate
        seed: Random seed for reproducibility
        
    Returns:
        List of synthetic MetaFeatureVector with BLEU scores
    """
    random.seed(seed)
    results = []
    
    # Model names to sample from
    model_names = [
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "microsoft/phi-2",
        "Qwen/Qwen2-0.5B",
        "google/gemma-2b",
    ]
    
    for i in range(n):
        # Sample input features with realistic ranges
        n_samples = random.choice([20, 50, 100, 200, 500, 1000, 2000])
        learning_rate = random.choice([1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4, 1e-3])
        batch_size = random.choice([1, 2, 4, 8])
        gradient_accumulation = random.choice([1, 2, 4, 8, 16])
        num_epochs = random.choice([1, 2, 3, 5])
        warmup_ratio = random.uniform(0.0, 0.1)
        weight_decay = random.choice([0.0, 0.01, 0.1])
        max_length = random.choice([256, 512, 1024, 2048])
        lora_enabled = random.choice([True, False])
        lora_r = random.choice([4, 8, 16, 32]) if lora_enabled else None
        lora_alpha = lora_r * 2 if lora_r else None
        
        # Dataset features
        avg_text_length = random.uniform(100, 2000)
        vocab_size = random.randint(500, 10000)
        type_token_ratio = random.uniform(0.1, 0.8)
        oov_rate = random.uniform(0.0, 0.3)
        avg_sequence_length = random.uniform(50, max_length * 0.8)
        max_sequence_length = int(avg_sequence_length * random.uniform(1.2, 3.0))
        truncation_rate = random.uniform(0.0, 0.4)
        
        # Probe features - these correlate with final performance
        probe_steps = random.choice([5, 10, 20, 50])
        probe_initial_loss = random.uniform(2.5, 5.0)
        
        # Loss slope depends on learning rate and data quality
        base_slope = -random.uniform(0.01, 0.3)
        # Higher LR = faster initial drop
        lr_factor = log10(learning_rate) + 5  # normalize around 1e-5
        base_slope *= (1 + lr_factor * 0.2)
        probe_loss_slope = base_slope
        
        probe_final_loss = probe_initial_loss + probe_loss_slope * probe_steps
        probe_final_loss = max(0.5, probe_final_loss)  # floor
        
        probe_loss_variance = random.uniform(0.001, 0.1)
        probe_grad_norm_mean = random.uniform(0.1, 10.0)
        probe_grad_norm_std = probe_grad_norm_mean * random.uniform(0.1, 0.5)
        
        # Compute synthetic BLEU based on heuristics
        bleu = 40.0  # baseline
        
        # More data helps (logarithmic scaling)
        data_factor = min(1.0, (n_samples / 500) ** 0.5)
        bleu += 15 * data_factor
        
        # Steeper loss slope = better learning (slope is negative)
        loss_drop = probe_initial_loss - probe_final_loss
        bleu += 8 * loss_drop
        
        # Lower variance = more stable training
        bleu -= 40 * probe_loss_variance
        
        # Truncation hurts
        bleu -= 25 * truncation_rate
        
        # OOV hurts
        bleu -= 20 * oov_rate
        
        # Learning rate sweet spot around 2e-5 to 1e-4
        lr_log = abs(log10(learning_rate) + 4.3)  # optimal around ~5e-5
        bleu -= 8 * lr_log
        
        # Too high LR with small dataset = disaster
        if learning_rate > 1e-4 and n_samples < 100:
            bleu -= 15
        
        # LoRA generally helps with small datasets
        if lora_enabled and n_samples < 500:
            bleu += 5
        
        # More epochs can help (diminishing returns)
        bleu += 3 * min(num_epochs, 3)
        
        # Add realistic noise
        bleu += random.gauss(0, 8)
        
        # Clamp to valid range
        bleu = max(0.0, min(100.0, bleu))
        
        results.append(MetaFeatureVector(
            experiment_id=f"synthetic_{uuid.uuid4().hex[:8]}",
            is_synthetic=True,
            # Dataset features
            n_samples=n_samples,
            avg_text_length=avg_text_length,
            vocab_size=vocab_size,
            type_token_ratio=type_token_ratio,
            oov_rate=oov_rate,
            avg_sequence_length=avg_sequence_length,
            max_sequence_length=max_sequence_length,
            truncation_rate=truncation_rate,
            # Config features
            learning_rate=learning_rate,
            num_epochs=num_epochs,
            batch_size=batch_size,
            gradient_accumulation_steps=gradient_accumulation,
            warmup_ratio=warmup_ratio,
            weight_decay=weight_decay,
            max_length=max_length,
            lora_enabled=lora_enabled,
            lora_r=lora_r,
            lora_alpha=lora_alpha,
            model_name=random.choice(model_names),
            # Probe features
            probe_steps=probe_steps,
            probe_initial_loss=probe_initial_loss,
            probe_final_loss=probe_final_loss,
            probe_loss_slope=probe_loss_slope,
            probe_loss_variance=probe_loss_variance,
            probe_grad_norm_mean=probe_grad_norm_mean,
            probe_grad_norm_std=probe_grad_norm_std,
            # Target
            final_bleu_score=bleu,
            final_eval_loss=probe_final_loss * random.uniform(0.8, 1.2),
        ))
    
    return results

