"""
RTCP Statistics and Monitoring
Based on Asterisk RTCP implementation

Collects and analyzes Real-Time Control Protocol statistics for
call quality monitoring and troubleshooting.
"""
import time
import math
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pbx.utils.logger import get_logger


@dataclass
class RTCPStats:
    """RTCP statistics for a call"""
    # Sender statistics
    packets_sent: int = 0
    bytes_sent: int = 0
    
    # Receiver statistics
    packets_received: int = 0
    packets_lost: int = 0
    packets_expected: int = 0
    bytes_received: int = 0
    
    # Jitter (in milliseconds)
    jitter_ms: float = 0.0
    
    # Round-trip time (in milliseconds)
    rtt_ms: float = 0.0
    
    # Quality metrics
    packet_loss_percent: float = 0.0
    mos_score: float = 0.0  # Mean Opinion Score estimate
    
    # Timestamps
    first_packet_time: Optional[float] = None
    last_packet_time: Optional[float] = None
    
    # Sequence tracking
    highest_sequence: int = 0
    sequence_cycles: int = 0
    last_sequence: Optional[int] = None
    
    # Timing
    last_sr_timestamp: int = 0  # Last Sender Report timestamp
    last_sr_time: float = 0.0   # When we received last SR


class RTCPMonitor:
    """
    RTCP statistics collection and monitoring
    
    Tracks call quality metrics for real-time monitoring and
    historical analysis. Based on Asterisk RTCP implementation.
    
    Features:
    - Packet loss detection and percentage
    - Jitter calculation (RFC 3550)
    - Round-trip time measurement
    - MOS score estimation
    - Quality thresholds and alerting
    """
    
    def __init__(self, call_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize RTCP monitor
        
        Args:
            call_id: Unique call identifier
            config: Configuration dictionary with:
                - interval_seconds: RTCP report interval (default: 5)
                - alert_thresholds: Quality alert thresholds
        """
        self.logger = get_logger()
        self.call_id = call_id
        self.config = config or {}
        
        # Statistics
        self.stats = RTCPStats()
        
        # Configuration
        self.interval_seconds = self.config.get('interval_seconds', 5)
        self.alert_thresholds = self.config.get('alert_thresholds', {
            'packet_loss_percent': 5.0,
            'jitter_ms': 50.0,
            'mos_min': 3.5,
            'rtt_ms': 300.0
        })
        
        # Internal tracking
        self.transit_time = None
        self.last_arrival_time = None
        
        self.logger.info(f"RTCP monitor initialized for call {call_id}")
    
    def update_sent_packet(self, size: int):
        """
        Update statistics for sent packet
        
        Args:
            size: Packet size in bytes
        """
        self.stats.packets_sent += 1
        self.stats.bytes_sent += size
    
    def update_received_packet(self, sequence: int, timestamp: int, size: int):
        """
        Update statistics for received packet
        
        Args:
            sequence: RTP sequence number
            timestamp: RTP timestamp
            size: Packet size in bytes
        """
        arrival_time = time.time()
        
        # Update basic counts
        self.stats.packets_received += 1
        self.stats.bytes_received += size
        
        # Track timing
        if self.stats.first_packet_time is None:
            self.stats.first_packet_time = arrival_time
        self.stats.last_packet_time = arrival_time
        
        # Handle sequence numbers
        self._update_sequence(sequence)
        
        # Calculate jitter (RFC 3550)
        self._calculate_jitter(timestamp, arrival_time)
        
        # Calculate packet loss
        self._calculate_packet_loss()
        
        # Estimate MOS score
        self._estimate_mos()
    
    def update_lost_packet(self):
        """Update statistics for lost packet"""
        self.stats.packets_lost += 1
        self._calculate_packet_loss()
        self._estimate_mos()
    
    def update_rtt(self, rtt_ms: float):
        """
        Update round-trip time
        
        Args:
            rtt_ms: Round-trip time in milliseconds
        """
        self.stats.rtt_ms = rtt_ms
        self._estimate_mos()
    
    def _update_sequence(self, sequence: int):
        """Track sequence numbers and detect cycles"""
        if self.stats.last_sequence is None:
            self.stats.last_sequence = sequence
            self.stats.highest_sequence = sequence
            return
        
        # Handle sequence wraparound
        seq_diff = sequence - self.stats.last_sequence
        
        if seq_diff > 32768:
            # Negative wraparound
            seq_diff -= 65536
        elif seq_diff < -32768:
            # Positive wraparound
            seq_diff += 65536
            self.stats.sequence_cycles += 1
        
        # Update highest sequence seen
        if seq_diff > 0:
            self.stats.highest_sequence = sequence
        
        # Calculate expected packets
        extended_max = self.stats.sequence_cycles * 65536 + self.stats.highest_sequence
        if self.stats.last_sequence is not None:
            extended_base = self.stats.sequence_cycles * 65536 + self.stats.last_sequence
            self.stats.packets_expected = extended_max - extended_base + 1
        
        self.stats.last_sequence = sequence
    
    def _calculate_jitter(self, timestamp: int, arrival_time: float):
        """
        Calculate inter-arrival jitter (RFC 3550)
        
        Args:
            timestamp: RTP timestamp
            arrival_time: Packet arrival time
        """
        if self.last_arrival_time is None:
            self.last_arrival_time = arrival_time
            self.transit_time = arrival_time - (timestamp / 8000.0)
            return
        
        # Calculate transit time
        transit = arrival_time - (timestamp / 8000.0)
        
        # Calculate transit time difference
        d = abs(transit - self.transit_time)
        
        # Update jitter estimate (RFC 3550 algorithm)
        # J(i) = J(i-1) + (|D(i-1,i)| - J(i-1))/16
        jitter_seconds = self.stats.jitter_ms / 1000.0
        jitter_seconds += (d - jitter_seconds) / 16.0
        self.stats.jitter_ms = jitter_seconds * 1000.0
        
        # Update for next calculation
        self.transit_time = transit
        self.last_arrival_time = arrival_time
    
    def _calculate_packet_loss(self):
        """Calculate packet loss percentage"""
        if self.stats.packets_expected > 0:
            self.stats.packet_loss_percent = (
                (self.stats.packets_lost / self.stats.packets_expected) * 100.0
            )
        else:
            self.stats.packet_loss_percent = 0.0
    
    def _estimate_mos(self):
        """
        Estimate MOS (Mean Opinion Score) using E-model
        
        Simplified E-model calculation based on:
        - Packet loss percentage
        - Jitter
        - Round-trip time (delay)
        
        MOS scale: 1.0 (bad) to 5.0 (excellent)
        """
        # Start with baseline R-factor (quality rating)
        r_factor = 93.2
        
        # Subtract impairments
        
        # Delay impairment (Id)
        # Based on ITU-T G.107
        delay_ms = self.stats.rtt_ms / 2  # One-way delay
        if delay_ms > 177.3:
            id_delay = 0.024 * delay_ms + 0.11 * (delay_ms - 177.3)
        else:
            id_delay = 0.024 * delay_ms
        
        r_factor -= id_delay
        
        # Packet loss impairment (Ie-eff)
        # Simplified calculation
        loss_percent = self.stats.packet_loss_percent
        ie_eff = 0
        
        if loss_percent > 0:
            # G.711 has Ie value of 0, but packet loss affects it
            # Use simplified formula
            ie_eff = 10 + 10 * math.log10(1 + 15 * loss_percent)
        
        r_factor -= ie_eff
        
        # Jitter doesn't directly affect R-factor in E-model,
        # but high jitter indicates network issues
        # Add small penalty for high jitter
        if self.stats.jitter_ms > 30:
            r_factor -= (self.stats.jitter_ms - 30) * 0.1
        
        # Convert R-factor to MOS
        # ITU-T G.107 formula
        if r_factor < 0:
            mos = 1.0
        elif r_factor > 100:
            mos = 4.5
        else:
            mos = 1 + 0.035 * r_factor + 7e-6 * r_factor * (r_factor - 60) * (100 - r_factor)
        
        # Clamp to 1.0 - 5.0 range
        self.stats.mos_score = max(1.0, min(5.0, mos))
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current RTCP statistics
        
        Returns:
            dict: Complete statistics
        """
        call_duration = 0.0
        if self.stats.first_packet_time and self.stats.last_packet_time:
            call_duration = self.stats.last_packet_time - self.stats.first_packet_time
        
        return {
            'call_id': self.call_id,
            'packets_sent': self.stats.packets_sent,
            'packets_received': self.stats.packets_received,
            'packets_lost': self.stats.packets_lost,
            'packets_expected': self.stats.packets_expected,
            'bytes_sent': self.stats.bytes_sent,
            'bytes_received': self.stats.bytes_received,
            'packet_loss_percent': round(self.stats.packet_loss_percent, 2),
            'jitter_ms': round(self.stats.jitter_ms, 2),
            'rtt_ms': round(self.stats.rtt_ms, 2),
            'mos_score': round(self.stats.mos_score, 2),
            'call_duration_seconds': round(call_duration, 2),
            'quality_rating': self._get_quality_rating()
        }
    
    def _get_quality_rating(self) -> str:
        """
        Get quality rating based on MOS score
        
        Returns:
            str: Quality rating (Excellent, Good, Fair, Poor, Bad)
        """
        mos = self.stats.mos_score
        
        if mos >= 4.3:
            return 'Excellent'
        elif mos >= 4.0:
            return 'Good'
        elif mos >= 3.6:
            return 'Fair'
        elif mos >= 3.1:
            return 'Poor'
        else:
            return 'Bad'
    
    def check_quality_alerts(self) -> List[str]:
        """
        Check if any quality thresholds are exceeded
        
        Returns:
            list: Alert messages
        """
        alerts = []
        
        # Check packet loss
        if self.stats.packet_loss_percent > self.alert_thresholds['packet_loss_percent']:
            alerts.append(
                f"High packet loss: {self.stats.packet_loss_percent:.1f}% "
                f"(threshold: {self.alert_thresholds['packet_loss_percent']}%)"
            )
        
        # Check jitter
        if self.stats.jitter_ms > self.alert_thresholds['jitter_ms']:
            alerts.append(
                f"High jitter: {self.stats.jitter_ms:.1f}ms "
                f"(threshold: {self.alert_thresholds['jitter_ms']}ms)"
            )
        
        # Check MOS
        if self.stats.mos_score < self.alert_thresholds['mos_min']:
            alerts.append(
                f"Low MOS score: {self.stats.mos_score:.2f} "
                f"(threshold: {self.alert_thresholds['mos_min']})"
            )
        
        # Check RTT
        if self.stats.rtt_ms > self.alert_thresholds['rtt_ms']:
            alerts.append(
                f"High latency: {self.stats.rtt_ms:.1f}ms "
                f"(threshold: {self.alert_thresholds['rtt_ms']}ms)"
            )
        
        return alerts
    
    def reset(self):
        """Reset statistics"""
        self.stats = RTCPStats()
        self.transit_time = None
        self.last_arrival_time = None
        
        self.logger.info(f"RTCP statistics reset for call {self.call_id}")


class RTCPMonitorManager:
    """
    Manager for RTCP monitors (one per call)
    """
    
    def __init__(self, pbx):
        """
        Initialize RTCP monitor manager
        
        Args:
            pbx: PBX instance
        """
        self.pbx = pbx
        self.logger = get_logger()
        self.monitors: Dict[str, RTCPMonitor] = {}
        
        # Get global config
        self.config = {}
        if hasattr(pbx, 'config') and pbx.config:
            self.config = pbx.config.get('rtcp', {})
        
        self.logger.info("RTCP monitor manager initialized")
    
    def create_monitor(self, call_id: str, config: Optional[Dict[str, Any]] = None) -> RTCPMonitor:
        """
        Create RTCP monitor for a call
        
        Args:
            call_id: Unique call identifier
            config: Optional monitor configuration
        
        Returns:
            RTCPMonitor instance
        """
        monitor_config = config or self.config
        monitor = RTCPMonitor(call_id, monitor_config)
        self.monitors[call_id] = monitor
        
        self.logger.debug(f"Created RTCP monitor for call {call_id}")
        return monitor
    
    def get_monitor(self, call_id: str) -> Optional[RTCPMonitor]:
        """Get monitor for a call"""
        return self.monitors.get(call_id)
    
    def remove_monitor(self, call_id: str):
        """Remove monitor for a call"""
        if call_id in self.monitors:
            del self.monitors[call_id]
            self.logger.debug(f"Removed RTCP monitor for call {call_id}")
    
    def get_all_statistics(self) -> List[Dict[str, Any]]:
        """Get statistics for all monitored calls"""
        return [
            monitor.get_statistics()
            for monitor in self.monitors.values()
        ]
    
    def get_active_calls_count(self) -> int:
        """Get number of active monitored calls"""
        return len(self.monitors)
    
    def get_quality_summary(self) -> Dict[str, Any]:
        """
        Get summary of call quality across all calls
        
        Returns:
            dict: Aggregated quality metrics
        """
        if not self.monitors:
            return {
                'active_calls': 0,
                'average_mos': 0.0,
                'average_packet_loss': 0.0,
                'average_jitter_ms': 0.0,
                'calls_with_issues': 0
            }
        
        total_mos = 0.0
        total_loss = 0.0
        total_jitter = 0.0
        calls_with_issues = 0
        
        for monitor in self.monitors.values():
            stats = monitor.stats
            total_mos += stats.mos_score
            total_loss += stats.packet_loss_percent
            total_jitter += stats.jitter_ms
            
            if monitor.check_quality_alerts():
                calls_with_issues += 1
        
        count = len(self.monitors)
        
        return {
            'active_calls': count,
            'average_mos': round(total_mos / count, 2),
            'average_packet_loss': round(total_loss / count, 2),
            'average_jitter_ms': round(total_jitter / count, 2),
            'calls_with_issues': calls_with_issues
        }
