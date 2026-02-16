# Grafana Dashboards for PBX System

This directory contains pre-configured Grafana dashboards for monitoring the PBX system using Prometheus metrics.

## Available Dashboards

### 1. PBX System Overview (`pbx-overview.json`)

Comprehensive dashboard showing:
- **System Status**: Version info and overall health
- **Active Calls**: Real-time concurrent call count
- **Registered Extensions**: Number of registered SIP endpoints
- **Call Quality**: Average MOS (Mean Opinion Score)
- **Call Rate**: Calls per minute by status and direction
- **Call Duration**: Distribution histogram
- **System Resources**: CPU and memory usage
- **Network Quality**: Packet loss, jitter, RTT
- **Queue Statistics**: Waiting calls and average wait time
- **API Performance**: Response time percentiles
- **Database Connections**: Active connection count
- **Error Rate**: Errors per second by type
- **SIP Trunk Status**: Trunk up/down status
- **Certificate Expiry**: Days until SSL certificate expiration
- **Authentication**: Success/failure rates

## Setup Instructions

### Prerequisites

1. **Prometheus** configured to scrape PBX metrics
2. **Grafana** installed and running
3. PBX system exposing Prometheus metrics endpoint

### 1. Configure Prometheus

Add this job to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'pbx'
    static_configs:
      - targets: ['pbx-server:9000']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s
```

### 2. Add Prometheus Data Source in Grafana

1. Open Grafana UI
2. Go to **Configuration** → **Data Sources**
3. Click **Add data source**
4. Select **Prometheus**
5. Configure:
   - **Name**: `Prometheus-PBX`
   - **URL**: `http://prometheus:9090` (or your Prometheus URL)
   - **Access**: `Server` (default)
6. Click **Save & Test**

### 3. Import Dashboard

**Method 1: Via Grafana UI**
1. Go to **Dashboards** → **Import**
2. Click **Upload JSON file**
3. Select `pbx-overview.json`
4. Select **Prometheus-PBX** as the data source
5. Click **Import**

**Method 2: Via Provisioning**
1. Copy dashboard JSON to Grafana provisioning directory:
   ```bash
   sudo cp pbx-overview.json /etc/grafana/provisioning/dashboards/
   ```

2. Create provisioning config if not exists:
   ```bash
   sudo nano /etc/grafana/provisioning/dashboards/pbx.yaml
   ```

3. Add configuration:
   ```yaml
   apiVersion: 1
   providers:
     - name: 'PBX Dashboards'
       orgId: 1
       folder: 'PBX'
       type: file
       disableDeletion: false
       updateIntervalSeconds: 30
       allowUiUpdates: true
       options:
         path: /etc/grafana/provisioning/dashboards
         foldersFromFilesStructure: true
   ```

4. Restart Grafana:
   ```bash
   sudo systemctl restart grafana-server
   ```

## Enabling Metrics in PBX

### 1. Add Prometheus Dependency

```bash
uv pip install prometheus-client
```

### 2. Initialize Metrics Exporter

In your PBX application (e.g., `main.py`):

```python
from pbx.utils.prometheus_exporter import PBXMetricsExporter
from prometheus_client import start_http_server

# Initialize exporter
metrics = PBXMetricsExporter()

# Set system info
metrics.set_system_info(
    version="1.0.0",
    environment="production",
    instance="pbx-01"
)

# Start metrics server on port 9090
start_http_server(9090)
```

### 3. Record Metrics

In your call handling code:

```python
# Record call start
metrics.record_call_start(direction="inbound")

# Update call quality
metrics.update_call_quality(
    extension="1001",
    mos=4.2,
    packet_loss=0.5,
    jitter=15.0,
    rtt=20.0
)

# Record call end
metrics.record_call_end(
    duration=180.5,
    status="completed",
    direction="inbound"
)
```

### 4. Expose Metrics Endpoint

Add to your Flask/API server:

```python
from flask import Response
from prometheus_client import generate_latest

@app.route('/metrics')
def metrics_endpoint():
    """Prometheus metrics endpoint."""
    return Response(
        generate_latest(metrics.registry),
        mimetype='text/plain'
    )
```

## Dashboard Panels Explained

### Key Metrics

| Metric | Description | Threshold |
|--------|-------------|-----------|
| **Active Calls** | Current concurrent calls | Yellow: >50, Red: >100 |
| **MOS** | Call quality score (1-5) | Yellow: <3.5, Green: >4.0 |
| **Packet Loss** | Network packet loss % | Green: <1%, Yellow: <3%, Red: >3% |
| **Jitter** | Variation in packet arrival | Green: <30ms, Yellow: <50ms, Red: >50ms |
| **API Response Time** | P95 response time | Green: <500ms, Yellow: <1s, Red: >1s |
| **Certificate Expiry** | Days until expiration | Red: <14, Yellow: <30, Green: >30 |

### Alerts to Configure

Recommended alerts in Grafana:

1. **High Active Calls**
   ```
   pbx_active_calls > 80
   for 5m
   ```

2. **Poor Call Quality**
   ```
   avg(pbx_call_quality_mos) < 3.5
   for 5m
   ```

3. **High Packet Loss**
   ```
   avg(pbx_packet_loss_percent) > 3
   for 5m
   ```

4. **Certificate Expiring Soon**
   ```
   pbx_certificate_expiry_days < 14
   ```

5. **High Error Rate**
   ```
   rate(pbx_errors_total[5m]) > 10
   for 5m
   ```

6. **Trunk Down**
   ```
   pbx_trunk_status == 0
   ```

7. **High Queue Wait**
   ```
   pbx_queue_average_wait_seconds > 60
   for 5m
   ```

## Customization

### Adding Custom Panels

1. Edit dashboard in Grafana UI
2. Add new panel
3. Configure query using PromQL
4. Export updated JSON
5. Replace `pbx-overview.json`

### Example Custom Queries

**Call success rate:**
```promql
sum(rate(pbx_calls_total{status="completed"}[5m])) / 
sum(rate(pbx_calls_total[5m])) * 100
```

**Top extensions by call volume:**
```promql
topk(10, sum by (extension) (rate(pbx_calls_total[1h])))
```

**Average call duration:**
```promql
avg(rate(pbx_call_duration_seconds_sum[5m]) / 
    rate(pbx_call_duration_seconds_count[5m]))
```

## Troubleshooting

### No Data in Dashboards

1. **Check Prometheus is scraping:**
   ```bash
   curl http://prometheus:9090/api/v1/targets
   ```

2. **Check PBX metrics endpoint:**
   ```bash
   curl http://pbx-server:9000/metrics
   ```

3. **Verify Prometheus data source:**
   - Grafana → Configuration → Data Sources
   - Test connection

### Metrics Not Updating

1. Check scrape interval in Prometheus config
2. Verify PBX application is recording metrics
3. Check for errors in Prometheus logs

### Dashboard Import Fails

1. Ensure Grafana version compatibility
2. Update dashboard schema version if needed
3. Check JSON syntax validity

## Related Documentation

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [PBX Metrics Exporter Code](../../pbx/utils/prometheus_exporter.py)

## Support

For issues or questions:
1. Check PBX system logs
2. Review Prometheus targets status
3. Check Grafana data source configuration
4. Consult [OPERATIONS_RUNBOOK.md](../../docs/OPERATIONS_RUNBOOK.md) for troubleshooting

---
