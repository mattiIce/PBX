"""
Database migration system for PBX features
Manages schema versioning and migrations
"""
from datetime import datetime
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

    def register_migration(self, version: int, name: str, sql: str):
        """
        Register a migration

        Args:
            version: Migration version number
            name: Migration name/description
            sql: SQL to execute
        """
        self.migrations.append({
            'version': version,
            'name': name,
            'sql': sql
        })

    def init_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        try:
            if self.db.db_type == 'postgresql':
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
            result = self.db.fetch_one(
                "SELECT MAX(version) as max_version FROM schema_migrations"
            )
            if result and result.get('max_version') is not None:
                return result['max_version']
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
            self.migrations.sort(key=lambda x: x['version'])

            # Filter migrations to apply
            pending = [
                m for m in self.migrations
                if m['version'] > current_version
            ]

            if target_version:
                pending = [m for m in pending if m['version'] <= target_version]

            if not pending:
                self.logger.info("No pending migrations")
                return True

            self.logger.info(f"Applying {len(pending)} migrations...")

            for migration in pending:
                self.logger.info(
                    f"Applying migration {migration['version']}: {migration['name']}"
                )

                # Execute migration SQL
                self.db.execute(migration['sql'])

                # Record migration
                self.db.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (?, ?)"
                    if self.db.db_type == 'sqlite'
                    else "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
                    (migration['version'], migration['name'])
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
            current_version = self.get_current_version()
            
            # Get applied migrations
            applied = self.db.execute(
                "SELECT version, name, applied_at FROM schema_migrations ORDER BY version"
            )
            applied_versions = {row[0]: row for row in (applied or [])}

            status = []
            for migration in sorted(self.migrations, key=lambda x: x['version']):
                version = migration['version']
                if version in applied_versions:
                    status.append({
                        'version': version,
                        'name': migration['name'],
                        'status': 'applied',
                        'applied_at': applied_versions[version][2]
                    })
                else:
                    status.append({
                        'version': version,
                        'name': migration['name'],
                        'status': 'pending',
                        'applied_at': None
                    })

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
    manager.register_migration(1000, "AI Features Framework", """
        -- Real-time speech analytics
        CREATE TABLE IF NOT EXISTS speech_analytics_configs (
            id SERIAL PRIMARY KEY,
            extension VARCHAR(20) NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            transcription_enabled BOOLEAN DEFAULT TRUE,
            sentiment_enabled BOOLEAN DEFAULT TRUE,
            summarization_enabled BOOLEAN DEFAULT TRUE,
            keywords TEXT,
            alert_threshold FLOAT DEFAULT 0.7,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Conversational AI assistant
        CREATE TABLE IF NOT EXISTS ai_assistant_configs (
            id SERIAL PRIMARY KEY,
            extension VARCHAR(20) NOT NULL,
            enabled BOOLEAN DEFAULT FALSE,
            auto_response_enabled BOOLEAN DEFAULT FALSE,
            greeting_template TEXT,
            response_language VARCHAR(10) DEFAULT 'en',
            confidence_threshold FLOAT DEFAULT 0.8,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Voice biometrics
        CREATE TABLE IF NOT EXISTS voice_biometrics (
            id SERIAL PRIMARY KEY,
            extension VARCHAR(20) NOT NULL,
            voiceprint_data BYTEA,
            enrollment_status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_verified TIMESTAMP
        );

        -- Call quality prediction
        CREATE TABLE IF NOT EXISTS call_quality_predictions (
            id SERIAL PRIMARY KEY,
            call_id VARCHAR(50),
            predicted_mos FLOAT,
            predicted_issues TEXT,
            actual_mos FLOAT,
            prediction_accuracy FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """ if manager.db.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS speech_analytics_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extension TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            transcription_enabled INTEGER DEFAULT 1,
            sentiment_enabled INTEGER DEFAULT 1,
            summarization_enabled INTEGER DEFAULT 1,
            keywords TEXT,
            alert_threshold REAL DEFAULT 0.7,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ai_assistant_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extension TEXT NOT NULL,
            enabled INTEGER DEFAULT 0,
            auto_response_enabled INTEGER DEFAULT 0,
            greeting_template TEXT,
            response_language TEXT DEFAULT 'en',
            confidence_threshold REAL DEFAULT 0.8,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS voice_biometrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extension TEXT NOT NULL,
            voiceprint_data BLOB,
            enrollment_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_verified TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS call_quality_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id TEXT,
            predicted_mos REAL,
            predicted_issues TEXT,
            actual_mos REAL,
            prediction_accuracy REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Migration 1001: Video Conferencing Framework
    manager.register_migration(1001, "Video Conferencing Framework", """
        -- Video conferencing rooms
        CREATE TABLE IF NOT EXISTS video_conference_rooms (
            id SERIAL PRIMARY KEY,
            room_name VARCHAR(100) NOT NULL UNIQUE,
            owner_extension VARCHAR(20),
            max_participants INTEGER DEFAULT 10,
            enable_4k BOOLEAN DEFAULT FALSE,
            enable_screen_share BOOLEAN DEFAULT TRUE,
            recording_enabled BOOLEAN DEFAULT FALSE,
            password_hash VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Video conference participants
        CREATE TABLE IF NOT EXISTS video_conference_participants (
            id SERIAL PRIMARY KEY,
            room_id INTEGER REFERENCES video_conference_rooms(id),
            extension VARCHAR(20),
            display_name VARCHAR(100),
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            left_at TIMESTAMP,
            video_enabled BOOLEAN DEFAULT TRUE,
            audio_enabled BOOLEAN DEFAULT TRUE,
            screen_sharing BOOLEAN DEFAULT FALSE
        );

        -- Video codec configurations
        CREATE TABLE IF NOT EXISTS video_codec_configs (
            id SERIAL PRIMARY KEY,
            codec_name VARCHAR(50) NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            priority INTEGER DEFAULT 100,
            max_resolution VARCHAR(20) DEFAULT '1920x1080',
            max_bitrate INTEGER DEFAULT 2000,
            min_bitrate INTEGER DEFAULT 500
        );
    """ if manager.db.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS video_conference_rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_name TEXT NOT NULL UNIQUE,
            owner_extension TEXT,
            max_participants INTEGER DEFAULT 10,
            enable_4k INTEGER DEFAULT 0,
            enable_screen_share INTEGER DEFAULT 1,
            recording_enabled INTEGER DEFAULT 0,
            password_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS video_conference_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER REFERENCES video_conference_rooms(id),
            extension TEXT,
            display_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            left_at TIMESTAMP,
            video_enabled INTEGER DEFAULT 1,
            audio_enabled INTEGER DEFAULT 1,
            screen_sharing INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS video_codec_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codec_name TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 100,
            max_resolution TEXT DEFAULT '1920x1080',
            max_bitrate INTEGER DEFAULT 2000,
            min_bitrate INTEGER DEFAULT 500
        );
    """)

    # Migration 1002: Emergency Services Framework
    manager.register_migration(1002, "Emergency Services Framework", """
        -- Nomadic E911 locations
        CREATE TABLE IF NOT EXISTS nomadic_e911_locations (
            id SERIAL PRIMARY KEY,
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
            auto_detected BOOLEAN DEFAULT FALSE
        );

        -- E911 location updates log
        CREATE TABLE IF NOT EXISTS e911_location_updates (
            id SERIAL PRIMARY KEY,
            extension VARCHAR(20),
            old_location TEXT,
            new_location TEXT,
            update_source VARCHAR(50),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Multi-site E911 configurations
        CREATE TABLE IF NOT EXISTS multi_site_e911_configs (
            id SERIAL PRIMARY KEY,
            site_name VARCHAR(100) NOT NULL,
            ip_range_start VARCHAR(45),
            ip_range_end VARCHAR(45),
            emergency_trunk VARCHAR(50),
            psap_number VARCHAR(20),
            elin VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """ if manager.db.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS nomadic_e911_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extension TEXT NOT NULL,
            ip_address TEXT,
            location_name TEXT,
            street_address TEXT,
            city TEXT,
            state TEXT,
            postal_code TEXT,
            country TEXT DEFAULT 'USA',
            building TEXT,
            floor TEXT,
            room TEXT,
            latitude REAL,
            longitude REAL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            auto_detected INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS e911_location_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extension TEXT,
            old_location TEXT,
            new_location TEXT,
            update_source TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS multi_site_e911_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_name TEXT NOT NULL,
            ip_range_start TEXT,
            ip_range_end TEXT,
            emergency_trunk TEXT,
            psap_number TEXT,
            elin TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Migration 1003: Analytics & Reporting Framework
    manager.register_migration(1003, "Analytics & Reporting Framework", """
        -- BI integration configs
        CREATE TABLE IF NOT EXISTS bi_integration_configs (
            id SERIAL PRIMARY KEY,
            integration_type VARCHAR(50) NOT NULL,
            enabled BOOLEAN DEFAULT FALSE,
            api_key_encrypted TEXT,
            endpoint_url VARCHAR(255),
            sync_interval INTEGER DEFAULT 3600,
            last_sync TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Call tags and categories
        CREATE TABLE IF NOT EXISTS call_tags (
            id SERIAL PRIMARY KEY,
            tag_name VARCHAR(50) NOT NULL UNIQUE,
            category VARCHAR(50),
            color VARCHAR(20),
            auto_apply_rules TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS call_tag_assignments (
            id SERIAL PRIMARY KEY,
            call_id VARCHAR(50) NOT NULL,
            tag_id INTEGER REFERENCES call_tags(id),
            assigned_by VARCHAR(50),
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            auto_assigned BOOLEAN DEFAULT FALSE
        );
    """ if manager.db.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS bi_integration_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            integration_type TEXT NOT NULL,
            enabled INTEGER DEFAULT 0,
            api_key_encrypted TEXT,
            endpoint_url TEXT,
            sync_interval INTEGER DEFAULT 3600,
            last_sync TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS call_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_name TEXT NOT NULL UNIQUE,
            category TEXT,
            color TEXT,
            auto_apply_rules TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS call_tag_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id TEXT NOT NULL,
            tag_id INTEGER REFERENCES call_tags(id),
            assigned_by TEXT,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            auto_assigned INTEGER DEFAULT 0
        );
    """)

    # Migration 1004: Integration Framework
    manager.register_migration(1004, "Integration Framework", """
        -- HubSpot integration
        CREATE TABLE IF NOT EXISTS hubspot_integration (
            id SERIAL PRIMARY KEY,
            enabled BOOLEAN DEFAULT FALSE,
            api_key_encrypted TEXT,
            portal_id VARCHAR(50),
            sync_contacts BOOLEAN DEFAULT TRUE,
            sync_deals BOOLEAN DEFAULT TRUE,
            auto_create_contacts BOOLEAN DEFAULT FALSE,
            last_sync TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Zendesk integration
        CREATE TABLE IF NOT EXISTS zendesk_integration (
            id SERIAL PRIMARY KEY,
            enabled BOOLEAN DEFAULT FALSE,
            subdomain VARCHAR(100),
            api_token_encrypted TEXT,
            email VARCHAR(255),
            auto_create_tickets BOOLEAN DEFAULT FALSE,
            default_priority VARCHAR(20) DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Integration activity log
        CREATE TABLE IF NOT EXISTS integration_activity_log (
            id SERIAL PRIMARY KEY,
            integration_type VARCHAR(50),
            action VARCHAR(100),
            status VARCHAR(20),
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """ if manager.db.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS hubspot_integration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enabled INTEGER DEFAULT 0,
            api_key_encrypted TEXT,
            portal_id TEXT,
            sync_contacts INTEGER DEFAULT 1,
            sync_deals INTEGER DEFAULT 1,
            auto_create_contacts INTEGER DEFAULT 0,
            last_sync TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS zendesk_integration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enabled INTEGER DEFAULT 0,
            subdomain TEXT,
            api_token_encrypted TEXT,
            email TEXT,
            auto_create_tickets INTEGER DEFAULT 0,
            default_priority TEXT DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS integration_activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            integration_type TEXT,
            action TEXT,
            status TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Migration 1005: Mobile Framework
    manager.register_migration(1005, "Mobile Framework", """
        -- Mobile app installations
        CREATE TABLE IF NOT EXISTS mobile_app_installations (
            id SERIAL PRIMARY KEY,
            extension VARCHAR(20) NOT NULL,
            platform VARCHAR(20) NOT NULL,
            app_version VARCHAR(20),
            device_token VARCHAR(255),
            device_model VARCHAR(100),
            os_version VARCHAR(50),
            install_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP,
            enabled BOOLEAN DEFAULT TRUE
        );

        -- Mobile number portability
        CREATE TABLE IF NOT EXISTS mobile_number_portability (
            id SERIAL PRIMARY KEY,
            extension VARCHAR(20) NOT NULL,
            mobile_number VARCHAR(20),
            carrier VARCHAR(100),
            port_status VARCHAR(20) DEFAULT 'pending',
            port_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """ if manager.db.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS mobile_app_installations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extension TEXT NOT NULL,
            platform TEXT NOT NULL,
            app_version TEXT,
            device_token TEXT,
            device_model TEXT,
            os_version TEXT,
            install_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP,
            enabled INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS mobile_number_portability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extension TEXT NOT NULL,
            mobile_number TEXT,
            carrier TEXT,
            port_status TEXT DEFAULT 'pending',
            port_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Migration 1006: Advanced Call Features Framework
    manager.register_migration(1006, "Advanced Call Features Framework", """
        -- Call blending configurations
        CREATE TABLE IF NOT EXISTS call_blending_configs (
            id SERIAL PRIMARY KEY,
            queue_name VARCHAR(100) NOT NULL,
            enabled BOOLEAN DEFAULT FALSE,
            inbound_priority INTEGER DEFAULT 1,
            outbound_campaign_id INTEGER,
            blend_ratio FLOAT DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Predictive voicemail drop
        CREATE TABLE IF NOT EXISTS voicemail_drop_templates (
            id SERIAL PRIMARY KEY,
            template_name VARCHAR(100) NOT NULL,
            audio_file VARCHAR(255),
            duration_seconds INTEGER,
            enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Call recording analytics
        CREATE TABLE IF NOT EXISTS call_recording_analytics (
            id SERIAL PRIMARY KEY,
            recording_id VARCHAR(100),
            sentiment_score FLOAT,
            keywords_detected TEXT,
            compliance_score FLOAT,
            quality_score FLOAT,
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """ if manager.db.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS call_blending_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_name TEXT NOT NULL,
            enabled INTEGER DEFAULT 0,
            inbound_priority INTEGER DEFAULT 1,
            outbound_campaign_id INTEGER,
            blend_ratio REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS voicemail_drop_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_name TEXT NOT NULL,
            audio_file TEXT,
            duration_seconds INTEGER,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS call_recording_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recording_id TEXT,
            sentiment_score REAL,
            keywords_detected TEXT,
            compliance_score REAL,
            quality_score REAL,
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Migration 1007: SIP Trunking Framework
    manager.register_migration(1007, "SIP Trunking Framework", """
        -- Geographic redundancy
        CREATE TABLE IF NOT EXISTS trunk_geographic_regions (
            id SERIAL PRIMARY KEY,
            region_name VARCHAR(100) NOT NULL,
            trunk_ids TEXT,
            priority INTEGER DEFAULT 100,
            enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- DNS SRV failover
        CREATE TABLE IF NOT EXISTS dns_srv_configs (
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
            sbc_name VARCHAR(100) NOT NULL,
            sbc_address VARCHAR(255),
            sbc_port INTEGER DEFAULT 5060,
            topology_hiding BOOLEAN DEFAULT TRUE,
            nat_traversal BOOLEAN DEFAULT TRUE,
            security_profiles TEXT,
            enabled BOOLEAN DEFAULT TRUE
        );
    """ if manager.db.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS trunk_geographic_regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region_name TEXT NOT NULL,
            trunk_ids TEXT,
            priority INTEGER DEFAULT 100,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS dns_srv_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trunk_id INTEGER,
            srv_record TEXT,
            priority INTEGER,
            weight INTEGER,
            port INTEGER,
            last_tested TIMESTAMP,
            status TEXT DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS sbc_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sbc_name TEXT NOT NULL,
            sbc_address TEXT,
            sbc_port INTEGER DEFAULT 5060,
            topology_hiding INTEGER DEFAULT 1,
            nat_traversal INTEGER DEFAULT 1,
            security_profiles TEXT,
            enabled INTEGER DEFAULT 1
        );
    """)

    # Migration 1008: Collaboration Framework
    manager.register_migration(1008, "Collaboration Framework", """
        -- Team messaging
        CREATE TABLE IF NOT EXISTS team_messaging_channels (
            id SERIAL PRIMARY KEY,
            channel_name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            is_private BOOLEAN DEFAULT FALSE,
            created_by VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS team_messaging_members (
            id SERIAL PRIMARY KEY,
            channel_id INTEGER REFERENCES team_messaging_channels(id),
            extension VARCHAR(20),
            role VARCHAR(20) DEFAULT 'member',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS team_messages (
            id SERIAL PRIMARY KEY,
            channel_id INTEGER REFERENCES team_messaging_channels(id),
            sender_extension VARCHAR(20),
            message_text TEXT,
            message_type VARCHAR(20) DEFAULT 'text',
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- File sharing
        CREATE TABLE IF NOT EXISTS shared_files (
            id SERIAL PRIMARY KEY,
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
    """ if manager.db.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS team_messaging_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_private INTEGER DEFAULT 0,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS team_messaging_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER REFERENCES team_messaging_channels(id),
            extension TEXT,
            role TEXT DEFAULT 'member',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS team_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER REFERENCES team_messaging_channels(id),
            sender_extension TEXT,
            message_text TEXT,
            message_type TEXT DEFAULT 'text',
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS shared_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_path TEXT,
            file_size INTEGER,
            mime_type TEXT,
            uploaded_by TEXT,
            shared_with TEXT,
            description TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        );
    """)

    # Migration 1009: Compliance Framework (SOC 2 Type 2 only)
    # Note: PCI DSS and GDPR tables commented out as not required
    manager.register_migration(1009, "Compliance Framework", """
        -- SOC 2 Type 2 enhanced
        CREATE TABLE IF NOT EXISTS soc2_controls (
            id SERIAL PRIMARY KEY,
            control_id VARCHAR(50) NOT NULL,
            control_category VARCHAR(50),
            description TEXT,
            implementation_status VARCHAR(20),
            last_tested TIMESTAMP,
            test_results TEXT
        );

        -- Data residency (used by SOC 2)
        CREATE TABLE IF NOT EXISTS data_residency_configs (
            id SERIAL PRIMARY KEY,
            data_type VARCHAR(50),
            region VARCHAR(50),
            storage_location VARCHAR(255),
            encryption_required BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """ if manager.db.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS soc2_controls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            control_id TEXT NOT NULL,
            control_category TEXT,
            description TEXT,
            implementation_status TEXT,
            last_tested TIMESTAMP,
            test_results TEXT
        );

        CREATE TABLE IF NOT EXISTS data_residency_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_type TEXT,
            region TEXT,
            storage_location TEXT,
            encryption_required INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Migration 1010: Click-to-Dial Framework
    manager.register_migration(1010, "Click-to-Dial Framework", """
        -- Click-to-dial configurations
        CREATE TABLE IF NOT EXISTS click_to_dial_configs (
            id SERIAL PRIMARY KEY,
            extension VARCHAR(20) NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            default_caller_id VARCHAR(20),
            auto_answer BOOLEAN DEFAULT FALSE,
            browser_notification BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Click-to-dial history
        CREATE TABLE IF NOT EXISTS click_to_dial_history (
            id SERIAL PRIMARY KEY,
            extension VARCHAR(20),
            destination VARCHAR(20),
            call_id VARCHAR(50),
            source VARCHAR(50),
            initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            connected_at TIMESTAMP,
            status VARCHAR(20)
        );
    """ if manager.db.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS click_to_dial_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extension TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            default_caller_id TEXT,
            auto_answer INTEGER DEFAULT 0,
            browser_notification INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS click_to_dial_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extension TEXT,
            destination TEXT,
            call_id TEXT,
            source TEXT,
            initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            connected_at TIMESTAMP,
            status TEXT
        );
    """)
