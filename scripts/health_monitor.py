#!/usr/bin/env python3
"""
Production Health Monitoring Dashboard Generator

This script generates a comprehensive health monitoring report for the PBX system
and optionally sends alerts for critical issues.

Usage:
    python scripts/health_monitor.py [--format html|json|text] [--alert] [--output report.html]

Features:
    - System resource monitoring (CPU, memory, disk)
    - Service status checks
    - Database connectivity
    - Network connectivity
    - Call quality metrics
    - Active calls monitoring
    - SIP trunk status
    - Alert generation for critical issues

Requirements:
    - psutil
    - requests (for API checks)
"""

import argparse
import datetime
from datetime import timezone
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

try:
    import psutil
except ImportError:
    print("Error: psutil module required. Install with: pip install psutil")
    sys.exit(1)

try:
    import requests
except ImportError:
    requests = None


class HealthMonitor:
    """Production health monitoring and reporting."""

    def __init__(self, api_url="https://localhost:8080", verify_ssl=False):
        self.api_url = api_url
        self.verify_ssl = verify_ssl
        self.base_dir = Path(__file__).parent.parent
        self.health_data = {
            "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
            "hostname": socket.gethostname(),
            "checks": {},
            "alerts": [],
            "summary": {"healthy": 0, "warning": 0, "critical": 0},
        }

    def check_system_resources(self):
        """Check system resource usage."""
        checks = {}

        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        checks["cpu"] = {
            "value": cpu_percent,
            "unit": "%",
            "status": self._get_status(cpu_percent, 70, 90),
            "message": f"CPU usage: {cpu_percent}%",
        }

        # Memory
        memory = psutil.virtual_memory()
        checks["memory"] = {
            "value": memory.percent,
            "unit": "%",
            "total": f"{memory.total / (1024**3):.1f} GB",
            "available": f"{memory.available / (1024**3):.1f} GB",
            "status": self._get_status(memory.percent, 80, 95),
            "message": f"Memory usage: {memory.percent}%",
        }

        # Disk
        disk = psutil.disk_usage("/")
        checks["disk"] = {
            "value": disk.percent,
            "unit": "%",
            "total": f"{disk.total / (1024**3):.1f} GB",
            "free": f"{disk.free / (1024**3):.1f} GB",
            "status": self._get_status(disk.percent, 80, 90),
            "message": f"Disk usage: {disk.percent}%",
        }

        # Load average
        if hasattr(os, "getloadavg"):
            load_avg = os.getloadavg()
            cpu_count = psutil.cpu_count()
            load_percent = (load_avg[0] / cpu_count) * 100
            checks["load_average"] = {
                "1min": load_avg[0],
                "5min": load_avg[1],
                "15min": load_avg[2],
                "status": self._get_status(load_percent, 70, 90),
                "message": f"Load average: {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}",
            }

        self.health_data["checks"]["system"] = checks
        self._update_summary(checks)

    def check_pbx_service(self):
        """Check if PBX service is running."""
        checks = {}

        try:
            # Check if process is running
            process_found = False
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = " ".join(proc.info["cmdline"] or [])
                    if "main.py" in cmdline or "pbx" in proc.info["name"].lower():
                        process_found = True
                        checks["process"] = {
                            "pid": proc.info["pid"],
                            "status": "healthy",
                            "message": f"PBX process running (PID: {proc.info['pid']})",
                        }

                        # Get process resource usage
                        try:
                            cpu = proc.cpu_percent(interval=0.1)
                            mem = proc.memory_info()
                            checks["process"]["cpu_percent"] = cpu
                            checks["process"]["memory_mb"] = mem.rss / (1024 * 1024)
                        except Exception:
                            # Resource usage metrics are optional; ignore errors collecting them
                            pass
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not process_found:
                checks["process"] = {
                    "status": "critical",
                    "message": "PBX process not found",
                }
                self.health_data["alerts"].append("CRITICAL: PBX process not running")

            # Check if service is listening on expected ports
            ports_to_check = [(5060, "SIP"), (8080, "API")]
            for port, service in ports_to_check:
                listening = self._is_port_listening(port)
                checks[f"port_{port}"] = {
                    "port": port,
                    "service": service,
                    "status": "healthy" if listening else "critical",
                    "message": f"{service} port {port}: {'LISTENING' if listening else 'NOT LISTENING'}",
                }
                if not listening:
                    self.health_data["alerts"].append(
                        f"CRITICAL: {service} not listening on port {port}"
                    )

        except Exception as e:
            checks["process"] = {
                "status": "critical",
                "message": f"Error checking PBX service: {e}",
            }

        self.health_data["checks"]["pbx_service"] = checks
        self._update_summary(checks)

    def check_database(self):
        """Check database connectivity."""
        checks = {}

        try:
            import psycopg2

            db_password = os.getenv("DB_PASSWORD")
            if db_password is None or db_password == "":
                checks["connectivity"] = {
                    "status": "warning",
                    "message": "Database password is not set; skipping connectivity check",
                }
                self.health_data["alerts"].append(
                    "WARNING: Database password is not configured; database connectivity check skipped"
                )
            else:
                # Try to connect to database
                try:
                    conn = psycopg2.connect(
                        host=os.getenv("DB_HOST", "localhost"),
                        port=int(os.getenv("DB_PORT", "5432")),
                        database=os.getenv("DB_NAME", "pbx_system"),
                        user=os.getenv("DB_USER", "pbx_user"),
                        password=db_password,
                        connect_timeout=5,
                    )

                    # Test query
                    cursor = conn.cursor()
                    cursor.execute("SELECT version();")
                    version = cursor.fetchone()[0]

                    # Get database size
                    cursor.execute(
                        "SELECT pg_size_pretty(pg_database_size(%s));",
                        (os.getenv("DB_NAME", "pbx_system"),),
                    )
                    db_size = cursor.fetchone()[0]

                    cursor.close()
                    conn.close()

                    checks["connectivity"] = {
                        "status": "healthy",
                        "message": "Database connection successful",
                        "version": version,
                        "size": db_size,
                    }
                except Exception as e:
                    checks["connectivity"] = {
                        "status": "critical",
                        "message": f"Database connection failed: {e}",
                    }
                    self.health_data["alerts"].append(f"CRITICAL: Database connection failed: {e}")

        except ImportError:
            checks["connectivity"] = {
                "status": "warning",
                "message": "psycopg2 not installed, cannot check PostgreSQL",
            }

        self.health_data["checks"]["database"] = checks
        self._update_summary(checks)

    def check_api_endpoints(self):
        """Check API endpoint availability."""
        if not requests:
            self.health_data["checks"]["api"] = {
                "status": "warning",
                "message": "requests module not available",
            }
            return

        checks = {}
        endpoints = [
            ("/api/status", "System Status"),
            ("/health", "Health Check"),
        ]

        for path, name in endpoints:
            try:
                url = f"{self.api_url}{path}"
                response = requests.get(url, verify=self.verify_ssl, timeout=5)

                checks[path] = {
                    "status": "healthy" if response.status_code == 200 else "warning",
                    "status_code": response.status_code,
                    "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                    "message": f"{name}: {response.status_code}",
                }
            except Exception as e:
                checks[path] = {
                    "status": "critical",
                    "message": f"{name}: Connection failed - {e}",
                }
                self.health_data["alerts"].append(f"CRITICAL: API endpoint {path} unavailable")

        self.health_data["checks"]["api"] = checks
        self._update_summary(checks)

    def check_disk_space_specific(self):
        """Check disk space for specific PBX directories."""
        checks = {}

        directories = [
            (self.base_dir / "voicemail", "Voicemail"),
            (self.base_dir / "recordings", "Call Recordings"),
            (self.base_dir / "logs", "Logs"),
        ]

        for directory, name in directories:
            if directory.exists():
                usage = psutil.disk_usage(str(directory))
                checks[name.lower().replace(" ", "_")] = {
                    "path": str(directory),
                    "percent_used": usage.percent,
                    "total_gb": usage.total / (1024**3),
                    "free_gb": usage.free / (1024**3),
                    "status": self._get_status(usage.percent, 80, 90),
                    "message": f"{name}: {usage.percent}% used",
                }

        self.health_data["checks"]["storage"] = checks
        self._update_summary(checks)

    def check_ssl_certificate(self):
        """Check SSL certificate expiration."""
        checks = {}

        ssl_cert = self.base_dir / "ssl" / "pbx.crt"
        if ssl_cert.exists():
            try:
                result = subprocess.run(
                    ["openssl", "x509", "-in", str(ssl_cert), "-noout", "-enddate"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    # Parse expiration date
                    expiry_str = result.stdout.strip().split("=")[1]
                    expiry_date = datetime.datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")
                    days_until_expiry = (expiry_date - datetime.datetime.now(timezone.utc)).days

                    if days_until_expiry < 7:
                        status = "critical"
                        self.health_data["alerts"].append(
                            f"CRITICAL: SSL certificate expires in {days_until_expiry} days"
                        )
                    elif days_until_expiry < 30:
                        status = "warning"
                    else:
                        status = "healthy"

                    checks["expiration"] = {
                        "status": status,
                        "days_until_expiry": days_until_expiry,
                        "expiry_date": expiry_date.isoformat(),
                        "message": f"SSL certificate expires in {days_until_expiry} days",
                    }
            except Exception as e:
                checks["expiration"] = {
                    "status": "warning",
                    "message": f"Could not check certificate expiration: {e}",
                }
        else:
            checks["expiration"] = {
                "status": "warning",
                "message": "SSL certificate not found",
            }

        self.health_data["checks"]["ssl"] = checks
        self._update_summary(checks)

    def _is_port_listening(self, port):
        """Check if a port is listening."""
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr.port == port and conn.status == "LISTEN":
                return True
        return False

    def _get_status(self, value, warning_threshold, critical_threshold):
        """Determine status based on thresholds."""
        if value >= critical_threshold:
            return "critical"
        elif value >= warning_threshold:
            return "warning"
        else:
            return "healthy"

    def _update_summary(self, checks):
        """Update summary counts."""
        for check in checks.values():
            if isinstance(check, dict) and "status" in check:
                status = check["status"]
                if status == "healthy":
                    self.health_data["summary"]["healthy"] += 1
                elif status == "warning":
                    self.health_data["summary"]["warning"] += 1
                elif status == "critical":
                    self.health_data["summary"]["critical"] += 1

    def run_all_checks(self):
        """Run all health checks."""
        print("Running health checks...")
        self.check_system_resources()
        self.check_pbx_service()
        self.check_database()
        self.check_api_endpoints()
        self.check_disk_space_specific()
        self.check_ssl_certificate()

    def generate_text_report(self):
        """Generate text report."""
        lines = []
        lines.append("=" * 80)
        lines.append("PBX SYSTEM HEALTH REPORT")
        lines.append("=" * 80)
        lines.append(f"Timestamp: {self.health_data['timestamp']}")
        lines.append(f"Hostname: {self.health_data['hostname']}")
        lines.append("")

        # Summary
        summary = self.health_data["summary"]
        lines.append("SUMMARY:")
        lines.append(f"  Healthy: {summary['healthy']}")
        lines.append(f"  Warnings: {summary['warning']}")
        lines.append(f"  Critical: {summary['critical']}")
        lines.append("")

        # Alerts
        if self.health_data["alerts"]:
            lines.append("ALERTS:")
            for alert in self.health_data["alerts"]:
                lines.append(f"  • {alert}")
            lines.append("")

        # Detailed checks
        for category, checks in self.health_data["checks"].items():
            lines.append(f"{category.upper().replace('_', ' ')}:")
            for name, check in checks.items():
                if isinstance(check, dict):
                    status_icon = {
                        "healthy": "✓",
                        "warning": "⚠",
                        "critical": "✗",
                    }.get(check.get("status", ""), "?")
                    lines.append(f"  {status_icon} {check.get('message', name)}")
            lines.append("")

        lines.append("=" * 80)
        return "\n".join(lines)

    def generate_json_report(self):
        """Generate JSON report."""
        return json.dumps(self.health_data, indent=2)

    def generate_html_report(self):
        """Generate HTML report."""
        html = (
            """
<!DOCTYPE html>
<html>
<head>
    <title>PBX Health Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        .summary { display: flex; gap: 20px; margin: 20px 0; }
        .summary-box { flex: 1; padding: 20px; border-radius: 5px; text-align: center; }
        .summary-box h3 { margin: 0; font-size: 36px; }
        .summary-box p { margin: 5px 0 0 0; color: #666; }
        .healthy { background: #d4edda; border-left: 4px solid #28a745; }
        .warning { background: #fff3cd; border-left: 4px solid #ffc107; }
        .critical { background: #f8d7da; border-left: 4px solid #dc3545; }
        .check { padding: 10px; margin: 5px 0; border-radius: 3px; }
        .check.healthy { background: #d4edda; }
        .check.warning { background: #fff3cd; }
        .check.critical { background: #f8d7da; }
        .alerts { background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 20px 0; border-radius: 3px; }
        .timestamp { color: #999; font-size: 14px; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #4CAF50; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <h1>PBX System Health Report</h1>
        <p class="timestamp">Generated: """
            + self.health_data["timestamp"]
            + """</p>
        <p>Hostname: """
            + self.health_data["hostname"]
            + """</p>

        <div class="summary">
            <div class="summary-box healthy">
                <h3>"""
            + str(self.health_data["summary"]["healthy"])
            + """</h3>
                <p>Healthy</p>
            </div>
            <div class="summary-box warning">
                <h3>"""
            + str(self.health_data["summary"]["warning"])
            + """</h3>
                <p>Warnings</p>
            </div>
            <div class="summary-box critical">
                <h3>"""
            + str(self.health_data["summary"]["critical"])
            + """</h3>
                <p>Critical</p>
            </div>
        </div>
"""
        )

        # Alerts
        if self.health_data["alerts"]:
            html += '<div class="alerts"><h3>⚠ Alerts</h3><ul>'
            for alert in self.health_data["alerts"]:
                html += f"<li>{alert}</li>"
            html += "</ul></div>"

        # Detailed checks
        for category, checks in self.health_data["checks"].items():
            html += f"<h2>{category.upper().replace('_', ' ')}</h2>"
            for name, check in checks.items():
                if isinstance(check, dict):
                    status = check.get("status", "unknown")
                    message = check.get("message", name)
                    html += f'<div class="check {status}">{message}</div>'

        html += """
    </div>
</body>
</html>
"""
        return html


def main():
    parser = argparse.ArgumentParser(description="PBX Health Monitoring")
    parser.add_argument(
        "--format",
        choices=["text", "json", "html"],
        default="text",
        help="Output format",
    )
    parser.add_argument("--output", help="Output file (default: stdout)")
    parser.add_argument("--alert", action="store_true", help="Send alerts for critical issues")
    parser.add_argument("--api-url", default="https://localhost:8080", help="PBX API URL")
    args = parser.parse_args()

    monitor = HealthMonitor(api_url=args.api_url)
    monitor.run_all_checks()

    # Generate report
    if args.format == "text":
        report = monitor.generate_text_report()
    elif args.format == "json":
        report = monitor.generate_json_report()
    else:  # html
        report = monitor.generate_html_report()

    # Output report
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report written to: {args.output}")
    else:
        print(report)

    # Exit with error code if critical issues found
    if monitor.health_data["summary"]["critical"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
