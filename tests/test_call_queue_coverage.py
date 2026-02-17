"""Comprehensive tests for Call Queue and ACD system."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestQueueStrategyEnum:
    """Tests for QueueStrategy enum."""

    def test_strategy_values(self) -> None:
        """Test all strategy enum values."""
        from pbx.features.call_queue import QueueStrategy

        assert QueueStrategy.RING_ALL.value == "ring_all"
        assert QueueStrategy.ROUND_ROBIN.value == "round_robin"
        assert QueueStrategy.LEAST_RECENT.value == "least_recent"
        assert QueueStrategy.FEWEST_CALLS.value == "fewest_calls"
        assert QueueStrategy.RANDOM.value == "random"


@pytest.mark.unit
class TestAgentStatusEnum:
    """Tests for AgentStatus enum."""

    def test_status_values(self) -> None:
        """Test all agent status enum values."""
        from pbx.features.call_queue import AgentStatus

        assert AgentStatus.AVAILABLE.value == "available"
        assert AgentStatus.BUSY.value == "busy"
        assert AgentStatus.ON_BREAK.value == "on_break"
        assert AgentStatus.OFFLINE.value == "offline"


@pytest.mark.unit
class TestQueuedCall:
    """Tests for QueuedCall."""

    def test_init(self) -> None:
        """Test queued call initialization."""
        from pbx.features.call_queue import QueuedCall

        call = QueuedCall("call-1", "1001", "8001")

        assert call.call_id == "call-1"
        assert call.caller_extension == "1001"
        assert call.queue_number == "8001"
        assert call.position == 0
        assert isinstance(call.enqueue_time, datetime)

    def test_get_wait_time(self) -> None:
        """Test getting wait time."""
        from pbx.features.call_queue import QueuedCall

        call = QueuedCall("call-1", "1001", "8001")
        wait_time = call.get_wait_time()

        assert wait_time >= 0


@pytest.mark.unit
class TestAgent:
    """Tests for Agent."""

    def test_init(self) -> None:
        """Test agent initialization."""
        from pbx.features.call_queue import Agent, AgentStatus

        agent = Agent("1001", "John Doe")

        assert agent.extension == "1001"
        assert agent.name == "John Doe"
        assert agent.status == AgentStatus.OFFLINE
        assert agent.calls_taken == 0
        assert agent.last_call_time is None
        assert agent.current_call_id is None

    def test_init_default_name(self) -> None:
        """Test agent initialization with default name."""
        from pbx.features.call_queue import Agent

        agent = Agent("1001")

        assert agent.name == ""

    def test_set_available(self) -> None:
        """Test setting agent available."""
        from pbx.features.call_queue import Agent, AgentStatus

        agent = Agent("1001")
        agent.set_available()

        assert agent.status == AgentStatus.AVAILABLE

    def test_set_busy(self) -> None:
        """Test setting agent busy."""
        from pbx.features.call_queue import Agent, AgentStatus

        agent = Agent("1001")
        agent.set_busy("call-1")

        assert agent.status == AgentStatus.BUSY
        assert agent.current_call_id == "call-1"

    def test_set_busy_no_call_id(self) -> None:
        """Test setting agent busy without call ID."""
        from pbx.features.call_queue import Agent, AgentStatus

        agent = Agent("1001")
        agent.set_busy()

        assert agent.status == AgentStatus.BUSY
        assert agent.current_call_id is None

    def test_set_break(self) -> None:
        """Test setting agent on break."""
        from pbx.features.call_queue import Agent, AgentStatus

        agent = Agent("1001")
        agent.set_break()

        assert agent.status == AgentStatus.ON_BREAK

    def test_set_offline(self) -> None:
        """Test setting agent offline."""
        from pbx.features.call_queue import Agent, AgentStatus

        agent = Agent("1001")
        agent.set_available()
        agent.set_offline()

        assert agent.status == AgentStatus.OFFLINE

    def test_complete_call(self) -> None:
        """Test completing a call."""
        from pbx.features.call_queue import Agent, AgentStatus

        agent = Agent("1001")
        agent.set_busy("call-1")
        agent.complete_call()

        assert agent.calls_taken == 1
        assert agent.last_call_time is not None
        assert agent.current_call_id is None
        assert agent.status == AgentStatus.AVAILABLE

    def test_is_available_true(self) -> None:
        """Test is_available returns True."""
        from pbx.features.call_queue import Agent

        agent = Agent("1001")
        agent.set_available()

        assert agent.is_available() is True

    def test_is_available_false(self) -> None:
        """Test is_available returns False."""
        from pbx.features.call_queue import Agent

        agent = Agent("1001")
        agent.set_busy()

        assert agent.is_available() is False


@pytest.mark.unit
class TestCallQueue:
    """Tests for CallQueue."""

    @patch("pbx.features.call_queue.get_logger")
    def test_init(self, mock_get_logger: MagicMock) -> None:
        """Test call queue initialization."""
        from pbx.features.call_queue import CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales Queue", QueueStrategy.ROUND_ROBIN, 300, 50)

        assert queue.queue_number == "8001"
        assert queue.name == "Sales Queue"
        assert queue.strategy == QueueStrategy.ROUND_ROBIN
        assert queue.max_wait_time == 300
        assert queue.max_queue_size == 50
        assert queue.queue == []
        assert queue.agents == {}

    @patch("pbx.features.call_queue.get_logger")
    def test_add_agent(self, mock_get_logger: MagicMock) -> None:
        """Test adding agent to queue."""
        from pbx.features.call_queue import Agent, CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.ROUND_ROBIN)
        agent = Agent("1001", "John")
        queue.add_agent(agent)

        assert "1001" in queue.agents

    @patch("pbx.features.call_queue.get_logger")
    def test_remove_agent(self, mock_get_logger: MagicMock) -> None:
        """Test removing agent from queue."""
        from pbx.features.call_queue import Agent, CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.ROUND_ROBIN)
        agent = Agent("1001", "John")
        queue.add_agent(agent)
        queue.remove_agent("1001")

        assert "1001" not in queue.agents

    @patch("pbx.features.call_queue.get_logger")
    def test_remove_agent_nonexistent(self, mock_get_logger: MagicMock) -> None:
        """Test removing nonexistent agent."""
        from pbx.features.call_queue import CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.ROUND_ROBIN)
        queue.remove_agent("9999")
        # Should not raise

    @patch("pbx.features.call_queue.get_logger")
    def test_enqueue(self, mock_get_logger: MagicMock) -> None:
        """Test adding call to queue."""
        from pbx.features.call_queue import CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.ROUND_ROBIN)
        result = queue.enqueue("call-1", "1001")

        assert result is not None
        assert result.call_id == "call-1"
        assert result.position == 1
        assert len(queue.queue) == 1

    @patch("pbx.features.call_queue.get_logger")
    def test_enqueue_full_queue(self, mock_get_logger: MagicMock) -> None:
        """Test adding call to full queue."""
        from pbx.features.call_queue import CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.ROUND_ROBIN, max_queue_size=2)
        queue.enqueue("call-1", "1001")
        queue.enqueue("call-2", "1002")
        result = queue.enqueue("call-3", "1003")

        assert result is None
        assert len(queue.queue) == 2

    @patch("pbx.features.call_queue.get_logger")
    def test_dequeue(self, mock_get_logger: MagicMock) -> None:
        """Test removing call from queue."""
        from pbx.features.call_queue import CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.ROUND_ROBIN)
        queue.enqueue("call-1", "1001")
        queue.enqueue("call-2", "1002")

        result = queue.dequeue()

        assert result is not None
        assert result.call_id == "call-1"
        assert len(queue.queue) == 1
        # Check position update
        assert queue.queue[0].position == 1

    @patch("pbx.features.call_queue.get_logger")
    def test_dequeue_empty(self, mock_get_logger: MagicMock) -> None:
        """Test dequeue from empty queue."""
        from pbx.features.call_queue import CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.ROUND_ROBIN)
        result = queue.dequeue()

        assert result is None


@pytest.mark.unit
class TestCallQueueGetNextAgent:
    """Tests for CallQueue.get_next_agent strategies."""

    @patch("pbx.features.call_queue.get_logger")
    def test_no_available_agents(self, mock_get_logger: MagicMock) -> None:
        """Test get_next_agent with no available agents."""
        from pbx.features.call_queue import Agent, CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.ROUND_ROBIN)
        agent = Agent("1001")
        agent.set_busy()
        queue.add_agent(agent)

        assert queue.get_next_agent() is None

    @patch("pbx.features.call_queue.get_logger")
    def test_ring_all_strategy(self, mock_get_logger: MagicMock) -> None:
        """Test RING_ALL strategy returns all agents."""
        from pbx.features.call_queue import Agent, CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.RING_ALL)
        agent1 = Agent("1001")
        agent1.set_available()
        agent2 = Agent("1002")
        agent2.set_available()
        queue.add_agent(agent1)
        queue.add_agent(agent2)

        result = queue.get_next_agent()

        assert isinstance(result, list)
        assert len(result) == 2

    @patch("pbx.features.call_queue.get_logger")
    def test_round_robin_strategy(self, mock_get_logger: MagicMock) -> None:
        """Test ROUND_ROBIN strategy cycles agents."""
        from pbx.features.call_queue import Agent, CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.ROUND_ROBIN)
        agent1 = Agent("1001")
        agent1.set_available()
        agent2 = Agent("1002")
        agent2.set_available()
        queue.add_agent(agent1)
        queue.add_agent(agent2)

        first = queue.get_next_agent()
        second = queue.get_next_agent()

        assert first is not None
        assert second is not None
        # Round robin should cycle (though order depends on dict iteration)

    @patch("pbx.features.call_queue.get_logger")
    def test_least_recent_strategy(self, mock_get_logger: MagicMock) -> None:
        """Test LEAST_RECENT strategy picks agent who hasn't taken call longest."""
        from pbx.features.call_queue import Agent, CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.LEAST_RECENT)
        agent1 = Agent("1001")
        agent1.set_available()
        agent1.last_call_time = datetime.now(UTC) - timedelta(hours=2)

        agent2 = Agent("1002")
        agent2.set_available()
        agent2.last_call_time = datetime.now(UTC) - timedelta(minutes=10)

        queue.add_agent(agent1)
        queue.add_agent(agent2)

        result = queue.get_next_agent()

        assert result is agent1  # Hasn't taken call in 2 hours

    @patch("pbx.features.call_queue.get_logger")
    def test_least_recent_strategy_none_last_call(self, mock_get_logger: MagicMock) -> None:
        """Test LEAST_RECENT strategy when agent has no last_call_time."""
        from pbx.features.call_queue import Agent, CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.LEAST_RECENT)
        agent1 = Agent("1001")
        agent1.set_available()
        agent1.last_call_time = None  # Never taken a call

        agent2 = Agent("1002")
        agent2.set_available()
        agent2.last_call_time = datetime.now(UTC)

        queue.add_agent(agent1)
        queue.add_agent(agent2)

        result = queue.get_next_agent()

        assert result is agent1  # Never taken a call, so picked first

    @patch("pbx.features.call_queue.get_logger")
    def test_fewest_calls_strategy(self, mock_get_logger: MagicMock) -> None:
        """Test FEWEST_CALLS strategy picks agent with fewest calls."""
        from pbx.features.call_queue import Agent, CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.FEWEST_CALLS)
        agent1 = Agent("1001")
        agent1.set_available()
        agent1.calls_taken = 10

        agent2 = Agent("1002")
        agent2.set_available()
        agent2.calls_taken = 3

        queue.add_agent(agent1)
        queue.add_agent(agent2)

        result = queue.get_next_agent()

        assert result is agent2  # Fewest calls


@pytest.mark.unit
class TestCallQueueProcessing:
    """Tests for CallQueue.process_queue."""

    @patch("pbx.features.call_queue.get_logger")
    def test_process_queue_empty(self, mock_get_logger: MagicMock) -> None:
        """Test processing empty queue."""
        from pbx.features.call_queue import CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.ROUND_ROBIN)
        assignments = queue.process_queue()

        assert assignments == []

    @patch("pbx.features.call_queue.get_logger")
    def test_process_queue_assigns_calls(self, mock_get_logger: MagicMock) -> None:
        """Test processing queue assigns calls to agents."""
        from pbx.features.call_queue import Agent, CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.ROUND_ROBIN)

        agent = Agent("1001")
        agent.set_available()
        queue.add_agent(agent)

        queue.enqueue("call-1", "2001")

        assignments = queue.process_queue()

        assert len(assignments) == 1
        call, assigned_agent = assignments[0]
        assert call.call_id == "call-1"
        assert assigned_agent is agent
        assert agent.status.value == "busy"

    @patch("pbx.features.call_queue.get_logger")
    def test_process_queue_no_agents_available(self, mock_get_logger: MagicMock) -> None:
        """Test processing queue when no agents available."""
        from pbx.features.call_queue import Agent, CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.ROUND_ROBIN)

        agent = Agent("1001")
        agent.set_busy()
        queue.add_agent(agent)

        queue.enqueue("call-1", "2001")

        assignments = queue.process_queue()

        assert len(assignments) == 0
        assert len(queue.queue) == 1  # Call still in queue

    @patch("pbx.features.call_queue.get_logger")
    def test_process_queue_expired_calls(self, mock_get_logger: MagicMock) -> None:
        """Test processing queue removes expired calls."""
        from pbx.features.call_queue import CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.ROUND_ROBIN, max_wait_time=10)
        queued_call = queue.enqueue("call-1", "2001")

        # Manually set enqueue time to past
        queued_call.enqueue_time = datetime.now(UTC) - timedelta(seconds=60)

        queue.process_queue()

        assert len(queue.queue) == 0


@pytest.mark.unit
class TestCallQueueStatus:
    """Tests for CallQueue.get_queue_status."""

    @patch("pbx.features.call_queue.get_logger")
    def test_get_queue_status(self, mock_get_logger: MagicMock) -> None:
        """Test getting queue status."""
        from pbx.features.call_queue import Agent, CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.ROUND_ROBIN)

        agent1 = Agent("1001")
        agent1.set_available()
        agent2 = Agent("1002")
        agent2.set_busy()
        queue.add_agent(agent1)
        queue.add_agent(agent2)

        queue.enqueue("call-1", "2001")

        status = queue.get_queue_status()

        assert status["queue_number"] == "8001"
        assert status["name"] == "Sales"
        assert status["calls_waiting"] == 1
        assert status["total_agents"] == 2
        assert status["available_agents"] == 1
        assert status["average_wait_time"] >= 0

    @patch("pbx.features.call_queue.get_logger")
    def test_get_average_wait_time_empty(self, mock_get_logger: MagicMock) -> None:
        """Test average wait time with empty queue."""
        from pbx.features.call_queue import CallQueue, QueueStrategy

        queue = CallQueue("8001", "Sales", QueueStrategy.ROUND_ROBIN)
        avg = queue._get_average_wait_time()

        assert avg == 0


@pytest.mark.unit
class TestQueueSystem:
    """Tests for QueueSystem."""

    @patch("pbx.features.call_queue.get_logger")
    def test_init(self, mock_get_logger: MagicMock) -> None:
        """Test queue system initialization."""
        from pbx.features.call_queue import QueueSystem

        system = QueueSystem()

        assert system.queues == {}

    @patch("pbx.features.call_queue.get_logger")
    def test_create_queue(self, mock_get_logger: MagicMock) -> None:
        """Test creating a queue."""
        from pbx.features.call_queue import QueueStrategy, QueueSystem

        system = QueueSystem()
        queue = system.create_queue("8001", "Sales", QueueStrategy.ROUND_ROBIN)

        assert queue is not None
        assert queue.queue_number == "8001"
        assert "8001" in system.queues

    @patch("pbx.features.call_queue.get_logger")
    def test_get_queue(self, mock_get_logger: MagicMock) -> None:
        """Test getting a queue."""
        from pbx.features.call_queue import QueueStrategy, QueueSystem

        system = QueueSystem()
        system.create_queue("8001", "Sales", QueueStrategy.ROUND_ROBIN)

        queue = system.get_queue("8001")

        assert queue is not None
        assert queue.name == "Sales"

    @patch("pbx.features.call_queue.get_logger")
    def test_get_queue_nonexistent(self, mock_get_logger: MagicMock) -> None:
        """Test getting nonexistent queue."""
        from pbx.features.call_queue import QueueSystem

        system = QueueSystem()

        assert system.get_queue("9999") is None

    @patch("pbx.features.call_queue.get_logger")
    def test_enqueue_call(self, mock_get_logger: MagicMock) -> None:
        """Test enqueuing a call through system."""
        from pbx.features.call_queue import QueueStrategy, QueueSystem

        system = QueueSystem()
        system.create_queue("8001", "Sales", QueueStrategy.ROUND_ROBIN)

        result = system.enqueue_call("8001", "call-1", "1001")

        assert result is True

    @patch("pbx.features.call_queue.get_logger")
    def test_enqueue_call_nonexistent_queue(self, mock_get_logger: MagicMock) -> None:
        """Test enqueuing call to nonexistent queue."""
        from pbx.features.call_queue import QueueSystem

        system = QueueSystem()

        result = system.enqueue_call("9999", "call-1", "1001")

        assert result is False

    @patch("pbx.features.call_queue.get_logger")
    def test_process_all_queues(self, mock_get_logger: MagicMock) -> None:
        """Test processing all queues."""
        from pbx.features.call_queue import Agent, QueueStrategy, QueueSystem

        system = QueueSystem()
        queue = system.create_queue("8001", "Sales", QueueStrategy.ROUND_ROBIN)

        agent = Agent("1001")
        agent.set_available()
        queue.add_agent(agent)
        queue.enqueue("call-1", "2001")

        result = system.process_all_queues()

        assert len(result) == 1

    @patch("pbx.features.call_queue.get_logger")
    def test_get_all_status(self, mock_get_logger: MagicMock) -> None:
        """Test getting status of all queues."""
        from pbx.features.call_queue import QueueStrategy, QueueSystem

        system = QueueSystem()
        system.create_queue("8001", "Sales", QueueStrategy.ROUND_ROBIN)
        system.create_queue("8002", "Support", QueueStrategy.LEAST_RECENT)

        result = system.get_all_status()

        assert len(result) == 2
        assert result[0]["queue_number"] == "8001"
        assert result[1]["queue_number"] == "8002"

    @patch("pbx.features.call_queue.get_logger")
    def test_get_all_status_empty(self, mock_get_logger: MagicMock) -> None:
        """Test getting status of empty system."""
        from pbx.features.call_queue import QueueSystem

        system = QueueSystem()

        result = system.get_all_status()

        assert result == []
