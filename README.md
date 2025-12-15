# Auto Finetuner

This repo includes a light-weight fine-tuning webui to experiment with
language models on on your data. The harness focuses on causal language modeling so you can
practice:

- tweaking hyperparameters (batch size, LR, warmup, early stopping, etc.)
- freezing embeddings or arbitrary encoder layers
- observing validation loss/perplexity changes 

## Quickstart

**Run**
### Front end

```bash
uv run python -m src.flask_app --port 8001
```
### Back end

```bash
uv run uvicorn src.api:app --reload --port 8000
```
