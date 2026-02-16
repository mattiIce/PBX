"""
Enhanced Statistics and Analytics System
Provides comprehensive analytics for dashboard visualization
"""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from pbx.utils.logger import get_logger


class StatisticsEngine:
    """Advanced statistics and analytics engine"""

    def __init__(self, cdr_system) -> None:
        """
        Initialize statistics engine

        Args:
            cdr_system: CDR system instance
        """
        self.cdr_system = cdr_system
        self.logger = get_logger()

    def get_dashboard_statistics(self, days: int =7) -> dict:
        """
        Get comprehensive statistics for dashboard

        Args:
            days: Number of days to analyze (default 7)

        Returns:
            Dictionary with comprehensive statistics
        """
        datetime.now(UTC)
        stats = {
            "overview": self._get_overview_stats(days),
            "daily_trends": self._get_daily_trends(days),
            "hourly_distribution": self._get_hourly_distribution(days),
            "top_callers": self._get_top_callers(days),
            "call_disposition": self._get_call_disposition(days),
            "peak_hours": self._get_peak_hours(days),
            "average_metrics": self._get_average_metrics(days),
        }

        return stats

    def _get_overview_stats(self, days: int):
        """Get overview statistics for the period"""
        total_calls = 0
        answered_calls = 0
        missed_calls = 0
        total_duration = 0

        for i in range(days):
            date = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=10000)

            total_calls += len(records)
            answered_calls += sum(1 for r in records if r.get("disposition") == "answered")
            missed_calls += sum(1 for r in records if r.get("disposition") in ["no_answer", "busy"])
            total_duration += sum(r.get("duration", 0) for r in records)

        avg_call_duration = (total_duration / answered_calls) if answered_calls > 0 else 0
        answer_rate = (answered_calls / total_calls * 100) if total_calls > 0 else 0

        return {
            "total_calls": total_calls,
            "answered_calls": answered_calls,
            "missed_calls": missed_calls,
            "answer_rate": round(answer_rate, 2),
            "avg_call_duration": round(avg_call_duration, 2),
            "total_duration_hours": round(total_duration / 3600, 2),
        }

    def _get_daily_trends(self, days: int):
        """Get daily call trends"""
        trends = []

        for i in range(days - 1, -1, -1):  # Reverse order for chronological
            date = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=10000)

            total = len(records)
            answered = sum(1 for r in records if r.get("disposition") == "answered")
            missed = sum(1 for r in records if r.get("disposition") in ["no_answer", "busy"])
            failed = sum(1 for r in records if r.get("disposition") == "failed")

            trends.append(
                {
                    "date": date,
                    "total_calls": total,
                    "answered": answered,
                    "missed": missed,
                    "failed": failed,
                }
            )

        return trends

    def _get_hourly_distribution(self, days: int):
        """Get call distribution by hour of day"""
        hourly_counts = defaultdict(int)

        for i in range(days):
            date = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=10000)

            for record in records:
                start_time = record.get("start_time")
                if start_time:
                    try:
                        dt = datetime.fromisoformat(start_time)
                        hour = dt.hour
                        hourly_counts[hour] += 1
                    except (ValueError, TypeError) as e:
                        self.logger.debug(f"Error parsing timestamp: {e}")

        # Convert to sorted list
        distribution = [{"hour": hour, "calls": hourly_counts[hour]} for hour in range(24)]

        return distribution

    def _get_top_callers(self, days: int, limit: int =10):
        """Get top callers by call volume"""
        caller_stats = defaultdict(lambda: {"calls": 0, "duration": 0})

        for i in range(days):
            date = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=10000)

            for record in records:
                from_ext = record.get("from_extension", "Unknown")
                caller_stats[from_ext]["calls"] += 1
                caller_stats[from_ext]["duration"] += record.get("duration", 0)

        # Sort by call count and get top callers
        top_callers = [
            {
                "extension": ext,
                "calls": stats["calls"],
                "total_duration": round(stats["duration"], 2),
                "avg_duration": (
                    round(stats["duration"] / stats["calls"], 2) if stats["calls"] > 0 else 0
                ),
            }
            for ext, stats in sorted(
                caller_stats.items(), key=lambda x: x[1]["calls"], reverse=True
            )[:limit]
        ]

        return top_callers

    def _get_call_disposition(self, days: int):
        """Get call disposition breakdown"""
        dispositions = defaultdict(int)

        for i in range(days):
            date = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=10000)

            for record in records:
                disposition = record.get("disposition", "unknown")
                dispositions[disposition] += 1

        total = sum(dispositions.values())

        return [
            {
                "disposition": disp,
                "count": count,
                "percentage": round((count / total * 100), 2) if total > 0 else 0,
            }
            for disp, count in dispositions.items()
        ]

    def _get_peak_hours(self, days: int):
        """Get peak call hours"""
        hourly_counts = defaultdict(int)

        for i in range(days):
            date = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=10000)

            for record in records:
                start_time = record.get("start_time")
                if start_time:
                    try:
                        dt = datetime.fromisoformat(start_time)
                        hour = dt.hour
                        hourly_counts[hour] += 1
                    except (ValueError, TypeError) as e:
                        self.logger.debug(f"Error parsing timestamp: {e}")

        # Get top 3 peak hours
        peak_hours = sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        return [{"hour": f"{hour:02d}:00", "calls": count} for hour, count in peak_hours]

    def _get_average_metrics(self, days: int):
        """Get average daily metrics"""
        total_calls = 0
        total_answered = 0
        total_duration = 0

        for i in range(days):
            date = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=10000)

            total_calls += len(records)
            total_answered += sum(1 for r in records if r.get("disposition") == "answered")
            total_duration += sum(r.get("duration", 0) for r in records)

        return {
            "avg_calls_per_day": round(total_calls / days, 2) if days > 0 else 0,
            "avg_answered_per_day": round(total_answered / days, 2) if days > 0 else 0,
            # in minutes
            "avg_duration_per_day": round(total_duration / days / 60, 2) if days > 0 else 0,
        }

    def get_call_quality_metrics(self, pbx_core=None) -> dict:
        """
        Get call quality metrics from QoS monitoring

        Args:
            pbx_core: PBX core instance (optional, for QoS integration)

        Returns:
            Dictionary with quality metrics
        """
        # Try to get metrics from QoS monitor if available
        if pbx_core and hasattr(pbx_core, "qos_monitor"):
            qos_stats = pbx_core.qos_monitor.get_statistics()
            historical = pbx_core.qos_monitor.get_historical_metrics(limit=100)

            if historical:
                # Calculate averages from historical data
                avg_mos = sum(m["mos_score"] for m in historical) / len(historical)
                avg_jitter = sum(m["jitter_avg_ms"] for m in historical) / len(historical)
                avg_packet_loss = sum(m["packet_loss_percentage"] for m in historical) / len(
                    historical
                )
                avg_latency = sum(m["latency_avg_ms"] for m in historical) / len(historical)

                # Calculate quality distribution
                excellent = sum(1 for m in historical if m["mos_score"] >= 4.3)
                good = sum(1 for m in historical if 4.0 <= m["mos_score"] < 4.3)
                fair = sum(1 for m in historical if 3.6 <= m["mos_score"] < 4.0)
                poor = sum(1 for m in historical if 3.1 <= m["mos_score"] < 3.6)
                bad = sum(1 for m in historical if m["mos_score"] < 3.1)

                total = len(historical)

                return {
                    "average_mos": round(avg_mos, 2),
                    "average_jitter": round(avg_jitter, 2),
                    "average_packet_loss": round(avg_packet_loss, 2),
                    "average_latency": round(avg_latency, 2),
                    "quality_distribution": {
                        "excellent": round((excellent / total) * 100, 1),
                        "good": round((good / total) * 100, 1),
                        "fair": round((fair / total) * 100, 1),
                        "poor": round((poor / total) * 100, 1),
                        "bad": round((bad / total) * 100, 1),
                    },
                    "total_calls_monitored": qos_stats["total_calls"],
                    "active_monitored_calls": qos_stats["active_calls"],
                    "calls_with_issues": qos_stats["calls_with_issues"],
                }

        # Fallback to placeholder data if QoS not available
        return {
            "average_mos": 0.0,
            "average_jitter": 0.0,
            "average_packet_loss": 0.0,
            "average_latency": 0.0,
            "quality_distribution": {"excellent": 0, "good": 0, "fair": 0, "poor": 0, "bad": 0},
            "note": "QoS monitoring not available - no quality data",
        }

    def get_real_time_metrics(self, pbx_core) -> dict:
        """
        Get real-time system metrics

        Args:
            pbx_core: PBX core instance

        Returns:
            Dictionary with real-time metrics
        """
        active_calls = len(pbx_core.calls) if hasattr(pbx_core, "calls") else 0
        registered_extensions = (
            len([ext for ext in pbx_core.extensions.values() if ext.get("registered", False)])
            if hasattr(pbx_core, "extensions")
            else 0
        )

        return {
            "active_calls": active_calls,
            "registered_extensions": registered_extensions,
            "system_uptime": self._get_system_uptime(pbx_core),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _get_system_uptime(self, pbx_core):
        """Get system uptime in seconds"""
        if hasattr(pbx_core, "start_time"):
            uptime = (datetime.now(UTC) - pbx_core.start_time).total_seconds()
            return round(uptime, 0)
        return 0

    def get_advanced_analytics(self, start_date, end_date, filters=None) -> dict:
        """
        Get advanced analytics with date range and filters

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            filters: Optional filters dict (extension, disposition, min_duration, etc.)

        Returns:
            Dictionary with filtered analytics
        """
        from datetime import datetime as dt

        start = dt.strptime(start_date, "%Y-%m-%d")
        end = dt.strptime(end_date, "%Y-%m-%d")
        days_diff = (end - start).days + 1

        all_records = []
        for i in range(days_diff):
            date = (start + timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=100000)
            all_records.extend(records)

        # Apply filters
        if filters:
            filtered_records = all_records

            if filters.get("extension"):
                filtered_records = [
                    r
                    for r in filtered_records
                    if r.get("from_ext") == filters["extension"]
                    or r.get("to_ext") == filters["extension"]
                ]

            if filters.get("disposition"):
                filtered_records = [
                    r for r in filtered_records if r.get("disposition") == filters["disposition"]
                ]

            if filters.get("min_duration"):
                min_dur = filters["min_duration"]
                filtered_records = [r for r in filtered_records if r.get("duration", 0) >= min_dur]

            all_records = filtered_records

        # Calculate comprehensive metrics
        total_calls = len(all_records)
        answered_calls = sum(1 for r in all_records if r.get("disposition") == "answered")
        missed_calls = sum(1 for r in all_records if r.get("disposition") in ["no_answer", "busy"])
        failed_calls = sum(1 for r in all_records if r.get("disposition") == "failed")
        total_duration = sum(r.get("duration", 0) for r in all_records)

        return {
            "date_range": {"start": start_date, "end": end_date, "days": days_diff},
            "summary": {
                "total_calls": total_calls,
                "answered": answered_calls,
                "missed": missed_calls,
                "failed": failed_calls,
                "answer_rate": round(
                    (answered_calls / total_calls * 100) if total_calls > 0 else 0, 2
                ),
                "total_duration_hours": round(total_duration / 3600, 2),
                "avg_call_duration": round(
                    (total_duration / answered_calls) if answered_calls > 0 else 0, 2
                ),
            },
            "records": all_records,
            "filters_applied": filters or {},
        }

    def get_call_center_metrics(self, days: int =7, queue_name=None) -> dict:
        """
        Get call center performance metrics

        Args:
            days: Number of days to analyze
            queue_name: Optional queue name to filter

        Returns:
            Dictionary with call center metrics
        """
        all_records = []
        for i in range(days):
            date = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            records = self.cdr_system.get_records(date, limit=10000)
            all_records.extend(records)

        # Filter queue calls if specified
        if queue_name:
            all_records = [r for r in all_records if r.get("queue") == queue_name]

        answered = [r for r in all_records if r.get("disposition") == "answered"]
        abandoned = [r for r in all_records if r.get("disposition") in ["no_answer", "busy"]]

        # Calculate metrics
        total_calls = len(all_records)
        answered_count = len(answered)
        abandoned_count = len(abandoned)

        # Average handle time (AHT) - time spent on call
        aht = (
            sum(r.get("duration", 0) for r in answered) / answered_count
            if answered_count > 0
            else 0
        )

        # Average speed of answer (ASA) - wait time before answer
        # Note: This requires wait_time field in CDR which may not be present
        asa = (
            sum(r.get("wait_time", 0) for r in answered) / answered_count
            if answered_count > 0
            else 0
        )

        # Service level - % answered within threshold (typically 20 seconds)
        service_threshold = 20  # seconds
        answered_within_threshold = sum(
            1 for r in answered if r.get("wait_time", 0) <= service_threshold
        )
        service_level = (
            (answered_within_threshold / answered_count * 100) if answered_count > 0 else 0
        )

        # Abandonment rate
        abandonment_rate = (abandoned_count / total_calls * 100) if total_calls > 0 else 0

        return {
            "period_days": days,
            "queue": queue_name or "All Queues",
            "total_calls": total_calls,
            "answered": answered_count,
            "abandoned": abandoned_count,
            "average_handle_time": round(aht, 2),
            "average_speed_of_answer": round(asa, 2),
            "service_level_20s": round(service_level, 2),
            "abandonment_rate": round(abandonment_rate, 2),
            "answer_rate": round((answered_count / total_calls * 100) if total_calls > 0 else 0, 2),
        }

    def export_to_csv(self, records, filename: str) -> bool:
        """
        Export call records to CSV file

        Args:
            records: list of call records
            filename: Output filename

        Returns:
            Boolean indicating success
        """
        try:
            import csv  # Import here to avoid unnecessary dependency if not used

            if not records:
                return False

            # Define CSV headers
            headers = [
                "timestamp",
                "from_ext",
                "to_ext",
                "caller_id",
                "called_number",
                "disposition",
                "duration",
                "wait_time",
                "queue",
            ]

            with open(filename, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(records)

            self.logger.info(f"Exported {len(records)} records to {filename}")
            return True

        except OSError as e:
            self.logger.error(f"Failed to export to CSV: {e}")
            return False

    def generate_report(self, report_type, params) -> dict:
        """
        Generate custom report

        Args:
            report_type: type of report ('daily', 'weekly', 'monthly', 'custom')
            params: Report parameters (date range, filters, etc.)

        Returns:
            Dictionary with report data
        """
        if report_type == "daily":
            date = params.get("date", datetime.now(UTC).strftime("%Y-%m-%d"))
            records = self.cdr_system.get_records(date, limit=100000)

            return {
                "report_type": "Daily Report",
                "date": date,
                "total_calls": len(records),
                "answered": sum(1 for r in records if r.get("disposition") == "answered"),
                "records": records,
            }

        if report_type == "weekly":
            end_date = datetime.now(UTC)
            start_date = end_date - timedelta(days=7)
            return self.get_advanced_analytics(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                params.get("filters"),
            )

        if report_type == "monthly":
            end_date = datetime.now(UTC)
            start_date = end_date - timedelta(days=30)
            return self.get_advanced_analytics(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                params.get("filters"),
            )

        if report_type == "custom":
            return self.get_advanced_analytics(
                params["start_date"], params["end_date"], params.get("filters")
            )

        return {"error": "Invalid report type"}
