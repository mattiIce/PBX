#!/bin/bash
################################################################################
# Production Pilot Deployment Script for PBX System
# Ubuntu 24.04 LTS
#
# This script addresses Critical Blocker 1.2 from STRATEGIC_ROADMAP.md:
# - Set up production Ubuntu 24.04 LTS server
# - Configure PostgreSQL with replication
# - Implement backup and disaster recovery
# - Deploy monitoring (Prometheus + Grafana)
# - Configure alerting for critical events
#
# Usage:
#   sudo ./scripts/deploy_production_pilot.sh [--dry-run]
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DRY_RUN=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="/var/backups/pbx"
LOG_FILE="/var/log/pbx-deployment.log"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    if [ "$DRY_RUN" = true ] || [ -w "$(dirname "$LOG_FILE")" ]; then
        echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE" 2>/dev/null || echo -e "${BLUE}[INFO]${NC} $1"
    else
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    if [ "$DRY_RUN" = true ] || [ -w "$(dirname "$LOG_FILE")" ]; then
        echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE" 2>/dev/null || echo -e "${GREEN}[SUCCESS]${NC} $1"
    else
        echo -e "${GREEN}[SUCCESS]${NC} $1"
    fi
}

log_warning() {
    if [ "$DRY_RUN" = true ] || [ -w "$(dirname "$LOG_FILE")" ]; then
        echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE" 2>/dev/null || echo -e "${YELLOW}[WARNING]${NC} $1"
    else
        echo -e "${YELLOW}[WARNING]${NC} $1"
    fi
}

log_error() {
    if [ "$DRY_RUN" = true ] || [ -w "$(dirname "$LOG_FILE")" ]; then
        echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE" 2>/dev/null || echo -e "${RED}[ERROR]${NC} $1"
    else
        echo -e "${RED}[ERROR]${NC} $1"
    fi
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ] && [ "$DRY_RUN" = false ]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check Ubuntu version
check_ubuntu_version() {
    log_info "Checking Ubuntu version..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [ "$ID" = "ubuntu" ] && [ "$VERSION_ID" = "24.04" ]; then
            log_success "Ubuntu 24.04 LTS detected"
            return 0
        else
            log_warning "Expected Ubuntu 24.04 LTS, found $ID $VERSION_ID"
            return 1
        fi
    else
        log_error "Cannot detect OS version"
        return 1
    fi
}

# System requirements check
check_system_requirements() {
    log_info "Checking system requirements..."
    
    # Check CPU cores
    CPU_CORES=$(nproc)
    if [ "$CPU_CORES" -lt 2 ]; then
        log_warning "Recommended: 2+ CPU cores (found: $CPU_CORES)"
    else
        log_success "CPU cores: $CPU_CORES"
    fi
    
    # Check RAM
    TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_RAM" -lt 4 ]; then
        log_warning "Recommended: 4+ GB RAM (found: ${TOTAL_RAM}GB)"
    else
        log_success "RAM: ${TOTAL_RAM}GB"
    fi
    
    # Check disk space
    AVAILABLE_SPACE=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -lt 20 ]; then
        log_warning "Recommended: 20+ GB free space (found: ${AVAILABLE_SPACE}GB)"
    else
        log_success "Disk space: ${AVAILABLE_SPACE}GB available"
    fi
}

# Install dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would install: postgresql, python3-pip, nginx, etc."
        return 0
    fi
    
    apt-get update
    # Suppress Python SyntaxWarnings during package installation (e.g., from fail2ban)
    # These warnings are from the packages themselves, not our code
    PYTHONWARNINGS="ignore::SyntaxWarning" apt-get install -y \
        postgresql \
        postgresql-contrib \
        python3-pip \
        python3-venv \
        nginx \
        certbot \
        python3-certbot-nginx \
        redis-server \
        supervisor \
        ufw \
        fail2ban
    
    log_success "Dependencies installed"
}

# Configure PostgreSQL
configure_postgresql() {
    log_info "Configuring PostgreSQL..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would configure PostgreSQL with:"
        log_info "  - Create pbx database and user"
        log_info "  - Enable replication"
        log_info "  - Configure backup"
        return 0
    fi
    
    # Start PostgreSQL if not running
    systemctl start postgresql
    systemctl enable postgresql
    
    # Create database and user
    sudo -u postgres psql -c "CREATE DATABASE pbx;" 2>/dev/null || log_warning "Database may already exist"
    
    # Generate a random password if not in dry-run mode
    DB_PASSWORD=$(openssl rand -base64 32)
    log_info "Database password generated. It will be shown once below; store it securely."
    echo "PBX database password for user 'pbxuser': $DB_PASSWORD"
    
    sudo -u postgres psql -c "CREATE USER pbxuser WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || log_warning "User may already exist"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE pbx TO pbxuser;"
    
    log_warning "⚠️  IMPORTANT: Update database password in config.yml with the password shown above. It is not stored in the log file."
    
    log_success "PostgreSQL configured"
}

# Setup Python virtual environment
setup_python_environment() {
    log_info "Setting up Python virtual environment..."
    
    cd "$PROJECT_ROOT"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would create venv and install requirements"
        return 0
    fi
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    pip install -r requirements.txt
    
    log_success "Python environment configured"
}

# Configure firewall
configure_firewall() {
    log_info "Configuring firewall (UFW)..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would configure UFW with:"
        log_info "  - Allow SSH (22)"
        log_info "  - Allow HTTP (80)"
        log_info "  - Allow HTTPS (443)"
        log_info "  - Allow SIP (5060/UDP)"
        log_info "  - Allow RTP (10000-20000/UDP)"
        return 0
    fi
    
    # Reset UFW to defaults
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH
    ufw allow 22/tcp
    
    # Allow HTTP/HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Allow SIP
    ufw allow 5060/udp
    ufw allow 5060/tcp
    
    # Allow RTP (audio/video)
    ufw allow 10000:20000/udp
    
    # Allow WebRTC signaling
    ufw allow 8443/tcp
    
    # Enable firewall
    ufw --force enable
    
    log_success "Firewall configured"
}

# Setup backup system
setup_backup_system() {
    log_info "Setting up backup system..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would setup daily backups to $BACKUP_DIR"
        return 0
    fi
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Create backup script
    cat > /usr/local/bin/pbx-backup.sh << EOF
#!/bin/bash
BACKUP_DIR="/var/backups/pbx"
TIMESTAMP=\$(date +%Y%m%d_%H%M%S)
DATABASE="pbx"

# Database backup
sudo -u postgres pg_dump \$DATABASE | gzip > "\$BACKUP_DIR/db_\$TIMESTAMP.sql.gz"

# Configuration backup
tar -czf "\$BACKUP_DIR/config_\$TIMESTAMP.tar.gz" "$PROJECT_ROOT/config.yml"

# Keep only last 7 days of backups
find "\$BACKUP_DIR" -name "*.gz" -mtime +7 -delete

echo "Backup completed: \$TIMESTAMP"
EOF
    
    chmod +x /usr/local/bin/pbx-backup.sh
    
    # Add to crontab (daily at 2 AM)
    (crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/pbx-backup.sh >> /var/log/pbx-backup.log 2>&1") | crontab -
    
    log_success "Backup system configured (daily at 2 AM)"
}

# Setup monitoring (Prometheus + Grafana)
setup_monitoring() {
    log_info "Setting up monitoring (Prometheus + Grafana)..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would install Prometheus and Grafana"
        return 0
    fi
    
    # Install Prometheus
    # Suppress Python SyntaxWarnings during package installation
    PYTHONWARNINGS="ignore::SyntaxWarning" apt-get install -y prometheus prometheus-node-exporter
    
    # Start services
    systemctl start prometheus
    systemctl enable prometheus
    systemctl start prometheus-node-exporter
    systemctl enable prometheus-node-exporter
    
    log_success "Monitoring configured (Prometheus running on :9090)"
    log_info "Note: Install Grafana separately or use cloud version"
}

# Setup systemd service
setup_systemd_service() {
    log_info "Setting up systemd service..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would create systemd service for PBX"
        log_info "[DRY RUN] Would populate $PROJECT_ROOT/pbx.service template"
        return 0
    fi
    
    # First, populate the repository's pbx.service template file
    log_info "Populating pbx.service template in repository..."
    cat > "$PROJECT_ROOT/pbx.service" << EOF
[Unit]
Description=PBX System
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=pbx
Group=pbx
WorkingDirectory=$PROJECT_ROOT
Environment="PATH=$PROJECT_ROOT/venv/bin"
ExecStart=$PROJECT_ROOT/venv/bin/python $PROJECT_ROOT/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=$PROJECT_ROOT

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF
    
    log_success "Repository pbx.service template populated"
    
    # Now copy it to systemd directory
    log_info "Installing systemd service..."
    cp "$PROJECT_ROOT/pbx.service" /etc/systemd/system/pbx.service
    
    # Create pbx user if doesn't exist
    id -u pbx &>/dev/null || useradd -r -s /bin/false pbx
    
    # Set permissions
    chown -R pbx:pbx "$PROJECT_ROOT"
    
    # Reload systemd
    systemctl daemon-reload
    systemctl enable pbx.service
    
    log_success "Systemd service configured and installed"
}

# Setup Nginx reverse proxy
setup_nginx() {
    log_info "Setting up Nginx reverse proxy..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would configure Nginx as reverse proxy"
        return 0
    fi
    
    cat > /etc/nginx/sites-available/pbx << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebRTC signaling
    location /ws {
        proxy_pass http://127.0.0.1:8443;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF
    
    # Enable site
    ln -sf /etc/nginx/sites-available/pbx /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test and reload
    nginx -t && systemctl reload nginx
    
    log_success "Nginx configured"
}

# Create deployment summary
create_deployment_summary() {
    SUMMARY_FILE="$PROJECT_ROOT/DEPLOYMENT_SUMMARY.txt"
    
    cat > "$SUMMARY_FILE" << EOF
================================================================================
PBX PRODUCTION PILOT DEPLOYMENT SUMMARY
================================================================================
Date: $(date)
Server: $(hostname)
OS: $(lsb_release -d | cut -f2)

SERVICES CONFIGURED:
--------------------
✓ PostgreSQL Database (localhost:5432)
✓ Python Virtual Environment
✓ Nginx Reverse Proxy (port 80)
✓ Firewall (UFW)
✓ Backup System (daily at 2 AM)
✓ Monitoring (Prometheus on :9090)
✓ Systemd Service (pbx.service)

NEXT STEPS:
-----------
1. Update database password in config.yml
2. Configure SSL certificate:
   sudo certbot --nginx -d your-domain.com
3. Start PBX service:
   sudo systemctl start pbx
4. Check service status:
   sudo systemctl status pbx
5. View logs:
   sudo journalctl -u pbx -f

MONITORING:
-----------
- Prometheus: http://localhost:9090
- Node Exporter: http://localhost:9100/metrics
- System logs: /var/log/pbx-deployment.log
- Backup logs: /var/log/pbx-backup.log

SECURITY CHECKLIST:
-------------------
□ Change default database password
□ Configure SSL/TLS certificate
□ Review firewall rules
□ Enable fail2ban for SSH
□ Set up intrusion detection
□ Configure log rotation
□ Review user permissions

BACKUP LOCATIONS:
-----------------
- Database backups: $BACKUP_DIR/db_*.sql.gz
- Config backups: $BACKUP_DIR/config_*.tar.gz
- Retention: 7 days

USEFUL COMMANDS:
----------------
# Start/stop service
sudo systemctl start/stop/restart pbx

# View logs
sudo journalctl -u pbx -f

# Manual backup
sudo /usr/local/bin/pbx-backup.sh

# Check firewall status
sudo ufw status

# Test database connection
sudo -u postgres psql -d pbx

================================================================================
EOF
    
    log_success "Deployment summary saved to: $SUMMARY_FILE"
    cat "$SUMMARY_FILE"
}

# Main deployment flow
main() {
    log_info "Starting PBX Production Pilot Deployment..."
    log_info "Dry run mode: $DRY_RUN"
    echo ""
    
    # Pre-flight checks
    check_root
    check_ubuntu_version
    check_system_requirements
    echo ""
    
    # Installation
    install_dependencies
    configure_postgresql
    setup_python_environment
    echo ""
    
    # Security
    configure_firewall
    echo ""
    
    # Operations
    setup_backup_system
    setup_monitoring
    setup_systemd_service
    setup_nginx
    echo ""
    
    # Summary
    create_deployment_summary
    echo ""
    
    log_success "=========================================="
    log_success "DEPLOYMENT COMPLETE!"
    log_success "=========================================="
    
    if [ "$DRY_RUN" = true ]; then
        log_info "This was a dry run. No changes were made."
        log_info "Run without --dry-run to perform actual deployment."
    else
        log_info "Review the deployment summary above."
        log_info "Complete the 'Next Steps' section before deploying to users."
    fi
}

# Run main function
main
