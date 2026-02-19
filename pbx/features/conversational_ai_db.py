"""
Database layer for Conversational AI Assistant
Provides persistence for conversations, intents, and statistics
"""

from datetime import UTC, datetime
from typing import Any

from pbx.utils.logger import get_logger


class ConversationalAIDatabase:
    """
    Database layer for conversational AI
    Stores conversations, messages, intents, and analytics
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
        """Create tables for conversational AI"""
        try:
            # Conversations table
            if self.db.db_type == "postgresql":
                sql_conversations = """
                CREATE TABLE IF NOT EXISTS ai_conversations (
                    id SERIAL PRIMARY KEY,
                    call_id VARCHAR(255) UNIQUE NOT NULL,
                    caller_id VARCHAR(50),
                    started_at TIMESTAMP NOT NULL,
                    ended_at TIMESTAMP,
                    final_intent VARCHAR(100),
                    message_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_messages = """
                CREATE TABLE IF NOT EXISTS ai_messages (
                    id SERIAL PRIMARY KEY,
                    conversation_id INTEGER REFERENCES ai_conversations(id) ON DELETE CASCADE,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_intents = """
                CREATE TABLE IF NOT EXISTS ai_intents (
                    id SERIAL PRIMARY KEY,
                    conversation_id INTEGER REFERENCES ai_conversations(id) ON DELETE CASCADE,
                    intent VARCHAR(100) NOT NULL,
                    confidence FLOAT,
                    entities JSONB,
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_config = """
                CREATE TABLE IF NOT EXISTS ai_configurations (
                    id SERIAL PRIMARY KEY,
                    provider VARCHAR(50) NOT NULL,
                    model VARCHAR(100),
                    api_key_encrypted BYTEA,
                    max_tokens INTEGER DEFAULT 150,
                    temperature FLOAT DEFAULT 0.7,
                    enabled BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            else:  # SQLite
                sql_conversations = """
                CREATE TABLE IF NOT EXISTS ai_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_id TEXT UNIQUE NOT NULL,
                    caller_id TEXT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    final_intent TEXT,
                    message_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """

                sql_messages = """
                CREATE TABLE IF NOT EXISTS ai_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id) ON DELETE CASCADE
                )
                """

                sql_intents = """
                CREATE TABLE IF NOT EXISTS ai_intents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER,
                    intent TEXT NOT NULL,
                    confidence REAL,
                    entities TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id) ON DELETE CASCADE
                )
                """

                sql_config = """
                CREATE TABLE IF NOT EXISTS ai_configurations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    model TEXT,
                    api_key_encrypted BLOB,
                    max_tokens INTEGER DEFAULT 150,
                    temperature REAL DEFAULT 0.7,
                    enabled INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """

            cursor = self.db.connection.cursor()
            cursor.execute(sql_conversations)
            cursor.execute(sql_messages)
            cursor.execute(sql_intents)
            cursor.execute(sql_config)
            self.db.connection.commit()

            self.logger.info("Conversational AI tables created successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error creating Conversational AI tables: {e}")
            return False

    def save_conversation(self, call_id: str, caller_id: str, started_at: datetime) -> int | None:
        """
        Save a new conversation

        Args:
            call_id: Unique call identifier
            caller_id: Caller's phone number
            started_at: When conversation started

        Returns:
            Conversation ID or None
        """
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                INSERT INTO ai_conversations (call_id, caller_id, started_at)
                VALUES (%s, %s, %s)
                RETURNING id
                """
            else:
                sql = """
                INSERT INTO ai_conversations (call_id, caller_id, started_at)
                VALUES (?, ?, ?)
                """

            params = (call_id, caller_id, started_at.isoformat())
            cursor.execute(sql, params)

            if self.db.db_type == "postgresql":
                conversation_id = cursor.fetchone()[0]
            else:
                conversation_id = cursor.lastrowid

            self.db.connection.commit()
            return conversation_id

        except Exception as e:
            self.logger.error(f"Error saving conversation: {e}")
            return None

    def save_message(
        self, conversation_id: int, role: str, content: str, timestamp: datetime
    ) -> None:
        """Save a message in the conversation"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                INSERT INTO ai_messages (conversation_id, role, content, timestamp)
                VALUES (%s, %s, %s, %s)
                """
            else:
                sql = """
                INSERT INTO ai_messages (conversation_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
                """

            params = (conversation_id, role, content, timestamp.isoformat())
            cursor.execute(sql, params)
            self.db.connection.commit()

        except Exception as e:
            self.logger.error(f"Error saving message: {e}")

    def save_intent(
        self,
        conversation_id: int,
        intent: str,
        confidence: float,
        entities: dict,
        timestamp: datetime,
    ) -> None:
        """Save detected intent"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                import json

                sql = """
                INSERT INTO ai_intents (conversation_id, intent, confidence, entities, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                """
                params = (
                    conversation_id,
                    intent,
                    confidence,
                    json.dumps(entities),
                    timestamp.isoformat(),
                )
            else:
                import json

                sql = """
                INSERT INTO ai_intents (conversation_id, intent, confidence, entities, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """
                params = (
                    conversation_id,
                    intent,
                    confidence,
                    json.dumps(entities),
                    timestamp.isoformat(),
                )

            cursor.execute(sql, params)
            self.db.connection.commit()

        except (ValueError, json.JSONDecodeError) as e:
            self.logger.error(f"Error saving intent: {e}")

    def end_conversation(self, call_id: str, final_intent: str, message_count: int) -> None:
        """Mark conversation as ended"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                UPDATE ai_conversations
                SET ended_at = %s, final_intent = %s, message_count = %s
                WHERE call_id = %s
                """
            else:
                sql = """
                UPDATE ai_conversations
                SET ended_at = ?, final_intent = ?, message_count = ?
                WHERE call_id = ?
                """

            params = (datetime.now(UTC).isoformat(), final_intent, message_count, call_id)
            cursor.execute(sql, params)
            self.db.connection.commit()

        except Exception as e:
            self.logger.error(f"Error ending conversation: {e}")

    def get_conversation_history(self, limit: int = 100) -> list[dict]:
        """Get recent conversation history"""
        try:
            cursor = self.db.connection.cursor()

            if self.db.db_type == "postgresql":
                sql = """
                SELECT c.*, COUNT(m.id) as msg_count
                FROM ai_conversations c
                LEFT JOIN ai_messages m ON c.id = m.conversation_id
                GROUP BY c.id
                ORDER BY c.started_at DESC
                LIMIT %s
                """
            else:
                sql = """
                SELECT c.*, COUNT(m.id) as msg_count
                FROM ai_conversations c
                LEFT JOIN ai_messages m ON c.id = m.conversation_id
                GROUP BY c.id
                ORDER BY c.started_at DESC
                LIMIT ?
                """

            cursor.execute(sql, (limit,))

            if self.db.db_type == "postgresql":
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row, strict=False)) for row in rows]
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row, strict=False)) for row in rows]

        except Exception as e:
            self.logger.error(f"Error getting conversation history: {e}")
            return []

    def get_intent_statistics(self) -> dict:
        """Get intent usage statistics"""
        try:
            cursor = self.db.connection.cursor()

            sql = """
            SELECT intent, COUNT(*) as count
            FROM ai_intents
            GROUP BY intent
            ORDER BY count DESC
            """

            cursor.execute(sql)

            if self.db.db_type == "postgresql":
                [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return {row[0]: row[1] for row in rows}
            rows = cursor.fetchall()
            return {row[0]: row[1] for row in rows}

        except Exception as e:
            self.logger.error(f"Error getting intent statistics: {e}")
            return {}
