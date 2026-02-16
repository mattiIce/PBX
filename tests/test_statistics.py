"""
Tests for Statistics and Analytics System
"""

import json
import shutil
import tempfile
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from pbx.features.cdr import CallDisposition, CDRSystem
from pbx.features.statistics import StatisticsEngine


class MockPBXCore:
    """Mock PBX core for testing"""

    def __init__(self) -> None:
        self.calls: list[Any] = []
        self.extensions: dict[str, Any] = {}
        self.start_time = datetime.now(UTC) - timedelta(hours=5)


class TestStatisticsEngine:
    """Test statistics engine functionality"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.cdr_system = CDRSystem(storage_path=self.temp_dir)
        self.stats_engine = StatisticsEngine(self.cdr_system)
        self.pbx_core = MockPBXCore()

        # Create sample call data
        self._create_sample_cdr_data()

    def teardown_method(self) -> None:
        """Clean up test fixtures"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def _create_sample_cdr_data(self) -> None:
        """Create sample CDR records for testing"""
        today = datetime.now(UTC)

        # Create CDR records for the last 3 days
        for day_offset in range(3):
            date = (today - timedelta(days=day_offset)).strftime("%Y-%m-%d")
            filename = Path(self.temp_dir) / f"cdr_{date}.jsonl"

            with open(filename, "w") as f:
                # Create 10 sample records per day
                for i in range(10):
                    record = {
                        "call_id": f"call-{day_offset}-{i}",
                        "from_extension": f"100{i % 5}",
                        "to_extension": f"200{i % 3}",
                        "start_time": (today - timedelta(days=day_offset, hours=i)).isoformat(),
                        "answer_time": (
                            (today - timedelta(days=day_offset, hours=i, minutes=1)).isoformat()
                            if i % 4 != 0
                            else None
                        ),
                        "end_time": (
                            today - timedelta(days=day_offset, hours=i, minutes=3)
                        ).isoformat(),
                        "disposition": "answered" if i % 4 != 0 else "no_answer",
                        "duration": 180.0 if i % 4 != 0 else 60.0,
                        "billsec": 120.0 if i % 4 != 0 else 0.0,
                        "recording_file": None,
                        "hangup_cause": None,
                        "user_agent": "TestPhone",
                    }
                    json.dump(record, f)
                    f.write("\n")

    def test_dashboard_statistics(self) -> None:
        """Test getting dashboard statistics"""
        stats = self.stats_engine.get_dashboard_statistics(days=3)

        # Check that all expected keys are present
        assert "overview" in stats
        assert "daily_trends" in stats
        assert "hourly_distribution" in stats
        assert "top_callers" in stats
        assert "call_disposition" in stats
        assert "peak_hours" in stats
        assert "average_metrics" in stats
        # Check overview stats
        overview = stats["overview"]
        assert overview["total_calls"] == 30  # 10 calls per day * 3 days
        assert overview["answered_calls"] > 0
        assert overview["answer_rate"] > 0

    def test_daily_trends(self) -> None:
        """Test daily trends calculation"""
        stats = self.stats_engine.get_dashboard_statistics(days=3)
        trends = stats["daily_trends"]

        # Should have 3 days of data
        assert len(trends) == 3
        # Each day should have the expected fields
        for trend in trends:
            assert "date" in trend
            assert "total_calls" in trend
            assert "answered" in trend
            assert "missed" in trend
            assert "failed" in trend

    def test_hourly_distribution(self) -> None:
        """Test hourly distribution calculation"""
        stats = self.stats_engine.get_dashboard_statistics(days=3)
        distribution = stats["hourly_distribution"]

        # Should have 24 hours
        assert len(distribution) == 24
        # Check that hours are in order
        for i, dist in enumerate(distribution):
            assert dist["hour"] == i
            assert "calls" in dist

    def test_top_callers(self) -> None:
        """Test top callers calculation"""
        stats = self.stats_engine.get_dashboard_statistics(days=3)
        top_callers = stats["top_callers"]

        # Should have some top callers
        assert len(top_callers) > 0
        # Check that callers are sorted by call count
        for i in range(len(top_callers) - 1):
            assert top_callers[i]["calls"] >= top_callers[i + 1]["calls"]

    def test_call_disposition(self) -> None:
        """Test call disposition breakdown"""
        stats = self.stats_engine.get_dashboard_statistics(days=3)
        disposition = stats["call_disposition"]

        # Should have disposition data
        assert len(disposition) > 0
        # Check that percentages add up to approximately 100
        total_percentage = sum(d["percentage"] for d in disposition)
        assert total_percentage == pytest.approx(100.0, abs=0.1)

    def test_peak_hours(self) -> None:
        """Test peak hours calculation"""
        stats = self.stats_engine.get_dashboard_statistics(days=3)
        peak_hours = stats["peak_hours"]

        # Should have up to 3 peak hours
        assert len(peak_hours) <= 3
        # Each peak hour should have hour and calls
        for peak in peak_hours:
            assert "hour" in peak
            assert "calls" in peak

    def test_average_metrics(self) -> None:
        """Test average metrics calculation"""
        stats = self.stats_engine.get_dashboard_statistics(days=3)
        avg_metrics = stats["average_metrics"]

        # Should have average metrics
        assert "avg_calls_per_day" in avg_metrics
        assert "avg_answered_per_day" in avg_metrics
        assert "avg_duration_per_day" in avg_metrics
        # Averages should be positive
        assert avg_metrics["avg_calls_per_day"] > 0

    def test_call_quality_metrics(self) -> None:
        """Test call quality metrics (placeholder)"""
        quality = self.stats_engine.get_call_quality_metrics()

        # Should have quality metrics
        assert "average_mos" in quality
        assert "average_jitter" in quality
        assert "average_packet_loss" in quality
        assert "average_latency" in quality
        assert "quality_distribution" in quality

    def test_real_time_metrics(self) -> None:
        """Test real-time metrics"""
        metrics = self.stats_engine.get_real_time_metrics(self.pbx_core)

        # Should have real-time metrics
        assert "active_calls" in metrics
        assert "registered_extensions" in metrics
        assert "system_uptime" in metrics
        assert "timestamp" in metrics
        # Uptime should be greater than 0
        assert metrics["system_uptime"] > 0

    def test_empty_data(self) -> None:
        """Test statistics with empty data"""
        # Create a new statistics engine with empty CDR
        temp_dir = tempfile.mkdtemp()
        cdr_system = CDRSystem(storage_path=temp_dir)
        stats_engine = StatisticsEngine(cdr_system)

        try:
            stats = stats_engine.get_dashboard_statistics(days=7)

            # Should not raise errors with empty data
            assert stats["overview"]["total_calls"] == 0
            assert len(stats["daily_trends"]) == 7
        finally:
            if Path(temp_dir).exists():
                shutil.rmtree(temp_dir)


class TestCDRSystem:
    """Test CDR system functionality"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.cdr_system = CDRSystem(storage_path=self.temp_dir)

    def teardown_method(self) -> None:
        """Clean up test fixtures"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_record_lifecycle(self) -> None:
        """Test CDR record lifecycle"""
        # Start a record
        record = self.cdr_system.start_record("test-call", "1001", "2001")
        assert record.call_id == "test-call"
        assert record.from_extension == "1001"
        assert record.to_extension == "2001"
        # Mark as answered
        self.cdr_system.mark_answered("test-call")
        assert record.disposition == CallDisposition.ANSWERED
        # End the record
        self.cdr_system.end_record("test-call", "normal_clearing")

        # Record should be saved and removed from active records
        assert "test-call" not in self.cdr_system.active_records

    def test_get_statistics(self) -> None:
        """Test getting CDR statistics"""
        # Create a sample record
        self.cdr_system.start_record("test-call", "1001", "2001")
        self.cdr_system.mark_answered("test-call")
        self.cdr_system.end_record("test-call")

        # Get statistics
        stats = self.cdr_system.get_statistics()

        assert stats["total_calls"] == 1
        assert stats["answered_calls"] == 1
        assert stats["answer_rate"] == 100.0
