"""
Webhook System for Event-Driven Integrations
Sends HTTP POST notifications to external systems when PBX events occur
"""

import hashlib
import hmac
import json
import queue
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pbx.utils.logger import get_logger


class WebhookEvent:
    """Represents a webhook event"""

    # Event types
    CALL_STARTED = "call.started"
    CALL_ANSWERED = "call.answered"
    CALL_ENDED = "call.ended"
    CALL_HOLD = "call.hold"
    CALL_RESUME = "call.resume"
    CALL_TRANSFER = "call.transfer"
    CALL_PARKED = "call.parked"
    CALL_RETRIEVED = "call.retrieved"

    VOICEMAIL_NEW = "voicemail.new"
    VOICEMAIL_READ = "voicemail.read"
    VOICEMAIL_DELETED = "voicemail.deleted"

    EXTENSION_REGISTERED = "extension.registered"
    EXTENSION_UNREGISTERED = "extension.unregistered"

    QUEUE_CALL_ADDED = "queue.call_added"
    QUEUE_CALL_ANSWERED = "queue.call_answered"
    QUEUE_CALL_ABANDONED = "queue.call_abandoned"

    PAGING_STARTED = "paging.started"
    PAGING_ENDED = "paging.ended"

    CONFERENCE_STARTED = "conference.started"
    CONFERENCE_PARTICIPANT_JOINED = "conference.participant_joined"
    CONFERENCE_PARTICIPANT_LEFT = "conference.participant_left"
    CONFERENCE_ENDED = "conference.ended"

    def __init__(self, event_type: str, data: Dict):
        """
        Initialize webhook event

        Args:
            event_type: Type of event (e.g., "call.started")
            data: Event data dictionary
        """
        self.event_type = event_type
        self.data = data
        self.timestamp = datetime.now().isoformat()
        self.event_id = f"{event_type}-{int(time.time() * 1000)}"

    def to_dict(self) -> Dict:
        """Convert event to dictionary for JSON serialization"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "data": self.data,
        }


class WebhookSubscription:
    """Represents a webhook subscription"""

    def __init__(
        self,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        enabled: bool = True,
    ):
        """
        Initialize webhook subscription

        Args:
            url: Target URL for webhook POST requests
            events: List of event types to subscribe to (or ['*'] for all)
            secret: Optional secret for HMAC signature verification
            headers: Optional custom headers to include in requests
            enabled: Whether this subscription is active
        """
        self.url = url
        self.events = events
        self.secret = secret
        self.headers = headers or {}
        self.enabled = enabled
        self.created_at = datetime.now()
        self.last_sent = None
        self.success_count = 0
        self.failure_count = 0

    def matches_event(self, event_type: str) -> bool:
        """Check if this subscription matches an event type"""
        if not self.enabled:
            return False
        return "*" in self.events or event_type in self.events


class WebhookDeliveryQueue:
    """Queue for asynchronous webhook delivery"""

    def __init__(self, max_size: int = 1000):
        """
        Initialize delivery queue

        Args:
            max_size: Maximum queue size
        """
        self.queue = queue.Queue(maxsize=max_size)
        self.logger = get_logger()

    def enqueue(self, event: WebhookEvent, subscription: WebhookSubscription):
        """Add event to delivery queue"""
        try:
            self.queue.put_nowait((event, subscription))
        except queue.Full:
            self.logger.warning("Webhook delivery queue is full, dropping event")

    def dequeue(self, timeout: float = 1.0) -> Optional[tuple]:
        """Get next event from queue"""
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None


class WebhookSystem:
    """
    Webhook system for event-driven integrations

    Provides:
    - Event notification to external HTTP endpoints
    - Subscription management
    - Asynchronous delivery with retry logic
    - Event filtering and routing
    - Delivery status tracking
    """

    def __init__(self, config=None):
        """
        Initialize webhook system

        Args:
            config: Configuration object
        """
        self.logger = get_logger()
        self.config = config or {}

        # Webhook configuration
        self.enabled = self._get_config("features.webhooks.enabled", False)
        self.max_retries = self._get_config("features.webhooks.max_retries", 3)
        self.retry_delay = self._get_config("features.webhooks.retry_delay", 5)  # seconds
        self.timeout = self._get_config("features.webhooks.timeout", 10)  # seconds
        self.worker_threads = self._get_config("features.webhooks.worker_threads", 2)

        # Subscriptions
        self.subscriptions = []
        self.subscriptions_lock = threading.Lock()

        # Delivery queue
        self.delivery_queue = WebhookDeliveryQueue()

        # Worker threads
        self.workers = []
        self.running = False

        # Load subscriptions from config
        self._load_subscriptions()

        if self.enabled:
            self.logger.info("Webhook system enabled")
            self.logger.info(f"Loaded {len(self.subscriptions)} webhook subscriptions")
            self._start_workers()
        else:
            self.logger.info("Webhook system disabled")

    def _get_config(self, key: str, default=None):
        """Get configuration value"""
        if hasattr(self.config, "get"):
            return self.config.get(key, default)
        return default

    def _load_subscriptions(self):
        """Load webhook subscriptions from configuration"""
        webhooks_config = self._get_config("features.webhooks.subscriptions", [])

        with self.subscriptions_lock:
            for webhook_config in webhooks_config:
                subscription = WebhookSubscription(
                    url=webhook_config.get("url"),
                    events=webhook_config.get("events", ["*"]),
                    secret=webhook_config.get("secret"),
                    headers=webhook_config.get("headers"),
                    enabled=webhook_config.get("enabled", True),
                )
                self.subscriptions.append(subscription)
                self.logger.info(
                    f"Loaded webhook subscription: {subscription.url} (events: {subscription.events})"
                )

    def _start_workers(self):
        """Start webhook delivery worker threads"""
        self.running = True
        for i in range(self.worker_threads):
            worker = threading.Thread(
                target=self._delivery_worker, name=f"WebhookWorker-{i}", daemon=True
            )
            worker.start()
            self.workers.append(worker)
        self.logger.info(
            f"Started {self.worker_threads} webhook delivery workers"
        )

    def stop(self):
        """Stop the webhook system"""
        self.logger.info("Stopping webhook system...")
        self.running = False
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=5)
        self.logger.info("Webhook system stopped")

    def _delivery_worker(self):
        """Worker thread for delivering webhooks"""
        while self.running:
            item = self.delivery_queue.dequeue(timeout=1.0)
            if item:
                event, subscription = item
                self._deliver_webhook(event, subscription)

    def _deliver_webhook(self, event: WebhookEvent, subscription: WebhookSubscription):
        """
        Deliver webhook to subscription with retry logic

        Args:
            event: Webhook event
            subscription: Webhook subscription
        """
        attempt = 0
        while attempt < self.max_retries:
            try:
                # Prepare payload
                payload = json.dumps(event.to_dict()).encode("utf-8")

                # Prepare headers
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "PBX-Webhook/1.0",
                    "X-Webhook-Event": event.event_type,
                    "X-Webhook-ID": event.event_id,
                    **subscription.headers,
                }

                # Add HMAC signature if secret is provided
                if subscription.secret:
                    signature = hmac.new(
                        subscription.secret.encode("utf-8"), payload, hashlib.sha256
                    ).hexdigest()
                    headers["X-Webhook-Signature"] = f"sha256={signature}"

                # Create request
                request = Request(subscription.url, data=payload, headers=headers, method="POST")

                # Send request
                response = urlopen(
                    request, timeout=self.timeout
                )  # nosec B310 - URL is from configured webhook subscription

                # Success
                subscription.last_sent = datetime.now()
                subscription.success_count += 1
                self.logger.info(
                    f"Webhook delivered: {event.event_type} -> {subscription.url} (status: {response.status})"
                )
                return

            except (URLError, HTTPError) as e:
                attempt += 1
                subscription.failure_count += 1
                self.logger.warning(
                    f"Webhook delivery failed (attempt {attempt}/{self.max_retries}): {event.event_type} -> {subscription.url} - {e}"
                )

                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error(
                        f"Webhook delivery failed after {self.max_retries} attempts: {event.event_type} -> {subscription.url}"
                    )

            except Exception as e:
                self.logger.error(f"Unexpected error delivering webhook: {e}")
                self.logger.debug("Webhook delivery error details", exc_info=True)
                break

    def trigger_event(self, event_type: str, data: Dict):
        """
        Trigger a webhook event

        Args:
            event_type: Type of event (e.g., WebhookEvent.CALL_STARTED)
            data: Event data dictionary
        """
        if not self.enabled:
            return

        # Create event
        event = WebhookEvent(event_type, data)

        # Find matching subscriptions (make a copy to avoid holding lock during delivery)
        with self.subscriptions_lock:
            matching_subscriptions = [
                sub for sub in self.subscriptions if sub.matches_event(event_type)
            ]

        if not matching_subscriptions:
            return

        # Queue for delivery
        for subscription in matching_subscriptions:
            self.delivery_queue.enqueue(event, subscription)

        self.logger.debug(
            f"Triggered webhook event: {event_type} (subscriptions: {len(matching_subscriptions)})"
        )

    def add_subscription(
        self,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> WebhookSubscription:
        """
        Add a webhook subscription

        Args:
            url: Target URL
            events: List of event types
            secret: Optional secret
            headers: Optional custom headers

        Returns:
            WebhookSubscription object
        """
        subscription = WebhookSubscription(url, events, secret, headers)
        with self.subscriptions_lock:
            self.subscriptions.append(subscription)
        self.logger.info(f"Added webhook subscription: {url} (events: {events})")
        return subscription

    def remove_subscription(self, url: str) -> bool:
        """
        Remove a webhook subscription

        Args:
            url: Subscription URL to remove

        Returns:
            True if removed, False if not found
        """
        with self.subscriptions_lock:
            for i, subscription in enumerate(self.subscriptions):
                if subscription.url == url:
                    self.subscriptions.pop(i)
                    self.logger.info(f"Removed webhook subscription: {url}")
                    return True
        return False

    def get_subscriptions(self) -> List[Dict]:
        """Get all webhook subscriptions"""
        with self.subscriptions_lock:
            return [
                {
                    "url": sub.url,
                    "events": sub.events,
                    "enabled": sub.enabled,
                    "created_at": sub.created_at.isoformat() if sub.created_at else None,
                    "last_sent": sub.last_sent.isoformat() if sub.last_sent else None,
                    "success_count": sub.success_count,
                    "failure_count": sub.failure_count,
                }
                for sub in self.subscriptions
            ]

    def enable_subscription(self, url: str) -> bool:
        """Enable a webhook subscription"""
        with self.subscriptions_lock:
            for subscription in self.subscriptions:
                if subscription.url == url:
                    subscription.enabled = True
                    self.logger.info(f"Enabled webhook subscription: {url}")
                    return True
        return False

    def disable_subscription(self, url: str) -> bool:
        """Disable a webhook subscription"""
        with self.subscriptions_lock:
            for subscription in self.subscriptions:
                if subscription.url == url:
                    subscription.enabled = False
                    self.logger.info(f"Disabled webhook subscription: {url}")
                    return True
        return False
