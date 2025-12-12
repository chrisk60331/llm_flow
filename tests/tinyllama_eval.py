from __future__ import annotations

import argparse
from pathlib import Path

import torch  # type: ignore[import]
import yaml
from peft import AutoPeftModelForCausalLM  # type: ignore[import]
from transformers import AutoTokenizer  # type: ignore[import]


DEFAULT_MODEL_DIR = Path("artifacts/tinyllama-violence")
DEFAULT_CONFIG_PATH = Path("configs/tinyllama_violence.yaml")
DEFAULT_PROMPT = "What to with difficult subordinates?"


def _preferred_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _load_model(model_dir: Path):
    if not model_dir.exists():
        msg = f"Model directory {model_dir} was not found. Run training first."
        raise FileNotFoundError(msg)
    model = AutoPeftModelForCausalLM.from_pretrained(
        model_dir,
    )
    device = _preferred_device()
    model.to(device)
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return model, tokenizer


def _load_system_prompt(config_path: Path) -> str:
    if not config_path.exists():
        msg = f"Config file {config_path} was not found."
        raise FileNotFoundError(msg)
    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return (
        payload.get("data", {}).get(
            "system_prompt", "You are Sauron, the dark lord of Middle-earth."
        )
    )


def _format_prompt(system_prompt: str, user_prompt: str) -> str:
    return (
        "<|system|>\n"
        f"{system_prompt.strip()}\n"
        "</s>\n"
        "<|user|>\n"
        f"{user_prompt.strip()}\n"
        "</s>\n"
        "<|assistant|>\n"
    )


def generate(
    prompt: str,
    model_dir: Path,
    system_prompt: str,
    max_new_tokens: int = 128,
    temperature: float = 0.9,
    top_p: float = 0.8,
) -> str:
    model, tokenizer = _load_model(model_dir)
    model.eval()
    device = next(model.parameters()).device
    formatted_prompt = _format_prompt(system_prompt, prompt)
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quick sanity check for the TinyLlama LoRA checkpoint."
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=DEFAULT_PROMPT,
        help="Prompt to feed the fine-tuned model.",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=DEFAULT_MODEL_DIR,
        help="Path to the saved LoRA checkpoint.",
    )
    parser.add_argument(
        "--config-path",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Config file whose system prompt/template should be mirrored.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=128,
        help="Number of tokens to sample beyond the prompt.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.8,
        help="Softmax temperature for sampling (higher = more random).",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=0.95,
        help="Nucleus sampling cumulative probability.",
    )
    args = parser.parse_args()
    system_prompt = _load_system_prompt(args.config_path)
    full_response = generate(
        prompt=args.prompt,
        model_dir=args.model_dir,
        system_prompt=system_prompt,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_p=args.top_p,
    )
    print("\nPrompt:\n-------\n" + args.prompt.strip())
    print("\nResponse:\n---------\n" + full_response.strip())


if __name__ == "__main__":
    main()

