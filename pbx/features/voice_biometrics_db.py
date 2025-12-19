"""
Database layer for Voice Biometrics
Provides persistence for voice profiles, enrollments, and verifications
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

from pbx.utils.logger import get_logger


class VoiceBiometricsDatabase:
    """
    Database layer for voice biometrics
    Stores voice profiles, enrollment data, and verification history
    """

    def __init__(self, db_backend):
        """
        Initialize database layer

        Args:
            db_backend: DatabaseBackend instance
        """
        self.logger = get_logger()
        self.db = db_backend

    def create_tables(self):
        """Create tables for voice biometrics"""
        try:
            # Voice profiles table
            if self.db.db_type == "postgresql":
                sql_profiles = """
                CREATE TABLE IF NOT EXISTS voice_profiles (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) UNIQUE NOT NULL,
                    extension VARCHAR(20),
                    status VARCHAR(20) NOT NULL,
                    enrollment_samples INTEGER DEFAULT 0,
                    required_samples INTEGER DEFAULT 3,
                    voiceprint_data BYTEA,
                    successful_verifications INTEGER DEFAULT 0,
                    failed_verifications INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_enrollments = """
                CREATE TABLE IF NOT EXISTS voice_enrollments (
                    id SERIAL PRIMARY KEY,
                    profile_id INTEGER REFERENCES voice_profiles(id) ON DELETE CASCADE,
                    sample_number INTEGER NOT NULL,
                    audio_hash VARCHAR(64),
                    quality_score FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_verifications = """
                CREATE TABLE IF NOT EXISTS voice_verifications (
                    id SERIAL PRIMARY KEY,
                    profile_id INTEGER REFERENCES voice_profiles(id) ON DELETE CASCADE,
                    call_id VARCHAR(255),
                    verified BOOLEAN NOT NULL,
                    confidence FLOAT,
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_fraud = """
                CREATE TABLE IF NOT EXISTS voice_fraud_detections (
                    id SERIAL PRIMARY KEY,
                    call_id VARCHAR(255),
                    caller_id VARCHAR(50),
                    fraud_detected BOOLEAN NOT NULL,
                    risk_score FLOAT,
                    indicators JSONB,
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            else:  # SQLite
                sql_profiles = """
                CREATE TABLE IF NOT EXISTS voice_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    extension TEXT,
                    status TEXT NOT NULL,
                    enrollment_samples INTEGER DEFAULT 0,
                    required_samples INTEGER DEFAULT 3,
                    voiceprint_data BLOB,
                    successful_verifications INTEGER DEFAULT 0,
                    failed_verifications INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_enrollments = """
                CREATE TABLE IF NOT EXISTS voice_enrollments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER,
                    sample_number INTEGER NOT NULL,
                    audio_hash TEXT,
                    quality_score REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (profile_id) REFERENCES voice_profiles(id) ON DELETE CASCADE
                )
                """

                sql_verifications = """
                CREATE TABLE IF NOT EXISTS voice_verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER,
                    call_id TEXT,
                    verified INTEGER NOT NULL,
                    confidence REAL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (profile_id) REFERENCES voice_profiles(id) ON DELETE CASCADE
                )
                """

                sql_fraud = """
                CREATE TABLE IF NOT EXISTS voice_fraud_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_id TEXT,
                    caller_id TEXT,
                    fraud_detected INTEGER NOT NULL,
                    risk_score REAL,
                    indicators TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """

            cursor = self.db.connection.cursor()
            cursor.execute(sql_profiles)
            cursor.execute(sql_enrollments)
            cursor.execute(sql_verifications)
            cursor.execute(sql_fraud)
            self.db.connection.commit()

            self.logger.info("Voice biometrics tables created successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error creating voice biometrics tables: {e}")
            return False

    def save_profile(self, user_id: str, extension: str, status: str) -> Optional[int]:
        """Save a new voice profile"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                INSERT INTO voice_profiles (user_id, extension, status)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET extension = EXCLUDED.extension, status = EXCLUDED.status, last_updated = CURRENT_TIMESTAMP
                RETURNING id
                """
            else:
                sql = """
                INSERT OR REPLACE INTO voice_profiles (user_id, extension, status, last_updated)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """

            params = (user_id, extension, status)
            cursor.execute(sql, params)

            if self.db.db_type == "postgresql":
                profile_id = cursor.fetchone()[0]
            else:
                profile_id = cursor.lastrowid

            self.db.connection.commit()
            return profile_id

        except Exception as e:
            self.logger.error(f"Error saving voice profile: {e}")
            return None

    def get_profile(self, user_id: str) -> Optional[Dict]:
        """Get voice profile by user ID"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = "SELECT * FROM voice_profiles WHERE user_id = %s"
            else:
                sql = "SELECT * FROM voice_profiles WHERE user_id = ?"

            cursor.execute(sql, (user_id,))
            row = cursor.fetchone()

            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None

        except Exception as e:
            self.logger.error(f"Error getting voice profile: {e}")
            return None

    def update_enrollment_progress(self, user_id: str, samples: int):
        """Update enrollment progress"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                UPDATE voice_profiles
                SET enrollment_samples = %s, last_updated = CURRENT_TIMESTAMP
                WHERE user_id = %s
                """
            else:
                sql = """
                UPDATE voice_profiles
                SET enrollment_samples = ?, last_updated = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """

            cursor.execute(sql, (samples, user_id))
            self.db.connection.commit()

        except Exception as e:
            self.logger.error(f"Error updating enrollment progress: {e}")

    def save_verification(self, user_id: str, call_id: str, verified: bool, confidence: float):
        """Save verification result"""
        try:
            # Get profile ID
            profile = self.get_profile(user_id)
            if not profile:
                return

            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                INSERT INTO voice_verifications (profile_id, call_id, verified, confidence, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                """
                params = (profile["id"], call_id, verified, confidence, datetime.now())
            else:
                sql = """
                INSERT INTO voice_verifications (profile_id, call_id, verified, confidence, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """
                params = (
                    profile["id"],
                    call_id,
                    1 if verified else 0,
                    confidence,
                    datetime.now().isoformat(),
                )

            cursor.execute(sql, params)

            # Update profile stats
            if self.db.db_type == "postgresql":
                if verified:
                    update_sql = "UPDATE voice_profiles SET successful_verifications = successful_verifications + 1 WHERE user_id = %s"
                else:
                    update_sql = "UPDATE voice_profiles SET failed_verifications = failed_verifications + 1 WHERE user_id = %s"
            else:
                if verified:
                    update_sql = "UPDATE voice_profiles SET successful_verifications = successful_verifications + 1 WHERE user_id = ?"
                else:
                    update_sql = "UPDATE voice_profiles SET failed_verifications = failed_verifications + 1 WHERE user_id = ?"

            cursor.execute(update_sql, (user_id,))
            self.db.connection.commit()

        except Exception as e:
            self.logger.error(f"Error saving verification: {e}")

    def save_fraud_detection(
        self,
        call_id: str,
        caller_id: str,
        fraud_detected: bool,
        risk_score: float,
        indicators: List[str],
    ):
        """Save fraud detection result"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                INSERT INTO voice_fraud_detections (call_id, caller_id, fraud_detected, risk_score, indicators, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                params = (
                    call_id,
                    caller_id,
                    fraud_detected,
                    risk_score,
                    json.dumps(indicators),
                    datetime.now(),
                )
            else:
                sql = """
                INSERT INTO voice_fraud_detections (call_id, caller_id, fraud_detected, risk_score, indicators, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                params = (
                    call_id,
                    caller_id,
                    1 if fraud_detected else 0,
                    risk_score,
                    json.dumps(indicators),
                    datetime.now().isoformat(),
                )

            cursor.execute(sql, params)
            self.db.connection.commit()

        except Exception as e:
            self.logger.error(f"Error saving fraud detection: {e}")

    def get_statistics(self) -> Dict:
        """Get voice biometrics statistics"""
        try:
            cursor = self.db.connection.cursor()

            # Total profiles
            cursor.execute("SELECT COUNT(*) FROM voice_profiles")
            total_profiles = cursor.fetchone()[0]

            # Enrolled profiles
            if self.db.db_type == "postgresql":
                cursor.execute("SELECT COUNT(*) FROM voice_profiles WHERE status = 'enrolled'")
            else:
                cursor.execute("SELECT COUNT(*) FROM voice_profiles WHERE status = 'enrolled'")
            enrolled = cursor.fetchone()[0]

            # Total verifications
            cursor.execute("SELECT COUNT(*) FROM voice_verifications")
            total_verifications = cursor.fetchone()[0]

            # Successful verifications
            if self.db.db_type == "postgresql":
                cursor.execute("SELECT COUNT(*) FROM voice_verifications WHERE verified = TRUE")
            else:
                cursor.execute("SELECT COUNT(*) FROM voice_verifications WHERE verified = 1")
            successful = cursor.fetchone()[0]

            # Fraud detections
            if self.db.db_type == "postgresql":
                cursor.execute(
                    "SELECT COUNT(*) FROM voice_fraud_detections WHERE fraud_detected = TRUE"
                )
            else:
                cursor.execute(
                    "SELECT COUNT(*) FROM voice_fraud_detections WHERE fraud_detected = 1"
                )
            fraud_detected = cursor.fetchone()[0]

            return {
                "total_profiles": total_profiles,
                "enrolled_profiles": enrolled,
                "total_verifications": total_verifications,
                "successful_verifications": successful,
                "failed_verifications": total_verifications - successful,
                "fraud_attempts_detected": fraud_detected,
            }

        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {}
