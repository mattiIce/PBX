"""
AI-Based Call Routing
Intelligent routing using free machine learning (scikit-learn)
"""

import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from pbx.utils.logger import get_logger

# Try to import scikit-learn (free ML library)
try:
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class AICallRouting:
    """AI-powered call routing using machine learning"""

    def __init__(self, config: Any | None = None) -> None:
        """Initialize AI call routing"""
        self.logger = get_logger()
        self.config = config or {}
        self.enabled = self.config.get("features", {}).get("ai_routing", {}).get("enabled", False)

        # ML model
        self.model = None
        self.label_encoder = None
        self.feature_names = ["hour", "day_of_week", "call_duration_avg", "queue_wait_time"]

        # Training data
        self.training_data = []  # Historical routing decisions
        self.min_training_samples = 100

        # Performance tracking
        self.routing_decisions = defaultdict(list)  # destination -> outcomes

        if self.enabled and not SKLEARN_AVAILABLE:
            self.logger.warning("AI routing enabled but scikit-learn not installed")
            self.logger.info("  Install with: pip install scikit-learn numpy")
        elif self.enabled:
            self.logger.info("AI call routing initialized")
            self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize ML model"""
        if not SKLEARN_AVAILABLE:
            return

        try:
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.label_encoder = LabelEncoder()
            self.logger.info("ML model initialized (Random Forest)")
        except Exception as e:
            self.logger.error(f"Error initializing ML model: {e}")

    def record_call_outcome(self, call_data: dict) -> bool:
        """
        Record call routing outcome for training

        Args:
            call_data: Call information including routing decision and outcome
                Required: timestamp, routed_to, outcome, caller_id
                Optional: wait_time, duration, queue_id

        Returns:
            True if recorded
        """
        if not self.enabled:
            return False

        # Extract features
        timestamp = call_data.get("timestamp", datetime.now(UTC))
        features = {
            "hour": timestamp.hour,
            "day_of_week": timestamp.weekday(),
            "call_duration": call_data.get("duration", 0),
            "wait_time": call_data.get("wait_time", 0),
            "queue_id": call_data.get("queue_id", "unknown"),
            "routed_to": call_data["routed_to"],
            "outcome": call_data["outcome"],  # 'answered', 'abandoned', 'voicemail', etc.
        }

        self.training_data.append(features)

        # Track performance by destination
        self.routing_decisions[features["routed_to"]].append(
            {"outcome": features["outcome"], "timestamp": timestamp}
        )

        # Retrain model if we have enough data
        if (
            len(self.training_data) >= self.min_training_samples
            and len(self.training_data) % 50 == 0  # Retrain every 50 calls
        ):
            self._train_model()

        return True

    def _train_model(self) -> None:
        """Train the ML model on historical data"""
        if (
            not SKLEARN_AVAILABLE
            or not self.model
            or len(self.training_data) < self.min_training_samples
        ):
            return

        try:
            # Prepare features and labels
            X = []
            y = []

            for data in self.training_data[-1000:]:  # Use last 1000 samples
                features = [
                    data["hour"],
                    data["day_of_week"],
                    data["call_duration"],
                    data["wait_time"],
                ]
                X.append(features)
                y.append(data["routed_to"])

            X = np.array(X)
            y = np.array(y)

            # Encode labels
            y_encoded = self.label_encoder.fit_transform(y)

            # Train model
            self.model.fit(X, y_encoded)

            self.logger.info(f"Trained ML model on {len(X)} samples")

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error training ML model: {e}")

    def get_routing_recommendation(
        self, call_info: dict, available_destinations: list[str]
    ) -> dict:
        """
        Get AI-recommended routing destination

        Args:
            call_info: Current call information
            available_destinations: list of available destinations

        Returns:
            Routing recommendation with confidence score
        """
        if not self.enabled:
            return {
                "destination": available_destinations[0] if available_destinations else None,
                "confidence": 0.0,
                "method": "default",
            }

        # If model not trained, use rule-based routing
        if not self.model or len(self.training_data) < self.min_training_samples:
            return self._rule_based_routing(call_info, available_destinations)

        try:
            # Extract features
            timestamp = call_info.get("timestamp", datetime.now(UTC))
            features = [
                [
                    timestamp.hour,
                    timestamp.weekday(),
                    call_info.get("caller_avg_duration", 180),
                    call_info.get("current_wait_time", 0),
                ]
            ]

            # Get prediction
            prediction = self.model.predict(features)[0]
            destination = self.label_encoder.inverse_transform([prediction])[0]

            # Get confidence (probability)
            probabilities = self.model.predict_proba(features)[0]
            confidence = float(max(probabilities))

            # Check if predicted destination is available
            if destination not in available_destinations:
                # Fall back to rule-based
                return self._rule_based_routing(call_info, available_destinations)

            self.logger.debug(f"AI routing: {destination} (confidence: {confidence:.2f})")

            return {
                "destination": destination,
                "confidence": confidence,
                "method": "ml_prediction",
                "all_probabilities": dict(
                    zip(
                        self.label_encoder.classes_, [float(p) for p in probabilities], strict=False
                    )
                ),
            }

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error in ML routing: {e}")
            return self._rule_based_routing(call_info, available_destinations)

    def _rule_based_routing(self, call_info: dict, available_destinations: list[str]) -> dict:
        """Fallback rule-based routing"""
        if not available_destinations:
            return {"destination": None, "confidence": 0.0, "method": "no_destinations"}

        # Simple rule: route based on historical performance
        best_destination = available_destinations[0]
        best_score = 0.0

        for dest in available_destinations:
            outcomes = self.routing_decisions.get(dest, [])
            if outcomes:
                # Calculate success rate
                recent = list(outcomes[-100:])  # Last 100 calls
                if recent:
                    success_rate = sum(1 for o in recent if o["outcome"] == "answered") / len(
                        recent
                    )
                    if success_rate > best_score:
                        best_score = success_rate
                        best_destination = dest

        return {"destination": best_destination, "confidence": best_score, "method": "rule_based"}

    def get_destination_performance(self, destination: str, days: int = 7) -> dict:
        """Get performance metrics for a destination"""
        cutoff = datetime.now(UTC) - timedelta(days=days)

        outcomes = self.routing_decisions.get(destination, [])
        recent = [o for o in outcomes if o["timestamp"] > cutoff]

        if not recent:
            return {"destination": destination, "no_data": True}

        answered = sum(1 for o in recent if o["outcome"] == "answered")
        abandoned = sum(1 for o in recent if o["outcome"] == "abandoned")
        voicemail = sum(1 for o in recent if o["outcome"] == "voicemail")

        return {
            "destination": destination,
            "total_calls": len(recent),
            "answered": answered,
            "abandoned": abandoned,
            "voicemail": voicemail,
            "answer_rate": answered / len(recent) if recent else 0.0,
            "abandon_rate": abandoned / len(recent) if recent else 0.0,
        }

    def export_training_data(self, filename: str) -> bool:
        """Export training data to JSON file"""
        try:
            # Convert datetime to ISO format
            export_data = []
            for data in self.training_data:
                export_item = data.copy()
                if "timestamp" in export_item and isinstance(export_item["timestamp"], datetime):
                    export_item["timestamp"] = export_item["timestamp"].isoformat()
                export_data.append(export_item)

            with open(filename, "w") as f:
                json.dump(export_data, f, indent=2)

            self.logger.info(f"Exported {len(export_data)} training samples to {filename}")
            return True
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as e:
            self.logger.error(f"Error exporting training data: {e}")
            return False

    def import_training_data(self, filename: str) -> bool:
        """Import training data from JSON file"""
        try:
            with open(filename) as f:
                import_data = json.load(f)

            for item in import_data:
                if "timestamp" in item and isinstance(item["timestamp"], str):
                    item["timestamp"] = datetime.fromisoformat(item["timestamp"])
                self.training_data.append(item)

            self.logger.info(f"Imported {len(import_data)} training samples from {filename}")

            # Retrain model
            if len(self.training_data) >= self.min_training_samples:
                self._train_model()

            return True
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as e:
            self.logger.error(f"Error importing training data: {e}")
            return False

    def get_statistics(self) -> dict:
        """Get AI routing statistics"""
        model_trained = (
            self.model is not None and len(self.training_data) >= self.min_training_samples
        )

        return {
            "enabled": self.enabled,
            "sklearn_available": SKLEARN_AVAILABLE,
            "model_trained": model_trained,
            "training_samples": len(self.training_data),
            "tracked_destinations": len(self.routing_decisions),
        }
