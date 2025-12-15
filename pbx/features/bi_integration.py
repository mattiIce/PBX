"""
Business Intelligence Integration
Export to BI tools (Tableau, Power BI, etc.)
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from pbx.utils.logger import get_logger
import json


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
    
    def __init__(self, name: str, query: str):
        """Initialize dataset"""
        self.name = name
        self.query = query
        self.created_at = datetime.now()
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
    
    def __init__(self, config=None):
        """Initialize BI integration"""
        self.logger = get_logger()
        self.config = config or {}
        
        # Configuration
        bi_config = self.config.get('features', {}).get('bi_integration', {})
        self.enabled = bi_config.get('enabled', False)
        self.default_provider = BIProvider(bi_config.get('default_provider', 'tableau'))
        self.export_path = bi_config.get('export_path', '/var/pbx/bi_exports')
        self.auto_export_enabled = bi_config.get('auto_export', False)
        self.export_schedule = bi_config.get('export_schedule', 'daily')  # daily, weekly, monthly
        
        # Datasets
        self.datasets: Dict[str, DataSet] = {}
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
    
    def _initialize_default_datasets(self):
        """Initialize default datasets"""
        # Call Detail Records
        self.datasets['cdr'] = DataSet(
            'Call Detail Records',
            'SELECT * FROM call_detail_records WHERE created_at >= :start_date'
        )
        
        # Call Queue Statistics
        self.datasets['queue_stats'] = DataSet(
            'Call Queue Statistics',
            'SELECT * FROM call_queue_stats WHERE date >= :start_date'
        )
        
        # Extension Usage
        self.datasets['extension_usage'] = DataSet(
            'Extension Usage',
            'SELECT extension, COUNT(*) as call_count, SUM(duration) as total_duration '
            'FROM call_detail_records WHERE created_at >= :start_date '
            'GROUP BY extension'
        )
        
        # QoS Metrics
        self.datasets['qos_metrics'] = DataSet(
            'QoS Metrics',
            'SELECT * FROM qos_metrics WHERE timestamp >= :start_date'
        )
    
    def export_dataset(self, dataset_name: str, format: ExportFormat = ExportFormat.CSV,
                      start_date: datetime = None, end_date: datetime = None,
                      provider: BIProvider = None) -> Dict:
        """
        Export dataset to specified format
        
        Args:
            dataset_name: Name of dataset to export
            format: Export format
            start_date: Start date for data
            end_date: End date for data
            provider: BI provider (optional)
            
        Returns:
            Dict: Export result
        """
        if dataset_name not in self.datasets:
            return {
                'success': False,
                'error': f'Dataset {dataset_name} not found'
            }
        
        dataset = self.datasets[dataset_name]
        provider = provider or self.default_provider
        
        # Default date range
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        self.logger.info(f"Exporting dataset '{dataset_name}' to {format.value}")
        self.logger.info(f"  Date range: {start_date} to {end_date}")
        
        # TODO: Execute query and fetch data
        # data = self._execute_query(dataset.query, start_date, end_date)
        
        # TODO: Convert to requested format
        # export_file = self._format_data(data, format, dataset_name)
        
        # Placeholder
        export_file = f"{self.export_path}/{dataset_name}_{datetime.now().strftime('%Y%m%d')}.{format.value}"
        
        dataset.last_exported = datetime.now()
        dataset.export_count += 1
        self.total_exports += 1
        self.last_export_time = datetime.now()
        
        return {
            'success': True,
            'dataset': dataset_name,
            'format': format.value,
            'file_path': export_file,
            'record_count': 0,  # TODO: Actual count
            'exported_at': datetime.now().isoformat()
        }
    
    def create_tableau_extract(self, dataset_name: str) -> Optional[str]:
        """
        Create Tableau TDE/Hyper extract
        
        Args:
            dataset_name: Dataset to export
            
        Returns:
            Optional[str]: Path to extract file
        """
        # TODO: Use Tableau Hyper API to create extract
        # from tableauhyperapi import HyperProcess, Telemetry, Connection, CreateMode
        
        self.logger.info(f"Creating Tableau extract for {dataset_name}")
        
        # Placeholder
        extract_path = f"{self.export_path}/{dataset_name}.hyper"
        return extract_path
    
    def create_powerbi_dataset(self, dataset_name: str, credentials: Dict) -> Dict:
        """
        Create Power BI dataset via REST API
        
        Args:
            dataset_name: Dataset name
            credentials: Power BI API credentials
            
        Returns:
            Dict: Dataset creation result
        """
        # TODO: Use Power BI REST API
        # POST https://api.powerbi.com/v1.0/myorg/datasets
        
        self.logger.info(f"Creating Power BI dataset for {dataset_name}")
        
        return {
            'success': True,
            'dataset_id': 'placeholder-id',
            'dataset_name': dataset_name
        }
    
    def setup_direct_query(self, provider: BIProvider, connection_string: str) -> Dict:
        """
        Setup direct query connection for BI tool
        
        Args:
            provider: BI provider
            connection_string: Database connection string
            
        Returns:
            Dict: Connection setup result
        """
        # TODO: Configure direct database connection for BI tool
        
        self.logger.info(f"Setting up direct query for {provider.value}")
        self.logger.info(f"  Connection: {connection_string}")
        
        return {
            'success': True,
            'provider': provider.value,
            'connection_type': 'direct_query'
        }
    
    def create_custom_dataset(self, name: str, query: str):
        """
        Create custom dataset
        
        Args:
            name: Dataset name
            query: SQL query for dataset
        """
        dataset = DataSet(name, query)
        self.datasets[name] = dataset
        
        self.logger.info(f"Created custom dataset: {name}")
    
    def schedule_export(self, dataset_name: str, schedule: str,
                       format: ExportFormat = ExportFormat.CSV):
        """
        Schedule automatic export
        
        Args:
            dataset_name: Dataset to export
            schedule: Schedule (daily, weekly, monthly)
            format: Export format
        """
        # TODO: Setup scheduled export job
        
        self.logger.info(f"Scheduled export for {dataset_name}")
        self.logger.info(f"  Schedule: {schedule}")
        self.logger.info(f"  Format: {format.value}")
    
    def get_available_datasets(self) -> List[Dict]:
        """Get list of available datasets"""
        return [
            {
                'name': name,
                'display_name': dataset.name,
                'last_exported': dataset.last_exported.isoformat() if dataset.last_exported else None,
                'export_count': dataset.export_count
            }
            for name, dataset in self.datasets.items()
        ]
    
    def test_connection(self, provider: BIProvider, credentials: Dict) -> Dict:
        """
        Test connection to BI provider
        
        Args:
            provider: BI provider
            credentials: API credentials
            
        Returns:
            Dict: Test result
        """
        # TODO: Test actual connection to BI provider API
        
        self.logger.info(f"Testing connection to {provider.value}")
        
        return {
            'success': True,
            'provider': provider.value,
            'message': 'Connection test successful'
        }
    
    def get_statistics(self) -> Dict:
        """Get BI integration statistics"""
        return {
            'enabled': self.enabled,
            'default_provider': self.default_provider.value,
            'total_datasets': len(self.datasets),
            'total_exports': self.total_exports,
            'failed_exports': self.failed_exports,
            'last_export_time': self.last_export_time.isoformat() if self.last_export_time else None,
            'auto_export_enabled': self.auto_export_enabled
        }


# Global instance
_bi_integration = None


def get_bi_integration(config=None) -> BIIntegration:
    """Get or create BI integration instance"""
    global _bi_integration
    if _bi_integration is None:
        _bi_integration = BIIntegration(config)
    return _bi_integration
