# High Availability (HA) Deployment Guide

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Component Setup](#component-setup)
5. [Configuration](#configuration)
6. [Testing and Validation](#testing-and-validation)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This guide describes how to deploy the Warden VoIP PBX system in a high availability configuration to ensure:

- **99.99% uptime** (less than 1 hour downtime per year)
- **Zero downtime upgrades** via blue-green deployment
- **Automatic failover** in case of server failure
- **Geographic redundancy** for disaster recovery
- **Load distribution** across multiple PBX instances

### HA Deployment Options

| Option | Uptime | Complexity | Cost | Use Case |
|--------|--------|------------|------|----------|
| **Active-Passive** | 99.9% | Low | $ | Small deployments (< 100 users) |
| **Active-Active** | 99.99% | Medium | $$ | Medium deployments (100-500 users) |
| **Geographic Redundancy** | 99.999% | High | $$$ | Enterprise (> 500 users, multi-site) |

---

## Architecture

### Active-Passive Configuration

```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    │   (HAProxy/     │
                    │    Keepalived)  │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
         ┌──────────▼────────┐  ┌────▼──────────────┐
         │  PBX Primary      │  │  PBX Standby      │
         │  (Active)         │  │  (Passive)        │
         │  192.168.1.10     │  │  192.168.1.11     │
         └─────────┬─────────┘  └────────┬──────────┘
                   │                     │
                   │  ┌──────────────────┘
                   │  │
         ┌─────────▼──▼─────────┐
         │  PostgreSQL with     │
         │  Streaming Replica   │
         │  Primary + Standby   │
         └──────────────────────┘
```

### Active-Active Configuration

```
                    ┌─────────────────┐
                    │  DNS SRV        │
                    │  Load Balancer  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼────┐  ┌──────▼─────┐  ┌────▼──────┐
    │  PBX Node 1  │  │ PBX Node 2 │  │ PBX Node 3│
    │  .10 (A/A)   │  │ .11 (A/A)  │  │ .12 (A/A) │
    └─────────┬────┘  └──────┬─────┘  └────┬──────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
              ┌──────────────▼──────────────┐
              │  PostgreSQL Cluster         │
              │  (Patroni + Etcd)          │
              │  Auto-failover             │
              └─────────────────────────────┘
              
              ┌─────────────────────────────┐
              │  Redis Cluster              │
              │  (Session State)            │
              └─────────────────────────────┘
```

### Geographic Redundancy

```
    Region 1 (Primary)              Region 2 (DR)
    ┌─────────────────┐             ┌─────────────────┐
    │  PBX Cluster    │             │  PBX Cluster    │
    │  Node 1, 2      │◄───────────►│  Node 1, 2      │
    │  Active         │  Async Rep  │  Standby        │
    └────────┬────────┘             └────────┬────────┘
             │                               │
    ┌────────▼────────┐             ┌────────▼────────┐
    │  PostgreSQL     │             │  PostgreSQL     │
    │  Primary        │────────────►│  Replica        │
    └─────────────────┘  Streaming  └─────────────────┘
```

---

## Prerequisites

### Hardware Requirements (Per Node)

**Minimum for 100 users**:
- CPU: 4 cores (Intel Xeon or AMD EPYC)
- RAM: 16 GB
- Disk: 200 GB SSD (RAID 1 recommended)
- Network: 2 x 1 Gbps NICs (bonded for redundancy)

**Recommended for 500 users**:
- CPU: 8 cores
- RAM: 32 GB
- Disk: 500 GB NVMe SSD (RAID 10 recommended)
- Network: 2 x 10 Gbps NICs

### Network Requirements

- **Static IP addresses** for all nodes
- **Low latency** between nodes (< 5ms for same datacenter)
- **Dedicated VLAN** for PBX traffic (optional but recommended)
- **QoS configured** on network switches
- **Firewall rules** allowing:
  - SIP: 5060 UDP between nodes
  - RTP: 10000-20000 UDP between nodes
  - PostgreSQL: 5432 TCP between database nodes
  - Redis: 6379 TCP between PBX nodes
  - Keepalived: VRRP (IP protocol 112) for VIP

### Software Requirements

- Ubuntu 24.04 LTS on all nodes
- PostgreSQL 17+ with streaming replication
- HAProxy 2.8+ or Nginx Plus
- Keepalived 2.2+ for VIP management
- Redis 7+ for session state
- NTP synchronized across all nodes

---

## Component Setup

### 1. Database High Availability

#### Option A: PostgreSQL Streaming Replication (Active-Passive)

**On Primary Database Server (db1)**:

```bash
# Install PostgreSQL
sudo apt-get update
sudo apt-get install -y postgresql-14

# Configure for replication
sudo -u postgres psql << EOF
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'repl_password';
EOF

# Edit /etc/postgresql/14/main/postgresql.conf
sudo tee -a /etc/postgresql/14/main/postgresql.conf << EOF
# Replication settings
wal_level = replica
max_wal_senders = 3
wal_keep_size = 64
hot_standby = on
EOF

# Edit /etc/postgresql/14/main/pg_hba.conf
sudo tee -a /etc/postgresql/14/main/pg_hba.conf << EOF
# Replication connections
host    replication     replicator      192.168.1.11/32         scram-sha-256
EOF

# Restart PostgreSQL
sudo systemctl restart postgresql
```

**On Standby Database Server (db2)**:

```bash
# Stop PostgreSQL
sudo systemctl stop postgresql

# Remove data directory
sudo rm -rf /var/lib/postgresql/14/main

# Create base backup from primary
sudo -u postgres pg_basebackup -h 192.168.1.10 -D /var/lib/postgresql/14/main \
  -U replicator -P -v -R -X stream -C -S standby1

# Start PostgreSQL
sudo systemctl start postgresql

# Verify replication
sudo -u postgres psql -c "SELECT * FROM pg_stat_replication;"
```

#### Option B: Patroni for Automatic Failover (Active-Active)

**Install Patroni on all database nodes**:

```bash
# Install dependencies
sudo apt-get install -y python3-psycopg2 etcd

# Install Patroni
uv pip install patroni[etcd]

# Create Patroni configuration
sudo tee /etc/patroni.yml << EOF
scope: pbx-cluster
name: node1  # Change for each node: node1, node2, node3

restapi:
  listen: 0.0.0.0:8008
  connect_address: 192.168.1.10:8008  # This node's IP

etcd:
  hosts: 192.168.1.10:2379,192.168.1.11:2379,192.168.1.12:2379

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576
    postgresql:
      use_pg_rewind: true
      parameters:
        max_connections: 200
        shared_buffers: 4GB
        effective_cache_size: 12GB

  initdb:
    - encoding: UTF8
    - data-checksums

postgresql:
  listen: 0.0.0.0:5432
  connect_address: 192.168.1.10:5432
  data_dir: /var/lib/postgresql/14/main
  bin_dir: /usr/lib/postgresql/14/bin
  authentication:
    replication:
      username: replicator
      password: repl_password
    superuser:
      username: postgres
      password: postgres_password
  parameters:
    unix_socket_directories: '/var/run/postgresql'

tags:
  nofailover: false
  noloadbalance: false
  clonefrom: false
  nosync: false
EOF

# Start Patroni
sudo systemctl enable patroni
sudo systemctl start patroni

# Check cluster status
patronictl -c /etc/patroni.yml list
```

### 2. Load Balancer Setup

#### Option A: HAProxy + Keepalived (Simple HA)

**Install HAProxy on both load balancer nodes**:

```bash
sudo apt-get install -y haproxy keepalived

# Configure HAProxy
sudo tee /etc/haproxy/haproxy.cfg << EOF
global
    log /dev/log local0
    log /dev/log local1 notice
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy
    daemon

defaults
    log     global
    mode    tcp
    option  tcplog
    option  dontlognull
    timeout connect 5000
    timeout client  300000
    timeout server  300000

# SIP Frontend
frontend sip_frontend
    bind *:5060
    mode tcp
    default_backend sip_backend

# SIP Backend (Round-robin)
backend sip_backend
    mode tcp
    balance roundrobin
    option tcp-check
    server pbx1 192.168.1.10:5060 check inter 5s rise 2 fall 3
    server pbx2 192.168.1.11:5060 check inter 5s rise 2 fall 3

# RTP is stateful - use source hash for session affinity
frontend rtp_frontend
    bind *:10000-20000
    mode udp
    default_backend rtp_backend

backend rtp_backend
    mode udp
    balance source
    hash-type consistent
    server pbx1 192.168.1.10:10000-20000
    server pbx2 192.168.1.11:10000-20000

# HTTPS API Frontend
frontend https_api
    bind *:443 ssl crt /etc/ssl/certs/pbx.pem
    mode http
    default_backend api_backend

backend api_backend
    mode http
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200
    server pbx1 192.168.1.10:9000 check inter 10s
    server pbx2 192.168.1.11:9000 check inter 10s

# Stats page
listen stats
    bind *:8404
    mode http
    stats enable
    stats uri /stats
    stats refresh 30s
    stats admin if TRUE
EOF

# Enable and start HAProxy
sudo systemctl enable haproxy
sudo systemctl restart haproxy
```

**Configure Keepalived for VIP**:

```bash
# On LB1 (MASTER)
sudo tee /etc/keepalived/keepalived.conf << EOF
vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 150
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass $(openssl rand -base64 16)  # Generate a strong password
    }
    virtual_ipaddress {
        192.168.1.100/24 dev eth0
    }
}
EOF

# On LB2 (BACKUP)
sudo tee /etc/keepalived/keepalived.conf << EOF
vrrp_instance VI_1 {
    state BACKUP
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass $(openssl rand -base64 16)  # Use same password as MASTER
    }
    virtual_ipaddress {
        192.168.1.100/24 dev eth0
    }
}
EOF

# Start Keepalived on both nodes
sudo systemctl enable keepalived
sudo systemctl start keepalived
```

#### Option B: DNS SRV Load Balancing (Distributed)

**Configure DNS SRV records**:

```dns
; SIP SRV records with priorities and weights
_sip._udp.example.com. 300 IN SRV 10 50 5060 pbx1.example.com.
_sip._udp.example.com. 300 IN SRV 10 50 5060 pbx2.example.com.
_sip._udp.example.com. 300 IN SRV 20 100 5060 pbx3.example.com.

; A records for each PBX node
pbx1.example.com. 300 IN A 192.168.1.10
pbx2.example.com. 300 IN A 192.168.1.11
pbx3.example.com. 300 IN A 192.168.1.12
```

### 3. Redis Cluster for Session State

**On each PBX node**:

```bash
# Install Redis
sudo apt-get install -y redis-server redis-sentinel

# Configure Redis Cluster
sudo tee -a /etc/redis/redis.conf << EOF
# Cluster configuration
cluster-enabled yes
cluster-config-file nodes.conf
cluster-node-timeout 5000
appendonly yes
bind 0.0.0.0
protected-mode no
EOF

# Start Redis
sudo systemctl restart redis-server

# Create cluster (run on one node only)
redis-cli --cluster create \
  192.168.1.10:6379 \
  192.168.1.11:6379 \
  192.168.1.12:6379 \
  --cluster-replicas 0
```

### 4. PBX Application Setup

**On each PBX node**:

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/mattiIce/PBX.git
cd PBX

# Install dependencies
make install-prod

# Configure for HA
sudo tee /opt/PBX/config.yml << EOF
# Database connection (use VIP or Patroni endpoint)
database:
  host: ${DB_VIP:-192.168.1.100}
  port: 5432
  name: pbx_system
  user: pbx_user
  password: ${DB_PASSWORD}
  pool_size: 50
  max_overflow: 100

# Redis for session state
redis:
  enabled: true
  cluster: true
  nodes:
    - host: 192.168.1.10
      port: 6379
    - host: 192.168.1.11
      port: 6379
    - host: 192.168.1.12
      port: 6379

# HA settings
high_availability:
  enabled: true
  node_id: ${NODE_ID}  # Unique per node: node1, node2, node3
  cluster_name: pbx-cluster
  health_check_interval: 10
  failover_timeout: 30

# SIP configuration
sip:
  bind_address: 0.0.0.0
  bind_port: 5060
  advertise_address: ${PUBLIC_IP}  # This node's IP

# RTP configuration
rtp:
  port_range: [10000, 20000]
  bind_address: 0.0.0.0
  advertise_address: ${PUBLIC_IP}
EOF

# Install systemd service
sudo cp pbx.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pbx
sudo systemctl start pbx
```

---

## Configuration

### PBX HA-Specific Settings

Edit `config.yml` on each node:

```yaml
high_availability:
  enabled: true
  
  # Unique node identifier
  node_id: "node1"  # Change to node2, node3, etc.
  
  # Cluster settings
  cluster_name: "pbx-production"
  
  # Health monitoring
  health_check_interval: 10  # seconds
  health_check_timeout: 5
  
  # Failover settings
  failover_enabled: true
  failover_timeout: 30  # seconds
  auto_recovery: true
  
  # State synchronization
  state_sync:
    enabled: true
    sync_interval: 5  # seconds
    redis_cluster: true
    
  # Call preservation during failover
  call_preservation:
    enabled: true
    grace_period: 30  # Allow active calls to complete
    
  # Registration sync
  registration_sync:
    enabled: true
    sync_method: "redis"  # or "database"
```

### Database Connection Pooling

For HA deployments, configure connection pooling:

```yaml
database:
  pool_size: 50  # Increased for HA
  max_overflow: 100
  pool_pre_ping: true  # Test connections before use
  pool_recycle: 3600  # Recycle connections every hour
  
  # Connection retry settings
  connect_retry:
    max_attempts: 5
    retry_delay: 2  # seconds
    exponential_backoff: true
```

---

## Testing and Validation

### 1. Failover Testing

**Test Database Failover**:

```bash
# Stop primary database
sudo systemctl stop postgresql

# Watch for automatic promotion of standby
sudo -u postgres psql -c "SELECT pg_is_in_recovery();"
# Should return 'f' (false) on new primary

# Verify PBX nodes reconnected
curl http://192.168.1.10:9000/health
curl http://192.168.1.11:9000/health
```

**Test PBX Node Failover**:

```bash
# Make a test call
# Stop one PBX node
sudo systemctl stop pbx

# Verify call continues or new calls work
# Check load balancer redirected traffic
curl http://192.168.1.100:8404/stats
```

### 2. Load Testing

```bash
# Run load test against VIP
python scripts/load_test_sip.py \
  --pbx-host 192.168.1.100 \
  --concurrent-calls 100 \
  --total-calls 1000 \
  --test-type mixed
```

### 3. Network Partition Testing

```bash
# Simulate network partition
sudo iptables -A INPUT -s 192.168.1.11 -j DROP
sudo iptables -A OUTPUT -d 192.168.1.11 -j DROP

# Wait for cluster to detect failure
sleep 60

# Verify cluster still functions
# Remove partition
sudo iptables -D INPUT -s 192.168.1.11 -j DROP
sudo iptables -D OUTPUT -d 192.168.1.11 -j DROP

# Verify cluster rejoins
```

### 4. Disaster Recovery Testing

**Simulate Total Region Failure**:

```bash
# Document RTO and RPO
# Stop all nodes in primary region
# Promote DR region to primary
# Verify service restoration time
# Measure data loss (if any)
```

---

## Monitoring

### Key Metrics to Monitor

1. **Cluster Health**:
   - Node status (up/down)
   - Database replication lag
   - Load balancer health checks

2. **Performance**:
   - Active calls per node
   - Registration distribution
   - Response times
   - Resource utilization (CPU, RAM, disk, network)

3. **Failover Events**:
   - Failover count
   - Failover duration
   - Failed registrations during failover
   - Dropped calls during failover

### Grafana Dashboard

Import the HA dashboard:

```bash
# Import HA-specific dashboard
curl -X POST http://grafana:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @grafana/dashboards/pbx-ha-overview.json
```

### Alerting Rules

Configure alerts for HA issues:

```yaml
# In Prometheus alert rules
groups:
  - name: pbx_ha
    interval: 30s
    rules:
      - alert: PBXNodeDown
        expr: up{job="pbx"} == 0
        for: 1m
        annotations:
          summary: "PBX node {{ $labels.instance }} is down"
          
      - alert: DatabaseReplicationLag
        expr: pg_replication_lag_seconds > 60
        for: 5m
        annotations:
          summary: "Database replication lag is high"
          
      - alert: ClusterSplitBrain
        expr: count(up{job="pbx"} == 1) > 1 and count(pbx_cluster_leader) > 1
        for: 2m
        annotations:
          summary: "Cluster split-brain detected"
```

---

## Troubleshooting

### Common Issues

#### Split-Brain Condition

**Symptoms**: Multiple nodes think they are primary

**Solution**:
```bash
# Stop all nodes
sudo systemctl stop pbx

# Clear cluster state
redis-cli FLUSHDB

# Start one node first (becomes leader)
sudo systemctl start pbx

# Wait 30 seconds

# Start other nodes
```

#### Database Connection Issues

**Symptoms**: PBX can't connect to database after failover

**Solution**:
```bash
# Verify database is accepting connections
sudo -u postgres psql -c "SELECT 1;"

# Check PBX logs
journalctl -u pbx -f

# Restart PBX service
sudo systemctl restart pbx
```

#### Load Balancer Not Distributing Load

**Symptoms**: All traffic goes to one node

**Solution**:
```bash
# Check HAProxy stats
curl http://192.168.1.100:8404/stats

# Verify health checks
sudo tail -f /var/log/haproxy.log

# Test backend servers manually
nc -zv 192.168.1.10 5060
nc -zv 192.168.1.11 5060
```

---

## Best Practices

1. **Always test failover procedures** in staging before production
2. **Monitor replication lag** - keep it under 1 second
3. **Use odd number of nodes** (3 or 5) for quorum-based systems
4. **Keep node configurations identical** - use configuration management
5. **Automate health checks** - don't rely on manual monitoring
6. **Document RTO and RPO** - test regularly to verify
7. **Plan for network partitions** - implement proper fencing
8. **Use separate network for cluster communication** if possible
9. **Keep time synchronized** with NTP on all nodes
10. **Regular DR drills** - quarterly minimum

---

## Maintenance Windows

### Zero-Downtime Upgrades

```bash
# Rolling upgrade procedure
# 1. Upgrade one node at a time
# 2. Wait for health check to pass
# 3. Move to next node

for node in node1 node2 node3; do
  ssh $node "cd /opt/PBX && git pull && sudo systemctl restart pbx"
  sleep 60
  curl http://$node:9000/health || exit 1
done
```

### Planned Failover

```bash
# Gracefully move traffic before maintenance
# 1. Remove node from load balancer
# 2. Wait for active calls to complete
# 3. Perform maintenance
# 4. Add node back to load balancer
```

---

## Appendix

### A. Capacity Planning

| Users | Concurrent Calls | Nodes | CPU/Node | RAM/Node | DB | Redis |
|-------|------------------|-------|----------|----------|----|----|
| 100 | 25 | 2 | 4 cores | 16 GB | 1 primary + 1 replica | 2 nodes |
| 500 | 125 | 3 | 8 cores | 32 GB | 1 primary + 2 replicas | 3 nodes |
| 1000 | 250 | 5 | 16 cores | 64 GB | Patroni cluster (3 nodes) | 5 nodes |

### B. Cost Estimate

**Hardware costs for 500-user HA deployment**:
- Servers: 3 x $3,000 = $9,000
- Network equipment: $2,000
- Storage: $1,000
- Total: **~$12,000 one-time**

**Annual costs**:
- Power and cooling: $1,500/year
- Bandwidth: $600/year
- Total: **~$2,100/year**

### C. Reference Architecture Diagram

See `docs/diagrams/ha-architecture.png`

---

---
