"""Unit tests for pbx.features.call_queue — Agent, CallQueue, QueueSystem."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
@patch("pbx.features.call_queue.get_logger", return_value=MagicMock())
class TestCallQueue:
    """Tests for call queue classes."""

    def test_agent_status_transitions(self, _mock_logger):
        """Agent status transitions through all states."""
        from pbx.features.call_queue import Agent, AgentStatus

        agent = Agent("1001", "Alice")
        assert agent.status == AgentStatus.OFFLINE

        agent.set_available()
        assert agent.status == AgentStatus.AVAILABLE

        agent.set_busy("call1")
        assert agent.status == AgentStatus.BUSY

        agent.set_break()
        assert agent.status == AgentStatus.ON_BREAK

        agent.set_offline()
        assert agent.status == AgentStatus.OFFLINE

    def test_agent_complete_call(self, _mock_logger):
        """complete_call increments calls_taken and resets status."""
        from pbx.features.call_queue import Agent, AgentStatus

        agent = Agent("1001", "Alice")
        agent.set_busy("call1")
        assert agent.current_call_id == "call1"

        agent.complete_call()

        assert agent.calls_taken == 1
        assert agent.status == AgentStatus.AVAILABLE
        assert agent.current_call_id is None
        assert agent.last_call_time is not None

    def test_queue_enqueue_dequeue(self, _mock_logger):
        """Enqueue assigns positions; dequeue reindexes remaining."""
        from pbx.features.call_queue import CallQueue, QueueStrategy

        q = CallQueue("100", "Support", strategy=QueueStrategy.ROUND_ROBIN)
        c1 = q.enqueue("call1", "2001")
        c2 = q.enqueue("call2", "2002")
        c3 = q.enqueue("call3", "2003")

        assert c1.position == 1
        assert c2.position == 2
        assert c3.position == 3
        assert len(q.queue) == 3

        first = q.dequeue()
        assert first.call_id == "call1"
        assert len(q.queue) == 2
        assert q.queue[0].position == 1
        assert q.queue[1].position == 2

    def test_queue_full(self, _mock_logger):
        """Enqueue returns None when queue is full."""
        from pbx.features.call_queue import CallQueue, QueueStrategy

        q = CallQueue("100", "Support", strategy=QueueStrategy.ROUND_ROBIN, max_queue_size=2)
        assert q.enqueue("call1", "2001") is not None
        assert q.enqueue("call2", "2002") is not None
        assert q.enqueue("call3", "2003") is None

    def test_next_agent_round_robin(self, _mock_logger):
        """ROUND_ROBIN cycles through available agents."""
        from pbx.features.call_queue import Agent, CallQueue, QueueStrategy

        q = CallQueue("100", "Support", strategy=QueueStrategy.ROUND_ROBIN)
        agents = [Agent(f"100{i}", f"Agent{i}") for i in range(3)]
        for a in agents:
            a.set_available()
            q.add_agent(a)

        first = q.get_next_agent()
        second = q.get_next_agent()
        third = q.get_next_agent()

        # Should cycle through all three
        selected = {first.extension, second.extension, third.extension}
        assert len(selected) == 3

    def test_next_agent_fewest_calls(self, _mock_logger):
        """FEWEST_CALLS returns the agent with the lowest calls_taken."""
        from pbx.features.call_queue import Agent, CallQueue, QueueStrategy

        q = CallQueue("100", "Support", strategy=QueueStrategy.FEWEST_CALLS)

        a1 = Agent("1001", "Alice")
        a1.calls_taken = 5
        a1.set_available()

        a2 = Agent("1002", "Bob")
        a2.calls_taken = 1
        a2.set_available()

        a3 = Agent("1003", "Charlie")
        a3.calls_taken = 3
        a3.set_available()

        q.add_agent(a1)
        q.add_agent(a2)
        q.add_agent(a3)

        agent = q.get_next_agent()
        assert agent.extension == "1002"

    def test_process_queue(self, _mock_logger):
        """process_queue matches queued calls to available agents."""
        from pbx.features.call_queue import Agent, AgentStatus, CallQueue, QueueStrategy

        q = CallQueue("100", "Support", strategy=QueueStrategy.ROUND_ROBIN)

        a1 = Agent("1001", "Alice")
        a1.set_available()
        a2 = Agent("1002", "Bob")
        a2.set_available()
        q.add_agent(a1)
        q.add_agent(a2)

        q.enqueue("call1", "2001")
        q.enqueue("call2", "2002")

        assignments = q.process_queue()

        assert len(assignments) == 2
        for _call, agent in assignments:
            assert agent.status == AgentStatus.BUSY
        assert len(q.queue) == 0

    def test_queue_system_create_enqueue(self, _mock_logger):
        """QueueSystem.create_queue and enqueue_call basics."""
        from pbx.features.call_queue import QueueSystem

        system = QueueSystem()
        system.create_queue("100", "Support")

        assert system.enqueue_call("100", "call1", "2001") is True
        assert system.enqueue_call("999", "call2", "2002") is False
