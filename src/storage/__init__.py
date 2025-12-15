"""Storage operations for persistent data."""
from .benchmark_store import (
    delete_benchmark,
    delete_benchmark_eval,
    get_benchmark,
    get_benchmark_eval,
    list_benchmark_evals,
    list_benchmark_evals_by_benchmark,
    list_benchmarks,
    save_benchmark,
    save_benchmark_eval,
)
from .config_store import (
    config_name_exists,
    delete_config,
    get_config,
    get_config_by_name,
    list_configs,
    list_configs_with_metrics,
    save_config,
)
from .database import get_connection, init_db
from .dataset_store import delete_dataset, get_dataset, list_datasets, save_dataset
from .experiment_store import delete_experiment, get_experiment, list_experiments, save_experiment
from .job_store import (
    OptimizationJob,
    OptimizationStatus,
    delete_autotune_job,
    get_autotune_job,
    get_optimization_job,
    list_autotune_jobs,
    list_optimization_jobs,
    save_autotune_job,
    save_optimization_job,
)
from .meta_store import delete_meta_features, get_meta_features, list_meta_features, save_meta_features

__all__ = [
    # Database
    "get_connection",
    "init_db",
    # Dataset
    "delete_dataset",
    "get_dataset",
    "list_datasets",
    "save_dataset",
    # Config
    "config_name_exists",
    "delete_config",
    "get_config",
    "get_config_by_name",
    "list_configs",
    "list_configs_with_metrics",
    "save_config",
    # Experiment
    "delete_experiment",
    "get_experiment",
    "list_experiments",
    "save_experiment",
    # Benchmark
    "delete_benchmark",
    "delete_benchmark_eval",
    "get_benchmark",
    "get_benchmark_eval",
    "list_benchmark_evals",
    "list_benchmark_evals_by_benchmark",
    "list_benchmarks",
    "save_benchmark",
    "save_benchmark_eval",
    # Meta
    "delete_meta_features",
    "get_meta_features",
    "list_meta_features",
    "save_meta_features",
    # Jobs
    "OptimizationJob",
    "OptimizationStatus",
    "delete_autotune_job",
    "get_autotune_job",
    "get_optimization_job",
    "list_autotune_jobs",
    "list_optimization_jobs",
    "save_autotune_job",
    "save_optimization_job",
]

from .plugin_store import delete_plugin, get_plugin, list_plugins, save_plugin

__all__.extend(
    [
        # Plugins
        "save_plugin",
        "get_plugin",
        "list_plugins",
        "delete_plugin",
    ]
)

