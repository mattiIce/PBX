"""
Call Recording Announcements
Auto-play recording disclosure before recording starts
"""

import os
from datetime import datetime
from typing import Dict, Optional

from pbx.utils.logger import get_logger


class RecordingAnnouncements:
    """System for playing recording disclosure announcements"""

    def __init__(self, config=None, database=None):
        """Initialize recording announcements"""
        self.logger = get_logger()
        self.config = config or {}
        self.database = database

        # Configuration
        announcement_config = self.config.get("features", {}).get("recording_announcements", {})
        self.enabled = announcement_config.get("enabled", False)
        self.announcement_type = announcement_config.get(
            "type", "both"
        )  # 'caller', 'callee', 'both'
        self.audio_path = announcement_config.get("audio_path", "audio/recording_announcement.wav")
        self.announcement_text = announcement_config.get(
            "text", "This call may be recorded for quality and training purposes."
        )

        # Compliance requirements
        self.require_consent = announcement_config.get("require_consent", False)
        self.consent_timeout = announcement_config.get("consent_timeout_seconds", 10)

        # Statistics
        self.announcements_played = 0
        self.consent_accepted = 0
        self.consent_declined = 0

        # Initialize database schema if database is available
        if self.database and self.database.enabled:
            self._initialize_schema()

        if self.enabled:
            self.logger.info("Recording announcements initialized")
            self.logger.info(f"  Type: {self.announcement_type}")
            self.logger.info(f"  Require consent: {self.require_consent}")
            self._check_audio_file()

    def _initialize_schema(self):
        """Initialize database schema for recording announcements"""
        if not self.database or not self.database.enabled:
            return

        # Announcement logs table
        announcement_table = """
        CREATE TABLE IF NOT EXISTS recording_announcements_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id VARCHAR(100) NOT NULL,
            party VARCHAR(20) NOT NULL,
            announcement_played BOOLEAN DEFAULT 1,
            consent_required BOOLEAN DEFAULT 0,
            consent_given BOOLEAN,
            consent_timeout BOOLEAN DEFAULT 0,
            played_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        if self.database.db_type == "postgresql":
            announcement_table = """
            CREATE TABLE IF NOT EXISTS recording_announcements_log (
                id SERIAL PRIMARY KEY,
                call_id VARCHAR(100) NOT NULL,
                party VARCHAR(20) NOT NULL,
                announcement_played BOOLEAN DEFAULT TRUE,
                consent_required BOOLEAN DEFAULT FALSE,
                consent_given BOOLEAN,
                consent_timeout BOOLEAN DEFAULT FALSE,
                played_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """

        try:
            cursor = self.database.connection.cursor()
            cursor.execute(announcement_table)

            # Create index on call_id
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_recording_announcements_call_id
                ON recording_announcements_log(call_id)
            """)

            self.database.connection.commit()
            cursor.close()
            self.logger.debug("Recording announcements database schema initialized")
        except Exception as e:
            self.logger.error(f"Error initializing recording announcements schema: {e}")

    def _log_announcement(
        self,
        call_id: str,
        party: str,
        announcement_played: bool,
        consent_required: bool,
        consent_given: Optional[bool],
        consent_timeout: bool,
    ):
        """Log announcement to database"""
        if not self.database or not self.database.enabled:
            return

        try:
            cursor = self.database.connection.cursor()

            if self.database.db_type == "postgresql":
                cursor.execute(
                    """
                    INSERT INTO recording_announcements_log (call_id, party, announcement_played, consent_required, consent_given, consent_timeout, played_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        call_id,
                        party,
                        announcement_played,
                        consent_required,
                        consent_given,
                        consent_timeout,
                        datetime.now(),
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO recording_announcements_log (call_id, party, announcement_played, consent_required, consent_given, consent_timeout, played_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        call_id,
                        party,
                        1 if announcement_played else 0,
                        1 if consent_required else 0,
                        1 if consent_given else (0 if consent_given is False else None),
                        1 if consent_timeout else 0,
                        datetime.now(),
                    ),
                )

            self.database.connection.commit()
            cursor.close()
        except Exception as e:
            self.logger.error(f"Error logging announcement: {e}")

    def _check_audio_file(self):
        """Check if announcement audio file exists"""
        if os.path.exists(self.audio_path):
            self.logger.info(f"  Announcement audio: {self.audio_path}")
        else:
            self.logger.warning(f"  Announcement audio not found: {self.audio_path}")
            self.logger.info(f"  Using TTS: '{self.announcement_text}'")

    def should_announce(self, call_direction: str, recording_type: str) -> bool:
        """
        Determine if announcement should be played

        Args:
            call_direction: 'inbound' or 'outbound'
            recording_type: 'automatic' or 'on_demand'

        Returns:
            True if announcement should be played
        """
        if not self.enabled:
            return False

        # Always announce if consent required
        if self.require_consent:
            return True

        # Check announcement type
        if self.announcement_type == "both":
            return True
        elif self.announcement_type == "caller" and call_direction == "inbound":
            return True
        elif self.announcement_type == "callee" and call_direction == "outbound":
            return True

        return False

    def play_announcement(self, call_id: str, party: str = "both") -> Dict:
        """
        Play recording announcement for a call

        Args:
            call_id: Call identifier
            party: Who to play to ('caller', 'callee', 'both')

        Returns:
            Announcement result
        """
        if not self.enabled:
            return {"error": "Recording announcements not enabled"}

        self.logger.info(f"Playing recording announcement for call {call_id} (to: {party})")

        # Stub implementation - in production would actually play audio
        result = {
            "call_id": call_id,
            "announcement_played": True,
            "audio_file": self.audio_path if os.path.exists(self.audio_path) else None,
            "text": self.announcement_text,
            "party": party,
            "timestamp": datetime.now().isoformat(),
        }

        self.announcements_played += 1

        # Log to database
        self._log_announcement(call_id, party, True, self.require_consent, None, False)

        return result

    def request_consent(self, call_id: str) -> Dict:
        """
        Request recording consent from caller

        Args:
            call_id: Call identifier

        Returns:
            Consent request result
        """
        if not self.enabled or not self.require_consent:
            return {"consent": "not_required"}

        self.logger.info(f"Requesting recording consent for call {call_id}")

        # Play announcement
        announcement = self.play_announcement(call_id, party="caller")

        # Stub implementation - in production would wait for DTMF input
        # Press 1 to accept, 2 to decline
        result = {
            "call_id": call_id,
            "consent_requested": True,
            "announcement": announcement,
            "timeout_seconds": self.consent_timeout,
            "instructions": "Press 1 to accept recording, 2 to decline",
            "timestamp": datetime.now().isoformat(),
        }

        return result

    def record_consent_response(self, call_id: str, accepted: bool) -> bool:
        """
        Record consent response

        Args:
            call_id: Call identifier
            accepted: Whether consent was accepted

        Returns:
            True if recorded
        """
        if accepted:
            self.consent_accepted += 1
            self.logger.info(f"Call {call_id}: Recording consent accepted")
        else:
            self.consent_declined += 1
            self.logger.info(f"Call {call_id}: Recording consent declined")

        # Log to database
        self._log_announcement(call_id, "caller", True, True, accepted, False)

        return True

    def get_announcement_config(self) -> Dict:
        """Get current announcement configuration"""
        return {
            "enabled": self.enabled,
            "type": self.announcement_type,
            "require_consent": self.require_consent,
            "audio_file": self.audio_path,
            "text": self.announcement_text,
            "audio_exists": os.path.exists(self.audio_path),
        }

    def update_announcement_text(self, text: str) -> bool:
        """Update announcement text"""
        self.announcement_text = text
        self.logger.info(f"Updated announcement text: {text}")
        return True

    def set_audio_file(self, path: str) -> bool:
        """Set custom audio file for announcement"""
        if not os.path.exists(path):
            self.logger.error(f"Audio file not found: {path}")
            return False

        self.audio_path = path
        self.logger.info(f"Set announcement audio file: {path}")
        return True

    def get_state_requirements(self, state: str) -> Dict:
        """
        Get recording consent requirements for a US state

        Args:
            state: US state code (e.g., 'CA', 'FL')

        Returns:
            State requirements
        """
        # Two-party consent states (require all parties to consent)
        two_party_states = ["CA", "CT", "FL", "IL", "MD", "MA", "MT", "NH", "PA", "WA"]

        # One-party consent states (only one party needs to consent)
        one_party_states = [
            "AL",
            "AK",
            "AZ",
            "AR",
            "CO",
            "DC",
            "GA",
            "HI",
            "ID",
            "IN",
            "IA",
            "KS",
            "KY",
            "LA",
            "ME",
            "MI",
            "MN",
            "MS",
            "MO",
            "NE",
            "NV",
            "NJ",
            "NM",
            "NY",
            "NC",
            "ND",
            "OH",
            "OK",
            "OR",
            "RI",
            "SC",
            "SD",
            "TN",
            "TX",
            "UT",
            "VT",
            "VA",
            "WV",
            "WI",
            "WY",
        ]

        if state in two_party_states:
            return {
                "state": state,
                "consent_type": "two_party",
                "description": "All parties must consent to recording",
                "notification_required": True,
                "penalty": "Criminal and civil penalties may apply",
            }
        elif state in one_party_states:
            return {
                "state": state,
                "consent_type": "one_party",
                "description": "Only one party needs to consent",
                "notification_required": False,
                "recommendation": "Notification recommended for transparency",
            }
        else:
            return {
                "state": state,
                "consent_type": "unknown",
                "description": "Check local laws",
                "notification_required": True,  # Be safe
            }

    def get_statistics(self) -> Dict:
        """Get recording announcement statistics"""
        total_consent_requests = self.consent_accepted + self.consent_declined
        acceptance_rate = (
            (self.consent_accepted / total_consent_requests * 100)
            if total_consent_requests > 0
            else 0
        )

        return {
            "enabled": self.enabled,
            "announcements_played": self.announcements_played,
            "consent_requests": total_consent_requests,
            "consent_accepted": self.consent_accepted,
            "consent_declined": self.consent_declined,
            "acceptance_rate_percent": round(acceptance_rate, 2),
        }
