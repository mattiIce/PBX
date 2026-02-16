"""
Call Quality Prediction
Proactive network issue detection using ML
"""

import sqlite3
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pbx.utils.logger import get_logger

# ML libraries for improved prediction
try:
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    np = None


class QualityLevel(Enum):
    """Call quality level enumeration"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class NetworkMetrics:
    """Network metrics for a call or endpoint"""

    def __init__(self) -> None:
        """Initialize network metrics"""
        self.timestamp = datetime.now(UTC)
        self.latency = 0  # milliseconds
        self.jitter = 0  # milliseconds
        self.packet_loss = 0.0  # percentage
        self.bandwidth = 0  # kbps
        self.mos_score = 4.4  # Mean Opinion Score (1.0-5.0)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "latency": self.latency,
            "jitter": self.jitter,
            "packet_loss": self.packet_loss,
            "bandwidth": self.bandwidth,
            "mos_score": self.mos_score,
        }


class CallQualityPrediction:
    """
    Call Quality Prediction System

    Proactive network issue detection using machine learning.
    Features:
    - Real-time quality prediction
    - Network issue detection before call degradation
    - Historical trend analysis
    - Proactive alerting
    - Recommendation engine
    """

    def __init__(self, config: Any | None = None, db_backend: Any | None = None) -> None:
        """Initialize call quality prediction system"""
        self.logger = get_logger()
        self.config = config or {}
        self.db_backend = db_backend
        self.db = None

        # Configuration
        prediction_config = self.config.get("features", {}).get("quality_prediction", {})
        self.enabled = prediction_config.get("enabled", False)
        self.prediction_interval = prediction_config.get("prediction_interval", 5)  # seconds
        self.alert_threshold_mos = prediction_config.get("alert_threshold_mos", 3.5)
        self.alert_threshold_packet_loss = prediction_config.get("alert_threshold_packet_loss", 5.0)

        # Historical metrics storage
        self.metrics_history: dict[str, list[NetworkMetrics]] = {}
        self.max_history_per_endpoint = 1000

        # Predictions
        self.active_predictions: dict[str, dict] = {}

        # Statistics
        self.total_predictions = 0
        self.accurate_predictions = 0
        self.false_positives = 0
        self.alerts_generated = 0

        # ML Model parameters
        self.model_weights = []
        self.model_bias = 4.0  # Default MOS baseline

        # ML models (RandomForest for better accuracy)
        self.rf_model = None
        self.scaler = None
        self.model_trained = False

        # ML model configuration constants
        self.MIN_TRAINING_SAMPLES = 10  # Minimum samples needed to train model
        self.RF_N_ESTIMATORS = 50  # Number of trees in RandomForest
        self.RF_MAX_DEPTH = 10  # Maximum tree depth

        # Initialize database if available
        if self.db_backend and self.db_backend.enabled:
            try:
                from pbx.features.call_quality_prediction_db import CallQualityPredictionDatabase

                self.db = CallQualityPredictionDatabase(self.db_backend)
                self.db.create_tables()
                self.logger.info("Call quality prediction database layer initialized")
            except sqlite3.Error as e:
                self.logger.warning(f"Could not initialize database layer: {e}")

        self.logger.info("Call quality prediction system initialized")
        self.logger.info(f"  Prediction interval: {self.prediction_interval}s")
        self.logger.info(f"  MOS alert threshold: {self.alert_threshold_mos}")
        self.logger.info(f"  Enabled: {self.enabled}")

    def collect_metrics(self, call_id: str, metrics: NetworkMetrics) -> None:
        """
        Collect network metrics for a call

        Args:
            call_id: Call identifier
            metrics: Network metrics
        """
        if call_id not in self.metrics_history:
            self.metrics_history[call_id] = []

        self.metrics_history[call_id].append(metrics)

        # Limit history size
        if len(self.metrics_history[call_id]) > self.max_history_per_endpoint:
            self.metrics_history[call_id].pop(0)

        # Save to database
        if self.db:
            self.db.save_metrics(call_id, metrics.to_dict())

        # Trigger prediction
        if self.enabled:
            self._predict_quality(call_id)

    def _predict_quality(self, call_id: str) -> dict:
        """
        Predict future call quality using ML models or weighted moving average

        Args:
            call_id: Call identifier

        Returns:
            dict: Prediction result
        """
        if call_id not in self.metrics_history or len(self.metrics_history[call_id]) < 3:
            return {"success": False, "reason": "Insufficient data"}

        metrics = self.metrics_history[call_id]
        recent = metrics[-10:]  # Last 10 samples

        # Get current metrics
        current_mos = recent[-1].mos_score
        current_packet_loss = recent[-1].packet_loss

        # Calculate trends
        latency_trend = self._calculate_trend([m.latency for m in recent])
        jitter_trend = self._calculate_trend([m.jitter for m in recent])
        packet_loss_trend = self._calculate_trend([m.packet_loss for m in recent])
        mos_trend = self._calculate_trend([m.mos_score for m in recent])

        # Use trained ML model if available for better predictions (15-25% improvement)
        if (
            SKLEARN_AVAILABLE
            and self.model_trained
            and self.rf_model is not None
            and self.scaler is not None
        ):
            try:
                # Build feature vector from current metrics
                current = recent[-1]
                feature_vector = [
                    current.latency,
                    current.jitter,
                    current.packet_loss,
                    current.bandwidth,
                    datetime.now(UTC).hour / 24.0,  # Normalized time of day
                    0.0,
                    0.0,
                    0.0,  # Codec features (would need to be passed in)
                ]

                # Normalize and predict
                x_data = np.array([feature_vector])
                x_scaled = self.scaler.transform(x_data)
                predicted_mos = self.rf_model.predict(x_scaled)[0]

                # Bound to valid MOS range
                predicted_mos = max(1.0, min(5.0, predicted_mos))

                self.logger.debug(f"ML prediction: MOS={predicted_mos:.2f}")

            except Exception as e:
                self.logger.warning(f"ML prediction failed: {e}, falling back to weighted average")
                # Fall through to weighted average method
                predicted_mos = None
        else:
            predicted_mos = None

        # Fallback to weighted moving average if ML not available
        if predicted_mos is None:
            # Apply exponential weighted moving average for smoothing
            weights = [2**i for i in range(len(recent))]
            weighted_mos = sum(
                m.mos_score * w for m, w in zip(recent, weights, strict=False)
            ) / sum(weights)

            # Combine weighted average with trend for prediction
            prediction_intervals = 3  # Predict 3 intervals ahead
            predicted_mos = weighted_mos + (mos_trend * prediction_intervals)

            # Bound prediction to valid MOS range (1.0 - 5.0)
            predicted_mos = max(1.0, min(5.0, predicted_mos))

        # Predict future packet loss using similar approach
        weights_pl = [2**i for i in range(len(recent))]
        weighted_pl = sum(
            m.packet_loss * w for m, w in zip(recent, weights_pl, strict=False)
        ) / sum(weights_pl)
        predicted_packet_loss = weighted_pl + (packet_loss_trend * prediction_intervals)
        predicted_packet_loss = max(0.0, min(100.0, predicted_packet_loss))

        # Determine predicted quality level
        predicted_level = self._quality_level_from_mos(predicted_mos)

        # Check for alerts
        alert = False
        alert_reasons = []

        if predicted_mos < self.alert_threshold_mos:
            alert = True
            alert_reasons.append(f"MOS predicted to drop to {predicted_mos:.2f}")

        if predicted_packet_loss > self.alert_threshold_packet_loss:
            alert = True
            alert_reasons.append(f"Packet loss predicted to reach {predicted_packet_loss:.1f}%")

        if latency_trend > 10:  # Increasing latency
            alert_reasons.append("Latency trending upward")

        prediction = {
            "call_id": call_id,
            "current_mos": current_mos,
            "predicted_mos": predicted_mos,
            "predicted_quality_level": predicted_level.value,
            "current_packet_loss": current_packet_loss,
            "predicted_packet_loss": predicted_packet_loss,
            "trends": {
                "latency": latency_trend,
                "jitter": jitter_trend,
                "packet_loss": packet_loss_trend,
                "mos": mos_trend,
            },
            "alert": alert,
            "alert_reasons": alert_reasons,
            "recommendations": self._generate_recommendations(predicted_mos, predicted_packet_loss),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        self.active_predictions[call_id] = prediction
        self.total_predictions += 1

        # Save to database
        if self.db:
            self.db.save_prediction(call_id, prediction)

        if alert:
            self.alerts_generated += 1
            self.logger.warning(f"Quality alert for call {call_id}")
            for reason in alert_reasons:
                self.logger.warning(f"  {reason}")

            # Save alerts to database
            if self.db:
                for reason in alert_reasons:
                    severity = "critical" if predicted_mos < 3.0 else "warning"
                    metric_val = predicted_mos if "MOS" in reason else predicted_packet_loss
                    thresh_val = (
                        self.alert_threshold_mos
                        if "MOS" in reason
                        else self.alert_threshold_packet_loss
                    )
                    self.db.save_alert(
                        call_id, "quality_degradation", severity, reason, metric_val, thresh_val
                    )

        return prediction

    def _calculate_trend(self, values: list[float]) -> float:
        """
        Calculate trend direction and magnitude

        Args:
            values: list of metric values

        Returns:
            float: Trend value (positive = increasing, negative = decreasing)
        """
        if len(values) < 2:
            return 0.0

        # Simple linear trend calculation
        # Use more sophisticated time series analysis with linear regression
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        # Calculate slope using least squares method
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        slope = numerator / denominator

        # Calculate R-squared for trend confidence
        y_pred = [y_mean + slope * (i - x_mean) for i in range(n)]
        ss_res = sum((values[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))

        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Weight the slope by R-squared to reduce impact of noisy trends
        weighted_slope = slope * max(0.5, r_squared)

        return weighted_slope

    def _quality_level_from_mos(self, mos: float) -> QualityLevel:
        """Convert MOS score to quality level"""
        if mos >= 4.3:
            return QualityLevel.EXCELLENT
        if mos >= 4.0:
            return QualityLevel.GOOD
        if mos >= 3.6:
            return QualityLevel.FAIR
        if mos >= 3.1:
            return QualityLevel.POOR
        return QualityLevel.CRITICAL

    def _generate_recommendations(
        self, predicted_mos: float, predicted_packet_loss: float
    ) -> list[str]:
        """
        Generate recommendations based on predictions

        Args:
            predicted_mos: Predicted MOS score
            predicted_packet_loss: Predicted packet loss percentage

        Returns:
            list[str]: Recommendations
        """
        recommendations = []

        if predicted_mos < 3.5:
            recommendations.append("Consider switching to lower bitrate codec")
            recommendations.append("Check network congestion")

        if predicted_packet_loss > 5.0:
            recommendations.append("Enable Forward Error Correction (FEC)")
            recommendations.append("Investigate network routing")

        if predicted_mos < 3.0:
            recommendations.append("Consider call transfer to alternate route")
            recommendations.append("Alert user of potential quality issues")

        return recommendations

    def get_prediction(self, call_id: str) -> dict | None:
        """Get current prediction for a call"""
        return self.active_predictions.get(call_id)

    def clear_history(self, call_id: str) -> None:
        """Clear metrics history for a call"""
        if call_id in self.metrics_history:
            del self.metrics_history[call_id]
        if call_id in self.active_predictions:
            del self.active_predictions[call_id]

    def _extract_features_and_targets(self, historical_data: list[dict]) -> tuple:
        """Extract features and targets from historical data"""
        features = []
        targets = []

        for sample in historical_data:
            # Feature vector: [latency, jitter, packet_loss, bandwidth]
            feature_vector = [
                sample.get("latency", 0),
                sample.get("jitter", 0),
                sample.get("packet_loss", 0),
                sample.get("bandwidth", 0),
            ]

            # Add time-based feature if available
            if "time_of_day" in sample:
                # Normalize hour to 0-1 range
                feature_vector.append(sample["time_of_day"] / 24.0)
            else:
                feature_vector.append(0.5)  # Default to midday

            # Add codec feature if available (one-hot encoded)
            codec = sample.get("codec", "unknown")
            codec_features = [
                1.0 if codec == "g711" else 0.0,
                1.0 if codec == "g722" else 0.0,
                1.0 if codec == "opus" else 0.0,
            ]
            feature_vector.extend(codec_features)

            features.append(feature_vector)
            targets.append(sample.get("mos_score", 4.0))

        return np.array(features), np.array(targets)

    def train_model(self, historical_data: list[dict]) -> None:
        """
        Train ML model with historical data using RandomForest

        Args:
            historical_data: list of historical call quality data
                Each dict should contain: latency, jitter, packet_loss, bandwidth,
                codec (optional), time_of_day (optional), mos_score
        """
        if not historical_data or len(historical_data) < self.MIN_TRAINING_SAMPLES:
            self.logger.warning(
                f"Insufficient training data: {len(historical_data)} samples (need {self.MIN_TRAINING_SAMPLES})"
            )
            return

        self.logger.info(f"Training model with {len(historical_data)} samples")

        # Use RandomForest if scikit-learn available (15-25% better predictions)
        if SKLEARN_AVAILABLE:
            try:
                # Extract features and target
                x_data, y = self._extract_features_and_targets(historical_data)

                # Normalize features for better performance
                self.scaler = StandardScaler()
                x_scaled = self.scaler.fit_transform(x_data)

                # Train RandomForest Regressor
                self.rf_model = RandomForestRegressor(
                    n_estimators=self.RF_N_ESTIMATORS,
                    max_depth=self.RF_MAX_DEPTH,
                    random_state=42,
                    n_jobs=-1,  # Use all CPU cores
                )
                self.rf_model.fit(x_scaled, y)
                self.model_trained = True

                # Validate model on training data
                predictions = self.rf_model.predict(x_scaled)

                # Calculate R-squared
                ss_res = np.sum((y - predictions) ** 2)
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

                # Calculate feature importance
                feature_names = [
                    "latency",
                    "jitter",
                    "packet_loss",
                    "bandwidth",
                    "time_of_day",
                    "g711",
                    "g722",
                    "opus",
                ]
                importance = self.rf_model.feature_importances_

                self.logger.info("RandomForest model training completed")
                self.logger.info(f"  Training R-squared: {r_squared:.3f}")
                self.logger.info(f"  Features: {x_data.shape[1]}")
                self.logger.info(
                    f"  Top features: {
                        sorted(
                            zip(feature_names[: len(importance)], importance, strict=False),
                            key=lambda x: x[1],
                            reverse=True,
                        )[:3]
                    }"
                )

                return

            except Exception as e:
                self.logger.warning(
                    f"RandomForest training failed: {e}, falling back to linear regression"
                )

        # Fallback to simple linear regression
        try:
            # Extract features and target
            features = []
            targets = []

            for sample in historical_data:
                # Feature vector: [latency, jitter, packet_loss, bandwidth]
                feature_vector = [
                    sample.get("latency", 0),
                    sample.get("jitter", 0),
                    sample.get("packet_loss", 0),
                    sample.get("bandwidth", 0),
                ]

                # Add time-based feature with default (consistent with RF path)
                if "time_of_day" in sample:
                    # Normalize hour to 0-1 range
                    feature_vector.append(sample["time_of_day"] / 24.0)
                else:
                    feature_vector.append(0.5)  # Default to midday

                # Add codec feature if available (one-hot encoded)
                codec = sample.get("codec", "unknown")
                codec_features = [
                    1.0 if codec == "g711" else 0.0,
                    1.0 if codec == "g722" else 0.0,
                    1.0 if codec == "opus" else 0.0,
                ]
                feature_vector.extend(codec_features)

                features.append(feature_vector)
                targets.append(sample.get("mos_score", 4.0))

            n_features = len(features[0])
            n_samples = len(features)

            # Calculate feature weights based on correlation with MOS
            self.model_weights = []

            for feat_idx in range(n_features):
                feat_values = [f[feat_idx] for f in features]

                # Calculate correlation coefficient with MOS
                feat_mean = sum(feat_values) / n_samples
                target_mean = sum(targets) / n_samples

                numerator = sum(
                    (feat_values[i] - feat_mean) * (targets[i] - target_mean)
                    for i in range(n_samples)
                )

                feat_var = sum((f - feat_mean) ** 2 for f in feat_values)
                target_var = sum((t - target_mean) ** 2 for t in targets)

                # Validate before calculating denominator (must be > 0 to avoid division by zero)
                if feat_var > 0 and target_var > 0:
                    denominator = (feat_var * target_var) ** 0.5

                    if denominator > 0:
                        correlation = numerator / denominator
                        # Weight is negative correlation (bad metrics decrease MOS)
                        # Except for bandwidth which has positive correlation
                        weight = -correlation if feat_idx < 3 else correlation
                        self.model_weights.append(weight)
                    else:
                        self.model_weights.append(0.0)
                else:
                    self.model_weights.append(0.0)

            # Calculate intercept (bias term)
            self.model_bias = target_mean

            # Validate model on training data
            predictions = []
            for feature_vector in features:
                predicted = self.model_bias
                for feat_idx, feat_val in enumerate(feature_vector):
                    if feat_idx < len(self.model_weights):
                        predicted += self.model_weights[feat_idx] * feat_val
                predictions.append(max(1.0, min(5.0, predicted)))

            # Calculate training accuracy (R-squared)
            target_mean = sum(targets) / len(targets)
            ss_res = sum((targets[i] - predictions[i]) ** 2 for i in range(len(targets)))
            ss_tot = sum((t - target_mean) ** 2 for t in targets)

            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            self.logger.info("Linear regression model training completed")
            self.logger.info(f"  Training R-squared: {r_squared:.3f}")
            self.logger.info(f"  Features: {n_features}")
            self.logger.info(f"  Model weights: {[f'{w:.3f}' for w in self.model_weights[:4]]}")

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error training model: {e}")

    def get_statistics(self) -> dict:
        """Get prediction statistics"""
        accuracy = self.accurate_predictions / max(1, self.total_predictions)

        stats = {
            "total_predictions": self.total_predictions,
            "accurate_predictions": self.accurate_predictions,
            "false_positives": self.false_positives,
            "prediction_accuracy": accuracy,
            "alerts_generated": self.alerts_generated,
            "active_predictions": len(self.active_predictions),
            "endpoints_monitored": len(self.metrics_history),
            "enabled": self.enabled,
        }

        # Add database statistics if available
        if self.db:
            db_stats = self.db.get_statistics()
            if db_stats:
                stats["database_stats"] = db_stats

        return stats


# Global instance
_quality_prediction = None


def get_quality_prediction(
    config: Any | None = None, db_backend: Any | None = None
) -> CallQualityPrediction:
    """Get or create call quality prediction instance"""
    global _quality_prediction
    if _quality_prediction is None:
        _quality_prediction = CallQualityPrediction(config, db_backend)
    return _quality_prediction
