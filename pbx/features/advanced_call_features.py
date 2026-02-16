"""
Advanced Call Features
Call whisper, barge-in, and supervisor monitoring
"""

from datetime import UTC, datetime
from typing import Any

from pbx.utils.logger import get_logger


class AdvancedCallFeatures:
    """Advanced call features for supervisor monitoring and intervention"""

    def __init__(self, config: Any | None = None) -> None:
        """Initialize advanced call features"""
        self.logger = get_logger()
        self.config = config or {}
        self.enabled = (
            self.config.get("features", {}).get("advanced_call_features", {}).get("enabled", False)
        )

        # Track monitored calls
        self.monitored_calls = {}  # call_id -> monitoring info
        self.supervisor_permissions = {}  # supervisor_id -> set of allowed extensions

        if self.enabled:
            self.logger.info("Advanced call features initialized")
            self._load_supervisor_permissions()

    def _load_supervisor_permissions(self) -> None:
        """Load supervisor monitoring permissions from config"""
        perms = (
            self.config.get("features", {}).get("advanced_call_features", {}).get("supervisors", [])
        )
        for perm in perms:
            self.supervisor_permissions[perm["supervisor_id"]] = set(
                perm.get("monitored_extensions", [])
            )

    def can_monitor(self, supervisor_id: str, extension: str) -> bool:
        """Check if supervisor can monitor an extension"""
        if supervisor_id not in self.supervisor_permissions:
            return False

        perms = self.supervisor_permissions[supervisor_id]
        # '*' means can monitor all
        return "*" in perms or extension in perms

    def start_whisper(self, call_id: str, supervisor_id: str, agent_extension: str) -> dict:
        """
        Start whisper mode (supervisor can speak to agent only, customer can't hear)

        Args:
            call_id: Call identifier
            supervisor_id: Supervisor starting whisper
            agent_extension: Agent being whispered to

        Returns:
            Whisper session information
        """
        if not self.enabled:
            return {"error": "Advanced call features not enabled"}

        if not self.can_monitor(supervisor_id, agent_extension):
            return {"error": "Permission denied"}

        self.monitored_calls[call_id] = {
            "mode": "whisper",
            "supervisor_id": supervisor_id,
            "agent_extension": agent_extension,
            "started_at": datetime.now(UTC),
            "audio_mode": "supervisor_to_agent_only",
        }

        self.logger.info(
            f"Supervisor {supervisor_id} started whisper on call {call_id} with {agent_extension}"
        )

        return {"call_id": call_id, "mode": "whisper", "status": "active"}

    def start_barge_in(self, call_id: str, supervisor_id: str, agent_extension: str) -> dict:
        """
        Start barge-in mode (supervisor joins call, all parties can hear)

        Args:
            call_id: Call identifier
            supervisor_id: Supervisor barging in
            agent_extension: Agent whose call is being barged

        Returns:
            Barge-in session information
        """
        if not self.enabled:
            return {"error": "Advanced call features not enabled"}

        if not self.can_monitor(supervisor_id, agent_extension):
            return {"error": "Permission denied"}

        self.monitored_calls[call_id] = {
            "mode": "barge",
            "supervisor_id": supervisor_id,
            "agent_extension": agent_extension,
            "started_at": datetime.now(UTC),
            "audio_mode": "three_way_conference",
        }

        self.logger.info(
            f"Supervisor {supervisor_id} barged into call {call_id} with {agent_extension}"
        )

        return {"call_id": call_id, "mode": "barge", "status": "active"}

    def start_monitor(self, call_id: str, supervisor_id: str, agent_extension: str) -> dict:
        """
        Start silent monitoring (supervisor can hear both parties, neither can hear supervisor)

        Args:
            call_id: Call identifier
            supervisor_id: Supervisor monitoring
            agent_extension: Agent being monitored

        Returns:
            Monitoring session information
        """
        if not self.enabled:
            return {"error": "Advanced call features not enabled"}

        if not self.can_monitor(supervisor_id, agent_extension):
            return {"error": "Permission denied"}

        self.monitored_calls[call_id] = {
            "mode": "monitor",
            "supervisor_id": supervisor_id,
            "agent_extension": agent_extension,
            "started_at": datetime.now(UTC),
            "audio_mode": "supervisor_listen_only",
        }

        self.logger.info(
            f"Supervisor {supervisor_id} started monitoring call {call_id} with {agent_extension}"
        )

        return {"call_id": call_id, "mode": "monitor", "status": "active"}

    def stop_monitoring(self, call_id: str) -> bool:
        """Stop monitoring/whisper/barge on a call"""
        if call_id in self.monitored_calls:
            info = self.monitored_calls[call_id]
            self.logger.info(f"Stopped {info['mode']} on call {call_id}")
            del self.monitored_calls[call_id]
            return True
        return False

    def get_monitoring_info(self, call_id: str) -> dict | None:
        """Get monitoring information for a call"""
        return self.monitored_calls.get(call_id)

    def list_monitored_calls(self, supervisor_id: str | None = None) -> list[dict]:
        """list all monitored calls, optionally filtered by supervisor"""
        calls = []
        for call_id, info in self.monitored_calls.items():
            if supervisor_id is None or info["supervisor_id"] == supervisor_id:
                calls.append(
                    {
                        "call_id": call_id,
                        "mode": info["mode"],
                        "supervisor_id": info["supervisor_id"],
                        "agent_extension": info["agent_extension"],
                        "duration": (datetime.now(UTC) - info["started_at"]).total_seconds(),
                    }
                )
        return calls

    def add_supervisor_permission(self, supervisor_id: str, extensions: list[str]) -> bool:
        """Add monitoring permissions for a supervisor"""
        if not self.enabled:
            self.logger.error(
                f"Cannot add supervisor permission for {supervisor_id}: Advanced call features not enabled"
            )
            return False

        if supervisor_id not in self.supervisor_permissions:
            self.supervisor_permissions[supervisor_id] = set()
        self.supervisor_permissions[supervisor_id].update(extensions)
        self.logger.info(f"Added monitoring permissions for {supervisor_id}: {extensions}")
        return True

    def remove_supervisor_permission(self, supervisor_id: str, extensions: list[str]) -> bool:
        """Remove monitoring permissions for a supervisor"""
        if not self.enabled:
            self.logger.error(
                f"Cannot remove supervisor permission for {supervisor_id}: Advanced call features not enabled"
            )
            return False

        if supervisor_id in self.supervisor_permissions:
            self.supervisor_permissions[supervisor_id].difference_update(extensions)
            self.logger.info(f"Removed monitoring permissions for {supervisor_id}: {extensions}")
            return True
        return False

    def get_statistics(self) -> dict:
        """Get advanced call features statistics"""
        mode_counts = {}
        for info in self.monitored_calls.values():
            mode = info["mode"]
            mode_counts[mode] = mode_counts.get(mode, 0) + 1

        return {
            "enabled": self.enabled,
            "active_monitoring_sessions": len(self.monitored_calls),
            "supervisors": len(self.supervisor_permissions),
            "mode_breakdown": mode_counts,
        }
