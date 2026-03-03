"""
Call Queue and ACD (Automatic Call Distribution) system
Manages incoming calls and distributes them to available agents
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pbx.utils.logger import get_logger


class QueueStrategy(Enum):
    """Call distribution strategies"""

    RING_ALL = "ring_all"  # Ring all agents simultaneously
    ROUND_ROBIN = "round_robin"  # Distribute evenly
    LEAST_RECENT = "least_recent"  # Agent who hasn't taken call longest
    FEWEST_CALLS = "fewest_calls"  # Agent with fewest calls
    RANDOM = "random"  # Random distribution


class AgentStatus(Enum):
    """Agent availability status"""

    AVAILABLE = "available"
    BUSY = "busy"
    ON_BREAK = "on_break"
    OFFLINE = "offline"


class QueuedCall:
    """Represents a call in queue"""

    def __init__(self, call_id: str, caller_extension: str, queue_number: str) -> None:
        """
        Initialize queued call

        Args:
            call_id: Call identifier
            caller_extension: Caller's extension
            queue_number: Queue number called
        """
        self.call_id = call_id
        self.caller_extension = caller_extension
        self.queue_number = queue_number
        self.enqueue_time = datetime.now(UTC)
        self.position = 0

    def get_wait_time(self) -> float:
        """Get time spent in queue (seconds)"""
        return (datetime.now(UTC) - self.enqueue_time).total_seconds()


class Agent:
    """Represents a call queue agent"""

    def __init__(self, extension: str, name: str = "") -> None:
        """
        Initialize agent

        Args:
            extension: Agent's extension number
            name: Agent's name
        """
        self.extension = extension
        self.name = name
        self.status = AgentStatus.OFFLINE
        self.calls_taken = 0
        self.last_call_time = None
        self.current_call_id = None

    def set_available(self) -> None:
        """set agent as available"""
        self.status = AgentStatus.AVAILABLE

    def set_busy(self, call_id: str | None = None) -> None:
        """set agent as busy"""
        self.status = AgentStatus.BUSY
        self.current_call_id = call_id

    def set_break(self) -> None:
        """set agent on break"""
        self.status = AgentStatus.ON_BREAK

    def set_offline(self) -> None:
        """set agent offline"""
        self.status = AgentStatus.OFFLINE

    def complete_call(self) -> None:
        """Mark call as completed"""
        self.calls_taken += 1
        self.last_call_time = datetime.now(UTC)
        self.current_call_id = None
        self.status = AgentStatus.AVAILABLE

    def is_available(self) -> bool:
        """Check if agent is available"""
        return self.status == AgentStatus.AVAILABLE


class CallQueue:
    """Manages a call queue"""

    def __init__(
        self,
        queue_number: str,
        name: str,
        strategy: QueueStrategy = QueueStrategy.ROUND_ROBIN,
        max_wait_time: int = 300,
        max_queue_size: int = 50,
    ) -> None:
        """
        Initialize call queue

        Args:
            queue_number: Queue identifier
            name: Queue name
            strategy: Distribution strategy
            max_wait_time: Maximum wait time in seconds
            max_queue_size: Maximum number of calls in queue
        """
        self.queue_number = queue_number
        self.name = name
        self.strategy = strategy
        self.max_wait_time = max_wait_time
        self.max_queue_size = max_queue_size
        self.queue = []
        self.agents = {}
        self.logger = get_logger()
        self.round_robin_index = 0

    def add_agent(self, agent: Any) -> None:
        """
        Add agent to queue

        Args:
            agent: Agent object
        """
        self.agents[agent.extension] = agent
        self.logger.info(f"Added agent {agent.extension} to queue {self.queue_number}")

    def remove_agent(self, extension: str) -> None:
        """Remove agent from queue"""
        if extension in self.agents:
            del self.agents[extension]

    def enqueue(self, call_id: str, caller_extension: str) -> QueuedCall | None:
        """
        Add call to queue

        Args:
            call_id: Call identifier
            caller_extension: Caller's extension

        Returns:
            QueuedCall object or None if queue is full
        """
        if len(self.queue) >= self.max_queue_size:
            self.logger.warning(f"Queue {self.queue_number} is full")
            return None

        queued_call = QueuedCall(call_id, caller_extension, self.queue_number)
        queued_call.position = len(self.queue) + 1
        self.queue.append(queued_call)

        self.logger.info(
            f"Call {call_id} added to queue {self.queue_number}, position {queued_call.position}"
        )
        return queued_call

    def dequeue(self) -> Any | None:
        """
        Remove and return next call from queue

        Returns:
            QueuedCall object or None
        """
        if self.queue:
            call = self.queue.pop(0)
            self._update_positions()
            return call
        return None

    def _update_positions(self) -> None:
        """Update position numbers for queued calls"""
        for i, call in enumerate(self.queue):
            call.position = i + 1

    def get_next_agent(self) -> Any | None:
        """
        Get next available agent based on strategy

        Returns:
            Agent object or None
        """
        available_agents = [a for a in self.agents.values() if a.is_available()]

        if not available_agents:
            return None

        if self.strategy == QueueStrategy.RING_ALL:
            # Return all available agents
            return available_agents

        if self.strategy == QueueStrategy.ROUND_ROBIN:
            # Round robin distribution
            if available_agents:
                agent = available_agents[self.round_robin_index % len(available_agents)]
                self.round_robin_index += 1
                return agent

        elif self.strategy == QueueStrategy.LEAST_RECENT:
            # Agent who hasn't taken a call longest
            agent = min(
                available_agents, key=lambda a: a.last_call_time or datetime.min.replace(tzinfo=UTC)
            )
            return agent

        elif self.strategy == QueueStrategy.FEWEST_CALLS:
            # Agent with fewest calls
            agent = min(available_agents, key=lambda a: a.calls_taken)
            return agent

        return available_agents[0] if available_agents else None

    def process_queue(self) -> list:
        """
        Process queued calls and assign to agents

        Returns:
            list of (call, agent) tuples that were assigned
        """
        assignments = []

        # Check for expired calls
        expired = [c for c in self.queue if c.get_wait_time() > self.max_wait_time]
        for call in expired:
            self.queue.remove(call)
            self.logger.warning(f"Call {call.call_id} expired in queue")

        # Assign calls to available agents
        while self.queue:
            result = self.get_next_agent()
            if not result:
                break

            call = self.dequeue()
            if call:
                # RING_ALL returns a list of agents; other strategies return a single agent
                if isinstance(result, list):
                    for agent in result:
                        agent.set_busy(call.call_id)
                    assignments.append((call, result))
                    self.logger.info(f"Assigned call {call.call_id} to {len(result)} agents (ring all)")
                else:
                    result.set_busy(call.call_id)
                    assignments.append((call, result))
                    self.logger.info(f"Assigned call {call.call_id} to agent {result.extension}")

        return assignments

    def get_queue_status(self) -> dict:
        """Get queue status information"""
        available_agents = sum(1 for a in self.agents.values() if a.is_available())

        return {
            "queue_number": self.queue_number,
            "name": self.name,
            "calls_waiting": len(self.queue),
            "total_agents": len(self.agents),
            "available_agents": available_agents,
            "average_wait_time": self._get_average_wait_time(),
        }

    def _get_average_wait_time(self) -> float:
        """Calculate average wait time for calls in queue"""
        if not self.queue:
            return 0
        return sum(c.get_wait_time() for c in self.queue) / len(self.queue)


class QueueSystem:
    """Manages all call queues"""

    def __init__(self) -> None:
        """Initialize queue system"""
        self.queues = {}
        self.logger = get_logger()

    def create_queue(
        self, queue_number: str, name: str, strategy: QueueStrategy = QueueStrategy.ROUND_ROBIN
    ) -> Any:
        """
        Create new queue

        Args:
            queue_number: Queue identifier
            name: Queue name
            strategy: Distribution strategy

        Returns:
            CallQueue object
        """
        queue = CallQueue(queue_number, name, strategy)
        self.queues[queue_number] = queue
        self.logger.info(f"Created queue {queue_number}: {name}")
        return queue

    def get_queue(self, queue_number: str) -> dict | None:
        """Get queue by number"""
        return self.queues.get(queue_number)

    def enqueue_call(self, queue_number: str, call_id: str, caller_extension: str) -> bool:
        """
        Add call to queue

        Args:
            queue_number: Queue number
            call_id: Call identifier
            caller_extension: Caller's extension

        Returns:
            True if enqueued successfully
        """
        queue = self.get_queue(queue_number)
        if queue:
            return queue.enqueue(call_id, caller_extension) is not None
        return False

    def process_all_queues(self) -> list:
        """Process all queues and return assignments"""
        all_assignments = []
        for queue in self.queues.values():
            assignments = queue.process_queue()
            all_assignments.extend(assignments)
        return all_assignments

    def get_all_status(self) -> list[dict]:
        """Get status of all queues"""
        return [q.get_queue_status() for q in self.queues.values()]
