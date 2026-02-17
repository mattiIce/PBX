"""
Tests for AI-Based Call Routing

Comprehensive tests covering:
- AICallRouting initialization (enabled/disabled, sklearn present/absent)
- Model initialization and training
- Call outcome recording
- Routing recommendations (ML-based and rule-based)
- Destination performance metrics
- Training data import/export
- Statistics reporting
- Edge cases and error handling
"""

import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# We import the class but mock sklearn at various points
from pbx.features.ai_call_routing import AICallRouting


def _patch_sklearn():
    """Helper to create patches for sklearn classes that may not exist in module namespace.

    Since sklearn may not be installed, RandomForestClassifier and LabelEncoder
    may not exist as attributes on the ai_call_routing module. We use create=True
    to allow patching non-existent attributes.
    """
    return (
        patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True),
        patch("pbx.features.ai_call_routing.LabelEncoder", create=True),
    )


@pytest.mark.unit
class TestAICallRoutingInitDisabled:
    """Test AICallRouting initialization when disabled"""

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_init_no_config(self, mock_get_logger: MagicMock) -> None:
        """Initialization with no config should default to disabled"""
        router = AICallRouting()

        assert router.enabled is False
        assert router.model is None
        assert router.label_encoder is None
        assert router.training_data == []
        assert router.min_training_samples == 100

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_init_none_config(self, mock_get_logger: MagicMock) -> None:
        """Initialization with None config should default to disabled"""
        router = AICallRouting(config=None)

        assert router.enabled is False
        assert router.config == {}

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_init_empty_config(self, mock_get_logger: MagicMock) -> None:
        """Initialization with empty config should default to disabled"""
        router = AICallRouting(config={})

        assert router.enabled is False

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_init_disabled_explicitly(self, mock_get_logger: MagicMock) -> None:
        """Initialization with ai_routing disabled should not initialize model"""
        config = {"features": {"ai_routing": {"enabled": False}}}
        router = AICallRouting(config=config)

        assert router.enabled is False
        assert router.model is None

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_init_missing_features_key(self, mock_get_logger: MagicMock) -> None:
        """Config without features key should default to disabled"""
        config = {"server": {"host": "localhost"}}
        router = AICallRouting(config=config)

        assert router.enabled is False

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_init_missing_ai_routing_key(self, mock_get_logger: MagicMock) -> None:
        """Config without ai_routing key should default to disabled"""
        config = {"features": {"other_feature": True}}
        router = AICallRouting(config=config)

        assert router.enabled is False

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_init_feature_names(self, mock_get_logger: MagicMock) -> None:
        """Feature names should be initialized correctly"""
        router = AICallRouting()

        assert router.feature_names == [
            "hour",
            "day_of_week",
            "call_duration_avg",
            "queue_wait_time",
        ]

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_init_routing_decisions_is_defaultdict(self, mock_get_logger: MagicMock) -> None:
        """routing_decisions should be a defaultdict(list)"""
        router = AICallRouting()

        assert isinstance(router.routing_decisions, defaultdict)
        # Accessing a missing key should return an empty list
        assert router.routing_decisions["nonexistent"] == []


@pytest.mark.unit
class TestAICallRoutingInitEnabled:
    """Test AICallRouting initialization when enabled"""

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_init_enabled_with_sklearn(
        self,
        mock_label_encoder: MagicMock,
        mock_rf_classifier: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Enabled with sklearn should initialize ML model"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        assert router.enabled is True
        assert router.model is not None
        assert router.label_encoder is not None

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", False)
    def test_init_enabled_without_sklearn(self, mock_get_logger: MagicMock) -> None:
        """Enabled without sklearn should log warning"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        assert router.enabled is True
        assert router.model is None
        mock_logger.warning.assert_called_once()
        assert "scikit-learn" in mock_logger.warning.call_args[0][0]

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_init_enabled_logs_info(
        self,
        mock_label_encoder: MagicMock,
        mock_rf_classifier: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Enabled with sklearn should log info messages"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        config = {"features": {"ai_routing": {"enabled": True}}}
        AICallRouting(config=config)

        # Should log "AI call routing initialized" and "ML model initialized"
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("AI call routing initialized" in msg for msg in info_calls)
        assert any("ML model initialized" in msg for msg in info_calls)


@pytest.mark.unit
class TestInitializeModel:
    """Test _initialize_model method"""

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", False)
    def test_initialize_model_no_sklearn(self, mock_get_logger: MagicMock) -> None:
        """Without sklearn, model should remain None"""
        router = AICallRouting()
        router._initialize_model()

        assert router.model is None
        assert router.label_encoder is None

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_initialize_model_with_sklearn(
        self,
        mock_label_encoder: MagicMock,
        mock_rf_classifier: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """With sklearn, model and label_encoder should be created"""
        router = AICallRouting()
        router._initialize_model()

        mock_rf_classifier.assert_called_once_with(n_estimators=100, random_state=42)
        mock_label_encoder.assert_called_once()

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch(
        "pbx.features.ai_call_routing.RandomForestClassifier",
        side_effect=Exception("init error"),
        create=True,
    )
    def test_initialize_model_exception(
        self,
        mock_rf_classifier: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Exception during model initialization should be logged"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        router = AICallRouting()
        router._initialize_model()

        mock_logger.error.assert_called_once()
        assert "Error initializing ML model" in mock_logger.error.call_args[0][0]


@pytest.mark.unit
class TestRecordCallOutcome:
    """Test record_call_outcome method"""

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_record_when_disabled(self, mock_get_logger: MagicMock) -> None:
        """Recording when disabled should return False"""
        router = AICallRouting()
        result = router.record_call_outcome(
            {
                "routed_to": "ext_100",
                "outcome": "answered",
            }
        )

        assert result is False
        assert len(router.training_data) == 0

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_record_when_enabled(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Recording when enabled should return True and append data"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        result = router.record_call_outcome(
            {
                "routed_to": "ext_100",
                "outcome": "answered",
                "timestamp": datetime(2025, 6, 15, 10, 30, tzinfo=UTC),
            }
        )

        assert result is True
        assert len(router.training_data) == 1

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_record_extracts_features(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Recorded features should be extracted correctly from call_data"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        ts = datetime(2025, 3, 10, 14, 30, tzinfo=UTC)
        router.record_call_outcome(
            {
                "routed_to": "ext_200",
                "outcome": "voicemail",
                "timestamp": ts,
                "duration": 120,
                "wait_time": 15,
                "queue_id": "sales",
            }
        )

        data = router.training_data[0]
        assert data["hour"] == 14
        assert data["day_of_week"] == 0  # Monday
        assert data["call_duration"] == 120
        assert data["wait_time"] == 15
        assert data["queue_id"] == "sales"
        assert data["routed_to"] == "ext_200"
        assert data["outcome"] == "voicemail"

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_record_defaults_for_optional_fields(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Optional fields should default correctly"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        router.record_call_outcome(
            {
                "routed_to": "ext_100",
                "outcome": "answered",
            }
        )

        data = router.training_data[0]
        assert data["call_duration"] == 0
        assert data["wait_time"] == 0
        assert data["queue_id"] == "unknown"

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_record_tracks_routing_decisions(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Recording should track routing decisions per destination"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        router.record_call_outcome(
            {
                "routed_to": "ext_100",
                "outcome": "answered",
                "timestamp": datetime(2025, 6, 15, 10, 0, tzinfo=UTC),
            }
        )
        router.record_call_outcome(
            {
                "routed_to": "ext_100",
                "outcome": "abandoned",
                "timestamp": datetime(2025, 6, 15, 11, 0, tzinfo=UTC),
            }
        )
        router.record_call_outcome(
            {
                "routed_to": "ext_200",
                "outcome": "answered",
                "timestamp": datetime(2025, 6, 15, 12, 0, tzinfo=UTC),
            }
        )

        assert len(router.routing_decisions["ext_100"]) == 2
        assert len(router.routing_decisions["ext_200"]) == 1

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_record_triggers_retrain(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Recording should trigger retraining at correct intervals"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        # Mock _train_model
        router._train_model = MagicMock()

        # Add 99 samples (should not trigger retrain)
        for i in range(99):
            router.record_call_outcome(
                {
                    "routed_to": "ext_100",
                    "outcome": "answered",
                    "timestamp": datetime(2025, 6, 15, i % 24, 0, tzinfo=UTC),
                }
            )
        router._train_model.assert_not_called()

        # Add 1 more to reach 100 (should trigger since 100 >= 100 and 100 % 50 == 0)
        router.record_call_outcome(
            {
                "routed_to": "ext_100",
                "outcome": "answered",
                "timestamp": datetime(2025, 6, 15, 10, 0, tzinfo=UTC),
            }
        )
        router._train_model.assert_called_once()

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_record_does_not_retrain_at_non_interval(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Recording at 101 samples should not retrain (101 % 50 != 0)"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)
        router._train_model = MagicMock()

        for i in range(101):
            router.record_call_outcome(
                {
                    "routed_to": "ext_100",
                    "outcome": "answered",
                    "timestamp": datetime(2025, 6, 15, i % 24, 0, tzinfo=UTC),
                }
            )

        # Should have been called only once at 100
        assert router._train_model.call_count == 1


@pytest.mark.unit
class TestTrainModel:
    """Test _train_model method"""

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", False)
    def test_train_no_sklearn(self, mock_get_logger: MagicMock) -> None:
        """Training without sklearn should return early"""
        router = AICallRouting()
        router.training_data = [{"hour": 10}] * 200
        router._train_model()
        # Should not crash

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_train_insufficient_data(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Training with too few samples should return early"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)
        router.training_data = [{"hour": 10}] * 50

        # Reset the model's fit call count
        router.model.fit.reset_mock()
        router._train_model()

        router.model.fit.assert_not_called()

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.np", create=True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_train_sufficient_data(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_np: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Training with sufficient samples should call model.fit"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        # Add sufficient training data
        training_data = [
            {
                "hour": i % 24,
                "day_of_week": i % 7,
                "call_duration": 60,
                "wait_time": 5,
                "routed_to": f"ext_{i % 3}",
            }
            for i in range(150)
        ]
        router.training_data = training_data

        mock_np.array.return_value = MagicMock()
        mock_le_instance = MagicMock()
        mock_le_instance.fit_transform.return_value = MagicMock()
        router.label_encoder = mock_le_instance

        router._train_model()

        router.model.fit.assert_called_once()

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.np", create=True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_train_uses_last_1000_samples(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_np: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Training should use at most last 1000 samples"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        training_data = [
            {
                "hour": i % 24,
                "day_of_week": i % 7,
                "call_duration": 60,
                "wait_time": 5,
                "routed_to": "ext_100",
            }
            for i in range(1500)
        ]
        router.training_data = training_data

        mock_np.array.return_value = MagicMock()
        mock_le_instance = MagicMock()
        mock_le_instance.fit_transform.return_value = MagicMock()
        router.label_encoder = mock_le_instance

        router._train_model()

        # np.array should have been called with data from last 1000 samples
        assert mock_np.array.call_count >= 1

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.np", create=True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_train_handles_exception(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_np: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Training errors should be caught and logged"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        router.training_data = [
            {
                "hour": 10,
                "day_of_week": 1,
                "call_duration": 60,
                "wait_time": 5,
                "routed_to": "ext_100",
            }
        ] * 200

        mock_np.array.side_effect = ValueError("numpy error")
        router._train_model()

        mock_logger.error.assert_called()

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_train_no_model(self, mock_get_logger: MagicMock) -> None:
        """Training with no model should return early"""
        router = AICallRouting()
        router.training_data = [{"x": 1}] * 200
        router.model = None
        router._train_model()
        # Should not crash


@pytest.mark.unit
class TestGetRoutingRecommendation:
    """Test get_routing_recommendation method"""

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_recommendation_when_disabled(self, mock_get_logger: MagicMock) -> None:
        """When disabled, should return first available destination with default method"""
        router = AICallRouting()
        result = router.get_routing_recommendation(
            {"caller_id": "5551234"},
            ["ext_100", "ext_200"],
        )

        assert result["destination"] == "ext_100"
        assert result["confidence"] == 0.0
        assert result["method"] == "default"

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_recommendation_disabled_no_destinations(self, mock_get_logger: MagicMock) -> None:
        """When disabled with no destinations, should return None destination"""
        router = AICallRouting()
        result = router.get_routing_recommendation({"caller_id": "5551234"}, [])

        assert result["destination"] is None
        assert result["confidence"] == 0.0
        assert result["method"] == "default"

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_recommendation_enabled_no_training(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """When enabled but not trained, should use rule-based routing"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        result = router.get_routing_recommendation(
            {"caller_id": "5551234"},
            ["ext_100", "ext_200"],
        )

        assert result["method"] in ("rule_based", "no_destinations")

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_recommendation_ml_prediction(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """When model is trained, should use ML prediction"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        # Simulate trained model with enough data
        router.training_data = [{}] * 200

        # Configure mock model
        router.model.predict.return_value = [0]
        router.model.predict_proba.return_value = [[0.8, 0.2]]

        mock_le_instance = MagicMock()
        mock_le_instance.inverse_transform.return_value = ["ext_100"]
        mock_le_instance.classes_ = ["ext_100", "ext_200"]
        router.label_encoder = mock_le_instance

        result = router.get_routing_recommendation(
            {"caller_id": "5551234", "timestamp": datetime(2025, 6, 15, 14, 30, tzinfo=UTC)},
            ["ext_100", "ext_200"],
        )

        assert result["destination"] == "ext_100"
        assert result["confidence"] == 0.8
        assert result["method"] == "ml_prediction"
        assert "all_probabilities" in result

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_recommendation_ml_unavailable_destination(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """When ML predicts unavailable destination, should fall back to rules"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        router.training_data = [{}] * 200

        router.model.predict.return_value = [0]
        router.model.predict_proba.return_value = [[0.9, 0.1]]

        mock_le_instance = MagicMock()
        mock_le_instance.inverse_transform.return_value = ["ext_999"]  # Not available
        mock_le_instance.classes_ = ["ext_999", "ext_100"]
        router.label_encoder = mock_le_instance

        result = router.get_routing_recommendation(
            {"caller_id": "5551234"},
            ["ext_100", "ext_200"],
        )

        # Should fall back to rule-based since ext_999 not in available list
        assert result["method"] == "rule_based"

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_recommendation_ml_exception(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """ML prediction error should fall back to rule-based routing"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        router.training_data = [{}] * 200
        router.model.predict.side_effect = ValueError("prediction error")

        result = router.get_routing_recommendation(
            {"caller_id": "5551234"},
            ["ext_100", "ext_200"],
        )

        assert result["method"] == "rule_based"

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_recommendation_default_timestamp(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """When no timestamp provided, should use current UTC time"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)
        router.training_data = [{}] * 200

        router.model.predict.return_value = [0]
        router.model.predict_proba.return_value = [[0.7, 0.3]]

        mock_le_instance = MagicMock()
        mock_le_instance.inverse_transform.return_value = ["ext_100"]
        mock_le_instance.classes_ = ["ext_100", "ext_200"]
        router.label_encoder = mock_le_instance

        result = router.get_routing_recommendation(
            {"caller_id": "5551234"},
            ["ext_100", "ext_200"],
        )

        assert result["destination"] == "ext_100"

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_recommendation_default_call_info_fields(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Default values for caller_avg_duration and current_wait_time"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)
        router.training_data = [{}] * 200

        router.model.predict.return_value = [0]
        router.model.predict_proba.return_value = [[0.7, 0.3]]

        mock_le_instance = MagicMock()
        mock_le_instance.inverse_transform.return_value = ["ext_100"]
        mock_le_instance.classes_ = ["ext_100", "ext_200"]
        router.label_encoder = mock_le_instance

        # No caller_avg_duration or current_wait_time in call_info
        result = router.get_routing_recommendation(
            {},
            ["ext_100", "ext_200"],
        )

        # Should use defaults (180, 0) and not crash
        assert result is not None


@pytest.mark.unit
class TestRuleBasedRouting:
    """Test _rule_based_routing method"""

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_rule_based_no_destinations(self, mock_get_logger: MagicMock) -> None:
        """Rule-based with no destinations should return None destination"""
        router = AICallRouting()
        result = router._rule_based_routing({}, [])

        assert result["destination"] is None
        assert result["confidence"] == 0.0
        assert result["method"] == "no_destinations"

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_rule_based_single_destination_no_history(self, mock_get_logger: MagicMock) -> None:
        """Rule-based with single destination and no history returns first"""
        router = AICallRouting()
        result = router._rule_based_routing({}, ["ext_100"])

        assert result["destination"] == "ext_100"
        assert result["confidence"] == 0.0
        assert result["method"] == "rule_based"

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_rule_based_with_historical_data(self, mock_get_logger: MagicMock) -> None:
        """Rule-based should prefer destination with best success rate"""
        router = AICallRouting()

        # ext_100: 80% success (8/10 answered)
        router.routing_decisions["ext_100"] = [
            {"outcome": "answered", "timestamp": datetime.now(UTC)} for _ in range(8)
        ] + [{"outcome": "abandoned", "timestamp": datetime.now(UTC)} for _ in range(2)]

        # ext_200: 50% success (5/10 answered)
        router.routing_decisions["ext_200"] = [
            {"outcome": "answered", "timestamp": datetime.now(UTC)} for _ in range(5)
        ] + [{"outcome": "abandoned", "timestamp": datetime.now(UTC)} for _ in range(5)]

        result = router._rule_based_routing({}, ["ext_100", "ext_200"])

        assert result["destination"] == "ext_100"
        assert result["confidence"] == 0.8
        assert result["method"] == "rule_based"

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_rule_based_prefers_highest_success(self, mock_get_logger: MagicMock) -> None:
        """Rule-based should choose destination with highest answer rate"""
        router = AICallRouting()

        # ext_100: 50% success
        router.routing_decisions["ext_100"] = [
            {"outcome": "answered", "timestamp": datetime.now(UTC)},
            {"outcome": "abandoned", "timestamp": datetime.now(UTC)},
        ]

        # ext_200: 100% success
        router.routing_decisions["ext_200"] = [
            {"outcome": "answered", "timestamp": datetime.now(UTC)},
        ]

        result = router._rule_based_routing({}, ["ext_100", "ext_200"])

        assert result["destination"] == "ext_200"
        assert result["confidence"] == 1.0

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_rule_based_uses_last_100_outcomes(self, mock_get_logger: MagicMock) -> None:
        """Rule-based should only use last 100 outcomes"""
        router = AICallRouting()

        # 200 outcomes: first 150 answered, last 50 abandoned
        outcomes = [{"outcome": "answered", "timestamp": datetime.now(UTC)} for _ in range(150)] + [
            {"outcome": "abandoned", "timestamp": datetime.now(UTC)} for _ in range(50)
        ]
        router.routing_decisions["ext_100"] = outcomes

        result = router._rule_based_routing({}, ["ext_100"])

        # Last 100 outcomes: 50 answered + 50 abandoned = 50%
        assert result["destination"] == "ext_100"
        assert result["confidence"] == 0.5

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_rule_based_no_history_for_destination(self, mock_get_logger: MagicMock) -> None:
        """Destinations with no history should not affect the choice"""
        router = AICallRouting()

        # ext_100 has data; ext_200 has none
        router.routing_decisions["ext_100"] = [
            {"outcome": "answered", "timestamp": datetime.now(UTC)},
        ]

        result = router._rule_based_routing({}, ["ext_100", "ext_200"])

        assert result["destination"] == "ext_100"
        assert result["confidence"] == 1.0


@pytest.mark.unit
class TestGetDestinationPerformance:
    """Test get_destination_performance method"""

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_no_data(self, mock_get_logger: MagicMock) -> None:
        """Performance with no data should return no_data flag"""
        router = AICallRouting()
        result = router.get_destination_performance("ext_100")

        assert result["destination"] == "ext_100"
        assert result["no_data"] is True

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_no_recent_data(self, mock_get_logger: MagicMock) -> None:
        """Performance with only old data should return no_data"""
        router = AICallRouting()
        old_ts = datetime.now(UTC) - timedelta(days=30)
        router.routing_decisions["ext_100"] = [
            {"outcome": "answered", "timestamp": old_ts},
        ]

        result = router.get_destination_performance("ext_100", days=7)

        assert result["no_data"] is True

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_with_recent_data(self, mock_get_logger: MagicMock) -> None:
        """Performance with recent data should return metrics"""
        router = AICallRouting()
        recent_ts = datetime.now(UTC) - timedelta(hours=1)

        router.routing_decisions["ext_100"] = [
            {"outcome": "answered", "timestamp": recent_ts},
            {"outcome": "answered", "timestamp": recent_ts},
            {"outcome": "abandoned", "timestamp": recent_ts},
            {"outcome": "voicemail", "timestamp": recent_ts},
        ]

        result = router.get_destination_performance("ext_100", days=7)

        assert result["destination"] == "ext_100"
        assert result["total_calls"] == 4
        assert result["answered"] == 2
        assert result["abandoned"] == 1
        assert result["voicemail"] == 1
        assert result["answer_rate"] == 0.5
        assert result["abandon_rate"] == 0.25

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_custom_days_window(self, mock_get_logger: MagicMock) -> None:
        """Performance should respect custom days window"""
        router = AICallRouting()

        # 2 days ago
        two_days_ts = datetime.now(UTC) - timedelta(days=2)
        # 10 days ago
        ten_days_ts = datetime.now(UTC) - timedelta(days=10)

        router.routing_decisions["ext_100"] = [
            {"outcome": "answered", "timestamp": two_days_ts},
            {"outcome": "answered", "timestamp": ten_days_ts},
        ]

        # 3-day window: only the 2-day-old call should count
        result = router.get_destination_performance("ext_100", days=3)
        assert result["total_calls"] == 1
        assert result["answered"] == 1

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_all_answered(self, mock_get_logger: MagicMock) -> None:
        """100% answer rate should be reflected correctly"""
        router = AICallRouting()
        recent_ts = datetime.now(UTC) - timedelta(hours=1)

        router.routing_decisions["ext_100"] = [
            {"outcome": "answered", "timestamp": recent_ts} for _ in range(10)
        ]

        result = router.get_destination_performance("ext_100")
        assert result["answer_rate"] == 1.0
        assert result["abandon_rate"] == 0.0

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_all_abandoned(self, mock_get_logger: MagicMock) -> None:
        """100% abandon rate should be reflected correctly"""
        router = AICallRouting()
        recent_ts = datetime.now(UTC) - timedelta(hours=1)

        router.routing_decisions["ext_100"] = [
            {"outcome": "abandoned", "timestamp": recent_ts} for _ in range(5)
        ]

        result = router.get_destination_performance("ext_100")
        assert result["answer_rate"] == 0.0
        assert result["abandon_rate"] == 1.0


@pytest.mark.unit
class TestExportTrainingData:
    """Test export_training_data method"""

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_export_empty_data(self, mock_get_logger: MagicMock) -> None:
        """Exporting empty training data should create empty JSON array"""
        router = AICallRouting()

        with (
            patch("builtins.open", mock_open()) as mocked_file,
            patch.object(Path, "open", mocked_file),
        ):
            result = router.export_training_data("/tmp/test_export.json")

        assert result is True

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_export_with_data(self, mock_get_logger: MagicMock) -> None:
        """Exporting data should write JSON to file"""
        router = AICallRouting()
        router.training_data = [
            {"hour": 10, "day_of_week": 1, "routed_to": "ext_100", "outcome": "answered"},
            {"hour": 14, "day_of_week": 3, "routed_to": "ext_200", "outcome": "voicemail"},
        ]

        with (
            patch("builtins.open", mock_open()) as mocked_file,
            patch.object(Path, "open", mocked_file),
        ):
            result = router.export_training_data("/tmp/test_export.json")

        assert result is True

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_export_converts_datetime(self, mock_get_logger: MagicMock) -> None:
        """Export should convert datetime objects to ISO format strings"""
        router = AICallRouting()
        ts = datetime(2025, 6, 15, 10, 30, tzinfo=UTC)
        router.training_data = [
            {"hour": 10, "timestamp": ts, "routed_to": "ext_100", "outcome": "answered"},
        ]

        written_data = []

        def capture_json_dump(data, f, **kwargs):
            written_data.append(data)

        with (
            patch("builtins.open", mock_open()),
            patch.object(Path, "open", mock_open()),
            patch("json.dump", side_effect=capture_json_dump),
        ):
            result = router.export_training_data("/tmp/test_export.json")

        assert result is True
        assert len(written_data) == 1
        assert written_data[0][0]["timestamp"] == ts.isoformat()

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_export_non_datetime_timestamp(self, mock_get_logger: MagicMock) -> None:
        """Export should not convert non-datetime timestamps"""
        router = AICallRouting()
        router.training_data = [
            {"hour": 10, "timestamp": "2025-06-15", "routed_to": "ext_100", "outcome": "answered"},
        ]

        written_data = []

        def capture_json_dump(data, f, **kwargs):
            written_data.append(data)

        with (
            patch("builtins.open", mock_open()),
            patch.object(Path, "open", mock_open()),
            patch("json.dump", side_effect=capture_json_dump),
        ):
            result = router.export_training_data("/tmp/test_export.json")

        assert result is True
        # String timestamp should remain unchanged
        assert written_data[0][0]["timestamp"] == "2025-06-15"

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_export_file_error(self, mock_get_logger: MagicMock) -> None:
        """Export should return False on file error"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        router = AICallRouting()
        router.training_data = [{"hour": 10}]

        with patch.object(Path, "open", side_effect=OSError("permission denied")):
            result = router.export_training_data("/nonexistent/path/file.json")

        assert result is False
        mock_logger.error.assert_called_once()

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_export_logs_count(self, mock_get_logger: MagicMock) -> None:
        """Export should log the number of exported samples"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        router = AICallRouting()
        router.training_data = [
            {"hour": 10, "routed_to": "ext_100", "outcome": "answered"},
            {"hour": 11, "routed_to": "ext_200", "outcome": "voicemail"},
        ]

        with patch("builtins.open", mock_open()), patch.object(Path, "open", mock_open()):
            router.export_training_data("/tmp/test.json")

        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("2" in msg and "training samples" in msg.lower() for msg in info_calls)

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_export_does_not_mutate_original(self, mock_get_logger: MagicMock) -> None:
        """Export should not modify the original training_data"""
        router = AICallRouting()
        ts = datetime(2025, 6, 15, 10, 30, tzinfo=UTC)
        router.training_data = [
            {"hour": 10, "timestamp": ts, "routed_to": "ext_100", "outcome": "answered"},
        ]

        with patch("builtins.open", mock_open()), patch.object(Path, "open", mock_open()):
            router.export_training_data("/tmp/test.json")

        # Original should still have datetime, not string
        assert isinstance(router.training_data[0]["timestamp"], datetime)


@pytest.mark.unit
class TestImportTrainingData:
    """Test import_training_data method"""

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_import_empty_file(self, mock_get_logger: MagicMock) -> None:
        """Importing empty JSON array should succeed"""
        router = AICallRouting()

        with patch.object(Path, "open", mock_open(read_data="[]")):
            result = router.import_training_data("/tmp/test_import.json")

        assert result is True
        assert len(router.training_data) == 0

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_import_with_data(self, mock_get_logger: MagicMock) -> None:
        """Importing data should append to training_data"""
        router = AICallRouting()

        import_json = json.dumps(
            [
                {"hour": 10, "day_of_week": 1, "routed_to": "ext_100", "outcome": "answered"},
                {"hour": 14, "day_of_week": 3, "routed_to": "ext_200", "outcome": "voicemail"},
            ]
        )

        with patch.object(Path, "open", mock_open(read_data=import_json)):
            result = router.import_training_data("/tmp/test_import.json")

        assert result is True
        assert len(router.training_data) == 2

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_import_converts_iso_timestamp(self, mock_get_logger: MagicMock) -> None:
        """Import should convert ISO format timestamp strings to datetime"""
        router = AICallRouting()

        ts_str = "2025-06-15T10:30:00+00:00"
        import_json = json.dumps(
            [
                {"hour": 10, "timestamp": ts_str, "routed_to": "ext_100", "outcome": "answered"},
            ]
        )

        with patch.object(Path, "open", mock_open(read_data=import_json)):
            result = router.import_training_data("/tmp/test_import.json")

        assert result is True
        assert isinstance(router.training_data[0]["timestamp"], datetime)

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_import_non_string_timestamp_unchanged(self, mock_get_logger: MagicMock) -> None:
        """Import should leave non-string timestamps as-is"""
        router = AICallRouting()

        import_json = json.dumps(
            [
                {"hour": 10, "timestamp": 12345, "routed_to": "ext_100", "outcome": "answered"},
            ]
        )

        with patch.object(Path, "open", mock_open(read_data=import_json)):
            result = router.import_training_data("/tmp/test_import.json")

        assert result is True
        assert router.training_data[0]["timestamp"] == 12345

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_import_appends_to_existing(self, mock_get_logger: MagicMock) -> None:
        """Import should append to existing training data, not replace"""
        router = AICallRouting()
        router.training_data = [{"existing": True}]

        import_json = json.dumps([{"new": True}])
        with patch.object(Path, "open", mock_open(read_data=import_json)):
            result = router.import_training_data("/tmp/test.json")

        assert result is True
        assert len(router.training_data) == 2
        assert router.training_data[0] == {"existing": True}

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_import_triggers_retrain(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Import should trigger model retrain if enough data"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)
        router._train_model = MagicMock()

        # Pre-fill with 90 samples
        router.training_data = [
            {
                "hour": 10,
                "day_of_week": 1,
                "call_duration": 60,
                "wait_time": 5,
                "routed_to": "ext_100",
            }
        ] * 90

        # Import 20 more to exceed min_training_samples
        import_items = [{"hour": 10, "routed_to": "ext_100"}] * 20
        import_json = json.dumps(import_items)

        with patch.object(Path, "open", mock_open(read_data=import_json)):
            result = router.import_training_data("/tmp/test.json")

        assert result is True
        assert len(router.training_data) == 110
        router._train_model.assert_called_once()

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_import_does_not_retrain_insufficient_data(self, mock_get_logger: MagicMock) -> None:
        """Import should not retrain if total data is below threshold"""
        router = AICallRouting()
        router._train_model = MagicMock()

        import_json = json.dumps([{"hour": 10}] * 50)
        with patch.object(Path, "open", mock_open(read_data=import_json)):
            router.import_training_data("/tmp/test.json")

        router._train_model.assert_not_called()

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_import_file_not_found(self, mock_get_logger: MagicMock) -> None:
        """Import should return False when file not found"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        router = AICallRouting()
        with patch.object(Path, "open", side_effect=FileNotFoundError("not found")):
            result = router.import_training_data("/nonexistent/file.json")

        assert result is False
        mock_logger.error.assert_called_once()

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_import_invalid_json(self, mock_get_logger: MagicMock) -> None:
        """Import should return False on invalid JSON"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        router = AICallRouting()
        with patch.object(Path, "open", mock_open(read_data="not json at all")):
            result = router.import_training_data("/tmp/bad.json")

        assert result is False
        mock_logger.error.assert_called_once()

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_import_logs_count(self, mock_get_logger: MagicMock) -> None:
        """Import should log the number of imported samples"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        router = AICallRouting()
        import_json = json.dumps([{"hour": 1}, {"hour": 2}, {"hour": 3}])
        with patch.object(Path, "open", mock_open(read_data=import_json)):
            router.import_training_data("/tmp/test.json")

        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("3" in msg and "training samples" in msg.lower() for msg in info_calls)


@pytest.mark.unit
class TestGetStatistics:
    """Test get_statistics method"""

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_statistics_disabled(self, mock_get_logger: MagicMock) -> None:
        """Statistics when disabled"""
        router = AICallRouting()
        stats = router.get_statistics()

        assert stats["enabled"] is False
        assert stats["model_trained"] is False
        assert stats["training_samples"] == 0
        assert stats["tracked_destinations"] == 0

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_statistics_enabled_not_trained(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Statistics when enabled but not yet trained"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        stats = router.get_statistics()

        assert stats["enabled"] is True
        assert stats["model_trained"] is False
        assert stats["training_samples"] == 0

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_statistics_model_trained(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Statistics when model is trained"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)
        router.training_data = [{}] * 200

        stats = router.get_statistics()

        assert stats["enabled"] is True
        assert stats["model_trained"] is True
        assert stats["training_samples"] == 200

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_statistics_tracked_destinations(self, mock_get_logger: MagicMock) -> None:
        """Statistics should reflect number of tracked destinations"""
        router = AICallRouting()
        router.routing_decisions["ext_100"] = [{"outcome": "answered"}]
        router.routing_decisions["ext_200"] = [{"outcome": "abandoned"}]
        router.routing_decisions["ext_300"] = [{"outcome": "voicemail"}]

        stats = router.get_statistics()

        assert stats["tracked_destinations"] == 3

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", False)
    def test_statistics_sklearn_unavailable(self, mock_get_logger: MagicMock) -> None:
        """Statistics should reflect sklearn availability"""
        router = AICallRouting()
        stats = router.get_statistics()

        assert stats["sklearn_available"] is False

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_statistics_model_none_not_trained(self, mock_get_logger: MagicMock) -> None:
        """With model=None, model_trained should be False even with data"""
        router = AICallRouting()
        router.model = None
        router.training_data = [{}] * 200

        stats = router.get_statistics()

        assert stats["model_trained"] is False

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_statistics_below_threshold_not_trained(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """With model but insufficient data, model_trained should be False"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)
        router.training_data = [{}] * 50

        stats = router.get_statistics()

        assert stats["model_trained"] is False
        assert stats["training_samples"] == 50


@pytest.mark.unit
class TestAICallRoutingEdgeCases:
    """Test edge cases and boundary conditions"""

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_record_outcome_missing_required_keys(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Recording outcome with missing keys should raise KeyError"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)

        with pytest.raises(KeyError):
            router.record_call_outcome({"caller_id": "5551234"})

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_performance_all_voicemail(self, mock_get_logger: MagicMock) -> None:
        """Performance metrics with all voicemail outcomes"""
        router = AICallRouting()
        recent_ts = datetime.now(UTC) - timedelta(hours=1)

        router.routing_decisions["ext_100"] = [
            {"outcome": "voicemail", "timestamp": recent_ts} for _ in range(5)
        ]

        result = router.get_destination_performance("ext_100")

        assert result["total_calls"] == 5
        assert result["answered"] == 0
        assert result["abandoned"] == 0
        assert result["voicemail"] == 5
        assert result["answer_rate"] == 0.0
        assert result["abandon_rate"] == 0.0

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_recommendation_with_all_probabilities(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """ML prediction should include all_probabilities dict"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)
        router.training_data = [{}] * 200

        router.model.predict.return_value = [0]
        router.model.predict_proba.return_value = [[0.6, 0.3, 0.1]]

        mock_le_instance = MagicMock()
        mock_le_instance.inverse_transform.return_value = ["ext_100"]
        mock_le_instance.classes_ = ["ext_100", "ext_200", "ext_300"]
        router.label_encoder = mock_le_instance

        result = router.get_routing_recommendation(
            {"caller_id": "5551234"},
            ["ext_100", "ext_200", "ext_300"],
        )

        assert result["method"] == "ml_prediction"
        assert "all_probabilities" in result
        probs = result["all_probabilities"]
        assert probs["ext_100"] == 0.6
        assert probs["ext_200"] == 0.3
        assert probs["ext_300"] == 0.1

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_retrain_at_150_samples(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """Should retrain at both 100 and 150 (multiples of 50 above threshold)"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)
        router._train_model = MagicMock()

        for i in range(150):
            router.record_call_outcome(
                {
                    "routed_to": "ext_100",
                    "outcome": "answered",
                    "timestamp": datetime(2025, 6, 15, i % 24, 0, tzinfo=UTC),
                }
            )

        # Should have been called at 100 and 150
        assert router._train_model.call_count == 2

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_export_data_without_timestamp_key(self, mock_get_logger: MagicMock) -> None:
        """Export should handle data items without timestamp key"""
        router = AICallRouting()
        router.training_data = [
            {"hour": 10, "routed_to": "ext_100", "outcome": "answered"},
        ]

        written_data = []

        def capture_json_dump(data, f, **kwargs):
            written_data.append(data)

        with (
            patch("builtins.open", mock_open()),
            patch.object(Path, "open", mock_open()),
            patch("json.dump", side_effect=capture_json_dump),
        ):
            result = router.export_training_data("/tmp/test.json")

        assert result is True
        assert "timestamp" not in written_data[0][0]

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_import_data_without_timestamp_key(self, mock_get_logger: MagicMock) -> None:
        """Import should handle data items without timestamp key"""
        router = AICallRouting()

        import_json = json.dumps(
            [
                {"hour": 10, "routed_to": "ext_100", "outcome": "answered"},
            ]
        )

        with patch.object(Path, "open", mock_open(read_data=import_json)):
            result = router.import_training_data("/tmp/test.json")

        assert result is True
        assert "timestamp" not in router.training_data[0]

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_config_stored(self, mock_get_logger: MagicMock) -> None:
        """Config should be stored on instance"""
        config = {"features": {"ai_routing": {"enabled": False}}, "extra": "value"}
        router = AICallRouting(config=config)

        assert router.config is config
        assert router.config["extra"] == "value"

    @patch("pbx.features.ai_call_routing.get_logger")
    def test_performance_zero_days(self, mock_get_logger: MagicMock) -> None:
        """Performance with 0-day window should only include very recent data"""
        router = AICallRouting()
        recent_ts = datetime.now(UTC) - timedelta(hours=1)

        router.routing_decisions["ext_100"] = [
            {"outcome": "answered", "timestamp": recent_ts},
        ]

        result = router.get_destination_performance("ext_100", days=0)

        # 0-day window means cutoff is now, so hour-old data should be excluded
        assert result.get("no_data", False) is True

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_ml_prediction_type_error_fallback(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """TypeError in ML prediction should fall back to rule-based"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)
        router.training_data = [{}] * 200

        router.model.predict.side_effect = TypeError("type error")

        result = router.get_routing_recommendation(
            {"caller_id": "5551234"},
            ["ext_100"],
        )

        assert result["method"] == "rule_based"

    @patch("pbx.features.ai_call_routing.get_logger")
    @patch("pbx.features.ai_call_routing.SKLEARN_AVAILABLE", True)
    @patch("pbx.features.ai_call_routing.RandomForestClassifier", create=True)
    @patch("pbx.features.ai_call_routing.LabelEncoder", create=True)
    def test_ml_prediction_key_error_fallback(
        self,
        mock_le: MagicMock,
        mock_rf: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        """KeyError in ML prediction should fall back to rule-based"""
        config = {"features": {"ai_routing": {"enabled": True}}}
        router = AICallRouting(config=config)
        router.training_data = [{}] * 200

        router.model.predict.side_effect = KeyError("key error")

        result = router.get_routing_recommendation(
            {"caller_id": "5551234"},
            ["ext_100"],
        )

        assert result["method"] == "rule_based"
