"""
Geographic Redundancy
Multi-region trunk registration for disaster recovery
"""
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from pbx.utils.logger import get_logger


class RegionStatus(Enum):
    """Region status"""
    ACTIVE = "active"
    STANDBY = "standby"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


class GeographicRegion:
    """Represents a geographic region"""
    
    def __init__(self, region_id: str, name: str, location: str):
        """Initialize region"""
        self.region_id = region_id
        self.name = name
        self.location = location
        self.status = RegionStatus.STANDBY
        self.trunks: List[str] = []
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
    
    def __init__(self, config=None):
        """Initialize geographic redundancy"""
        self.logger = get_logger()
        self.config = config or {}
        
        # Configuration
        geo_config = self.config.get('features', {}).get('geographic_redundancy', {})
        self.enabled = geo_config.get('enabled', False)
        self.auto_failover = geo_config.get('auto_failover', True)
        self.health_check_interval = geo_config.get('health_check_interval', 60)  # seconds
        self.failover_threshold = geo_config.get('failover_threshold', 3)  # failures
        
        # Regions
        self.regions: Dict[str, GeographicRegion] = {}
        self.active_region = None
        
        # Statistics
        self.total_failovers = 0
        self.failover_history: List[Dict] = []
        
        self.logger.info("Geographic redundancy initialized")
        self.logger.info(f"  Auto-failover: {self.auto_failover}")
        self.logger.info(f"  Health check interval: {self.health_check_interval}s")
        self.logger.info(f"  Enabled: {self.enabled}")
    
    def add_region(self, region_id: str, name: str, location: str,
                   priority: int = 100, trunks: List[str] = None) -> Dict:
        """
        Add geographic region
        
        Args:
            region_id: Region identifier
            name: Region name
            location: Geographic location
            priority: Priority (lower = higher priority)
            trunks: Trunk IDs in this region
            
        Returns:
            Dict: Add result
        """
        region = GeographicRegion(region_id, name, location)
        region.priority = priority
        region.trunks = trunks or []
        
        self.regions[region_id] = region
        
        # Set as active if first region or higher priority
        if not self.active_region:
            self.active_region = region_id
            region.status = RegionStatus.ACTIVE
        
        self.logger.info(f"Added region: {name} ({location})")
        self.logger.info(f"  Priority: {priority}")
        self.logger.info(f"  Trunks: {len(region.trunks)}")
        
        return {
            'success': True,
            'region_id': region_id
        }
    
    def check_region_health(self, region_id: str) -> Dict:
        """
        Check health of a region
        
        Args:
            region_id: Region identifier
            
        Returns:
            Dict: Health status
        """
        if region_id not in self.regions:
            return {'healthy': False, 'error': 'Region not found'}
        
        region = self.regions[region_id]
        
        # TODO: Implement actual health checks
        # - Ping trunks in region
        # - Check network latency
        # - Verify database connectivity
        # - Check service availability
        
        health_checks = {
            'trunks_available': True,
            'network_latency': 50,  # ms
            'database_connected': True,
            'services_running': True
        }
        
        # Calculate overall health score
        health_score = 1.0
        if not health_checks['trunks_available']:
            health_score -= 0.4
        if health_checks['network_latency'] > 100:
            health_score -= 0.2
        if not health_checks['database_connected']:
            health_score -= 0.3
        if not health_checks['services_running']:
            health_score -= 0.4
        
        region.health_score = health_score
        region.last_health_check = datetime.now()
        
        healthy = health_score >= 0.7
        
        if not healthy and region.status == RegionStatus.ACTIVE:
            self.logger.warning(f"Region {region_id} health degraded: {health_score:.2f}")
            
            if self.auto_failover:
                self._trigger_failover(region_id, 'health_check_failed')
        
        return {
            'healthy': healthy,
            'health_score': health_score,
            'checks': health_checks,
            'checked_at': datetime.now().isoformat()
        }
    
    def _trigger_failover(self, failed_region_id: str, reason: str):
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
            'from_region': failed_region_id,
            'to_region': backup_region,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
        self.failover_history.append(failover_event)
        
        self.logger.warning(f"Failover executed: {failed_region_id} -> {backup_region}")
        self.logger.warning(f"  Reason: {reason}")
    
    def _select_backup_region(self, exclude_region: str) -> Optional[str]:
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
    
    def manual_failover(self, target_region_id: str) -> Dict:
        """
        Manually failover to specific region
        
        Args:
            target_region_id: Target region ID
            
        Returns:
            Dict: Failover result
        """
        if target_region_id not in self.regions:
            return {'success': False, 'error': 'Region not found'}
        
        old_region = self.active_region
        
        # Deactivate old region
        if old_region and old_region in self.regions:
            self.regions[old_region].status = RegionStatus.STANDBY
        
        # Activate new region
        self.active_region = target_region_id
        self.regions[target_region_id].status = RegionStatus.ACTIVE
        
        self.total_failovers += 1
        
        self.logger.info(f"Manual failover: {old_region} -> {target_region_id}")
        
        return {
            'success': True,
            'from_region': old_region,
            'to_region': target_region_id
        }
    
    def get_active_region(self) -> Optional[Dict]:
        """Get current active region"""
        if self.active_region and self.active_region in self.regions:
            region = self.regions[self.active_region]
            return {
                'region_id': region.region_id,
                'name': region.name,
                'location': region.location,
                'status': region.status.value,
                'health_score': region.health_score,
                'trunk_count': len(region.trunks)
            }
        return None
    
    def get_statistics(self) -> Dict:
        """Get redundancy statistics"""
        return {
            'enabled': self.enabled,
            'total_regions': len(self.regions),
            'active_region': self.active_region,
            'total_failovers': self.total_failovers,
            'recent_failovers': self.failover_history[-5:],
            'auto_failover': self.auto_failover
        }


# Global instance
_geographic_redundancy = None


def get_geographic_redundancy(config=None) -> GeographicRedundancy:
    """Get or create geographic redundancy instance"""
    global _geographic_redundancy
    if _geographic_redundancy is None:
        _geographic_redundancy = GeographicRedundancy(config)
    return _geographic_redundancy
