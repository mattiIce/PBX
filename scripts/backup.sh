#!/bin/bash
#
# Automated Backup Script for Warden VoIP PBX
#
# This script performs comprehensive backups of the PBX system including:
# - PostgreSQL database
# - Configuration files
# - Voicemail recordings
# - Call recordings
# - SSL certificates
# - Custom voice prompts
#
# Usage:
#   sudo ./backup.sh [--full|--incremental] [--destination /path/to/backup]
#
# Cron example (daily at 2 AM):
#   0 2 * * * /path/to/pbx/scripts/backup.sh --full >> /var/log/pbx/backup.log 2>&1
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
PBX_DIR="${PBX_DIR:-/home/runner/work/PBX/PBX}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/pbx}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_BUCKET="${S3_BUCKET:-}"  # Optional: S3 bucket for off-site backups

# Validate RETENTION_DAYS to prevent command injection
# RETENTION_DAYS must be a positive integer
if ! [[ "$RETENTION_DAYS" =~ ^[0-9]+$ ]] || [ "$RETENTION_DAYS" -lt 1 ]; then
    echo "ERROR: RETENTION_DAYS must be a positive integer (got: '$RETENTION_DAYS')" >&2
    exit 1
fi

# Database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-pbx_system}"
DB_USER="${DB_USER:-pbx_user}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Parse arguments
BACKUP_TYPE="full"
CUSTOM_DESTINATION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            BACKUP_TYPE="full"
            shift
            ;;
        --incremental)
            BACKUP_TYPE="incremental"
            shift
            ;;
        --destination)
            CUSTOM_DESTINATION="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--full|--incremental] [--destination /path/to/backup]"
            echo ""
            echo "Options:"
            echo "  --full           Perform full backup (default)"
            echo "  --incremental    Perform incremental backup"
            echo "  --destination    Custom backup destination directory"
            echo "  --help           Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Use custom destination if provided
if [ -n "$CUSTOM_DESTINATION" ]; then
    BACKUP_DIR="$CUSTOM_DESTINATION"
fi

# Create backup directory structure
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/${TIMESTAMP}"

log "Starting $BACKUP_TYPE backup to: $BACKUP_PATH"

# Create backup directories
mkdir -p "$BACKUP_PATH"/{database,config,voicemail,recordings,ssl,prompts}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required commands
for cmd in pg_dump tar gzip; do
    if ! command_exists "$cmd"; then
        error "Required command not found: $cmd"
        exit 1
    fi
done

# 1. Backup PostgreSQL Database
log "Backing up PostgreSQL database..."
if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | gzip > "${BACKUP_PATH}/database/pbx_database.sql.gz"; then
    log "✓ Database backup completed"
else
    error "Database backup failed"
    exit 1
fi

# Also create a plain SQL backup for easier inspection
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" > "${BACKUP_PATH}/database/pbx_database.sql"

# 2. Backup Configuration Files
log "Backing up configuration files..."
CONFIGS=(
    "$PBX_DIR/config.yml"
    "$PBX_DIR/.env"
    "$PBX_DIR/test_config.yml"
)

for config in "${CONFIGS[@]}"; do
    if [ -f "$config" ]; then
        cp "$config" "${BACKUP_PATH}/config/" || warning "Could not backup: $config"
    fi
done

log "✓ Configuration files backup completed"

# 3. Backup Voicemail
log "Backing up voicemail recordings..."
if [ -d "$PBX_DIR/voicemail" ]; then
    tar -czf "${BACKUP_PATH}/voicemail/voicemail.tar.gz" -C "$PBX_DIR" voicemail/ 2>/dev/null || warning "Voicemail backup had warnings"
    log "✓ Voicemail backup completed"
else
    warning "Voicemail directory not found: $PBX_DIR/voicemail"
fi

# 4. Backup Call Recordings
log "Backing up call recordings..."
if [ -d "$PBX_DIR/recordings" ]; then
    # Only backup recent recordings (last 30 days) for incremental
    if [ "$BACKUP_TYPE" = "incremental" ]; then
        # The '|| warning' pattern allows tar to complete with warnings without exiting (despite set -e)
        find "$PBX_DIR/recordings" -type f -mtime -30 -print0 | \
            tar -czf "${BACKUP_PATH}/recordings/recordings_incremental.tar.gz" --null -T - 2>/dev/null || warning "Incremental recordings backup had warnings"
    else
        # The '|| warning' pattern allows tar to complete with warnings without exiting (despite set -e)
        tar -czf "${BACKUP_PATH}/recordings/recordings.tar.gz" -C "$PBX_DIR" recordings/ 2>/dev/null || warning "Full recordings backup had warnings"
    fi
    log "✓ Call recordings backup completed"
else
    warning "Recordings directory not found: $PBX_DIR/recordings"
fi

# 5. Backup SSL Certificates
log "Backing up SSL certificates..."
if [ -d "$PBX_DIR/ssl" ]; then
    tar -czf "${BACKUP_PATH}/ssl/ssl_certificates.tar.gz" -C "$PBX_DIR" ssl/ 2>/dev/null || warning "SSL backup had warnings"
    log "✓ SSL certificates backup completed"
else
    warning "SSL directory not found: $PBX_DIR/ssl"
fi

# 6. Backup Voice Prompts
log "Backing up voice prompts..."
if [ -d "$PBX_DIR/voicemail_prompts" ]; then
    tar -czf "${BACKUP_PATH}/prompts/voicemail_prompts.tar.gz" -C "$PBX_DIR" voicemail_prompts/ 2>/dev/null || warning "Prompts backup had warnings"
    log "✓ Voice prompts backup completed"
fi

# Create backup manifest
log "Creating backup manifest..."
cat > "${BACKUP_PATH}/MANIFEST.txt" <<EOF
PBX Backup Manifest
===================
Backup Type: $BACKUP_TYPE
Date: $(date '+%Y-%m-%d %H:%M:%S')
Hostname: $(hostname)
PBX Directory: $PBX_DIR
Database: $DB_NAME

Contents:
EOF

find "$BACKUP_PATH" -type f -exec ls -lh {} \; | awk '{print $9, "\t", $5}' >> "${BACKUP_PATH}/MANIFEST.txt"

# Calculate total backup size
BACKUP_SIZE=$(du -sh "$BACKUP_PATH" | cut -f1)
log "Total backup size: $BACKUP_SIZE"

# Create checksum file for verification
log "Creating checksums..."
find "$BACKUP_PATH" -type f -not -name "CHECKSUMS.txt" -exec sha256sum {} \; > "${BACKUP_PATH}/CHECKSUMS.txt"

# Create a compressed archive of the entire backup
log "Creating compressed backup archive..."
ARCHIVE_NAME="pbx_backup_${TIMESTAMP}.tar.gz"
tar -czf "${BACKUP_DIR}/${ARCHIVE_NAME}" -C "$BACKUP_DIR" "$TIMESTAMP"
log "✓ Backup archive created: ${BACKUP_DIR}/${ARCHIVE_NAME}"

# Upload to S3 if configured
if [ -n "$S3_BUCKET" ] && command_exists aws; then
    log "Uploading backup to S3: s3://${S3_BUCKET}/pbx-backups/"
    if aws s3 cp "${BACKUP_DIR}/${ARCHIVE_NAME}" "s3://${S3_BUCKET}/pbx-backups/${ARCHIVE_NAME}"; then
        log "✓ Backup uploaded to S3"
    else
        error "S3 upload failed"
    fi
fi

# Cleanup old backups
log "Cleaning up old backups (older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -maxdepth 1 -type d -name "20*" -mtime +$RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true
find "$BACKUP_DIR" -maxdepth 1 -type f -name "pbx_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

if [ -n "$S3_BUCKET" ] && command_exists aws; then
    # Cleanup old S3 backups
    # NOTE: This uses GNU date syntax. On BSD/macOS, install GNU coreutils or adjust the date command.
    CUTOFF_DATE=$(date -d "$RETENTION_DAYS days ago" +%Y%m%d)
    aws s3 ls "s3://${S3_BUCKET}/pbx-backups/" | while read -r line; do
        BACKUP_FILE=$(echo "$line" | awk '{print $4}')
        BACKUP_DATE=$(echo "$BACKUP_FILE" | grep -oP '\d{8}' | head -1)
        if [ -n "$BACKUP_DATE" ] && [ "$BACKUP_DATE" -lt "$CUTOFF_DATE" ]; then
            log "Deleting old S3 backup: $BACKUP_FILE"
            aws s3 rm "s3://${S3_BUCKET}/pbx-backups/$BACKUP_FILE"
        fi
    done
fi

# Verify backup
log "Verifying backup integrity..."
if tar -tzf "${BACKUP_DIR}/${ARCHIVE_NAME}" >/dev/null 2>&1; then
    log "✓ Backup archive integrity verified"
else
    error "Backup archive verification failed!"
    exit 1
fi

# Summary
log "==================================="
log "Backup completed successfully!"
log "==================================="
log "Backup location: ${BACKUP_DIR}/${ARCHIVE_NAME}"
log "Backup size: $BACKUP_SIZE"
log "Backup type: $BACKUP_TYPE"
log "Timestamp: $TIMESTAMP"

# Send notification (if configured)
if command_exists mail && [ -n "${BACKUP_NOTIFICATION_EMAIL:-}" ]; then
    echo "PBX backup completed successfully. Size: $BACKUP_SIZE" | \
        mail -s "PBX Backup Success - $TIMESTAMP" "$BACKUP_NOTIFICATION_EMAIL"
fi

exit 0
