"""
Database layer for Call Quality Prediction
Provides persistence for quality metrics, predictions, and alerts
"""

import json
from datetime import UTC, datetime
from typing import Any

from pbx.utils.logger import get_logger


class CallQualityPredictionDatabase:
    """
    Database layer for call quality prediction
    Stores network metrics, predictions, and quality alerts
    """

    def __init__(self, db_backend: Any | None) -> None:
        """
        Initialize database layer

        Args:
            db_backend: DatabaseBackend instance
        """
        self.logger = get_logger()
        self.db = db_backend

    def create_tables(self) -> bool:
        """Create tables for call quality prediction"""
        try:
            if self.db.db_type == "postgresql":
                sql_metrics = """
                CREATE TABLE IF NOT EXISTS quality_metrics (
                    id SERIAL PRIMARY KEY,
                    call_id VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    latency INTEGER,
                    jitter INTEGER,
                    packet_loss FLOAT,
                    bandwidth INTEGER,
                    mos_score FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_predictions = """
                CREATE TABLE IF NOT EXISTS quality_predictions (
                    id SERIAL PRIMARY KEY,
                    call_id VARCHAR(255) NOT NULL,
                    current_mos FLOAT,
                    predicted_mos FLOAT,
                    predicted_quality_level VARCHAR(20),
                    current_packet_loss FLOAT,
                    predicted_packet_loss FLOAT,
                    alert BOOLEAN DEFAULT FALSE,
                    alert_reasons JSONB,
                    recommendations JSONB,
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_alerts = """
                CREATE TABLE IF NOT EXISTS quality_alerts (
                    id SERIAL PRIMARY KEY,
                    call_id VARCHAR(255) NOT NULL,
                    alert_type VARCHAR(50) NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    message TEXT,
                    metric_value FLOAT,
                    threshold_value FLOAT,
                    timestamp TIMESTAMP NOT NULL,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_trends = """
                CREATE TABLE IF NOT EXISTS quality_trends (
                    id SERIAL PRIMARY KEY,
                    endpoint VARCHAR(100) NOT NULL,
                    date DATE NOT NULL,
                    avg_mos FLOAT,
                    avg_latency INTEGER,
                    avg_jitter INTEGER,
                    avg_packet_loss FLOAT,
                    call_count INTEGER DEFAULT 0,
                    alert_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(endpoint, date)
                )
                """
            else:  # SQLite
                sql_metrics = """
                CREATE TABLE IF NOT EXISTS quality_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    latency INTEGER,
                    jitter INTEGER,
                    packet_loss REAL,
                    bandwidth INTEGER,
                    mos_score REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_predictions = """
                CREATE TABLE IF NOT EXISTS quality_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_id TEXT NOT NULL,
                    current_mos REAL,
                    predicted_mos REAL,
                    predicted_quality_level TEXT,
                    current_packet_loss REAL,
                    predicted_packet_loss REAL,
                    alert INTEGER DEFAULT 0,
                    alert_reasons TEXT,
                    recommendations TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_alerts = """
                CREATE TABLE IF NOT EXISTS quality_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_id TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT,
                    metric_value REAL,
                    threshold_value REAL,
                    timestamp TEXT NOT NULL,
                    acknowledged INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_trends = """
                CREATE TABLE IF NOT EXISTS quality_trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    date TEXT NOT NULL,
                    avg_mos REAL,
                    avg_latency INTEGER,
                    avg_jitter INTEGER,
                    avg_packet_loss REAL,
                    call_count INTEGER DEFAULT 0,
                    alert_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(endpoint, date)
                )
                """

            cursor = self.db.connection.cursor()
            cursor.execute(sql_metrics)
            cursor.execute(sql_predictions)
            cursor.execute(sql_alerts)
            cursor.execute(sql_trends)
            self.db.connection.commit()

            self.logger.info("Call quality prediction tables created successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error creating quality prediction tables: {e}")
            return False

    def save_metrics(self, call_id: str, metrics: dict) -> None:
        """Save quality metrics"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                INSERT INTO quality_metrics
                (call_id, timestamp, latency, jitter, packet_loss, bandwidth, mos_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
            else:
                sql = """
                INSERT INTO quality_metrics
                (call_id, timestamp, latency, jitter, packet_loss, bandwidth, mos_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """

            params = (
                call_id,
                metrics.get("timestamp", datetime.now(UTC).isoformat()),
                metrics.get("latency"),
                metrics.get("jitter"),
                metrics.get("packet_loss"),
                metrics.get("bandwidth"),
                metrics.get("mos_score"),
            )

            cursor.execute(sql, params)
            self.db.connection.commit()

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error saving quality metrics: {e}")

    def save_prediction(self, call_id: str, prediction: dict) -> None:
        """Save quality prediction"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                INSERT INTO quality_predictions
                (call_id, current_mos, predicted_mos, predicted_quality_level,
                 current_packet_loss, predicted_packet_loss, alert, alert_reasons,
                 recommendations, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    call_id,
                    prediction.get("current_mos"),
                    prediction.get("predicted_mos"),
                    prediction.get("predicted_quality_level"),
                    prediction.get("current_packet_loss"),
                    prediction.get("predicted_packet_loss"),
                    prediction.get("alert", False),
                    json.dumps(prediction.get("alert_reasons", [])),
                    json.dumps(prediction.get("recommendations", [])),
                    prediction.get("timestamp", datetime.now(UTC)),
                )
            else:
                sql = """
                INSERT INTO quality_predictions
                (call_id, current_mos, predicted_mos, predicted_quality_level,
                 current_packet_loss, predicted_packet_loss, alert, alert_reasons,
                 recommendations, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    call_id,
                    prediction.get("current_mos"),
                    prediction.get("predicted_mos"),
                    prediction.get("predicted_quality_level"),
                    prediction.get("current_packet_loss"),
                    prediction.get("predicted_packet_loss"),
                    1 if prediction.get("alert", False) else 0,
                    json.dumps(prediction.get("alert_reasons", [])),
                    json.dumps(prediction.get("recommendations", [])),
                    prediction.get("timestamp", datetime.now(UTC).isoformat()),
                )

            cursor.execute(sql, params)
            self.db.connection.commit()

        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as e:
            self.logger.error(f"Error saving prediction: {e}")

    def save_alert(
        self,
        call_id: str,
        alert_type: str,
        severity: str,
        message: str,
        metric_value: float,
        threshold_value: float,
    ) -> None:
        """Save quality alert"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                INSERT INTO quality_alerts
                (call_id, alert_type, severity, message, metric_value, threshold_value, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
            else:
                sql = """
                INSERT INTO quality_alerts
                (call_id, alert_type, severity, message, metric_value, threshold_value, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """

            params = (
                call_id,
                alert_type,
                severity,
                message,
                metric_value,
                threshold_value,
                datetime.now(UTC).isoformat(),
            )
            cursor.execute(sql, params)
            self.db.connection.commit()

        except Exception as e:
            self.logger.error(f"Error saving alert: {e}")

    def get_recent_predictions(self, limit: int = 100) -> list[dict]:
        """Get recent predictions"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                SELECT id, call_id, current_mos, predicted_mos, predicted_quality_level, current_packet_loss, predicted_packet_loss, alert, alert_reasons, recommendations, timestamp, created_at FROM quality_predictions
                ORDER BY timestamp DESC
                LIMIT %s
                """
            else:
                sql = """
                SELECT id, call_id, current_mos, predicted_mos, predicted_quality_level, current_packet_loss, predicted_packet_loss, alert, alert_reasons, recommendations, timestamp, created_at FROM quality_predictions
                ORDER BY timestamp DESC
                LIMIT ?
                """

            cursor.execute(sql, (limit,))
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row, strict=False)) for row in rows]

        except Exception as e:
            self.logger.error(f"Error getting predictions: {e}")
            return []

    def get_active_alerts(self) -> list[dict]:
        """Get active (unacknowledged) alerts"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                SELECT id, call_id, alert_type, severity, message, metric_value, threshold_value, timestamp, acknowledged, created_at FROM quality_alerts
                WHERE acknowledged = FALSE
                ORDER BY timestamp DESC
                """
            else:
                sql = """
                SELECT id, call_id, alert_type, severity, message, metric_value, threshold_value, timestamp, acknowledged, created_at FROM quality_alerts
                WHERE acknowledged = 0
                ORDER BY timestamp DESC
                """

            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row, strict=False)) for row in rows]

        except Exception as e:
            self.logger.error(f"Error getting active alerts: {e}")
            return []

    def acknowledge_alert(self, alert_id: int) -> bool:
        """Mark alert as acknowledged"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = "UPDATE quality_alerts SET acknowledged = TRUE WHERE id = %s"
            else:
                sql = "UPDATE quality_alerts SET acknowledged = 1 WHERE id = ?"

            cursor.execute(sql, (alert_id,))
            self.db.connection.commit()

        except Exception as e:
            self.logger.error(f"Error acknowledging alert: {e}")

    def update_daily_trends(self, endpoint: str, metrics: dict) -> None:
        """Update daily trend statistics"""
        try:
            cursor = self.db.connection.cursor()
            today = datetime.now(UTC).date().isoformat()

            if self.db.db_type == "postgresql":
                sql = """
                INSERT INTO quality_trends
                (endpoint, date, avg_mos, avg_latency, avg_jitter, avg_packet_loss, call_count, alert_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (endpoint, date) DO UPDATE
                SET avg_mos = EXCLUDED.avg_mos,
                    avg_latency = EXCLUDED.avg_latency,
                    avg_jitter = EXCLUDED.avg_jitter,
                    avg_packet_loss = EXCLUDED.avg_packet_loss,
                    call_count = quality_trends.call_count + 1,
                    alert_count = quality_trends.alert_count + EXCLUDED.alert_count
                """
            else:
                sql = """
                INSERT OR REPLACE INTO quality_trends
                (endpoint, date, avg_mos, avg_latency, avg_jitter, avg_packet_loss, call_count, alert_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """

            params = (
                endpoint,
                today,
                metrics.get("avg_mos"),
                metrics.get("avg_latency"),
                metrics.get("avg_jitter"),
                metrics.get("avg_packet_loss"),
                metrics.get("call_count", 1),
                metrics.get("alert_count", 0),
            )

            cursor.execute(sql, params)
            self.db.connection.commit()

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error updating daily trends: {e}")

    def get_statistics(self) -> dict:
        """Get quality prediction statistics"""
        try:
            cursor = self.db.connection.cursor()

            # Total predictions
            cursor.execute("SELECT COUNT(*) FROM quality_predictions")
            total_predictions = cursor.fetchone()[0]

            # Predictions with alerts
            if self.db.db_type == "postgresql":
                cursor.execute("SELECT COUNT(*) FROM quality_predictions WHERE alert = TRUE")
            else:
                cursor.execute("SELECT COUNT(*) FROM quality_predictions WHERE alert = 1")
            alerts_generated = cursor.fetchone()[0]

            # Active alerts
            if self.db.db_type == "postgresql":
                cursor.execute("SELECT COUNT(*) FROM quality_alerts WHERE acknowledged = FALSE")
            else:
                cursor.execute("SELECT COUNT(*) FROM quality_alerts WHERE acknowledged = 0")
            active_alerts = cursor.fetchone()[0]

            # Average MOS from recent metrics
            if self.db.db_type == "postgresql":
                sql = """
                    SELECT AVG(mos_score) FROM quality_metrics
                    WHERE timestamp > NOW() - INTERVAL '24 hours'
                """
            else:
                sql = """
                    SELECT AVG(mos_score) FROM quality_metrics
                    WHERE timestamp > datetime('now', '-24 hours')
                """

            cursor.execute(sql)
            row = cursor.fetchone()
            avg_mos_24h = row[0] if row and row[0] else 0.0

            return {
                "total_predictions": total_predictions,
                "alerts_generated": alerts_generated,
                "active_alerts": active_alerts,
                "avg_mos_24h": avg_mos_24h,
            }

        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {}
