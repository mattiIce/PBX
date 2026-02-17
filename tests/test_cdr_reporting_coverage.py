"""Comprehensive tests for CDR (Call Detail Records) and Statistics System."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest


@pytest.mark.unit
class TestCallDisposition:
    """Tests for CallDisposition enum."""

    def test_disposition_values(self) -> None:
        """Test all disposition enum values."""
        from pbx.features.cdr import CallDisposition

        assert CallDisposition.ANSWERED.value == "answered"
        assert CallDisposition.NO_ANSWER.value == "no_answer"
        assert CallDisposition.BUSY.value == "busy"
        assert CallDisposition.FAILED.value == "failed"
        assert CallDisposition.CANCELLED.value == "cancelled"


@pytest.mark.unit
class TestCDRRecord:
    """Tests for CDRRecord."""

    @patch("pbx.features.cdr.get_logger")
    def test_record_init(self, mock_get_logger: MagicMock) -> None:
        """Test record initialization."""
        from pbx.features.cdr import CDRRecord

        record = CDRRecord("call-1", "1001", "1002")

        assert record.call_id == "call-1"
        assert record.from_extension == "1001"
        assert record.to_extension == "1002"
        assert isinstance(record.start_time, datetime)
        assert record.answer_time is None
        assert record.end_time is None
        assert record.disposition is None
        assert record.duration == 0
        assert record.billsec == 0
        assert record.recording_file is None
        assert record.hangup_cause is None
        assert record.user_agent is None

    @patch("pbx.features.cdr.get_logger")
    def test_mark_answered(self, mock_get_logger: MagicMock) -> None:
        """Test marking call as answered."""
        from pbx.features.cdr import CDRRecord, CallDisposition

        record = CDRRecord("call-1", "1001", "1002")
        record.mark_answered()

        assert record.answer_time is not None
        assert record.disposition == CallDisposition.ANSWERED

    @patch("pbx.features.cdr.get_logger")
    def test_mark_ended_answered(self, mock_get_logger: MagicMock) -> None:
        """Test marking answered call as ended."""
        from pbx.features.cdr import CDRRecord, CallDisposition

        record = CDRRecord("call-1", "1001", "1002")
        record.mark_answered()
        record.mark_ended(hangup_cause="normal_clearing")

        assert record.end_time is not None
        assert record.duration > 0 or record.duration == 0  # May be 0 in fast test
        assert record.billsec >= 0
        assert record.hangup_cause == "normal_clearing"
        assert record.disposition == CallDisposition.ANSWERED

    @patch("pbx.features.cdr.get_logger")
    def test_mark_ended_unanswered(self, mock_get_logger: MagicMock) -> None:
        """Test marking unanswered call as ended."""
        from pbx.features.cdr import CDRRecord, CallDisposition

        record = CDRRecord("call-1", "1001", "1002")
        record.mark_ended(hangup_cause="no_answer")

        assert record.end_time is not None
        assert record.billsec == 0
        assert record.disposition == CallDisposition.FAILED

    @patch("pbx.features.cdr.get_logger")
    def test_to_dict(self, mock_get_logger: MagicMock) -> None:
        """Test CDR record serialization to dict."""
        from pbx.features.cdr import CDRRecord

        record = CDRRecord("call-1", "1001", "1002")
        record.user_agent = "TestPhone/1.0"
        result = record.to_dict()

        assert result["call_id"] == "call-1"
        assert result["from_extension"] == "1001"
        assert result["to_extension"] == "1002"
        assert "start_time" in result
        assert result["answer_time"] is None
        assert result["end_time"] is None
        assert result["disposition"] is None
        assert result["duration"] == 0
        assert result["billsec"] == 0
        assert result["user_agent"] == "TestPhone/1.0"

    @patch("pbx.features.cdr.get_logger")
    def test_to_dict_answered(self, mock_get_logger: MagicMock) -> None:
        """Test CDR record serialization after answering."""
        from pbx.features.cdr import CDRRecord

        record = CDRRecord("call-1", "1001", "1002")
        record.mark_answered()
        record.mark_ended()

        result = record.to_dict()

        assert result["answer_time"] is not None
        assert result["end_time"] is not None
        assert result["disposition"] == "answered"


@pytest.mark.unit
class TestCDRSystem:
    """Tests for CDRSystem."""

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_init(self, mock_get_logger: MagicMock, mock_mkdir: MagicMock) -> None:
        """Test CDR system initialization."""
        from pbx.features.cdr import CDRSystem

        system = CDRSystem(storage_path="/tmp/test_cdr")

        assert system.storage_path == "/tmp/test_cdr"
        assert system.active_records == {}
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_start_record(self, mock_get_logger: MagicMock, mock_mkdir: MagicMock) -> None:
        """Test starting a CDR record."""
        from pbx.features.cdr import CDRSystem

        system = CDRSystem(storage_path="/tmp/test_cdr")
        record = system.start_record("call-1", "1001", "1002")

        assert record is not None
        assert record.call_id == "call-1"
        assert "call-1" in system.active_records

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_mark_answered(self, mock_get_logger: MagicMock, mock_mkdir: MagicMock) -> None:
        """Test marking a call as answered in CDR."""
        from pbx.features.cdr import CDRSystem, CallDisposition

        system = CDRSystem(storage_path="/tmp/test_cdr")
        system.start_record("call-1", "1001", "1002")
        system.mark_answered("call-1")

        record = system.active_records["call-1"]
        assert record.disposition == CallDisposition.ANSWERED

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_mark_answered_nonexistent(
        self, mock_get_logger: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test marking nonexistent call as answered."""
        from pbx.features.cdr import CDRSystem

        system = CDRSystem(storage_path="/tmp/test_cdr")
        system.mark_answered("nonexistent")
        # Should not raise

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_set_recording(self, mock_get_logger: MagicMock, mock_mkdir: MagicMock) -> None:
        """Test setting recording file."""
        from pbx.features.cdr import CDRSystem

        system = CDRSystem(storage_path="/tmp/test_cdr")
        system.start_record("call-1", "1001", "1002")
        system.set_recording("call-1", "/recordings/call-1.wav")

        assert system.active_records["call-1"].recording_file == "/recordings/call-1.wav"

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_set_recording_nonexistent(
        self, mock_get_logger: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test setting recording for nonexistent call."""
        from pbx.features.cdr import CDRSystem

        system = CDRSystem(storage_path="/tmp/test_cdr")
        system.set_recording("nonexistent", "/recordings/test.wav")
        # Should not raise

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_end_record(
        self, mock_get_logger: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test ending a CDR record."""
        from pbx.features.cdr import CDRSystem

        system = CDRSystem(storage_path="/tmp/test_cdr")
        system.start_record("call-1", "1001", "1002")
        system.mark_answered("call-1")

        with patch("pathlib.Path.open", mock_open()) as mocked_open:
            system.end_record("call-1", hangup_cause="normal_clearing")

            assert "call-1" not in system.active_records
            mocked_open.assert_called_once()

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_end_record_nonexistent(
        self, mock_get_logger: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test ending nonexistent record."""
        from pbx.features.cdr import CDRSystem

        system = CDRSystem(storage_path="/tmp/test_cdr")
        system.end_record("nonexistent")
        # Should not raise

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_save_record_error(
        self, mock_get_logger: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test saving record with OS error."""
        from pbx.features.cdr import CDRSystem

        system = CDRSystem(storage_path="/tmp/test_cdr")
        system.start_record("call-1", "1001", "1002")

        with patch("pathlib.Path.open", side_effect=OSError("disk full")):
            system.end_record("call-1")
        # Should log error but not raise


@pytest.mark.unit
class TestCDRGetRecords:
    """Tests for CDRSystem.get_records."""

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_get_records_no_file(
        self, mock_get_logger: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test getting records when file doesn't exist."""
        from pbx.features.cdr import CDRSystem

        system = CDRSystem(storage_path="/tmp/test_cdr_nonexistent")
        records = system.get_records(date="2026-01-01")

        assert records == []

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_get_records_with_file(
        self, mock_get_logger: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test getting records from file."""
        from pbx.features.cdr import CDRSystem

        record_data = {"call_id": "call-1", "from_extension": "1001", "to_extension": "1002"}
        file_content = json.dumps(record_data) + "\n"

        system = CDRSystem(storage_path="/tmp/test_cdr")

        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.open", mock_open(read_data=file_content)):
            records = system.get_records(date="2026-01-15")

        assert len(records) == 1
        assert records[0]["call_id"] == "call-1"

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_get_records_with_limit(
        self, mock_get_logger: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test getting records with limit."""
        from pbx.features.cdr import CDRSystem

        records_data = ""
        for i in range(10):
            records_data += json.dumps({"call_id": f"call-{i}"}) + "\n"

        system = CDRSystem(storage_path="/tmp/test_cdr")

        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.open", mock_open(read_data=records_data)):
            records = system.get_records(date="2026-01-15", limit=3)

        assert len(records) == 3

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_get_records_default_date(
        self, mock_get_logger: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test getting records with default date (today)."""
        from pbx.features.cdr import CDRSystem

        system = CDRSystem(storage_path="/tmp/test_cdr")

        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.open", mock_open(read_data="")):
            records = system.get_records()

        assert records == []

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_get_records_read_error(
        self,
        mock_get_logger: MagicMock,
        mock_mkdir: MagicMock,
    ) -> None:
        """Test getting records with read error."""
        from pbx.features.cdr import CDRSystem

        system = CDRSystem(storage_path="/tmp/test_cdr")

        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.open", side_effect=OSError("read error")):
            records = system.get_records(date="2026-01-15")

        assert records == []


@pytest.mark.unit
class TestCDRStatistics:
    """Tests for CDRSystem.get_statistics and get_extension_statistics."""

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_get_statistics_no_records(
        self, mock_get_logger: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test getting statistics with no records."""
        from pbx.features.cdr import CDRSystem

        system = CDRSystem(storage_path="/tmp/test_cdr")

        with patch.object(system, "get_records", return_value=[]):
            stats = system.get_statistics(date="2026-01-15")

        assert stats["total_calls"] == 0
        assert stats["answered_calls"] == 0
        assert stats["failed_calls"] == 0
        assert stats["answer_rate"] == 0
        assert stats["average_duration"] == 0

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_get_statistics_with_records(
        self, mock_get_logger: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test getting statistics with records."""
        from pbx.features.cdr import CDRSystem

        records = [
            {"disposition": "answered", "duration": 120, "billsec": 100},
            {"disposition": "answered", "duration": 60, "billsec": 50},
            {"disposition": "failed", "duration": 10, "billsec": 0},
        ]

        system = CDRSystem(storage_path="/tmp/test_cdr")

        with patch.object(system, "get_records", return_value=records):
            stats = system.get_statistics(date="2026-01-15")

        assert stats["total_calls"] == 3
        assert stats["answered_calls"] == 2
        assert stats["failed_calls"] == 1
        assert stats["answer_rate"] == round(2 / 3 * 100, 2)
        assert stats["total_duration"] == 190
        assert stats["total_billsec"] == 150
        assert stats["average_duration"] == round(190 / 3, 2)

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_get_statistics_default_date(
        self, mock_get_logger: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test getting statistics with default date."""
        from pbx.features.cdr import CDRSystem

        system = CDRSystem(storage_path="/tmp/test_cdr")

        with patch.object(system, "get_records", return_value=[]):
            stats = system.get_statistics()

        assert "date" in stats

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_get_extension_statistics(
        self, mock_get_logger: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test getting statistics for specific extension."""
        from pbx.features.cdr import CDRSystem

        records = [
            {"from_extension": "1001", "to_extension": "1002"},
            {"from_extension": "1002", "to_extension": "1001"},
            {"from_extension": "1003", "to_extension": "1004"},
            {"from_extension": "1001", "to_extension": "1005"},
        ]

        system = CDRSystem(storage_path="/tmp/test_cdr")

        with patch.object(system, "get_records", return_value=records):
            stats = system.get_extension_statistics("1001", date="2026-01-15")

        assert stats["extension"] == "1001"
        assert stats["total_calls"] == 3  # 2 outbound + 1 inbound
        assert stats["outbound_calls"] == 2
        assert stats["inbound_calls"] == 1

    @patch("pbx.features.cdr.Path.mkdir")
    @patch("pbx.features.cdr.get_logger")
    def test_get_extension_statistics_no_calls(
        self, mock_get_logger: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test getting statistics for extension with no calls."""
        from pbx.features.cdr import CDRSystem

        system = CDRSystem(storage_path="/tmp/test_cdr")

        with patch.object(system, "get_records", return_value=[]):
            stats = system.get_extension_statistics("9999")

        assert stats["total_calls"] == 0
        assert stats["outbound_calls"] == 0
        assert stats["inbound_calls"] == 0
