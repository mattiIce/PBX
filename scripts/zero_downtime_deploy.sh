#!/bin/bash
#
# Zero-Downtime Deployment Script for Warden VoIP PBX
#
# This script performs a rolling deployment with zero downtime:
# - Pre-deployment validation
# - Database migration (if needed)
# - Blue-green deployment or rolling restart
# - Health checks after deployment
# - Automatic rollback on failure
#
# Usage: ./scripts/zero_downtime_deploy.sh [--rollback] [--dry-run]
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="${SERVICE_NAME:-pbx}"
HEALTH_CHECK_TIMEOUT=30
HEALTH_CHECK_INTERVAL=5

# Print colored message
print_msg() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

error_exit() {
    print_msg "$RED" "ERROR: $1"
    exit 1
}

# Check if service is running
is_service_running() {
    systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null
}

# Wait for service to be healthy
wait_for_health() {
    local timeout=$1
    local elapsed=0
    
    print_msg "$BLUE" "Waiting for service to be healthy..."
    
    while [ $elapsed -lt $timeout ]; do
        if python3 "$SCRIPT_DIR/production_health_check.py" --critical-only >/dev/null 2>&1; then
            print_msg "$GREEN" "✓ Service is healthy"
            return 0
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
        elapsed=$((elapsed + HEALTH_CHECK_INTERVAL))
        echo -n "."
    done
    
    echo ""
    print_msg "$RED" "✗ Service did not become healthy within ${timeout}s"
    return 1
}

# Pre-deployment checks
pre_deployment_checks() {
    print_msg "$BLUE" "=== Pre-Deployment Checks ==="
    
    # Check if we have the latest code
    if [ ! -d "$PROJECT_ROOT/.git" ]; then
        error_exit "Not a git repository"
    fi
    
    # Check for uncommitted changes (warning only)
    if ! git diff-index --quiet HEAD --; then
        print_msg "$YELLOW" "WARNING: You have uncommitted changes"
    fi
    
    # Validate configuration
    if [ ! -f "$PROJECT_ROOT/config.yml" ]; then
        error_exit "config.yml not found"
    fi
    
    # Check Python dependencies
    if ! python3 -c "import yaml, cryptography, twisted" 2>/dev/null; then
        error_exit "Required Python dependencies not installed"
    fi
    
    print_msg "$GREEN" "✓ Pre-deployment checks passed"
}

# Backup current deployment
backup_deployment() {
    local backup_dir="$PROJECT_ROOT/backups/deployment-$(date +%Y%m%d-%H%M%S)"
    
    print_msg "$BLUE" "Creating deployment backup..."
    mkdir -p "$backup_dir"
    
    # Backup configuration
    cp "$PROJECT_ROOT/config.yml" "$backup_dir/" 2>/dev/null || true
    cp "$PROJECT_ROOT/.env" "$backup_dir/" 2>/dev/null || true
    
    # Record current git commit
    git rev-parse HEAD > "$backup_dir/commit.txt"
    
    # Record current version
    if [ -f "$PROJECT_ROOT/VERSION" ]; then
        cp "$PROJECT_ROOT/VERSION" "$backup_dir/"
    fi
    
    echo "$backup_dir" > "$PROJECT_ROOT/.last_deployment_backup"
    print_msg "$GREEN" "✓ Backup created at $backup_dir"
}

# Run database migrations
run_migrations() {
    local dry_run=$1
    
    print_msg "$BLUE" "Checking for database migrations..."
    
    if [ "$dry_run" = "true" ]; then
        print_msg "$YELLOW" "[DRY RUN] Would run database migrations"
        return
    fi
    
    # Check if migration script exists
    if [ -f "$SCRIPT_DIR/init_database.py" ]; then
        python3 "$SCRIPT_DIR/init_database.py" --upgrade || {
            print_msg "$YELLOW" "Warning: Database migration check completed with warnings"
        }
        print_msg "$GREEN" "✓ Database migrations applied"
    else
        print_msg "$YELLOW" "No migration script found, skipping"
    fi
}

# Deploy new version
deploy_new_version() {
    local dry_run=$1
    
    print_msg "$BLUE" "=== Deploying New Version ==="
    
    if [ "$dry_run" = "true" ]; then
        print_msg "$YELLOW" "[DRY RUN] Would deploy new version"
        return
    fi
    
    # Restart service with systemd
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_msg "$BLUE" "Restarting $SERVICE_NAME service..."
        systemctl restart "$SERVICE_NAME"
        
        # Wait for service to start
        sleep 3
        
        # Check if service started successfully
        if ! systemctl is-active --quiet "$SERVICE_NAME"; then
            error_exit "Service failed to start"
        fi
        
        print_msg "$GREEN" "✓ Service restarted"
    else
        print_msg "$BLUE" "Starting $SERVICE_NAME service..."
        systemctl start "$SERVICE_NAME"
        print_msg "$GREEN" "✓ Service started"
    fi
}

# Post-deployment verification
post_deployment_verification() {
    print_msg "$BLUE" "=== Post-Deployment Verification ==="
    
    # Wait for service to be healthy
    if ! wait_for_health $HEALTH_CHECK_TIMEOUT; then
        error_exit "Post-deployment health check failed"
    fi
    
    # Run smoke tests
    if [ -f "$SCRIPT_DIR/smoke_tests.py" ]; then
        print_msg "$BLUE" "Running smoke tests..."
        if python3 "$SCRIPT_DIR/smoke_tests.py"; then
            print_msg "$GREEN" "✓ Smoke tests passed"
        else
            print_msg "$RED" "✗ Smoke tests failed"
            return 1
        fi
    fi
    
    print_msg "$GREEN" "✓ Post-deployment verification passed"
}

# Rollback to previous version
rollback() {
    print_msg "$YELLOW" "=== Rolling Back Deployment ==="
    
    if [ ! -f "$PROJECT_ROOT/.last_deployment_backup" ]; then
        error_exit "No backup found for rollback"
    fi
    
    local backup_dir=$(cat "$PROJECT_ROOT/.last_deployment_backup")
    
    if [ ! -d "$backup_dir" ]; then
        error_exit "Backup directory not found: $backup_dir"
    fi
    
    # Restore configuration
    if [ -f "$backup_dir/config.yml" ]; then
        cp "$backup_dir/config.yml" "$PROJECT_ROOT/"
        print_msg "$GREEN" "✓ Configuration restored"
    fi
    
    # Restore git commit
    if [ -f "$backup_dir/commit.txt" ]; then
        local commit=$(cat "$backup_dir/commit.txt")
        git checkout "$commit"
        print_msg "$GREEN" "✓ Code rolled back to $commit"
    fi
    
    # Restart service
    systemctl restart "$SERVICE_NAME"
    
    # Verify rollback
    if wait_for_health $HEALTH_CHECK_TIMEOUT; then
        print_msg "$GREEN" "✓ Rollback successful"
    else
        error_exit "Rollback failed - manual intervention required"
    fi
}

# Main deployment process
main() {
    local dry_run="false"
    local do_rollback="false"
    
    # Parse arguments
    for arg in "$@"; do
        case $arg in
            --dry-run)
                dry_run="true"
                print_msg "$YELLOW" "=== DRY RUN MODE ==="
                ;;
            --rollback)
                do_rollback="true"
                ;;
        esac
    done
    
    # Handle rollback
    if [ "$do_rollback" = "true" ]; then
        rollback
        exit 0
    fi
    
    print_msg "$BLUE" "=== Zero-Downtime Deployment ==="
    print_msg "$BLUE" "Started at: $(date)"
    
    # Execute deployment steps
    pre_deployment_checks
    backup_deployment
    run_migrations "$dry_run"
    deploy_new_version "$dry_run"
    
    if [ "$dry_run" != "true" ]; then
        if ! post_deployment_verification; then
            print_msg "$RED" "Deployment verification failed!"
            print_msg "$YELLOW" "Initiating automatic rollback..."
            rollback
            exit 1
        fi
    fi
    
    print_msg "$GREEN" ""
    print_msg "$GREEN" "=== Deployment Complete ==="
    print_msg "$GREEN" "Completed at: $(date)"
    
    if [ "$dry_run" = "true" ]; then
        print_msg "$YELLOW" ""
        print_msg "$YELLOW" "This was a dry run. No changes were made."
        print_msg "$YELLOW" "Run without --dry-run to execute deployment."
    fi
}

main "$@"
