"""
Database migration system for PBX features
Manages schema versioning and migrations
"""

from typing import Dict, List, Optional

from pbx.utils.logger import get_logger


class MigrationManager:
    """
    Manages database schema migrations
    Tracks versions and applies migrations in order
    """

    def __init__(self, db_backend):
        """
        Initialize migration manager

        Args:
            db_backend: DatabaseBackend instance
        """
        self.logger = get_logger()
        self.db = db_backend
        self.migrations = []

    def _build_migration_sql(self, template: str) -> str:
        """
        Build database-specific SQL from a template

        Converts template placeholders to database-specific syntax.

        Args:
            template: SQL template with placeholders

        Returns:
            Database-specific SQL string
        """
        replacements = {
            "{SERIAL}": (
                "SERIAL PRIMARY KEY"
                if self.db.db_type == "postgresql"
                else "INTEGER PRIMARY KEY AUTOINCREMENT"
            ),
            "{BOOLEAN_TRUE}": "TRUE" if self.db.db_type == "postgresql" else "1",
            "{BOOLEAN_FALSE}": "FALSE" if self.db.db_type == "postgresql" else "0",
            "{BYTEA}": "BYTEA" if self.db.db_type == "postgresql" else "BLOB",
            "{TEXT}": "TEXT",
        }

        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        return result

    def register_migration(self, version: int, name: str, sql: str):
        """
        Register a migration

        Args:
            version: Migration version number
            name: Migration name/description
            sql: SQL to execute
        """
        self.migrations.append({"version": version, "name": name, "sql": sql})

    def init_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        try:
            if self.db.db_type == "postgresql":
                sql = """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            else:  # SQLite
                sql = """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """

            self.db.execute(sql)
            self.logger.info("Migrations table initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize migrations table: {e}")
            return False

    def get_current_version(self) -> int:
        """
        Get current schema version

        Returns:
            int: Current version number
        """
        try:
            result = self.db.fetch_one("SELECT MAX(version) as max_version FROM schema_migrations")
            if result and result.get("max_version") is not None:
                return result["max_version"]
            return 0
        except Exception as e:
            self.logger.warning(f"Could not get current version: {e}")
            return 0

    def apply_migrations(self, target_version: Optional[int] = None) -> bool:
        """
        Apply pending migrations

        Args:
            target_version: Version to migrate to (None = latest)

        Returns:
            bool: True if successful
        """
        try:
            self.init_migrations_table()
            current_version = self.get_current_version()

            # Sort migrations by version
            self.migrations.sort(key=lambda x: x["version"])

            # Filter migrations to apply
            pending = [m for m in self.migrations if m["version"] > current_version]

            if target_version:
                pending = [m for m in pending if m["version"] <= target_version]

            if not pending:
                self.logger.info("No pending migrations")
                return True

            self.logger.info(f"Applying {len(pending)} migrations...")

            for migration in pending:
                self.logger.info(f"Applying migration {migration['version']}: {migration['name']}")

                # Execute migration SQL using execute_script for multi-statement support
                self.db.execute_script(migration["sql"])

                # Record migration
                self.db.execute(
                    (
                        "INSERT INTO schema_migrations (version, name) VALUES (?, ?)"
                        if self.db.db_type == "sqlite"
                        else "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)"
                    ),
                    (migration["version"], migration["name"]),
                )

                self.logger.info(f"✓ Migration {migration['version']} applied")

            self.logger.info("All migrations applied successfully")
            return True

        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            return False

    def get_migration_status(self) -> List[Dict]:
        """
        Get status of all migrations

        Returns:
            List of migration status dictionaries
        """
        try:
            self.get_current_version()

            # Get applied migrations
            applied = self.db.fetch_all(
                "SELECT version, name, applied_at FROM schema_migrations ORDER BY version"
            )
            applied_versions = {row["version"]: row for row in (applied or [])}

            status = []
            for migration in sorted(self.migrations, key=lambda x: x["version"]):
                version = migration["version"]
                if version in applied_versions:
                    status.append(
                        {
                            "version": version,
                            "name": migration["name"],
                            "status": "applied",
                            "applied_at": applied_versions[version]["applied_at"],
                        }
                    )
                else:
                    status.append(
                        {
                            "version": version,
                            "name": migration["name"],
                            "status": "pending",
                            "applied_at": None,
                        }
                    )

            return status
        except Exception as e:
            self.logger.error(f"Failed to get migration status: {e}")
            return []


def register_all_migrations(manager: MigrationManager):
    """
    Register all framework feature migrations

    Args:
        manager: MigrationManager instance
    """
    # Migration 1000: AI-Powered Features Framework
    manager.register_migration(
        1000,
        "AI Features Framework",
        manager._build_migration_sql(
            """
        -- Real-time speech analytics
        CREATE TABLE IF NOT EXISTS speech_analytics_configs (
            id {SERIAL},
            extension VARCHAR(20) NOT NULL,
            enabled BOOLEAN DEFAULT {BOOLEAN_TRUE},
            transcription_enabled BOOLEAN DEFAULT {BOOLEAN_TRUE},
            sentiment_enabled BOOLEAN DEFAULT {BOOLEAN_TRUE},
            summarization_enabled BOOLEAN DEFAULT {BOOLEAN_TRUE},
            keywords {TEXT},
            alert_threshold FLOAT DEFAULT 0.7,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Conversational AI assistant
        CREATE TABLE IF NOT EXISTS ai_assistant_configs (
            id {SERIAL},
            extension VARCHAR(20) NOT NULL,
            enabled BOOLEAN DEFAULT {BOOLEAN_FALSE},
            auto_response_enabled BOOLEAN DEFAULT {BOOLEAN_FALSE},
            greeting_template {TEXT},
            response_language VARCHAR(10) DEFAULT 'en',
            confidence_threshold FLOAT DEFAULT 0.8,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Voice biometrics
        CREATE TABLE IF NOT EXISTS voice_biometrics (
            id {SERIAL},
            extension VARCHAR(20) NOT NULL,
            voiceprint_data {BYTEA},
            enrollment_status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_verified TIMESTAMP
        );

        -- Call quality prediction
        CREATE TABLE IF NOT EXISTS call_quality_predictions (
            id {SERIAL},
            call_id VARCHAR(50),
            predicted_mos FLOAT,
            predicted_issues {TEXT},
            actual_mos FLOAT,
            prediction_accuracy FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
        ),
    )

    # Migration 1001: Video Conferencing Framework
    manager.register_migration(
        1001,
        "Video Conferencing Framework",
        manager._build_migration_sql(
            """
        -- Video conferencing rooms
        CREATE TABLE IF NOT EXISTS video_conference_rooms (
            id {SERIAL},
            room_name VARCHAR(100) NOT NULL UNIQUE,
            owner_extension VARCHAR(20),
            max_participants INTEGER DEFAULT 10,
            enable_4k BOOLEAN DEFAULT {BOOLEAN_FALSE},
            enable_screen_share BOOLEAN DEFAULT {BOOLEAN_TRUE},
            recording_enabled BOOLEAN DEFAULT {BOOLEAN_FALSE},
            password_hash VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Video conference participants
        CREATE TABLE IF NOT EXISTS video_conference_participants (
            id {SERIAL},
            room_id INTEGER REFERENCES video_conference_rooms(id),
            extension VARCHAR(20),
            display_name VARCHAR(100),
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            left_at TIMESTAMP,
            video_enabled BOOLEAN DEFAULT {BOOLEAN_TRUE},
            audio_enabled BOOLEAN DEFAULT {BOOLEAN_TRUE},
            screen_sharing BOOLEAN DEFAULT {BOOLEAN_FALSE}
        );

        -- Video codec configurations
        CREATE TABLE IF NOT EXISTS video_codec_configs (
            id {SERIAL},
            codec_name VARCHAR(50) NOT NULL,
            enabled BOOLEAN DEFAULT {BOOLEAN_TRUE},
            priority INTEGER DEFAULT 100,
            max_resolution VARCHAR(20) DEFAULT '1920x1080',
            max_bitrate INTEGER DEFAULT 2000,
            min_bitrate INTEGER DEFAULT 500
        );
    """
        ),
    )

    # Migration 1002: Emergency Services Framework
    manager.register_migration(
        1002,
        "Emergency Services Framework",
        manager._build_migration_sql(
            """
        -- Nomadic E911 locations
        CREATE TABLE IF NOT EXISTS nomadic_e911_locations (
            id {SERIAL},
            extension VARCHAR(20) NOT NULL,
            ip_address VARCHAR(45),
            location_name VARCHAR(100),
            street_address VARCHAR(255),
            city VARCHAR(100),
            state VARCHAR(50),
            postal_code VARCHAR(20),
            country VARCHAR(50) DEFAULT 'USA',
            building VARCHAR(100),
            floor VARCHAR(20),
            room VARCHAR(20),
            latitude DECIMAL(10, 8),
            longitude DECIMAL(11, 8),
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            auto_detected BOOLEAN DEFAULT {BOOLEAN_FALSE}
        );

        -- E911 location updates log
        CREATE TABLE IF NOT EXISTS e911_location_updates (
            id {SERIAL},
            extension VARCHAR(20),
            old_location TEXT,
            new_location TEXT,
            update_source VARCHAR(50),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Multi-site E911 configurations
        CREATE TABLE IF NOT EXISTS multi_site_e911_configs (
            id {SERIAL},
            site_name VARCHAR(100) NOT NULL,
            ip_range_start VARCHAR(45),
            ip_range_end VARCHAR(45),
            emergency_trunk VARCHAR(50),
            psap_number VARCHAR(20),
            elin VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
        ),
    )

    # Migration 1003: Analytics & Reporting Framework
    manager.register_migration(
        1003,
        "Analytics & Reporting Framework",
        manager._build_migration_sql(
            """
        -- BI integration configs
        CREATE TABLE IF NOT EXISTS bi_integration_configs (
            id {SERIAL},
            integration_type VARCHAR(50) NOT NULL,
            enabled BOOLEAN DEFAULT {BOOLEAN_FALSE},
            api_key_encrypted TEXT,
            endpoint_url VARCHAR(255),
            sync_interval INTEGER DEFAULT 3600,
            last_sync TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Call tags and categories
        CREATE TABLE IF NOT EXISTS call_tags (
            id {SERIAL},
            tag_name VARCHAR(50) NOT NULL UNIQUE,
            category VARCHAR(50),
            color VARCHAR(20),
            auto_apply_rules TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS call_tag_assignments (
            id {SERIAL},
            call_id VARCHAR(50) NOT NULL,
            tag_id INTEGER REFERENCES call_tags(id),
            assigned_by VARCHAR(50),
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            auto_assigned BOOLEAN DEFAULT {BOOLEAN_FALSE}
        );
    """
        ),
    )

    # Migration 1004: Integration Framework
    manager.register_migration(
        1004,
        "Integration Framework",
        manager._build_migration_sql(
            """
        -- HubSpot integration
        CREATE TABLE IF NOT EXISTS hubspot_integration (
            id {SERIAL},
            enabled BOOLEAN DEFAULT {BOOLEAN_FALSE},
            api_key_encrypted TEXT,
            portal_id VARCHAR(50),
            sync_contacts BOOLEAN DEFAULT {BOOLEAN_TRUE},
            sync_deals BOOLEAN DEFAULT {BOOLEAN_TRUE},
            auto_create_contacts BOOLEAN DEFAULT {BOOLEAN_FALSE},
            last_sync TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Zendesk integration
        CREATE TABLE IF NOT EXISTS zendesk_integration (
            id {SERIAL},
            enabled BOOLEAN DEFAULT {BOOLEAN_FALSE},
            subdomain VARCHAR(100),
            api_token_encrypted TEXT,
            email VARCHAR(255),
            auto_create_tickets BOOLEAN DEFAULT {BOOLEAN_FALSE},
            default_priority VARCHAR(20) DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Integration activity log
        CREATE TABLE IF NOT EXISTS integration_activity_log (
            id {SERIAL},
            integration_type VARCHAR(50),
            action VARCHAR(100),
            status VARCHAR(20),
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
        ),
    )

    # Migration 1005: Mobile Framework
    manager.register_migration(
        1005,
        "Mobile Framework",
        manager._build_migration_sql(
            """
        -- Mobile app installations
        CREATE TABLE IF NOT EXISTS mobile_app_installations (
            id {SERIAL},
            extension VARCHAR(20) NOT NULL,
            platform VARCHAR(20) NOT NULL,
            app_version VARCHAR(20),
            device_token VARCHAR(255),
            device_model VARCHAR(100),
            os_version VARCHAR(50),
            install_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP,
            enabled BOOLEAN DEFAULT {BOOLEAN_TRUE}
        );

        -- Mobile number portability
        CREATE TABLE IF NOT EXISTS mobile_number_portability (
            id {SERIAL},
            extension VARCHAR(20) NOT NULL,
            mobile_number VARCHAR(20),
            carrier VARCHAR(100),
            port_status VARCHAR(20) DEFAULT 'pending',
            port_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
        ),
    )

    # Migration 1006: Advanced Call Features Framework
    manager.register_migration(
        1006,
        "Advanced Call Features Framework",
        manager._build_migration_sql(
            """
        -- Call blending configurations
        CREATE TABLE IF NOT EXISTS call_blending_configs (
            id {SERIAL},
            queue_name VARCHAR(100) NOT NULL,
            enabled BOOLEAN DEFAULT {BOOLEAN_FALSE},
            inbound_priority INTEGER DEFAULT 1,
            outbound_campaign_id INTEGER,
            blend_ratio FLOAT DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Predictive voicemail drop
        CREATE TABLE IF NOT EXISTS voicemail_drop_templates (
            id {SERIAL},
            template_name VARCHAR(100) NOT NULL,
            audio_file VARCHAR(255),
            duration_seconds INTEGER,
            enabled BOOLEAN DEFAULT {BOOLEAN_TRUE},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Call recording analytics
        CREATE TABLE IF NOT EXISTS call_recording_analytics (
            id {SERIAL},
            recording_id VARCHAR(100),
            sentiment_score FLOAT,
            keywords_detected TEXT,
            compliance_score FLOAT,
            quality_score FLOAT,
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
        ),
    )

    # Migration 1007: SIP Trunking Framework
    manager.register_migration(
        1007,
        "SIP Trunking Framework",
        manager._build_migration_sql(
            """
        -- Geographic redundancy
        CREATE TABLE IF NOT EXISTS trunk_geographic_regions (
            id {SERIAL},
            region_name VARCHAR(100) NOT NULL,
            trunk_ids TEXT,
            priority INTEGER DEFAULT 100,
            enabled BOOLEAN DEFAULT {BOOLEAN_TRUE},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- DNS SRV failover
        CREATE TABLE IF NOT EXISTS dns_srv_configs (
            id {SERIAL},
            trunk_id INTEGER,
            srv_record VARCHAR(255),
            priority INTEGER,
            weight INTEGER,
            port INTEGER,
            last_tested TIMESTAMP,
            status VARCHAR(20) DEFAULT 'active'
        );

        -- Session Border Controller configs
        CREATE TABLE IF NOT EXISTS sbc_configs (
            id {SERIAL},
            sbc_name VARCHAR(100) NOT NULL,
            sbc_address VARCHAR(255),
            sbc_port INTEGER DEFAULT 5060,
            topology_hiding BOOLEAN DEFAULT {BOOLEAN_TRUE},
            nat_traversal BOOLEAN DEFAULT {BOOLEAN_TRUE},
            security_profiles TEXT,
            enabled BOOLEAN DEFAULT {BOOLEAN_TRUE}
        );
    """
        ),
    )

    # Migration 1008: Collaboration Framework
    manager.register_migration(
        1008,
        "Collaboration Framework",
        manager._build_migration_sql(
            """
        -- Team messaging
        CREATE TABLE IF NOT EXISTS team_messaging_channels (
            id {SERIAL},
            channel_name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            is_private BOOLEAN DEFAULT {BOOLEAN_FALSE},
            created_by VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS team_messaging_members (
            id {SERIAL},
            channel_id INTEGER REFERENCES team_messaging_channels(id),
            extension VARCHAR(20),
            role VARCHAR(20) DEFAULT 'member',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS team_messages (
            id {SERIAL},
            channel_id INTEGER REFERENCES team_messaging_channels(id),
            sender_extension VARCHAR(20),
            message_text TEXT,
            message_type VARCHAR(20) DEFAULT 'text',
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- File sharing
        CREATE TABLE IF NOT EXISTS shared_files (
            id {SERIAL},
            file_name VARCHAR(255) NOT NULL,
            file_path VARCHAR(500),
            file_size BIGINT,
            mime_type VARCHAR(100),
            uploaded_by VARCHAR(20),
            shared_with TEXT,
            description TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        );
    """
        ),
    )

    # Migration 1009: Compliance Framework (SOC 2 Type 2 only)
    # Note: PCI DSS and GDPR tables commented out as not required
    manager.register_migration(
        1009,
        "Compliance Framework",
        manager._build_migration_sql(
            """
        -- SOC 2 Type 2 enhanced
        CREATE TABLE IF NOT EXISTS soc2_controls (
            id {SERIAL},
            control_id VARCHAR(50) NOT NULL,
            control_category VARCHAR(50),
            description TEXT,
            implementation_status VARCHAR(20),
            last_tested TIMESTAMP,
            test_results TEXT
        );

        -- Data residency (used by SOC 2)
        CREATE TABLE IF NOT EXISTS data_residency_configs (
            id {SERIAL},
            data_type VARCHAR(50),
            region VARCHAR(50),
            storage_location VARCHAR(255),
            encryption_required BOOLEAN DEFAULT {BOOLEAN_TRUE},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
        ),
    )

    # Migration 1010: Click-to-Dial Framework
    manager.register_migration(
        1010,
        "Click-to-Dial Framework",
        manager._build_migration_sql(
            """
        -- Click-to-dial configurations
        CREATE TABLE IF NOT EXISTS click_to_dial_configs (
            id {SERIAL},
            extension VARCHAR(20) NOT NULL,
            enabled BOOLEAN DEFAULT {BOOLEAN_TRUE},
            default_caller_id VARCHAR(20),
            auto_answer BOOLEAN DEFAULT {BOOLEAN_FALSE},
            browser_notification BOOLEAN DEFAULT {BOOLEAN_TRUE},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Click-to-dial history
        CREATE TABLE IF NOT EXISTS click_to_dial_history (
            id {SERIAL},
            extension VARCHAR(20),
            destination VARCHAR(20),
            call_id VARCHAR(50),
            source VARCHAR(50),
            initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            connected_at TIMESTAMP,
            status VARCHAR(20)
        );
    """
        ),
    )
