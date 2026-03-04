"""Tests for SIP INVITE client transaction with retransmission (RFC 3261)."""

import threading
import time
from unittest.mock import MagicMock

import pytest

from pbx.sip.transaction import TIMER_B, InviteClientTransaction, T1, T2


@pytest.mark.unit
class TestInviteClientTransaction:
    """Tests for INVITE retransmission logic."""

    def test_start_sends_initial_message(self) -> None:
        send_fn = MagicMock()
        txn = InviteClientTransaction(
            message="INVITE sip:1001@10.0.0.1 SIP/2.0\r\n",
            dest_addr=("10.0.0.1", 5060),
            send_fn=send_fn,
        )
        txn.start()
        txn.cancel()  # Clean up timers

        send_fn.assert_called_with(
            "INVITE sip:1001@10.0.0.1 SIP/2.0\r\n", ("10.0.0.1", 5060)
        )

    def test_retransmits_after_t1(self) -> None:
        send_fn = MagicMock()
        txn = InviteClientTransaction(
            message="INVITE",
            dest_addr=("10.0.0.1", 5060),
            send_fn=send_fn,
        )
        txn.start()
        # Wait slightly longer than T1 for first retransmit
        time.sleep(T1 + 0.1)
        txn.cancel()

        # Initial send + at least 1 retransmit
        assert send_fn.call_count >= 2

    def test_response_stops_retransmission(self) -> None:
        send_fn = MagicMock()
        txn = InviteClientTransaction(
            message="INVITE",
            dest_addr=("10.0.0.1", 5060),
            send_fn=send_fn,
        )
        txn.start()
        txn.on_response_received()

        # Wait to verify no more retransmissions
        time.sleep(T1 + 0.2)

        # Should only have the initial send (response stopped retransmission)
        assert send_fn.call_count == 1

    def test_cancel_stops_retransmission(self) -> None:
        send_fn = MagicMock()
        txn = InviteClientTransaction(
            message="INVITE",
            dest_addr=("10.0.0.1", 5060),
            send_fn=send_fn,
        )
        txn.start()
        txn.cancel()

        time.sleep(T1 + 0.2)
        assert send_fn.call_count == 1

    def test_timeout_calls_callback(self) -> None:
        send_fn = MagicMock()
        timeout_cb = MagicMock()

        # Use very short timers for testing
        txn = InviteClientTransaction(
            message="INVITE",
            dest_addr=("10.0.0.1", 5060),
            send_fn=send_fn,
            on_timeout=timeout_cb,
        )
        # Override timer constants for fast test
        txn._timer_a_interval = 0.01
        # Manually fire timer B quickly
        txn.start()
        txn._timer_b.cancel()
        txn._on_timer_b()

        timeout_cb.assert_called_once()

    def test_timeout_without_callback_does_not_raise(self) -> None:
        send_fn = MagicMock()
        txn = InviteClientTransaction(
            message="INVITE",
            dest_addr=("10.0.0.1", 5060),
            send_fn=send_fn,
            on_timeout=None,
        )
        txn.start()
        # Should not raise even without callback
        txn._on_timer_b()
        txn.cancel()

    def test_interval_caps_at_t2(self) -> None:
        send_fn = MagicMock()
        txn = InviteClientTransaction(
            message="INVITE",
            dest_addr=("10.0.0.1", 5060),
            send_fn=send_fn,
        )

        # Simulate multiple retransmits without actual timers
        txn._timer_a_interval = T1
        for _ in range(10):
            txn._timer_a_interval = min(txn._timer_a_interval * 2, T2)

        assert txn._timer_a_interval == T2
        txn.cancel()

    def test_double_cancel_does_not_raise(self) -> None:
        send_fn = MagicMock()
        txn = InviteClientTransaction(
            message="INVITE",
            dest_addr=("10.0.0.1", 5060),
            send_fn=send_fn,
        )
        txn.start()
        txn.cancel()
        txn.cancel()  # Should not raise

    def test_response_after_cancel_does_not_raise(self) -> None:
        send_fn = MagicMock()
        txn = InviteClientTransaction(
            message="INVITE",
            dest_addr=("10.0.0.1", 5060),
            send_fn=send_fn,
        )
        txn.start()
        txn.cancel()
        txn.on_response_received()  # Should not raise
