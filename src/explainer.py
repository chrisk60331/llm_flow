"""SHAP-based explainer for performance predictions."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import shap

from .meta_features import MetaFeatureVector
from .predictor import PerformancePredictor


class PredictionExplainer:
    """SHAP-based explainer for interpreting performance predictions."""

    def __init__(self, predictor: PerformancePredictor) -> None:
        if predictor.model is None:
            msg = "Predictor model must be trained before creating explainer"
            raise ValueError(msg)
        self.predictor = predictor
        self.explainer = shap.TreeExplainer(predictor.model)

    def explain(self, features: MetaFeatureVector) -> dict[str, float]:
        """Get SHAP values for a single prediction.

        Args:
            features: MetaFeatureVector to explain

        Returns:
            Dict mapping feature names to SHAP values, sorted by absolute value
        """
        feature_dict = features.to_feature_dict()
        X = pd.DataFrame([feature_dict])[self.predictor.feature_names]

        shap_values = self.explainer.shap_values(X)

        # Create dict of feature -> shap value
        result = dict(
            zip(self.predictor.feature_names, shap_values[0], strict=False)
        )

        # Sort by absolute value
        return dict(sorted(result.items(), key=lambda x: abs(x[1]), reverse=True))

    def explain_batch(
        self, features: list[MetaFeatureVector]
    ) -> tuple[pd.DataFrame, float]:
        """Get SHAP values for multiple predictions.

        Args:
            features: List of MetaFeatureVector to explain

        Returns:
            Tuple of (DataFrame with SHAP values, expected base value)
        """
        records = [f.to_feature_dict() for f in features]
        X = pd.DataFrame(records)[self.predictor.feature_names]

        shap_values = self.explainer.shap_values(X)
        base_value = float(self.explainer.expected_value)

        shap_df = pd.DataFrame(shap_values, columns=self.predictor.feature_names)
        return shap_df, base_value

    def plot_waterfall(
        self,
        features: MetaFeatureVector,
        output_path: Path | None = None,
        title: str = "SHAP Waterfall",
    ) -> go.Figure:
        """Create a waterfall plot showing feature contributions.

        Args:
            features: MetaFeatureVector to explain
            output_path: Optional path to save the plot
            title: Plot title

        Returns:
            Plotly Figure object
        """
        explanation = self.explain(features)
        base_value = float(self.explainer.expected_value)
        prediction = self.predictor.predict(features)

        # Sort by absolute SHAP value
        sorted_features = sorted(
            explanation.items(), key=lambda x: abs(x[1]), reverse=True
        )

        # Limit to top 15 features for readability
        top_features = sorted_features[:15]

        names = [f[0] for f in top_features]
        values = [f[1] for f in top_features]

        # Calculate cumulative positions for waterfall
        cumulative = [base_value]
        for v in values:
            cumulative.append(cumulative[-1] + v)

        # Create waterfall chart
        fig = go.Figure()

        # Add bars
        colors = ["#ff6b6b" if v < 0 else "#4ecdc4" for v in values]

        for i, (name, value) in enumerate(zip(names, values, strict=False)):
            fig.add_trace(
                go.Bar(
                    x=[value],
                    y=[name],
                    orientation="h",
                    marker_color=colors[i],
                    text=f"{value:+.4f}",
                    textposition="outside",
                    showlegend=False,
                )
            )

        # Add base value annotation
        fig.add_annotation(
            x=0,
            y=len(names),
            text=f"Base: {base_value:.4f}",
            showarrow=False,
            yshift=20,
        )

        # Add prediction annotation
        fig.add_annotation(
            x=0,
            y=-1,
            text=f"Prediction: {prediction:.4f}",
            showarrow=False,
            yshift=-20,
        )

        fig.update_layout(
            title=title,
            xaxis_title="SHAP Value",
            yaxis_title="Feature",
            height=max(400, len(names) * 30),
            yaxis={"categoryorder": "array", "categoryarray": names[::-1]},
        )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(str(output_path))

        return fig

    def plot_summary(
        self,
        features: list[MetaFeatureVector],
        output_path: Path | None = None,
        title: str = "SHAP Feature Importance",
    ) -> go.Figure:
        """Create a summary plot showing overall feature importance.

        Args:
            features: List of MetaFeatureVector to analyze
            output_path: Optional path to save the plot
            title: Plot title

        Returns:
            Plotly Figure object
        """
        shap_df, _ = self.explain_batch(features)

        # Calculate mean absolute SHAP values
        mean_abs_shap = shap_df.abs().mean().sort_values(ascending=True)

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=mean_abs_shap.values,
                y=mean_abs_shap.index,
                orientation="h",
                marker_color="#667eea",
            )
        )

        fig.update_layout(
            title=title,
            xaxis_title="Mean |SHAP Value|",
            yaxis_title="Feature",
            height=max(400, len(mean_abs_shap) * 25),
        )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(str(output_path))

        return fig

    def get_top_drivers(
        self, features: MetaFeatureVector, n: int = 5
    ) -> list[dict[str, str | float]]:
        """Get top N features driving the prediction.

        Args:
            features: MetaFeatureVector to explain
            n: Number of top features to return

        Returns:
            List of dicts with feature name, value, shap_value, and direction
        """
        explanation = self.explain(features)
        feature_dict = features.to_feature_dict()

        top_features = list(explanation.items())[:n]

        results = []
        for name, shap_value in top_features:
            results.append(
                {
                    "feature": name,
                    "value": feature_dict.get(name),
                    "shap_value": shap_value,
                    "direction": "positive" if shap_value > 0 else "negative",
                }
            )

        return results
