"""
DNS SRV Failover
Automatic server failover using DNS SRV records
"""
from typing import Dict, List, Optional
from datetime import datetime
from pbx.utils.logger import get_logger
import random


class SRVRecord:
    """Represents a DNS SRV record"""
    
    def __init__(self, priority: int, weight: int, port: int, target: str):
        """Initialize SRV record"""
        self.priority = priority
        self.weight = weight
        self.port = port
        self.target = target
        self.available = True
        self.last_check = None
        self.failure_count = 0


class DNSSRVFailover:
    """
    DNS SRV Failover System
    
    Automatic server failover using DNS SRV records (RFC 2782).
    Features:
    - SRV record lookup and parsing
    - Priority-based server selection
    - Weight-based load balancing
    - Automatic failover on server failure
    - Health monitoring
    """
    
    def __init__(self, config=None):
        """Initialize DNS SRV failover"""
        self.logger = get_logger()
        self.config = config or {}
        
        # Configuration
        srv_config = self.config.get('features', {}).get('dns_srv_failover', {})
        self.enabled = srv_config.get('enabled', False)
        self.check_interval = srv_config.get('check_interval', 60)  # seconds
        self.max_failures = srv_config.get('max_failures', 3)
        
        # SRV records cache
        self.srv_cache: Dict[str, List[SRVRecord]] = {}
        
        # Statistics
        self.total_lookups = 0
        self.total_failovers = 0
        self.cache_hits = 0
        
        self.logger.info("DNS SRV failover initialized")
        self.logger.info(f"  Check interval: {self.check_interval}s")
        self.logger.info(f"  Max failures: {self.max_failures}")
        self.logger.info(f"  Enabled: {self.enabled}")
    
    def lookup_srv(self, service: str, protocol: str = 'tcp', 
                   domain: str = None) -> List[Dict]:
        """
        Lookup DNS SRV records
        
        Args:
            service: Service name (e.g., 'sip', 'sips')
            protocol: Protocol (tcp, udp, tls)
            domain: Domain name
            
        Returns:
            List[Dict]: SRV records
        """
        # Construct SRV query
        srv_name = f"_{service}._{protocol}.{domain}"
        
        self.total_lookups += 1
        
        # Check cache first
        if srv_name in self.srv_cache:
            self.cache_hits += 1
            records = self.srv_cache[srv_name]
            self.logger.debug(f"SRV cache hit for {srv_name}")
        else:
            # TODO: Perform actual DNS SRV lookup
            # import dns.resolver
            # answers = dns.resolver.resolve(srv_name, 'SRV')
            
            # Placeholder - in production, parse actual SRV responses
            records = []
            self.logger.info(f"SRV lookup for {srv_name}")
        
        return self._format_srv_records(records)
    
    def _format_srv_records(self, records: List[SRVRecord]) -> List[Dict]:
        """Format SRV records for output"""
        return [
            {
                'priority': record.priority,
                'weight': record.weight,
                'port': record.port,
                'target': record.target,
                'available': record.available
            }
            for record in records
        ]
    
    def select_server(self, service: str, protocol: str = 'tcp',
                     domain: str = None) -> Optional[Dict]:
        """
        Select best available server from SRV records
        
        Args:
            service: Service name
            protocol: Protocol
            domain: Domain
            
        Returns:
            Optional[Dict]: Selected server or None
        """
        srv_name = f"_{service}._{protocol}.{domain}"
        
        if srv_name not in self.srv_cache:
            records = self.lookup_srv(service, protocol, domain)
            if not records:
                return None
        
        records = self.srv_cache.get(srv_name, [])
        
        # Filter available servers
        available = [r for r in records if r.available]
        
        if not available:
            self.logger.error(f"No available servers for {srv_name}")
            return None
        
        # Sort by priority (lower = better)
        available.sort(key=lambda x: x.priority)
        
        # Get servers with highest priority
        best_priority = available[0].priority
        best_servers = [r for r in available if r.priority == best_priority]
        
        # Select by weight (RFC 2782 algorithm)
        selected = self._weighted_selection(best_servers)
        
        self.logger.info(f"Selected server: {selected.target}:{selected.port}")
        
        return {
            'target': selected.target,
            'port': selected.port,
            'priority': selected.priority,
            'weight': selected.weight
        }
    
    def _weighted_selection(self, records: List[SRVRecord]) -> SRVRecord:
        """
        Select server using weighted random selection
        
        Args:
            records: SRV records with same priority
            
        Returns:
            SRVRecord: Selected record
        """
        if len(records) == 1:
            return records[0]
        
        # Calculate total weight
        total_weight = sum(r.weight for r in records)
        
        if total_weight == 0:
            # Equal probability if all weights are 0
            return random.choice(records)
        
        # Weighted random selection
        rand = random.randint(0, total_weight)
        
        cumulative = 0
        for record in records:
            cumulative += record.weight
            if rand <= cumulative:
                return record
        
        return records[-1]
    
    def check_server_health(self, target: str, port: int) -> bool:
        """
        Check if server is healthy
        
        Args:
            target: Server hostname/IP
            port: Server port
            
        Returns:
            bool: Server is healthy
        """
        # TODO: Implement actual health check
        # - TCP connection test
        # - SIP OPTIONS ping
        # - HTTP health endpoint check
        
        self.logger.debug(f"Checking health: {target}:{port}")
        
        # Placeholder
        return True
    
    def mark_server_failed(self, service: str, protocol: str, domain: str,
                          target: str, port: int):
        """
        Mark server as failed
        
        Args:
            service: Service name
            protocol: Protocol
            domain: Domain
            target: Server target
            port: Server port
        """
        srv_name = f"_{service}._{protocol}.{domain}"
        
        if srv_name not in self.srv_cache:
            return
        
        for record in self.srv_cache[srv_name]:
            if record.target == target and record.port == port:
                record.failure_count += 1
                
                if record.failure_count >= self.max_failures:
                    record.available = False
                    self.total_failovers += 1
                    
                    self.logger.warning(f"Server marked as failed: {target}:{port}")
                    self.logger.warning(f"  Failure count: {record.failure_count}")
                    
                    # Trigger failover
                    self._trigger_failover(srv_name)
                
                break
    
    def _trigger_failover(self, srv_name: str):
        """Trigger failover to next available server"""
        self.logger.warning(f"Triggering failover for {srv_name}")
        
        # Select new server
        # This would be called by the application to get new server
        
    def mark_server_recovered(self, service: str, protocol: str, domain: str,
                             target: str, port: int):
        """Mark server as recovered"""
        srv_name = f"_{service}._{protocol}.{domain}"
        
        if srv_name not in self.srv_cache:
            return
        
        for record in self.srv_cache[srv_name]:
            if record.target == target and record.port == port:
                record.failure_count = 0
                record.available = True
                
                self.logger.info(f"Server recovered: {target}:{port}")
                break
    
    def clear_cache(self, service: str = None, protocol: str = None, 
                    domain: str = None):
        """Clear SRV cache"""
        if service and protocol and domain:
            srv_name = f"_{service}._{protocol}.{domain}"
            if srv_name in self.srv_cache:
                del self.srv_cache[srv_name]
                self.logger.info(f"Cleared cache for {srv_name}")
        else:
            self.srv_cache.clear()
            self.logger.info("Cleared entire SRV cache")
    
    def get_statistics(self) -> Dict:
        """Get DNS SRV failover statistics"""
        cache_hit_rate = self.cache_hits / max(1, self.total_lookups)
        
        return {
            'enabled': self.enabled,
            'total_lookups': self.total_lookups,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': cache_hit_rate,
            'total_failovers': self.total_failovers,
            'cached_services': len(self.srv_cache)
        }


# Global instance
_dns_srv_failover = None


def get_dns_srv_failover(config=None) -> DNSSRVFailover:
    """Get or create DNS SRV failover instance"""
    global _dns_srv_failover
    if _dns_srv_failover is None:
        _dns_srv_failover = DNSSRVFailover(config)
    return _dns_srv_failover
