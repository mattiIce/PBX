"""Comprehensive tests for nomadic_e911 feature module.

All tests are purely mock-based. NO real network calls, NO real emergency
service connections. All external dependencies are mocked with MagicMock.
"""

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.nomadic_e911 import NomadicE911Engine


@pytest.mark.unit
class TestNomadicE911Init:
    """Tests for NomadicE911Engine initialization."""

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_default_initialization(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        config = {"nomadic_e911.enabled": True}
        engine = NomadicE911Engine(db_backend=mock_db, config=config)
        assert engine.db is mock_db
        assert engine.config == config
        assert engine.enabled is True

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_initialization_disabled(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        config = {}
        engine = NomadicE911Engine(db_backend=mock_db, config=config)
        assert engine.enabled is True  # Default is True when key not found

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_initialization_with_none_db(self, mock_logger: MagicMock) -> None:
        engine = NomadicE911Engine(db_backend=None, config={})
        assert engine.db is None


@pytest.mark.unit
class TestUpdateLocation:
    """Tests for update_location method."""

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_update_location_new_extension(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.return_value = []  # No existing location
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        location_data = {
            "ip_address": "192.168.1.100",
            "location_name": "Main Office",
            "street_address": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
            "country": "USA",
            "building": "A",
            "floor": "2",
            "room": "201",
            "latitude": 39.7817,
            "longitude": -89.6501,
        }
        result = engine.update_location("1001", location_data)
        assert result is True
        assert mock_db.execute.call_count >= 1

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_update_location_with_existing(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        # First call for get_location returns existing location
        existing_row = (
            1,
            "1001",
            "192.168.1.50",
            "Old Office",
            "456 Old St",
            "Chicago",
            "IL",
            "60601",
            "USA",
            "B",
            "1",
            "101",
            41.8781,
            -87.6298,
            "2026-01-01",
            False,
        )
        # get_location returns the row, then update_location does inserts
        mock_db.execute.side_effect = [
            [existing_row],  # get_location query
            None,  # INSERT into nomadic_e911_locations
            None,  # INSERT into e911_location_updates
        ]
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        location_data = {
            "ip_address": "192.168.1.100",
            "location_name": "New Office",
            "street_address": "789 New St",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
        }
        result = engine.update_location("1001", location_data)
        assert result is True
        # Should have made 3 calls: get_location, insert new location, insert update log
        assert mock_db.execute.call_count == 3

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_update_location_auto_detected(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.return_value = []
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        location_data = {
            "ip_address": "10.0.0.5",
            "location_name": "Auto-detected Site",
            "street_address": "100 Auto St",
            "city": "Detroit",
            "state": "MI",
        }
        result = engine.update_location("1001", location_data, auto_detected=True)
        assert result is True
        # Check that auto_detected=True was passed in the parameters
        call_args = mock_db.execute.call_args_list[1]  # Second call is the INSERT
        assert call_args[0][1][-1] is True  # Last parameter is auto_detected

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_update_location_postgresql(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        mock_db.execute.return_value = []
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        location_data = {
            "street_address": "123 PG St",
            "city": "PGCity",
            "state": "CA",
        }
        result = engine.update_location("1001", location_data)
        assert result is True
        # Should use %s placeholders
        insert_call = mock_db.execute.call_args_list[1]
        assert "%s" in insert_call[0][0]

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_update_location_db_error(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.side_effect = sqlite3.Error("DB error")
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.update_location("1001", {"street_address": "test"})
        assert result is False

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_update_location_key_error(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.side_effect = KeyError("missing key")
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.update_location("1001", {})
        assert result is False


@pytest.mark.unit
class TestGetLocation:
    """Tests for get_location method."""

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_location_found(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        row = (
            1,
            "1001",
            "192.168.1.100",
            "Main Office",
            "123 Main St",
            "Springfield",
            "IL",
            "62701",
            "USA",
            "A",
            "2",
            "201",
            "39.7817",
            "-89.6501",
            "2026-01-15T10:30:00",
            True,
        )
        mock_db.execute.return_value = [row]
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.get_location("1001")
        assert result is not None
        assert result["extension"] == "1001"
        assert result["street_address"] == "123 Main St"
        assert result["city"] == "Springfield"
        assert result["latitude"] == 39.7817
        assert result["longitude"] == -89.6501
        assert result["auto_detected"] is True

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_location_not_found(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.return_value = []
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.get_location("9999")
        assert result is None

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_location_none_result(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.return_value = None
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.get_location("1001")
        assert result is None

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_location_null_lat_long(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        row = (
            1,
            "1001",
            "192.168.1.100",
            "Office",
            "123 St",
            "City",
            "ST",
            "12345",
            "USA",
            "A",
            "1",
            "101",
            None,
            None,
            "2026-01-15",
            False,
        )
        mock_db.execute.return_value = [row]
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.get_location("1001")
        assert result["latitude"] is None
        assert result["longitude"] is None

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_location_postgresql(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        row = (
            1,
            "1001",
            "10.0.0.1",
            "PG Office",
            "456 PG St",
            "PGCity",
            "CA",
            "90001",
            "USA",
            "C",
            "3",
            "301",
            "34.0522",
            "-118.2437",
            "2026-02-01",
            False,
        )
        mock_db.execute.return_value = [row]
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.get_location("1001")
        assert result is not None
        # Verify the query used %s placeholder
        call_args = mock_db.execute.call_args
        assert "%s" in call_args[0][0]

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_location_db_error(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.side_effect = sqlite3.Error("Query failed")
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.get_location("1001")
        assert result is None


@pytest.mark.unit
class TestDetectLocationByIp:
    """Tests for detect_location_by_ip method."""

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_detect_known_site(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        # _find_site_by_ip returns a site
        site_row = (
            1,
            "Main Office",
            "192.168.1.0",
            "192.168.1.255",
            "trunk-1",
            "911",
            "5551234",
            "123 Main St",
            "Springfield",
            "IL",
            "62701",
            "USA",
            "A",
            "2",
        )
        # Mock execute: first for _find_site_by_ip, then for update_location calls
        mock_db.execute.side_effect = [
            [site_row],  # _find_site_by_ip
            [],  # get_location (inside update_location)
            None,  # INSERT
        ]
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.detect_location_by_ip("1001", "192.168.1.100")
        assert result is not None
        assert result["location_name"] == "Main Office"
        assert result["auto_detected"] is True

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_detect_private_ip_unknown_site(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.return_value = []  # No site found
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.detect_location_by_ip("1001", "10.0.0.5")
        assert result is not None
        assert result["location_name"] == "Unknown Internal Location"
        assert result["needs_configuration"] is True

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_detect_public_ip_no_match(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.return_value = []
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.detect_location_by_ip("1001", "8.8.8.8")
        assert result is None

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_detect_update_fails(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        site_row = (
            1,
            "Office",
            "192.168.1.0",
            "192.168.1.255",
            "trunk-1",
            "911",
            "5551234",
            "123 St",
            "City",
            "ST",
            "12345",
            "USA",
            "A",
            "1",
        )
        # _find_site_by_ip succeeds, but update_location fails
        # update_location calls: get_location (execute), then INSERT (execute raises)
        mock_db.execute.side_effect = [
            [site_row],  # _find_site_by_ip query
            [],  # get_location inside update_location returns empty
            sqlite3.Error("Insert failed"),  # INSERT in update_location fails
        ]
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.detect_location_by_ip("1001", "192.168.1.50")
        # update_location returns False, so detect falls through to private IP check
        # 192.168.1.50 is private, so returns Unknown Internal Location
        assert result is not None


@pytest.mark.unit
class TestFindSiteByIp:
    """Tests for find_site_by_ip and _find_site_by_ip methods."""

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_find_site_match(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        site_row = (
            1,
            "Branch Office",
            "10.0.1.0",
            "10.0.1.255",
            "trunk-2",
            "911",
            "5559876",
            "456 Branch St",
            "Chicago",
            "IL",
            "60601",
            "USA",
            "B",
            "3",
        )
        mock_db.execute.return_value = [site_row]
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.find_site_by_ip("10.0.1.100")
        assert result is not None
        assert result["site_name"] == "Branch Office"
        assert result["ip_range_start"] == "10.0.1.0"
        assert result["ip_range_end"] == "10.0.1.255"

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_find_site_no_match(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        site_row = (
            1,
            "Office",
            "192.168.1.0",
            "192.168.1.255",
            "trunk-1",
            "911",
            "5551234",
            "123 St",
            "City",
            "ST",
            "12345",
            "USA",
            "A",
            "1",
        )
        mock_db.execute.return_value = [site_row]
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.find_site_by_ip("10.0.0.5")
        assert result is None

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_find_site_empty_result(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.execute.return_value = []
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.find_site_by_ip("10.0.0.5")
        assert result is None

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_find_site_none_result(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.execute.return_value = None
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine.find_site_by_ip("10.0.0.5")
        assert result is None

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_find_site_db_error(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.execute.side_effect = sqlite3.Error("DB error")
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine._find_site_by_ip("10.0.0.5")
        assert result is None

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_find_site_short_row(self, mock_logger: MagicMock) -> None:
        """Test with a row that has fewer columns than expected."""
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        # Short row - only 7 columns
        site_row = (1, "Short Site", "10.0.0.0", "10.0.0.255", "trunk-1", "911", "5551234")
        mock_db.execute.return_value = [site_row]
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        result = engine._find_site_by_ip("10.0.0.50")
        assert result is not None
        assert result["street_address"] == ""
        assert result["country"] == "USA"


@pytest.mark.unit
class TestIpInRange:
    """Tests for _ip_in_range method."""

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_ip_in_range(self, mock_logger: MagicMock) -> None:
        engine = NomadicE911Engine(db_backend=MagicMock(), config={})
        assert engine._ip_in_range("192.168.1.100", "192.168.1.0", "192.168.1.255") is True

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_ip_out_of_range(self, mock_logger: MagicMock) -> None:
        engine = NomadicE911Engine(db_backend=MagicMock(), config={})
        assert engine._ip_in_range("10.0.0.1", "192.168.1.0", "192.168.1.255") is False

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_ip_at_start(self, mock_logger: MagicMock) -> None:
        engine = NomadicE911Engine(db_backend=MagicMock(), config={})
        assert engine._ip_in_range("192.168.1.0", "192.168.1.0", "192.168.1.255") is True

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_ip_at_end(self, mock_logger: MagicMock) -> None:
        engine = NomadicE911Engine(db_backend=MagicMock(), config={})
        assert engine._ip_in_range("192.168.1.255", "192.168.1.0", "192.168.1.255") is True

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_invalid_ip(self, mock_logger: MagicMock) -> None:
        engine = NomadicE911Engine(db_backend=MagicMock(), config={})
        assert engine._ip_in_range("invalid", "192.168.1.0", "192.168.1.255") is False

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_invalid_range(self, mock_logger: MagicMock) -> None:
        engine = NomadicE911Engine(db_backend=MagicMock(), config={})
        assert engine._ip_in_range("192.168.1.100", "invalid", "192.168.1.255") is False


@pytest.mark.unit
class TestIsPrivateIp:
    """Tests for _is_private_ip method."""

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_private_10_range(self, mock_logger: MagicMock) -> None:
        engine = NomadicE911Engine(db_backend=MagicMock(), config={})
        assert engine._is_private_ip("10.0.0.1") is True

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_private_172_range(self, mock_logger: MagicMock) -> None:
        engine = NomadicE911Engine(db_backend=MagicMock(), config={})
        assert engine._is_private_ip("172.16.0.1") is True

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_private_192_range(self, mock_logger: MagicMock) -> None:
        engine = NomadicE911Engine(db_backend=MagicMock(), config={})
        assert engine._is_private_ip("192.168.1.1") is True

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_public_ip(self, mock_logger: MagicMock) -> None:
        engine = NomadicE911Engine(db_backend=MagicMock(), config={})
        assert engine._is_private_ip("8.8.8.8") is False

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_invalid_ip(self, mock_logger: MagicMock) -> None:
        engine = NomadicE911Engine(db_backend=MagicMock(), config={})
        assert engine._is_private_ip("not_an_ip") is False


@pytest.mark.unit
class TestCreateSiteConfig:
    """Tests for create_site_config method."""

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_create_site_sqlite(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        site_data = {
            "site_name": "New Office",
            "ip_range_start": "10.0.2.0",
            "ip_range_end": "10.0.2.255",
            "emergency_trunk": "trunk-3",
            "psap_number": "911",
            "elin": "5550001",
            "street_address": "789 New St",
            "city": "Boston",
            "state": "MA",
            "postal_code": "02101",
            "country": "USA",
            "building": "HQ",
            "floor": "1",
        }
        result = engine.create_site_config(site_data)
        assert result is True
        mock_db.execute.assert_called_once()

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_create_site_postgresql(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        site_data = {
            "site_name": "PG Office",
            "ip_range_start": "172.16.0.0",
            "ip_range_end": "172.16.0.255",
        }
        result = engine.create_site_config(site_data)
        assert result is True
        call_args = mock_db.execute.call_args
        assert "%s" in call_args[0][0]

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_create_site_db_error(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.side_effect = sqlite3.Error("Insert failed")
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        site_data = {
            "site_name": "Fail Office",
            "ip_range_start": "10.0.3.0",
            "ip_range_end": "10.0.3.255",
        }
        result = engine.create_site_config(site_data)
        assert result is False

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_create_site_missing_key(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        # Missing required 'site_name'
        result = engine.create_site_config({})
        assert result is False


@pytest.mark.unit
class TestGetAllSites:
    """Tests for get_all_sites method."""

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_all_sites(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        row1 = (
            1,
            "Office A",
            "10.0.0.0",
            "10.0.0.255",
            "trunk-1",
            "911",
            "5551111",
            "100 A St",
            "CityA",
            "CA",
            "90001",
            "USA",
            "A",
            "1",
            "2026-01-01",
        )
        row2 = (
            2,
            "Office B",
            "10.0.1.0",
            "10.0.1.255",
            "trunk-2",
            "911",
            "5552222",
            "200 B St",
            "CityB",
            "NY",
            "10001",
            "USA",
            "B",
            "2",
            "2026-01-02",
        )
        mock_db.execute.return_value = [row1, row2]
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        sites = engine.get_all_sites()
        assert len(sites) == 2
        assert sites[0]["site_name"] == "Office A"
        assert sites[1]["site_name"] == "Office B"
        assert sites[0]["street_address"] == "100 A St"

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_all_sites_empty(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.execute.return_value = []
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        sites = engine.get_all_sites()
        assert sites == []

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_all_sites_none_result(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.execute.return_value = None
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        sites = engine.get_all_sites()
        assert sites == []

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_all_sites_db_error(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.execute.side_effect = sqlite3.Error("Query error")
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        sites = engine.get_all_sites()
        assert sites == []

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_all_sites_short_rows(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        # Row with only 7 columns
        short_row = (1, "Short", "10.0.0.0", "10.0.0.255", "trunk-1", "911", "5551234")
        mock_db.execute.return_value = [short_row]
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        sites = engine.get_all_sites()
        assert len(sites) == 1
        assert sites[0]["street_address"] == ""
        assert sites[0]["country"] == "USA"


@pytest.mark.unit
class TestGetLocationHistory:
    """Tests for get_location_history method."""

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_history(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        row1 = (
            1,
            "1001",
            "Old Office, Chicago, IL",
            "New Office, Springfield, IL",
            "manual",
            "2026-01-15",
        )
        row2 = (2, "1001", "Home, Remote", "New Office, Springfield, IL", "auto", "2026-01-10")
        mock_db.execute.return_value = [row1, row2]
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        history = engine.get_location_history("1001")
        assert len(history) == 2
        assert history[0]["old_location"] == "Old Office, Chicago, IL"
        assert history[0]["update_source"] == "manual"

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_history_with_limit(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.return_value = []
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        engine.get_location_history("1001", limit=5)
        call_args = mock_db.execute.call_args
        assert call_args[0][1] == ("1001", 5)

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_history_postgresql(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        mock_db.execute.return_value = []
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        engine.get_location_history("1001")
        call_args = mock_db.execute.call_args
        assert "%s" in call_args[0][0]

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_history_empty(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.return_value = []
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        history = engine.get_location_history("9999")
        assert history == []

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_history_none_result(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.return_value = None
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        history = engine.get_location_history("1001")
        assert history == []

    @patch("pbx.features.nomadic_e911.get_logger")
    def test_get_history_db_error(self, mock_logger: MagicMock) -> None:
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.execute.side_effect = sqlite3.Error("Query error")
        engine = NomadicE911Engine(db_backend=mock_db, config={})
        history = engine.get_location_history("1001")
        assert history == []
