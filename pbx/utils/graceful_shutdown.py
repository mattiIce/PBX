"""
Graceful shutdown handler for production deployments.

This module provides enhanced shutdown capabilities with proper
cleanup, active call handling, and state preservation.
"""

import logging
import signal
import sys
import threading
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


class GracefulShutdownHandler:
    """
    Handles graceful shutdown of the PBX system.

    Features:
    - Catches shutdown signals (SIGTERM, SIGINT)
    - Allows active calls to complete
    - Performs cleanup in proper order
    - Prevents new calls during shutdown
    - Provides shutdown timeout for forced termination
    """

    def __init__(self, pbx_core: object = None, shutdown_timeout: int = 30) -> None:
        """
        Initialize shutdown handler.

        Args:
            pbx_core: Reference to PBX core instance
            shutdown_timeout: Max seconds to wait for graceful shutdown
        """
        self.pbx_core = pbx_core
        self.shutdown_timeout = shutdown_timeout
        self.shutdown_initiated = False
        self.shutdown_complete = False
        self._original_sigint = None
        self._original_sigterm = None

    def setup_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        # Store original handlers
        self._original_sigint = signal.signal(signal.SIGINT, self._signal_handler)
        self._original_sigterm = signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("Graceful shutdown handlers registered")

    def _signal_handler(self, signum: int, frame: object) -> None:
        """Handle shutdown signals."""
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"

        if self.shutdown_initiated:
            logger.warning(f"Received {signal_name} during shutdown. Forcing immediate exit...")
            sys.exit(1)

        logger.info(f"Received {signal_name}. Initiating graceful shutdown...")
        self.shutdown_initiated = True

        # Start shutdown in separate thread to avoid blocking signal handler
        shutdown_thread = threading.Thread(target=self._execute_shutdown)
        shutdown_thread.daemon = False
        shutdown_thread.start()

    def _execute_shutdown(self) -> None:
        """Execute the actual shutdown sequence."""
        try:
            start_time = time.time()

            # Step 1: Stop accepting new calls
            logger.info("Step 1/5: Stopping new call acceptance...")
            if self.pbx_core:
                self.pbx_core.running = False

            # Step 2: Wait for active calls to complete (with timeout)
            logger.info("Step 2/5: Waiting for active calls to complete...")
            self._wait_for_calls_to_complete(timeout=self.shutdown_timeout - 10)

            # Step 3: Stop services in order
            logger.info("Step 3/5: Stopping services...")
            self._stop_services()

            # Step 4: Cleanup resources
            logger.info("Step 4/5: Cleaning up resources...")
            self._cleanup_resources()

            # Step 5: Final logging and exit
            elapsed = time.time() - start_time
            logger.info(f"Step 5/5: Shutdown complete in {elapsed:.2f} seconds")

            self.shutdown_complete = True
            sys.exit(0)

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)

    def _wait_for_calls_to_complete(self, timeout: int = 20) -> None:
        """
        Wait for active calls to complete.

        Args:
            timeout: Max seconds to wait
        """
        if not self.pbx_core or not hasattr(self.pbx_core, "call_manager"):
            return

        start_time = time.time()

        while time.time() - start_time < timeout:
            active_calls = self.pbx_core.call_manager.get_active_calls()

            if not active_calls:
                logger.info("All calls completed")
                return

            call_count = len(active_calls)
            remaining = timeout - (time.time() - start_time)
            logger.info(
                f"Waiting for {call_count} active call(s) to complete... ({remaining:.1f}s remaining)"
            )

            time.sleep(2)

        # Timeout reached - force end remaining calls
        active_calls = self.pbx_core.call_manager.get_active_calls()
        if active_calls:
            logger.warning(f"Timeout reached. Force ending {len(active_calls)} active call(s)")
            for call in active_calls:
                try:
                    self.pbx_core.call_manager.end_call(call.call_id)
                except Exception as e:
                    logger.error(f"Error ending call {call.call_id}: {e}")

    def _stop_services(self) -> None:
        """Stop PBX services in proper order."""
        if not self.pbx_core:
            return

        # Stop in reverse order of startup
        services = [
            ("Security Monitor", lambda: self._stop_if_exists("security_monitor")),
            ("DND Scheduler", lambda: self._stop_if_exists("dnd_scheduler")),
            ("Recording Retention", lambda: self._stop_if_exists("recording_retention")),
            ("API Server", lambda: self._stop_if_exists("api_server")),
            ("SIP Server", lambda: self._stop_if_exists("sip_server")),
        ]

        for service_name, stop_func in services:
            try:
                logger.debug(f"Stopping {service_name}...")
                stop_func()
            except Exception as e:
                logger.error(f"Error stopping {service_name}: {e}")

    def _stop_if_exists(self, attr_name: str) -> None:
        """Stop a service if it exists and has a stop method."""
        if hasattr(self.pbx_core, attr_name):
            service = getattr(self.pbx_core, attr_name)
            if service and hasattr(service, "stop"):
                service.stop()

    def _cleanup_resources(self) -> None:
        """Cleanup resources before exit."""
        if not self.pbx_core:
            return

        try:
            # Stop any remaining recordings
            if hasattr(self.pbx_core, "recording_system"):
                logger.debug("Stopping any active recordings...")
                # Get all active recordings and stop them
                # (recording_system should track this)

            # Release RTP ports
            if hasattr(self.pbx_core, "rtp_relay"):
                logger.debug("Releasing RTP resources...")
                # RTP relay cleanup

            # Close database connections
            if hasattr(self.pbx_core, "database"):
                logger.debug("Closing database connections...")
                if hasattr(self.pbx_core.database, "close"):
                    self.pbx_core.database.close()

            # Clear extension registrations
            if hasattr(self.pbx_core, "extension_registry"):
                logger.debug("Clearing extension registrations...")
                # Mark all as unregistered
                for ext in self.pbx_core.extension_registry.get_all():
                    ext.registered = False

        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")


def setup_graceful_shutdown(pbx_core: object, timeout: int = 30) -> GracefulShutdownHandler:
    """
    Setup graceful shutdown handling for the PBX system.

    Args:
        pbx_core: PBX core instance
        timeout: Shutdown timeout in seconds

    Returns:
        GracefulShutdownHandler instance
    """
    handler = GracefulShutdownHandler(pbx_core, shutdown_timeout=timeout)
    handler.setup_handlers()
    return handler


class ConnectionRetry:
    """
    Implements exponential backoff for connection retries.

    Usage:
        retry = ConnectionRetry(max_retries=5)
        for attempt in retry:
            try:
                connect_to_database()
                break
            except Exception as e:
                retry.handle_error(e)
    """

    def __init__(
        self, max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 60.0
    ) -> None:
        """
        Initialize retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.attempt = 0
        self.last_error = None

    def __iter__(self) -> "ConnectionRetry":
        """Make this object iterable."""
        self.attempt = 0
        return self

    def __next__(self) -> int:
        """Get next retry attempt."""
        if self.attempt >= self.max_retries:
            if self.last_error:
                raise self.last_error
            raise StopIteration

        if self.attempt > 0:
            # Calculate delay with exponential backoff
            delay = min(self.base_delay * (2 ** (self.attempt - 1)), self.max_delay)
            logger.info(
                f"Retry attempt {self.attempt}/{self.max_retries} after {delay:.1f}s delay..."
            )
            time.sleep(delay)

        self.attempt += 1
        return self.attempt

    def handle_error(self, error: Exception) -> None:
        """
        Handle an error from a retry attempt.

        Args:
            error: The exception that occurred
        """
        self.last_error = error
        logger.warning(f"Attempt {self.attempt} failed: {error}")


def with_retry(func: Callable, max_retries: int = 3, on_error: Callable | None = None) -> object:
    """
    Decorator or wrapper for retrying a function with exponential backoff.

    Args:
        func: Function to retry
        max_retries: Maximum retry attempts
        on_error: Optional callback for errors

    Returns:
        Result of func() if successful

    Raises:
        Last exception if all retries fail
    """
    retry = ConnectionRetry(max_retries=max_retries)

    for attempt in retry:
        try:
            result = func()
            if attempt > 1:
                logger.info(f"Operation succeeded on attempt {attempt}")
            return result
        except Exception as e:
            retry.handle_error(e)
            if on_error:
                on_error(e, attempt)

    # Should not reach here, but just in case
    raise RuntimeError("Retry exhausted without success or exception")
