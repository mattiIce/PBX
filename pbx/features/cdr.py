"""
CDR (Call Detail Records) and Statistics System
Tracks all calls for billing, analytics, and reporting
"""

import json
import os
from datetime import datetime, timezone
from enum import Enum

from pbx.utils.logger import get_logger


class CallDisposition(Enum):
    """Call outcome"""

    ANSWERED = "answered"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CDRRecord:
    """Represents a single call detail record"""

    def __init__(self, call_id, from_extension, to_extension):
        """
        Initialize CDR record

        Args:
            call_id: Call identifier
            from_extension: Calling extension
            to_extension: Called extension
        """
        self.call_id = call_id
        self.from_extension = from_extension
        self.to_extension = to_extension
        self.start_time = datetime.now(timezone.utc)
        self.answer_time = None
        self.end_time = None
        self.disposition = None
        self.duration = 0  # Total call duration
        self.billsec = 0  # Billable seconds (time after answer)
        self.recording_file = None
        self.hangup_cause = None
        self.user_agent = None

    def mark_answered(self):
        """Mark call as answered"""
        self.answer_time = datetime.now(timezone.utc)
        self.disposition = CallDisposition.ANSWERED

    def mark_ended(self, hangup_cause=None):
        """
        Mark call as ended

        Args:
            hangup_cause: Reason for hangup
        """
        self.end_time = datetime.now(timezone.utc)
        self.hangup_cause = hangup_cause

        # Calculate durations
        self.duration = (self.end_time - self.start_time).total_seconds()

        if self.answer_time:
            self.billsec = (self.end_time - self.answer_time).total_seconds()

        if not self.disposition:
            self.disposition = CallDisposition.FAILED

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "call_id": self.call_id,
            "from_extension": self.from_extension,
            "to_extension": self.to_extension,
            "start_time": self.start_time.isoformat(),
            "answer_time": self.answer_time.isoformat() if self.answer_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "disposition": self.disposition.value if self.disposition else None,
            "duration": self.duration,
            "billsec": self.billsec,
            "recording_file": self.recording_file,
            "hangup_cause": self.hangup_cause,
            "user_agent": self.user_agent,
        }


class CDRSystem:
    """Manages call detail records"""

    def __init__(self, storage_path="cdr"):
        """
        Initialize CDR system

        Args:
            storage_path: Path to store CDR files
        """
        self.storage_path = storage_path
        self.active_records = {}  # call_id -> CDRRecord
        self.logger = get_logger()

        os.makedirs(storage_path, exist_ok=True)

    def start_record(self, call_id, from_extension, to_extension):
        """
        Start CDR record for new call

        Args:
            call_id: Call identifier
            from_extension: Calling extension
            to_extension: Called extension

        Returns:
            CDRRecord object
        """
        record = CDRRecord(call_id, from_extension, to_extension)
        self.active_records[call_id] = record
        self.logger.debug(f"Started CDR record for call {call_id}")
        return record

    def mark_answered(self, call_id):
        """
        Mark call as answered

        Args:
            call_id: Call identifier
        """
        record = self.active_records.get(call_id)
        if record:
            record.mark_answered()

    def end_record(self, call_id, hangup_cause=None):
        """
        End CDR record

        Args:
            call_id: Call identifier
            hangup_cause: Reason for hangup
        """
        record = self.active_records.get(call_id)
        if record:
            record.mark_ended(hangup_cause)
            self._save_record(record)
            del self.active_records[call_id]
            self.logger.debug(f"Ended CDR record for call {call_id}")

    def set_recording(self, call_id, recording_file):
        """
        set recording file for call

        Args:
            call_id: Call identifier
            recording_file: Path to recording file
        """
        record = self.active_records.get(call_id)
        if record:
            record.recording_file = recording_file

    def _save_record(self, record):
        """
        Save CDR record to file

        Args:
            record: CDRRecord object
        """
        # Save to daily file
        date_str = record.start_time.strftime("%Y-%m-%d")
        filename = os.path.join(self.storage_path, f"cdr_{date_str}.jsonl")

        try:
            with open(filename, "a") as f:
                json.dump(record.to_dict(), f)
                f.write("\n")
        except Exception as e:
            self.logger.error(f"Error saving CDR record: {e}")

    def get_records(self, date=None, limit=100):
        """
        Get CDR records

        Args:
            date: Date string (YYYY-MM-DD) or None for today
            limit: Maximum number of records

        Returns:
            list of CDR dictionaries
        """
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        filename = os.path.join(self.storage_path, f"cdr_{date}.jsonl")

        if not os.path.exists(filename):
            return []

        records = []
        try:
            with open(filename, "r") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
                        if len(records) >= limit:
                            break
        except Exception as e:
            self.logger.error(f"Error reading CDR records: {e}")

        return records

    def get_statistics(self, date=None):
        """
        Get call statistics

        Args:
            date: Date string (YYYY-MM-DD) or None for today

        Returns:
            Dictionary with statistics
        """
        records = self.get_records(date, limit=10000)

        total_calls = len(records)
        answered_calls = sum(1 for r in records if r.get("disposition") == "answered")
        failed_calls = sum(1 for r in records if r.get("disposition") == "failed")

        total_duration = sum(r.get("duration", 0) for r in records)
        total_billsec = sum(r.get("billsec", 0) for r in records)

        avg_duration = total_duration / total_calls if total_calls > 0 else 0
        answer_rate = (answered_calls / total_calls * 100) if total_calls > 0 else 0

        return {
            "date": date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "total_calls": total_calls,
            "answered_calls": answered_calls,
            "failed_calls": failed_calls,
            "answer_rate": round(answer_rate, 2),
            "total_duration": round(total_duration, 2),
            "total_billsec": round(total_billsec, 2),
            "average_duration": round(avg_duration, 2),
        }

    def get_extension_statistics(self, extension, date=None):
        """
        Get statistics for specific extension

        Args:
            extension: Extension number
            date: Date string or None for today

        Returns:
            Dictionary with statistics
        """
        records = self.get_records(date, limit=10000)

        # Filter for this extension
        ext_records = [
            r
            for r in records
            if r.get("from_extension") == extension or r.get("to_extension") == extension
        ]

        outbound = sum(1 for r in ext_records if r.get("from_extension") == extension)
        inbound = sum(1 for r in ext_records if r.get("to_extension") == extension)

        return {
            "extension": extension,
            "date": date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "total_calls": len(ext_records),
            "outbound_calls": outbound,
            "inbound_calls": inbound,
        }
