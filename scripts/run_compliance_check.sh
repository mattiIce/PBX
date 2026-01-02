#!/bin/bash
#
# Quick Security Compliance Check Wrapper
# Simplifies running compliance checks with common options
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPLIANCE_SCRIPT="$SCRIPT_DIR/security_compliance_check.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Display usage
usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Quick wrapper for security compliance checking.

OPTIONS:
    -h, --help              Show this help message
    -f, --full              Full compliance check (default)
    -q, --quick             Quick check (quiet mode, exit code only)
    -j, --json              JSON output
    -o, --output FILE       Save report to FILE
    -m, --monitor           Monitor mode (for cron jobs)
    --fips-only            Check FIPS compliance only
    --soc2-only            Check SOC 2 compliance only

EXAMPLES:
    # Full check with detailed output
    $(basename "$0")

    # Quick check for monitoring
    $(basename "$0") --quick

    # Generate JSON report
    $(basename "$0") --json --output compliance.json

    # Monitor mode (for cron)
    $(basename "$0") --monitor

EOF
    exit 0
}

# Monitor mode - log to file and send alerts on failure
monitor_mode() {
    LOG_DIR="/var/log/pbx"
    LOG_FILE="$LOG_DIR/compliance_$(date +%Y%m%d_%H%M%S).log"
    
    # Create log directory if it doesn't exist
    mkdir -p "$LOG_DIR" 2>/dev/null || true
    
    echo -e "${BLUE}Running compliance check in monitor mode...${NC}"
    echo "Logging to: $LOG_FILE"
    
    if python3 "$COMPLIANCE_SCRIPT" --quiet > "$LOG_FILE" 2>&1; then
        echo -e "${GREEN}✓ Compliance check PASSED${NC}"
        exit 0
    else
        echo -e "${RED}✗ Compliance check FAILED${NC}"
        echo "See log: $LOG_FILE"
        
        # Send alert if mail command is available
        if command -v mail &> /dev/null; then
            mail -s "PBX Compliance Check Failed" root < "$LOG_FILE"
        fi
        
        exit 1
    fi
}

# FIPS only check
fips_only() {
    echo -e "${BLUE}Running FIPS 140-2 compliance check...${NC}"
    python3 "$SCRIPT_DIR/verify_fips.py"
}

# SOC 2 only check (via main script, filtered)
soc2_only() {
    echo -e "${BLUE}Running SOC 2 Type 2 compliance check...${NC}"
    python3 "$COMPLIANCE_SCRIPT" --json | jq '.soc2'
}

# Main execution
main() {
    local mode="full"
    local args=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                ;;
            -f|--full)
                mode="full"
                shift
                ;;
            -q|--quick)
                args="--quiet"
                shift
                ;;
            -j|--json)
                args="$args --json"
                shift
                ;;
            -o|--output)
                args="$args --output $2"
                shift 2
                ;;
            -m|--monitor)
                monitor_mode
                exit $?
                ;;
            --fips-only)
                fips_only
                exit $?
                ;;
            --soc2-only)
                soc2_only
                exit $?
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                usage
                ;;
        esac
    done
    
    # Run the compliance check
    echo -e "${BLUE}Running comprehensive security compliance check...${NC}"
    echo ""
    
    if python3 "$COMPLIANCE_SCRIPT" $args; then
        EXIT_CODE=0
        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}  Compliance check completed successfully${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    else
        EXIT_CODE=$?
        echo ""
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}  Compliance check completed with issues${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${YELLOW}Review the issues above and consult:${NC}"
        echo "  - scripts/README_SECURITY_COMPLIANCE.md"
        echo "  - SECURITY_GUIDE.md"
        echo "  - REGULATIONS_COMPLIANCE_GUIDE.md"
    fi
    
    exit $EXIT_CODE
}

# Check if compliance script exists
if [ ! -f "$COMPLIANCE_SCRIPT" ]; then
    echo -e "${RED}Error: Compliance script not found: $COMPLIANCE_SCRIPT${NC}"
    exit 1
fi

# Run main
main "$@"
