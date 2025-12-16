# Business Intelligence Integration Guide

## Overview

The PBX system includes a comprehensive Business Intelligence (BI) Integration framework that enables exporting call data, statistics, and analytics to popular BI tools for advanced reporting and visualization.

## Supported BI Tools

- **Tableau** - REST API, TDE/Hyper files
- **Microsoft Power BI** - REST API, DirectQuery
- **Google Looker** - LookML, SQL
- **Qlik Sense** - QVD files, REST API
- **Metabase** - SQL, API

## Features

### Data Export Capabilities
- Multiple export formats: CSV, JSON, Parquet, Excel, SQL
- Scheduled exports (daily, weekly, monthly)
- On-demand export via API
- Incremental and full data exports

### Default Datasets
- **Call Detail Records (CDR)** - Complete call history
- **Queue Statistics** - Call center metrics
- **QoS Metrics** - Call quality data
- **Agent Performance** - Agent statistics
- **Custom Queries** - User-defined datasets

## Configuration

### config.yml
```yaml
features:
  bi_integration:
    enabled: true
    default_provider: tableau  # tableau, powerbi, looker, qlik, metabase
    export_path: /var/pbx/bi_exports
    auto_export: true
    export_schedule: daily  # daily, weekly, monthly
```

## Usage

### Python API

```python
from pbx.features.bi_integration import get_bi_integration, ExportFormat

bi = get_bi_integration()

# Export CDR data
result = bi.export_data(
    dataset_name='cdr',
    format=ExportFormat.CSV,
    start_date='2025-01-01',
    end_date='2025-01-31'
)

# Register custom dataset
bi.register_dataset(
    name='custom_report',
    query='SELECT * FROM calls WHERE duration > 300'
)

# Export to specific BI tool
bi.export_to_provider(
    provider='tableau',
    dataset='cdr',
    format=ExportFormat.PARQUET
)
```

### REST API Endpoints

#### Export Data
```bash
POST /api/framework/bi-integration/export
{
  "dataset": "cdr",
  "format": "csv",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "filters": {
    "extension": "1001"
  }
}
```

#### List Datasets
```bash
GET /api/framework/bi-integration/datasets
```

#### Register Custom Dataset
```bash
POST /api/framework/bi-integration/dataset
{
  "name": "custom_report",
  "query": "SELECT * FROM calls WHERE duration > 300"
}
```

#### Get Export History
```bash
GET /api/framework/bi-integration/history
```

## Integration Examples

### Tableau

1. **Using REST API:**
```python
# Tableau Server REST API integration
bi.configure_provider('tableau', {
    'server_url': 'https://tableau.yourcompany.com',
    'site_id': 'your-site',
    'token_name': 'your-token',
    'token_value': 'your-token-value',
    'project_name': 'PBX Analytics'
})
```

2. **Using Hyper Files:**
```python
# Export to Tableau Hyper format
result = bi.export_data(
    dataset_name='cdr',
    format=ExportFormat.PARQUET,  # Tableau can read Parquet
    output_path='/var/pbx/bi_exports/cdr.parquet'
)
```

### Power BI

1. **DirectQuery Setup:**
```python
# Configure PostgreSQL connection for Power BI
bi.configure_provider('powerbi', {
    'database_connection': {
        'host': 'localhost',
        'port': 5432,
        'database': 'pbx_system',
        'schema': 'public'
    }
})
```

2. **REST API Integration:**
```python
# Power BI REST API
bi.configure_provider('powerbi', {
    'tenant_id': 'your-tenant-id',
    'client_id': 'your-client-id',
    'client_secret': 'your-client-secret',
    'workspace_id': 'your-workspace-id'
})
```

### Metabase

```python
# Metabase SQL-based integration
bi.configure_provider('metabase', {
    'database_connection': {
        'host': 'localhost',
        'port': 5432,
        'database': 'pbx_system'
    },
    'metabase_url': 'http://metabase.yourcompany.com',
    'api_key': 'your-api-key'
})
```

## Admin Panel

Access BI Integration configuration in the admin panel:

1. Navigate to **Admin Panel** → **Framework Features** → **BI Integration**
2. Configure default provider and export settings
3. View export history and statistics
4. Schedule automatic exports
5. Register custom datasets

## Best Practices

### Data Export
- **Incremental Exports:** Export only new/changed data to reduce load
- **Compression:** Use Parquet or compressed CSV for large datasets
- **Scheduling:** Schedule exports during off-peak hours
- **Retention:** Archive old exports to save disk space

### Performance
- **Indexing:** Ensure database tables have proper indexes
- **Partitioning:** Use table partitioning for large CDR tables
- **Caching:** Cache frequently accessed datasets
- **Batch Size:** Export data in manageable batches

### Security
- **Access Control:** Limit who can export sensitive data
- **Encryption:** Encrypt exports containing sensitive information
- **Audit Logging:** Track all export activities
- **Data Masking:** Mask PII data in exports when appropriate

## Troubleshooting

### Export Fails
```
Error: Failed to export data
```
**Solution:** Check export path permissions, disk space, and database connectivity.

### Large Export Takes Too Long
**Solution:** 
- Use incremental exports
- Export during off-peak hours
- Consider using database views for complex queries
- Use Parquet format for better compression

### BI Tool Connection Issues
**Solution:**
- Verify API credentials
- Check network connectivity
- Ensure BI tool API version compatibility
- Review firewall rules

## Database Schema

### bi_integration_configs
```sql
CREATE TABLE bi_integration_configs (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    settings JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### bi_export_history
```sql
CREATE TABLE bi_export_history (
    id SERIAL PRIMARY KEY,
    dataset VARCHAR(100) NOT NULL,
    format VARCHAR(20) NOT NULL,
    provider VARCHAR(50),
    file_path TEXT,
    record_count INTEGER,
    file_size_bytes BIGINT,
    export_duration_ms INTEGER,
    status VARCHAR(20),
    error_message TEXT,
    exported_at TIMESTAMP DEFAULT NOW()
);
```

## Statistics and Monitoring

The BI Integration system tracks:
- Total exports performed
- Failed exports count
- Average export duration
- Data volume exported
- Most frequently exported datasets

Access statistics via:
```bash
GET /api/framework/bi-integration/statistics
```

## Next Steps

1. **Choose BI Tool:** Select your preferred BI platform
2. **Configure Connection:** Set up API credentials or database connection
3. **Register Datasets:** Define the data you want to export
4. **Schedule Exports:** Set up automatic export schedules
5. **Build Dashboards:** Create visualizations in your BI tool
6. **Monitor:** Track export success and data freshness

## See Also

- [FRAMEWORK_IMPLEMENTATION_GUIDE.md](FRAMEWORK_IMPLEMENTATION_GUIDE.md)
- [DATABASE_MIGRATION_GUIDE.md](DATABASE_MIGRATION_GUIDE.md)
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
