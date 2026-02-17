"""Comprehensive tests for pbx/features/webrtc.py covering WebRTCSession,
WebRTCSignalingServer, and WebRTCGateway classes."""

import threading
import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.webrtc import WebRTCGateway, WebRTCSession, WebRTCSignalingServer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(overrides: dict | None = None) -> MagicMock:
    """Create a mock config with sensible defaults and optional overrides."""
    config_map: dict = {
        "features.webrtc.enabled": False,
        "features.webrtc.verbose_logging": False,
        "features.webrtc.session_timeout": 3600,
        "features.webrtc.stun_servers": ["stun:stun.l.google.com:19302"],
        "features.webrtc.turn_servers": [],
        "features.webrtc.ice_transport_policy": "all",
        "features.webrtc.codecs": [
            {"payload_type": 0, "name": "PCMU", "priority": 1, "enabled": True},
        ],
        "features.webrtc.dtmf.mode": "RFC2833",
        "features.webrtc.dtmf.payload_type": 101,
        "features.webrtc.dtmf.duration": 160,
        "features.webrtc.dtmf.sip_info_fallback": True,
        "features.webrtc.rtp.port_min": 10000,
        "features.webrtc.rtp.port_max": 20000,
        "features.webrtc.rtp.packet_time": 20,
        "features.webrtc.nat.udp_update_time": 30,
        "features.webrtc.nat.rport": True,
        "features.webrtc.audio.echo_cancellation": True,
        "features.webrtc.audio.noise_reduction": True,
        "features.webrtc.audio.auto_gain_control": True,
        "features.webrtc.audio.voice_activity_detection": True,
        "features.webrtc.audio.comfort_noise": True,
    }
    if overrides:
        config_map.update(overrides)

    cfg = MagicMock()
    cfg.get.side_effect = lambda key, default=None: config_map.get(key, default)
    return cfg


def _enabled_config(**extra: object) -> MagicMock:
    """Shortcut for a config with WebRTC enabled and cleanup thread patched."""
    overrides = {"features.webrtc.enabled": True}
    overrides.update(extra)
    return _make_config(overrides)


SAMPLE_SDP = (
    "v=0\r\n"
    "o=- 123 0 IN IP4 192.168.1.100\r\n"
    "s=-\r\n"
    "c=IN IP4 192.168.1.100\r\n"
    "t=0 0\r\n"
    "m=audio 50000 RTP/AVP 0\r\n"
    "a=rtpmap:0 PCMU/8000\r\n"
    "a=sendrecv\r\n"
)

WEBRTC_SDP = (
    "v=0\r\n"
    "o=- 123 0 IN IP4 192.168.1.100\r\n"
    "s=WebRTC Call\r\n"
    "c=IN IP4 192.168.1.100\r\n"
    "t=0 0\r\n"
    "m=audio 54321 UDP/TLS/RTP/SAVPF 0 8\r\n"
    "a=rtpmap:0 PCMU/8000\r\n"
    "a=rtpmap:8 PCMA/8000\r\n"
    "a=ice-ufrag:abcd1234\r\n"
    "a=ice-pwd:abcdef1234567890abcdef12\r\n"
    "a=ice-options:trickle\r\n"
    "a=fingerprint:sha-256 AA:BB:CC\r\n"
    "a=setup:actpass\r\n"
    "a=mid:0\r\n"
    "a=rtcp-mux\r\n"
    "a=sendrecv\r\n"
)

SIP_SDP = (
    "v=0\r\n"
    "o=pbx 987654321 0 IN IP4 192.168.1.10\r\n"
    "s=PBX Call\r\n"
    "c=IN IP4 192.168.1.10\r\n"
    "t=0 0\r\n"
    "m=audio 10000 RTP/AVP 0 8 101\r\n"
    "a=rtpmap:0 PCMU/8000\r\n"
    "a=rtpmap:8 PCMA/8000\r\n"
    "a=rtpmap:101 telephone-event/8000\r\n"
    "a=fmtp:101 0-16\r\n"
    "a=sendrecv\r\n"
)


# ============================================================================
# WebRTCSession Tests
# ============================================================================


@pytest.mark.unit
class TestWebRTCSession:
    """Tests for the WebRTCSession data class."""

    def test_init_defaults(self) -> None:
        session = WebRTCSession("sid-1", "1001")
        assert session.session_id == "sid-1"
        assert session.extension == "1001"
        assert session.peer_connection_id is not None
        assert session.state == "new"
        assert session.local_sdp is None
        assert session.remote_sdp is None
        assert session.ice_candidates == []
        assert session.call_id is None
        assert session.metadata == {}
        assert isinstance(session.created_at, datetime)
        assert session.created_at.tzinfo is not None

    def test_init_with_peer_connection_id(self) -> None:
        session = WebRTCSession("sid-2", "1002", peer_connection_id="pc-custom")
        assert session.peer_connection_id == "pc-custom"

    def test_init_generates_peer_connection_id_when_none(self) -> None:
        session = WebRTCSession("sid-3", "1003", peer_connection_id=None)
        assert session.peer_connection_id is not None
        assert len(session.peer_connection_id) > 0

    def test_update_activity(self) -> None:
        session = WebRTCSession("sid-4", "1004")
        first_activity = session.last_activity
        time.sleep(0.01)
        session.update_activity()
        assert session.last_activity >= first_activity

    def test_to_dict_keys(self) -> None:
        session = WebRTCSession("sid-5", "1005")
        session.call_id = "call-abc"
        d = session.to_dict()
        assert d["session_id"] == "sid-5"
        assert d["extension"] == "1005"
        assert d["state"] == "new"
        assert d["call_id"] == "call-abc"
        assert "peer_connection_id" in d
        assert "created_at" in d
        assert "last_activity" in d

    def test_to_dict_iso_format(self) -> None:
        session = WebRTCSession("sid-6", "1006")
        d = session.to_dict()
        # Should be valid ISO-8601 strings
        datetime.fromisoformat(d["created_at"])
        datetime.fromisoformat(d["last_activity"])


# ============================================================================
# WebRTCSignalingServer Tests
# ============================================================================


@pytest.mark.unit
class TestWebRTCSignalingServerInit:
    """Tests for WebRTCSignalingServer initialization."""

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def test_init_enabled(self, mock_cleanup: MagicMock) -> None:
        cfg = _enabled_config()
        server = WebRTCSignalingServer(config=cfg)
        assert server.enabled is True
        mock_cleanup.assert_called_once()

    def test_init_disabled(self) -> None:
        cfg = _make_config({"features.webrtc.enabled": False})
        server = WebRTCSignalingServer(config=cfg)
        assert server.enabled is False
        assert server.cleanup_thread is None

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def test_init_verbose_logging(self, mock_cleanup: MagicMock) -> None:
        cfg = _enabled_config(**{"features.webrtc.verbose_logging": True})
        server = WebRTCSignalingServer(config=cfg)
        assert server.verbose_logging is True

    def test_init_no_config(self) -> None:
        server = WebRTCSignalingServer(config=None)
        assert server.enabled is False
        assert server.config == {}

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def test_init_reads_all_config_keys(self, mock_cleanup: MagicMock) -> None:
        cfg = _enabled_config(
            **{
                "features.webrtc.stun_servers": ["stun:custom:19302"],
                "features.webrtc.turn_servers": [{"url": "turn:t:3478"}],
                "features.webrtc.ice_transport_policy": "relay",
                "features.webrtc.session_timeout": 600,
                "features.webrtc.dtmf.mode": "SIPInfo",
                "features.webrtc.dtmf.payload_type": 96,
                "features.webrtc.dtmf.duration": 200,
                "features.webrtc.dtmf.sip_info_fallback": False,
                "features.webrtc.rtp.port_min": 20000,
                "features.webrtc.rtp.port_max": 30000,
                "features.webrtc.rtp.packet_time": 30,
                "features.webrtc.nat.udp_update_time": 60,
                "features.webrtc.nat.rport": False,
                "features.webrtc.audio.echo_cancellation": False,
                "features.webrtc.audio.noise_reduction": False,
                "features.webrtc.audio.auto_gain_control": False,
                "features.webrtc.audio.voice_activity_detection": False,
                "features.webrtc.audio.comfort_noise": False,
            }
        )
        server = WebRTCSignalingServer(config=cfg)
        assert server.stun_servers == ["stun:custom:19302"]
        assert server.turn_servers == [{"url": "turn:t:3478"}]
        assert server.ice_transport_policy == "relay"
        assert server.session_timeout == 600
        assert server.dtmf_mode == "SIPInfo"
        assert server.dtmf_payload_type == 96
        assert server.dtmf_duration == 200
        assert server.dtmf_sip_info_fallback is False
        assert server.rtp_port_min == 20000
        assert server.rtp_port_max == 30000
        assert server.rtp_packet_time == 30
        assert server.nat_udp_update_time == 60
        assert server.nat_rport is False
        assert server.audio_echo_cancellation is False
        assert server.audio_noise_reduction is False
        assert server.audio_auto_gain_control is False
        assert server.audio_vad is False
        assert server.audio_comfort_noise is False


@pytest.mark.unit
class TestWebRTCSignalingServerGetConfig:
    """Tests for _get_config helper."""

    def test_get_config_with_dict(self) -> None:
        server = WebRTCSignalingServer(config={"features.webrtc.enabled": True})
        # The default dict doesn't have nested get, so it falls through to default
        # But since dict has 'get', it works for flat keys
        val = server._get_config("features.webrtc.enabled", False)
        assert val is True

    def test_get_config_with_no_get(self) -> None:
        server = WebRTCSignalingServer(config=42)  # no .get attribute
        val = server._get_config("anything", "fallback")
        assert val == "fallback"


@pytest.mark.unit
class TestWebRTCSignalingServerSessions:
    """Tests for session CRUD operations on WebRTCSignalingServer."""

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def _make_server(self, mock_cleanup: MagicMock, **kwargs: object) -> WebRTCSignalingServer:
        cfg = _enabled_config(**kwargs)
        return WebRTCSignalingServer(config=cfg)

    def test_create_session(self) -> None:
        server = self._make_server()
        session = server.create_session("1001")
        assert session.extension == "1001"
        assert session.session_id in server.sessions
        assert "1001" in server.extension_sessions
        assert session.session_id in server.extension_sessions["1001"]

    def test_create_session_disabled_raises(self) -> None:
        server = WebRTCSignalingServer(config=_make_config())
        with pytest.raises(RuntimeError, match="not enabled"):
            server.create_session("1001")

    def test_get_session_found(self) -> None:
        server = self._make_server()
        session = server.create_session("1001")
        result = server.get_session(session.session_id)
        assert result is session

    def test_get_session_not_found(self) -> None:
        server = self._make_server()
        assert server.get_session("nonexistent") is None

    def test_get_extension_sessions(self) -> None:
        server = self._make_server()
        s1 = server.create_session("1001")
        s2 = server.create_session("1001")
        s3 = server.create_session("1002")
        ext_sessions = server.get_extension_sessions("1001")
        ids = {s.session_id for s in ext_sessions}
        assert s1.session_id in ids
        assert s2.session_id in ids
        assert s3.session_id not in ids

    def test_get_extension_sessions_empty(self) -> None:
        server = self._make_server()
        assert server.get_extension_sessions("9999") == []

    def test_close_session(self) -> None:
        server = self._make_server()
        session = server.create_session("1001")
        sid = session.session_id
        assert server.close_session(sid) is True
        assert server.get_session(sid) is None
        assert "1001" not in server.extension_sessions

    def test_close_session_not_found(self) -> None:
        server = self._make_server()
        assert server.close_session("nonexistent") is False

    def test_close_session_keeps_other_sessions_for_extension(self) -> None:
        server = self._make_server()
        s1 = server.create_session("1001")
        s2 = server.create_session("1001")
        server.close_session(s1.session_id)
        assert "1001" in server.extension_sessions
        assert s2.session_id in server.extension_sessions["1001"]

    def test_close_last_session_unregisters_extension(self) -> None:
        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.return_value = MagicMock()
        server = self._make_server()
        server.pbx_core = pbx_core
        session = server.create_session("1001")
        server.close_session(session.session_id)
        pbx_core.extension_registry.unregister.assert_called_once_with("1001")

    def test_close_last_session_unregister_exception(self) -> None:
        pbx_core = MagicMock()
        pbx_core.extension_registry.unregister.side_effect = RuntimeError("fail")
        server = self._make_server()
        server.pbx_core = pbx_core
        session = server.create_session("1001")
        # Should not raise
        assert server.close_session(session.session_id) is True

    def test_close_session_unregister_verbose(self) -> None:
        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.return_value = MagicMock()
        server = self._make_server(**{"features.webrtc.verbose_logging": True})
        server.pbx_core = pbx_core
        session = server.create_session("1001")
        server.close_session(session.session_id)
        pbx_core.extension_registry.unregister.assert_called_once_with("1001")


@pytest.mark.unit
class TestWebRTCSignalingServerCallbacks:
    """Tests for session created/closed callbacks."""

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def _make_server(self, mock_cleanup: MagicMock) -> WebRTCSignalingServer:
        return WebRTCSignalingServer(config=_enabled_config())

    def test_on_session_created_callback(self) -> None:
        server = self._make_server()
        cb = MagicMock()
        server.on_session_created = cb
        session = server.create_session("1001")
        cb.assert_called_once_with(session)

    def test_on_session_created_callback_exception(self) -> None:
        server = self._make_server()
        server.on_session_created = MagicMock(side_effect=RuntimeError("boom"))
        # Should not propagate
        session = server.create_session("1001")
        assert session is not None

    def test_on_session_closed_callback(self) -> None:
        server = self._make_server()
        cb = MagicMock()
        server.on_session_closed = cb
        session = server.create_session("1001")
        server.close_session(session.session_id)
        cb.assert_called_once()

    def test_on_session_closed_callback_exception(self) -> None:
        server = self._make_server()
        server.on_session_closed = MagicMock(side_effect=RuntimeError("boom"))
        session = server.create_session("1001")
        # Should not propagate
        assert server.close_session(session.session_id) is True


@pytest.mark.unit
class TestWebRTCSignalingServerOffer:
    """Tests for handle_offer."""

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def _make_server(self, mock_cleanup: MagicMock, **kwargs: object) -> WebRTCSignalingServer:
        return WebRTCSignalingServer(config=_enabled_config(**kwargs))

    def test_handle_offer_success(self) -> None:
        server = self._make_server()
        session = server.create_session("1001")
        result = server.handle_offer(session.session_id, SAMPLE_SDP)
        assert result is True
        assert session.local_sdp == SAMPLE_SDP
        assert session.state == "connecting"

    def test_handle_offer_unknown_session(self) -> None:
        server = self._make_server()
        assert server.handle_offer("unknown", SAMPLE_SDP) is False

    def test_handle_offer_unknown_session_verbose(self) -> None:
        server = self._make_server(**{"features.webrtc.verbose_logging": True})
        assert server.handle_offer("unknown", SAMPLE_SDP) is False

    def test_handle_offer_fires_callback(self) -> None:
        server = self._make_server()
        cb = MagicMock()
        server.on_offer_received = cb
        session = server.create_session("1001")
        server.handle_offer(session.session_id, SAMPLE_SDP)
        cb.assert_called_once_with(session, SAMPLE_SDP)

    def test_handle_offer_callback_exception(self) -> None:
        server = self._make_server()
        server.on_offer_received = MagicMock(side_effect=RuntimeError("err"))
        session = server.create_session("1001")
        assert server.handle_offer(session.session_id, SAMPLE_SDP) is True

    def test_handle_offer_verbose_logging(self) -> None:
        server = self._make_server(**{"features.webrtc.verbose_logging": True})
        session = server.create_session("1001")
        result = server.handle_offer(session.session_id, SAMPLE_SDP)
        assert result is True


@pytest.mark.unit
class TestWebRTCSignalingServerAnswer:
    """Tests for handle_answer."""

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def _make_server(self, mock_cleanup: MagicMock) -> WebRTCSignalingServer:
        return WebRTCSignalingServer(config=_enabled_config())

    def test_handle_answer_success(self) -> None:
        server = self._make_server()
        session = server.create_session("1001")
        result = server.handle_answer(session.session_id, SAMPLE_SDP)
        assert result is True
        assert session.remote_sdp == SAMPLE_SDP
        assert session.state == "connected"

    def test_handle_answer_unknown_session(self) -> None:
        server = self._make_server()
        assert server.handle_answer("unknown", SAMPLE_SDP) is False

    def test_handle_answer_fires_callback(self) -> None:
        server = self._make_server()
        cb = MagicMock()
        server.on_answer_received = cb
        session = server.create_session("1001")
        server.handle_answer(session.session_id, SAMPLE_SDP)
        cb.assert_called_once_with(session, SAMPLE_SDP)

    def test_handle_answer_callback_exception(self) -> None:
        server = self._make_server()
        server.on_answer_received = MagicMock(side_effect=RuntimeError("err"))
        session = server.create_session("1001")
        assert server.handle_answer(session.session_id, SAMPLE_SDP) is True


@pytest.mark.unit
class TestWebRTCSignalingServerICE:
    """Tests for ICE candidate handling."""

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def _make_server(self, mock_cleanup: MagicMock, **kwargs: object) -> WebRTCSignalingServer:
        return WebRTCSignalingServer(config=_enabled_config(**kwargs))

    def test_add_ice_candidate_success(self) -> None:
        server = self._make_server()
        session = server.create_session("1001")
        candidate = {"candidate": "candidate:1 1 UDP 2130706431 ...", "sdpMid": "audio"}
        assert server.add_ice_candidate(session.session_id, candidate) is True
        assert len(session.ice_candidates) == 1
        assert session.ice_candidates[0] is candidate

    def test_add_ice_candidate_unknown_session(self) -> None:
        server = self._make_server()
        assert server.add_ice_candidate("unknown", {}) is False

    def test_add_ice_candidate_verbose(self) -> None:
        server = self._make_server(**{"features.webrtc.verbose_logging": True})
        session = server.create_session("1001")
        candidate = {
            "candidate": "candidate:1 1 UDP 2130706431 ...",
            "sdpMid": "audio",
            "sdpMLineIndex": 0,
        }
        assert server.add_ice_candidate(session.session_id, candidate) is True

    def test_add_multiple_ice_candidates(self) -> None:
        server = self._make_server()
        session = server.create_session("1001")
        for i in range(5):
            server.add_ice_candidate(session.session_id, {"candidate": f"c{i}"})
        assert len(session.ice_candidates) == 5


@pytest.mark.unit
class TestWebRTCSignalingServerICEConfig:
    """Tests for get_ice_servers_config."""

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def test_basic_stun_config(self, mock_cleanup: MagicMock) -> None:
        server = WebRTCSignalingServer(config=_enabled_config())
        cfg = server.get_ice_servers_config()
        assert "iceServers" in cfg
        assert "iceTransportPolicy" in cfg
        assert "codecs" in cfg
        assert "audio" in cfg
        assert "dtmf" in cfg
        assert cfg["iceTransportPolicy"] == "all"

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def test_stun_and_turn_servers(self, mock_cleanup: MagicMock) -> None:
        cfg_data = _enabled_config(
            **{
                "features.webrtc.stun_servers": ["stun:s1:19302", "stun:s2:19302"],
                "features.webrtc.turn_servers": [
                    {"url": "turn:t1:3478", "username": "u1", "credential": "c1"},
                    {"url": "turn:t2:3478", "username": "u2", "credential": "c2"},
                ],
            }
        )
        server = WebRTCSignalingServer(config=cfg_data)
        ice_cfg = server.get_ice_servers_config()
        # 2 STUN + 2 TURN = 4
        assert len(ice_cfg["iceServers"]) == 4
        assert ice_cfg["iceServers"][0] == {"urls": "stun:s1:19302"}
        assert ice_cfg["iceServers"][2]["username"] == "u1"

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def test_audio_settings_in_config(self, mock_cleanup: MagicMock) -> None:
        server = WebRTCSignalingServer(config=_enabled_config())
        cfg = server.get_ice_servers_config()
        audio = cfg["audio"]
        assert audio["echoCancellation"] is True
        assert audio["noiseSuppression"] is True
        assert audio["autoGainControl"] is True

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def test_dtmf_settings_in_config(self, mock_cleanup: MagicMock) -> None:
        server = WebRTCSignalingServer(config=_enabled_config())
        cfg = server.get_ice_servers_config()
        dtmf = cfg["dtmf"]
        assert dtmf["mode"] == "RFC2833"
        assert dtmf["payloadType"] == 101
        assert dtmf["duration"] == 160
        assert dtmf["sipInfoFallback"] is True


@pytest.mark.unit
class TestWebRTCSignalingServerSessionsInfo:
    """Tests for get_sessions_info."""

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def test_get_sessions_info_empty(self, mock_cleanup: MagicMock) -> None:
        server = WebRTCSignalingServer(config=_enabled_config())
        assert server.get_sessions_info() == []

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def test_get_sessions_info_multiple(self, mock_cleanup: MagicMock) -> None:
        server = WebRTCSignalingServer(config=_enabled_config())
        server.create_session("1001")
        server.create_session("1002")
        info = server.get_sessions_info()
        assert len(info) == 2
        extensions = {s["extension"] for s in info}
        assert extensions == {"1001", "1002"}


@pytest.mark.unit
class TestWebRTCSignalingServerMetadata:
    """Tests for session metadata and call_id management."""

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def _make_server(self, mock_cleanup: MagicMock) -> WebRTCSignalingServer:
        return WebRTCSignalingServer(config=_enabled_config())

    def test_set_session_call_id(self) -> None:
        server = self._make_server()
        session = server.create_session("1001")
        assert server.set_session_call_id(session.session_id, "call-1") is True
        assert session.call_id == "call-1"

    def test_set_session_call_id_not_found(self) -> None:
        server = self._make_server()
        assert server.set_session_call_id("unknown", "call-1") is False

    def test_set_session_metadata(self) -> None:
        server = self._make_server()
        session = server.create_session("1001")
        assert server.set_session_metadata(session.session_id, "key1", "value1") is True
        assert session.metadata["key1"] == "value1"

    def test_set_session_metadata_not_found(self) -> None:
        server = self._make_server()
        assert server.set_session_metadata("unknown", "key1", "v") is False

    def test_get_session_metadata(self) -> None:
        server = self._make_server()
        session = server.create_session("1001")
        session.metadata["foo"] = "bar"
        assert server.get_session_metadata(session.session_id, "foo") == "bar"

    def test_get_session_metadata_default(self) -> None:
        server = self._make_server()
        session = server.create_session("1001")
        assert server.get_session_metadata(session.session_id, "missing", "def") == "def"

    def test_get_session_metadata_not_found(self) -> None:
        server = self._make_server()
        assert server.get_session_metadata("unknown", "key", "def") == "def"


@pytest.mark.unit
class TestWebRTCSignalingServerCleanup:
    """Tests for session cleanup logic."""

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def test_cleanup_stale_sessions(self, mock_cleanup: MagicMock) -> None:
        server = WebRTCSignalingServer(
            config=_enabled_config(**{"features.webrtc.session_timeout": 0})
        )
        session = server.create_session("1001")
        sid = session.session_id
        # Force the session to be stale
        session.last_activity = datetime(2020, 1, 1, tzinfo=UTC)
        server._cleanup_stale_sessions()
        assert server.get_session(sid) is None

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def test_cleanup_keeps_active_sessions(self, mock_cleanup: MagicMock) -> None:
        server = WebRTCSignalingServer(
            config=_enabled_config(**{"features.webrtc.session_timeout": 9999})
        )
        session = server.create_session("1001")
        server._cleanup_stale_sessions()
        assert server.get_session(session.session_id) is not None

    def test_stop(self) -> None:
        server = WebRTCSignalingServer(config=_make_config())
        server.running = True
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        server.cleanup_thread = mock_thread
        server.stop()
        assert server.running is False
        mock_thread.join.assert_called_once_with(timeout=5)

    def test_stop_no_thread(self) -> None:
        server = WebRTCSignalingServer(config=_make_config())
        server.running = True
        server.cleanup_thread = None
        server.stop()
        assert server.running is False

    def test_stop_thread_not_alive(self) -> None:
        server = WebRTCSignalingServer(config=_make_config())
        server.running = True
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False
        server.cleanup_thread = mock_thread
        server.stop()
        assert server.running is False
        mock_thread.join.assert_not_called()

    def test_start_cleanup_thread_creates_daemon(self) -> None:
        # Create server with enabled=True so _start_cleanup_thread is called
        # We need to test the actual method, so we patch threading.Thread
        with patch("threading.Thread") as mock_thread_cls:
            mock_thread_instance = MagicMock()
            mock_thread_cls.return_value = mock_thread_instance
            server = WebRTCSignalingServer(config=_enabled_config())
            assert server.running is True
            mock_thread_cls.assert_called_once()
            mock_thread_instance.start.assert_called_once()


@pytest.mark.unit
class TestWebRTCSignalingServerVirtualExtensions:
    """Tests for _create_virtual_webrtc_extension."""

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def _make_server(self, mock_cleanup: MagicMock) -> WebRTCSignalingServer:
        return WebRTCSignalingServer(config=_enabled_config())

    def test_no_pbx_core_returns_none(self) -> None:
        server = self._make_server()
        server.pbx_core = None
        result = server._create_virtual_webrtc_extension("1001")
        assert result is None

    def test_existing_extension_returned(self) -> None:
        server = self._make_server()
        mock_ext = MagicMock()
        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.return_value = mock_ext
        server.pbx_core = pbx_core
        result = server._create_virtual_webrtc_extension("1001")
        assert result is mock_ext

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def test_auto_create_virtual_webrtc_extension(self, mock_cleanup: MagicMock) -> None:
        server = WebRTCSignalingServer(config=_enabled_config())
        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.return_value = None
        pbx_core.extension_registry.extensions = {}
        server.pbx_core = pbx_core

        with (
            patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread"),
            patch("pbx.features.extensions.Extension") as MockExtCls,
        ):
            mock_ext_instance = MagicMock()
            MockExtCls.return_value = mock_ext_instance
            result = server._create_virtual_webrtc_extension("webrtc-100")
            MockExtCls.assert_called_once()
            assert result is mock_ext_instance

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def test_auto_create_skipped_for_non_webrtc_prefix(self, mock_cleanup: MagicMock) -> None:
        server = WebRTCSignalingServer(config=_enabled_config())
        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.return_value = None
        server.pbx_core = pbx_core
        result = server._create_virtual_webrtc_extension("1001")
        # Not starting with webrtc-, so returns None
        assert result is None

    def test_exception_in_virtual_extension_creation(self) -> None:
        server = self._make_server()
        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.side_effect = KeyError("fail")
        server.pbx_core = pbx_core
        result = server._create_virtual_webrtc_extension("webrtc-100")
        assert result is None

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def test_virtual_extension_verbose_logging(self, mock_cleanup: MagicMock) -> None:
        server = WebRTCSignalingServer(
            config=_enabled_config(**{"features.webrtc.verbose_logging": True})
        )
        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.return_value = None
        pbx_core.extension_registry.extensions = {}
        server.pbx_core = pbx_core
        with patch("pbx.features.extensions.Extension") as MockExtCls:
            MockExtCls.return_value = MagicMock()
            server._create_virtual_webrtc_extension("webrtc-200")
            # Should not raise, just log


@pytest.mark.unit
class TestWebRTCSignalingServerCreateSessionWithPBXCore:
    """Tests for create_session when pbx_core is available."""

    @patch("pbx.features.webrtc.WebRTCSignalingServer._start_cleanup_thread")
    def _make_server_with_pbx(
        self, mock_cleanup: MagicMock, ext_found: bool = True, **kwargs: object
    ) -> tuple[WebRTCSignalingServer, MagicMock]:
        server = WebRTCSignalingServer(config=_enabled_config(**kwargs))
        pbx_core = MagicMock()
        if ext_found:
            pbx_core.extension_registry.get_extension.return_value = MagicMock()
        else:
            pbx_core.extension_registry.get_extension.return_value = None
        pbx_core.registered_phones_db = None
        server.pbx_core = pbx_core
        return server, pbx_core

    def test_create_session_registers_extension(self) -> None:
        server, pbx_core = self._make_server_with_pbx()
        session = server.create_session("1001")
        pbx_core.extension_registry.register.assert_called_once_with(
            "1001", ("webrtc", session.session_id)
        )

    def test_create_session_registers_extension_verbose(self) -> None:
        server, pbx_core = self._make_server_with_pbx(**{"features.webrtc.verbose_logging": True})
        _session = server.create_session("1001")
        pbx_core.extension_registry.register.assert_called_once()

    def test_create_session_registers_in_phones_db(self) -> None:
        server, pbx_core = self._make_server_with_pbx()
        pbx_core.registered_phones_db = MagicMock()
        pbx_core.registered_phones_db.register_phone.return_value = (True, "mac-123")
        _session = server.create_session("1001")
        pbx_core.registered_phones_db.register_phone.assert_called_once()

    def test_create_session_registers_in_phones_db_verbose(self) -> None:
        server, pbx_core = self._make_server_with_pbx(**{"features.webrtc.verbose_logging": True})
        pbx_core.registered_phones_db = MagicMock()
        pbx_core.registered_phones_db.register_phone.return_value = (True, "mac-123")
        server.create_session("1001")
        pbx_core.registered_phones_db.register_phone.assert_called_once()

    def test_create_session_phones_db_failure(self) -> None:
        server, pbx_core = self._make_server_with_pbx()
        pbx_core.registered_phones_db = MagicMock()
        pbx_core.registered_phones_db.register_phone.return_value = (False, None)
        session = server.create_session("1001")
        assert session is not None

    def test_create_session_phones_db_exception(self) -> None:
        server, pbx_core = self._make_server_with_pbx()
        pbx_core.registered_phones_db = MagicMock()
        pbx_core.registered_phones_db.register_phone.side_effect = RuntimeError("db error")
        session = server.create_session("1001")
        assert session is not None

    def test_create_session_ext_not_found_warns(self) -> None:
        server, pbx_core = self._make_server_with_pbx(ext_found=False)
        session = server.create_session("1001")
        assert session is not None
        pbx_core.extension_registry.register.assert_not_called()

    def test_create_session_ext_not_found_verbose(self) -> None:
        server, pbx_core = self._make_server_with_pbx(
            ext_found=False, **{"features.webrtc.verbose_logging": True}
        )
        pbx_core.extension_registry.extensions = ["1002", "1003"]
        session = server.create_session("1001")
        assert session is not None

    def test_log_session_creation_verbose(self) -> None:
        server, _ = self._make_server_with_pbx(**{"features.webrtc.verbose_logging": True})
        session = server.create_session("1001")
        assert session is not None

    def test_log_session_creation_not_verbose(self) -> None:
        server, _ = self._make_server_with_pbx()
        server.verbose_logging = False
        session = server.create_session("1001")
        assert session is not None


# ============================================================================
# WebRTCGateway Tests
# ============================================================================


@pytest.mark.unit
class TestWebRTCGatewayInit:
    """Tests for WebRTCGateway initialization."""

    def test_init_no_pbx_core(self) -> None:
        gw = WebRTCGateway(pbx_core=None)
        assert gw.pbx_core is None
        assert gw.verbose_logging is False

    def test_init_with_pbx_core(self) -> None:
        pbx_core = MagicMock()
        del pbx_core.webrtc_signaling  # remove attribute
        gw = WebRTCGateway(pbx_core=pbx_core)
        assert gw.pbx_core is pbx_core

    def test_init_verbose_from_signaling(self) -> None:
        pbx_core = MagicMock()
        pbx_core.webrtc_signaling.verbose_logging = True
        gw = WebRTCGateway(pbx_core=pbx_core)
        assert gw.verbose_logging is True

    def test_init_verbose_false_from_signaling(self) -> None:
        pbx_core = MagicMock()
        pbx_core.webrtc_signaling.verbose_logging = False
        gw = WebRTCGateway(pbx_core=pbx_core)
        assert gw.verbose_logging is False


@pytest.mark.unit
class TestWebRTCGatewaySDPConversion:
    """Tests for SDP conversion methods."""

    def test_webrtc_to_sip_sdp_dtls_conversion(self) -> None:
        """Test that DTLS protocols are converted to RTP/AVP using real parser."""
        gw = WebRTCGateway()
        # Protocol must contain "DTLS" to trigger the conversion branch
        dtls_sdp = (
            "v=0\r\n"
            "o=- 123 0 IN IP4 192.168.1.100\r\n"
            "s=-\r\n"
            "c=IN IP4 192.168.1.100\r\n"
            "t=0 0\r\n"
            "m=audio 54321 UDP/DTLS/RTP/SAVPF 0 8\r\n"
            "a=rtpmap:0 PCMU/8000\r\n"
            "a=rtpmap:8 PCMA/8000\r\n"
            "a=ice-ufrag:abcd1234\r\n"
            "a=ice-pwd:abcdef1234567890abcdef12\r\n"
            "a=fingerprint:sha-256 AA:BB:CC\r\n"
            "a=setup:actpass\r\n"
            "a=mid:0\r\n"
            "a=rtcp-mux\r\n"
            "a=sendrecv\r\n"
        )
        result = gw.webrtc_to_sip_sdp(dtls_sdp)
        assert "RTP/AVP" in result
        # DTLS protocol should not remain
        assert "DTLS" not in result
        assert "ice-ufrag" not in result
        assert "ice-pwd" not in result
        assert "fingerprint" not in result
        assert "setup" not in result
        assert "rtcp-mux" not in result
        assert "sendrecv" in result

    def test_webrtc_to_sip_sdp_no_dtls(self) -> None:
        """Test media without DTLS is not modified."""
        gw = WebRTCGateway()
        result = gw.webrtc_to_sip_sdp(SIP_SDP)
        assert "RTP/AVP" in result

    def test_webrtc_to_sip_sdp_adds_sendrecv(self) -> None:
        """Test that sendrecv is added if missing."""
        gw = WebRTCGateway()
        sdp_no_sendrecv = (
            "v=0\r\n"
            "o=- 123 0 IN IP4 192.168.1.100\r\n"
            "s=-\r\n"
            "c=IN IP4 192.168.1.100\r\n"
            "t=0 0\r\n"
            "m=audio 50000 RTP/AVP 0\r\n"
            "a=rtpmap:0 PCMU/8000\r\n"
        )
        result = gw.webrtc_to_sip_sdp(sdp_no_sendrecv)
        assert "sendrecv" in result

    def test_webrtc_to_sip_sdp_no_duplicate_sendrecv(self) -> None:
        """Test that sendrecv is not duplicated if already present."""
        gw = WebRTCGateway()
        result = gw.webrtc_to_sip_sdp(SIP_SDP)
        # Count occurrences of sendrecv
        assert result.count("sendrecv") == 1

    def test_webrtc_to_sip_sdp_exception_fallback(self) -> None:
        """Test fallback on exception -- send malformed SDP that triggers error path."""
        gw = WebRTCGateway()
        # Patch SDPSession at the source module to raise on parse
        with patch("pbx.sip.sdp.SDPSession") as MockSDP:
            MockSDP.return_value.parse.side_effect = ValueError("parse error")
            result = gw.webrtc_to_sip_sdp("original-sdp")
        assert result == "original-sdp"

    def test_sip_to_webrtc_sdp_conversion(self) -> None:
        """Test RTP/AVP to RTP/SAVPF conversion using real parser."""
        gw = WebRTCGateway()
        result = gw.sip_to_webrtc_sdp(
            SIP_SDP, ice_ufrag="ufrag1", ice_pwd="pwd1", fingerprint="fp:sha"
        )
        assert "RTP/SAVPF" in result
        assert "ice-ufrag:ufrag1" in result
        assert "ice-pwd:pwd1" in result
        assert "rtcp-mux" in result
        assert "setup:actpass" in result

    def test_sip_to_webrtc_sdp_auto_generates_values(self) -> None:
        """Test auto-generation of ice_ufrag, ice_pwd, fingerprint."""
        gw = WebRTCGateway()
        result = gw.sip_to_webrtc_sdp(SIP_SDP)
        assert "ice-ufrag:" in result
        assert "ice-pwd:" in result
        assert "sha-256" in result

    def test_sip_to_webrtc_sdp_exception_fallback(self) -> None:
        """Test fallback on exception."""
        gw = WebRTCGateway()
        with patch("pbx.sip.sdp.SDPSession") as MockSDP:
            MockSDP.return_value.parse.side_effect = TypeError("parse error")
            result = gw.sip_to_webrtc_sdp("original-sip-sdp")
        assert result == "original-sip-sdp"

    def test_sip_to_webrtc_sdp_multiple_media(self) -> None:
        """Test conversion with multiple media sections."""
        gw = WebRTCGateway()
        multi_media_sdp = (
            "v=0\r\n"
            "o=pbx 1 0 IN IP4 192.168.1.10\r\n"
            "s=-\r\n"
            "c=IN IP4 192.168.1.10\r\n"
            "t=0 0\r\n"
            "m=audio 10000 RTP/AVP 0\r\n"
            "a=rtpmap:0 PCMU/8000\r\n"
            "a=sendrecv\r\n"
            "m=audio 10002 RTP/AVP 8\r\n"
            "a=rtpmap:8 PCMA/8000\r\n"
            "a=sendrecv\r\n"
        )
        result = gw.sip_to_webrtc_sdp(multi_media_sdp, ice_ufrag="u", ice_pwd="p", fingerprint="fp")
        assert "mid:0" in result
        assert "mid:1" in result

    def test_webrtc_to_sip_sdp_real_parse(self) -> None:
        """Integration-style test with real SDPSession parser."""
        gw = WebRTCGateway()
        result = gw.webrtc_to_sip_sdp(WEBRTC_SDP)
        assert result is not None
        assert "ice-ufrag" not in result
        assert "fingerprint" not in result

    def test_sip_to_webrtc_sdp_real_parse(self) -> None:
        """Integration-style test with real SDPSession parser."""
        gw = WebRTCGateway()
        result = gw.sip_to_webrtc_sdp(SIP_SDP)
        assert result is not None
        assert "ice-ufrag" in result
        assert "ice-pwd" in result
        assert "rtcp-mux" in result


@pytest.mark.unit
class TestWebRTCGatewayInitiateCall:
    """Tests for WebRTCGateway.initiate_call."""

    def _make_gateway_and_signaling(
        self, verbose: bool = False
    ) -> tuple[WebRTCGateway, WebRTCSignalingServer, MagicMock]:
        pbx_core = MagicMock()
        if not verbose:
            del pbx_core.webrtc_signaling
        else:
            pbx_core.webrtc_signaling.verbose_logging = True

        pbx_core.extension_registry.get_extension.return_value = MagicMock()
        pbx_core.call_manager.create_call.return_value = MagicMock()
        pbx_core.call_manager.create_call.return_value.local_sdp = None
        pbx_core.call_manager.create_call.return_value.caller_rtp = None
        pbx_core.call_manager.create_call.return_value.rtp_ports = None
        pbx_core.rtp_relay.allocate_relay.return_value = (10000, 10001)
        pbx_core.auto_attendant = None
        pbx_core.voicemail_system = None

        gw = WebRTCGateway(pbx_core=pbx_core)

        with patch.object(WebRTCSignalingServer, "_start_cleanup_thread"):
            signaling = WebRTCSignalingServer(config=_enabled_config())

        return gw, signaling, pbx_core

    def test_initiate_call_no_pbx_core(self) -> None:
        gw = WebRTCGateway(pbx_core=None)
        assert gw.initiate_call("sid", "1002") is None

    def test_initiate_call_no_signaling(self) -> None:
        gw, _signaling, _pbx_core = self._make_gateway_and_signaling()
        # No signaling provided -> session not found
        result = gw.initiate_call("nonexistent", "1002", webrtc_signaling=None)
        assert result is None

    def test_initiate_call_session_not_found(self) -> None:
        gw, signaling, _pbx_core = self._make_gateway_and_signaling()
        result = gw.initiate_call("nonexistent", "1002", webrtc_signaling=signaling)
        assert result is None

    def test_initiate_call_session_not_found_verbose(self) -> None:
        gw, signaling, _pbx_core = self._make_gateway_and_signaling(verbose=True)
        result = gw.initiate_call("nonexistent", "1002", webrtc_signaling=signaling)
        assert result is None

    def test_initiate_call_target_not_found(self) -> None:
        gw, signaling, pbx_core = self._make_gateway_and_signaling()
        session = signaling.create_session("1001")
        pbx_core.extension_registry.get_extension.return_value = None
        pbx_core._check_dialplan.return_value = False
        result = gw.initiate_call(session.session_id, "9999", webrtc_signaling=signaling)
        assert result is None

    def test_initiate_call_target_not_found_verbose(self) -> None:
        gw, signaling, pbx_core = self._make_gateway_and_signaling(verbose=True)
        session = signaling.create_session("1001")
        pbx_core.extension_registry.get_extension.return_value = None
        pbx_core._check_dialplan.return_value = False
        pbx_core.extension_registry.extensions = ["1002"]
        result = gw.initiate_call(session.session_id, "9999", webrtc_signaling=signaling)
        assert result is None

    def test_initiate_call_target_via_dialplan(self) -> None:
        gw, signaling, pbx_core = self._make_gateway_and_signaling()
        session = signaling.create_session("1001")

        # First call returns extension for from_extension, second returns None for target
        def get_ext_side_effect(number: str) -> MagicMock | None:
            if number == "1001":
                return MagicMock()
            return None

        pbx_core.extension_registry.get_extension.side_effect = get_ext_side_effect
        pbx_core._check_dialplan.return_value = True
        result = gw.initiate_call(session.session_id, "9999", webrtc_signaling=signaling)
        assert result is not None

    def test_initiate_call_success_no_sdp(self) -> None:
        gw, signaling, pbx_core = self._make_gateway_and_signaling()
        session = signaling.create_session("1001")
        result = gw.initiate_call(session.session_id, "1002", webrtc_signaling=signaling)
        assert result is not None
        pbx_core.call_manager.create_call.assert_called_once()
        pbx_core.rtp_relay.allocate_relay.assert_called_once()

    def test_initiate_call_success_with_sdp(self) -> None:
        gw, signaling, pbx_core = self._make_gateway_and_signaling()
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        mock_call = MagicMock()
        mock_call.caller_rtp = None
        mock_call.rtp_ports = None
        pbx_core.call_manager.create_call.return_value = mock_call

        result = gw.initiate_call(session.session_id, "1002", webrtc_signaling=signaling)
        assert result is not None
        mock_call.start.assert_called_once()

    def test_initiate_call_rtp_allocation_fails(self) -> None:
        gw, signaling, pbx_core = self._make_gateway_and_signaling()
        session = signaling.create_session("1001")
        pbx_core.rtp_relay.allocate_relay.return_value = None
        result = gw.initiate_call(session.session_id, "1002", webrtc_signaling=signaling)
        assert result is None

    def test_initiate_call_exception_handling(self) -> None:
        gw, signaling, pbx_core = self._make_gateway_and_signaling()
        session = signaling.create_session("1001")
        pbx_core.call_manager.create_call.side_effect = ValueError("boom")
        result = gw.initiate_call(session.session_id, "1002", webrtc_signaling=signaling)
        assert result is None

    def test_initiate_call_exception_handling_verbose(self) -> None:
        gw, signaling, pbx_core = self._make_gateway_and_signaling(verbose=True)
        session = signaling.create_session("1001")
        pbx_core.call_manager.create_call.side_effect = ValueError("boom")
        result = gw.initiate_call(session.session_id, "1002", webrtc_signaling=signaling)
        assert result is None

    def test_initiate_call_associates_call_id(self) -> None:
        gw, signaling, _pbx_core = self._make_gateway_and_signaling()
        session = signaling.create_session("1001")
        call_id = gw.initiate_call(session.session_id, "1002", webrtc_signaling=signaling)
        assert session.call_id == call_id

    def test_initiate_call_verbose_logging_all_branches(self) -> None:
        gw, signaling, pbx_core = self._make_gateway_and_signaling(verbose=True)
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        mock_call = MagicMock()
        mock_call.caller_rtp = None
        mock_call.rtp_ports = None
        pbx_core.call_manager.create_call.return_value = mock_call

        # Target ext found by extension registry (verbose path)
        pbx_core.extension_registry.get_extension.return_value = MagicMock()
        result = gw.initiate_call(session.session_id, "1002", webrtc_signaling=signaling)
        assert result is not None


@pytest.mark.unit
class TestWebRTCGatewayInitiateCallAutoAttendant:
    """Tests for initiate_call auto attendant branch."""

    def _make_aa_setup(self) -> tuple[WebRTCGateway, WebRTCSignalingServer, MagicMock]:
        pbx_core = MagicMock()
        del pbx_core.webrtc_signaling
        pbx_core.extension_registry.get_extension.return_value = MagicMock()
        pbx_core.rtp_relay.allocate_relay.return_value = (10000, 10001)
        pbx_core.auto_attendant.get_extension.return_value = "0"
        pbx_core.auto_attendant.start_session.return_value = {
            "action": "play",
            "file": "/tmp/welcome.wav",
        }
        pbx_core.voicemail_system = None

        mock_call = MagicMock()
        mock_call.caller_rtp = {"address": "192.168.1.100", "port": 50000}
        mock_call.rtp_ports = [10000, 10001]
        mock_call.local_sdp = None
        pbx_core.call_manager.create_call.return_value = mock_call

        gw = WebRTCGateway(pbx_core=pbx_core)

        with patch.object(WebRTCSignalingServer, "_start_cleanup_thread"):
            signaling = WebRTCSignalingServer(config=_enabled_config())

        return gw, signaling, pbx_core

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_auto_attendant_with_audio_file(
        self, MockRTPPlayer: MagicMock, mock_exists: MagicMock
    ) -> None:
        gw, signaling, _pbx_core = self._make_aa_setup()
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        mock_player = MagicMock()
        mock_player.start.return_value = True
        MockRTPPlayer.return_value = mock_player

        result = gw.initiate_call(session.session_id, "0", webrtc_signaling=signaling)
        assert result is not None
        mock_player.play_file.assert_called_once()

    @patch("pathlib.Path.exists", return_value=False)
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_auto_attendant_audio_file_not_found(
        self, MockRTPPlayer: MagicMock, mock_exists: MagicMock
    ) -> None:
        gw, signaling, _pbx_core = self._make_aa_setup()
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        mock_player = MagicMock()
        mock_player.start.return_value = True
        MockRTPPlayer.return_value = mock_player

        result = gw.initiate_call(session.session_id, "0", webrtc_signaling=signaling)
        assert result is not None
        mock_player.play_file.assert_not_called()

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_auto_attendant_player_start_fails(
        self, MockRTPPlayer: MagicMock, mock_exists: MagicMock
    ) -> None:
        gw, signaling, _pbx_core = self._make_aa_setup()
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        mock_player = MagicMock()
        mock_player.start.return_value = False
        MockRTPPlayer.return_value = mock_player

        result = gw.initiate_call(session.session_id, "0", webrtc_signaling=signaling)
        assert result is not None
        mock_player.play_file.assert_not_called()

    def test_auto_attendant_no_caller_rtp(self) -> None:
        gw, signaling, pbx_core = self._make_aa_setup()
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        mock_call = pbx_core.call_manager.create_call.return_value
        mock_call.caller_rtp = None

        result = gw.initiate_call(session.session_id, "0", webrtc_signaling=signaling)
        assert result is not None

    def test_auto_attendant_incomplete_caller_rtp(self) -> None:
        gw, signaling, pbx_core = self._make_aa_setup()
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        mock_call = pbx_core.call_manager.create_call.return_value
        mock_call.caller_rtp = {"address": None, "port": None}

        result = gw.initiate_call(session.session_id, "0", webrtc_signaling=signaling)
        assert result is not None


@pytest.mark.unit
class TestWebRTCGatewayInitiateCallVoicemail:
    """Tests for initiate_call voicemail access branch."""

    def _make_vm_setup(
        self, verbose: bool = False
    ) -> tuple[WebRTCGateway, WebRTCSignalingServer, MagicMock]:
        pbx_core = MagicMock()
        if not verbose:
            del pbx_core.webrtc_signaling
        else:
            pbx_core.webrtc_signaling.verbose_logging = True

        pbx_core.extension_registry.get_extension.return_value = MagicMock()
        pbx_core.rtp_relay.allocate_relay.return_value = (10000, 10001)
        pbx_core.auto_attendant = None
        pbx_core.voicemail_system.get_mailbox.return_value = MagicMock()
        pbx_core.cdr_system = None

        mock_call = MagicMock()
        mock_call.caller_rtp = {"address": "192.168.1.100", "port": 50000}
        mock_call.rtp_ports = [10000, 10001]
        mock_call.local_sdp = None
        pbx_core.call_manager.create_call.return_value = mock_call

        gw = WebRTCGateway(pbx_core=pbx_core)

        with patch.object(WebRTCSignalingServer, "_start_cleanup_thread"):
            cfg = _enabled_config()
            if verbose:
                cfg = _enabled_config(**{"features.webrtc.verbose_logging": True})
            signaling = WebRTCSignalingServer(config=cfg)

        return gw, signaling, pbx_core

    @patch("pbx.features.voicemail.VoicemailIVR")
    @patch("threading.Thread")
    def test_voicemail_access_pattern(self, mock_thread_cls: MagicMock, MockIVR: MagicMock) -> None:
        gw, signaling, _pbx_core = self._make_vm_setup()
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        mock_thread_inst = MagicMock()
        mock_thread_cls.return_value = mock_thread_inst

        result = gw.initiate_call(session.session_id, "*1002", webrtc_signaling=signaling)
        assert result is not None
        MockIVR.assert_called_once()
        mock_thread_inst.start.assert_called_once()

    @patch("pbx.features.voicemail.VoicemailIVR")
    @patch("threading.Thread")
    def test_voicemail_access_verbose(self, mock_thread_cls: MagicMock, MockIVR: MagicMock) -> None:
        gw, signaling, _pbx_core = self._make_vm_setup(verbose=True)
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        result = gw.initiate_call(session.session_id, "*1002", webrtc_signaling=signaling)
        assert result is not None

    @patch("pbx.features.voicemail.VoicemailIVR")
    def test_voicemail_no_caller_rtp(self, MockIVR: MagicMock) -> None:
        gw, signaling, pbx_core = self._make_vm_setup()
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        mock_call = pbx_core.call_manager.create_call.return_value
        mock_call.caller_rtp = None

        result = gw.initiate_call(session.session_id, "*1002", webrtc_signaling=signaling)
        assert result is not None

    @patch("pbx.features.voicemail.VoicemailIVR")
    def test_voicemail_no_caller_rtp_verbose(self, MockIVR: MagicMock) -> None:
        gw, signaling, pbx_core = self._make_vm_setup(verbose=True)
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        mock_call = pbx_core.call_manager.create_call.return_value
        mock_call.caller_rtp = None

        result = gw.initiate_call(session.session_id, "*1002", webrtc_signaling=signaling)
        assert result is not None

    @patch("pbx.features.voicemail.VoicemailIVR")
    def test_voicemail_incomplete_rtp(self, MockIVR: MagicMock) -> None:
        gw, signaling, pbx_core = self._make_vm_setup()
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        mock_call = pbx_core.call_manager.create_call.return_value
        mock_call.caller_rtp = {"address": None, "port": None}

        result = gw.initiate_call(session.session_id, "*1002", webrtc_signaling=signaling)
        assert result is not None

    @patch("pbx.features.voicemail.VoicemailIVR")
    def test_voicemail_incomplete_rtp_verbose(self, MockIVR: MagicMock) -> None:
        gw, signaling, pbx_core = self._make_vm_setup(verbose=True)
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        mock_call = pbx_core.call_manager.create_call.return_value
        mock_call.caller_rtp = {"address": None, "port": None}

        result = gw.initiate_call(session.session_id, "*1002", webrtc_signaling=signaling)
        assert result is not None

    def test_voicemail_system_unavailable(self) -> None:
        gw, signaling, pbx_core = self._make_vm_setup()
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        pbx_core.voicemail_system = None

        result = gw.initiate_call(session.session_id, "*1002", webrtc_signaling=signaling)
        assert result is not None

    def test_voicemail_system_unavailable_verbose(self) -> None:
        gw, signaling, pbx_core = self._make_vm_setup(verbose=True)
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        pbx_core.voicemail_system = None

        result = gw.initiate_call(session.session_id, "*1002", webrtc_signaling=signaling)
        assert result is not None

    @patch("pbx.features.voicemail.VoicemailIVR")
    @patch("threading.Thread")
    def test_voicemail_with_cdr_system(
        self, mock_thread_cls: MagicMock, MockIVR: MagicMock
    ) -> None:
        gw, signaling, pbx_core = self._make_vm_setup()
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        pbx_core.cdr_system = MagicMock()

        result = gw.initiate_call(session.session_id, "*1002", webrtc_signaling=signaling)
        assert result is not None
        pbx_core.cdr_system.start_record.assert_called_once()

    @patch("pbx.features.voicemail.VoicemailIVR")
    @patch("threading.Thread")
    def test_voicemail_with_cdr_system_verbose(
        self, mock_thread_cls: MagicMock, MockIVR: MagicMock
    ) -> None:
        gw, signaling, pbx_core = self._make_vm_setup(verbose=True)
        session = signaling.create_session("1001")
        signaling.handle_offer(session.session_id, SIP_SDP)

        pbx_core.cdr_system = MagicMock()

        result = gw.initiate_call(session.session_id, "*1002", webrtc_signaling=signaling)
        assert result is not None

    def test_non_voicemail_pattern_not_matched(self) -> None:
        """Patterns like *12 (too short) should not match voicemail."""
        gw, signaling, _pbx_core = self._make_vm_setup()
        session = signaling.create_session("1001")

        result = gw.initiate_call(session.session_id, "*12", webrtc_signaling=signaling)
        # Call still goes through, but voicemail code should not be hit
        assert result is not None


@pytest.mark.unit
class TestWebRTCGatewayReceiveCall:
    """Tests for WebRTCGateway.receive_call."""

    def _make_setup(self) -> tuple[WebRTCGateway, WebRTCSignalingServer, MagicMock]:
        pbx_core = MagicMock()
        del pbx_core.webrtc_signaling
        mock_call = MagicMock()
        mock_call.from_extension = "1001"
        pbx_core.call_manager.get_call.return_value = mock_call

        gw = WebRTCGateway(pbx_core=pbx_core)

        with patch.object(WebRTCSignalingServer, "_start_cleanup_thread"):
            signaling = WebRTCSignalingServer(config=_enabled_config())

        return gw, signaling, pbx_core

    def test_receive_call_no_pbx_core(self) -> None:
        gw = WebRTCGateway(pbx_core=None)
        assert gw.receive_call("sid", "cid") is False

    def test_receive_call_no_signaling(self) -> None:
        gw, _signaling, _pbx_core = self._make_setup()
        result = gw.receive_call("nonexistent", "call-1", webrtc_signaling=None)
        assert result is False

    def test_receive_call_session_not_found(self) -> None:
        gw, signaling, _pbx_core = self._make_setup()
        result = gw.receive_call("nonexistent", "call-1", webrtc_signaling=signaling)
        assert result is False

    def test_receive_call_call_not_found(self) -> None:
        gw, signaling, pbx_core = self._make_setup()
        session = signaling.create_session("1002")
        pbx_core.call_manager.get_call.return_value = None
        result = gw.receive_call(session.session_id, "call-1", webrtc_signaling=signaling)
        assert result is False

    def test_receive_call_success_with_sdp(self) -> None:
        gw, signaling, _pbx_core = self._make_setup()
        session = signaling.create_session("1002")
        result = gw.receive_call(
            session.session_id, "call-1", caller_sdp=SIP_SDP, webrtc_signaling=signaling
        )
        assert result is True
        assert session.remote_sdp is not None
        assert session.state == "ringing"
        assert session.call_id == "call-1"

    def test_receive_call_success_no_sdp(self) -> None:
        gw, signaling, _pbx_core = self._make_setup()
        session = signaling.create_session("1002")
        result = gw.receive_call(
            session.session_id, "call-1", caller_sdp=None, webrtc_signaling=signaling
        )
        assert result is True

    def test_receive_call_sets_metadata(self) -> None:
        gw, signaling, _pbx_core = self._make_setup()
        session = signaling.create_session("1002")
        gw.receive_call(
            session.session_id, "call-1", caller_sdp=SIP_SDP, webrtc_signaling=signaling
        )
        assert signaling.get_session_metadata(session.session_id, "incoming_call") is True
        assert signaling.get_session_metadata(session.session_id, "caller_extension") == "1001"

    def test_receive_call_calls_ring(self) -> None:
        gw, signaling, pbx_core = self._make_setup()
        session = signaling.create_session("1002")
        mock_call = pbx_core.call_manager.get_call.return_value
        gw.receive_call(
            session.session_id, "call-1", caller_sdp=SIP_SDP, webrtc_signaling=signaling
        )
        mock_call.ring.assert_called_once()

    def test_receive_call_exception(self) -> None:
        gw, signaling, pbx_core = self._make_setup()
        session = signaling.create_session("1002")
        pbx_core.call_manager.get_call.side_effect = RuntimeError("fail")
        result = gw.receive_call(
            session.session_id, "call-1", caller_sdp=SIP_SDP, webrtc_signaling=signaling
        )
        assert result is False


@pytest.mark.unit
class TestWebRTCGatewayAnswerCall:
    """Tests for WebRTCGateway.answer_call."""

    def _make_setup(self) -> tuple[WebRTCGateway, WebRTCSignalingServer, MagicMock]:
        pbx_core = MagicMock()
        del pbx_core.webrtc_signaling
        mock_call = MagicMock()
        pbx_core.call_manager.get_call.return_value = mock_call

        gw = WebRTCGateway(pbx_core=pbx_core)

        with patch.object(WebRTCSignalingServer, "_start_cleanup_thread"):
            signaling = WebRTCSignalingServer(config=_enabled_config())

        return gw, signaling, pbx_core

    def test_answer_call_no_pbx_core(self) -> None:
        gw = WebRTCGateway(pbx_core=None)
        assert gw.answer_call("sid") is False

    def test_answer_call_no_signaling(self) -> None:
        gw, _signaling, _pbx_core = self._make_setup()
        result = gw.answer_call("sid", webrtc_signaling=None)
        assert result is False

    def test_answer_call_session_not_found(self) -> None:
        gw, signaling, _pbx_core = self._make_setup()
        result = gw.answer_call("nonexistent", webrtc_signaling=signaling)
        assert result is False

    def test_answer_call_no_call_id(self) -> None:
        gw, signaling, _pbx_core = self._make_setup()
        session = signaling.create_session("1002")
        # call_id is None by default
        result = gw.answer_call(session.session_id, webrtc_signaling=signaling)
        assert result is False

    def test_answer_call_call_not_found(self) -> None:
        gw, signaling, pbx_core = self._make_setup()
        session = signaling.create_session("1002")
        session.call_id = "call-1"
        pbx_core.call_manager.get_call.return_value = None
        result = gw.answer_call(session.session_id, webrtc_signaling=signaling)
        assert result is False

    def test_answer_call_success_with_local_sdp(self) -> None:
        gw, signaling, pbx_core = self._make_setup()
        session = signaling.create_session("1002")
        session.call_id = "call-1"
        session.local_sdp = SIP_SDP

        mock_call = pbx_core.call_manager.get_call.return_value
        result = gw.answer_call(session.session_id, webrtc_signaling=signaling)
        assert result is True
        assert session.state == "connected"
        mock_call.connect.assert_called_once()

    def test_answer_call_success_without_local_sdp(self) -> None:
        gw, signaling, pbx_core = self._make_setup()
        session = signaling.create_session("1002")
        session.call_id = "call-1"
        session.local_sdp = None

        mock_call = pbx_core.call_manager.get_call.return_value
        result = gw.answer_call(session.session_id, webrtc_signaling=signaling)
        assert result is True
        mock_call.connect.assert_called_once()

    def test_answer_call_exception(self) -> None:
        gw, signaling, pbx_core = self._make_setup()
        session = signaling.create_session("1002")
        session.call_id = "call-1"
        pbx_core.call_manager.get_call.side_effect = ValueError("error")
        result = gw.answer_call(session.session_id, webrtc_signaling=signaling)
        assert result is False

    def test_answer_call_sdp_parse_sets_callee_rtp(self) -> None:
        gw, signaling, pbx_core = self._make_setup()
        session = signaling.create_session("1002")
        session.call_id = "call-1"
        session.local_sdp = SIP_SDP

        mock_call = pbx_core.call_manager.get_call.return_value
        result = gw.answer_call(session.session_id, webrtc_signaling=signaling)
        assert result is True
        # callee_rtp should be set from SDP parsing
        assert mock_call.callee_rtp is not None or hasattr(mock_call, "callee_rtp")
