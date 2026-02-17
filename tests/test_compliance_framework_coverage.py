#!/usr/bin/env python3
"""
Comprehensive tests for Compliance Framework (pbx/features/compliance_framework.py)
Covers SOC2ComplianceEngine (the only active/non-commented class).
"""

import sqlite3
from unittest.mock import MagicMock, call, patch

import pytest


@pytest.mark.unit
class TestSOC2ComplianceEngineInit:
    """Tests for SOC2ComplianceEngine initialization"""

    def _make_engine(self, config=None, db_type="sqlite"):
        """Helper to create engine with mock db"""
        mock_db = MagicMock()
        mock_db.db_type = db_type
        mock_db.fetch_one.return_value = None  # controls don't exist yet
        if config is None:
            config = {"soc2.enabled": True}

        with patch("pbx.features.compliance_framework.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.compliance_framework import SOC2ComplianceEngine

            engine = SOC2ComplianceEngine(mock_db, config)
        return engine

    def test_init_enabled(self) -> None:
        """Test initialization with SOC2 enabled"""
        engine = self._make_engine(config={"soc2.enabled": True})

        assert engine.enabled is True
        assert engine.db is not None

    def test_init_default_enabled(self) -> None:
        """Test initialization defaults to enabled"""
        engine = self._make_engine(config={})

        assert engine.enabled is True

    def test_init_disabled(self) -> None:
        """Test initialization with SOC2 disabled"""
        engine = self._make_engine(config={"soc2.enabled": False})

        assert engine.enabled is False

    def test_init_logs_message(self) -> None:
        """Test that init logs initialization message"""
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.fetch_one.return_value = None
        config = {}

        with patch("pbx.features.compliance_framework.get_logger") as mock_logger_fn:
            mock_logger = MagicMock()
            mock_logger_fn.return_value = mock_logger
            from pbx.features.compliance_framework import SOC2ComplianceEngine

            SOC2ComplianceEngine(mock_db, config)

        mock_logger.info.assert_any_call("SOC 2 type II Compliance Framework initialized")

    def test_init_registers_default_controls(self) -> None:
        """Test that init registers default SOC2 controls"""
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.fetch_one.return_value = None  # controls don't exist yet

        config = {"soc2.enabled": True}

        with patch("pbx.features.compliance_framework.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.compliance_framework import SOC2ComplianceEngine

            _engine = SOC2ComplianceEngine(mock_db, config)

        # Should have called execute for each default control INSERT
        # 16 default controls, each calls fetch_one + execute (insert)
        assert mock_db.fetch_one.call_count == 16
        assert mock_db.execute.call_count == 16

    def test_init_default_controls_already_exist(self) -> None:
        """Test that existing controls are updated rather than inserted"""
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.fetch_one.return_value = (1,)  # controls already exist

        config = {}

        with patch("pbx.features.compliance_framework.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.compliance_framework import SOC2ComplianceEngine

            SOC2ComplianceEngine(mock_db, config)

        # All controls exist so they should be updated
        assert mock_db.execute.call_count == 16

    def test_init_control_registration_exception_handled(self) -> None:
        """Test that exception during control registration is handled gracefully"""
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.fetch_one.side_effect = Exception("db connection lost")

        config = {}

        with patch("pbx.features.compliance_framework.get_logger") as mock_logger_fn:
            mock_logger = MagicMock()
            mock_logger_fn.return_value = mock_logger
            from pbx.features.compliance_framework import SOC2ComplianceEngine

            # Should not raise
            engine = SOC2ComplianceEngine(mock_db, config)

        assert engine is not None
        # Should log debug for each failed control registration
        assert mock_logger.debug.call_count == 16


@pytest.mark.unit
class TestSOC2ComplianceEngineRegisterControl:
    """Tests for SOC2ComplianceEngine.register_control"""

    def _make_engine(self):
        """Helper to create engine with mock db, skipping default control init"""
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.fetch_one.return_value = None

        config = {"soc2.enabled": True}

        with patch("pbx.features.compliance_framework.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.compliance_framework import SOC2ComplianceEngine

            engine = SOC2ComplianceEngine(mock_db, config)

        # Reset mocks after init to isolate test calls
        mock_db.reset_mock()
        return engine

    def test_register_new_control_sqlite(self) -> None:
        """Test registering a new control (INSERT) with sqlite"""
        engine = self._make_engine()
        engine.db.fetch_one.return_value = None  # control doesn't exist

        control_data = {
            "control_id": "TEST1",
            "control_category": "Security",
            "description": "Test control",
            "implementation_status": "implemented",
        }

        result = engine.register_control(control_data)

        assert result is True
        engine.db.fetch_one.assert_called_once()
        engine.db.execute.assert_called_once()
        # Verify INSERT query used
        insert_query = engine.db.execute.call_args[0][0]
        assert "INSERT" in insert_query

    def test_register_existing_control_update_sqlite(self) -> None:
        """Test registering an existing control (UPDATE) with sqlite"""
        engine = self._make_engine()
        engine.db.fetch_one.return_value = (1,)  # control exists

        control_data = {
            "control_id": "TEST1",
            "control_category": "Security",
            "description": "Updated test control",
            "implementation_status": "implemented",
            "test_results": "pass",
        }

        result = engine.register_control(control_data)

        assert result is True
        update_query = engine.db.execute.call_args[0][0]
        assert "UPDATE" in update_query

    def test_register_new_control_postgresql(self) -> None:
        """Test registering a new control with postgresql"""
        engine = self._make_engine()
        engine.db.db_type = "postgresql"
        engine.db.fetch_one.return_value = None

        control_data = {
            "control_id": "PG1",
            "control_category": "Availability",
            "description": "PG control",
            "implementation_status": "pending",
        }

        result = engine.register_control(control_data)

        assert result is True
        insert_query = engine.db.execute.call_args[0][0]
        assert "%s" in insert_query

    def test_register_existing_control_postgresql(self) -> None:
        """Test updating an existing control with postgresql"""
        engine = self._make_engine()
        engine.db.db_type = "postgresql"
        engine.db.fetch_one.return_value = (5,)

        control_data = {
            "control_id": "PG1",
            "control_category": "Security",
            "description": "Updated",
            "implementation_status": "implemented",
        }

        result = engine.register_control(control_data)

        assert result is True
        update_query = engine.db.execute.call_args[0][0]
        assert "UPDATE" in update_query
        assert "%s" in update_query

    def test_register_control_default_status(self) -> None:
        """Test registering a control with default implementation status"""
        engine = self._make_engine()
        engine.db.fetch_one.return_value = None

        control_data = {
            "control_id": "DEF1",
        }

        engine.register_control(control_data)

        insert_args = engine.db.execute.call_args[0][1]
        assert insert_args[3] == "pending"  # default status

    def test_register_control_missing_control_id(self) -> None:
        """Test registering a control without control_id"""
        engine = self._make_engine()

        control_data = {"control_category": "Security"}

        result = engine.register_control(control_data)

        assert result is False

    def test_register_control_db_error(self) -> None:
        """Test registering a control with database error"""
        engine = self._make_engine()
        engine.db.fetch_one.side_effect = sqlite3.Error("db error")

        control_data = {"control_id": "ERR1"}

        result = engine.register_control(control_data)

        assert result is False

    def test_register_control_type_error(self) -> None:
        """Test registering a control with type error"""
        engine = self._make_engine()
        engine.db.fetch_one.side_effect = TypeError("type error")

        control_data = {"control_id": "ERR2"}

        result = engine.register_control(control_data)

        assert result is False

    def test_register_control_value_error(self) -> None:
        """Test registering a control with value error"""
        engine = self._make_engine()
        engine.db.fetch_one.side_effect = ValueError("value error")

        control_data = {"control_id": "ERR3"}

        result = engine.register_control(control_data)

        assert result is False

    def test_register_control_logs_success(self) -> None:
        """Test that successful registration is logged"""
        engine = self._make_engine()
        engine.db.fetch_one.return_value = None

        control_data = {
            "control_id": "LOG1",
            "control_category": "Security",
        }

        engine.register_control(control_data)

        engine.logger.info.assert_called_with("Registered SOC 2 control: LOG1")


@pytest.mark.unit
class TestSOC2ComplianceEngineUpdateControlTest:
    """Tests for SOC2ComplianceEngine.update_control_test"""

    def _make_engine(self):
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.fetch_one.return_value = None

        config = {"soc2.enabled": True}

        with patch("pbx.features.compliance_framework.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.compliance_framework import SOC2ComplianceEngine

            engine = SOC2ComplianceEngine(mock_db, config)

        mock_db.reset_mock()
        return engine

    def test_update_control_test_success_sqlite(self) -> None:
        """Test updating control test results with sqlite"""
        engine = self._make_engine()

        result = engine.update_control_test("CC1.1", "All checks passed")

        assert result is True
        engine.db.execute.assert_called_once()
        query = engine.db.execute.call_args[0][0]
        assert "UPDATE" in query
        assert "test_results" in query

    def test_update_control_test_success_postgresql(self) -> None:
        """Test updating control test results with postgresql"""
        engine = self._make_engine()
        engine.db.db_type = "postgresql"

        result = engine.update_control_test("CC1.1", "Passed")

        assert result is True
        query = engine.db.execute.call_args[0][0]
        assert "%s" in query

    def test_update_control_test_db_error(self) -> None:
        """Test updating control test with database error"""
        engine = self._make_engine()
        engine.db.execute.side_effect = sqlite3.Error("db error")

        result = engine.update_control_test("CC1.1", "test")

        assert result is False

    def test_update_control_test_logs_success(self) -> None:
        """Test that update logs success message"""
        engine = self._make_engine()

        engine.update_control_test("CC7.1", "Detection verified")

        engine.logger.info.assert_called_with("Updated test results for control CC7.1")


@pytest.mark.unit
class TestSOC2ComplianceEngineGetAllControls:
    """Tests for SOC2ComplianceEngine.get_all_controls"""

    def _make_engine(self):
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.fetch_one.return_value = None

        config = {}

        with patch("pbx.features.compliance_framework.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.compliance_framework import SOC2ComplianceEngine

            engine = SOC2ComplianceEngine(mock_db, config)

        mock_db.reset_mock()
        return engine

    def test_get_all_controls_success(self) -> None:
        """Test getting all controls"""
        engine = self._make_engine()
        engine.db.fetch_all.return_value = [
            {
                "control_id": "CC1.1",
                "control_category": "Security",
                "description": "Integrity",
                "implementation_status": "implemented",
                "last_tested": "2025-01-01",
                "test_results": "pass",
            },
            {
                "control_id": "A1.1",
                "control_category": "Availability",
                "description": "Monitoring",
                "implementation_status": "pending",
                "last_tested": None,
                "test_results": None,
            },
        ]

        result = engine.get_all_controls()

        assert len(result) == 2
        assert result[0]["control_id"] == "CC1.1"
        assert result[0]["control_category"] == "Security"
        assert result[0]["implementation_status"] == "implemented"
        assert result[1]["control_id"] == "A1.1"
        assert result[1]["last_tested"] is None

    def test_get_all_controls_empty(self) -> None:
        """Test getting controls when no controls exist"""
        engine = self._make_engine()
        engine.db.fetch_all.return_value = None

        result = engine.get_all_controls()

        assert result == []

    def test_get_all_controls_empty_list(self) -> None:
        """Test getting controls when result is empty list"""
        engine = self._make_engine()
        engine.db.fetch_all.return_value = []

        result = engine.get_all_controls()

        assert result == []

    def test_get_all_controls_db_error(self) -> None:
        """Test getting controls with db error"""
        engine = self._make_engine()
        engine.db.fetch_all.side_effect = sqlite3.Error("db error")

        result = engine.get_all_controls()

        assert result == []

    def test_get_all_controls_type_error(self) -> None:
        """Test getting controls with type error"""
        engine = self._make_engine()
        engine.db.fetch_all.side_effect = TypeError("type error")

        result = engine.get_all_controls()

        assert result == []


@pytest.mark.unit
class TestSOC2ComplianceEngineGetControlsByCategory:
    """Tests for SOC2ComplianceEngine.get_controls_by_category"""

    def _make_engine(self):
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.fetch_one.return_value = None

        config = {}

        with patch("pbx.features.compliance_framework.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.compliance_framework import SOC2ComplianceEngine

            engine = SOC2ComplianceEngine(mock_db, config)

        mock_db.reset_mock()
        return engine

    def test_get_controls_by_category_security(self) -> None:
        """Test getting security controls"""
        engine = self._make_engine()
        engine.db.fetch_all.return_value = [
            {
                "control_id": "CC1.1",
                "control_category": "Security",
                "description": "Integrity",
                "implementation_status": "implemented",
                "last_tested": None,
                "test_results": None,
            },
        ]

        result = engine.get_controls_by_category("Security")

        assert len(result) == 1
        assert result[0]["control_category"] == "Security"

    def test_get_controls_by_category_availability(self) -> None:
        """Test getting availability controls"""
        engine = self._make_engine()
        engine.db.fetch_all.return_value = [
            {
                "control_id": "A1.1",
                "control_category": "Availability",
                "description": "Monitoring",
                "implementation_status": "implemented",
                "last_tested": None,
                "test_results": None,
            },
        ]

        result = engine.get_controls_by_category("Availability")

        assert len(result) == 1

    def test_get_controls_by_category_empty(self) -> None:
        """Test getting controls for category with no results"""
        engine = self._make_engine()
        engine.db.fetch_all.return_value = None

        result = engine.get_controls_by_category("NonExistent")

        assert result == []

    def test_get_controls_by_category_db_error(self) -> None:
        """Test getting controls by category with db error"""
        engine = self._make_engine()
        engine.db.fetch_all.side_effect = sqlite3.Error("db error")

        result = engine.get_controls_by_category("Security")

        assert result == []

    def test_get_controls_by_category_key_error(self) -> None:
        """Test getting controls by category with key error"""
        engine = self._make_engine()
        engine.db.fetch_all.side_effect = KeyError("missing key")

        result = engine.get_controls_by_category("Security")

        assert result == []

    def test_get_controls_by_category_postgresql(self) -> None:
        """Test getting controls with postgresql"""
        engine = self._make_engine()
        engine.db.db_type = "postgresql"
        engine.db.fetch_all.return_value = [
            {
                "control_id": "CC1.1",
                "control_category": "Security",
                "description": "Test",
                "implementation_status": "implemented",
                "last_tested": None,
                "test_results": None,
            },
        ]

        result = engine.get_controls_by_category("Security")

        assert len(result) == 1
        query = engine.db.fetch_all.call_args[0][0]
        assert "%s" in query


@pytest.mark.unit
class TestSOC2ComplianceEngineGetComplianceSummary:
    """Tests for SOC2ComplianceEngine.get_compliance_summary"""

    def _make_engine(self):
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.fetch_one.return_value = None

        config = {}

        with patch("pbx.features.compliance_framework.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.compliance_framework import SOC2ComplianceEngine

            engine = SOC2ComplianceEngine(mock_db, config)

        mock_db.reset_mock()
        return engine

    def test_get_compliance_summary_all_implemented(self) -> None:
        """Test compliance summary when all controls are implemented"""
        engine = self._make_engine()
        engine.db.fetch_all.return_value = [
            {
                "control_id": "CC1.1",
                "control_category": "Security",
                "description": "Test",
                "implementation_status": "implemented",
                "last_tested": "2025-01-01",
                "test_results": "pass",
            },
            {
                "control_id": "A1.1",
                "control_category": "Availability",
                "description": "Test",
                "implementation_status": "implemented",
                "last_tested": "2025-01-02",
                "test_results": "pass",
            },
        ]

        result = engine.get_compliance_summary()

        assert result["total_controls"] == 2
        assert result["implemented"] == 2
        assert result["pending"] == 0
        assert result["tested"] == 2
        assert result["compliance_percentage"] == 100.0
        assert "Security" in result["categories"]
        assert "Availability" in result["categories"]
        assert result["categories"]["Security"]["total"] == 1
        assert result["categories"]["Security"]["implemented"] == 1

    def test_get_compliance_summary_mixed_status(self) -> None:
        """Test compliance summary with mixed implementation statuses"""
        engine = self._make_engine()
        engine.db.fetch_all.return_value = [
            {
                "control_id": "CC1.1",
                "control_category": "Security",
                "description": "Test",
                "implementation_status": "implemented",
                "last_tested": "2025-01-01",
                "test_results": "pass",
            },
            {
                "control_id": "CC2.1",
                "control_category": "Security",
                "description": "Test",
                "implementation_status": "pending",
                "last_tested": None,
                "test_results": None,
            },
            {
                "control_id": "A1.1",
                "control_category": "Availability",
                "description": "Test",
                "implementation_status": "implemented",
                "last_tested": None,
                "test_results": None,
            },
        ]

        result = engine.get_compliance_summary()

        assert result["total_controls"] == 3
        assert result["implemented"] == 2
        assert result["pending"] == 1
        assert result["tested"] == 1
        assert result["compliance_percentage"] == pytest.approx(66.666, rel=1e-2)
        assert result["categories"]["Security"]["total"] == 2
        assert result["categories"]["Security"]["implemented"] == 1

    def test_get_compliance_summary_no_controls(self) -> None:
        """Test compliance summary with no controls"""
        engine = self._make_engine()
        engine.db.fetch_all.return_value = []

        result = engine.get_compliance_summary()

        assert result["total_controls"] == 0
        assert result["implemented"] == 0
        assert result["pending"] == 0
        assert result["tested"] == 0
        assert result["compliance_percentage"] == 0
        assert result["categories"] == {}

    def test_get_compliance_summary_all_pending(self) -> None:
        """Test compliance summary when all controls are pending"""
        engine = self._make_engine()
        engine.db.fetch_all.return_value = [
            {
                "control_id": "CC1.1",
                "control_category": "Security",
                "description": "Test",
                "implementation_status": "pending",
                "last_tested": None,
                "test_results": None,
            },
        ]

        result = engine.get_compliance_summary()

        assert result["compliance_percentage"] == 0
        assert result["pending"] == 1
        assert result["implemented"] == 0

    def test_get_compliance_summary_error_handling(self) -> None:
        """Test compliance summary error handling when get_all_controls raises"""
        engine = self._make_engine()
        # Make get_all_controls raise a TypeError by returning a non-iterable
        engine.db.fetch_all.side_effect = TypeError("unexpected type")

        result = engine.get_compliance_summary()

        # get_all_controls catches TypeError and returns [], which gives empty summary
        assert result["total_controls"] == 0
        assert result["compliance_percentage"] == 0

    def test_get_compliance_summary_multiple_categories(self) -> None:
        """Test compliance summary with multiple categories"""
        engine = self._make_engine()
        engine.db.fetch_all.return_value = [
            {
                "control_id": "CC1.1",
                "control_category": "Security",
                "description": "Test",
                "implementation_status": "implemented",
                "last_tested": None,
                "test_results": None,
            },
            {
                "control_id": "A1.1",
                "control_category": "Availability",
                "description": "Test",
                "implementation_status": "implemented",
                "last_tested": None,
                "test_results": None,
            },
            {
                "control_id": "PI1.1",
                "control_category": "Processing Integrity",
                "description": "Test",
                "implementation_status": "pending",
                "last_tested": None,
                "test_results": None,
            },
            {
                "control_id": "C1.1",
                "control_category": "Confidentiality",
                "description": "Test",
                "implementation_status": "implemented",
                "last_tested": None,
                "test_results": None,
            },
        ]

        result = engine.get_compliance_summary()

        assert len(result["categories"]) == 4
        assert result["total_controls"] == 4
        assert result["implemented"] == 3
        assert result["compliance_percentage"] == 75.0
