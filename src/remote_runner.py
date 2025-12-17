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
        The remote work directory path (absolute, with ~ expanded).
    """
    remote_work_dir = client.target.remote_work_dir
    # Expand ~ to absolute path for use in payloads (Python doesn't auto-expand ~)
    if remote_work_dir.startswith("~/"):
        exit_code, stdout, _ = client.run_command("echo $HOME")
        if exit_code == 0:
            home = stdout.strip()
            remote_work_dir = remote_work_dir.replace("~", home, 1)
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


def run_causal_lm_remote(
    target: ComputeTarget,
    experiment_id: str,
    payload: dict,
    dataset_path: str,
    poll_interval: int = 5,
    timeout: int = 3600,
    on_log_update: callable | None = None,
) -> tuple[bool, dict, str | None, str]:
    """Run a causal LM experiment on a remote compute target.

    Args:
        target: The compute target to run on.
        experiment_id: The experiment ID.
        payload: The runner payload dictionary.
        dataset_path: Local path to the dataset file.
        poll_interval: Seconds between status checks.
        timeout: Maximum seconds to wait for completion.
        on_log_update: Optional callback called with (logs: str) when logs update.

    Returns:
        Tuple of (success, metrics_dict, error_message, logs)
    """
    with SSHClient(target) as client:
        remote_work_dir = prepare_remote_environment(
            client,
            dataset_path=dataset_path,
        )

        remote_artifacts_dir = f"{remote_work_dir}/artifacts"
        remote_output_dir = f"{remote_artifacts_dir}/causal_lm_{experiment_id}"
        client.mkdir_p(remote_output_dir)

        # Create local artifacts dir immediately so UI can read partial logs during execution
        local_output_dir = _get_repo_root() / "artifacts" / f"causal_lm_{experiment_id}"
        local_output_dir.mkdir(parents=True, exist_ok=True)

        adjusted_payload = _adjust_payload_paths(payload, remote_work_dir)

        payload_json = json.dumps(adjusted_payload, indent=2)
        payload_path = f"{remote_output_dir}/runner_payload.json"
        log_path = f"{remote_output_dir}/runner.log"
        pid_path = f"{remote_output_dir}/runner.pid"
        done_path = f"{remote_output_dir}/runner.done"

        exit_code, _, _ = client.run_command(
            f"cat > {payload_path} << 'PAYLOAD_EOF'\n{payload_json}\nPAYLOAD_EOF"
        )
        if exit_code != 0:
            return False, {}, "Failed to write payload file", ""

        # Start job in background with nohup, redirect output to log file
        # Write PID to file, and touch done file when complete
        python_cmd = ".venv/bin/python3" if client.file_exists(f"{remote_work_dir}/.venv/bin/python3") else "python3"
        # Force unbuffered output so log polling sees updates during execution.
        bg_cmd = (
            f"cd {remote_work_dir} && nohup env PYTHONUNBUFFERED=1 {python_cmd} -u -m src.causal_lm_runner {payload_path} "
            f"> {log_path} 2>&1 & echo $! > {pid_path}"
        )
        exit_code, _, stderr = client.run_command(bg_cmd)
        if exit_code != 0:
            return False, {}, f"Failed to start background job: {stderr}", ""

        # Poll for completion
        logs = ""
        last_log_size = 0
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                return False, {}, f"Timeout after {timeout}s", logs

            # Check if metrics.json exists (job completed successfully)
            metrics_path = f"{remote_output_dir}/metrics.json"
            if client.file_exists(metrics_path):
                break

            # Check if process is still running
            exit_code, stdout, _ = client.run_command(
                f"cat {pid_path} 2>/dev/null && ps -p $(cat {pid_path}) > /dev/null 2>&1 && echo 'running' || echo 'stopped'"
            )
            process_status = stdout.strip().split('\n')[-1]

            # Read new log content
            if client.file_exists(log_path):
                try:
                    log_content = client.read_file(log_path)
                    if len(log_content) > last_log_size:
                        logs = log_content
                        last_log_size = len(log_content)
                        if on_log_update:
                            on_log_update(logs)
                except Exception:
                    pass

            # Sync structured training logs during execution (for UI chart/table)
            remote_training_logs = f"{remote_output_dir}/training_logs.json"
            if client.file_exists(remote_training_logs):
                try:
                    client.download_file(remote_training_logs, local_output_dir / "training_logs.json")
                except Exception:
                    pass

            # If process stopped but no metrics, it failed
            if process_status == "stopped" and not client.file_exists(metrics_path):
                error_msg = "Runner process exited without producing metrics"
                if logs:
                    # Extract error from logs
                    error_lines = [l for l in logs.split('\n') if 'error' in l.lower() or 'exception' in l.lower() or 'traceback' in l.lower()]
                    if error_lines:
                        error_msg = logs  # Return full logs as error
                return False, {}, error_msg, logs

            time.sleep(poll_interval)

        # Read final logs
        if client.file_exists(log_path):
            try:
                logs = client.read_file(log_path)
            except Exception:
                pass

        # Read metrics
        metrics_content = client.read_file(metrics_path)
        metrics = json.loads(metrics_content)

        # Download artifacts
        client.download_directory(remote_output_dir, local_output_dir)

        return True, metrics, None, logs


def run_masked_lm_remote(
    target: ComputeTarget,
    experiment_id: str,
    payload: dict,
    dataset_path: str,
    poll_interval: int = 5,
    timeout: int = 3600,
    on_log_update: callable | None = None,
) -> tuple[bool, dict, str | None, str]:
    """Run a masked LM experiment on a remote compute target.

    Args:
        target: The compute target to run on.
        experiment_id: The experiment ID.
        payload: The runner payload dictionary.
        dataset_path: Local path to the dataset file.
        poll_interval: Seconds between status checks.
        timeout: Maximum seconds to wait for completion.
        on_log_update: Optional callback called with (logs: str) when logs update.

    Returns:
        Tuple of (success, metrics_dict, error_message, logs)
    """
    with SSHClient(target) as client:
        remote_work_dir = prepare_remote_environment(
            client,
            dataset_path=dataset_path,
        )

        remote_artifacts_dir = f"{remote_work_dir}/artifacts"
        remote_output_dir = f"{remote_artifacts_dir}/masked_lm_{experiment_id}"
        client.mkdir_p(remote_output_dir)

        # Create local artifacts dir immediately so UI can read partial logs during execution
        local_output_dir = _get_repo_root() / "artifacts" / f"masked_lm_{experiment_id}"
        local_output_dir.mkdir(parents=True, exist_ok=True)

        adjusted_payload = _adjust_payload_paths(payload, remote_work_dir)

        payload_json = json.dumps(adjusted_payload, indent=2)
        payload_path = f"{remote_output_dir}/runner_payload.json"
        log_path = f"{remote_output_dir}/runner.log"
        pid_path = f"{remote_output_dir}/runner.pid"

        exit_code, _, _ = client.run_command(
            f"cat > {payload_path} << 'PAYLOAD_EOF'\n{payload_json}\nPAYLOAD_EOF"
        )
        if exit_code != 0:
            return False, {}, "Failed to write payload file", ""

        # Start job in background with nohup
        python_cmd = ".venv/bin/python3" if client.file_exists(f"{remote_work_dir}/.venv/bin/python3") else "python3"
        # Force unbuffered output so log polling sees updates during execution.
        bg_cmd = (
            f"cd {remote_work_dir} && nohup env PYTHONUNBUFFERED=1 {python_cmd} -u -m src.masked_lm_runner {payload_path} "
            f"> {log_path} 2>&1 & echo $! > {pid_path}"
        )
        exit_code, _, stderr = client.run_command(bg_cmd)
        if exit_code != 0:
            return False, {}, f"Failed to start background job: {stderr}", ""

        # Poll for completion
        logs = ""
        last_log_size = 0
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                return False, {}, f"Timeout after {timeout}s", logs

            metrics_path = f"{remote_output_dir}/metrics.json"
            if client.file_exists(metrics_path):
                break

            # Check if process is still running
            exit_code, stdout, _ = client.run_command(
                f"cat {pid_path} 2>/dev/null && ps -p $(cat {pid_path}) > /dev/null 2>&1 && echo 'running' || echo 'stopped'"
            )
            process_status = stdout.strip().split('\n')[-1]

            # Read new log content
            if client.file_exists(log_path):
                try:
                    log_content = client.read_file(log_path)
                    if len(log_content) > last_log_size:
                        logs = log_content
                        last_log_size = len(log_content)
                        if on_log_update:
                            on_log_update(logs)
                except Exception:
                    pass

            # Sync structured training logs during execution (for UI chart/table)
            remote_training_logs = f"{remote_output_dir}/training_logs.json"
            if client.file_exists(remote_training_logs):
                try:
                    client.download_file(remote_training_logs, local_output_dir / "training_logs.json")
                except Exception:
                    pass

            if process_status == "stopped" and not client.file_exists(metrics_path):
                error_msg = "Runner process exited without producing metrics"
                if logs:
                    error_msg = logs
                return False, {}, error_msg, logs

            time.sleep(poll_interval)

        # Read final logs
        if client.file_exists(log_path):
            try:
                logs = client.read_file(log_path)
            except Exception:
                pass

        metrics_content = client.read_file(metrics_path)
        metrics = json.loads(metrics_content)

        client.download_directory(remote_output_dir, local_output_dir)

        return True, metrics, None, logs


def run_experiment_remote(
    target: ComputeTarget,
    experiment_id: str,
    payload: dict,
    dataset_path: str,
    plugin_paths: list[str] | None = None,
    poll_interval: int = 5,
    timeout: int = 3600,
    on_log_update: callable | None = None,
) -> tuple[bool, dict, str | None, str]:
    """Run an experiment on a remote compute target.

    Args:
        target: The compute target to run on.
        experiment_id: The experiment ID.
        payload: The runner payload dictionary.
        dataset_path: Local path to the dataset file.
        plugin_paths: Optional list of local plugin file paths.
        poll_interval: Seconds between status checks.
        timeout: Maximum seconds to wait for completion.
        on_log_update: Optional callback called with (logs: str) when logs update.

    Returns:
        Tuple of (success, metrics_dict, error_message, logs)
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

        # Create local artifacts dir immediately so UI can read partial logs during execution
        local_output_dir = _get_repo_root() / "artifacts" / f"custom_lightning_{experiment_id}"
        local_output_dir.mkdir(parents=True, exist_ok=True)

        adjusted_payload = _adjust_payload_paths(payload, remote_work_dir)

        payload_json = json.dumps(adjusted_payload, indent=2)
        payload_path = f"{remote_output_dir}/runner_payload.json"
        log_path = f"{remote_output_dir}/runner.log"
        pid_path = f"{remote_output_dir}/runner.pid"

        exit_code, _, _ = client.run_command(
            f"cat > {payload_path} << 'PAYLOAD_EOF'\n{payload_json}\nPAYLOAD_EOF"
        )
        if exit_code != 0:
            return False, {}, "Failed to write payload file", ""

        # Start job in background with nohup
        python_cmd = ".venv/bin/python3" if client.file_exists(f"{remote_work_dir}/.venv/bin/python3") else "python3"
        # Force unbuffered output so log polling sees updates during execution.
        bg_cmd = (
            f"cd {remote_work_dir} && nohup env PYTHONUNBUFFERED=1 {python_cmd} -u -m src.custom_lightning_runner {payload_path} "
            f"> {log_path} 2>&1 & echo $! > {pid_path}"
        )
        exit_code, _, stderr = client.run_command(bg_cmd)
        if exit_code != 0:
            return False, {}, f"Failed to start background job: {stderr}", ""

        # Poll for completion
        logs = ""
        last_log_size = 0
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                return False, {}, f"Timeout after {timeout}s", logs

            metrics_path = f"{remote_output_dir}/metrics.json"
            if client.file_exists(metrics_path):
                break

            # Check if process is still running
            exit_code, stdout, _ = client.run_command(
                f"cat {pid_path} 2>/dev/null && ps -p $(cat {pid_path}) > /dev/null 2>&1 && echo 'running' || echo 'stopped'"
            )
            process_status = stdout.strip().split('\n')[-1]

            # Read new log content
            if client.file_exists(log_path):
                try:
                    log_content = client.read_file(log_path)
                    if len(log_content) > last_log_size:
                        logs = log_content
                        last_log_size = len(log_content)
                        if on_log_update:
                            on_log_update(logs)
                except Exception:
                    pass

            # Sync structured training logs + progress during execution (for UI chart/table/progress bar)
            remote_training_logs = f"{remote_output_dir}/training_logs.json"
            if client.file_exists(remote_training_logs):
                try:
                    client.download_file(remote_training_logs, local_output_dir / "training_logs.json")
                except Exception:
                    pass

            remote_progress = f"{remote_output_dir}/progress.json"
            if client.file_exists(remote_progress):
                try:
                    client.download_file(remote_progress, local_output_dir / "progress.json")
                except Exception:
                    pass

            if process_status == "stopped" and not client.file_exists(metrics_path):
                error_msg = "Runner process exited without producing metrics"
                if logs:
                    error_msg = logs
                return False, {}, error_msg, logs

            time.sleep(poll_interval)

        # Read final logs
        if client.file_exists(log_path):
            try:
                logs = client.read_file(log_path)
            except Exception:
                pass

        metrics_content = client.read_file(metrics_path)
        metrics = json.loads(metrics_content)

        client.download_directory(remote_output_dir, local_output_dir)

        return True, metrics, None, logs


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

        # Use venv python if available, otherwise use system python
        cmd = f"cd {remote_work_dir} && if [ -f .venv/bin/python3 ]; then .venv/bin/python3 -m {runner_module} {payload_path}; else python3 -m {runner_module} {payload_path}; fi"
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

        # Use venv python if available, otherwise use system python
        probe_script = f"import json; from src.probe import run_probe; payload = json.load(open('{payload_path}')); result = run_probe(payload); json.dump(result, open('{remote_probe_dir}/probe_result.json', 'w'))"
        cmd = f"cd {remote_work_dir} && if [ -f .venv/bin/python3 ]; then .venv/bin/python3 -c \"{probe_script}\"; else python3 -c \"{probe_script}\"; fi"
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

