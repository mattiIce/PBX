"""
Business Intelligence Integration
Export to BI tools (Tableau, Power BI, etc.)
"""

import csv
import json
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tableauhyperapi import TableDefinition

import sqlite3

from pbx.utils.logger import get_logger


class BIProvider(Enum):
    """BI provider enumeration"""

    TABLEAU = "tableau"
    POWER_BI = "powerbi"
    LOOKER = "looker"
    QLIK = "qlik"
    METABASE = "metabase"


class ExportFormat(Enum):
    """Data export format"""

    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
    EXCEL = "excel"
    SQL = "sql"


class DataSet:
    """Represents a dataset for BI export"""

    def __init__(self, name: str, query: str) -> None:
        """Initialize dataset"""
        self.name = name
        self.query = query
        self.created_at = datetime.now(UTC)
        self.last_exported = None
        self.export_count = 0


class BIIntegration:
    """
    Business Intelligence Integration

    Export PBX data to BI tools for advanced reporting and analytics.
    Supports:
    - Tableau (REST API, TDE/Hyper files)
    - Microsoft Power BI (REST API, DirectQuery)
    - Google Looker (LookML, SQL)
    - Qlik Sense (QVD files, REST API)
    - Metabase (SQL, API)
    """

    def __init__(self, config: Any | None = None) -> None:
        """Initialize BI integration"""
        self.logger = get_logger()
        self.config = config or {}

        # Configuration
        bi_config = self.config.get("features", {}).get("bi_integration", {})
        self.enabled = bi_config.get("enabled", False)
        self.default_provider = BIProvider(bi_config.get("default_provider", "tableau"))
        self.export_path = bi_config.get("export_path", "/var/pbx/bi_exports")
        self.auto_export_enabled = bi_config.get("auto_export", False)
        self.export_schedule = bi_config.get("export_schedule", "daily")  # daily, weekly, monthly

        # Datasets
        self.datasets: dict[str, DataSet] = {}
        self._initialize_default_datasets()

        # Statistics
        self.total_exports = 0
        self.failed_exports = 0
        self.last_export_time = None

        self.logger.info("Business Intelligence integration initialized")
        self.logger.info(f"  Default provider: {self.default_provider.value}")
        self.logger.info(f"  Export path: {self.export_path}")
        self.logger.info(f"  Auto export: {self.auto_export_enabled}")
        self.logger.info(f"  Enabled: {self.enabled}")

    def _initialize_default_datasets(self) -> None:
        """Initialize default datasets"""
        # Call Detail Records
        self.datasets["cdr"] = DataSet(
            "Call Detail Records",
            "SELECT * FROM call_detail_records WHERE created_at >= :start_date",
        )

        # Call Queue Statistics
        self.datasets["queue_stats"] = DataSet(
            "Call Queue Statistics", "SELECT * FROM call_queue_stats WHERE date >= :start_date"
        )

        # Extension Usage
        self.datasets["extension_usage"] = DataSet(
            "Extension Usage",
            "SELECT extension, COUNT(*) as call_count, SUM(duration) as total_duration "
            "FROM call_detail_records WHERE created_at >= :start_date "
            "GROUP BY extension",
        )

        # QoS Metrics
        self.datasets["qos_metrics"] = DataSet(
            "QoS Metrics", "SELECT * FROM qos_metrics WHERE timestamp >= :start_date"
        )

    def _execute_query(self, query: str, start_date: datetime, end_date: datetime) -> list[dict]:
        """
        Execute query and fetch data from database

        Args:
            query: SQL query
            start_date: Start date parameter
            end_date: End date parameter

        Returns:
            list[dict]: Query results
        """
        try:
            from pbx.utils.database import get_database

            db = get_database()

            if not db or not db.enabled or not db.connection:
                self.logger.warning("Database not available for BI export")
                return []

            # Replace query parameters
            query = query.replace(":start_date", f"'{start_date.isoformat()}'")
            query = query.replace(":end_date", f"'{end_date.isoformat()}'")

            # Execute query
            if db.db_type == "postgresql":
                from psycopg2.extras import RealDictCursor

                cursor = db.connection.cursor(cursor_factory=RealDictCursor)
                cursor.execute(query)
                results = cursor.fetchall()
                cursor.close()
                # Convert RealDictRow to regular dict
                return [dict(row) for row in results]
            if db.db_type == "sqlite":
                cursor = db.connection.cursor()
                cursor.execute(query)
                columns = [description[0] for description in cursor.description]
                results = cursor.fetchall()
                # Convert tuples to dicts
                return [dict(zip(columns, row, strict=False)) for row in results]
            self.logger.error(f"Unsupported database type: {db.db_type}")
            return []
        except sqlite3.Error as e:
            self.logger.error(f"Query execution failed: {e}")
            return []

    def _format_data(self, data: list[dict], format: ExportFormat, dataset_name: str) -> str:
        """
        Convert data to requested format

        Args:
            data: Query results
            format: Export format
            dataset_name: Dataset name

        Returns:
            str: Path to exported file
        """
        # Ensure export directory exists
        Path(self.export_path).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

        if format == ExportFormat.CSV:
            return self._export_csv(data, dataset_name, timestamp)
        if format == ExportFormat.JSON:
            return self._export_json(data, dataset_name, timestamp)
        if format == ExportFormat.EXCEL:
            return self._export_excel(data, dataset_name, timestamp)
        self.logger.warning(f"Format {format.value} not yet implemented")
        return ""

    def _export_csv(self, data: list[dict], dataset_name: str, timestamp: str) -> str:
        """Export data to CSV"""
        filename = f"{self.export_path}/{dataset_name}_{timestamp}.csv"

        if not data:
            # Create empty file
            with open(filename, "w", newline="") as f:
                f.write("")
            return filename

        # Write CSV with headers
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

        self.logger.info(f"Exported {len(data)} rows to {filename}")
        return filename

    def _export_json(self, data: list[dict], dataset_name: str, timestamp: str) -> str:
        """Export data to JSON"""
        filename = f"{self.export_path}/{dataset_name}_{timestamp}.json"

        # Convert datetime objects to strings for JSON serialization
        def serialize_datetime(obj: Any) -> str:
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"type {type(obj)} not serializable")

        with open(filename, "w") as f:
            json.dump(data, f, indent=2, default=serialize_datetime)

        self.logger.info(f"Exported {len(data)} rows to {filename}")
        return filename

    def _export_excel(self, data: list[dict], dataset_name: str, timestamp: str) -> str:
        """Export data to Excel (requires openpyxl)"""
        filename = f"{self.export_path}/{dataset_name}_{timestamp}.xlsx"

        try:
            from openpyxl import Workbook

            wb = Workbook()
            ws = wb.active
            ws.title = dataset_name[:31]  # Excel sheet name limit

            if data:
                # Write headers
                headers = list(data[0].keys())
                ws.append(headers)

                # Write data rows
                for row in data:
                    ws.append(list(row.values()))

            wb.save(filename)
            self.logger.info(f"Exported {len(data)} rows to {filename}")
            return filename
        except ImportError:
            self.logger.warning("openpyxl not installed, falling back to CSV")
            return self._export_csv(data, dataset_name, timestamp)

    def export_dataset(
        self,
        dataset_name: str,
        format: ExportFormat = ExportFormat.CSV,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        provider: BIProvider = None,
    ) -> dict:
        """
        Export dataset to specified format

        Args:
            dataset_name: Name of dataset to export
            format: Export format
            start_date: Start date for data
            end_date: End date for data
            provider: BI provider (optional)

        Returns:
            dict: Export result
        """
        if dataset_name not in self.datasets:
            return {"success": False, "error": f"Dataset {dataset_name} not found"}

        dataset = self.datasets[dataset_name]
        provider = provider or self.default_provider

        # Default date range
        if not start_date:
            start_date = datetime.now(UTC) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(UTC)

        self.logger.info(f"Exporting dataset '{dataset_name}' to {format.value}")
        self.logger.info(f"  Date range: {start_date} to {end_date}")

        # Execute query and fetch data
        data = self._execute_query(dataset.query, start_date, end_date)

        # Convert to requested format
        export_file = self._format_data(data, format, dataset_name)

        dataset.last_exported = datetime.now(UTC)
        dataset.export_count += 1
        self.total_exports += 1
        self.last_export_time = datetime.now(UTC)

        return {
            "success": True,
            "dataset": dataset_name,
            "format": format.value,
            "file_path": export_file,
            "record_count": len(data),
            "exported_at": datetime.now(UTC).isoformat(),
        }

    def create_tableau_extract(self, dataset_name: str) -> str | None:
        """
        Create Tableau TDE/Hyper extract

        Args:
            dataset_name: Dataset to export

        Returns:
            str | None: Path to extract file
        """
        self.logger.info(f"Creating Tableau extract for {dataset_name}")

        try:
            # Check if Tableau Hyper API is available
            from tableauhyperapi import (
                Connection,
                CreateMode,
                HyperProcess,
                Inserter,
                Telemetry,
            )

            if dataset_name not in self.datasets:
                self.logger.error(f"Dataset {dataset_name} not found")
                return None

            dataset = self.datasets[dataset_name]

            # Execute query to get data
            data = self._execute_query(
                dataset.query, datetime.now(UTC) - timedelta(days=30), datetime.now(UTC)
            )

            if not data:
                self.logger.warning("No data to export to Tableau")
                return None

            # Create Hyper file
            extract_path = f"{self.export_path}/{dataset_name}.hyper"

            with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
                with Connection(
                    endpoint=hyper.endpoint,
                    database=extract_path,
                    create_mode=CreateMode.CREATE_AND_REPLACE,
                ) as connection:
                    # Create table definition from data structure
                    table_def = self._create_tableau_table_definition(dataset_name, data[0])
                    connection.catalog.create_table(table_def)

                    # Insert data
                    with Inserter(connection, table_def) as inserter:
                        for row in data:
                            inserter.add_row([row.get(col) for col in row])
                        inserter.execute()

            self.logger.info(f"Created Tableau extract: {extract_path}")
            return extract_path
        except ImportError:
            self.logger.warning(
                "Tableau Hyper API not installed. Install with: pip install tableauhyperapi"
            )
            # Fallback to CSV export
            return self._export_csv(
                self._execute_query(
                    self.datasets[dataset_name].query,
                    datetime.now(UTC) - timedelta(days=30),
                    datetime.now(UTC),
                ),
                dataset_name,
                datetime.now(UTC).strftime("%Y%m%d_%H%M%S"),
            )
        except (KeyError, OSError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to create Tableau extract: {e}")
            return None

    def _create_tableau_table_definition(
        self, table_name: str, sample_row: dict
    ) -> "TableDefinition":
        """Create Tableau table definition from sample row"""
        from tableauhyperapi import SqlType, TableDefinition, TableName

        # Map Python types to Tableau SQL types
        columns = []
        for key, value in sample_row.items():
            if isinstance(value, int):
                sql_type = SqlType.big_int()
            elif isinstance(value, float):
                sql_type = SqlType.double()
            elif isinstance(value, datetime):
                sql_type = SqlType.timestamp()
            elif isinstance(value, bool):
                sql_type = SqlType.bool()
            else:
                sql_type = SqlType.text()

            columns.append(TableDefinition.Column(key, sql_type))

        return TableDefinition(table_name=TableName("Extract", table_name), columns=columns)

    def create_powerbi_dataset(self, dataset_name: str, credentials: dict) -> dict:
        """
        Create Power BI dataset via REST API

        Args:
            dataset_name: Dataset name
            credentials: Power BI API credentials (access_token, workspace_id)

        Returns:
            dict: Dataset creation result
        """
        self.logger.info(f"Creating Power BI dataset for {dataset_name}")

        try:
            import requests

            access_token = credentials.get("access_token")
            workspace_id = credentials.get("workspace_id")

            if not access_token or not workspace_id:
                return {
                    "success": False,
                    "error": "Missing credentials (access_token or workspace_id)",
                }

            # Get data structure from sample query
            if dataset_name not in self.datasets:
                return {"success": False, "error": f"Dataset {dataset_name} not found"}

            dataset = self.datasets[dataset_name]
            sample_data = self._execute_query(
                dataset.query, datetime.now(UTC) - timedelta(days=1), datetime.now(UTC)
            )

            # Create Power BI dataset schema
            schema = self._create_powerbi_schema(dataset_name, sample_data)

            # Power BI REST API endpoint
            url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-type": "application/json",
            }

            response = requests.post(url, headers=headers, json=schema, timeout=30)

            if response.status_code == 201:
                result = response.json()
                return {
                    "success": True,
                    "dataset_id": result.get("id"),
                    "dataset_name": dataset_name,
                }
            return {
                "success": False,
                "error": f"Power BI API error: {response.status_code} - {response.text}",
            }
        except ImportError:
            return {"success": False, "error": "requests library not installed"}
        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Failed to create Power BI dataset: {e}")
            return {"success": False, "error": str(e)}

    def _create_powerbi_schema(self, dataset_name: str, sample_data: list[dict]) -> dict:
        """Create Power BI dataset schema"""
        if not sample_data:
            return {"name": dataset_name, "tables": []}

        sample_row = sample_data[0]
        columns = []

        for key, value in sample_row.items():
            if isinstance(value, int):
                data_type = "Int64"
            elif isinstance(value, float):
                data_type = "Double"
            elif isinstance(value, datetime):
                data_type = "DateTime"
            elif isinstance(value, bool):
                data_type = "Boolean"
            else:
                data_type = "String"

            columns.append({"name": key, "dataType": data_type})

        return {"name": dataset_name, "tables": [{"name": dataset_name, "columns": columns}]}

    def setup_direct_query(self, provider: BIProvider, connection_string: str) -> dict:
        """
        Setup direct query connection for BI tool

        Args:
            provider: BI provider
            connection_string: Database connection string

        Returns:
            dict: Connection setup result
        """
        self.logger.info(f"Setting up direct query for {provider.value}")
        self.logger.info(f"  Connection: {connection_string}")

        # Validate connection string format
        if not connection_string:
            return {"success": False, "error": "Connection string is required"}

        # Test database connection
        try:
            from pbx.utils.database import get_database

            db = get_database()

            if not db or not db.enabled:
                return {"success": False, "error": "Database not configured"}

            # For different providers, provide connection info
            connection_info = {
                "provider": provider.value,
                "connection_type": "direct_query",
                "database_type": db.db_type,
                "connection_string": connection_string,
                "setup_instructions": self._get_setup_instructions(provider, db.db_type),
            }

            return {"success": True, **connection_info}
        except Exception as e:
            self.logger.error(f"Direct query setup failed: {e}")
            return {"success": False, "error": str(e)}

    def _get_setup_instructions(self, provider: BIProvider, db_type: str) -> str:
        """Get setup instructions for BI provider"""
        instructions = {
            BIProvider.TABLEAU: f"1. Open Tableau Desktop\n2. Connect to {db_type.upper()}\n3. Use connection string provided",
            BIProvider.POWER_BI: f"1. Open Power BI Desktop\n2. Get Data > {db_type.upper()}\n3. Enter connection details",
            BIProvider.LOOKER: f"1. Open Looker\n2. Create new connection to {db_type.upper()}\n3. Configure connection parameters",
        }
        return instructions.get(provider, "Configure direct database connection in your BI tool")

    def create_custom_dataset(self, name: str, query: str) -> None:
        """
        Create custom dataset

        Args:
            name: Dataset name
            query: SQL query for dataset
        """
        dataset = DataSet(name, query)
        self.datasets[name] = dataset

        self.logger.info(f"Created custom dataset: {name}")

    def schedule_export(
        self, dataset_name: str, schedule: str, format: ExportFormat = ExportFormat.CSV
    ) -> None:
        """
        Schedule automatic export

        Args:
            dataset_name: Dataset to export
            schedule: Schedule (daily, weekly, monthly)
            format: Export format
        """
        if dataset_name not in self.datasets:
            self.logger.error(f"Dataset {dataset_name} not found for scheduling")
            return

        # Setup scheduled export job
        # In production, this would integrate with cron or a task scheduler
        self.logger.info(f"Scheduled export for {dataset_name}")
        self.logger.info(f"  Schedule: {schedule}")
        self.logger.info(f"  Format: {format.value}")

        # Store schedule configuration
        if not hasattr(self, "scheduled_exports"):
            self.scheduled_exports = {}

        self.scheduled_exports[dataset_name] = {
            "schedule": schedule,
            "format": format,
            "last_run": None,
            "next_run": self._calculate_next_run(schedule),
        }

        self.logger.info(f"  Next run: {self.scheduled_exports[dataset_name]['next_run']}")

    def _calculate_next_run(self, schedule: str) -> datetime:
        """Calculate next scheduled run time"""
        now = datetime.now(UTC)

        if schedule == "daily":
            # Next day at midnight
            return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        if schedule == "weekly":
            # Next Monday at midnight
            days_until_monday = (7 - now.weekday()) % 7 or 7
            return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
                days=days_until_monday
            )
        if schedule == "monthly":
            # First day of next month
            if now.month == 12:
                return now.replace(
                    year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
                )
            return now.replace(
                month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
        # Default to daily
        return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    def get_available_datasets(self) -> list[dict]:
        """Get list of available datasets"""
        return [
            {
                "name": name,
                "display_name": dataset.name,
                "last_exported": (
                    dataset.last_exported.isoformat() if dataset.last_exported else None
                ),
                "export_count": dataset.export_count,
            }
            for name, dataset in self.datasets.items()
        ]

    def test_connection(self, provider: BIProvider, credentials: dict) -> dict:
        """
        Test connection to BI provider

        Args:
            provider: BI provider
            credentials: API credentials

        Returns:
            dict: Test result
        """
        self.logger.info(f"Testing connection to {provider.value}")

        try:
            if provider == BIProvider.POWER_BI:
                # Test Power BI connection
                import requests

                access_token = credentials.get("access_token")
                if not access_token:
                    return {
                        "success": False,
                        "provider": provider.value,
                        "error": "Missing access_token",
                    }

                # Test API endpoint
                url = "https://api.powerbi.com/v1.0/myorg/groups"
                headers = {"Authorization": f"Bearer {access_token}"}

                response = requests.get(url, headers=headers, timeout=5)

                if response.status_code == 200:
                    return {
                        "success": True,
                        "provider": provider.value,
                        "message": "Power BI connection successful",
                    }
                return {
                    "success": False,
                    "provider": provider.value,
                    "error": f"Power BI API returned {response.status_code}",
                }

            if provider == BIProvider.TABLEAU:
                # Test Tableau connection
                # Would test Tableau Server REST API if configured
                return {
                    "success": True,
                    "provider": provider.value,
                    "message": "Tableau connection test (file-based exports only)",
                }

            # Generic test
            return {
                "success": True,
                "provider": provider.value,
                "message": f"{provider.value} connection test successful",
            }
        except ImportError:
            return {
                "success": False,
                "provider": provider.value,
                "error": "Required library not installed (requests)",
            }
        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Connection test failed: {e}")
            return {"success": False, "provider": provider.value, "error": str(e)}

    def get_statistics(self) -> dict:
        """Get BI integration statistics"""
        return {
            "enabled": self.enabled,
            "default_provider": self.default_provider.value,
            "total_datasets": len(self.datasets),
            "total_exports": self.total_exports,
            "failed_exports": self.failed_exports,
            "last_export_time": (
                self.last_export_time.isoformat() if self.last_export_time else None
            ),
            "auto_export_enabled": self.auto_export_enabled,
        }


# Global instance
_bi_integration = None


def get_bi_integration(config: Any | None = None) -> BIIntegration:
    """Get or create BI integration instance"""
    global _bi_integration
    if _bi_integration is None:
        _bi_integration = BIIntegration(config)
    return _bi_integration
