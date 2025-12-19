"""
QoS (Quality of Service) Monitoring System
Tracks call quality metrics including jitter, packet loss, latency, and MOS scores
"""

import threading
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from pbx.utils.logger import get_logger


class QoSMetrics:
    """Container for QoS metrics for a single call"""

    def __init__(self, call_id: str):
        """
        Initialize QoS metrics for a call

        Args:
            call_id: Unique identifier for the call
        """
        self.call_id = call_id
        self.start_time = datetime.now()
        self.end_time = None

        # Packet statistics
        self.packets_sent = 0
        self.packets_received = 0
        self.packets_lost = 0
        self.packets_out_of_order = 0

        # Timing statistics (in milliseconds)
        # Use deque for efficient O(1) append/pop operations (instead of list
        # pop(0) which is O(n))
        self.jitter_samples = deque(maxlen=100)  # Recent jitter measurements
        self.latency_samples = deque(maxlen=100)  # Recent latency measurements
        self.max_jitter = 0.0
        self.max_latency = 0.0
        self.avg_jitter = 0.0
        self.avg_latency = 0.0

        # Sequence tracking for packet loss detection
        self.last_sequence_number = None
        self.expected_sequence = None

        # Timestamp tracking for jitter calculation
        self.last_packet_timestamp = None
        self.last_arrival_time = None

        # MOS score (Mean Opinion Score: 1.0-5.0, where 5.0 is best)
        self.mos_score = 0.0

        # Lock for thread safety
        self.lock = threading.Lock()

    def update_packet_received(
        self, sequence_number: int, timestamp: int, payload_size: int
    ) -> None:
        """
        Update metrics when a packet is received

        Args:
            sequence_number: RTP sequence number
            timestamp: RTP timestamp
            payload_size: Size of payload in bytes
        """
        with self.lock:
            self.packets_received += 1
            current_time = time.time()

            # Initialize sequence tracking on first packet
            if self.last_sequence_number is None:
                self.last_sequence_number = sequence_number
                self.expected_sequence = sequence_number + 1
                self.last_packet_timestamp = timestamp
                self.last_arrival_time = current_time
                return

            # Detect packet loss
            if sequence_number != self.expected_sequence:
                if sequence_number > self.expected_sequence:
                    # Packets were lost
                    lost = sequence_number - self.expected_sequence
                    self.packets_lost += lost
                elif sequence_number < self.last_sequence_number:
                    # Out of order packet
                    self.packets_out_of_order += 1

            # Calculate jitter (RFC 3550)
            # Jitter = variation in packet arrival times
            if self.last_arrival_time is not None and self.last_packet_timestamp is not None:
                # Time difference between packet arrivals (in ms)
                arrival_delta = (current_time - self.last_arrival_time) * 1000

                # Timestamp difference
                # Note: RTP timestamp units depend on codec sample rate (typically 8kHz for G.711)
                # For accurate jitter, the clock rate should be provided per-codec
                # Using 8kHz as default for telephony codecs (G.711)
                clock_rate = 8.0  # kHz (could be made configurable per codec)
                timestamp_delta = (timestamp - self.last_packet_timestamp) / clock_rate

                # Jitter is the absolute difference
                jitter = abs(arrival_delta - timestamp_delta)

                # Store jitter sample (deque automatically maintains
                # maxlen=100)
                self.jitter_samples.append(jitter)

                # Update max jitter
                if jitter > self.max_jitter:
                    self.max_jitter = jitter

                # Calculate average jitter
                self.avg_jitter = sum(self.jitter_samples) / len(self.jitter_samples)

            # Update tracking variables
            self.last_sequence_number = sequence_number
            self.expected_sequence = (sequence_number + 1) & 0xFFFF  # Wrap at 16 bits
            self.last_packet_timestamp = timestamp
            self.last_arrival_time = current_time

            # Recalculate MOS score
            self._calculate_mos()

    def update_packet_sent(self) -> None:
        """Update metrics when a packet is sent"""
        with self.lock:
            self.packets_sent += 1

    def add_latency_sample(self, latency_ms: float) -> None:
        """
        Add a latency measurement

        Args:
            latency_ms: Round-trip latency in milliseconds
        """
        with self.lock:
            # Deque automatically maintains maxlen=100
            self.latency_samples.append(latency_ms)

            if latency_ms > self.max_latency:
                self.max_latency = latency_ms

            self.avg_latency = sum(self.latency_samples) / len(self.latency_samples)

            # Recalculate MOS score
            self._calculate_mos()

    def _calculate_mos(self) -> None:
        """
        Calculate MOS (Mean Opinion Score) based on current metrics
        MOS scale: 1.0 (bad) to 5.0 (excellent)

        Uses E-Model (ITU-T G.107) simplified calculation
        """
        # If no packets were received and no latency data, we can't calculate a meaningful MOS
        # In this case, keep MOS at 0.0 to indicate "no data"
        if self.packets_received == 0 and not self.latency_samples:
            # No receive data available - cannot calculate MOS
            # This indicates a problem with the call (no RTP received)
            return

        # Start with perfect score
        r_factor = 93.2

        # Impact of packet loss (aggressive penalty)
        if self.packets_received > 0:
            loss_rate = (self.packets_lost / (self.packets_received + self.packets_lost)) * 100
            # ~2.5 R-factor reduction per 1% loss
            r_factor -= loss_rate * 2.5

        # Impact of latency (one-way delay)
        if self.latency_samples:
            # Assuming round-trip time, one-way is half
            one_way_delay = self.avg_latency / 2
            if one_way_delay > 160:  # ITU-T G.114 recommendation
                r_factor -= (one_way_delay - 160) * 0.3

        # Impact of jitter
        if self.jitter_samples:
            if self.avg_jitter > 30:  # Noticeable jitter threshold
                r_factor -= (self.avg_jitter - 30) * 0.1

        # Convert R-factor to MOS
        # MOS = 1 + 0.035*R + 7E-6*R*(R-60)*(100-R)
        if r_factor < 0:
            self.mos_score = 1.0
        elif r_factor > 100:
            self.mos_score = 4.5
        else:
            self.mos_score = (
                1 + 0.035 * r_factor + 0.000007 * r_factor * (r_factor - 60) * (100 - r_factor)
            )

            # Clamp to valid range
            self.mos_score = max(1.0, min(5.0, self.mos_score))

    def end_call(self) -> None:
        """Mark the call as ended"""
        with self.lock:
            self.end_time = datetime.now()
            # Ensure MOS score is calculated at call end
            self._calculate_mos()

    def get_summary(self) -> Dict:
        """
        Get a summary of QoS metrics

        Returns:
            Dictionary containing all QoS metrics
        """
        with self.lock:
            duration = None
            if self.end_time:
                duration = (self.end_time - self.start_time).total_seconds()
            else:
                duration = (datetime.now() - self.start_time).total_seconds()

            # Calculate packet loss percentage
            total_packets = self.packets_received + self.packets_lost
            loss_percentage = 0.0
            if total_packets > 0:
                loss_percentage = (self.packets_lost / total_packets) * 100

            return {
                "call_id": self.call_id,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration_seconds": round(duration, 2),
                "packets_sent": self.packets_sent,
                "packets_received": self.packets_received,
                "packets_lost": self.packets_lost,
                "packets_out_of_order": self.packets_out_of_order,
                "packet_loss_percentage": round(loss_percentage, 2),
                "jitter_avg_ms": round(self.avg_jitter, 2),
                "jitter_max_ms": round(self.max_jitter, 2),
                "latency_avg_ms": round(self.avg_latency, 2),
                "latency_max_ms": round(self.max_latency, 2),
                "mos_score": round(self.mos_score, 2),
                "quality_rating": self._get_quality_rating(),
            }

    def _get_quality_rating(self) -> str:
        """
        Get human-readable quality rating based on MOS score

        Returns:
            Quality rating string
        """
        if self.mos_score >= 4.3:
            return "Excellent"
        elif self.mos_score >= 4.0:
            return "Good"
        elif self.mos_score >= 3.6:
            return "Fair"
        elif self.mos_score >= 3.1:
            return "Poor"
        else:
            return "Bad"


class QoSMonitor:
    """
    QoS monitoring system for tracking call quality across the PBX
    """

    def __init__(self, pbx):
        """
        Initialize QoS monitor

        Args:
            pbx: Reference to main PBX instance
        """
        self.pbx = pbx
        self.logger = get_logger()
        self.active_calls = {}  # call_id -> QoSMetrics
        self.historical_data = []  # List of completed call metrics
        self.alert_thresholds = {
            "mos_min": 3.5,  # Alert if MOS drops below this
            "packet_loss_max": 2.0,  # Alert if packet loss exceeds this percentage
            "jitter_max": 50.0,  # Alert if jitter exceeds this (ms)
            "latency_max": 300.0,  # Alert if latency exceeds this (ms)
        }
        self.alerts = []  # List of quality alerts
        self.max_historical_records = 10000  # Keep last 10k calls
        self.lock = threading.Lock()

        self.logger.info("QoS monitoring system initialized")

    def start_monitoring(self, call_id: str) -> QoSMetrics:
        """
        Start monitoring QoS for a call

        Args:
            call_id: Unique identifier for the call

        Returns:
            QoSMetrics object for this call
        """
        with self.lock:
            if call_id in self.active_calls:
                self.logger.warning(f"QoS monitoring already active for call {call_id}")
                return self.active_calls[call_id]

            metrics = QoSMetrics(call_id)
            self.active_calls[call_id] = metrics
            self.logger.info(f"Started QoS monitoring for call {call_id}")
            return metrics

    def stop_monitoring(self, call_id: str) -> Optional[Dict]:
        """
        Stop monitoring QoS for a call and return final metrics

        Args:
            call_id: Unique identifier for the call

        Returns:
            Dictionary of final QoS metrics, or None if call not found
        """
        with self.lock:
            if call_id not in self.active_calls:
                self.logger.warning(f"No QoS monitoring active for call {call_id}")
                return None

            metrics = self.active_calls[call_id]
            metrics.end_call()
            summary = metrics.get_summary()

            # Move to historical data
            self.historical_data.append(summary)
            if len(self.historical_data) > self.max_historical_records:
                self.historical_data.pop(0)

            # Check for quality issues and generate alerts
            self._check_quality_alerts(summary)

            # Remove from active calls
            del self.active_calls[call_id]

            self.logger.info(
                f"Stopped QoS monitoring for call {call_id}, MOS: {
                    summary['mos_score']}"
            )

            # Store in database if available
            self._store_metrics(summary)

            return summary

    def get_metrics(self, call_id: str) -> Optional[Dict]:
        """
        Get current QoS metrics for an active call

        Args:
            call_id: Unique identifier for the call

        Returns:
            Dictionary of current QoS metrics, or None if call not found
        """
        with self.lock:
            if call_id not in self.active_calls:
                return None

            return self.active_calls[call_id].get_summary()

    def get_all_active_metrics(self) -> List[Dict]:
        """
        Get QoS metrics for all active calls

        Returns:
            List of dictionaries containing metrics for each active call
        """
        with self.lock:
            return [metrics.get_summary() for metrics in self.active_calls.values()]

    def get_historical_metrics(
        self, limit: int = 100, min_mos: Optional[float] = None
    ) -> List[Dict]:
        """
        Get historical QoS metrics

        Args:
            limit: Maximum number of records to return
            min_mos: Optional filter for minimum MOS score

        Returns:
            List of historical QoS metric dictionaries
        """
        with self.lock:
            data = self.historical_data[-limit:]

            if min_mos is not None:
                data = [d for d in data if d["mos_score"] >= min_mos]

            return data

    def get_alerts(self, limit: int = 50) -> List[Dict]:
        """
        Get recent quality alerts

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of alert dictionaries
        """
        with self.lock:
            return self.alerts[-limit:]

    def clear_alerts(self) -> int:
        """
        Clear all alerts

        Returns:
            Number of alerts cleared
        """
        with self.lock:
            count = len(self.alerts)
            self.alerts = []
            self.logger.info(f"Cleared {count} QoS alerts")
            return count

    def get_statistics(self) -> Dict:
        """
        Get overall QoS statistics

        Returns:
            Dictionary of aggregate statistics
        """
        with self.lock:
            if not self.historical_data:
                return {
                    "total_calls": 0,
                    "average_mos": 0.0,
                    "calls_with_issues": 0,
                    "total_alerts": len(self.alerts),
                    "active_calls": len(self.active_calls),
                }

            total_calls = len(self.historical_data)
            avg_mos = sum(d["mos_score"] for d in self.historical_data) / total_calls
            calls_with_issues = sum(
                1 for d in self.historical_data if d["mos_score"] < self.alert_thresholds["mos_min"]
            )

            return {
                "total_calls": total_calls,
                "average_mos": round(avg_mos, 2),
                "calls_with_issues": calls_with_issues,
                "issue_percentage": round((calls_with_issues / total_calls) * 100, 2),
                "total_alerts": len(self.alerts),
                "active_calls": len(self.active_calls),
            }

    def _check_quality_alerts(self, summary: Dict) -> None:
        """
        Check if metrics trigger any quality alerts

        Args:
            summary: QoS metrics summary
        """
        alerts_generated = []

        # Check MOS score
        if summary["mos_score"] < self.alert_thresholds["mos_min"]:
            alerts_generated.append(
                {
                    "type": "low_mos",
                    "severity": "warning",
                    "message": f"Low MOS score: {
                        summary['mos_score']} (threshold: {
                        self.alert_thresholds['mos_min']})",
                    "call_id": summary["call_id"],
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Check packet loss
        if summary["packet_loss_percentage"] > self.alert_thresholds["packet_loss_max"]:
            alerts_generated.append(
                {
                    "type": "high_packet_loss",
                    "severity": "error",
                    "message": f"High packet loss: {
                        summary['packet_loss_percentage']}% (threshold: {
                        self.alert_thresholds['packet_loss_max']}%)",
                    "call_id": summary["call_id"],
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Check jitter
        if summary["jitter_avg_ms"] > self.alert_thresholds["jitter_max"]:
            alerts_generated.append(
                {
                    "type": "high_jitter",
                    "severity": "warning",
                    "message": f"High jitter: {
                        summary['jitter_avg_ms']}ms (threshold: {
                        self.alert_thresholds['jitter_max']}ms)",
                    "call_id": summary["call_id"],
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Check latency
        if summary["latency_avg_ms"] > self.alert_thresholds["latency_max"]:
            alerts_generated.append(
                {
                    "type": "high_latency",
                    "severity": "warning",
                    "message": f"High latency: {
                        summary['latency_avg_ms']}ms (threshold: {
                        self.alert_thresholds['latency_max']}ms)",
                    "call_id": summary["call_id"],
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Add alerts to list
        for alert in alerts_generated:
            self.alerts.append(alert)
            self.logger.warning(f"QoS Alert: {alert['message']}")

        # Keep alerts list from growing too large
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]

    def _store_metrics(self, summary: Dict) -> None:
        """
        Store QoS metrics in database if available

        Args:
            summary: QoS metrics summary
        """
        try:
            if hasattr(self.pbx, "db") and self.pbx.db and self.pbx.db.enabled:
                # Store in database
                query = """
                    INSERT INTO qos_metrics
                    (call_id, start_time, end_time, duration_seconds,
                     packets_sent, packets_received, packets_lost, packet_loss_percentage,
                     jitter_avg_ms, jitter_max_ms, latency_avg_ms, latency_max_ms,
                     mos_score, quality_rating)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                params = (
                    summary["call_id"],
                    summary["start_time"],
                    summary["end_time"],
                    summary["duration_seconds"],
                    summary["packets_sent"],
                    summary["packets_received"],
                    summary["packets_lost"],
                    summary["packet_loss_percentage"],
                    summary["jitter_avg_ms"],
                    summary["jitter_max_ms"],
                    summary["latency_avg_ms"],
                    summary["latency_max_ms"],
                    summary["mos_score"],
                    summary["quality_rating"],
                )

                self.pbx.db.execute(query, params)
                self.logger.debug(
                    f"Stored QoS metrics for call {
                        summary['call_id']} in database"
                )
        except Exception as e:
            self.logger.error(f"Failed to store QoS metrics in database: {e}")

    def update_alert_thresholds(self, thresholds: Dict) -> None:
        """
        Update quality alert thresholds

        Args:
            thresholds: Dictionary of threshold values
        """
        with self.lock:
            self.alert_thresholds.update(thresholds)
            self.logger.info(
                f"Updated QoS alert thresholds: {
                    self.alert_thresholds}"
            )
