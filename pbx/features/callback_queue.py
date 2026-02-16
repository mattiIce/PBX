"""
Callback Queuing System
Avoid hold time with scheduled callbacks
"""

import sqlite3
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from pbx.utils.logger import get_logger


class CallbackStatus(Enum):
    """Callback request status"""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CallbackQueue:
    """System for managing callback requests"""

    def __init__(self, config: Any | None = None, database: Any | None = None) -> None:
        """Initialize callback queue"""
        self.logger = get_logger()
        self.config = config or {}
        self.database = database
        self.enabled = (
            self.config.get("features", {}).get("callback_queue", {}).get("enabled", False)
        )

        # Configuration
        self.max_wait_time = (
            self.config.get("features", {}).get("callback_queue", {}).get("max_wait_minutes", 30)
        )
        self.retry_attempts = (
            self.config.get("features", {}).get("callback_queue", {}).get("retry_attempts", 3)
        )
        self.retry_interval = (
            self.config.get("features", {})
            .get("callback_queue", {})
            .get("retry_interval_minutes", 5)
        )

        # Callback requests
        self.callbacks = {}  # callback_id -> callback info
        self.queue_callbacks = {}  # queue_id -> list of callback_ids

        # Initialize database schema if database is available
        if self.database and self.database.enabled:
            self._initialize_schema()
            self._load_callbacks_from_database()

        if self.enabled:
            self.logger.info("Callback queue system initialized")
            self.logger.info(f"  Max wait time: {self.max_wait_time} minutes")
            self.logger.info(f"  Retry attempts: {self.retry_attempts}")

    def _initialize_schema(self) -> None:
        """Initialize database schema for callback queue"""
        if not self.database or not self.database.enabled:
            return

        # Callback requests table
        callback_table = """
        CREATE TABLE IF NOT EXISTS callback_requests (
            callback_id VARCHAR(100) PRIMARY KEY,
            queue_id VARCHAR(50) NOT NULL,
            caller_number VARCHAR(50) NOT NULL,
            caller_name VARCHAR(100),
            requested_at TIMESTAMP NOT NULL,
            callback_time TIMESTAMP NOT NULL,
            status VARCHAR(20) NOT NULL,
            attempts INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 3,
            agent_id VARCHAR(50),
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            failed_at TIMESTAMP,
            cancelled_at TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        try:
            cursor = self.database.connection.cursor()
            cursor.execute(callback_table)

            # Create index on queue_id for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_callback_queue_id
                ON callback_requests(queue_id)
            """)

            # Create index on status for filtering
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_callback_status
                ON callback_requests(status)
            """)

            # Create index on callback_time for scheduling
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_callback_time
                ON callback_requests(callback_time)
            """)

            self.database.connection.commit()
            cursor.close()
            self.logger.debug("Callback queue database schema initialized")
        except sqlite3.Error as e:
            self.logger.error(f"Error initializing callback queue schema: {e}")

    def _load_callbacks_from_database(self) -> None:
        """Load active callbacks from database"""
        if not self.database or not self.database.enabled:
            return

        try:
            cursor = self.database.connection.cursor()

            # Load callbacks that are not completed, failed, or cancelled
            cursor.execute("""
                SELECT callback_id, queue_id, caller_number, caller_name,
                       requested_at, callback_time, status, attempts, max_attempts,
                       agent_id, started_at
                FROM callback_requests
                WHERE status IN ('scheduled', 'in_progress', 'pending')
                ORDER BY callback_time ASC
            """)

            rows = cursor.fetchall()
            for row in rows:
                (
                    callback_id,
                    queue_id,
                    caller_number,
                    caller_name,
                    requested_at,
                    callback_time,
                    status,
                    attempts,
                    max_attempts,
                    agent_id,
                    started_at,
                ) = row

                # Convert status string to enum
                try:
                    status_enum = CallbackStatus(status)
                except ValueError:
                    status_enum = CallbackStatus.SCHEDULED

                callback_info = {
                    "callback_id": callback_id,
                    "queue_id": queue_id,
                    "caller_number": caller_number,
                    "caller_name": caller_name,
                    "requested_at": requested_at,
                    "callback_time": callback_time,
                    "status": status_enum,
                    "attempts": attempts,
                    "max_attempts": max_attempts,
                }

                if agent_id:
                    callback_info["agent_id"] = agent_id
                if started_at:
                    callback_info["started_at"] = started_at

                self.callbacks[callback_id] = callback_info

                # Add to queue
                if queue_id not in self.queue_callbacks:
                    self.queue_callbacks[queue_id] = []
                self.queue_callbacks[queue_id].append(callback_id)

            cursor.close()
            if rows:
                self.logger.info(f"Loaded {len(rows)} active callbacks from database")
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error loading callbacks from database: {e}")

    def _save_callback_to_database(self, callback_id: str) -> bool:
        """Save callback to database"""
        if not self.database or not self.database.enabled:
            return False

        if callback_id not in self.callbacks:
            return False

        callback = self.callbacks[callback_id]

        try:
            cursor = self.database.connection.cursor()

            # Prepare values
            status_value = callback["status"].value

            if self.database.db_type == "postgresql":
                cursor.execute(
                    """
                    INSERT INTO callback_requests (
                        callback_id, queue_id, caller_number, caller_name,
                        requested_at, callback_time, status, attempts, max_attempts,
                        agent_id, started_at, completed_at, failed_at, cancelled_at,
                        notes, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (callback_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        attempts = EXCLUDED.attempts,
                        agent_id = EXCLUDED.agent_id,
                        started_at = EXCLUDED.started_at,
                        completed_at = EXCLUDED.completed_at,
                        failed_at = EXCLUDED.failed_at,
                        cancelled_at = EXCLUDED.cancelled_at,
                        notes = EXCLUDED.notes,
                        updated_at = EXCLUDED.updated_at
                """,
                    (
                        callback_id,
                        callback["queue_id"],
                        callback["caller_number"],
                        callback.get("caller_name"),
                        callback["requested_at"],
                        callback["callback_time"],
                        status_value,
                        callback["attempts"],
                        callback["max_attempts"],
                        callback.get("agent_id"),
                        callback.get("started_at"),
                        callback.get("completed_at"),
                        callback.get("failed_at"),
                        callback.get("cancelled_at"),
                        callback.get("notes"),
                        datetime.now(UTC),
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO callback_requests (
                        callback_id, queue_id, caller_number, caller_name,
                        requested_at, callback_time, status, attempts, max_attempts,
                        agent_id, started_at, completed_at, failed_at, cancelled_at,
                        notes, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        callback_id,
                        callback["queue_id"],
                        callback["caller_number"],
                        callback.get("caller_name"),
                        callback["requested_at"],
                        callback["callback_time"],
                        status_value,
                        callback["attempts"],
                        callback["max_attempts"],
                        callback.get("agent_id"),
                        callback.get("started_at"),
                        callback.get("completed_at"),
                        callback.get("failed_at"),
                        callback.get("cancelled_at"),
                        callback.get("notes"),
                        datetime.now(UTC),
                    ),
                )

            self.database.connection.commit()
            cursor.close()
            return True
        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Error saving callback to database: {e}")
            return False

    def request_callback(
        self,
        queue_id: str,
        caller_number: str,
        caller_name: str | None = None,
        preferred_time: datetime | None = None,
    ) -> dict:
        """
        Request a callback instead of waiting in queue

        Args:
            queue_id: Queue identifier
            caller_number: Caller's phone number
            caller_name: Caller's name (optional)
            preferred_time: Preferred callback time (optional, defaults to ASAP)

        Returns:
            Callback request information
        """
        if not self.enabled:
            return {"error": "Callback queue not enabled"}

        # Generate callback ID
        callback_id = f"cb_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{len(self.callbacks)}"

        # Calculate estimated callback time
        if preferred_time:
            callback_time = preferred_time
        else:
            # ASAP - estimate based on queue length
            queue_length = len(self.queue_callbacks.get(queue_id, []))
            callback_time = datetime.now(UTC) + timedelta(
                minutes=queue_length * 5
            )  # 5 min per call estimate

        callback_info = {
            "callback_id": callback_id,
            "queue_id": queue_id,
            "caller_number": caller_number,
            "caller_name": caller_name,
            "requested_at": datetime.now(UTC),
            "callback_time": callback_time,
            "status": CallbackStatus.SCHEDULED,
            "attempts": 0,
            "max_attempts": self.retry_attempts,
        }

        self.callbacks[callback_id] = callback_info

        # Add to queue
        if queue_id not in self.queue_callbacks:
            self.queue_callbacks[queue_id] = []
        self.queue_callbacks[queue_id].append(callback_id)

        # Save to database
        self._save_callback_to_database(callback_id)

        self.logger.info(
            f"Callback requested: {callback_id} for {caller_number} in queue {queue_id}"
        )
        self.logger.info(
            f"  Estimated callback time: {callback_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        return {
            "callback_id": callback_id,
            "estimated_time": callback_time.isoformat(),
            "queue_position": len(self.queue_callbacks[queue_id]),
            "status": "scheduled",
        }

    def get_next_callback(self, queue_id: str) -> dict | None:
        """Get next callback to process for a queue"""
        if queue_id not in self.queue_callbacks or not self.queue_callbacks[queue_id]:
            return None

        now = datetime.now(UTC)

        # Find next callback that's ready
        for callback_id in self.queue_callbacks[queue_id]:
            callback = self.callbacks.get(callback_id)
            if not callback:
                continue

            # Check if it's time to call back
            if callback["status"] == CallbackStatus.SCHEDULED and callback["callback_time"] <= now:
                return callback

        return None

    def start_callback(self, callback_id: str, agent_id: str) -> dict:
        """Start processing a callback"""
        if callback_id not in self.callbacks:
            return {"error": "Callback not found"}

        callback = self.callbacks[callback_id]
        callback["status"] = CallbackStatus.IN_PROGRESS
        callback["agent_id"] = agent_id
        callback["started_at"] = datetime.now(UTC)
        callback["attempts"] += 1

        # Save to database
        self._save_callback_to_database(callback_id)

        self.logger.info(f"Starting callback {callback_id} (attempt {callback['attempts']})")

        return {
            "callback_id": callback_id,
            "caller_number": callback["caller_number"],
            "caller_name": callback["caller_name"],
            "queue_id": callback["queue_id"],
        }

    def complete_callback(self, callback_id: str, success: bool, notes: str | None = None) -> bool:
        """Mark callback as completed"""
        if callback_id not in self.callbacks:
            return False

        callback = self.callbacks[callback_id]

        if success:
            callback["status"] = CallbackStatus.COMPLETED
            callback["completed_at"] = datetime.now(UTC)
            callback["notes"] = notes

            # Save to database
            self._save_callback_to_database(callback_id)

            # Remove from queue
            queue_id = callback["queue_id"]
            if queue_id in self.queue_callbacks:
                self.queue_callbacks[queue_id].remove(callback_id)

            self.logger.info(f"Callback {callback_id} completed successfully")
        # Check if we should retry
        elif callback["attempts"] < callback["max_attempts"]:
            callback["status"] = CallbackStatus.SCHEDULED
            callback["callback_time"] = datetime.now(UTC) + timedelta(minutes=self.retry_interval)

            # Save to database
            self._save_callback_to_database(callback_id)

            self.logger.info(
                f"Callback {callback_id} failed, will retry at {callback['callback_time']}"
            )
        else:
            callback["status"] = CallbackStatus.FAILED
            callback["failed_at"] = datetime.now(UTC)
            callback["notes"] = notes

            # Save to database
            self._save_callback_to_database(callback_id)

            # Remove from queue
            queue_id = callback["queue_id"]
            if queue_id in self.queue_callbacks:
                self.queue_callbacks[queue_id].remove(callback_id)

            self.logger.warning(
                f"Callback {callback_id} failed after {callback['attempts']} attempts"
            )

        return True

    def cancel_callback(self, callback_id: str) -> bool:
        """Cancel a pending callback"""
        if callback_id not in self.callbacks:
            return False

        callback = self.callbacks[callback_id]
        callback["status"] = CallbackStatus.CANCELLED
        callback["cancelled_at"] = datetime.now(UTC)

        # Save to database
        self._save_callback_to_database(callback_id)

        # Remove from queue
        queue_id = callback["queue_id"]
        if queue_id in self.queue_callbacks:
            self.queue_callbacks[queue_id].remove(callback_id)

        self.logger.info(f"Callback {callback_id} cancelled")
        return True

    def get_callback_info(self, callback_id: str) -> dict | None:
        """Get information about a callback"""
        callback = self.callbacks.get(callback_id)
        if not callback:
            return None

        return {
            "callback_id": callback_id,
            "queue_id": callback["queue_id"],
            "caller_number": callback["caller_number"],
            "caller_name": callback["caller_name"],
            "status": callback["status"].value,
            "requested_at": callback["requested_at"].isoformat(),
            "callback_time": callback["callback_time"].isoformat(),
            "attempts": callback["attempts"],
        }

    def list_queue_callbacks(
        self, queue_id: str, status: CallbackStatus | None = None
    ) -> list[dict]:
        """list callbacks for a queue"""
        callback_ids = self.queue_callbacks.get(queue_id, [])

        callbacks = []
        for callback_id in callback_ids:
            callback = self.callbacks.get(callback_id)
            if callback and (status is None or callback["status"] == status):
                callbacks.append(self.get_callback_info(callback_id))

        return callbacks

    def get_queue_statistics(self, queue_id: str) -> dict:
        """Get callback statistics for a queue"""
        all_callbacks = [
            self.callbacks[cid]
            for cid in self.queue_callbacks.get(queue_id, [])
            if cid in self.callbacks
        ]

        return {
            "queue_id": queue_id,
            "pending_callbacks": sum(
                1 for c in all_callbacks if c["status"] == CallbackStatus.SCHEDULED
            ),
            "in_progress_callbacks": sum(
                1 for c in all_callbacks if c["status"] == CallbackStatus.IN_PROGRESS
            ),
            "completed_callbacks": sum(
                1 for c in all_callbacks if c["status"] == CallbackStatus.COMPLETED
            ),
            "failed_callbacks": sum(
                1 for c in all_callbacks if c["status"] == CallbackStatus.FAILED
            ),
        }

    def cleanup_old_callbacks(self, days: int = 30) -> None:
        """Clean up old completed/failed callbacks"""
        cutoff = datetime.now(UTC) - timedelta(days=days)

        to_remove = []
        for callback_id, callback in self.callbacks.items():
            if callback["status"] in [
                CallbackStatus.COMPLETED,
                CallbackStatus.FAILED,
                CallbackStatus.CANCELLED,
            ]:
                completed_at = (
                    callback.get("completed_at")
                    or callback.get("failed_at")
                    or callback.get("cancelled_at")
                )
                if completed_at and completed_at < cutoff:
                    to_remove.append(callback_id)

        for callback_id in to_remove:
            del self.callbacks[callback_id]

        if to_remove:
            self.logger.info(f"Cleaned up {len(to_remove)} old callbacks")

    def get_statistics(self) -> dict:
        """Get overall callback queue statistics"""
        status_counts = {}
        for callback in self.callbacks.values():
            status = callback["status"].value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "enabled": self.enabled,
            "total_callbacks": len(self.callbacks),
            "active_queues": len(self.queue_callbacks),
            "status_breakdown": status_counts,
        }
