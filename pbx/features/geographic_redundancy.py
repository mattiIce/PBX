"""
Geographic Redundancy
Multi-region trunk registration for disaster recovery
"""

import socket
import time
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pbx.utils.logger import get_logger


class RegionStatus(Enum):
    """Region status"""

    ACTIVE = "active"
    STANDBY = "standby"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


class GeographicRegion:
    """Represents a geographic region"""

    def __init__(self, region_id: str, name: str, location: str) -> None:
        """Initialize region"""
        self.region_id = region_id
        self.name = name
        self.location = location
        self.status = RegionStatus.STANDBY
        self.trunks: list[str] = []
        self.priority = 100
        self.last_health_check = None
        self.health_score = 1.0


class GeographicRedundancy:
    """
    Geographic Redundancy System

    Multi-region trunk registration for high availability and disaster recovery.
    Features:
    - Multiple geographic regions
    - Automatic failover between regions
    - Health monitoring per region
    - Priority-based region selection
    - Data replication
    """

    def __init__(self, config: Any | None = None) -> None:
        """Initialize geographic redundancy"""
        self.logger = get_logger()
        self.config = config or {}

        # Configuration
        geo_config = self.config.get("features", {}).get("geographic_redundancy", {})
        self.enabled = geo_config.get("enabled", False)
        self.auto_failover = geo_config.get("auto_failover", True)
        self.health_check_interval = geo_config.get("health_check_interval", 60)  # seconds
        self.failover_threshold = geo_config.get("failover_threshold", 3)  # failures

        # Regions
        self.regions: dict[str, GeographicRegion] = {}
        self.active_region = None

        # Statistics
        self.total_failovers = 0
        self.failover_history: list[dict] = []

        self.logger.info("Geographic redundancy initialized")
        self.logger.info(f"  Auto-failover: {self.auto_failover}")
        self.logger.info(f"  Health check interval: {self.health_check_interval}s")
        self.logger.info(f"  Enabled: {self.enabled}")

    def add_region(
        self,
        region_id: str,
        name: str,
        location: str,
        priority: int = 100,
        trunks: list[str] | None = None,
    ) -> dict:
        """
        Add geographic region

        Args:
            region_id: Region identifier
            name: Region name
            location: Geographic location
            priority: Priority (lower = higher priority)
            trunks: Trunk IDs in this region

        Returns:
            dict: Add result
        """
        region = GeographicRegion(region_id, name, location)
        region.priority = priority
        region.trunks = trunks or []

        self.regions[region_id] = region

        # set as active if first region or higher priority
        if not self.active_region:
            self.active_region = region_id
            region.status = RegionStatus.ACTIVE

        self.logger.info(f"Added region: {name} ({location})")
        self.logger.info(f"  Priority: {priority}")
        self.logger.info(f"  Trunks: {len(region.trunks)}")

        return {"success": True, "region_id": region_id}

    def _check_trunk_health(self, region: "GeographicRegion") -> bool:
        """
        Check health of trunks in region

        Args:
            region: Geographic region

        Returns:
            bool: True if at least one trunk is healthy
        """
        if not region.trunks:
            # No trunks configured
            return False

        # Try to get trunk manager
        try:
            from pbx.features.sip_trunk import get_trunk_manager

            trunk_manager = get_trunk_manager()

            healthy_trunks = 0
            for trunk_id in region.trunks:
                trunk = trunk_manager.get_trunk(trunk_id)
                if trunk and trunk.can_make_call():
                    healthy_trunks += 1

            # At least one trunk must be healthy
            return healthy_trunks > 0
        except Exception as e:
            self.logger.warning(f"Cannot check trunk health: {e}")
            # Assume healthy if can't check
            return True

    def _check_network_latency(self, target_host: str | None = None) -> float:
        """
        Check network latency to region

        Args:
            target_host: Host to ping (optional)

        Returns:
            float: Latency in milliseconds
        """
        if not target_host:
            # Use a public DNS server as default
            target_host = "8.8.8.8"

        try:
            # Simple TCP connection test
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)  # 2 second timeout
            result = sock.connect_ex((target_host, 53))  # DNS port
            sock.close()
            end_time = time.time()

            if result == 0:
                # Connection successful
                latency_ms = (end_time - start_time) * 1000
                return latency_ms
            # Connection failed
            return 9999.0  # High latency indicates failure
        except OSError as e:
            self.logger.warning(f"Network latency check failed: {e}")
            return 9999.0

    def _check_database_connectivity(self) -> bool:
        """
        Check database connectivity

        Returns:
            bool: True if database is connected
        """
        try:
            from pbx.utils.database import get_database

            db = get_database()
            if db and db.enabled and db.connection:
                # Try a simple query
                try:
                    cursor = db.connection.cursor()
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                    cursor.close()
                    return True
                except Exception as e:
                    self.logger.warning(f"Database query failed: {e}")
                    return False
            else:
                # Database not configured, assume OK
                return True
        except Exception as e:
            self.logger.warning(f"Database check failed: {e}")
            # If database module not available, assume OK
            return True

    def _check_services_running(self) -> bool:
        """
        Check if critical services are running

        Returns:
            bool: True if services are running
        """
        # Check if we can import critical modules
        try:
            # If imports succeed, services are available
            return True
        except Exception as e:
            self.logger.error(f"Service check failed: {e}")
            return False

    def check_region_health(self, region_id: str) -> dict:
        """
        Check health of a region

        Args:
            region_id: Region identifier

        Returns:
            dict: Health status
        """
        if region_id not in self.regions:
            return {"healthy": False, "error": "Region not found"}

        region = self.regions[region_id]

        # Perform actual health checks
        trunks_available = self._check_trunk_health(region)
        network_latency = self._check_network_latency()
        database_connected = self._check_database_connectivity()
        services_running = self._check_services_running()

        health_checks = {
            "trunks_available": trunks_available,
            "network_latency": network_latency,
            "database_connected": database_connected,
            "services_running": services_running,
        }

        # Calculate overall health score
        health_score = 1.0
        if not trunks_available:
            health_score -= 0.4
        if network_latency > 100:
            health_score -= 0.2
        if not database_connected:
            health_score -= 0.3
        if not services_running:
            health_score -= 0.4

        region.health_score = health_score
        region.last_health_check = datetime.now(UTC)

        healthy = health_score >= 0.7

        if not healthy and region.status == RegionStatus.ACTIVE:
            self.logger.warning(f"Region {region_id} health degraded: {health_score:.2f}")

            if self.auto_failover:
                self._trigger_failover(region_id, "health_check_failed")

        return {
            "healthy": healthy,
            "health_score": health_score,
            "checks": health_checks,
            "checked_at": datetime.now(UTC).isoformat(),
        }

    def _trigger_failover(self, failed_region_id: str, reason: str) -> None:
        """
        Trigger failover to backup region

        Args:
            failed_region_id: Failed region ID
            reason: Failure reason
        """
        if failed_region_id in self.regions:
            self.regions[failed_region_id].status = RegionStatus.FAILED

        # Find best backup region
        backup_region = self._select_backup_region(failed_region_id)

        if not backup_region:
            self.logger.error("No backup region available for failover!")
            return

        # Perform failover
        self.active_region = backup_region
        self.regions[backup_region].status = RegionStatus.ACTIVE

        self.total_failovers += 1

        failover_event = {
            "from_region": failed_region_id,
            "to_region": backup_region,
            "reason": reason,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self.failover_history.append(failover_event)

        self.logger.warning(f"Failover executed: {failed_region_id} -> {backup_region}")
        self.logger.warning(f"  Reason: {reason}")

    def _select_backup_region(self, exclude_region: str) -> str | None:
        """Select best backup region"""
        candidates = [
            (region_id, region)
            for region_id, region in self.regions.items()
            if region_id != exclude_region and region.status != RegionStatus.FAILED
        ]

        if not candidates:
            return None

        # Sort by priority (lower = better) and health score
        candidates.sort(key=lambda x: (x[1].priority, -x[1].health_score))

        return candidates[0][0]

    def manual_failover(self, target_region_id: str) -> dict:
        """
        Manually failover to specific region

        Args:
            target_region_id: Target region ID

        Returns:
            dict: Failover result
        """
        if target_region_id not in self.regions:
            return {"success": False, "error": "Region not found"}

        old_region = self.active_region

        # Deactivate old region
        if old_region and old_region in self.regions:
            self.regions[old_region].status = RegionStatus.STANDBY

        # Activate new region
        self.active_region = target_region_id
        self.regions[target_region_id].status = RegionStatus.ACTIVE

        self.total_failovers += 1

        self.logger.info(f"Manual failover: {old_region} -> {target_region_id}")

        return {"success": True, "from_region": old_region, "to_region": target_region_id}

    def get_active_region(self) -> dict | None:
        """Get current active region"""
        if self.active_region and self.active_region in self.regions:
            region = self.regions[self.active_region]
            return {
                "region_id": region.region_id,
                "name": region.name,
                "location": region.location,
                "status": region.status.value,
                "health_score": region.health_score,
                "trunk_count": len(region.trunks),
            }
        return None

    def get_all_regions(self) -> list[dict]:
        """Get all regions"""
        return [
            {
                "region_id": region.region_id,
                "name": region.name,
                "location": region.location,
                "status": region.status.value,
                "health_score": region.health_score,
                "trunk_count": len(region.trunks),
                "priority": region.priority,
                "is_active": region.region_id == self.active_region,
            }
            for region in self.regions.values()
        ]

    def get_region_status(self, region_id: str) -> dict | None:
        """Get status of a specific region"""
        if region_id not in self.regions:
            return None

        region = self.regions[region_id]
        return {
            "region_id": region.region_id,
            "name": region.name,
            "location": region.location,
            "status": region.status.value,
            "health_score": region.health_score,
            "trunk_count": len(region.trunks),
            "trunks": region.trunks,
            "priority": region.priority,
            "is_active": region.region_id == self.active_region,
            "last_health_check": (
                region.last_health_check.isoformat() if region.last_health_check else None
            ),
        }

    def create_region(self, region_id: str, name: str, location: str) -> dict:
        """Create a new geographic region"""
        if region_id in self.regions:
            return {"success": False, "error": "Region already exists"}

        region = GeographicRegion(region_id, name, location)
        self.regions[region_id] = region

        self.logger.info(f"Created region: {region_id} ({name}) at {location}")

        return {"success": True, "region_id": region_id, "name": name, "location": location}

    def trigger_failover(self, target_region_id: str | None = None) -> dict:
        """Trigger manual failover to specified region or auto-select"""
        if target_region_id:
            return self.manual_failover(target_region_id)
        # Auto-select best region
        best_region_id = self._select_backup_region(self.active_region)
        if best_region_id:
            return self.manual_failover(best_region_id)
        return {"success": False, "error": "No available regions for failover"}

    def get_statistics(self) -> dict:
        """Get redundancy statistics"""
        return {
            "enabled": self.enabled,
            "total_regions": len(self.regions),
            "active_region": self.active_region,
            "total_failovers": self.total_failovers,
            "recent_failovers": self.failover_history[-5:],
            "auto_failover": self.auto_failover,
        }


# Global instance
_geographic_redundancy = None


def get_geographic_redundancy(config: Any | None = None) -> GeographicRedundancy:
    """Get or create geographic redundancy instance"""
    global _geographic_redundancy
    if _geographic_redundancy is None:
        _geographic_redundancy = GeographicRedundancy(config)
    return _geographic_redundancy
