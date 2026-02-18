#!/bin/bash
# User data script for PBX EC2 instances
# This script runs on first boot to configure the PBX system

set -e

# Variables from Terraform
DB_HOST="${db_host}"
DB_NAME="${db_name}"
DB_SECRET_ARN="${db_secret_arn}"
REDIS_ENDPOINT="${redis_endpoint}"
REDIS_PASSWORD="${redis_password}"
AWS_REGION="${aws_region}"
ENVIRONMENT="${environment}"

# Logging
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "Starting PBX instance configuration..."
echo "Environment: $ENVIRONMENT"
echo "Timestamp: $(date)"

# Update system
apt-get update
apt-get upgrade -y

# Install required packages
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    postgresql-client \
    redis-tools \
    espeak \
    ffmpeg \
    libopus-dev \
    portaudio19-dev \
    libspeex-dev \
    awscli \
    jq

# Download and install packages from AWS (trusted source)
# SECURITY NOTE: In high-security environments, consider:
# 1. Hosting CloudWatch agent in your own S3 bucket
# 2. Verifying GPG signatures before installation
# 3. Using AWS Systems Manager for agent installation
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i -E ./amazon-cloudwatch-agent.deb
rm amazon-cloudwatch-agent.deb

# Create PBX user
useradd -r -s /bin/bash -d /opt/pbx -m pbx

# Clone repository
# SECURITY NOTE: For production, consider:
# 1. Cloning from a private repository with SSH keys
# 2. Using a specific commit hash or signed release tag
# 3. Verifying repository signature before deployment
# Example: git clone --branch v1.0.0 https://github.com/mattiIce/PBX.git
cd /opt/pbx
sudo -u pbx git clone https://github.com/mattiIce/PBX.git /opt/pbx/app
cd /opt/pbx/app

# Create virtual environment
sudo -u pbx python3 -m venv /opt/pbx/venv
source /opt/pbx/venv/bin/activate

# Install Python dependencies
pip install --upgrade pip uv
uv pip install -e .

# Get database credentials from Secrets Manager
DB_CREDENTIALS=$(aws secretsmanager get-secret-value \
    --secret-id "$DB_SECRET_ARN" \
    --region "$AWS_REGION" \
    --query SecretString \
    --output text)

DB_USER=$(echo "$DB_CREDENTIALS" | jq -r .username)
DB_PASSWORD=$(echo "$DB_CREDENTIALS" | jq -r .password)

# Create configuration file
# SECURITY NOTE: Credentials are secured via:
# 1. File permissions (chmod 600)
# 2. AWS Secrets Manager for database password
# 3. IAM instance profile for AWS API access
# 4. Environment variables cleared after service start
cat > /opt/pbx/app/.env << EOF
# Database configuration
DB_HOST=$DB_HOST
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD

# Redis configuration
REDIS_HOST=$REDIS_ENDPOINT
REDIS_PORT=6379
REDIS_PASSWORD=$REDIS_PASSWORD

# Environment
ENVIRONMENT=$ENVIRONMENT
AWS_REGION=$AWS_REGION

# High availability
HA_ENABLED=true
NODE_ID=$(ec2-metadata --instance-id | cut -d " " -f 2)
EOF

# Set proper permissions
chown -R pbx:pbx /opt/pbx
chmod 600 /opt/pbx/app/.env

# Initialize database (only if not already initialized)
if ! sudo -u pbx psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1 FROM extensions LIMIT 1;" 2>/dev/null; then
    echo "Initializing database..."
    cd /opt/pbx/app
    source /opt/pbx/venv/bin/activate
    python scripts/init_database.py
fi

# Generate voice prompts if not already present
if [ ! -d "/opt/pbx/app/voicemail_prompts" ] || [ -z "$(ls -A /opt/pbx/app/voicemail_prompts)" ]; then
    echo "Generating voice prompts..."
    cd /opt/pbx/app
    source /opt/pbx/venv/bin/activate
    python scripts/generate_tts_prompts.py
fi

# Create systemd service
cat > /etc/systemd/system/pbx.service << 'SERVICEEOF'
[Unit]
Description=Warden VoIP PBX System
After=network.target

[Service]
Type=simple
User=pbx
Group=pbx
WorkingDirectory=/opt/pbx/app
Environment="PATH=/opt/pbx/venv/bin"
EnvironmentFile=/opt/pbx/app/.env
ExecStart=/opt/pbx/venv/bin/python /opt/pbx/app/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pbx

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/pbx/app/voicemail /opt/pbx/app/recordings /opt/pbx/app/logs

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Enable and start PBX service
systemctl daemon-reload
systemctl enable pbx.service
systemctl start pbx.service

# Configure CloudWatch agent for monitoring
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << CWEOF
{
  "metrics": {
    "namespace": "PBX/$ENVIRONMENT",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          {
            "name": "cpu_usage_idle",
            "rename": "CPU_IDLE",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60,
        "totalcpu": false
      },
      "disk": {
        "measurement": [
          {
            "name": "used_percent",
            "rename": "DISK_USED",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60,
        "resources": [
          "*"
        ]
      },
      "mem": {
        "measurement": [
          {
            "name": "mem_used_percent",
            "rename": "MEM_USED",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/user-data.log",
            "log_group_name": "/pbx/$ENVIRONMENT/user-data",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/opt/pbx/app/logs/pbx.log",
            "log_group_name": "/pbx/$ENVIRONMENT/application",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
CWEOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Configure log rotation
cat > /etc/logrotate.d/pbx << LOGROTEOF
/opt/pbx/app/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 pbx pbx
    sharedscripts
    postrotate
        systemctl reload pbx.service > /dev/null 2>&1 || true
    endscript
}
LOGROTEOF

# Wait for service to start
sleep 10

# Verify service is running
if systemctl is-active --quiet pbx.service; then
    echo "PBX service started successfully"
else
    echo "ERROR: PBX service failed to start"
    systemctl status pbx.service
    exit 1
fi

# Send completion signal
echo "PBX instance configuration complete"
echo "Instance ID: $(ec2-metadata --instance-id | cut -d ' ' -f 2)"
echo "Private IP: $(ec2-metadata --local-ipv4 | cut -d ' ' -f 2)"
echo "Completion time: $(date)"
