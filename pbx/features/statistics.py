"""
Enhanced Statistics and Analytics System
Provides comprehensive analytics for dashboard visualization
"""
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
from pbx.utils.logger import get_logger


class StatisticsEngine:
    """Advanced statistics and analytics engine"""
    
    def __init__(self, cdr_system):
        """
        Initialize statistics engine
        
        Args:
            cdr_system: CDR system instance
        """
        self.cdr_system = cdr_system
        self.logger = get_logger()
    
    def get_dashboard_statistics(self, days=7):
        """
        Get comprehensive statistics for dashboard
        
        Args:
            days: Number of days to analyze (default 7)
            
        Returns:
            Dictionary with comprehensive statistics
        """
        today = datetime.now()
        stats = {
            'overview': self._get_overview_stats(days),
            'daily_trends': self._get_daily_trends(days),
            'hourly_distribution': self._get_hourly_distribution(days),
            'top_callers': self._get_top_callers(days),
            'call_disposition': self._get_call_disposition(days),
            'peak_hours': self._get_peak_hours(days),
            'average_metrics': self._get_average_metrics(days)
        }
        
        return stats
    
    def _get_overview_stats(self, days):
        """Get overview statistics for the period"""
        total_calls = 0
        answered_calls = 0
        missed_calls = 0
        total_duration = 0
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=10000)
            
            total_calls += len(records)
            answered_calls += sum(1 for r in records if r.get('disposition') == 'answered')
            missed_calls += sum(1 for r in records if r.get('disposition') in ['no_answer', 'busy'])
            total_duration += sum(r.get('duration', 0) for r in records)
        
        avg_call_duration = (total_duration / answered_calls) if answered_calls > 0 else 0
        answer_rate = (answered_calls / total_calls * 100) if total_calls > 0 else 0
        
        return {
            'total_calls': total_calls,
            'answered_calls': answered_calls,
            'missed_calls': missed_calls,
            'answer_rate': round(answer_rate, 2),
            'avg_call_duration': round(avg_call_duration, 2),
            'total_duration_hours': round(total_duration / 3600, 2)
        }
    
    def _get_daily_trends(self, days):
        """Get daily call trends"""
        trends = []
        
        for i in range(days - 1, -1, -1):  # Reverse order for chronological
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=10000)
            
            total = len(records)
            answered = sum(1 for r in records if r.get('disposition') == 'answered')
            missed = sum(1 for r in records if r.get('disposition') in ['no_answer', 'busy'])
            failed = sum(1 for r in records if r.get('disposition') == 'failed')
            
            trends.append({
                'date': date,
                'total_calls': total,
                'answered': answered,
                'missed': missed,
                'failed': failed
            })
        
        return trends
    
    def _get_hourly_distribution(self, days):
        """Get call distribution by hour of day"""
        hourly_counts = defaultdict(int)
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=10000)
            
            for record in records:
                start_time = record.get('start_time')
                if start_time:
                    try:
                        dt = datetime.fromisoformat(start_time)
                        hour = dt.hour
                        hourly_counts[hour] += 1
                    except:
                        pass
        
        # Convert to sorted list
        distribution = [
            {'hour': hour, 'calls': hourly_counts[hour]}
            for hour in range(24)
        ]
        
        return distribution
    
    def _get_top_callers(self, days, limit=10):
        """Get top callers by call volume"""
        caller_stats = defaultdict(lambda: {'calls': 0, 'duration': 0})
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=10000)
            
            for record in records:
                from_ext = record.get('from_extension', 'Unknown')
                caller_stats[from_ext]['calls'] += 1
                caller_stats[from_ext]['duration'] += record.get('duration', 0)
        
        # Sort by call count and get top callers
        top_callers = [
            {
                'extension': ext,
                'calls': stats['calls'],
                'total_duration': round(stats['duration'], 2),
                'avg_duration': round(stats['duration'] / stats['calls'], 2) if stats['calls'] > 0 else 0
            }
            for ext, stats in sorted(caller_stats.items(), key=lambda x: x[1]['calls'], reverse=True)[:limit]
        ]
        
        return top_callers
    
    def _get_call_disposition(self, days):
        """Get call disposition breakdown"""
        dispositions = defaultdict(int)
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=10000)
            
            for record in records:
                disposition = record.get('disposition', 'unknown')
                dispositions[disposition] += 1
        
        total = sum(dispositions.values())
        
        return [
            {
                'disposition': disp,
                'count': count,
                'percentage': round((count / total * 100), 2) if total > 0 else 0
            }
            for disp, count in dispositions.items()
        ]
    
    def _get_peak_hours(self, days):
        """Get peak call hours"""
        hourly_counts = defaultdict(int)
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=10000)
            
            for record in records:
                start_time = record.get('start_time')
                if start_time:
                    try:
                        dt = datetime.fromisoformat(start_time)
                        hour = dt.hour
                        hourly_counts[hour] += 1
                    except:
                        pass
        
        # Get top 3 peak hours
        peak_hours = sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return [
            {
                'hour': f"{hour:02d}:00",
                'calls': count
            }
            for hour, count in peak_hours
        ]
    
    def _get_average_metrics(self, days):
        """Get average daily metrics"""
        total_calls = 0
        total_answered = 0
        total_duration = 0
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=10000)
            
            total_calls += len(records)
            total_answered += sum(1 for r in records if r.get('disposition') == 'answered')
            total_duration += sum(r.get('duration', 0) for r in records)
        
        return {
            'avg_calls_per_day': round(total_calls / days, 2) if days > 0 else 0,
            'avg_answered_per_day': round(total_answered / days, 2) if days > 0 else 0,
            'avg_duration_per_day': round(total_duration / days / 60, 2) if days > 0 else 0  # in minutes
        }
    
    def get_call_quality_metrics(self):
        """
        Get call quality metrics (placeholder for RTP quality data)
        
        Returns:
            Dictionary with quality metrics
        """
        # This is a placeholder for future RTP quality monitoring
        # In a real implementation, this would collect data from RTP sessions
        return {
            'average_mos': 4.2,  # Mean Opinion Score (1-5)
            'average_jitter': 15.5,  # milliseconds
            'average_packet_loss': 0.5,  # percentage
            'average_latency': 45.3,  # milliseconds
            'quality_distribution': {
                'excellent': 75,  # percentage
                'good': 20,
                'fair': 4,
                'poor': 1
            },
            'note': 'Call quality metrics require RTP monitoring implementation'
        }
    
    def get_real_time_metrics(self, pbx_core):
        """
        Get real-time system metrics
        
        Args:
            pbx_core: PBX core instance
            
        Returns:
            Dictionary with real-time metrics
        """
        active_calls = len(pbx_core.calls) if hasattr(pbx_core, 'calls') else 0
        registered_extensions = len([ext for ext in pbx_core.extensions.values() if ext.get('registered', False)]) if hasattr(pbx_core, 'extensions') else 0
        
        return {
            'active_calls': active_calls,
            'registered_extensions': registered_extensions,
            'system_uptime': self._get_system_uptime(pbx_core),
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_system_uptime(self, pbx_core):
        """Get system uptime in seconds"""
        if hasattr(pbx_core, 'start_time'):
            uptime = (datetime.now() - pbx_core.start_time).total_seconds()
            return round(uptime, 0)
        return 0
