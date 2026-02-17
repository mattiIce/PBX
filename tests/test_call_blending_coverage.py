"""
Comprehensive tests for Call Blending feature.
Tests all public classes, methods, enums, and edge cases.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.call_blending import (
    Agent,
    AgentMode,
    CallBlending,
    CallDirection,
    get_call_blending,
)


@pytest.mark.unit
class TestCallDirection:
    """Tests for CallDirection enum."""

    def test_inbound_value(self) -> None:
        assert CallDirection.INBOUND.value == "inbound"

    def test_outbound_value(self) -> None:
        assert CallDirection.OUTBOUND.value == "outbound"

    def test_enum_members(self) -> None:
        members = list(CallDirection)
        assert len(members) == 2
        assert CallDirection.INBOUND in members
        assert CallDirection.OUTBOUND in members


@pytest.mark.unit
class TestAgentMode:
    """Tests for AgentMode enum."""

    def test_inbound_only_value(self) -> None:
        assert AgentMode.INBOUND_ONLY.value == "inbound_only"

    def test_outbound_only_value(self) -> None:
        assert AgentMode.OUTBOUND_ONLY.value == "outbound_only"

    def test_blended_value(self) -> None:
        assert AgentMode.BLENDED.value == "blended"

    def test_auto_value(self) -> None:
        assert AgentMode.AUTO.value == "auto"

    def test_enum_members(self) -> None:
        members = list(AgentMode)
        assert len(members) == 4


@pytest.mark.unit
class TestAgent:
    """Tests for Agent class."""

    def test_init_defaults(self) -> None:
        agent = Agent("agent1", "1001")
        assert agent.agent_id == "agent1"
        assert agent.extension == "1001"
        assert agent.mode == AgentMode.BLENDED
        assert agent.available is True
        assert agent.current_call is None
        assert agent.inbound_calls_handled == 0
        assert agent.outbound_calls_handled == 0

    def test_init_various_ids(self) -> None:
        agent = Agent("a-long-agent-id-123", "9999")
        assert agent.agent_id == "a-long-agent-id-123"
        assert agent.extension == "9999"

    def test_mutable_attributes(self) -> None:
        agent = Agent("agent1", "1001")
        agent.available = False
        agent.current_call = "call-123"
        agent.inbound_calls_handled = 5
        agent.outbound_calls_handled = 3
        agent.mode = AgentMode.AUTO

        assert agent.available is False
        assert agent.current_call == "call-123"
        assert agent.inbound_calls_handled == 5
        assert agent.outbound_calls_handled == 3
        assert agent.mode == AgentMode.AUTO


@pytest.mark.unit
class TestCallBlendingInit:
    """Tests for CallBlending initialization."""

    @patch("pbx.features.call_blending.get_logger")
    def test_init_no_config(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        assert cb.config == {}
        assert cb.enabled is False
        assert cb.inbound_priority is True
        assert cb.max_inbound_wait == 30
        assert cb.blend_ratio == 0.7
        assert cb.agents == {}
        assert cb.inbound_queue == []
        assert cb.outbound_queue == []
        assert cb.total_blended_calls == 0
        assert cb.inbound_calls == 0
        assert cb.outbound_calls == 0

    @patch("pbx.features.call_blending.get_logger")
    def test_init_none_config(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending(config=None)
        assert cb.config == {}

    @patch("pbx.features.call_blending.get_logger")
    def test_init_empty_config(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending(config={})
        assert cb.enabled is False

    @patch("pbx.features.call_blending.get_logger")
    def test_init_enabled_config(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {
            "features": {
                "call_blending": {
                    "enabled": True,
                    "inbound_priority": False,
                    "max_inbound_wait": 60,
                    "blend_ratio": 0.5,
                }
            }
        }
        cb = CallBlending(config=config)
        assert cb.enabled is True
        assert cb.inbound_priority is False
        assert cb.max_inbound_wait == 60
        assert cb.blend_ratio == 0.5

    @patch("pbx.features.call_blending.get_logger")
    def test_init_disabled_config(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {"features": {"call_blending": {"enabled": False}}}
        cb = CallBlending(config=config)
        assert cb.enabled is False

    @patch("pbx.features.call_blending.get_logger")
    def test_init_partial_config(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {"features": {"call_blending": {"enabled": True}}}
        cb = CallBlending(config=config)
        assert cb.enabled is True
        assert cb.inbound_priority is True
        assert cb.max_inbound_wait == 30
        assert cb.blend_ratio == 0.7

    @patch("pbx.features.call_blending.get_logger")
    def test_init_logging(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        CallBlending()
        assert mock_logger.info.call_count == 4


@pytest.mark.unit
class TestCallBlendingRegisterAgent:
    """Tests for agent registration."""

    @patch("pbx.features.call_blending.get_logger")
    def test_register_agent_default_mode(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        result = cb.register_agent("agent1", "1001")
        assert result["success"] is True
        assert result["agent_id"] == "agent1"
        assert result["extension"] == "1001"
        assert result["mode"] == "blended"
        assert "agent1" in cb.agents

    @patch("pbx.features.call_blending.get_logger")
    def test_register_agent_inbound_only(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        result = cb.register_agent("agent1", "1001", mode="inbound_only")
        assert result["success"] is True
        assert result["mode"] == "inbound_only"
        assert cb.agents["agent1"].mode == AgentMode.INBOUND_ONLY

    @patch("pbx.features.call_blending.get_logger")
    def test_register_agent_outbound_only(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        result = cb.register_agent("agent1", "1001", mode="outbound_only")
        assert result["success"] is True
        assert result["mode"] == "outbound_only"
        assert cb.agents["agent1"].mode == AgentMode.OUTBOUND_ONLY

    @patch("pbx.features.call_blending.get_logger")
    def test_register_agent_auto(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        result = cb.register_agent("agent1", "1001", mode="auto")
        assert result["success"] is True
        assert result["mode"] == "auto"
        assert cb.agents["agent1"].mode == AgentMode.AUTO

    @patch("pbx.features.call_blending.get_logger")
    def test_register_agent_blended_explicit(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        result = cb.register_agent("agent1", "1001", mode="blended")
        assert result["success"] is True
        assert result["mode"] == "blended"
        assert cb.agents["agent1"].mode == AgentMode.BLENDED

    @patch("pbx.features.call_blending.get_logger")
    def test_register_agent_unknown_mode_defaults_blended(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        result = cb.register_agent("agent1", "1001", mode="unknown_mode")
        assert result["success"] is True
        assert result["mode"] == "blended"

    @patch("pbx.features.call_blending.get_logger")
    def test_register_duplicate_agent(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001")
        result = cb.register_agent("agent1", "1002")
        assert result["success"] is False
        assert "already registered" in result["error"]

    @patch("pbx.features.call_blending.get_logger")
    def test_register_multiple_agents(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001")
        cb.register_agent("agent2", "1002")
        cb.register_agent("agent3", "1003")
        assert len(cb.agents) == 3


@pytest.mark.unit
class TestCallBlendingQueueCall:
    """Tests for call queuing."""

    @patch("pbx.features.call_blending.get_logger")
    def test_queue_inbound_call(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        call = {"call_id": "call-1", "from": "5551234"}
        cb.queue_call(call, "inbound")
        assert len(cb.inbound_queue) == 1
        assert cb.inbound_queue[0]["call_id"] == "call-1"
        assert "queued_at" in cb.inbound_queue[0]

    @patch("pbx.features.call_blending.get_logger")
    def test_queue_outbound_call(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        call = {"call_id": "call-1", "to": "5551234"}
        cb.queue_call(call, "outbound")
        assert len(cb.outbound_queue) == 1
        assert cb.outbound_queue[0]["call_id"] == "call-1"
        assert "queued_at" in cb.outbound_queue[0]

    @patch("pbx.features.call_blending.get_logger")
    def test_queue_multiple_calls(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        for i in range(5):
            cb.queue_call({"call_id": f"in-{i}"}, "inbound")
            cb.queue_call({"call_id": f"out-{i}"}, "outbound")
        assert len(cb.inbound_queue) == 5
        assert len(cb.outbound_queue) == 5

    @patch("pbx.features.call_blending.get_logger")
    def test_queue_call_sets_queued_at(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        call = {"call_id": "call-1"}
        before = datetime.now(UTC)
        cb.queue_call(call, "inbound")
        after = datetime.now(UTC)
        queued_at = cb.inbound_queue[0]["queued_at"]
        assert before <= queued_at <= after


@pytest.mark.unit
class TestCallBlendingGetNextCall:
    """Tests for get_next_call_for_agent."""

    @patch("pbx.features.call_blending.get_logger")
    def test_agent_not_found(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        result = cb.get_next_call_for_agent("nonexistent")
        assert result is None

    @patch("pbx.features.call_blending.get_logger")
    def test_agent_not_available(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001")
        cb.agents["agent1"].available = False
        result = cb.get_next_call_for_agent("agent1")
        assert result is None

    @patch("pbx.features.call_blending.get_logger")
    def test_inbound_only_agent_gets_inbound(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001", mode="inbound_only")
        cb.queue_call({"call_id": "in-1"}, "inbound")
        result = cb.get_next_call_for_agent("agent1")
        assert result is not None
        assert result["call_id"] == "in-1"

    @patch("pbx.features.call_blending.get_logger")
    def test_inbound_only_agent_no_inbound(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001", mode="inbound_only")
        cb.queue_call({"call_id": "out-1"}, "outbound")
        result = cb.get_next_call_for_agent("agent1")
        assert result is None

    @patch("pbx.features.call_blending.get_logger")
    def test_outbound_only_agent_gets_outbound(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001", mode="outbound_only")
        cb.queue_call({"call_id": "out-1"}, "outbound")
        result = cb.get_next_call_for_agent("agent1")
        assert result is not None
        assert result["call_id"] == "out-1"

    @patch("pbx.features.call_blending.get_logger")
    def test_outbound_only_agent_no_outbound(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001", mode="outbound_only")
        cb.queue_call({"call_id": "in-1"}, "inbound")
        result = cb.get_next_call_for_agent("agent1")
        assert result is None

    @patch("pbx.features.call_blending.get_logger")
    def test_blended_agent_gets_call(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001", mode="blended")
        cb.queue_call({"call_id": "in-1"}, "inbound")
        result = cb.get_next_call_for_agent("agent1")
        assert result is not None

    @patch("pbx.features.call_blending.get_logger")
    def test_auto_agent_gets_call(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001", mode="auto")
        cb.queue_call({"call_id": "in-1"}, "inbound")
        result = cb.get_next_call_for_agent("agent1")
        assert result is not None


@pytest.mark.unit
class TestCallBlendingPrivateMethods:
    """Tests for private blending methods."""

    @patch("pbx.features.call_blending.get_logger")
    def test_get_inbound_call_empty_queue(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        result = cb._get_inbound_call()
        assert result is None

    @patch("pbx.features.call_blending.get_logger")
    def test_get_inbound_call_pops_first(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.queue_call({"call_id": "in-1"}, "inbound")
        cb.queue_call({"call_id": "in-2"}, "inbound")
        result = cb._get_inbound_call()
        assert result["call_id"] == "in-1"
        assert len(cb.inbound_queue) == 1
        assert cb.inbound_calls == 1

    @patch("pbx.features.call_blending.get_logger")
    def test_get_outbound_call_empty_queue(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        result = cb._get_outbound_call()
        assert result is None

    @patch("pbx.features.call_blending.get_logger")
    def test_get_outbound_call_pops_first(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.queue_call({"call_id": "out-1"}, "outbound")
        cb.queue_call({"call_id": "out-2"}, "outbound")
        result = cb._get_outbound_call()
        assert result["call_id"] == "out-1"
        assert len(cb.outbound_queue) == 1
        assert cb.outbound_calls == 1

    @patch("pbx.features.call_blending.get_logger")
    def test_blend_call_inbound_priority_wait_exceeded(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001")
        agent = cb.agents["agent1"]

        # Queue an inbound call with a timestamp in the past (beyond max_inbound_wait)
        call = {"call_id": "in-1", "queued_at": datetime.now(UTC) - timedelta(seconds=60)}
        cb.inbound_queue.append(call)

        result = cb._blend_call(agent)
        assert result is not None
        assert result["call_id"] == "in-1"

    @patch("pbx.features.call_blending.get_logger")
    def test_blend_call_inbound_priority_wait_not_exceeded(
        self, mock_get_logger: MagicMock
    ) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001")
        agent = cb.agents["agent1"]

        # Queue an inbound call with recent timestamp (within max_inbound_wait)
        call = {"call_id": "in-1", "queued_at": datetime.now(UTC) - timedelta(seconds=5)}
        cb.inbound_queue.append(call)

        # Agent has 0 calls handled, so inbound_ratio=0 < 0.7, gets inbound
        result = cb._blend_call(agent)
        assert result is not None
        assert result["call_id"] == "in-1"

    @patch("pbx.features.call_blending.get_logger")
    def test_blend_call_inbound_priority_disabled(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {
            "features": {
                "call_blending": {
                    "enabled": True,
                    "inbound_priority": False,
                }
            }
        }
        cb = CallBlending(config=config)
        cb.register_agent("agent1", "1001")
        agent = cb.agents["agent1"]

        call = {"call_id": "in-1", "queued_at": datetime.now(UTC) - timedelta(seconds=60)}
        cb.inbound_queue.append(call)

        # Inbound priority is off so it won't check wait time first
        # But ratio is 0 < 0.7, so it still picks inbound
        result = cb._blend_call(agent)
        assert result is not None

    @patch("pbx.features.call_blending.get_logger")
    def test_blend_call_ratio_favors_outbound(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {
            "features": {
                "call_blending": {
                    "enabled": True,
                    "inbound_priority": False,
                    "blend_ratio": 0.3,
                }
            }
        }
        cb = CallBlending(config=config)
        cb.register_agent("agent1", "1001")
        agent = cb.agents["agent1"]
        # Simulate agent having handled more inbound than ratio
        agent.inbound_calls_handled = 8
        agent.outbound_calls_handled = 2

        cb.queue_call({"call_id": "in-1"}, "inbound")
        cb.queue_call({"call_id": "out-1"}, "outbound")

        # current_inbound_ratio = 8/10 = 0.8 > 0.3, so outbound is chosen
        result = cb._blend_call(agent)
        assert result is not None
        assert result["call_id"] == "out-1"
        assert agent.outbound_calls_handled == 3

    @patch("pbx.features.call_blending.get_logger")
    def test_blend_call_ratio_favors_inbound(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {
            "features": {
                "call_blending": {
                    "enabled": True,
                    "inbound_priority": False,
                    "blend_ratio": 0.7,
                }
            }
        }
        cb = CallBlending(config=config)
        cb.register_agent("agent1", "1001")
        agent = cb.agents["agent1"]
        agent.inbound_calls_handled = 2
        agent.outbound_calls_handled = 8

        cb.queue_call({"call_id": "in-1"}, "inbound")
        cb.queue_call({"call_id": "out-1"}, "outbound")

        # current_inbound_ratio = 2/10 = 0.2 < 0.7, so inbound chosen
        result = cb._blend_call(agent)
        assert result is not None
        assert result["call_id"] == "in-1"
        assert agent.inbound_calls_handled == 3

    @patch("pbx.features.call_blending.get_logger")
    def test_blend_call_zero_handled_calls(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {
            "features": {
                "call_blending": {
                    "enabled": True,
                    "inbound_priority": False,
                }
            }
        }
        cb = CallBlending(config=config)
        cb.register_agent("agent1", "1001")
        agent = cb.agents["agent1"]

        cb.queue_call({"call_id": "in-1"}, "inbound")

        # total=0, current_inbound_ratio=0.0 < 0.7, gets inbound
        result = cb._blend_call(agent)
        assert result is not None
        assert result["call_id"] == "in-1"

    @patch("pbx.features.call_blending.get_logger")
    def test_blend_call_fallback_to_inbound(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {
            "features": {
                "call_blending": {
                    "enabled": True,
                    "inbound_priority": False,
                    "blend_ratio": 0.1,
                }
            }
        }
        cb = CallBlending(config=config)
        cb.register_agent("agent1", "1001")
        agent = cb.agents["agent1"]
        # Ratio is high so outbound is wanted, but no outbound available
        agent.inbound_calls_handled = 5
        agent.outbound_calls_handled = 1

        cb.queue_call({"call_id": "in-1"}, "inbound")
        # No outbound calls in queue

        # current_inbound_ratio = 5/6 ~= 0.83 > 0.1 -> tries outbound -> empty
        # falls back to inbound
        result = cb._blend_call(agent)
        assert result is not None
        assert result["call_id"] == "in-1"

    @patch("pbx.features.call_blending.get_logger")
    def test_blend_call_empty_queues(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {
            "features": {
                "call_blending": {
                    "enabled": True,
                    "inbound_priority": False,
                }
            }
        }
        cb = CallBlending(config=config)
        cb.register_agent("agent1", "1001")
        agent = cb.agents["agent1"]
        result = cb._blend_call(agent)
        assert result is None

    @patch("pbx.features.call_blending.get_logger")
    def test_blend_call_increments_total_blended(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {
            "features": {
                "call_blending": {
                    "enabled": True,
                    "inbound_priority": False,
                }
            }
        }
        cb = CallBlending(config=config)
        cb.register_agent("agent1", "1001")
        agent = cb.agents["agent1"]
        cb.queue_call({"call_id": "in-1"}, "inbound")
        cb._blend_call(agent)
        assert cb.total_blended_calls == 1

    @patch("pbx.features.call_blending.get_logger")
    def test_auto_blend_inbound_surge(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001")
        agent = cb.agents["agent1"]
        # Queue 11 inbound calls (surge threshold > 10)
        for i in range(11):
            cb.queue_call({"call_id": f"in-{i}"}, "inbound")
        result = cb._auto_blend_call(agent)
        assert result is not None
        assert result["call_id"] == "in-0"

    @patch("pbx.features.call_blending.get_logger")
    def test_auto_blend_no_inbound_has_outbound(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001")
        agent = cb.agents["agent1"]
        cb.queue_call({"call_id": "out-1"}, "outbound")
        result = cb._auto_blend_call(agent)
        assert result is not None
        assert result["call_id"] == "out-1"

    @patch("pbx.features.call_blending.get_logger")
    def test_auto_blend_normal_blend(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001")
        agent = cb.agents["agent1"]
        # Queue a few inbound (not surge) and some outbound
        for i in range(3):
            cb.queue_call({"call_id": f"in-{i}"}, "inbound")
        cb.queue_call({"call_id": "out-1"}, "outbound")
        result = cb._auto_blend_call(agent)
        assert result is not None

    @patch("pbx.features.call_blending.get_logger")
    def test_auto_blend_empty_queues(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001")
        agent = cb.agents["agent1"]
        result = cb._auto_blend_call(agent)
        assert result is None


@pytest.mark.unit
class TestCallBlendingSetAgentAvailable:
    """Tests for set_agent_available."""

    @patch("pbx.features.call_blending.get_logger")
    def test_set_available_disabled(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()  # enabled is False by default
        cb.register_agent("agent1", "1001")
        result = cb.set_agent_available("agent1", False)
        assert result is False

    @patch("pbx.features.call_blending.get_logger")
    def test_set_available_success(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {"features": {"call_blending": {"enabled": True}}}
        cb = CallBlending(config=config)
        cb.register_agent("agent1", "1001")
        result = cb.set_agent_available("agent1", False)
        assert result is True
        assert cb.agents["agent1"].available is False

    @patch("pbx.features.call_blending.get_logger")
    def test_set_available_back_to_true(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {"features": {"call_blending": {"enabled": True}}}
        cb = CallBlending(config=config)
        cb.register_agent("agent1", "1001")
        cb.set_agent_available("agent1", False)
        result = cb.set_agent_available("agent1", True)
        assert result is True
        assert cb.agents["agent1"].available is True

    @patch("pbx.features.call_blending.get_logger")
    def test_set_available_nonexistent_agent(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {"features": {"call_blending": {"enabled": True}}}
        cb = CallBlending(config=config)
        result = cb.set_agent_available("nonexistent", True)
        assert result is False


@pytest.mark.unit
class TestCallBlendingSetAgentMode:
    """Tests for set_agent_mode."""

    @patch("pbx.features.call_blending.get_logger")
    def test_set_mode_agent_not_found(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        result = cb.set_agent_mode("nonexistent", "blended")
        assert result["success"] is False
        assert "not found" in result["error"]

    @patch("pbx.features.call_blending.get_logger")
    def test_set_mode_inbound_only(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001")
        result = cb.set_agent_mode("agent1", "inbound_only")
        assert result["success"] is True
        assert result["mode"] == "inbound_only"
        assert cb.agents["agent1"].mode == AgentMode.INBOUND_ONLY

    @patch("pbx.features.call_blending.get_logger")
    def test_set_mode_outbound_only(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001")
        result = cb.set_agent_mode("agent1", "outbound_only")
        assert result["success"] is True
        assert cb.agents["agent1"].mode == AgentMode.OUTBOUND_ONLY

    @patch("pbx.features.call_blending.get_logger")
    def test_set_mode_blended(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001", mode="inbound_only")
        result = cb.set_agent_mode("agent1", "blended")
        assert result["success"] is True
        assert cb.agents["agent1"].mode == AgentMode.BLENDED

    @patch("pbx.features.call_blending.get_logger")
    def test_set_mode_auto(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001")
        result = cb.set_agent_mode("agent1", "auto")
        assert result["success"] is True
        assert cb.agents["agent1"].mode == AgentMode.AUTO

    @patch("pbx.features.call_blending.get_logger")
    def test_set_mode_invalid(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001")
        result = cb.set_agent_mode("agent1", "invalid_mode")
        assert result["success"] is False
        assert "Invalid mode" in result["error"]


@pytest.mark.unit
class TestCallBlendingGetAgentStatus:
    """Tests for agent status methods."""

    @patch("pbx.features.call_blending.get_logger")
    def test_get_agent_status_found(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001")
        status = cb.get_agent_status("agent1")
        assert status is not None
        assert status["agent_id"] == "agent1"
        assert status["extension"] == "1001"
        assert status["mode"] == "blended"
        assert status["available"] is True
        assert status["current_call"] is None
        assert status["inbound_calls_handled"] == 0
        assert status["outbound_calls_handled"] == 0

    @patch("pbx.features.call_blending.get_logger")
    def test_get_agent_status_not_found(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        status = cb.get_agent_status("nonexistent")
        assert status is None

    @patch("pbx.features.call_blending.get_logger")
    def test_get_all_agents_empty(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        agents = cb.get_all_agents()
        assert agents == []

    @patch("pbx.features.call_blending.get_logger")
    def test_get_all_agents_multiple(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.register_agent("agent1", "1001", mode="inbound_only")
        cb.register_agent("agent2", "1002", mode="outbound_only")
        agents = cb.get_all_agents()
        assert len(agents) == 2
        agent_ids = [a["agent_id"] for a in agents]
        assert "agent1" in agent_ids
        assert "agent2" in agent_ids


@pytest.mark.unit
class TestCallBlendingStatistics:
    """Tests for statistics methods."""

    @patch("pbx.features.call_blending.get_logger")
    def test_get_queue_statistics_empty(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        stats = cb.get_queue_statistics()
        assert stats["inbound_queue_size"] == 0
        assert stats["outbound_queue_size"] == 0
        assert stats["total_queued"] == 0

    @patch("pbx.features.call_blending.get_logger")
    def test_get_queue_statistics_with_calls(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        cb.queue_call({"call_id": "in-1"}, "inbound")
        cb.queue_call({"call_id": "in-2"}, "inbound")
        cb.queue_call({"call_id": "out-1"}, "outbound")
        stats = cb.get_queue_statistics()
        assert stats["inbound_queue_size"] == 2
        assert stats["outbound_queue_size"] == 1
        assert stats["total_queued"] == 3

    @patch("pbx.features.call_blending.get_logger")
    def test_get_statistics_defaults(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        stats = cb.get_statistics()
        assert stats["enabled"] is False
        assert stats["total_agents"] == 0
        assert stats["available_agents"] == 0
        assert stats["total_blended_calls"] == 0
        assert stats["inbound_calls"] == 0
        assert stats["outbound_calls"] == 0
        assert stats["actual_blend_ratio"] == 0.0
        assert stats["target_blend_ratio"] == 0.7
        assert stats["inbound_queue_size"] == 0
        assert stats["outbound_queue_size"] == 0

    @patch("pbx.features.call_blending.get_logger")
    def test_get_statistics_with_data(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {"features": {"call_blending": {"enabled": True}}}
        cb = CallBlending(config=config)
        cb.register_agent("agent1", "1001")
        cb.register_agent("agent2", "1002")
        cb.agents["agent2"].available = False

        # Simulate some calls processed
        cb.inbound_calls = 7
        cb.outbound_calls = 3
        cb.total_blended_calls = 10

        cb.queue_call({"call_id": "in-1"}, "inbound")

        stats = cb.get_statistics()
        assert stats["enabled"] is True
        assert stats["total_agents"] == 2
        assert stats["available_agents"] == 1
        assert stats["total_blended_calls"] == 10
        assert stats["inbound_calls"] == 7
        assert stats["outbound_calls"] == 3
        assert stats["actual_blend_ratio"] == 0.7
        assert stats["inbound_queue_size"] == 1
        assert stats["outbound_queue_size"] == 0

    @patch("pbx.features.call_blending.get_logger")
    def test_get_statistics_zero_total_calls(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        cb = CallBlending()
        stats = cb.get_statistics()
        # 0 / max(1, 0) = 0.0
        assert stats["actual_blend_ratio"] == 0.0


@pytest.mark.unit
class TestGetCallBlendingSingleton:
    """Tests for the global get_call_blending function."""

    @patch("pbx.features.call_blending.get_logger")
    def test_get_call_blending_creates_instance(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        # Reset global state
        import pbx.features.call_blending as cb_module

        cb_module._call_blending = None
        instance = get_call_blending()
        assert instance is not None
        assert isinstance(instance, CallBlending)

    @patch("pbx.features.call_blending.get_logger")
    def test_get_call_blending_returns_same_instance(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        import pbx.features.call_blending as cb_module

        cb_module._call_blending = None
        instance1 = get_call_blending()
        instance2 = get_call_blending()
        assert instance1 is instance2

    @patch("pbx.features.call_blending.get_logger")
    def test_get_call_blending_with_config(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        import pbx.features.call_blending as cb_module

        cb_module._call_blending = None
        config = {"features": {"call_blending": {"enabled": True}}}
        instance = get_call_blending(config=config)
        assert instance.enabled is True
        # Cleanup
        cb_module._call_blending = None

    @patch("pbx.features.call_blending.get_logger")
    def test_get_call_blending_ignores_config_after_init(
        self, mock_get_logger: MagicMock
    ) -> None:
        mock_get_logger.return_value = MagicMock()
        import pbx.features.call_blending as cb_module

        cb_module._call_blending = None
        instance1 = get_call_blending()
        assert instance1.enabled is False
        # Passing config on second call is ignored since instance already exists
        config = {"features": {"call_blending": {"enabled": True}}}
        instance2 = get_call_blending(config=config)
        assert instance2.enabled is False
        assert instance1 is instance2
        # Cleanup
        cb_module._call_blending = None


@pytest.mark.unit
class TestCallBlendingEndToEnd:
    """End-to-end blending scenarios."""

    @patch("pbx.features.call_blending.get_logger")
    def test_full_inbound_workflow(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {"features": {"call_blending": {"enabled": True}}}
        cb = CallBlending(config=config)
        cb.register_agent("agent1", "1001", mode="inbound_only")
        cb.set_agent_available("agent1", True)

        cb.queue_call({"call_id": "in-1"}, "inbound")
        cb.queue_call({"call_id": "in-2"}, "inbound")

        call = cb.get_next_call_for_agent("agent1")
        assert call is not None
        assert call["call_id"] == "in-1"

        call = cb.get_next_call_for_agent("agent1")
        assert call is not None
        assert call["call_id"] == "in-2"

        call = cb.get_next_call_for_agent("agent1")
        assert call is None

    @patch("pbx.features.call_blending.get_logger")
    def test_full_outbound_workflow(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {"features": {"call_blending": {"enabled": True}}}
        cb = CallBlending(config=config)
        cb.register_agent("agent1", "1001", mode="outbound_only")

        cb.queue_call({"call_id": "out-1"}, "outbound")
        call = cb.get_next_call_for_agent("agent1")
        assert call is not None
        assert call["call_id"] == "out-1"

    @patch("pbx.features.call_blending.get_logger")
    def test_blended_workflow_maintains_ratio(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        config = {
            "features": {
                "call_blending": {
                    "enabled": True,
                    "inbound_priority": False,
                    "blend_ratio": 0.5,
                }
            }
        }
        cb = CallBlending(config=config)
        cb.register_agent("agent1", "1001", mode="blended")

        # Queue equal number of inbound and outbound
        for i in range(5):
            cb.queue_call({"call_id": f"in-{i}"}, "inbound")
            cb.queue_call({"call_id": f"out-{i}"}, "outbound")

        # Process calls and check distribution
        inbound_count = 0
        outbound_count = 0
        for _ in range(10):
            call = cb.get_next_call_for_agent("agent1")
            if call is None:
                break
            if call["call_id"].startswith("in-"):
                inbound_count += 1
            else:
                outbound_count += 1

        # Both types should have been served
        assert inbound_count > 0
        assert outbound_count > 0
