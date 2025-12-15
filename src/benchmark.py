"""Benchmark evaluation with BLEU and ROUGE-L scoring."""
from __future__ import annotations

from pathlib import Path

import evaluate
import torch
from peft import AutoPeftModelForCausalLM
from sacrebleu.metrics import BLEU
from transformers import AutoTokenizer


def _preferred_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def load_model_and_tokenizer(model_path: Path) -> tuple:
    """Load a PEFT model and tokenizer from checkpoint."""
    model = AutoPeftModelForCausalLM.from_pretrained(model_path)
    device = _preferred_device()
    model.to(device)
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return model, tokenizer


def format_prompt(system_prompt: str, user_prompt: str) -> str:
    """Format a prompt using the TinyLlama chat template."""
    return (
        "<|system|>\n"
        f"{system_prompt.strip()}\n"
        "</s>\n"
        "<|user|>\n"
        f"{user_prompt.strip()}\n"
        "</s>\n"
        "<|assistant|>\n"
    )


def generate_response(
    model,
    tokenizer,
    prompt: str,
    system_prompt: str = "You are an AI assistant.",
    max_new_tokens: int = 128,
    temperature: float = 0.7,
    top_p: float = 0.9,
) -> str:
    """Generate a response from the model."""
    model.eval()
    device = next(model.parameters()).device
    formatted_prompt = format_prompt(system_prompt, prompt)
    encoded = tokenizer(formatted_prompt, return_tensors="pt").to(device)
    generation_kwargs = {
        "max_new_tokens": max_new_tokens,
        "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
        "eos_token_id": tokenizer.eos_token_id,
        "temperature": temperature,
        "top_p": top_p,
        "do_sample": True,
        "repetition_penalty": 1.1,
    }
    with torch.no_grad():
        output = model.generate(**encoded, **generation_kwargs)
    gen_tokens = output[:, encoded["input_ids"].shape[-1] :]
    return tokenizer.decode(gen_tokens[0], skip_special_tokens=True).strip()


def compute_bleu_score(hypothesis: str, reference: str) -> float:
    """Compute BLEU score for a single hypothesis against a reference."""
    bleu = BLEU(effective_order=True)
    result = bleu.sentence_score(hypothesis, [reference])
    return result.score


def compute_rouge_l_score(hypothesis: str, reference: str) -> float:
    """Compute ROUGE-L F1 score for a single hypothesis against a reference.
    
    ROUGE-L uses longest common subsequence, which is better for semantically
    similar but lexically different answers compared to n-gram based BLEU.
    """
    rouge = evaluate.load("rouge")
    result = rouge.compute(predictions=[hypothesis], references=[reference])
    return result["rougeL"] * 100  # Scale to 0-100 like BLEU
