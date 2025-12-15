"""Gradient boosting predictor for fine-tuning performance."""
from __future__ import annotations

import json
from pathlib import Path

import lightgbm as lgb
import pandas as pd
from sklearn.model_selection import KFold

from .meta_features import MetaFeatureVector

PREDICTOR_DIR = Path("artifacts/predictor")


class PerformancePredictor:
    """LightGBM-based predictor for fine-tuning performance."""

    def __init__(self) -> None:
        self.model: lgb.Booster | None = None
        self.feature_names: list[str] = []
        self.target_name: str = ""

    def fit(
        self,
        features: list[MetaFeatureVector],
        target: str = "final_bleu_score",
        params: dict | None = None,
    ) -> dict[str, float]:
        """Train the predictor on collected meta-features.

        Args:
            features: List of MetaFeatureVector with target values set
            target: Target column name ('final_bleu_score' or 'final_eval_loss')
            params: Optional LightGBM parameters

        Returns:
            Training metrics dict
        """
        # Convert to DataFrame
        records = []
        for f in features:
            record = f.to_feature_dict()
            record[target] = getattr(f, target)
            records.append(record)

        df = pd.DataFrame(records)

        # Filter out rows without target
        df = df.dropna(subset=[target])

        if len(df) < 5:
            msg = f"Need at least 5 samples with {target} set, got {len(df)}"
            raise ValueError(msg)

        # Prepare features and target
        self.target_name = target
        self.feature_names = [c for c in df.columns if c != target]

        X = df[self.feature_names]
        y = df[target]

        # Default LightGBM parameters
        default_params = {
            "objective": "regression",
            "metric": "rmse",
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.9,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
        }
        if params:
            default_params.update(params)

        # Create dataset
        train_data = lgb.Dataset(X, label=y)

        # Train with early stopping via cv (use KFold for regression)
        n_folds = min(5, len(df))
        cv_results = lgb.cv(
            default_params,
            train_data,
            num_boost_round=1000,
            folds=KFold(n_splits=n_folds, shuffle=True, random_state=42),
            callbacks=[lgb.early_stopping(stopping_rounds=50)],
            return_cvbooster=True,
        )

        best_iteration = len(cv_results["valid rmse-mean"])

        # Train final model
        self.model = lgb.train(
            default_params,
            train_data,
            num_boost_round=best_iteration,
        )

        return {
            "best_iteration": best_iteration,
            "train_rmse": cv_results["valid rmse-mean"][-1],
            "train_rmse_std": cv_results["valid rmse-stdv"][-1],
            "num_features": len(self.feature_names),
            "num_samples": len(df),
        }

    def predict(self, features: MetaFeatureVector) -> float:
        """Predict performance for a single feature vector.

        Args:
            features: MetaFeatureVector to predict for

        Returns:
            Predicted performance value
        """
        if self.model is None:
            msg = "Model not trained. Call fit() first."
            raise RuntimeError(msg)

        feature_dict = features.to_feature_dict()
        # Ensure we have all required features in correct order
        X = pd.DataFrame([feature_dict])[self.feature_names]
        return float(self.model.predict(X)[0])

    def predict_batch(self, features: list[MetaFeatureVector]) -> list[float]:
        """Predict performance for multiple feature vectors.

        Args:
            features: List of MetaFeatureVector to predict for

        Returns:
            List of predicted performance values
        """
        if self.model is None:
            msg = "Model not trained. Call fit() first."
            raise RuntimeError(msg)

        records = [f.to_feature_dict() for f in features]
        X = pd.DataFrame(records)[self.feature_names]
        return [float(p) for p in self.model.predict(X)]

    def feature_importance(self) -> dict[str, float]:
        """Get feature importance scores.

        Returns:
            Dict mapping feature names to importance values
        """
        if self.model is None:
            msg = "Model not trained. Call fit() first."
            raise RuntimeError(msg)

        importance = self.model.feature_importance(importance_type="gain")
        return dict(zip(self.feature_names, importance, strict=False))

    def save(self, path: Path | None = None) -> Path:
        """Save the trained model to disk.

        Args:
            path: Directory to save to (default: artifacts/predictor)

        Returns:
            Path where model was saved
        """
        if self.model is None:
            msg = "Model not trained. Call fit() first."
            raise RuntimeError(msg)

        save_dir = path or PREDICTOR_DIR
        save_dir.mkdir(parents=True, exist_ok=True)

        # Save model
        model_path = save_dir / "model.txt"
        self.model.save_model(str(model_path))

        # Save metadata
        metadata = {
            "feature_names": self.feature_names,
            "target_name": self.target_name,
        }
        metadata_path = save_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2))

        return save_dir

    def load(self, path: Path | None = None) -> None:
        """Load a trained model from disk.

        Args:
            path: Directory to load from (default: artifacts/predictor)
        """
        load_dir = path or PREDICTOR_DIR

        model_path = load_dir / "model.txt"
        metadata_path = load_dir / "metadata.json"

        if not model_path.exists():
            msg = f"Model file not found: {model_path}"
            raise FileNotFoundError(msg)

        self.model = lgb.Booster(model_file=str(model_path))

        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())
            self.feature_names = metadata["feature_names"]
            self.target_name = metadata["target_name"]
        else:
            # Fallback to model's feature names
            self.feature_names = self.model.feature_name()
            self.target_name = "unknown"
