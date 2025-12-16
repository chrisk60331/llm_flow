"""Flask application that wraps FastAPI routes with a UI."""
from __future__ import annotations

import os
import json
from urllib.parse import quote
from pathlib import Path

import requests
from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for

# Configure Flask to find templates in src/templates
template_dir = Path(__file__).parent / "templates"
app = Flask(__name__, template_folder=str(template_dir))

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

IMG_DIR = Path(__file__).resolve().parent.parent / "img"


@app.route("/favicon.ico")
def favicon():
    resp = send_from_directory(IMG_DIR, "favicon.png", mimetype="image/png", max_age=0)
    resp.headers["Cache-Control"] = "no-store"
    return resp


# ============================================================================
# Home
# ============================================================================

@app.route("/")
def index():
    stats = {
        "datasets": 0,
        "configs": 0,
        "models": 0,
        "benchmarks": 0,
        "evals": 0,
        "meta_features": 0,
    }
    datasets = []
    configs = []
    benchmarks = []
    
    try:
        datasets_resp = requests.get(f"{API_BASE_URL}/datasets", timeout=5)
        datasets = datasets_resp.json().get("datasets", [])
        stats["datasets"] = len(datasets)
    except Exception:
        pass
    try:
        configs_resp = requests.get(f"{API_BASE_URL}/configs", timeout=5)
        configs = configs_resp.json().get("configs", [])
        stats["configs"] = len(configs)
    except Exception:
        pass
    try:
        experiments_resp = requests.get(f"{API_BASE_URL}/experiments", timeout=5)
        experiments = experiments_resp.json().get("experiments", [])
        stats["models"] = len([e for e in experiments if e.get("status") == "completed"])
    except Exception:
        pass
    try:
        benchmarks_resp = requests.get(f"{API_BASE_URL}/benchmarks", timeout=5)
        benchmarks = benchmarks_resp.json().get("benchmarks", [])
        stats["benchmarks"] = len(benchmarks)
    except Exception:
        pass
    try:
        evals_resp = requests.get(f"{API_BASE_URL}/evaluations", timeout=5)
        stats["evals"] = len(evals_resp.json().get("evaluations", []))
    except Exception:
        pass
    try:
        meta_resp = requests.get(f"{API_BASE_URL}/meta/features", timeout=5)
        stats["meta_features"] = len(meta_resp.json().get("features", []))
    except Exception:
        pass
    
    return render_template("home.html", stats=stats, datasets=datasets, configs=configs, benchmarks=benchmarks)


# ============================================================================
# Datasets
# ============================================================================

@app.route("/datasets")
def datasets_page():
    resp = requests.get(f"{API_BASE_URL}/datasets", timeout=10)
    data = resp.json()
    return render_template("datasets.html", datasets=data.get("datasets", []))


@app.route("/datasets/upload", methods=["POST"])
def upload_dataset():
    file = request.files.get("file")
    if not file:
        return redirect(url_for("datasets_page"))
    files = {"file": (file.filename, file.stream, file.content_type)}
    requests.post(f"{API_BASE_URL}/datasets/upload", files=files, timeout=60)
    return redirect(url_for("datasets_page"))


@app.route("/datasets/<dataset_id>/delete", methods=["POST"])
def delete_dataset(dataset_id: str):
    requests.delete(f"{API_BASE_URL}/datasets/{dataset_id}", timeout=10)
    return redirect(url_for("datasets_page"))


# ============================================================================
# Plugins
# ============================================================================

@app.route("/plugins")
def plugins_page():
    resp = requests.get(f"{API_BASE_URL}/plugins", timeout=10)
    data = resp.json() if resp.status_code == 200 else {}
    return render_template("plugins.html", plugins=data.get("plugins", []))


@app.route("/plugins/upload", methods=["POST"])
def upload_plugin():
    kind = request.form.get("kind")
    file = request.files.get("file")
    if not kind or not file:
        return redirect(url_for("plugins_page"))

    files = {"file": (file.filename, file.stream, file.content_type)}
    requests.post(f"{API_BASE_URL}/plugins/upload", params={"kind": kind}, files=files, timeout=60)
    return redirect(url_for("plugins_page"))


@app.route("/plugins/<plugin_id>/delete", methods=["POST"])
def delete_plugin(plugin_id: str):
    requests.delete(f"{API_BASE_URL}/plugins/{plugin_id}", timeout=10)
    return redirect(url_for("plugins_page"))


# ============================================================================
# Configs
# ============================================================================

@app.route("/configs")
def configs_page():
    resp = requests.get(f"{API_BASE_URL}/configs", timeout=10)
    data = resp.json()
    return render_template("configs.html", configs=data.get("configs", []))


@app.route("/configs/upload", methods=["POST"])
def upload_config():
    file = request.files.get("file")
    if not file:
        return redirect(url_for("configs_page"))
    
    files = {"file": (file.filename, file.stream, file.content_type)}
    resp = requests.post(f"{API_BASE_URL}/configs/upload", files=files, timeout=30)
    
    if resp.status_code == 200:
        config_data = resp.json()
        return redirect(url_for("config_detail", config_id=config_data["id"]))
    return redirect(url_for("configs_page"))


@app.route("/configs/<config_id>")
def config_detail(config_id: str):
    resp = requests.get(f"{API_BASE_URL}/configs/{config_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("configs_page"))
    config = resp.json()
    return render_template("config_detail.html", config=config)


@app.route("/configs/<config_id>/delete", methods=["POST"])
def delete_config(config_id: str):
    requests.delete(f"{API_BASE_URL}/configs/{config_id}", timeout=10)
    return redirect(url_for("configs_page"))


@app.route("/configs/<config_id>/edit", methods=["GET", "POST"])
def edit_config(config_id: str):
    if request.method == "GET":
        resp = requests.get(f"{API_BASE_URL}/configs/{config_id}", timeout=10)
        if resp.status_code != 200:
            return redirect(url_for("configs_page"))
        config = resp.json()
        return render_template("config_edit.html", config=config)
    
    # POST - create new config from form
    form = request.form.to_dict()
    
    resp = requests.get(f"{API_BASE_URL}/configs/{config_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("configs_page"))
    original = resp.json()
    
    new_name = form.get("new_name", "").strip() or None
    
    if original["experiment_type"] == "causal_lm":
        target_modules = [m.strip() for m in form.get("peft_target_modules", "").split(",") if m.strip()]
        config_data = {
            "data": {
                "question_field": form.get("question_field", "question"),
                "answer_field": form.get("answer_field", "answer"),
                "system_prompt": form.get("system_prompt", ""),
                "template": form.get("template", ""),
                "validation_split": float(form.get("validation_split", 0.2)),
                "seed": int(form.get("seed", 42)),
                "max_length": int(form.get("max_length", 512)),
            },
            "model": {
                "pretrained_model_name": form.get("pretrained_model_name", ""),
                "trust_remote_code": False,
                "pad_token_override": form.get("pad_token_override") or None,
            },
            "peft": {
                "enabled": "peft_enabled" in form,
                "r": int(form.get("peft_r", 8)),
                "lora_alpha": int(form.get("peft_lora_alpha", 16)),
                "lora_dropout": float(form.get("peft_lora_dropout", 0.05)),
                "bias": form.get("peft_bias", "none"),
                "target_modules": target_modules or ["q_proj", "k_proj", "v_proj", "o_proj"],
            },
            "training": {
                "num_train_epochs": float(form.get("num_train_epochs", 3)),
                "per_device_train_batch_size": int(form.get("per_device_train_batch_size", 1)),
                "per_device_eval_batch_size": int(form.get("per_device_eval_batch_size", 1)),
                "learning_rate": float(form.get("learning_rate", 2e-5)),
                "weight_decay": float(form.get("weight_decay", 0.0)),
                "warmup_ratio": float(form.get("warmup_ratio", 0.03)),
                "gradient_accumulation_steps": int(form.get("gradient_accumulation_steps", 8)),
                "lr_scheduler_type": form.get("lr_scheduler_type", "cosine"),
                "logging_steps": 10,
                "eval_steps": 50,
                "save_steps": 200,
                "save_total_limit": 2,
                "max_steps": int(form.get("max_steps", -1)),
                "gradient_checkpointing": "gradient_checkpointing" in form,
                "fp16": "fp16" in form,
                "bf16": "bf16" in form,
                "early_stopping_patience": int(form.get("early_stopping_patience")) if form.get("early_stopping_patience") else None,
                "early_stopping_metric": form.get("early_stopping_metric", "eval_loss"),
                "early_stopping_greater_is_better": "early_stopping_greater_is_better" in form,
            },
        }
    else:
        text_fields = [f.strip() for f in form.get("text_fields", "").split(",") if f.strip()]
        config_data = {
            "data": {
                "text_fields": text_fields,
                "separator": form.get("separator", "\n\n").replace("\\n", "\n"),
                "validation_split": float(form.get("validation_split", 0.2)),
                "seed": int(form.get("seed", 42)),
                "max_length": int(form.get("max_length", 256)),
            },
            "model": {
                "pretrained_model_name": form.get("pretrained_model_name", "distilbert-base-uncased"),
                "freeze_embedding": False,
                "freeze_encoder_layers": int(form.get("freeze_encoder_layers", 0)),
            },
            "training": {
                "num_train_epochs": float(form.get("num_train_epochs", 3)),
                "per_device_train_batch_size": int(form.get("per_device_train_batch_size", 8)),
                "per_device_eval_batch_size": int(form.get("per_device_eval_batch_size", 8)),
                "learning_rate": float(form.get("learning_rate", 5e-5)),
                "weight_decay": float(form.get("weight_decay", 0.01)),
                "warmup_ratio": 0.0,
                "logging_steps": 10,
                "eval_steps": 50,
                "save_steps": 200,
                "save_total_limit": 2,
                "gradient_accumulation_steps": 1,
                "max_steps": -1,
                "early_stopping_patience": int(form.get("early_stopping_patience")) if form.get("early_stopping_patience") else None,
                "early_stopping_metric": form.get("early_stopping_metric", "eval_loss"),
                "early_stopping_greater_is_better": "early_stopping_greater_is_better" in form,
            },
        }
    
    payload = {"name": new_name, "config": config_data}
    resp = requests.post(f"{API_BASE_URL}/configs", json=payload, timeout=10)
    
    if resp.status_code == 200:
        new_config = resp.json()
        return redirect(url_for("config_detail", config_id=new_config["id"]))
    return redirect(url_for("configs_page"))


# ============================================================================
# Experiments
# ============================================================================

@app.route("/experiments")
def experiments_page():
    resp = requests.get(f"{API_BASE_URL}/experiments", timeout=10)
    data = resp.json()
    return render_template("experiments.html", experiments=data.get("experiments", []))


@app.route("/experiments/new/masked-lm")
def new_masked_lm_experiment():
    dataset_id = request.args.get("dataset_id")
    if not dataset_id:
        return redirect(url_for("datasets_page"))
    resp = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("datasets_page"))
    configs_resp = requests.get(f"{API_BASE_URL}/configs/by-type/masked_lm", timeout=10)
    configs = configs_resp.json().get("configs", []) if configs_resp.status_code == 200 else []
    return render_template("new_masked_lm.html", dataset=resp.json(), configs=configs)


@app.route("/experiments/new/causal-lm")
def new_causal_lm_experiment():
    dataset_id = request.args.get("dataset_id")
    if not dataset_id:
        return redirect(url_for("datasets_page"))
    resp = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("datasets_page"))
    configs_resp = requests.get(f"{API_BASE_URL}/configs/by-type/causal_lm", timeout=10)
    configs = configs_resp.json().get("configs", []) if configs_resp.status_code == 200 else []
    return render_template("new_causal_lm.html", dataset=resp.json(), configs=configs)


@app.route("/experiments/new/custom-lightning")
def new_custom_lightning_experiment():
    dataset_id = request.args.get("dataset_id")
    if not dataset_id:
        return redirect(url_for("datasets_page"))

    ds_resp = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}", timeout=10)
    if ds_resp.status_code != 200:
        return redirect(url_for("datasets_page"))

    plugins_resp = requests.get(f"{API_BASE_URL}/plugins", timeout=10)
    plugins = plugins_resp.json().get("plugins", []) if plugins_resp.status_code == 200 else []

    lightning_plugins = [p for p in plugins if p.get("kind") == "lightning_module"]
    dataloader_plugins = [p for p in plugins if p.get("kind") == "dataloaders"]

    lightning_plugin_classes = {
        p.get("id"): (p.get("symbols", {}) or {}).get("lightning_modules", [])
        for p in lightning_plugins
    }

    return render_template(
        "new_custom_lightning.html",
        dataset=ds_resp.json(),
        lightning_plugins=lightning_plugins,
        dataloader_plugins=dataloader_plugins,
        lightning_plugin_classes=lightning_plugin_classes,
        error=None,
    )


@app.route("/experiments/masked-lm", methods=["POST"])
def start_masked_lm():
    form = request.form.to_dict()
    config_id = form.get("config_id")
    
    if config_id:
        payload = {
            "dataset_id": form.get("dataset_id"),
            "config_id": config_id,
        }
    else:
        text_fields = [f.strip() for f in form.pop("text_fields", "").split(",") if f.strip()]
        payload = {
            "dataset_id": form.get("dataset_id"),
            "config_name": form.get("config_name") or None,
            "config": {
                "data": {
                    "text_fields": text_fields,
                    "separator": form.get("separator", "\n\n").replace("\\n", "\n"),
                    "validation_split": float(form.get("validation_split", 0.2)),
                    "seed": int(form.get("seed", 42)),
                    "max_length": int(form.get("max_length", 256)),
                },
                "model": {
                    "pretrained_model_name": form.get("pretrained_model_name", "distilbert-base-uncased"),
                    "freeze_embedding": "freeze_embedding" in form,
                    "freeze_encoder_layers": int(form.get("freeze_encoder_layers", 0)),
                },
                "training": {
                    "num_train_epochs": float(form.get("num_train_epochs", 3)),
                    "per_device_train_batch_size": int(form.get("per_device_train_batch_size", 8)),
                    "per_device_eval_batch_size": int(form.get("per_device_eval_batch_size", 8)),
                    "learning_rate": float(form.get("learning_rate", 5e-5)),
                    "weight_decay": float(form.get("weight_decay", 0.01)),
                    "warmup_ratio": float(form.get("warmup_ratio", 0.0)),
                    "gradient_accumulation_steps": int(form.get("gradient_accumulation_steps", 1)),
                    "logging_steps": int(form.get("logging_steps", 10)),
                    "eval_steps": int(form.get("eval_steps", 50)),
                    "save_steps": int(form.get("save_steps", 200)),
                    "save_total_limit": int(form.get("save_total_limit", 2)),
                    "max_steps": int(form.get("max_steps", -1)),
                    "early_stopping_patience": int(form.get("early_stopping_patience")) if form.get("early_stopping_patience") else None,
                    "early_stopping_metric": form.get("early_stopping_metric", "eval_loss"),
                    "early_stopping_greater_is_better": "early_stopping_greater_is_better" in form,
                },
            },
        }
    resp = requests.post(f"{API_BASE_URL}/experiments/masked-lm", json=payload, timeout=10)
    if resp.status_code == 200:
        experiment_id = resp.json().get("experiment_id")
        if experiment_id:
            return redirect(url_for("experiment_detail", experiment_id=experiment_id))
    return redirect(url_for("experiments_page"))


@app.route("/experiments/causal-lm", methods=["POST"])
def start_causal_lm():
    form = request.form.to_dict()
    config_id = form.get("config_id")
    
    if config_id:
        payload = {
            "dataset_id": form.get("dataset_id"),
            "config_id": config_id,
        }
    else:
        target_modules = [m.strip() for m in form.get("peft_target_modules", "").split(",") if m.strip()]
        payload = {
            "dataset_id": form.get("dataset_id"),
            "config_name": form.get("config_name") or None,
            "config": {
                "data": {
                    "question_field": form.get("question_field", "question"),
                    "answer_field": form.get("answer_field", "answer"),
                    "system_prompt": form.get("system_prompt", "You are an AI assistant."),
                    "template": form.get("template", "<|system|>\n{system_prompt}\n</s>\n<|user|>\n{question}\n</s>\n<|assistant|>\n{answer}\n</s>"),
                    "validation_split": float(form.get("validation_split", 0.2)),
                    "seed": int(form.get("seed", 42)),
                    "max_length": int(form.get("max_length", 512)),
                },
                "model": {
                    "pretrained_model_name": form.get("pretrained_model_name", "TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
                    "trust_remote_code": "trust_remote_code" in form,
                    "pad_token_override": form.get("pad_token_override") or None,
                },
                "peft": {
                    "enabled": "peft_enabled" in form,
                    "r": int(form.get("peft_r", 8)),
                    "lora_alpha": int(form.get("peft_lora_alpha", 16)),
                    "lora_dropout": float(form.get("peft_lora_dropout", 0.05)),
                    "bias": form.get("peft_bias", "none"),
                    "target_modules": target_modules or ["q_proj", "k_proj", "v_proj", "o_proj"],
                },
                "training": {
                    "num_train_epochs": float(form.get("num_train_epochs", 3)),
                    "per_device_train_batch_size": int(form.get("per_device_train_batch_size", 1)),
                    "per_device_eval_batch_size": int(form.get("per_device_eval_batch_size", 1)),
                    "learning_rate": float(form.get("learning_rate", 2e-5)),
                    "weight_decay": float(form.get("weight_decay", 0.0)),
                    "warmup_ratio": float(form.get("warmup_ratio", 0.03)),
                    "gradient_accumulation_steps": int(form.get("gradient_accumulation_steps", 8)),
                    "lr_scheduler_type": form.get("lr_scheduler_type", "cosine"),
                    "logging_steps": int(form.get("logging_steps", 5)),
                    "eval_steps": int(form.get("eval_steps", 20)),
                    "save_steps": int(form.get("save_steps", 100)),
                    "save_total_limit": int(form.get("save_total_limit", 2)),
                    "max_steps": int(form.get("max_steps", -1)),
                    "gradient_checkpointing": "gradient_checkpointing" in form,
                    "fp16": "fp16" in form,
                    "bf16": "bf16" in form,
                    "early_stopping_patience": int(form.get("early_stopping_patience")) if form.get("early_stopping_patience") else None,
                    "early_stopping_metric": form.get("early_stopping_metric", "eval_loss"),
                    "early_stopping_greater_is_better": "early_stopping_greater_is_better" in form,
                    "auto_evaluate": "auto_evaluate" in form,
                },
            },
        }
    resp = requests.post(f"{API_BASE_URL}/experiments/causal-lm", json=payload, timeout=10)
    if resp.status_code == 200:
        experiment_id = resp.json().get("experiment_id")
        if experiment_id:
            return redirect(url_for("experiment_detail", experiment_id=experiment_id))
    return redirect(url_for("experiments_page"))


@app.route("/experiments/custom-lightning", methods=["POST"])
def start_custom_lightning():
    form = request.form.to_dict()
    dataset_id = form.get("dataset_id")
    if not dataset_id:
        return redirect(url_for("datasets_page"))

    try:
        cfg_blob = json.loads(form.get("cfg_json", ""))
    except Exception:
        # Fail fast: render the form again with an error.
        ds_resp = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}", timeout=10)
        plugins_resp = requests.get(f"{API_BASE_URL}/plugins", timeout=10)
        plugins = plugins_resp.json().get("plugins", []) if plugins_resp.status_code == 200 else []
        lightning_plugins = [p for p in plugins if p.get("kind") == "lightning_module"]
        dataloader_plugins = [p for p in plugins if p.get("kind") == "dataloaders"]
        lightning_plugin_classes = {
            p.get("id"): (p.get("symbols", {}) or {}).get("lightning_modules", [])
            for p in lightning_plugins
        }
        return render_template(
            "new_custom_lightning.html",
            dataset=ds_resp.json() if ds_resp.status_code == 200 else {"id": dataset_id, "filename": "", "row_count": 0, "columns": []},
            lightning_plugins=lightning_plugins,
            dataloader_plugins=dataloader_plugins,
            lightning_plugin_classes=lightning_plugin_classes,
            error="cfg_json must be valid JSON",
        ), 400

    payload = {
        "dataset_id": dataset_id,
        "config": {
            "training": {
                "max_epochs": int(form.get("max_epochs", 1)),
                "accelerator": form.get("accelerator", "auto"),
                "devices": form.get("devices", "auto"),
                "precision": form.get("precision", "32"),
                "log_every_n_steps": int(form.get("log_every_n_steps", 10)),
            },
            "cfg": cfg_blob,
        },
        "lightning_module_plugin_id": form.get("lightning_module_plugin_id"),
        "lightning_module_class_name": form.get("lightning_module_class_name"),
        "dataloaders_plugin_id": form.get("dataloaders_plugin_id"),
        "dataloaders_function_name": "build_dataloaders",
    }

    resp = requests.post(f"{API_BASE_URL}/experiments/custom-lightning", json=payload, timeout=10)
    if resp.status_code == 200:
        experiment_id = resp.json().get("experiment_id")
        if experiment_id:
            return redirect(url_for("experiment_detail", experiment_id=experiment_id))

    return redirect(url_for("experiments_page"))


@app.route("/experiments/<experiment_id>")
def experiment_detail(experiment_id: str):
    resp = requests.get(f"{API_BASE_URL}/experiments/{experiment_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("experiments_page"))
    logs_resp = requests.get(f"{API_BASE_URL}/experiments/{experiment_id}/logs", timeout=10)
    logs_data = logs_resp.json() if logs_resp.status_code == 200 else {}
    logs = logs_data.get("logs", []) if isinstance(logs_data, dict) else logs_data
    benchmarks_resp = requests.get(f"{API_BASE_URL}/benchmarks", timeout=10)
    benchmarks = benchmarks_resp.json().get("benchmarks", []) if benchmarks_resp.status_code == 200 else []
    return render_template("experiment_detail.html", experiment=resp.json(), logs=logs, benchmarks=benchmarks)


@app.route("/experiments/<experiment_id>/copy")
def copy_experiment(experiment_id: str):
    resp = requests.get(f"{API_BASE_URL}/experiments/{experiment_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("experiments_page"))
    experiment = resp.json()
    datasets_resp = requests.get(f"{API_BASE_URL}/datasets", timeout=10)
    datasets = datasets_resp.json().get("datasets", []) if datasets_resp.status_code == 200 else []

    plugins_resp = requests.get(f"{API_BASE_URL}/plugins", timeout=10)
    plugins = plugins_resp.json().get("plugins", []) if plugins_resp.status_code == 200 else []
    lightning_plugins = [p for p in plugins if p.get("kind") == "lightning_module"]
    dataloader_plugins = [p for p in plugins if p.get("kind") == "dataloaders"]
    lightning_plugin_classes = {
        p.get("id"): (p.get("symbols", {}) or {}).get("lightning_modules", [])
        for p in lightning_plugins
    }

    return render_template(
        "copy_experiment.html",
        experiment=experiment,
        datasets=datasets,
        lightning_plugins=lightning_plugins,
        dataloader_plugins=dataloader_plugins,
        lightning_plugin_classes=lightning_plugin_classes,
    )


@app.route("/experiments/<experiment_id>/delete", methods=["POST"])
def delete_experiment(experiment_id: str):
    requests.delete(f"{API_BASE_URL}/experiments/{experiment_id}", timeout=10)
    return redirect(url_for("experiments_page"))


@app.route("/experiments/<experiment_id>/stop", methods=["POST"])
def stop_experiment(experiment_id: str):
    requests.post(f"{API_BASE_URL}/experiments/{experiment_id}/stop", timeout=10)
    return redirect(url_for("experiment_detail", experiment_id=experiment_id))


@app.route("/experiments/compare")
def experiments_compare_page():
    ids = request.args.get("ids", "")
    experiment_ids = [eid.strip() for eid in ids.split(",") if eid.strip()]
    if len(experiment_ids) < 2:
        return redirect(url_for("evaluations_page"))

    resp = requests.post(f"{API_BASE_URL}/experiments/compare", json=experiment_ids, timeout=30)
    if resp.status_code != 200:
        return redirect(url_for("experiments_page"))
    
    return render_template("experiments_compare.html", comparison=resp.json())


@app.route("/experiments/<experiment_id>/extract-meta", methods=["POST"])
def extract_meta_features(experiment_id: str):
    # Start background job (non-blocking). The UI uses AJAX now; this route is kept
    # for compatibility and must not block on long probe runs.
    try:
        requests.post(f"{API_BASE_URL}/meta/extract/{experiment_id}/start", timeout=10)
    except Exception:
        pass
    return redirect(url_for("experiment_detail", experiment_id=experiment_id))


# ============================================================================
# Benchmarks
# ============================================================================

@app.route("/benchmarks")
def benchmarks_page():
    resp = requests.get(f"{API_BASE_URL}/benchmarks", timeout=10)
    data = resp.json()
    plugins_resp = requests.get(f"{API_BASE_URL}/plugins", timeout=10)
    plugins = plugins_resp.json().get("plugins", []) if plugins_resp.status_code == 200 else []
    benchmark_plugins = [p for p in plugins if p.get("kind") == "benchmark"]
    err = request.args.get("error")
    return render_template(
        "benchmarks.html",
        benchmarks=data.get("benchmarks", []),
        benchmark_plugins=benchmark_plugins,
        error=err,
    )


@app.route("/benchmarks/create", methods=["POST"])
def create_benchmark():
    form = request.form.to_dict()
    benchmark_type = form.get("benchmark_type", "causal_lm_qa")
    spec_blob = {}
    if benchmark_type in {"custom_lightning_sin_regression", "custom_lightning_plugin"}:
        try:
            spec_blob = json.loads(form.get("spec_json", ""))
        except Exception:
            spec_blob = {}
    payload = {
        "name": form.get("name", "").strip() or None,
        "benchmark_type": benchmark_type,
        "spec": spec_blob,
        "question": form.get("question", ""),
        "gold_answer": form.get("gold_answer", ""),
        "max_new_tokens": int(form.get("max_new_tokens", 128)),
        "temperature": float(form.get("temperature", 0.7)),
        "top_p": float(form.get("top_p", 0.9)),
    }
    resp = requests.post(f"{API_BASE_URL}/benchmarks", json=payload, timeout=10)
    if resp.status_code == 200:
        return redirect(url_for("benchmarks_page"))
    msg = "Failed to create benchmark"
    try:
        body = resp.json()
        if isinstance(body, dict) and body.get("detail"):
            msg = str(body.get("detail"))
    except Exception:
        pass
    return redirect(url_for("benchmarks_page", error=quote(msg, safe="")))


@app.route("/benchmarks/<benchmark_id>/edit", methods=["GET", "POST"])
def edit_benchmark(benchmark_id: str):
    if request.method == "GET":
        resp = requests.get(f"{API_BASE_URL}/benchmarks/{benchmark_id}", timeout=10)
        if resp.status_code != 200:
            return redirect(url_for("benchmarks_page"))
        return render_template("benchmark_edit.html", benchmark=resp.json())
    
    form = request.form.to_dict()
    spec_blob = None
    if form.get("spec_json"):
        try:
            spec_blob = json.loads(form.get("spec_json", ""))
        except Exception:
            spec_blob = None
    payload = {
        "name": form.get("name", "").strip() or None,
        "question": form.get("question", ""),
        "gold_answer": form.get("gold_answer", ""),
        "spec": spec_blob,
        "max_new_tokens": int(form.get("max_new_tokens", 128)),
        "temperature": float(form.get("temperature", 0.7)),
        "top_p": float(form.get("top_p", 0.9)),
    }
    resp = requests.put(f"{API_BASE_URL}/benchmarks/{benchmark_id}", json=payload, timeout=10)
    if resp.status_code == 200:
        return redirect(url_for("benchmarks_page"))
    msg = "Failed to update benchmark"
    try:
        body = resp.json()
        if isinstance(body, dict) and body.get("detail"):
            msg = str(body.get("detail"))
    except Exception:
        pass
    return redirect(url_for("benchmarks_page", error=quote(msg, safe="")))


@app.route("/benchmarks/<benchmark_id>/delete", methods=["POST"])
def delete_benchmark(benchmark_id: str):
    requests.delete(f"{API_BASE_URL}/benchmarks/{benchmark_id}", timeout=10)
    return redirect(url_for("benchmarks_page"))


@app.route("/benchmarks/<benchmark_id>/evaluate", methods=["GET"])
def benchmark_evaluate_form(benchmark_id: str):
    experiment_id = request.args.get("experiment_id")
    if experiment_id:
        return redirect(url_for("start_benchmark_eval", benchmark_id=benchmark_id, experiment_id=experiment_id))
    
    benchmark_resp = requests.get(f"{API_BASE_URL}/benchmarks/{benchmark_id}", timeout=10)
    if benchmark_resp.status_code != 200:
        return redirect(url_for("benchmarks_page"))
    benchmark = benchmark_resp.json()
    experiments_resp = requests.get(f"{API_BASE_URL}/experiments", timeout=10)
    experiments = experiments_resp.json().get("experiments", []) if experiments_resp.status_code == 200 else []
    bt = benchmark.get("benchmark_type", "causal_lm_qa")
    if bt == "causal_lm_qa":
        target_type = "causal_lm"
    elif bt == "masked_lm_fill_mask":
        target_type = "masked_lm"
    elif bt in {"custom_lightning_sin_regression", "custom_lightning_plugin"}:
        target_type = "custom_lightning"
    else:
        target_type = "causal_lm"

    completed_experiments = [
        e for e in experiments if e.get("status") == "completed" and e.get("experiment_type") == target_type
    ]
    return render_template("benchmark_evaluate.html", benchmark=benchmark, experiments=completed_experiments)


@app.route("/benchmarks/<benchmark_id>/evaluate", methods=["POST"])
def start_benchmark_eval(benchmark_id: str):
    experiment_id = request.args.get("experiment_id") or request.form.get("experiment_id")
    if not experiment_id:
        return redirect(url_for("benchmarks_page"))
    
    payload = {"experiment_id": experiment_id}
    resp = requests.post(f"{API_BASE_URL}/benchmarks/{benchmark_id}/evaluate", json=payload, timeout=10)
    if resp.status_code == 200:
        eval_id = resp.json().get("eval_id")
        if eval_id:
            return redirect(url_for("evaluation_detail", eval_id=eval_id))
    return redirect(url_for("benchmarks_page"))


@app.route("/benchmarks/<benchmark_id>/results")
def benchmark_results(benchmark_id: str):
    benchmark_resp = requests.get(f"{API_BASE_URL}/benchmarks/{benchmark_id}", timeout=10)
    if benchmark_resp.status_code != 200:
        return redirect(url_for("benchmarks_page"))
    evals_resp = requests.get(f"{API_BASE_URL}/evaluations/by-benchmark/{benchmark_id}", timeout=10)
    evaluations = evals_resp.json().get("evaluations", []) if evals_resp.status_code == 200 else []
    return render_template("benchmark_results.html", benchmark=benchmark_resp.json(), evaluations=evaluations)


# ============================================================================
# Evaluations
# ============================================================================

@app.route("/evaluations")
def evaluations_page():
    resp = requests.get(f"{API_BASE_URL}/evaluations", timeout=10)
    data = resp.json()
    return render_template("evaluations.html", evaluations=data.get("evaluations", []))


@app.route("/evaluations/<eval_id>")
def evaluation_detail(eval_id: str):
    resp = requests.get(f"{API_BASE_URL}/evaluations/{eval_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("evaluations_page"))
    return render_template("evaluation_detail.html", evaluation=resp.json())


@app.route("/evaluations/<eval_id>/delete", methods=["POST"])
def delete_evaluation(eval_id: str):
    requests.delete(f"{API_BASE_URL}/evaluations/{eval_id}", timeout=10)
    return redirect(url_for("evaluations_page"))


# ============================================================================
# Meta-Learning
# ============================================================================

@app.route("/meta")
def meta_page():
    meta_features = []
    predictor_trained = False
    synthetic_count = 0
    real_count = 0
    autotune_jobs = []
    
    try:
        features_resp = requests.get(f"{API_BASE_URL}/meta/features", timeout=5)
        if features_resp.status_code == 200:
            meta_features = features_resp.json().get("features", [])
            synthetic_count = sum(1 for f in meta_features if f.get("is_synthetic"))
            real_count = len(meta_features) - synthetic_count
    except Exception:
        pass
    
    try:
        predictor_resp = requests.get(f"{API_BASE_URL}/meta/predictor/status", timeout=5)
        if predictor_resp.status_code == 200:
            predictor_trained = predictor_resp.json().get("trained", False)
    except Exception:
        pass
    
    try:
        autotune_resp = requests.get(f"{API_BASE_URL}/autotune", timeout=5)
        if autotune_resp.status_code == 200:
            autotune_jobs = autotune_resp.json().get("jobs", [])
    except Exception:
        pass
    
    # Check for training results from redirect
    train_results = None
    if request.args.get("train_success"):
        train_results = {
            "message": request.args.get("train_message", ""),
            "rmse": request.args.get("train_rmse", ""),
            "rmse_std": request.args.get("train_rmse_std", ""),
            "iterations": request.args.get("train_iterations", ""),
            "samples": request.args.get("train_samples", ""),
        }
    
    return render_template(
        "meta.html",
        meta_features=meta_features,
        meta_features_count=len(meta_features),
        predictor_trained=predictor_trained,
        synthetic_count=synthetic_count,
        real_count=real_count,
        autotune_jobs=autotune_jobs,
        train_results=train_results,
    )


@app.route("/meta/probe")
def meta_probe_page():
    dataset_id = request.args.get("dataset_id")
    if not dataset_id:
        return redirect(url_for("datasets_page"))
    resp = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("datasets_page"))
    configs_resp = requests.get(f"{API_BASE_URL}/configs/by-type/causal_lm", timeout=10)
    configs = configs_resp.json().get("configs", []) if configs_resp.status_code == 200 else []
    return render_template("meta_probe.html", dataset=resp.json(), configs=configs)


@app.route("/meta/probe", methods=["POST"])
def meta_probe_submit():
    form = request.form.to_dict()
    dataset_id = form.get("dataset_id")
    config_id = form.get("config_id")
    probe_steps = int(form.get("probe_steps", 5))
    
    # Run probe
    payload = {
        "dataset_id": dataset_id,
        "config_id": config_id,
        "probe_steps": probe_steps,
    }
    resp = requests.post(f"{API_BASE_URL}/meta/probe", json=payload, timeout=120)
    if resp.status_code != 200:
        return redirect(url_for("meta_page"))
    
    result = resp.json()
    features = result.get("features", {})
    prediction = result.get("prediction")
    
    return render_template("meta_probe_result.html", features=features, prediction=prediction)


@app.route("/meta/train", methods=["POST"])
def meta_train():
    include_synthetic = "include_synthetic" in request.form
    resp = requests.post(f"{API_BASE_URL}/meta/train-predictor", json={"include_synthetic": include_synthetic}, timeout=60)
    if resp.status_code == 200:
        data = resp.json()
        metrics = data.get("metrics", {})
        return redirect(url_for("meta_page", 
            train_success="1",
            train_message=data.get("message", ""),
            train_rmse=f"{metrics.get('train_rmse', 0):.2f}",
            train_rmse_std=f"{metrics.get('train_rmse_std', 0):.2f}",
            train_iterations=int(metrics.get('best_iteration', 0)),
            train_samples=int(metrics.get('num_samples', 0)),
        ))
    return redirect(url_for("meta_page"))


@app.route("/meta/generate-synthetic", methods=["POST"])
def meta_generate_synthetic():
    n_samples = int(request.form.get("n_samples", 100))
    requests.post(f"{API_BASE_URL}/meta/generate-synthetic", json={"n_samples": n_samples}, timeout=30)
    return redirect(url_for("meta_page"))


@app.route("/meta/clear-synthetic", methods=["POST"])
def meta_clear_synthetic():
    requests.post(f"{API_BASE_URL}/meta/clear-synthetic", timeout=10)
    return redirect(url_for("meta_page"))


@app.route("/meta/backfill-rouge", methods=["POST"])
def meta_backfill_rouge():
    requests.post(f"{API_BASE_URL}/meta/backfill-rouge", timeout=30)
    return redirect(url_for("meta_page"))


@app.route("/meta/explain/<experiment_id>")
def meta_explain(experiment_id: str):
    resp = requests.get(f"{API_BASE_URL}/meta/explain/{experiment_id}", timeout=30)
    if resp.status_code != 200:
        return redirect(url_for("meta_page"))
    return render_template("meta_explain.html", explanation=resp.json(), experiment_id=experiment_id)


@app.route("/meta/optimize")
def meta_optimize_page():
    dataset_id = request.args.get("dataset_id")
    if not dataset_id:
        return redirect(url_for("datasets_page"))
    resp = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("datasets_page"))
    return render_template("meta_optimize.html", dataset=resp.json())


@app.route("/meta/optimize", methods=["POST"])
def meta_optimize_submit():
    form = request.form.to_dict()
    payload = {
        "dataset_id": form.get("dataset_id"),
        "target_metric": form.get("target_metric", "final_bleu_score"),
        "n_trials": int(form.get("n_trials", 20)),
    }
    resp = requests.post(f"{API_BASE_URL}/meta/optimize", json=payload, timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("meta_page"))
    
    job_id = resp.json().get("job_id")
    return redirect(url_for("meta_optimize_status", job_id=job_id))


@app.route("/meta/optimize/<job_id>")
def meta_optimize_status(job_id: str):
    resp = requests.get(f"{API_BASE_URL}/meta/optimize/{job_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("meta_page"))
    job = resp.json()
    
    if job.get("status") == "completed":
        return render_template("meta_optimize_results.html", job=job)
    else:
        return render_template("meta_optimize_progress.html", job=job)


@app.route("/meta/optimize/<job_id>/results")
def meta_optimize_results(job_id: str):
    resp = requests.get(f"{API_BASE_URL}/meta/optimize/{job_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("meta_page"))
    return render_template("meta_optimize_results.html", job=resp.json())


# ============================================================================
# API Proxy Endpoints (for AJAX calls from frontend)
# ============================================================================

@app.route("/api/health")
def api_health():
    resp = requests.get(f"{API_BASE_URL}/health", timeout=5)
    return jsonify(resp.json())


@app.route("/api/configs/<config_id>")
def api_config_detail(config_id: str):
    # Try by ID first (UUID format), fallback to by-name
    resp = requests.get(f"{API_BASE_URL}/configs/{config_id}", timeout=10)
    if resp.status_code == 404:
        resp = requests.get(f"{API_BASE_URL}/configs/by-name/{config_id}", timeout=10)
    return jsonify(resp.json()), resp.status_code


@app.route("/api/experiments/<experiment_id>")
def api_experiment_detail(experiment_id: str):
    resp = requests.get(f"{API_BASE_URL}/experiments/{experiment_id}", timeout=10)
    return jsonify(resp.json())


@app.route("/api/experiments/<experiment_id>/logs")
def api_experiment_logs(experiment_id: str):
    resp = requests.get(f"{API_BASE_URL}/experiments/{experiment_id}/logs", timeout=10)
    data = resp.json()
    # Return just the logs array for easier consumption by frontend
    return jsonify(data.get("logs", []))


@app.route("/api/experiments/<experiment_id>/progress")
def api_experiment_progress(experiment_id: str):
    """Get live training progress updated every step."""
    resp = requests.get(f"{API_BASE_URL}/experiments/{experiment_id}/progress", timeout=10)
    return jsonify(resp.json()), resp.status_code


@app.route("/api/experiments/<experiment_id>/stop", methods=["POST"])
def api_stop_experiment(experiment_id: str):
    resp = requests.post(f"{API_BASE_URL}/experiments/{experiment_id}/stop", timeout=10)
    return jsonify(resp.json()), resp.status_code


@app.route("/api/evaluations/<eval_id>")
def api_evaluation_detail(eval_id: str):
    # Evaluation payloads can be large and the API process may be busy loading
    # models; 10s is too aggressive and causes spurious UI 500s.
    resp = requests.get(f"{API_BASE_URL}/evaluations/{eval_id}", timeout=60)
    return jsonify(resp.json())


@app.route("/api/optimize/<job_id>/status")
def api_optimize_status(job_id: str):
    resp = requests.get(f"{API_BASE_URL}/meta/optimize/{job_id}", timeout=10)
    return jsonify(resp.json())


@app.route("/api/autotune/run", methods=["POST"])
def api_autotune_run():
    payload = request.get_json()
    resp = requests.post(f"{API_BASE_URL}/autotune/run", json=payload, timeout=10)
    return jsonify(resp.json()), resp.status_code


@app.route("/api/autotune/<job_id>")
def api_autotune_status(job_id: str):
    resp = requests.get(f"{API_BASE_URL}/autotune/{job_id}", timeout=10)
    return jsonify(resp.json())


@app.route("/api/autotune")
def api_autotune_list():
    resp = requests.get(f"{API_BASE_URL}/autotune", timeout=10)
    return jsonify(resp.json())


@app.route("/api/meta/train-predictor", methods=["POST"])
def api_meta_train_predictor():
    payload = request.get_json()
    resp = requests.post(f"{API_BASE_URL}/meta/train-predictor", json=payload, timeout=120)
    return jsonify(resp.json()), resp.status_code


@app.route("/api/meta/extract/<experiment_id>/start", methods=["POST"])
def api_meta_extract_start(experiment_id: str):
    resp = requests.post(f"{API_BASE_URL}/meta/extract/{experiment_id}/start", timeout=10)
    return jsonify(resp.json()), resp.status_code


@app.route("/api/meta/extract/jobs/<job_id>")
def api_meta_extract_status(job_id: str):
    resp = requests.get(f"{API_BASE_URL}/meta/extract/jobs/{job_id}", timeout=10)
    return jsonify(resp.json()), resp.status_code


@app.route("/api/datasets/<dataset_id>/row/<int:row_idx>")
def api_dataset_row(dataset_id: str, row_idx: int):
    resp = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}/row/{row_idx}", timeout=10)
    return jsonify(resp.json())


@app.route("/api/proxy/benchmarks/<benchmark_id>/evaluate", methods=["POST"])
def api_start_benchmark_eval(benchmark_id: str):
    payload = request.get_json()
    resp = requests.post(f"{API_BASE_URL}/benchmarks/{benchmark_id}/evaluate", json=payload, timeout=10)
    return jsonify(resp.json()), resp.status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=True)
