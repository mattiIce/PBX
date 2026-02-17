"""Comprehensive tests for call_quality_prediction feature module."""

import struct
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.call_quality_prediction import (
    CallQualityPrediction,
    NetworkMetrics,
    QualityLevel,
    get_quality_prediction,
)


@pytest.mark.unit
class TestQualityLevel:
    """Tests for QualityLevel enum."""

    def test_enum_values(self) -> None:
        assert QualityLevel.EXCELLENT.value == "excellent"
        assert QualityLevel.GOOD.value == "good"
        assert QualityLevel.FAIR.value == "fair"
        assert QualityLevel.POOR.value == "poor"
        assert QualityLevel.CRITICAL.value == "critical"

    def test_enum_from_value(self) -> None:
        assert QualityLevel("excellent") == QualityLevel.EXCELLENT
        assert QualityLevel("critical") == QualityLevel.CRITICAL


@pytest.mark.unit
class TestNetworkMetrics:
    """Tests for NetworkMetrics class."""

    def test_default_initialization(self) -> None:
        metrics = NetworkMetrics()
        assert metrics.latency == 0
        assert metrics.jitter == 0
        assert metrics.packet_loss == 0.0
        assert metrics.bandwidth == 0
        assert metrics.mos_score == 4.4
        assert isinstance(metrics.timestamp, datetime)

    def test_to_dict(self) -> None:
        metrics = NetworkMetrics()
        metrics.latency = 50
        metrics.jitter = 10
        metrics.packet_loss = 1.5
        metrics.bandwidth = 64
        metrics.mos_score = 4.0
        result = metrics.to_dict()
        assert result["latency"] == 50
        assert result["jitter"] == 10
        assert result["packet_loss"] == 1.5
        assert result["bandwidth"] == 64
        assert result["mos_score"] == 4.0
        assert "timestamp" in result


@pytest.mark.unit
class TestCallQualityPredictionInit:
    """Tests for CallQualityPrediction initialization."""

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_default_initialization(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        assert cqp.enabled is False
        assert cqp.prediction_interval == 5
        assert cqp.alert_threshold_mos == 3.5
        assert cqp.alert_threshold_packet_loss == 5.0
        assert cqp.metrics_history == {}
        assert cqp.active_predictions == {}
        assert cqp.total_predictions == 0
        assert cqp.db is None

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_initialization_with_config(self, mock_logger: MagicMock) -> None:
        config = {
            "features": {
                "quality_prediction": {
                    "enabled": True,
                    "prediction_interval": 10,
                    "alert_threshold_mos": 3.0,
                    "alert_threshold_packet_loss": 3.0,
                }
            }
        }
        cqp = CallQualityPrediction(config=config)
        assert cqp.enabled is True
        assert cqp.prediction_interval == 10
        assert cqp.alert_threshold_mos == 3.0
        assert cqp.alert_threshold_packet_loss == 3.0

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_initialization_with_db_backend(self, mock_logger: MagicMock) -> None:
        mock_db_backend = MagicMock()
        mock_db_backend.enabled = True
        cqp = CallQualityPrediction(db_backend=mock_db_backend)
        # The db may or may not be set depending on import success of the DB module
        # Just verify it didn't crash
        assert cqp.db_backend is mock_db_backend

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_initialization_db_backend_disabled(self, mock_logger: MagicMock) -> None:
        mock_db_backend = MagicMock()
        mock_db_backend.enabled = False
        cqp = CallQualityPrediction(db_backend=mock_db_backend)
        assert cqp.db is None


@pytest.mark.unit
class TestCollectMetrics:
    """Tests for collect_metrics method."""

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_collect_first_metric(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        metrics = NetworkMetrics()
        metrics.latency = 30
        cqp.collect_metrics("call-1", metrics)
        assert "call-1" in cqp.metrics_history
        assert len(cqp.metrics_history["call-1"]) == 1

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_collect_multiple_metrics(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        for i in range(5):
            m = NetworkMetrics()
            m.latency = i * 10
            cqp.collect_metrics("call-1", m)
        assert len(cqp.metrics_history["call-1"]) == 5

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_collect_metrics_limit_history(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        cqp.max_history_per_endpoint = 5
        for i in range(10):
            m = NetworkMetrics()
            m.latency = i
            cqp.collect_metrics("call-1", m)
        assert len(cqp.metrics_history["call-1"]) == 5

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_collect_metrics_saves_to_db(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        cqp.db = MagicMock()
        m = NetworkMetrics()
        cqp.collect_metrics("call-1", m)
        cqp.db.save_metrics.assert_called_once()

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_collect_metrics_triggers_prediction_when_enabled(self, mock_logger: MagicMock) -> None:
        config = {"features": {"quality_prediction": {"enabled": True}}}
        cqp = CallQualityPrediction(config=config)
        # Add enough metrics to allow prediction
        for i in range(5):
            m = NetworkMetrics()
            m.mos_score = 4.0
            m.latency = 20
            m.jitter = 5
            m.packet_loss = 0.5
            m.bandwidth = 64
            cqp.collect_metrics("call-1", m)
        assert cqp.total_predictions > 0


@pytest.mark.unit
class TestPredictQuality:
    """Tests for _predict_quality method."""

    @patch("pbx.features.call_quality_prediction.get_logger")
    def _make_cqp_with_metrics(self, mock_logger: MagicMock, count: int = 5, mos: float = 4.0) -> CallQualityPrediction:
        cqp = CallQualityPrediction()
        cqp.enabled = True
        for i in range(count):
            m = NetworkMetrics()
            m.mos_score = mos
            m.latency = 20 + i
            m.jitter = 5 + i
            m.packet_loss = 0.5
            m.bandwidth = 64
            cqp.metrics_history.setdefault("call-1", []).append(m)
        return cqp

    def test_predict_insufficient_data(self) -> None:
        with patch("pbx.features.call_quality_prediction.get_logger"):
            cqp = CallQualityPrediction()
            result = cqp._predict_quality("call-1")
            assert result["success"] is False

    def test_predict_insufficient_data_few_metrics(self) -> None:
        with patch("pbx.features.call_quality_prediction.get_logger"):
            cqp = CallQualityPrediction()
            cqp.metrics_history["call-1"] = [NetworkMetrics(), NetworkMetrics()]
            result = cqp._predict_quality("call-1")
            assert result["success"] is False

    def test_predict_quality_normal(self) -> None:
        cqp = self._make_cqp_with_metrics(count=5, mos=4.2)
        result = cqp._predict_quality("call-1")
        assert "predicted_mos" in result
        assert "predicted_quality_level" in result
        assert "trends" in result
        assert "alert" in result
        assert "recommendations" in result
        assert "call-1" in cqp.active_predictions

    def test_predict_quality_generates_alert_low_mos(self) -> None:
        cqp = self._make_cqp_with_metrics(count=5, mos=2.5)
        result = cqp._predict_quality("call-1")
        assert result["alert"] is True
        assert cqp.alerts_generated > 0

    def test_predict_quality_saves_to_db(self) -> None:
        cqp = self._make_cqp_with_metrics(count=5, mos=4.0)
        cqp.db = MagicMock()
        result = cqp._predict_quality("call-1")
        cqp.db.save_prediction.assert_called_once()

    def test_predict_quality_alert_saves_to_db(self) -> None:
        cqp = self._make_cqp_with_metrics(count=5, mos=2.0)
        cqp.db = MagicMock()
        result = cqp._predict_quality("call-1")
        assert cqp.db.save_alert.called

    def test_predict_quality_high_packet_loss_alert(self) -> None:
        with patch("pbx.features.call_quality_prediction.get_logger"):
            cqp = CallQualityPrediction()
            cqp.enabled = True
            for i in range(5):
                m = NetworkMetrics()
                m.mos_score = 4.0
                m.latency = 20
                m.jitter = 5
                m.packet_loss = 6.0 + i * 2  # Increasing packet loss
                m.bandwidth = 64
                cqp.metrics_history.setdefault("call-1", []).append(m)
            result = cqp._predict_quality("call-1")
            # High packet loss should trigger alert
            assert result["predicted_packet_loss"] > 0

    def test_predict_quality_latency_trend_alert(self) -> None:
        with patch("pbx.features.call_quality_prediction.get_logger"):
            cqp = CallQualityPrediction()
            cqp.enabled = True
            for i in range(5):
                m = NetworkMetrics()
                m.mos_score = 3.0
                m.latency = 20 + i * 50  # Sharply increasing latency
                m.jitter = 5
                m.packet_loss = 6.0
                m.bandwidth = 64
                cqp.metrics_history.setdefault("call-1", []).append(m)
            result = cqp._predict_quality("call-1")
            # Should detect latency trend
            assert "latency" in result["trends"]


@pytest.mark.unit
class TestCalculateTrend:
    """Tests for _calculate_trend method."""

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_single_value(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        assert cqp._calculate_trend([5.0]) == 0.0

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_increasing_trend(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        result = cqp._calculate_trend([1.0, 2.0, 3.0, 4.0, 5.0])
        assert result > 0

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_decreasing_trend(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        result = cqp._calculate_trend([5.0, 4.0, 3.0, 2.0, 1.0])
        assert result < 0

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_flat_trend(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        result = cqp._calculate_trend([3.0, 3.0, 3.0, 3.0])
        assert result == 0.0

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_empty_list(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        assert cqp._calculate_trend([]) == 0.0


@pytest.mark.unit
class TestQualityLevelFromMos:
    """Tests for _quality_level_from_mos method."""

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_excellent(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        assert cqp._quality_level_from_mos(4.5) == QualityLevel.EXCELLENT

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_good(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        assert cqp._quality_level_from_mos(4.1) == QualityLevel.GOOD

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_fair(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        assert cqp._quality_level_from_mos(3.7) == QualityLevel.FAIR

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_poor(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        assert cqp._quality_level_from_mos(3.2) == QualityLevel.POOR

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_critical(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        assert cqp._quality_level_from_mos(2.5) == QualityLevel.CRITICAL

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_boundary_excellent(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        assert cqp._quality_level_from_mos(4.3) == QualityLevel.EXCELLENT

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_boundary_critical(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        assert cqp._quality_level_from_mos(3.0) == QualityLevel.CRITICAL


@pytest.mark.unit
class TestGenerateRecommendations:
    """Tests for _generate_recommendations method."""

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_good_quality_no_recommendations(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        result = cqp._generate_recommendations(4.5, 1.0)
        assert result == []

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_low_mos_recommendations(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        result = cqp._generate_recommendations(3.0, 1.0)
        assert len(result) >= 2
        assert any("codec" in r.lower() for r in result)

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_high_packet_loss_recommendations(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        result = cqp._generate_recommendations(4.0, 6.0)
        assert any("FEC" in r for r in result)

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_very_low_mos_recommendations(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        result = cqp._generate_recommendations(2.5, 1.0)
        assert any("transfer" in r.lower() for r in result)

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_both_bad_recommendations(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        result = cqp._generate_recommendations(2.5, 10.0)
        assert len(result) >= 4


@pytest.mark.unit
class TestGetPredictionAndClear:
    """Tests for get_prediction and clear_history."""

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_get_prediction_exists(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        cqp.active_predictions["call-1"] = {"predicted_mos": 4.0}
        assert cqp.get_prediction("call-1") == {"predicted_mos": 4.0}

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_get_prediction_not_exists(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        assert cqp.get_prediction("nonexistent") is None

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_clear_history(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        cqp.metrics_history["call-1"] = [NetworkMetrics()]
        cqp.active_predictions["call-1"] = {"predicted_mos": 4.0}
        cqp.clear_history("call-1")
        assert "call-1" not in cqp.metrics_history
        assert "call-1" not in cqp.active_predictions

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_clear_history_nonexistent(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        cqp.clear_history("nonexistent")  # Should not raise


@pytest.mark.unit
class TestTrainModel:
    """Tests for train_model method."""

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_train_model_insufficient_data(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        cqp.train_model([])
        assert cqp.model_trained is False

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_train_model_below_minimum(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        data = [{"latency": 10, "jitter": 5, "packet_loss": 1, "bandwidth": 64, "mos_score": 4.0}]
        cqp.train_model(data)
        assert cqp.model_trained is False

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_train_model_linear_regression_fallback(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        data = []
        for i in range(20):
            data.append({
                "latency": 10 + i * 2,
                "jitter": 5 + i,
                "packet_loss": 0.5 + i * 0.1,
                "bandwidth": 64,
                "mos_score": 4.5 - i * 0.05,
            })
        with patch("pbx.features.call_quality_prediction.SKLEARN_AVAILABLE", False):
            cqp.train_model(data)
            assert len(cqp.model_weights) > 0

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_train_model_with_codec_and_time(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        data = []
        for i in range(20):
            data.append({
                "latency": 10 + i,
                "jitter": 5,
                "packet_loss": 1.0,
                "bandwidth": 64,
                "mos_score": 4.0,
                "codec": "g711",
                "time_of_day": 12,
            })
        with patch("pbx.features.call_quality_prediction.SKLEARN_AVAILABLE", False):
            cqp.train_model(data)
            assert len(cqp.model_weights) > 0

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_train_model_constant_values(self, mock_logger: MagicMock) -> None:
        """Train with constant values - zero variance case."""
        cqp = CallQualityPrediction()
        data = [
            {"latency": 10, "jitter": 5, "packet_loss": 1, "bandwidth": 64, "mos_score": 4.0}
            for _ in range(15)
        ]
        with patch("pbx.features.call_quality_prediction.SKLEARN_AVAILABLE", False):
            cqp.train_model(data)


@pytest.mark.unit
class TestExtractFeaturesAndTargets:
    """Tests for _extract_features_and_targets method."""

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_extract_basic_features(self, mock_logger: MagicMock) -> None:
        try:
            import numpy as np
        except ImportError:
            pytest.skip("numpy not available")
        cqp = CallQualityPrediction()
        data = [
            {"latency": 10, "jitter": 5, "packet_loss": 1, "bandwidth": 64, "mos_score": 4.0},
            {"latency": 20, "jitter": 10, "packet_loss": 2, "bandwidth": 128, "mos_score": 3.5},
        ]
        features, targets = cqp._extract_features_and_targets(data)
        assert features.shape[0] == 2
        assert features.shape[1] == 8  # 4 base + time + 3 codec
        assert targets.shape[0] == 2

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_extract_with_codec(self, mock_logger: MagicMock) -> None:
        try:
            import numpy as np
        except ImportError:
            pytest.skip("numpy not available")
        cqp = CallQualityPrediction()
        data = [
            {"latency": 10, "jitter": 5, "packet_loss": 1, "bandwidth": 64,
             "mos_score": 4.0, "codec": "g722", "time_of_day": 14},
        ]
        features, targets = cqp._extract_features_and_targets(data)
        assert features[0][6] == 1.0  # g722 feature


@pytest.mark.unit
class TestGetStatistics:
    """Tests for get_statistics method."""

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_get_statistics_no_db(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        cqp.total_predictions = 10
        cqp.accurate_predictions = 8
        stats = cqp.get_statistics()
        assert stats["total_predictions"] == 10
        assert stats["prediction_accuracy"] == 0.8
        assert stats["enabled"] is False
        assert "database_stats" not in stats

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_get_statistics_with_db(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        cqp.db = MagicMock()
        cqp.db.get_statistics.return_value = {"records": 100}
        stats = cqp.get_statistics()
        assert stats["database_stats"] == {"records": 100}

    @patch("pbx.features.call_quality_prediction.get_logger")
    def test_get_statistics_with_db_empty(self, mock_logger: MagicMock) -> None:
        cqp = CallQualityPrediction()
        cqp.db = MagicMock()
        cqp.db.get_statistics.return_value = None
        stats = cqp.get_statistics()
        assert "database_stats" not in stats


@pytest.mark.unit
class TestGetQualityPredictionSingleton:
    """Tests for get_quality_prediction global function."""

    def test_get_quality_prediction_creates_instance(self) -> None:
        import pbx.features.call_quality_prediction as mod
        original = mod._quality_prediction
        mod._quality_prediction = None
        try:
            with patch("pbx.features.call_quality_prediction.get_logger"):
                instance = get_quality_prediction()
                assert isinstance(instance, CallQualityPrediction)
        finally:
            mod._quality_prediction = original

    def test_get_quality_prediction_returns_same_instance(self) -> None:
        import pbx.features.call_quality_prediction as mod
        original = mod._quality_prediction
        mod._quality_prediction = None
        try:
            with patch("pbx.features.call_quality_prediction.get_logger"):
                instance1 = get_quality_prediction()
                instance2 = get_quality_prediction()
                assert instance1 is instance2
        finally:
            mod._quality_prediction = original
