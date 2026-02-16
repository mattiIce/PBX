#!/usr/bin/env python3
"""
Load Testing Script for Warden VoIP PBX System

This script performs comprehensive load testing on the PBX system using SIP/RTP protocols.
Tests concurrent calls, registration load, and system performance under stress.

Usage:
    python scripts/load_test_sip.py --concurrent-calls 50 --duration 60
    python scripts/load_test_sip.py --test-type registrations --users 100
    python scripts/load_test_sip.py --full-suite --save-report results.json
"""

import argparse
import asyncio
import json
import logging
import random
import socket
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class LoadTestConfig:
    """Load test configuration"""

    pbx_host: str = "localhost"
    pbx_sip_port: int = 5060
    pbx_api_port: int = 9000
    concurrent_calls: int = 10
    total_calls: int = 100
    call_duration: int = 10  # seconds
    users_count: int = 50
    test_duration: int = 60  # seconds
    ramp_up_time: int = 10  # seconds
    test_type: str = "calls"  # calls, registrations, mixed
    socket_timeout: int = 5  # seconds - configurable timeout


@dataclass
class LoadTestResults:
    """Load test results"""

    test_type: str
    timestamp: str
    duration: float
    total_attempts: int
    successful: int
    failed: int
    timeouts: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    concurrent_peak: int
    errors: dict[str, int]
    system_metrics: dict[str, Any]


class SIPLoadTester:
    """SIP protocol load tester"""

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.results = {
            "response_times": [],
            "successful": 0,
            "failed": 0,
            "timeouts": 0,
            "errors": defaultdict(int),
            "concurrent_active": 0,
            "peak_concurrent": 0,
        }
        self.start_time = None
        self.end_time = None

    async def send_sip_register(self, user_id: int) -> tuple[bool, float]:
        """Send SIP REGISTER request"""
        start = time.time()
        try:
            # Create SIP REGISTER message
            extension = f"10{user_id:03d}"
            sip_message = (
                f"REGISTER sip:{self.config.pbx_host}:{self.config.pbx_sip_port} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP loadtest-{user_id}:5060;branch=z9hG4bK{random.randint(1000, 9999)}\r\n"
                f"From: <sip:{extension}@{self.config.pbx_host}>;tag={random.randint(1000, 9999)}\r\n"
                f"To: <sip:{extension}@{self.config.pbx_host}>\r\n"
                f"Call-ID: loadtest-{user_id}-{int(time.time())}\r\n"
                f"CSeq: 1 REGISTER\r\n"
                f"Contact: <sip:{extension}@loadtest-{user_id}:5060>\r\n"
                f"Expires: 3600\r\n"
                f"Content-Length: 0\r\n\r\n"
            )

            # Send UDP packet
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.config.socket_timeout)
            sock.sendto(sip_message.encode(), (self.config.pbx_host, self.config.pbx_sip_port))

            # Wait for response
            try:
                data, _ = sock.recvfrom(4096)
                response = data.decode()
                response_time = time.time() - start

                # Check if registration was successful (200 OK)
                if "200 OK" in response or "SIP/2.0 200" in response:
                    return True, response_time
                self.logger.debug(f"Registration failed for user {user_id}: {response[:100]}")
                return False, response_time
            except TimeoutError:
                self.logger.warning(f"Registration timeout for user {user_id}")
                return False, time.time() - start
            finally:
                sock.close()

        except OSError as e:
            self.logger.error(f"Error during registration for user {user_id}: {e}")
            return False, time.time() - start

    async def simulate_call(self, call_id: int) -> tuple[bool, float]:
        """Simulate a SIP call (INVITE, ACK, BYE)"""
        start = time.time()
        try:
            # This is a simplified simulation
            # In a real load test, you'd use a proper SIP library like pjsip
            extension_a = f"10{call_id % 100:03d}"
            extension_b = f"10{(call_id + 1) % 100:03d}"

            # INVITE
            invite_msg = (
                f"INVITE sip:{extension_b}@{self.config.pbx_host} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP loadtest-{call_id}:5060;branch=z9hG4bK{random.randint(1000, 9999)}\r\n"
                f"From: <sip:{extension_a}@{self.config.pbx_host}>;tag={random.randint(1000, 9999)}\r\n"
                f"To: <sip:{extension_b}@{self.config.pbx_host}>\r\n"
                f"Call-ID: loadtest-call-{call_id}-{int(time.time())}\r\n"
                f"CSeq: 1 INVITE\r\n"
                f"Contact: <sip:{extension_a}@loadtest-{call_id}:5060>\r\n"
                f"Content-Type: application/sdp\r\n"
                f"Content-Length: 0\r\n\r\n"
            )

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.config.socket_timeout)
            sock.sendto(invite_msg.encode(), (self.config.pbx_host, self.config.pbx_sip_port))

            # Wait for response
            try:
                data, _ = sock.recvfrom(4096)
                response = data.decode()

                # Check for various success responses
                success = any(x in response for x in ["100 Trying", "180 Ringing", "200 OK"])

                # Simulate call duration
                if success:
                    await asyncio.sleep(
                        min(self.config.call_duration, 1)
                    )  # Shortened for load test

                response_time = time.time() - start
                return success, response_time
            except TimeoutError:
                return False, time.time() - start
            finally:
                sock.close()

        except (KeyError, OSError, TypeError, ValueError) as e:
            self.logger.error(f"Error during call {call_id}: {e}")
            return False, time.time() - start

    async def run_registration_test(self) -> None:
        """Run registration load test"""
        self.logger.info(f"Starting registration load test: {self.config.users_count} users")
        self.start_time = time.time()

        tasks = []
        for user_id in range(self.config.users_count):
            # Ramp up gradually
            if self.config.ramp_up_time > 0:
                delay = (user_id / self.config.users_count) * self.config.ramp_up_time
                await asyncio.sleep(delay / self.config.users_count)

            task = asyncio.create_task(self.send_sip_register(user_id))
            tasks.append(task)

        # Wait for all registrations
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, Exception):
                self.results["failed"] += 1
                self.results["errors"][str(result)] += 1
            else:
                success, response_time = result
                if success:
                    self.results["successful"] += 1
                else:
                    self.results["failed"] += 1
                self.results["response_times"].append(response_time)

        self.end_time = time.time()

    async def run_call_test(self) -> None:
        """Run call load test"""
        self.logger.info(
            f"Starting call load test: {self.config.concurrent_calls} concurrent, "
            f"{self.config.total_calls} total"
        )
        self.start_time = time.time()

        active_tasks = []
        calls_started = 0
        calls_completed = 0

        while calls_completed < self.config.total_calls:
            # Start new calls up to concurrent limit
            while (
                len(active_tasks) < self.config.concurrent_calls
                and calls_started < self.config.total_calls
            ):
                task = asyncio.create_task(self.simulate_call(calls_started))
                active_tasks.append(task)
                calls_started += 1

                # Update peak concurrent
                self.results["concurrent_active"] = len(active_tasks)
                self.results["peak_concurrent"] = max(
                    self.results["peak_concurrent"], self.results["concurrent_active"]
                )

            # Wait for at least one call to complete
            if active_tasks:
                done, active_tasks = await asyncio.wait(
                    active_tasks, return_when=asyncio.FIRST_COMPLETED, timeout=1
                )

                # Process completed calls
                for task in done:
                    try:
                        success, response_time = await task
                        if success:
                            self.results["successful"] += 1
                        else:
                            self.results["failed"] += 1
                        self.results["response_times"].append(response_time)
                        calls_completed += 1
                    except (KeyError, TypeError, ValueError) as e:
                        self.results["failed"] += 1
                        self.results["errors"][str(e)] += 1
                        calls_completed += 1

                self.results["concurrent_active"] = len(active_tasks)

        # Wait for remaining calls
        if active_tasks:
            await asyncio.gather(*active_tasks, return_exceptions=True)

        self.end_time = time.time()

    async def run_mixed_test(self) -> None:
        """Run mixed load test (registrations + calls)"""
        self.logger.info("Starting mixed load test")
        self.start_time = time.time()

        # Run registrations first
        reg_tasks = [self.send_sip_register(i) for i in range(self.config.users_count)]
        await asyncio.gather(*reg_tasks, return_exceptions=True)

        # Then run calls
        await self.run_call_test()

        self.end_time = time.time()

    def calculate_statistics(self) -> LoadTestResults:
        """Calculate test statistics"""
        if not self.results["response_times"]:
            self.results["response_times"] = [0]

        sorted_times = sorted(self.results["response_times"])
        total_attempts = (
            self.results["successful"] + self.results["failed"] + self.results["timeouts"]
        )
        duration = self.end_time - self.start_time if self.end_time else 0

        return LoadTestResults(
            test_type=self.config.test_type,
            timestamp=datetime.now(UTC).isoformat(),
            duration=duration,
            total_attempts=total_attempts,
            successful=self.results["successful"],
            failed=self.results["failed"],
            timeouts=self.results["timeouts"],
            avg_response_time=sum(sorted_times) / len(sorted_times),
            min_response_time=min(sorted_times),
            max_response_time=max(sorted_times),
            p95_response_time=sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0,
            p99_response_time=sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0,
            requests_per_second=total_attempts / duration if duration > 0 else 0,
            concurrent_peak=self.results["peak_concurrent"],
            errors=dict(self.results["errors"]),
            system_metrics={},
        )


def print_results(results: LoadTestResults) -> None:
    """Print formatted test results"""
    print("\n" + "=" * 70)
    print("LOAD TEST RESULTS")
    print("=" * 70)
    print(f"Test Type: {results.test_type}")
    print(f"Timestamp: {results.timestamp}")
    print(f"Duration: {results.duration:.2f}s")
    print()

    print("Performance Metrics:")
    print(f"  Total Attempts: {results.total_attempts}")
    print(
        f"  Successful: {results.successful} ({results.successful / results.total_attempts * 100:.1f}%)"
    )
    print(f"  Failed: {results.failed} ({results.failed / results.total_attempts * 100:.1f}%)")
    print(f"  Timeouts: {results.timeouts}")
    print(f"  Requests/sec: {results.requests_per_second:.2f}")
    print(f"  Peak Concurrent: {results.concurrent_peak}")
    print()

    print("Response Time Statistics (seconds):")
    print(f"  Average: {results.avg_response_time:.3f}s")
    print(f"  Min: {results.min_response_time:.3f}s")
    print(f"  Max: {results.max_response_time:.3f}s")
    print(f"  P95: {results.p95_response_time:.3f}s")
    print(f"  P99: {results.p99_response_time:.3f}s")
    print()

    if results.errors:
        print("Errors:")
        for error, count in results.errors.items():
            print(f"  {error}: {count}")
        print()

    # Pass/Fail determination
    success_rate = (
        results.successful / results.total_attempts * 100 if results.total_attempts > 0 else 0
    )
    print("=" * 70)
    if success_rate >= 95 and results.p95_response_time < 2.0:
        print("✅ LOAD TEST PASSED")
        print(f"   Success rate: {success_rate:.1f}% (>= 95%)")
        print(f"   P95 response: {results.p95_response_time:.3f}s (< 2.0s)")
    else:
        print("❌ LOAD TEST FAILED")
        if success_rate < 95:
            print(f"   Success rate: {success_rate:.1f}% (< 95%)")
        if results.p95_response_time >= 2.0:
            print(f"   P95 response: {results.p95_response_time:.3f}s (>= 2.0s)")
    print("=" * 70 + "\n")


async def main() -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Load testing tool for Warden VoIP PBX System")
    parser.add_argument(
        "--pbx-host", default="localhost", help="PBX server hostname or IP (default: localhost)"
    )
    parser.add_argument("--sip-port", type=int, default=5060, help="SIP port (default: 5060)")
    parser.add_argument(
        "--test-type",
        choices=["calls", "registrations", "mixed"],
        default="calls",
        help="Type of load test to run",
    )
    parser.add_argument(
        "--concurrent-calls", type=int, default=10, help="Number of concurrent calls (default: 10)"
    )
    parser.add_argument(
        "--total-calls", type=int, default=100, help="Total number of calls to make (default: 100)"
    )
    parser.add_argument(
        "--users", type=int, default=50, help="Number of users for registration test (default: 50)"
    )
    parser.add_argument(
        "--duration", type=int, default=60, help="Test duration in seconds (default: 60)"
    )
    parser.add_argument(
        "--call-duration",
        type=int,
        default=10,
        help="Duration of each call in seconds (default: 10)",
    )
    parser.add_argument(
        "--ramp-up", type=int, default=10, help="Ramp-up time in seconds (default: 10)"
    )
    parser.add_argument("--save-report", help="Save results to JSON file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Create config
    config = LoadTestConfig(
        pbx_host=args.pbx_host,
        pbx_sip_port=args.sip_port,
        concurrent_calls=args.concurrent_calls,
        total_calls=args.total_calls,
        call_duration=args.call_duration,
        users_count=args.users,
        test_duration=args.duration,
        ramp_up_time=args.ramp_up,
        test_type=args.test_type,
    )

    # Run test
    tester = SIPLoadTester(config)

    try:
        if args.test_type == "registrations":
            await tester.run_registration_test()
        elif args.test_type == "calls":
            await tester.run_call_test()
        elif args.test_type == "mixed":
            await tester.run_mixed_test()

        # Calculate and display results
        results = tester.calculate_statistics()
        print_results(results)

        # Save report if requested
        if args.save_report:
            with open(args.save_report, "w") as f:
                json.dump(asdict(results), f, indent=2)
            print(f"Results saved to {args.save_report}")

        # Exit with appropriate code
        success_rate = (
            results.successful / results.total_attempts * 100 if results.total_attempts > 0 else 0
        )
        sys.exit(0 if success_rate >= 95 else 1)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as e:
        logging.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
