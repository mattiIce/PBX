"""
Comprehensive tests for DNS SRV Failover feature.

Tests cover SRVRecord, DNSSRVFailover, and the module-level
get_dns_srv_failover() singleton factory.
"""

import socket
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.dns_srv_failover import DNSSRVFailover, SRVRecord, get_dns_srv_failover


def _make_dns_mocks(rdata_list):
    """Helper to create properly linked dns/dns.resolver mocks.

    The mock_dns.resolver attribute must be the same object as mock_resolver
    so that ``import dns.resolver`` inside a function resolves correctly when
    sys.modules is patched.
    """
    mock_resolver = MagicMock()
    mock_resolver.resolve.return_value = rdata_list
    mock_dns = MagicMock()
    mock_dns.resolver = mock_resolver
    return mock_dns, mock_resolver


@pytest.mark.unit
class TestSRVRecord:
    """Tests for the SRVRecord data class."""

    def test_basic_initialization(self) -> None:
        """Test SRVRecord initializes all fields correctly."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")

        assert record.priority == 10
        assert record.weight == 60
        assert record.port == 5060
        assert record.target == "sip.example.com"
        assert record.available is True
        assert record.last_check is None
        assert record.failure_count == 0

    def test_zero_values(self) -> None:
        """Test SRVRecord with all zero values."""
        record = SRVRecord(priority=0, weight=0, port=0, target="")

        assert record.priority == 0
        assert record.weight == 0
        assert record.port == 0
        assert record.target == ""
        assert record.available is True
        assert record.failure_count == 0

    def test_high_values(self) -> None:
        """Test SRVRecord with large numeric values."""
        record = SRVRecord(priority=65535, weight=65535, port=65535, target="host.example.com")

        assert record.priority == 65535
        assert record.weight == 65535
        assert record.port == 65535

    def test_mutable_fields(self) -> None:
        """Test that mutable fields can be updated after creation."""
        record = SRVRecord(priority=10, weight=20, port=5060, target="sip.example.com")

        record.available = False
        record.failure_count = 5
        record.last_check = 1234567890.0

        assert record.available is False
        assert record.failure_count == 5
        assert record.last_check == 1234567890.0


@pytest.mark.unit
class TestDNSSRVFailoverInit:
    """Tests for DNSSRVFailover initialization with various configs."""

    @patch("pbx.features.dns_srv_failover.get_logger")
    def test_init_no_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with no config (None)."""
        mock_get_logger.return_value = MagicMock()
        failover = DNSSRVFailover(config=None)

        assert failover.enabled is False
        assert failover.check_interval == 60
        assert failover.max_failures == 3
        assert failover.srv_cache == {}
        assert failover.total_lookups == 0
        assert failover.total_failovers == 0
        assert failover.cache_hits == 0

    @patch("pbx.features.dns_srv_failover.get_logger")
    def test_init_empty_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with empty dict config."""
        mock_get_logger.return_value = MagicMock()
        failover = DNSSRVFailover(config={})

        assert failover.enabled is False
        assert failover.check_interval == 60
        assert failover.max_failures == 3

    @patch("pbx.features.dns_srv_failover.get_logger")
    def test_init_enabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with feature enabled."""
        mock_get_logger.return_value = MagicMock()
        config = {
            "features": {
                "dns_srv_failover": {
                    "enabled": True,
                    "check_interval": 30,
                    "max_failures": 5,
                }
            }
        }
        failover = DNSSRVFailover(config=config)

        assert failover.enabled is True
        assert failover.check_interval == 30
        assert failover.max_failures == 5

    @patch("pbx.features.dns_srv_failover.get_logger")
    def test_init_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with feature explicitly disabled."""
        mock_get_logger.return_value = MagicMock()
        config = {
            "features": {
                "dns_srv_failover": {
                    "enabled": False,
                }
            }
        }
        failover = DNSSRVFailover(config=config)

        assert failover.enabled is False

    @patch("pbx.features.dns_srv_failover.get_logger")
    def test_init_partial_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with partial config (features key but no dns_srv_failover)."""
        mock_get_logger.return_value = MagicMock()
        config = {"features": {}}
        failover = DNSSRVFailover(config=config)

        assert failover.enabled is False
        assert failover.check_interval == 60
        assert failover.max_failures == 3

    @patch("pbx.features.dns_srv_failover.get_logger")
    def test_init_logs_info(self, mock_get_logger: MagicMock) -> None:
        """Test that initialization logs configuration details."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        config = {
            "features": {
                "dns_srv_failover": {
                    "enabled": True,
                    "check_interval": 45,
                    "max_failures": 7,
                }
            }
        }
        DNSSRVFailover(config=config)

        # Verify logger was called with configuration info
        info_calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("initialized" in c for c in info_calls)
        assert any("45" in c for c in info_calls)
        assert any("7" in c for c in info_calls)
        assert any("True" in c for c in info_calls)


@pytest.mark.unit
class TestDNSSRVFailoverLookup:
    """Tests for lookup_srv and _perform_srv_lookup methods."""

    @patch("pbx.features.dns_srv_failover.get_logger")
    def setup_method(self, method: object, mock_get_logger: MagicMock) -> None:
        """Set up a fresh DNSSRVFailover instance for each test."""
        mock_get_logger.return_value = MagicMock()
        self.failover = DNSSRVFailover(config={})

    def test_lookup_srv_with_dnspython(self) -> None:
        """Test SRV lookup using dnspython resolver."""
        mock_rdata_1 = MagicMock()
        mock_rdata_1.priority = 10
        mock_rdata_1.weight = 60
        mock_rdata_1.port = 5060
        mock_rdata_1.target = "sip1.example.com."

        mock_rdata_2 = MagicMock()
        mock_rdata_2.priority = 20
        mock_rdata_2.weight = 40
        mock_rdata_2.port = 5060
        mock_rdata_2.target = "sip2.example.com."

        mock_dns, mock_resolver = _make_dns_mocks([mock_rdata_1, mock_rdata_2])

        with patch.dict("sys.modules", {"dns": mock_dns, "dns.resolver": mock_resolver}):
            results = self.failover.lookup_srv("sip", "tcp", "example.com")

        assert len(results) == 2
        assert self.failover.total_lookups == 1

        # First result should be lower priority (better)
        assert results[0]["priority"] == 10
        assert results[0]["target"] == "sip1.example.com"
        assert results[0]["available"] is True

        assert results[1]["priority"] == 20
        assert results[1]["target"] == "sip2.example.com"

    def test_lookup_srv_cache_hit(self) -> None:
        """Test that second lookup for same name returns cached results."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        results = self.failover.lookup_srv("sip", "tcp", "example.com")

        assert self.failover.total_lookups == 1
        assert self.failover.cache_hits == 1
        assert len(results) == 1
        assert results[0]["target"] == "sip.example.com"

    def test_lookup_srv_cache_miss_then_hit(self) -> None:
        """Test cache miss followed by cache hit."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")

        # First call: cache miss, manually populate
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]
        self.failover.lookup_srv("sip", "tcp", "example.com")
        assert self.failover.cache_hits == 1

        # Second call: cache hit
        self.failover.lookup_srv("sip", "tcp", "example.com")
        assert self.failover.cache_hits == 2
        assert self.failover.total_lookups == 2

    @patch("pbx.features.dns_srv_failover.socket")
    def test_perform_srv_lookup_fallback_no_dnspython(self, mock_socket: MagicMock) -> None:
        """Test fallback to basic DNS when dnspython is not installed."""
        mock_socket.gethostbyname.return_value = "192.168.1.100"
        mock_socket.gaierror = OSError

        # Simulate ImportError for dns.resolver
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "dns.resolver":
                raise ImportError("No module named 'dns.resolver'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            records = self.failover._perform_srv_lookup("_sip._tcp.example.com")

        assert len(records) == 1
        assert records[0].target == "192.168.1.100"
        assert records[0].port == 5060
        assert records[0].priority == 0
        assert records[0].weight == 0

    @patch("pbx.features.dns_srv_failover.socket")
    def test_perform_srv_lookup_fallback_dns_failure(self, mock_socket: MagicMock) -> None:
        """Test fallback with DNS resolution failure (gaierror)."""
        mock_socket.gaierror = OSError
        mock_socket.gethostbyname.side_effect = OSError("DNS resolution failed")

        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "dns.resolver":
                raise ImportError("No module named 'dns.resolver'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            records = self.failover._perform_srv_lookup("_sip._tcp.example.com")

        assert len(records) == 0

    def test_perform_srv_lookup_general_exception(self) -> None:
        """Test _perform_srv_lookup when dns.resolver.resolve raises a general exception."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = RuntimeError("Network unreachable")
        mock_dns = MagicMock()
        mock_dns.resolver = mock_resolver

        with patch.dict("sys.modules", {"dns": mock_dns, "dns.resolver": mock_resolver}):
            records = self.failover._perform_srv_lookup("_sip._tcp.example.com")

        assert len(records) == 0

    def test_perform_srv_lookup_fallback_short_srv_name(self) -> None:
        """Test fallback with SRV name that has fewer than 3 parts."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "dns.resolver":
                raise ImportError("No module named 'dns.resolver'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            # Only 2 parts: "_sip._tcp" - fewer than 3, so hostname extraction won't happen
            records = self.failover._perform_srv_lookup("_sip._tcp")

        assert len(records) == 0

    def test_lookup_srv_empty_results_not_cached(self) -> None:
        """Test that empty lookup results are not cached."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = RuntimeError("Fail")
        mock_dns = MagicMock()
        mock_dns.resolver = mock_resolver

        with patch.dict("sys.modules", {"dns": mock_dns, "dns.resolver": mock_resolver}):
            results = self.failover.lookup_srv("sip", "tcp", "nonexistent.example.com")

        assert len(results) == 0
        assert "_sip._tcp.nonexistent.example.com" not in self.failover.srv_cache

    def test_lookup_srv_nonempty_results_are_cached(self) -> None:
        """Test that non-empty lookup results are cached."""
        mock_rdata = MagicMock()
        mock_rdata.priority = 10
        mock_rdata.weight = 60
        mock_rdata.port = 5060
        mock_rdata.target = "sip.example.com."

        mock_dns, mock_resolver = _make_dns_mocks([mock_rdata])

        with patch.dict("sys.modules", {"dns": mock_dns, "dns.resolver": mock_resolver}):
            results = self.failover.lookup_srv("sip", "tcp", "example.com")

        assert len(results) == 1
        assert "_sip._tcp.example.com" in self.failover.srv_cache

    def test_lookup_srv_records_sorted_by_priority_then_weight(self) -> None:
        """Test that records are sorted by priority ascending, then weight descending."""
        mock_rdata_low_pri_low_w = MagicMock()
        mock_rdata_low_pri_low_w.priority = 10
        mock_rdata_low_pri_low_w.weight = 20
        mock_rdata_low_pri_low_w.port = 5060
        mock_rdata_low_pri_low_w.target = "server-a."

        mock_rdata_low_pri_high_w = MagicMock()
        mock_rdata_low_pri_high_w.priority = 10
        mock_rdata_low_pri_high_w.weight = 80
        mock_rdata_low_pri_high_w.port = 5060
        mock_rdata_low_pri_high_w.target = "server-b."

        mock_rdata_high_pri = MagicMock()
        mock_rdata_high_pri.priority = 20
        mock_rdata_high_pri.weight = 50
        mock_rdata_high_pri.port = 5060
        mock_rdata_high_pri.target = "server-c."

        rdata_list = [mock_rdata_high_pri, mock_rdata_low_pri_low_w, mock_rdata_low_pri_high_w]
        mock_dns, mock_resolver = _make_dns_mocks(rdata_list)

        with patch.dict("sys.modules", {"dns": mock_dns, "dns.resolver": mock_resolver}):
            results = self.failover.lookup_srv("sip", "tcp", "example.com")

        assert len(results) == 3
        # Priority 10, weight 80 should be first
        assert results[0]["target"] == "server-b"
        assert results[0]["priority"] == 10
        assert results[0]["weight"] == 80
        # Priority 10, weight 20 should be second
        assert results[1]["target"] == "server-a"
        assert results[1]["priority"] == 10
        assert results[1]["weight"] == 20
        # Priority 20 should be last
        assert results[2]["target"] == "server-c"
        assert results[2]["priority"] == 20


@pytest.mark.unit
class TestDNSSRVFailoverFormatSRVRecords:
    """Tests for _format_srv_records method."""

    @patch("pbx.features.dns_srv_failover.get_logger")
    def setup_method(self, method: object, mock_get_logger: MagicMock) -> None:
        """Set up a fresh DNSSRVFailover instance for each test."""
        mock_get_logger.return_value = MagicMock()
        self.failover = DNSSRVFailover(config={})

    def test_format_empty_list(self) -> None:
        """Test formatting empty record list."""
        result = self.failover._format_srv_records([])
        assert result == []

    def test_format_single_record(self) -> None:
        """Test formatting a single record."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        result = self.failover._format_srv_records([record])

        assert len(result) == 1
        assert result[0] == {
            "priority": 10,
            "weight": 60,
            "port": 5060,
            "target": "sip.example.com",
            "available": True,
        }

    def test_format_multiple_records(self) -> None:
        """Test formatting multiple records."""
        records = [
            SRVRecord(priority=10, weight=60, port=5060, target="sip1.example.com"),
            SRVRecord(priority=20, weight=40, port=5061, target="sip2.example.com"),
        ]
        result = self.failover._format_srv_records(records)

        assert len(result) == 2
        assert result[0]["target"] == "sip1.example.com"
        assert result[1]["target"] == "sip2.example.com"

    def test_format_unavailable_record(self) -> None:
        """Test formatting a record marked as unavailable."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="down.example.com")
        record.available = False

        result = self.failover._format_srv_records([record])
        assert result[0]["available"] is False


@pytest.mark.unit
class TestDNSSRVFailoverSelectServer:
    """Tests for select_server and _weighted_selection methods."""

    @patch("pbx.features.dns_srv_failover.get_logger")
    def setup_method(self, method: object, mock_get_logger: MagicMock) -> None:
        """Set up a fresh DNSSRVFailover instance for each test."""
        mock_get_logger.return_value = MagicMock()
        self.failover = DNSSRVFailover(config={})

    def test_select_server_with_cached_records(self) -> None:
        """Test server selection with records already in cache."""
        records = [
            SRVRecord(priority=10, weight=60, port=5060, target="sip1.example.com"),
            SRVRecord(priority=20, weight=40, port=5061, target="sip2.example.com"),
        ]
        self.failover.srv_cache["_sip._tcp.example.com"] = records

        result = self.failover.select_server("sip", "tcp", "example.com")

        assert result is not None
        assert result["target"] == "sip1.example.com"
        assert result["port"] == 5060
        assert result["priority"] == 10
        assert result["weight"] == 60

    def test_select_server_triggers_lookup_on_cache_miss(self) -> None:
        """Test that select_server triggers lookup when not cached."""
        mock_rdata = MagicMock()
        mock_rdata.priority = 10
        mock_rdata.weight = 60
        mock_rdata.port = 5060
        mock_rdata.target = "sip.example.com."

        mock_dns, mock_resolver = _make_dns_mocks([mock_rdata])

        with patch.dict("sys.modules", {"dns": mock_dns, "dns.resolver": mock_resolver}):
            result = self.failover.select_server("sip", "tcp", "example.com")

        assert result is not None
        assert result["target"] == "sip.example.com"

    def test_select_server_no_records_returns_none(self) -> None:
        """Test select_server returns None when lookup returns no records."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = RuntimeError("Fail")
        mock_dns = MagicMock()
        mock_dns.resolver = mock_resolver

        with patch.dict("sys.modules", {"dns": mock_dns, "dns.resolver": mock_resolver}):
            result = self.failover.select_server("sip", "tcp", "nonexistent.example.com")

        assert result is None

    def test_select_server_no_available_servers(self) -> None:
        """Test select_server returns None when all servers are unavailable."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        record.available = False
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        result = self.failover.select_server("sip", "tcp", "example.com")

        assert result is None

    def test_select_server_picks_best_priority(self) -> None:
        """Test that server selection picks the lowest priority first."""
        records = [
            SRVRecord(priority=30, weight=10, port=5060, target="backup.example.com"),
            SRVRecord(priority=10, weight=10, port=5060, target="primary.example.com"),
            SRVRecord(priority=20, weight=10, port=5060, target="secondary.example.com"),
        ]
        self.failover.srv_cache["_sip._tcp.example.com"] = records

        result = self.failover.select_server("sip", "tcp", "example.com")

        assert result is not None
        assert result["target"] == "primary.example.com"

    def test_select_server_skips_unavailable_high_priority(self) -> None:
        """Test that unavailable primary causes selection of secondary."""
        primary = SRVRecord(priority=10, weight=60, port=5060, target="primary.example.com")
        primary.available = False

        secondary = SRVRecord(priority=20, weight=40, port=5060, target="secondary.example.com")

        self.failover.srv_cache["_sip._tcp.example.com"] = [primary, secondary]

        result = self.failover.select_server("sip", "tcp", "example.com")

        assert result is not None
        assert result["target"] == "secondary.example.com"

    def test_weighted_selection_single_record(self) -> None:
        """Test weighted selection returns the only record when there's just one."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")

        selected = self.failover._weighted_selection([record])

        assert selected is record

    @patch("pbx.features.dns_srv_failover.random")
    def test_weighted_selection_all_zero_weights(self, mock_random: MagicMock) -> None:
        """Test weighted selection with all zero weights uses random.choice."""
        records = [
            SRVRecord(priority=10, weight=0, port=5060, target="server-a.example.com"),
            SRVRecord(priority=10, weight=0, port=5060, target="server-b.example.com"),
        ]
        mock_random.choice.return_value = records[1]

        selected = self.failover._weighted_selection(records)

        mock_random.choice.assert_called_once_with(records)
        assert selected.target == "server-b.example.com"

    @patch("pbx.features.dns_srv_failover.random")
    def test_weighted_selection_weighted_random(self, mock_random: MagicMock) -> None:
        """Test weighted random selection picks according to cumulative weights."""
        records = [
            SRVRecord(priority=10, weight=70, port=5060, target="heavy.example.com"),
            SRVRecord(priority=10, weight=30, port=5060, target="light.example.com"),
        ]
        # Total weight = 100, rand returns 50 -> cumulative 70 covers it -> first record
        mock_random.randint.return_value = 50

        selected = self.failover._weighted_selection(records)

        assert selected.target == "heavy.example.com"

    @patch("pbx.features.dns_srv_failover.random")
    def test_weighted_selection_picks_second_record(self, mock_random: MagicMock) -> None:
        """Test weighted selection picks the second record when rand is high."""
        records = [
            SRVRecord(priority=10, weight=30, port=5060, target="light.example.com"),
            SRVRecord(priority=10, weight=70, port=5060, target="heavy.example.com"),
        ]
        # Total weight = 100, rand returns 80 -> cumulative 30 doesn't cover, 30+70=100 covers
        mock_random.randint.return_value = 80

        selected = self.failover._weighted_selection(records)

        assert selected.target == "heavy.example.com"

    @patch("pbx.features.dns_srv_failover.random")
    def test_weighted_selection_falls_through_to_last(self, mock_random: MagicMock) -> None:
        """Test weighted selection returns last record when rand exceeds cumulative."""
        records = [
            SRVRecord(priority=10, weight=10, port=5060, target="server-a.example.com"),
            SRVRecord(priority=10, weight=10, port=5060, target="server-b.example.com"),
        ]
        # Total weight = 20, rand could return 20 (inclusive), cumulative never exceeds
        # rand=20: cumulative after A=10 (10 < 20 no), cumulative after B=20 (20 <= 20 yes)
        # Actually rand <= cumulative: 20 <= 20 is True, so it picks B
        mock_random.randint.return_value = 20

        selected = self.failover._weighted_selection(records)

        assert selected.target == "server-b.example.com"

    @patch("pbx.features.dns_srv_failover.random")
    def test_weighted_selection_exact_boundary(self, mock_random: MagicMock) -> None:
        """Test weighted selection at exact boundary of first record."""
        records = [
            SRVRecord(priority=10, weight=50, port=5060, target="server-a.example.com"),
            SRVRecord(priority=10, weight=50, port=5060, target="server-b.example.com"),
        ]
        # rand=50, cumulative after A=50, 50 <= 50 -> picks A
        mock_random.randint.return_value = 50

        selected = self.failover._weighted_selection(records)

        assert selected.target == "server-a.example.com"

    @patch("pbx.features.dns_srv_failover.random")
    def test_weighted_selection_fallback_to_last_record(self, mock_random: MagicMock) -> None:
        """Test defensive fallback returning last record when rand exceeds total weight."""
        records = [
            SRVRecord(priority=10, weight=10, port=5060, target="server-a.example.com"),
            SRVRecord(priority=10, weight=10, port=5060, target="server-b.example.com"),
        ]
        # Force rand to exceed total_weight (20) so the loop never matches
        mock_random.randint.return_value = 21

        selected = self.failover._weighted_selection(records)

        assert selected.target == "server-b.example.com"


@pytest.mark.unit
class TestDNSSRVFailoverHealthCheck:
    """Tests for check_server_health method."""

    @patch("pbx.features.dns_srv_failover.get_logger")
    def setup_method(self, method: object, mock_get_logger: MagicMock) -> None:
        """Set up a fresh DNSSRVFailover instance for each test."""
        mock_get_logger.return_value = MagicMock()
        self.failover = DNSSRVFailover(config={})

    @patch("pbx.features.dns_srv_failover.socket")
    def test_health_check_success(self, mock_socket_mod: MagicMock) -> None:
        """Test health check when TCP connection succeeds."""
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket_mod.AF_INET = 2
        mock_socket_mod.SOCK_STREAM = 1
        mock_socket_mod.socket.return_value = mock_sock

        result = self.failover.check_server_health("sip.example.com", 5060)

        assert result is True
        mock_sock.settimeout.assert_called_once_with(2.0)
        mock_sock.connect_ex.assert_called_once_with(("sip.example.com", 5060))
        mock_sock.close.assert_called_once()

    @patch("pbx.features.dns_srv_failover.socket")
    def test_health_check_connection_refused(self, mock_socket_mod: MagicMock) -> None:
        """Test health check when TCP connection is refused (non-zero result)."""
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 111  # Connection refused
        mock_socket_mod.AF_INET = 2
        mock_socket_mod.SOCK_STREAM = 1
        mock_socket_mod.socket.return_value = mock_sock

        result = self.failover.check_server_health("sip.example.com", 5060)

        assert result is False
        mock_sock.close.assert_called_once()

    @patch("pbx.features.dns_srv_failover.socket")
    def test_health_check_dns_resolution_fails(self, mock_socket_mod: MagicMock) -> None:
        """Test health check when DNS resolution (gaierror) fails."""
        mock_socket_mod.AF_INET = 2
        mock_socket_mod.SOCK_STREAM = 1
        mock_socket_mod.gaierror = socket.gaierror
        mock_socket_mod.socket.return_value = MagicMock(
            connect_ex=MagicMock(side_effect=socket.gaierror("Name resolution failed"))
        )

        result = self.failover.check_server_health("nonexistent.example.com", 5060)

        assert result is False

    @patch("pbx.features.dns_srv_failover.socket")
    def test_health_check_os_error(self, mock_socket_mod: MagicMock) -> None:
        """Test health check when OSError occurs."""
        mock_socket_mod.AF_INET = 2
        mock_socket_mod.SOCK_STREAM = 1
        mock_socket_mod.gaierror = socket.gaierror
        mock_socket_mod.socket.return_value = MagicMock(
            connect_ex=MagicMock(side_effect=OSError("Network unreachable"))
        )

        result = self.failover.check_server_health("sip.example.com", 5060)

        assert result is False


@pytest.mark.unit
class TestDNSSRVFailoverMarkServerFailed:
    """Tests for mark_server_failed and _trigger_failover methods."""

    @patch("pbx.features.dns_srv_failover.get_logger")
    def setup_method(self, method: object, mock_get_logger: MagicMock) -> None:
        """Set up a fresh DNSSRVFailover instance for each test."""
        self.mock_logger = MagicMock()
        mock_get_logger.return_value = self.mock_logger
        self.failover = DNSSRVFailover(config={})

    def test_mark_failed_not_in_cache(self) -> None:
        """Test mark_server_failed when srv_name is not in cache (no-op)."""
        self.failover.mark_server_failed("sip", "tcp", "example.com", "sip.example.com", 5060)

        # Should return early without any effect
        assert self.failover.total_failovers == 0

    def test_mark_failed_increment_failure_count(self) -> None:
        """Test that failure count increments but server remains available below threshold."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        self.failover.mark_server_failed("sip", "tcp", "example.com", "sip.example.com", 5060)

        assert record.failure_count == 1
        assert record.available is True
        assert self.failover.total_failovers == 0

    def test_mark_failed_reaches_max_failures(self) -> None:
        """Test that server becomes unavailable when failure count reaches max_failures."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        record.failure_count = 2  # Already at max_failures - 1
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        self.failover.mark_server_failed("sip", "tcp", "example.com", "sip.example.com", 5060)

        assert record.failure_count == 3
        assert record.available is False
        assert self.failover.total_failovers == 1

    def test_mark_failed_triggers_failover(self) -> None:
        """Test that _trigger_failover is called when max_failures reached."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        record.failure_count = 2
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        with patch.object(self.failover, "_trigger_failover") as mock_trigger:
            self.failover.mark_server_failed("sip", "tcp", "example.com", "sip.example.com", 5060)
            mock_trigger.assert_called_once_with("_sip._tcp.example.com")

    def test_mark_failed_no_matching_record(self) -> None:
        """Test mark_server_failed when target/port don't match any cached record."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        self.failover.mark_server_failed("sip", "tcp", "example.com", "other.example.com", 5060)

        assert record.failure_count == 0
        assert record.available is True

    def test_mark_failed_wrong_port(self) -> None:
        """Test mark_server_failed when target matches but port does not."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        self.failover.mark_server_failed("sip", "tcp", "example.com", "sip.example.com", 5061)

        assert record.failure_count == 0

    def test_mark_failed_multiple_records_only_matches_correct_one(self) -> None:
        """Test that only the matching record is affected among multiple."""
        record_a = SRVRecord(priority=10, weight=60, port=5060, target="sip1.example.com")
        record_b = SRVRecord(priority=20, weight=40, port=5060, target="sip2.example.com")
        self.failover.srv_cache["_sip._tcp.example.com"] = [record_a, record_b]

        self.failover.mark_server_failed("sip", "tcp", "example.com", "sip2.example.com", 5060)

        assert record_a.failure_count == 0
        assert record_b.failure_count == 1

    def test_mark_failed_custom_max_failures(self) -> None:
        """Test mark_server_failed with custom max_failures configuration."""
        config = {"features": {"dns_srv_failover": {"max_failures": 1}}}
        with patch("pbx.features.dns_srv_failover.get_logger", return_value=MagicMock()):
            failover = DNSSRVFailover(config=config)

        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        failover.srv_cache["_sip._tcp.example.com"] = [record]

        failover.mark_server_failed("sip", "tcp", "example.com", "sip.example.com", 5060)

        assert record.failure_count == 1
        assert record.available is False
        assert failover.total_failovers == 1

    def test_trigger_failover_logs_warning(self) -> None:
        """Test that _trigger_failover logs a warning message."""
        self.failover._trigger_failover("_sip._tcp.example.com")

        self.mock_logger.warning.assert_called()
        warning_calls = [str(c) for c in self.mock_logger.warning.call_args_list]
        assert any("failover" in c.lower() for c in warning_calls)


@pytest.mark.unit
class TestDNSSRVFailoverMarkServerRecovered:
    """Tests for mark_server_recovered method."""

    @patch("pbx.features.dns_srv_failover.get_logger")
    def setup_method(self, method: object, mock_get_logger: MagicMock) -> None:
        """Set up a fresh DNSSRVFailover instance for each test."""
        mock_get_logger.return_value = MagicMock()
        self.failover = DNSSRVFailover(config={})

    def test_recover_not_in_cache(self) -> None:
        """Test mark_server_recovered when srv_name is not in cache (no-op)."""
        self.failover.mark_server_recovered("sip", "tcp", "example.com", "sip.example.com", 5060)

        # No error should occur

    def test_recover_resets_failure_count_and_availability(self) -> None:
        """Test that recovery resets failure_count and marks server available."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        record.failure_count = 5
        record.available = False
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        self.failover.mark_server_recovered("sip", "tcp", "example.com", "sip.example.com", 5060)

        assert record.failure_count == 0
        assert record.available is True

    def test_recover_no_matching_record(self) -> None:
        """Test mark_server_recovered with no matching target/port."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        record.failure_count = 3
        record.available = False
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        self.failover.mark_server_recovered("sip", "tcp", "example.com", "other.example.com", 5060)

        # Original record should remain unchanged
        assert record.failure_count == 3
        assert record.available is False

    def test_recover_already_healthy_server(self) -> None:
        """Test recovery on a server that was already available."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        assert record.available is True
        assert record.failure_count == 0
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        self.failover.mark_server_recovered("sip", "tcp", "example.com", "sip.example.com", 5060)

        assert record.failure_count == 0
        assert record.available is True

    def test_recover_only_affects_matching_record(self) -> None:
        """Test that only the matching record is recovered among multiple records."""
        record_a = SRVRecord(priority=10, weight=60, port=5060, target="sip1.example.com")
        record_a.failure_count = 5
        record_a.available = False

        record_b = SRVRecord(priority=20, weight=40, port=5060, target="sip2.example.com")
        record_b.failure_count = 3
        record_b.available = False

        self.failover.srv_cache["_sip._tcp.example.com"] = [record_a, record_b]

        self.failover.mark_server_recovered("sip", "tcp", "example.com", "sip2.example.com", 5060)

        # Only record_b should be recovered
        assert record_a.failure_count == 5
        assert record_a.available is False
        assert record_b.failure_count == 0
        assert record_b.available is True


@pytest.mark.unit
class TestDNSSRVFailoverClearCache:
    """Tests for clear_cache method."""

    @patch("pbx.features.dns_srv_failover.get_logger")
    def setup_method(self, method: object, mock_get_logger: MagicMock) -> None:
        """Set up a fresh DNSSRVFailover instance for each test."""
        mock_get_logger.return_value = MagicMock()
        self.failover = DNSSRVFailover(config={})

    def test_clear_specific_cache_entry(self) -> None:
        """Test clearing a specific SRV cache entry."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]
        self.failover.srv_cache["_sip._tcp.other.com"] = [record]

        self.failover.clear_cache(service="sip", protocol="tcp", domain="example.com")

        assert "_sip._tcp.example.com" not in self.failover.srv_cache
        assert "_sip._tcp.other.com" in self.failover.srv_cache

    def test_clear_specific_cache_entry_not_present(self) -> None:
        """Test clearing a specific entry that doesn't exist in cache (no error)."""
        self.failover.clear_cache(service="sip", protocol="tcp", domain="nonexistent.com")

        assert len(self.failover.srv_cache) == 0

    def test_clear_entire_cache(self) -> None:
        """Test clearing the entire cache."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]
        self.failover.srv_cache["_sip._tcp.other.com"] = [record]
        self.failover.srv_cache["_sips._tls.secure.com"] = [record]

        self.failover.clear_cache()

        assert len(self.failover.srv_cache) == 0

    def test_clear_cache_with_partial_args_clears_all(self) -> None:
        """Test that providing only some args (not all 3) clears entire cache."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        # Only service provided, protocol and domain are None
        self.failover.clear_cache(service="sip")

        assert len(self.failover.srv_cache) == 0

    def test_clear_cache_with_only_two_args_clears_all(self) -> None:
        """Test that providing only two of three args clears entire cache."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        self.failover.clear_cache(service="sip", protocol="tcp")

        assert len(self.failover.srv_cache) == 0


@pytest.mark.unit
class TestDNSSRVFailoverStatistics:
    """Tests for get_statistics method."""

    @patch("pbx.features.dns_srv_failover.get_logger")
    def setup_method(self, method: object, mock_get_logger: MagicMock) -> None:
        """Set up a fresh DNSSRVFailover instance for each test."""
        mock_get_logger.return_value = MagicMock()
        self.failover = DNSSRVFailover(config={})

    def test_initial_statistics(self) -> None:
        """Test statistics right after initialization."""
        stats = self.failover.get_statistics()

        assert stats["enabled"] is False
        assert stats["total_lookups"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_hit_rate"] == 0.0
        assert stats["total_failovers"] == 0
        assert stats["cached_services"] == 0

    def test_statistics_after_lookups(self) -> None:
        """Test statistics after performing lookups."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        # Perform two lookups (both cache hits)
        self.failover.lookup_srv("sip", "tcp", "example.com")
        self.failover.lookup_srv("sip", "tcp", "example.com")

        stats = self.failover.get_statistics()

        assert stats["total_lookups"] == 2
        assert stats["cache_hits"] == 2
        assert stats["cache_hit_rate"] == 1.0
        assert stats["cached_services"] == 1

    def test_statistics_after_failover(self) -> None:
        """Test statistics after a failover event."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        record.failure_count = 2
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        self.failover.mark_server_failed("sip", "tcp", "example.com", "sip.example.com", 5060)

        stats = self.failover.get_statistics()

        assert stats["total_failovers"] == 1

    def test_statistics_cache_hit_rate_no_lookups(self) -> None:
        """Test that cache_hit_rate is 0 when total_lookups is 0 (avoid division by zero)."""
        stats = self.failover.get_statistics()

        assert stats["cache_hit_rate"] == 0.0

    def test_statistics_with_enabled_config(self) -> None:
        """Test statistics reflect enabled state."""
        config = {"features": {"dns_srv_failover": {"enabled": True}}}
        with patch("pbx.features.dns_srv_failover.get_logger", return_value=MagicMock()):
            failover = DNSSRVFailover(config=config)

        stats = failover.get_statistics()

        assert stats["enabled"] is True

    def test_statistics_multiple_cached_services(self) -> None:
        """Test cached_services count with multiple entries."""
        self.failover.srv_cache["_sip._tcp.example.com"] = []
        self.failover.srv_cache["_sips._tls.example.com"] = []
        self.failover.srv_cache["_sip._udp.other.com"] = []

        stats = self.failover.get_statistics()

        assert stats["cached_services"] == 3


@pytest.mark.unit
class TestGetDnsSrvFailover:
    """Tests for the module-level get_dns_srv_failover singleton factory."""

    @patch("pbx.features.dns_srv_failover.get_logger")
    def test_creates_instance_when_none(self, mock_get_logger: MagicMock) -> None:
        """Test that a new instance is created when global is None."""
        mock_get_logger.return_value = MagicMock()

        import pbx.features.dns_srv_failover as module

        # Reset global singleton
        module._dns_srv_failover = None

        instance = get_dns_srv_failover(config={"features": {}})

        assert instance is not None
        assert isinstance(instance, DNSSRVFailover)

        # Clean up
        module._dns_srv_failover = None

    @patch("pbx.features.dns_srv_failover.get_logger")
    def test_returns_existing_instance(self, mock_get_logger: MagicMock) -> None:
        """Test that subsequent calls return the same instance."""
        mock_get_logger.return_value = MagicMock()

        import pbx.features.dns_srv_failover as module

        # Reset global singleton
        module._dns_srv_failover = None

        instance1 = get_dns_srv_failover(config={})
        instance2 = get_dns_srv_failover(config={"different": True})

        assert instance1 is instance2

        # Clean up
        module._dns_srv_failover = None

    @patch("pbx.features.dns_srv_failover.get_logger")
    def test_returns_existing_instance_with_none_config(self, mock_get_logger: MagicMock) -> None:
        """Test that passing None to an existing instance still returns it."""
        mock_get_logger.return_value = MagicMock()

        import pbx.features.dns_srv_failover as module

        module._dns_srv_failover = None

        instance1 = get_dns_srv_failover(config={})
        instance2 = get_dns_srv_failover(config=None)

        assert instance1 is instance2

        # Clean up
        module._dns_srv_failover = None

    @patch("pbx.features.dns_srv_failover.get_logger")
    def test_creates_with_none_config(self, mock_get_logger: MagicMock) -> None:
        """Test creation with None config (defaults should apply)."""
        mock_get_logger.return_value = MagicMock()

        import pbx.features.dns_srv_failover as module

        module._dns_srv_failover = None

        instance = get_dns_srv_failover(config=None)

        assert instance.enabled is False
        assert instance.check_interval == 60
        assert instance.max_failures == 3

        # Clean up
        module._dns_srv_failover = None


@pytest.mark.unit
class TestDNSSRVFailoverIntegration:
    """Integration-style tests exercising multiple methods together."""

    @patch("pbx.features.dns_srv_failover.get_logger")
    def setup_method(self, method: object, mock_get_logger: MagicMock) -> None:
        """Set up a fresh DNSSRVFailover instance for each test."""
        mock_get_logger.return_value = MagicMock()
        self.failover = DNSSRVFailover(
            config={
                "features": {
                    "dns_srv_failover": {
                        "enabled": True,
                        "check_interval": 30,
                        "max_failures": 2,
                    }
                }
            }
        )

    def test_full_lifecycle_lookup_fail_recover(self) -> None:
        """Test full lifecycle: lookup, mark failed, recover."""
        # Populate cache
        records = [
            SRVRecord(priority=10, weight=60, port=5060, target="primary.example.com"),
            SRVRecord(priority=20, weight=40, port=5060, target="backup.example.com"),
        ]
        self.failover.srv_cache["_sip._tcp.example.com"] = records

        # Select server (should be primary)
        server = self.failover.select_server("sip", "tcp", "example.com")
        assert server is not None
        assert server["target"] == "primary.example.com"

        # Mark primary as failed twice (max_failures=2)
        self.failover.mark_server_failed("sip", "tcp", "example.com", "primary.example.com", 5060)
        self.failover.mark_server_failed("sip", "tcp", "example.com", "primary.example.com", 5060)

        # Primary should now be unavailable
        assert records[0].available is False

        # Select server again (should be backup)
        server = self.failover.select_server("sip", "tcp", "example.com")
        assert server is not None
        assert server["target"] == "backup.example.com"

        # Recover primary
        self.failover.mark_server_recovered(
            "sip", "tcp", "example.com", "primary.example.com", 5060
        )
        assert records[0].available is True
        assert records[0].failure_count == 0

        # Select server again (should be primary again)
        server = self.failover.select_server("sip", "tcp", "example.com")
        assert server is not None
        assert server["target"] == "primary.example.com"

    def test_all_servers_fail(self) -> None:
        """Test behavior when all servers become unavailable."""
        records = [
            SRVRecord(priority=10, weight=60, port=5060, target="primary.example.com"),
            SRVRecord(priority=20, weight=40, port=5060, target="backup.example.com"),
        ]
        self.failover.srv_cache["_sip._tcp.example.com"] = records

        # Fail both servers
        for _ in range(2):
            self.failover.mark_server_failed(
                "sip", "tcp", "example.com", "primary.example.com", 5060
            )
        for _ in range(2):
            self.failover.mark_server_failed(
                "sip", "tcp", "example.com", "backup.example.com", 5060
            )

        # Select server should return None
        server = self.failover.select_server("sip", "tcp", "example.com")
        assert server is None

        # Verify failover count
        assert self.failover.total_failovers == 2

    def test_clear_cache_and_re_lookup(self) -> None:
        """Test clearing cache and performing a fresh lookup."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        # Verify cache has entry
        assert len(self.failover.srv_cache) == 1

        # Clear cache
        self.failover.clear_cache(service="sip", protocol="tcp", domain="example.com")

        # Verify cache is empty for that entry
        assert "_sip._tcp.example.com" not in self.failover.srv_cache

    def test_statistics_accumulate_correctly(self) -> None:
        """Test that statistics accumulate properly across operations."""
        record = SRVRecord(priority=10, weight=60, port=5060, target="sip.example.com")
        self.failover.srv_cache["_sip._tcp.example.com"] = [record]

        # Perform lookups
        self.failover.lookup_srv("sip", "tcp", "example.com")
        self.failover.lookup_srv("sip", "tcp", "example.com")
        self.failover.lookup_srv("sip", "tcp", "example.com")

        stats = self.failover.get_statistics()

        assert stats["enabled"] is True
        assert stats["total_lookups"] == 3
        assert stats["cache_hits"] == 3
        assert stats["cache_hit_rate"] == 1.0
        assert stats["cached_services"] == 1

    def test_select_server_among_same_priority_different_weights(self) -> None:
        """Test server selection among records with same priority but varying weights."""
        records = [
            SRVRecord(priority=10, weight=90, port=5060, target="heavy.example.com"),
            SRVRecord(priority=10, weight=10, port=5060, target="light.example.com"),
        ]
        self.failover.srv_cache["_sip._tcp.example.com"] = records

        # Run many selections and ensure distribution
        selections = {"heavy.example.com": 0, "light.example.com": 0}
        for _ in range(100):
            server = self.failover.select_server("sip", "tcp", "example.com")
            assert server is not None
            selections[server["target"]] += 1

        # Heavy should generally be selected more often
        assert selections["heavy.example.com"] > selections["light.example.com"]
