# AIP-C01 Generative AI Prep

This repo now includes a light-weight fine-tuning harness to experiment with
`distilbert-base-uncased` on the Tolkien-flavored SaaS Q&A dataset under
`data/saas.csv`. The harness focuses on masked-language modeling so you can
practice:

- tweaking hyperparameters (batch size, LR, warmup, eval cadence, etc.)
- freezing embeddings or arbitrary encoder layers
- observing validation loss/perplexity changes when holding out data

## Quickstart

1. **Install deps with uv**

   ```bash
   uv pip install -r pyproject.toml
   ```

2. **Edit a config**

   Copy `configs/local_example.yaml` and change any knobs you want to explore.

3. **Train**

   ```bash
    uv run python -m aip_c01_prep.cli train configs/local_example.yaml
   ```

   Metrics print to stdout and checkpoints land inside `training.output_dir`.

4. **Optional TinyLlama run**

   ```bash
   uv run python -m aip_c01_prep.cli train configs/tinyllama_example.yaml
   ```

   The CLI detects the causal LLM template (or you can keep using the explicit
   `train-llm` command), formats each Q&A pair with your template, fine-tunes
   TinyLlama, and writes outputs to `training.output_dir`. Set the new `peft`
   block to `enabled: true` to switch the run into LoRA adapter mode so only a
   small set of parameters train on CPU/MPS hardware.

5. **Inspect the Plotly loss curves**

   Every training command drops an interactive Plotly HTML file under
   `training.output_dir/plots/*_loss.html`. Open it in a browser to compare train
   versus eval loss across global steps.

6. **Sanity-check the TinyLlama checkpoint**

   ```bash
   uv run python tests/tinyllama_eval.py "How should I secure multi-account S3 access?"
   ```

   The helper loads the saved LoRA adapters from `artifacts/tinyllama-saas` and
   prints the generated response for the supplied prompt.

## Extending

- Swap out `data.csv_path` to point at a different CSV to continue experimenting.
- Increase `model.freeze_encoder_layers` to study how many layers you can lock
  before validation loss degrades.
- Modify `training.max_steps` for quick dry runs without finishing an epoch.
- Duplicate `configs/tinyllama_example.yaml` when exploring other causal LLMs
  and keep the `{system_prompt}`, `{question}`, `{answer}` placeholders intact
  so formatting issues fail fast.
- Save multiple plot revisions by copying the generated HTML outside the
  `plots/` directory before starting another run if you want to compare curves.
