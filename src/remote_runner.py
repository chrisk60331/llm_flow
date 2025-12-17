"""Remote execution orchestration for experiments and benchmarks."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .models import ComputeTarget
from .ssh_client import SSHClient
from .storage import get_compute_target


def _get_repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).resolve().parent.parent


def prepare_remote_environment(
    client: SSHClient,
    dataset_path: str | None = None,
    plugin_paths: list[str] | None = None,
) -> str:
    """Prepare the remote environment by syncing code, datasets, and plugins.

    Returns:
        The remote work directory path.
    """
    remote_work_dir = client.target.remote_work_dir
    repo_root = _get_repo_root()

    client.mkdir_p(remote_work_dir)

    src_dir = repo_root / "src"
    if src_dir.exists():
        client.upload_directory(src_dir, f"{remote_work_dir}/src")

    remote_data_dir = f"{remote_work_dir}/data"
    client.mkdir_p(remote_data_dir)
    client.mkdir_p(f"{remote_data_dir}/uploads")
    client.mkdir_p(f"{remote_data_dir}/plugins")

    if dataset_path:
        local_dataset = Path(dataset_path)
        if local_dataset.exists():
            remote_dataset_path = f"{remote_data_dir}/uploads/{local_dataset.name}"
            client.upload_file(local_dataset, remote_dataset_path)

    if plugin_paths:
        for plugin_path in plugin_paths:
            local_plugin = Path(plugin_path)
            if local_plugin.exists():
                remote_plugin_path = f"{remote_data_dir}/plugins/{local_plugin.name}"
                client.upload_file(local_plugin, remote_plugin_path)

    remote_artifacts_dir = f"{remote_work_dir}/artifacts"
    client.mkdir_p(remote_artifacts_dir)

    return remote_work_dir


def run_experiment_remote(
    target: ComputeTarget,
    experiment_id: str,
    payload: dict,
    dataset_path: str,
    plugin_paths: list[str] | None = None,
    poll_interval: int = 5,
    timeout: int = 3600,
) -> tuple[bool, dict, str | None]:
    """Run an experiment on a remote compute target.

    Args:
        target: The compute target to run on.
        experiment_id: The experiment ID.
        payload: The runner payload dictionary.
        dataset_path: Local path to the dataset file.
        plugin_paths: Optional list of local plugin file paths.
        poll_interval: Seconds between status checks.
        timeout: Maximum seconds to wait for completion.

    Returns:
        Tuple of (success, metrics_dict, error_message)
    """
    with SSHClient(target) as client:
        remote_work_dir = prepare_remote_environment(
            client,
            dataset_path=dataset_path,
            plugin_paths=plugin_paths,
        )

        remote_artifacts_dir = f"{remote_work_dir}/artifacts"
        remote_output_dir = f"{remote_artifacts_dir}/custom_lightning_{experiment_id}"
        client.mkdir_p(remote_output_dir)

        adjusted_payload = _adjust_payload_paths(payload, remote_work_dir)

        payload_json = json.dumps(adjusted_payload, indent=2)
        payload_path = f"{remote_output_dir}/runner_payload.json"

        exit_code, _, _ = client.run_command(
            f"cat > {payload_path} << 'PAYLOAD_EOF'\n{payload_json}\nPAYLOAD_EOF"
        )
        if exit_code != 0:
            return False, {}, "Failed to write payload file"

        cmd = f"cd {remote_work_dir} && python3 -m src.custom_lightning_runner {payload_path}"
        exit_code, stdout, stderr = client.run_command(cmd, timeout=timeout)

        if stdout:
            client.run_command(
                f"cat > {remote_output_dir}/runner_stdout.txt << 'EOF'\n{stdout}\nEOF"
            )
        if stderr:
            client.run_command(
                f"cat > {remote_output_dir}/runner_stderr.txt << 'EOF'\n{stderr}\nEOF"
            )

        if exit_code != 0:
            error_msg = stderr or "Runner failed with no error message"
            return False, {}, error_msg

        metrics_path = f"{remote_output_dir}/metrics.json"
        if not client.file_exists(metrics_path):
            return False, {}, "Runner completed but metrics.json is missing"

        metrics_content = client.read_file(metrics_path)
        metrics = json.loads(metrics_content)

        local_output_dir = _get_repo_root() / "artifacts" / f"custom_lightning_{experiment_id}"
        local_output_dir.mkdir(parents=True, exist_ok=True)

        client.download_directory(remote_output_dir, local_output_dir)

        return True, metrics, None


def run_benchmark_remote(
    target: ComputeTarget,
    eval_id: str,
    experiment_id: str,
    payload: dict,
    runner_module: str,
    plugin_paths: list[str] | None = None,
    timeout: int = 300,
) -> tuple[bool, dict, str | None]:
    """Run a benchmark evaluation on a remote compute target.

    Args:
        target: The compute target to run on.
        eval_id: The evaluation ID.
        experiment_id: The experiment ID being evaluated.
        payload: The benchmark runner payload dictionary.
        runner_module: The Python module to run (e.g., 'src.custom_lightning_sin_benchmark_runner').
        plugin_paths: Optional list of local plugin file paths.
        timeout: Maximum seconds to wait for completion.

    Returns:
        Tuple of (success, metrics_dict, error_message)
    """
    with SSHClient(target) as client:
        remote_work_dir = prepare_remote_environment(
            client,
            plugin_paths=plugin_paths,
        )

        remote_artifacts_dir = f"{remote_work_dir}/artifacts"
        remote_output_dir = f"{remote_artifacts_dir}/custom_lightning_{experiment_id}"

        local_output_dir = _get_repo_root() / "artifacts" / f"custom_lightning_{experiment_id}"
        if local_output_dir.exists():
            model_ckpt = local_output_dir / "model.ckpt"
            if model_ckpt.exists():
                client.mkdir_p(remote_output_dir)
                client.upload_file(model_ckpt, f"{remote_output_dir}/model.ckpt")

        adjusted_payload = _adjust_payload_paths(payload, remote_work_dir)

        payload_json = json.dumps(adjusted_payload, indent=2)
        payload_path = f"{remote_output_dir}/benchmark_payload_{eval_id}.json"

        exit_code, _, _ = client.run_command(
            f"cat > {payload_path} << 'PAYLOAD_EOF'\n{payload_json}\nPAYLOAD_EOF"
        )
        if exit_code != 0:
            return False, {}, "Failed to write benchmark payload file"

        cmd = f"cd {remote_work_dir} && python3 -m {runner_module} {payload_path}"
        exit_code, stdout, stderr = client.run_command(cmd, timeout=timeout)

        if exit_code != 0:
            error_msg = stderr or "Benchmark runner failed"
            return False, {}, error_msg

        metrics_filename = "benchmark_metrics.json"
        if "plugin" in runner_module:
            metrics_filename = "benchmark_plugin_metrics.json"

        metrics_path = f"{remote_output_dir}/{metrics_filename}"
        if not client.file_exists(metrics_path):
            return False, {}, f"Benchmark runner completed but {metrics_filename} is missing"

        metrics_content = client.read_file(metrics_path)
        metrics = json.loads(metrics_content)

        local_output_dir.mkdir(parents=True, exist_ok=True)
        client.download_file(metrics_path, local_output_dir / metrics_filename)

        return True, metrics, None


def run_probe_remote(
    target: ComputeTarget,
    probe_id: str,
    payload: dict,
    dataset_path: str,
    timeout: int = 600,
) -> tuple[bool, dict, str | None]:
    """Run a meta-learning probe on a remote compute target.

    Args:
        target: The compute target to run on.
        probe_id: Unique ID for this probe run.
        payload: The probe configuration.
        dataset_path: Local path to the dataset file.
        timeout: Maximum seconds to wait for completion.

    Returns:
        Tuple of (success, features_dict, error_message)
    """
    with SSHClient(target) as client:
        remote_work_dir = prepare_remote_environment(
            client,
            dataset_path=dataset_path,
        )

        remote_artifacts_dir = f"{remote_work_dir}/artifacts"
        remote_probe_dir = f"{remote_artifacts_dir}/probe_{probe_id}"
        client.mkdir_p(remote_probe_dir)

        adjusted_payload = _adjust_payload_paths(payload, remote_work_dir)

        payload_json = json.dumps(adjusted_payload, indent=2)
        payload_path = f"{remote_probe_dir}/probe_payload.json"

        exit_code, _, _ = client.run_command(
            f"cat > {payload_path} << 'PAYLOAD_EOF'\n{payload_json}\nPAYLOAD_EOF"
        )
        if exit_code != 0:
            return False, {}, "Failed to write probe payload file"

        cmd = f"cd {remote_work_dir} && python3 -c \"import json; from src.probe import run_probe; payload = json.load(open('{payload_path}')); result = run_probe(payload); json.dump(result, open('{remote_probe_dir}/probe_result.json', 'w'))\""
        exit_code, stdout, stderr = client.run_command(cmd, timeout=timeout)

        if exit_code != 0:
            error_msg = stderr or "Probe failed"
            return False, {}, error_msg

        result_path = f"{remote_probe_dir}/probe_result.json"
        if not client.file_exists(result_path):
            return False, {}, "Probe completed but result file is missing"

        result_content = client.read_file(result_path)
        result = json.loads(result_content)

        return True, result, None


def _adjust_payload_paths(payload: dict, remote_work_dir: str) -> dict:
    """Adjust file paths in payload for remote execution."""
    adjusted = payload.copy()

    path_keys = [
        "output_dir",
        "checkpoint_path",
        "lightning_module_path",
        "dataloaders_path",
        "benchmark_plugin_path",
    ]

    for key in path_keys:
        if key in adjusted and adjusted[key]:
            local_path = Path(adjusted[key])
            if "artifacts" in str(local_path):
                relative_part = str(local_path).split("artifacts/")[-1]
                adjusted[key] = f"{remote_work_dir}/artifacts/{relative_part}"
            elif "plugins" in str(local_path):
                adjusted[key] = f"{remote_work_dir}/data/plugins/{local_path.name}"

    if "dataset" in adjusted and isinstance(adjusted["dataset"], dict):
        dataset = adjusted["dataset"].copy()
        if "path" in dataset:
            local_path = Path(dataset["path"])
            dataset["path"] = f"{remote_work_dir}/data/uploads/{local_path.name}"
        adjusted["dataset"] = dataset

    if "config" in adjusted and isinstance(adjusted["config"], dict):
        config = adjusted["config"].copy()
        if "training" in config and isinstance(config["training"], dict):
            training = config["training"].copy()
            if "output_dir" in training:
                local_path = Path(training["output_dir"])
                if "artifacts" in str(local_path):
                    relative_part = str(local_path).split("artifacts/")[-1]
                    training["output_dir"] = f"{remote_work_dir}/artifacts/{relative_part}"
            config["training"] = training
        adjusted["config"] = config

    return adjusted


def retrieve_artifacts(
    target: ComputeTarget,
    experiment_id: str,
) -> bool:
    """Retrieve artifacts from a remote compute target.

    Args:
        target: The compute target.
        experiment_id: The experiment ID.

    Returns:
        True if artifacts were retrieved successfully.
    """
    with SSHClient(target) as client:
        remote_work_dir = client.target.remote_work_dir
        remote_output_dir = f"{remote_work_dir}/artifacts/custom_lightning_{experiment_id}"

        if not client.file_exists(remote_output_dir):
            return False

        local_output_dir = _get_repo_root() / "artifacts" / f"custom_lightning_{experiment_id}"
        local_output_dir.mkdir(parents=True, exist_ok=True)

        client.download_directory(remote_output_dir, local_output_dir)
        return True

