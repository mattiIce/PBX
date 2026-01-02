"""
Call Blending
Mix inbound and outbound calls for agent efficiency
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pbx.utils.logger import get_logger


class CallDirection(Enum):
    """Call direction"""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class AgentMode(Enum):
    """Agent operating mode"""

    INBOUND_ONLY = "inbound_only"
    OUTBOUND_ONLY = "outbound_only"
    BLENDED = "blended"
    AUTO = "auto"


class Agent:
    """Represents an agent"""

    def __init__(self, agent_id: str, extension: str):
        """Initialize agent"""
        self.agent_id = agent_id
        self.extension = extension
        self.mode = AgentMode.BLENDED
        self.available = True
        self.current_call = None
        self.inbound_calls_handled = 0
        self.outbound_calls_handled = 0


class CallBlending:
    """
    Call Blending System

    Intelligently mix inbound and outbound calls to maximize agent efficiency.
    Features:
    - Dynamic agent mode switching
    - Priority-based call distribution
    - Inbound surge protection
    - Outbound campaign integration
    - Real-time workload balancing
    """

    def __init__(self, config=None):
        """Initialize call blending"""
        self.logger = get_logger()
        self.config = config or {}

        # Configuration
        blending_config = self.config.get("features", {}).get("call_blending", {})
        self.enabled = blending_config.get("enabled", False)
        self.inbound_priority = blending_config.get("inbound_priority", True)
        self.max_inbound_wait = blending_config.get("max_inbound_wait", 30)  # seconds
        self.blend_ratio = blending_config.get("blend_ratio", 0.7)  # 70% inbound, 30% outbound

        # Agents
        self.agents: Dict[str, Agent] = {}

        # Call queues
        self.inbound_queue: List[Dict] = []
        self.outbound_queue: List[Dict] = []

        # Statistics
        self.total_blended_calls = 0
        self.inbound_calls = 0
        self.outbound_calls = 0

        self.logger.info("Call blending system initialized")
        self.logger.info(f"  Inbound priority: {self.inbound_priority}")
        self.logger.info(f"  Blend ratio: {self.blend_ratio:.0%} inbound")
        self.logger.info(f"  Enabled: {self.enabled}")

    def get_next_call_for_agent(self, agent_id: str) -> Optional[Dict]:
        """
        Get next call for agent based on blending rules

        Args:
            agent_id: Agent identifier

        Returns:
            Optional[Dict]: Next call or None
        """
        if agent_id not in self.agents:
            return None

        agent = self.agents[agent_id]

        if not agent.available:
            return None

        # Determine which call to assign based on mode and priority
        if agent.mode == AgentMode.INBOUND_ONLY:
            return self._get_inbound_call()
        elif agent.mode == AgentMode.OUTBOUND_ONLY:
            return self._get_outbound_call()
        elif agent.mode == AgentMode.BLENDED:
            return self._blend_call(agent)
        elif agent.mode == AgentMode.AUTO:
            return self._auto_blend_call(agent)

        return None

    def _get_inbound_call(self) -> Optional[Dict]:
        """Get next inbound call"""
        if self.inbound_queue:
            call = self.inbound_queue.pop(0)
            self.inbound_calls += 1
            return call
        return None

    def _get_outbound_call(self) -> Optional[Dict]:
        """Get next outbound call"""
        if self.outbound_queue:
            call = self.outbound_queue.pop(0)
            self.outbound_calls += 1
            return call
        return None

    def _blend_call(self, agent: Agent) -> Optional[Dict]:
        """
        Blend calls based on configured ratio

        Args:
            agent: Agent to assign call to

        Returns:
            Optional[Dict]: Next call
        """
        # Always prioritize inbound if queue is building
        if self.inbound_priority and self.inbound_queue:
            oldest_inbound = self.inbound_queue[0]
            wait_time = (datetime.now() - oldest_inbound["queued_at"]).total_seconds()

            if wait_time > self.max_inbound_wait:
                return self._get_inbound_call()

        # Calculate current ratio
        total = agent.inbound_calls_handled + agent.outbound_calls_handled
        if total == 0:
            current_inbound_ratio = 0.0
        else:
            current_inbound_ratio = agent.inbound_calls_handled / total

        # Determine next call type to maintain ratio
        if current_inbound_ratio < self.blend_ratio and self.inbound_queue:
            call = self._get_inbound_call()
            if call:
                agent.inbound_calls_handled += 1
                self.total_blended_calls += 1
                return call

        if self.outbound_queue:
            call = self._get_outbound_call()
            if call:
                agent.outbound_calls_handled += 1
                self.total_blended_calls += 1
                return call

        # Fallback to any available call
        return self._get_inbound_call() or self._get_outbound_call()

    def _auto_blend_call(self, agent: Agent) -> Optional[Dict]:
        """
        Automatically blend based on current conditions

        Args:
            agent: Agent to assign call to

        Returns:
            Optional[Dict]: Next call
        """
        # Analyze current queue lengths
        inbound_count = len(self.inbound_queue)
        outbound_count = len(self.outbound_queue)

        # Switch to inbound-only if inbound surge
        if inbound_count > 10:
            return self._get_inbound_call()

        # If no inbound, do outbound
        if inbound_count == 0 and outbound_count > 0:
            return self._get_outbound_call()

        # Otherwise use normal blending
        return self._blend_call(agent)

    def queue_call(self, call: Dict, direction: str):
        """
        Queue a call for blending

        Args:
            call: Call information
            direction: Call direction (inbound/outbound)
        """
        call["queued_at"] = datetime.now()

        if direction == "inbound":
            self.inbound_queue.append(call)
            self.logger.debug(f"Queued inbound call, queue size: {len(self.inbound_queue)}")
        else:
            self.outbound_queue.append(call)
            self.logger.debug(f"Queued outbound call, queue size: {len(self.outbound_queue)}")

    def set_agent_available(self, agent_id: str, available: bool):
        """Set agent availability"""
        if not self.enabled:
            self.logger.error("Cannot set agent availability: Call blending feature is not enabled")
            return False

        if agent_id in self.agents:
            self.agents[agent_id].available = available
            return True

        self.logger.warning(f"Agent {agent_id} not found in call blending system")
        return False

    def register_agent(self, agent_id: str, extension: str, mode: str = "blended") -> Dict:
        """
        Register a new agent for call blending

        Args:
            agent_id: Unique agent identifier
            extension: Agent's extension number
            mode: Initial operating mode (default: blended)

        Returns:
            Dict: Registration result
        """
        if agent_id in self.agents:
            return {"success": False, "error": "Agent already registered"}

        agent = Agent(agent_id, extension)

        # Set initial mode
        if mode == "inbound_only":
            agent.mode = AgentMode.INBOUND_ONLY
        elif mode == "outbound_only":
            agent.mode = AgentMode.OUTBOUND_ONLY
        elif mode == "auto":
            agent.mode = AgentMode.AUTO
        else:
            agent.mode = AgentMode.BLENDED

        self.agents[agent_id] = agent

        self.logger.info(f"Registered agent {agent_id} (ext {extension}) in {mode} mode")

        return {
            "success": True,
            "agent_id": agent_id,
            "extension": extension,
            "mode": agent.mode.value,
        }

    def get_all_agents(self) -> List[Dict]:
        """Get all registered agents"""
        return [
            {
                "agent_id": agent.agent_id,
                "extension": agent.extension,
                "mode": agent.mode.value,
                "available": agent.available,
                "current_call": agent.current_call,
                "inbound_calls_handled": agent.inbound_calls_handled,
                "outbound_calls_handled": agent.outbound_calls_handled,
            }
            for agent in self.agents.values()
        ]

    def get_agent_status(self, agent_id: str) -> Optional[Dict]:
        """Get status of a specific agent"""
        if agent_id not in self.agents:
            return None

        agent = self.agents[agent_id]
        return {
            "agent_id": agent.agent_id,
            "extension": agent.extension,
            "mode": agent.mode.value,
            "available": agent.available,
            "current_call": agent.current_call,
            "inbound_calls_handled": agent.inbound_calls_handled,
            "outbound_calls_handled": agent.outbound_calls_handled,
        }

    def set_agent_mode(self, agent_id: str, mode: str) -> Dict:
        """Set agent operating mode"""
        if agent_id not in self.agents:
            return {"success": False, "error": "Agent not found"}

        agent = self.agents[agent_id]
        try:
            if mode == "inbound_only":
                agent.mode = AgentMode.INBOUND_ONLY
            elif mode == "outbound_only":
                agent.mode = AgentMode.OUTBOUND_ONLY
            elif mode == "blended":
                agent.mode = AgentMode.BLENDED
            elif mode == "auto":
                agent.mode = AgentMode.AUTO
            else:
                return {"success": False, "error": "Invalid mode"}

            self.logger.info(f"Set agent {agent_id} mode to {mode}")
            return {"success": True, "agent_id": agent_id, "mode": mode}
        except Exception as e:
            self.logger.error(f"Error setting agent mode: {e}")
            return {"success": False, "error": str(e)}

    def get_queue_statistics(self) -> Dict:
        """Get queue statistics"""
        return {
            "inbound_queue_size": len(self.inbound_queue),
            "outbound_queue_size": len(self.outbound_queue),
            "total_queued": len(self.inbound_queue) + len(self.outbound_queue),
        }

    def get_statistics(self) -> Dict:
        """Get blending statistics"""
        total_calls = self.inbound_calls + self.outbound_calls
        actual_ratio = self.inbound_calls / max(1, total_calls)

        return {
            "enabled": self.enabled,
            "total_agents": len(self.agents),
            "available_agents": sum(1 for a in self.agents.values() if a.available),
            "total_blended_calls": self.total_blended_calls,
            "inbound_calls": self.inbound_calls,
            "outbound_calls": self.outbound_calls,
            "actual_blend_ratio": actual_ratio,
            "target_blend_ratio": self.blend_ratio,
            "inbound_queue_size": len(self.inbound_queue),
            "outbound_queue_size": len(self.outbound_queue),
        }


# Global instance
_call_blending = None


def get_call_blending(config=None) -> CallBlending:
    """Get or create call blending instance"""
    global _call_blending
    if _call_blending is None:
        _call_blending = CallBlending(config)
    return _call_blending
