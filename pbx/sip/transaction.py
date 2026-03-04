"""
SIP INVITE client transaction with retransmission (RFC 3261 Section 17.1.1).

Handles Timer A (retransmission with exponential backoff) and Timer B
(transaction timeout) for INVITE requests sent over UDP.
"""

import threading
from collections.abc import Callable

from pbx.utils.logger import get_logger

# RFC 3261 timer constants
T1 = 0.5  # 500ms - RTT estimate
T2 = 4.0  # 4s - maximum retransmit interval
TIMER_B = 32.0  # 32s - INVITE transaction timeout


class InviteClientTransaction:
    """
    Manages INVITE retransmission for a single outbound transaction.

    Sends the initial INVITE immediately, then retransmits with exponential
    backoff: T1, 2*T1, 4*T1, ... up to T2.  Timer B terminates the
    transaction if no response arrives within 32 seconds.
    """

    def __init__(
        self,
        message: str,
        dest_addr: tuple[str, int],
        send_fn: Callable[[str, tuple[str, int]], None],
        on_timeout: Callable[[], None] | None = None,
    ) -> None:
        """
        Initialize the INVITE client transaction.

        Args:
            message: The serialized SIP INVITE message.
            dest_addr: Destination (host, port) tuple.
            send_fn: Function to call to send the message over the network.
            on_timeout: Optional callback invoked when Timer B fires.
        """
        self.message = message
        self.dest_addr = dest_addr
        self.send_fn = send_fn
        self.on_timeout = on_timeout
        self.logger = get_logger()
        self._timer_a_interval: float = T1
        self._timer_a: threading.Timer | None = None
        self._timer_b: threading.Timer | None = None
        self._terminated: bool = False

    def start(self) -> None:
        """Send the initial INVITE and start retransmission timers."""
        self.send_fn(self.message, self.dest_addr)
        self._schedule_timer_a()
        self._timer_b = threading.Timer(TIMER_B, self._on_timer_b)
        self._timer_b.daemon = True
        self._timer_b.start()

    def on_response_received(self) -> None:
        """Stop retransmission upon receiving any provisional or final response."""
        self._terminate()

    def cancel(self) -> None:
        """Cancel the transaction (e.g., caller hung up)."""
        self._terminate()

    def _schedule_timer_a(self) -> None:
        if self._terminated:
            return
        self._timer_a = threading.Timer(self._timer_a_interval, self._on_timer_a)
        self._timer_a.daemon = True
        self._timer_a.start()

    def _on_timer_a(self) -> None:
        if self._terminated:
            return
        self.logger.debug(
            f"INVITE retransmit to {self.dest_addr} (interval={self._timer_a_interval}s)"
        )
        self.send_fn(self.message, self.dest_addr)
        self._timer_a_interval = min(self._timer_a_interval * 2, T2)
        self._schedule_timer_a()

    def _on_timer_b(self) -> None:
        if self._terminated:
            return
        self.logger.warning(f"INVITE transaction timeout for {self.dest_addr}")
        self._terminate()
        if self.on_timeout:
            self.on_timeout()

    def _terminate(self) -> None:
        self._terminated = True
        if self._timer_a:
            self._timer_a.cancel()
        if self._timer_b:
            self._timer_b.cancel()
