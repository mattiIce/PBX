"""
Advanced Analytics Module for Premium Features
Provides comprehensive call analytics and reporting
"""
import json
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from pbx.utils.logger import get_logger

logger = get_logger(__name__)


class AnalyticsEngine:
    """Advanced analytics engine for call data analysis"""
    
    def __init__(self, config: dict, cdr_manager=None):
        """Initialize analytics engine"""
        self.config = config
        self.cdr_manager = cdr_manager
        self.cdr_dir = Path(config.get('cdr.directory', 'cdr'))
        
    def get_call_volume_by_hour(self, days: int = 7) -> Dict[int, int]:
        """
        Get call volume distribution by hour of day
        Args:
            days: Number of days to analyze
        Returns:
            Dictionary with hour (0-23) as key and call count as value
        """
        volume_by_hour = defaultdict(int)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        records = self._load_cdr_records(start_date, end_date)
        
        for record in records:
            try:
                timestamp = datetime.fromisoformat(record.get('start_time', ''))
                hour = timestamp.hour
                volume_by_hour[hour] += 1
            except (ValueError, TypeError):
                continue
                
        return dict(volume_by_hour)
    
    def get_call_volume_by_day(self, days: int = 30) -> Dict[str, int]:
        """
        Get call volume by day
        Args:
            days: Number of days to analyze
        Returns:
            Dictionary with date as key and call count as value
        """
        volume_by_day = defaultdict(int)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        records = self._load_cdr_records(start_date, end_date)
        
        for record in records:
            try:
                timestamp = datetime.fromisoformat(record.get('start_time', ''))
                date_key = timestamp.strftime('%Y-%m-%d')
                volume_by_day[date_key] += 1
            except (ValueError, TypeError):
                continue
                
        return dict(volume_by_day)
    
    def get_extension_statistics(self, extension: str, days: int = 30) -> Dict:
        """
        Get detailed statistics for a specific extension
        Args:
            extension: Extension number
            days: Number of days to analyze
        Returns:
            Dictionary with extension statistics
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        records = self._load_cdr_records(start_date, end_date)
        
        stats = {
            'extension': extension,
            'total_calls': 0,
            'inbound_calls': 0,
            'outbound_calls': 0,
            'answered_calls': 0,
            'missed_calls': 0,
            'total_duration_seconds': 0,
            'average_duration_seconds': 0,
            'longest_call_seconds': 0,
            'shortest_call_seconds': float('inf'),
            'busiest_hour': None,
            'call_distribution': defaultdict(int)
        }
        
        durations = []
        hour_distribution = defaultdict(int)
        
        for record in records:
            from_ext = record.get('from')
            to_ext = record.get('to')
            
            if from_ext == extension or to_ext == extension:
                stats['total_calls'] += 1
                
                if from_ext == extension:
                    stats['outbound_calls'] += 1
                if to_ext == extension:
                    stats['inbound_calls'] += 1
                
                disposition = record.get('disposition', '').lower()
                if disposition == 'answered':
                    stats['answered_calls'] += 1
                elif disposition in ['no_answer', 'missed']:
                    stats['missed_calls'] += 1
                
                duration = record.get('duration', 0)
                if duration > 0:
                    durations.append(duration)
                    stats['total_duration_seconds'] += duration
                    stats['longest_call_seconds'] = max(stats['longest_call_seconds'], duration)
                    if duration < stats['shortest_call_seconds']:
                        stats['shortest_call_seconds'] = duration
                
                # Track hourly distribution
                try:
                    timestamp = datetime.fromisoformat(record.get('start_time', ''))
                    hour_distribution[timestamp.hour] += 1
                except (ValueError, TypeError):
                    pass
        
        # Calculate averages
        if durations:
            stats['average_duration_seconds'] = sum(durations) / len(durations)
        if stats['shortest_call_seconds'] == float('inf'):
            stats['shortest_call_seconds'] = 0
            
        # Find busiest hour
        if hour_distribution:
            stats['busiest_hour'] = max(hour_distribution.items(), key=lambda x: x[1])[0]
        
        return stats
    
    def get_queue_performance(self, queue_number: str, days: int = 7) -> Dict:
        """
        Get queue performance metrics
        Args:
            queue_number: Queue number
            days: Number of days to analyze
        Returns:
            Dictionary with queue performance metrics
        """
        # This is a placeholder for queue analytics
        # In a real implementation, this would analyze queue-specific CDR data
        return {
            'queue_number': queue_number,
            'total_calls': 0,
            'answered_calls': 0,
            'abandoned_calls': 0,
            'average_wait_time': 0,
            'longest_wait_time': 0,
            'service_level_20s': 0,  # % answered within 20 seconds
            'service_level_30s': 0   # % answered within 30 seconds
        }
    
    def get_top_callers(self, limit: int = 10, days: int = 30) -> List[Dict]:
        """
        Get top callers by call volume
        Args:
            limit: Number of top callers to return
            days: Number of days to analyze
        Returns:
            List of dictionaries with caller information
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        records = self._load_cdr_records(start_date, end_date)
        
        caller_stats = defaultdict(lambda: {'calls': 0, 'total_duration': 0})
        
        for record in records:
            from_ext = record.get('from')
            if from_ext:
                caller_stats[from_ext]['calls'] += 1
                caller_stats[from_ext]['total_duration'] += record.get('duration', 0)
        
        # Sort by call count
        sorted_callers = sorted(
            caller_stats.items(),
            key=lambda x: x[1]['calls'],
            reverse=True
        )[:limit]
        
        return [
            {
                'extension': ext,
                'call_count': stats['calls'],
                'total_duration_seconds': stats['total_duration']
            }
            for ext, stats in sorted_callers
        ]
    
    def get_call_quality_metrics(self, days: int = 7) -> Dict:
        """
        Get call quality metrics (placeholder for future QoS implementation)
        Args:
            days: Number of days to analyze
        Returns:
            Dictionary with call quality metrics
        """
        return {
            'average_mos': 4.2,  # Mean Opinion Score (1-5)
            'average_jitter_ms': 2.5,
            'average_latency_ms': 45,
            'packet_loss_percentage': 0.5,
            'calls_with_quality_issues': 0,
            'total_calls_analyzed': 0
        }
    
    def get_cost_analysis(self, days: int = 30) -> Dict:
        """
        Get cost analysis for calls (premium feature)
        Args:
            days: Number of days to analyze
        Returns:
            Dictionary with cost metrics
        """
        # Placeholder for cost calculation
        # Would integrate with trunk pricing, international rates, etc.
        return {
            'total_cost': 0.0,
            'inbound_cost': 0.0,
            'outbound_cost': 0.0,
            'international_cost': 0.0,
            'cost_per_minute': 0.0,
            'cost_by_extension': {}
        }
    
    def generate_executive_summary(self, days: int = 7) -> Dict:
        """
        Generate executive summary report
        Args:
            days: Number of days to analyze
        Returns:
            Dictionary with executive summary
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        records = self._load_cdr_records(start_date, end_date)
        
        total_calls = len(records)
        answered = sum(1 for r in records if r.get('disposition') == 'ANSWERED')
        total_duration = sum(r.get('duration', 0) for r in records)
        
        return {
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'days': days
            },
            'overview': {
                'total_calls': total_calls,
                'answered_calls': answered,
                'answer_rate': (answered / total_calls * 100) if total_calls > 0 else 0,
                'total_duration_hours': total_duration / 3600,
                'average_call_duration_minutes': (total_duration / total_calls / 60) if total_calls > 0 else 0,
                'calls_per_day': total_calls / days if days > 0 else 0
            },
            'trends': {
                'volume_change': 0,  # Would compare to previous period
                'duration_change': 0
            }
        }
    
    def _load_cdr_records(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Load CDR records within date range
        Args:
            start_date: Start date
            end_date: End date
        Returns:
            List of CDR records
        """
        records = []
        
        if not self.cdr_dir.exists():
            return records
        
        # Iterate through CDR files in date range
        current_date = start_date
        while current_date <= end_date:
            cdr_file = self.cdr_dir / f"cdr_{current_date.strftime('%Y-%m-%d')}.jsonl"
            
            if cdr_file.exists():
                try:
                    with open(cdr_file, 'r') as f:
                        for line in f:
                            if line.strip():
                                try:
                                    record = json.loads(line)
                                    records.append(record)
                                except json.JSONDecodeError:
                                    continue
                except Exception as e:
                    logger.error(f"Error reading CDR file {cdr_file}: {e}")
            
            current_date += timedelta(days=1)
        
        return records
