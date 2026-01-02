#!/usr/bin/env python3
"""
Capacity planning calculator for PBX system.

Helps determine resource requirements based on usage patterns.
"""

import argparse
import json
import sys
from dataclasses import dataclass


@dataclass
class CapacityRequirements:
    """Resource requirements for PBX deployment."""

    # Compute resources
    cpu_cores: int
    memory_gb: int
    disk_gb: int

    # Network resources
    bandwidth_mbps: float

    # Application limits
    max_extensions: int
    max_concurrent_calls: int
    max_queue_size: int

    # Storage estimates
    voicemail_gb: float
    recording_gb: float
    database_gb: float
    logs_gb: float

    # Costs (optional)
    estimated_monthly_cost: float = 0.0


class CapacityCalculator:
    """Calculate capacity requirements for PBX deployment."""

    # Resource per extension
    MEMORY_PER_EXTENSION_MB = 2  # 2 MB per registered extension
    CPU_PER_CONCURRENT_CALL = 0.02  # 2% CPU per concurrent call
    BANDWIDTH_PER_CALL_KBPS = 100  # ~100 Kbps per call (G.711)

    # Storage estimates
    VOICEMAIL_PER_USER_MB = 50  # Average 50 MB per user
    RECORDING_PER_HOUR_MB = 7.2  # ~7.2 MB per hour (G.711, mono)
    DATABASE_BASE_MB = 500  # Base database size
    DATABASE_PER_EXTENSION_MB = 1  # Additional per extension
    LOGS_PER_DAY_MB = 100  # Log file growth

    # Cost estimates (example AWS-like pricing; for planning only)
    # NOTE: These values are illustrative and may not reflect current or accurate
    # cloud provider pricing. Review and adjust them before using this tool for
    # production or billing-related decisions.
    COST_PER_CPU_CORE = 20  # $20/month per vCPU (example estimate)
    COST_PER_GB_RAM = 5  # $5/month per GB RAM (example estimate)
    COST_PER_GB_DISK = 0.10  # $0.10/month per GB storage (example estimate)
    COST_PER_MBPS = 10  # $10/month per Mbps (example estimate)

    def calculate(
        self,
        extensions: int,
        concurrent_calls: int,
        avg_call_duration_min: int = 5,
        calls_per_day: int = 100,
        recording_enabled: bool = False,
        recording_retention_days: int = 90,
        voicemail_users_percent: int = 80,
        log_retention_days: int = 30,
    ) -> CapacityRequirements:
        """
        Calculate capacity requirements.

        Args:
            extensions: Number of extensions
            concurrent_calls: Peak concurrent calls
            avg_call_duration_min: Average call duration in minutes
            calls_per_day: Average calls per day
            recording_enabled: Whether call recording is enabled
            recording_retention_days: Call recording retention period
            voicemail_users_percent: Percentage of users using voicemail
            log_retention_days: Log retention period

        Returns:
            CapacityRequirements object
        """
        # CPU calculation
        # Base: 2 cores minimum
        # Additional: 0.02 CPU per concurrent call
        cpu_for_calls = concurrent_calls * self.CPU_PER_CONCURRENT_CALL
        cpu_cores = max(2, int(cpu_for_calls) + 2)  # +2 for overhead

        # Adjust for large deployments
        if extensions > 500:
            cpu_cores = max(cpu_cores, 8)
        if extensions > 1000:
            cpu_cores = max(cpu_cores, 16)

        # Memory calculation
        # Base: 4 GB minimum
        # Extensions: 2 MB per extension
        # Calls: 50 MB per concurrent call (RTP buffers, codec state)
        memory_extensions_mb = extensions * self.MEMORY_PER_EXTENSION_MB
        memory_calls_mb = concurrent_calls * 50
        memory_base_mb = 4096  # 4 GB base
        memory_total_mb = memory_base_mb + memory_extensions_mb + memory_calls_mb
        memory_gb = int((memory_total_mb / 1024) + 1)  # Round up

        # Storage calculation
        # Voicemail storage
        voicemail_users = int(extensions * (voicemail_users_percent / 100))
        voicemail_gb = (
            voicemail_users * self.VOICEMAIL_PER_USER_MB / 1024
        )  # Convert to GB

        # Call recording storage
        recording_gb = 0.0
        if recording_enabled:
            hours_per_day = (calls_per_day * avg_call_duration_min) / 60
            recording_mb_per_day = hours_per_day * self.RECORDING_PER_HOUR_MB
            recording_gb = (
                recording_mb_per_day * recording_retention_days / 1024
            )  # Convert to GB

        # Database storage
        database_mb = (
            self.DATABASE_BASE_MB + extensions * self.DATABASE_PER_EXTENSION_MB
        )
        # Add CDR storage (assume 200 bytes per call)
        cdr_days = 365  # Keep CDR for 1 year
        cdr_mb = (calls_per_day * cdr_days * 200) / (1024 * 1024)
        database_gb = (database_mb + cdr_mb) / 1024

        # Log storage
        logs_gb = (self.LOGS_PER_DAY_MB * log_retention_days) / 1024

        # Total disk
        disk_base_gb = 20  # OS + application
        disk_total_gb = int(
            disk_base_gb + voicemail_gb + recording_gb + database_gb + logs_gb + 10
        )  # +10 GB buffer

        # Network bandwidth
        # Peak: concurrent calls * bandwidth per call
        # Buffer: 1.5x for overhead
        bandwidth_kbps = concurrent_calls * self.BANDWIDTH_PER_CALL_KBPS * 1.5
        bandwidth_mbps = bandwidth_kbps / 1000

        # Application limits
        max_extensions = extensions
        max_concurrent_calls = concurrent_calls
        max_queue_size = int(concurrent_calls * 0.5)  # 50% of concurrent calls

        # Cost estimate
        cost_cpu = cpu_cores * self.COST_PER_CPU_CORE
        cost_memory = memory_gb * self.COST_PER_GB_RAM
        cost_disk = disk_total_gb * self.COST_PER_GB_DISK
        cost_bandwidth = bandwidth_mbps * self.COST_PER_MBPS
        estimated_monthly_cost = cost_cpu + cost_memory + cost_disk + cost_bandwidth

        return CapacityRequirements(
            cpu_cores=cpu_cores,
            memory_gb=memory_gb,
            disk_gb=disk_total_gb,
            bandwidth_mbps=round(bandwidth_mbps, 2),
            max_extensions=max_extensions,
            max_concurrent_calls=max_concurrent_calls,
            max_queue_size=max_queue_size,
            voicemail_gb=round(voicemail_gb, 2),
            recording_gb=round(recording_gb, 2),
            database_gb=round(database_gb, 2),
            logs_gb=round(logs_gb, 2),
            estimated_monthly_cost=round(estimated_monthly_cost, 2),
        )

    def print_report(self, requirements: CapacityRequirements, format: str = "text"):
        """
        Print capacity planning report.

        Args:
            requirements: CapacityRequirements object
            format: Output format (text/json)
        """
        if format == "json":
            print(json.dumps(requirements.__dict__, indent=2))
            return

        print("=" * 70)
        print("PBX CAPACITY PLANNING REPORT")
        print("=" * 70)
        print()

        print("COMPUTE RESOURCES:")
        print(f"  CPU Cores:    {requirements.cpu_cores} vCPUs")
        print(f"  Memory:       {requirements.memory_gb} GB RAM")
        print(f"  Disk Storage: {requirements.disk_gb} GB SSD")
        print()

        print("NETWORK RESOURCES:")
        print(f"  Bandwidth:    {requirements.bandwidth_mbps} Mbps")
        print()

        print("APPLICATION CAPACITY:")
        print(f"  Max Extensions:       {requirements.max_extensions}")
        print(f"  Max Concurrent Calls: {requirements.max_concurrent_calls}")
        print(f"  Max Queue Size:       {requirements.max_queue_size}")
        print()

        print("STORAGE BREAKDOWN:")
        print(f"  Voicemail:     {requirements.voicemail_gb} GB")
        print(f"  Recordings:    {requirements.recording_gb} GB")
        print(f"  Database:      {requirements.database_gb} GB")
        print(f"  Logs:          {requirements.logs_gb} GB")
        print()

        print("ESTIMATED MONTHLY COST:")
        print(f"  Infrastructure: ${requirements.estimated_monthly_cost:.2f}/month")
        print()

        print("RECOMMENDED SERVER SPECIFICATIONS:")
        print("-" * 70)
        if requirements.cpu_cores <= 4 and requirements.memory_gb <= 16:
            print("  Instance Type: SMALL")
            print("  Example: AWS t3.xlarge, DigitalOcean 4vCPU/16GB")
        elif requirements.cpu_cores <= 8 and requirements.memory_gb <= 32:
            print("  Instance Type: MEDIUM")
            print("  Example: AWS m5.2xlarge, DigitalOcean 8vCPU/32GB")
        else:
            print("  Instance Type: LARGE")
            print("  Example: AWS m5.4xlarge, DigitalOcean 16vCPU/64GB")
        print()

        print("SCALING RECOMMENDATIONS:")
        print("-" * 70)
        print(
            f"  • Current capacity supports {requirements.max_concurrent_calls} concurrent calls"
        )
        print(f"  • Monitor CPU usage; scale up if consistently > 70%")
        print(f"  • Monitor memory usage; scale up if consistently > 80%")
        print(
            f"  • Consider load balancing for > {int(requirements.max_concurrent_calls * 1.5)} concurrent calls"
        )
        print(
            f"  • Review storage monthly; current allocation for {requirements.disk_gb}GB"
        )
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Calculate PBX capacity requirements",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Small office (50 users, 10 concurrent calls)
  %(prog)s --extensions 50 --concurrent-calls 10

  # Medium business (200 users, 50 concurrent calls, call recording)
  %(prog)s --extensions 200 --concurrent-calls 50 --recording

  # Large enterprise (1000 users, 200 concurrent calls)
  %(prog)s --extensions 1000 --concurrent-calls 200 --recording --calls-per-day 1000

  # JSON output
  %(prog)s --extensions 100 --concurrent-calls 25 --format json
        """,
    )

    parser.add_argument(
        "--extensions", type=int, required=True, help="Number of extensions"
    )
    parser.add_argument(
        "--concurrent-calls",
        type=int,
        required=True,
        help="Peak concurrent calls",
    )
    parser.add_argument(
        "--avg-call-duration",
        type=int,
        default=5,
        help="Average call duration in minutes (default: 5)",
    )
    parser.add_argument(
        "--calls-per-day",
        type=int,
        default=100,
        help="Average calls per day (default: 100)",
    )
    parser.add_argument(
        "--recording",
        action="store_true",
        help="Enable call recording",
    )
    parser.add_argument(
        "--recording-retention-days",
        type=int,
        default=90,
        help="Call recording retention in days (default: 90)",
    )
    parser.add_argument(
        "--voicemail-users-percent",
        type=int,
        default=80,
        help="Percentage of users using voicemail (default: 80)",
    )
    parser.add_argument(
        "--log-retention-days",
        type=int,
        default=30,
        help="Log retention in days (default: 30)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    calculator = CapacityCalculator()
    requirements = calculator.calculate(
        extensions=args.extensions,
        concurrent_calls=args.concurrent_calls,
        avg_call_duration_min=args.avg_call_duration,
        calls_per_day=args.calls_per_day,
        recording_enabled=args.recording,
        recording_retention_days=args.recording_retention_days,
        voicemail_users_percent=args.voicemail_users_percent,
        log_retention_days=args.log_retention_days,
    )

    calculator.print_report(requirements, format=args.format)

    return 0


if __name__ == "__main__":
    sys.exit(main())
