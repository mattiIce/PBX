#!/bin/bash
# Setup Apache Reverse Proxy for PBX System
# This script automates the configuration of Apache for accessing PBX via a domain name

set -e

# Cleanup temporary files on exit
trap 'rm -f /tmp/apache_test.log /tmp/certbot_output.log' EXIT

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Error patterns for certbot SSL certificate issues
CERTBOT_OPENSSL_ERROR_PATTERN='UnsupportedDigestmodError\|digital envelope routines'

# Helper function to check if port 80 is in use
is_port_80_in_use() {
    netstat -tuln 2>/dev/null | grep -q ':80 ' || ss -tuln 2>/dev/null | grep -q ':80 '
}

# Helper function to check if Apache processes are running
has_apache_processes() {
    pgrep apache2 >/dev/null 2>&1 || pgrep httpd >/dev/null 2>&1
}

# Function to check if port 80 is available and handle conflicts
check_port_80() {
    echo "Checking port 80 availability..."

    # Check if something is listening on port 80
    if is_port_80_in_use; then
        echo -e "${YELLOW}Port 80 is already in use${NC}"

        # Try to identify what's using port 80
        local port_80_process=""
        if command -v lsof &> /dev/null; then
            port_80_process=$(lsof -ti:80 2>/dev/null | head -1)
        elif command -v ss &> /dev/null; then
            port_80_process=$(ss -tlnp 2>/dev/null | grep ':80 ' | awk -F'pid=' '{if ($2) {split($2, a, ","); print a[1]}}' | head -1)
        fi

        # Validate PID is numeric
        if [ -n "$port_80_process" ] && ! [[ "$port_80_process" =~ ^[0-9]+$ ]]; then
            port_80_process=""
        fi

        if [ -n "$port_80_process" ]; then
            local process_name=$(ps -p "$port_80_process" -o comm= 2>/dev/null || echo "unknown")
            local process_cmdline=$(ps -p "$port_80_process" -o args= 2>/dev/null || echo "unknown")

            echo "Process using port 80:"
            echo "  PID: $port_80_process"
            echo "  Name: $process_name"
            echo "  Command: $process_cmdline"

            # Check if it's an Apache process
            if [[ "$process_name" == *"apache"* ]] || [[ "$process_name" == *"httpd"* ]]; then
                echo ""
                echo -e "${YELLOW}An Apache process is already running on port 80${NC}"
                echo "This is expected - we will reconfigure Apache for the PBX system."
                echo ""
                return 0
            else
                # Not Apache - could be Nginx or another web server
                echo ""
                echo -e "${YELLOW}Port 80 is in use by a non-Apache process${NC}"
                echo ""

                # Check if it's a known service that we can offer to stop automatically
                local is_systemd_service=false
                local service_name=""

                # Common web servers
                for svc in nginx lighttpd; do
                    if systemctl is-active --quiet "$svc" 2>/dev/null; then
                        is_systemd_service=true
                        service_name="$svc"
                        break
                    fi
                done

                if [ "$is_systemd_service" = true ] && [ -n "$service_name" ]; then
                    echo "Detected $service_name service is running on port 80."
                    echo ""
                    echo "Would you like to stop $service_name to free port 80 for Apache?"
                    echo -e "${YELLOW}Warning: This will stop the $service_name service.${NC}"
                    echo "You can restart it later if needed with: sudo systemctl start $service_name"
                    echo ""
                    read -p "Stop $service_name now? (y/n): " STOP_SERVICE

                    if [ "$STOP_SERVICE" = "y" ] || [ "$STOP_SERVICE" = "Y" ]; then
                        echo "Stopping $service_name..."
                        if systemctl stop "$service_name"; then
                            echo -e "${GREEN}Successfully stopped $service_name${NC}"

                            echo ""
                            read -p "Disable $service_name from starting on boot? (y/n): " DISABLE_SERVICE
                            if [ "$DISABLE_SERVICE" = "y" ] || [ "$DISABLE_SERVICE" = "Y" ]; then
                                systemctl disable "$service_name" 2>/dev/null || true
                                echo -e "${GREEN}$service_name disabled from automatic startup${NC}"
                            fi

                            # Verify port 80 is now free
                            sleep 2
                            if is_port_80_in_use; then
                                echo -e "${RED}Error: Port 80 is still in use after stopping $service_name${NC}"
                                return 1
                            fi

                            echo -e "${GREEN}Port 80 is now available${NC}"
                            return 0
                        else
                            echo -e "${RED}Failed to stop $service_name${NC}"
                            return 1
                        fi
                    else
                        echo "Setup cancelled."
                        return 1
                    fi
                else
                    echo -e "${RED}Error: Port 80 is in use by an unknown process${NC}"
                    echo ""
                    echo "To fix this manually:"
                    echo "  1. Stop the process: sudo kill $port_80_process"
                    echo "  2. Then run this script again"
                    return 1
                fi
            fi
        else
            echo -e "${YELLOW}Could not identify the process using port 80${NC}"
            echo "Please manually check what's using port 80:"
            echo "  sudo lsof -i :80"
            echo "  sudo ss -tlnp | grep :80"
            return 1
        fi
    else
        echo "Port 80 is available"
        return 0
    fi
}

echo "================================================================"
echo "PBX Apache Reverse Proxy Setup Script"
echo "================================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Get domain name
read -p "Enter your domain name (e.g., abps.albl.com): " DOMAIN_NAME

if [ -z "$DOMAIN_NAME" ]; then
    echo -e "${RED}Error: Domain name is required${NC}"
    exit 1
fi

# Get email for Let's Encrypt
read -p "Enter email address for SSL certificate notifications: " EMAIL

if [ -z "$EMAIL" ]; then
    echo -e "${RED}Error: Email address is required${NC}"
    exit 1
fi

# Get PBX backend port
read -p "Enter PBX backend port [default: 8080]: " BACKEND_PORT
BACKEND_PORT=${BACKEND_PORT:-8080}

# Confirm configuration
echo ""
echo -e "${YELLOW}Configuration Summary:${NC}"
echo "  Domain Name: $DOMAIN_NAME"
echo "  Email: $EMAIL"
echo "  Backend Port: $BACKEND_PORT"
echo ""
read -p "Continue with this configuration? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Setup cancelled."
    exit 0
fi

echo ""
echo -e "${GREEN}Starting setup...${NC}"

# Install Apache if not installed
echo "Checking for Apache..."
if ! command -v apache2 &> /dev/null && ! command -v httpd &> /dev/null; then
    echo "Installing Apache..."
    apt update
    apt install -y apache2
else
    echo "Apache is already installed"
fi

# Determine Apache service name (apache2 on Debian/Ubuntu, httpd on RHEL/CentOS)
APACHE_SERVICE="apache2"
if ! systemctl list-unit-files | grep -q apache2; then
    APACHE_SERVICE="httpd"
fi

# Install certbot if not installed
echo "Checking for certbot..."
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    apt install -y certbot python3-certbot-apache
else
    echo "certbot is already installed"
fi

# Check if port 80 is available and handle conflicts
check_port_80 || exit 1

# Enable required Apache modules
echo "Enabling required Apache modules..."
a2enmod proxy proxy_http proxy_wstunnel headers rewrite ssl 2>/dev/null || true

# Create Apache configuration
echo "Creating Apache configuration for $DOMAIN_NAME..."

cat > /etc/apache2/sites-available/pbx.conf << 'EOF'
# HTTP Virtual Host - Redirects to HTTPS
<VirtualHost *:80>
    ServerName DOMAIN_NAME_PLACEHOLDER
    ServerAdmin EMAIL_PLACEHOLDER

    # Redirect all HTTP traffic to HTTPS (will be uncommented after SSL cert is obtained)
    # RewriteEngine On
    # RewriteCond %{HTTPS} off
    # RewriteRule ^(.*)$ https://%{HTTP_HOST}$1 [R=301,L]

    # Allow Let's Encrypt certificate validation
    Alias /.well-known/acme-challenge/ /var/www/html/.well-known/acme-challenge/
    <Directory "/var/www/html/.well-known/acme-challenge/">
        Options None
        AllowOverride None
        Require all granted
    </Directory>

    # Temporarily proxy to PBX (until SSL is configured)
    ProxyPreserveHost On
    ProxyRequests Off
    ProxyTimeout 300

    <Location />
        ProxyPass http://localhost:BACKEND_PORT_PLACEHOLDER/
        ProxyPassReverse http://localhost:BACKEND_PORT_PLACEHOLDER/
        RequestHeader set X-Forwarded-Proto "http"
        RequestHeader set X-Real-IP %{REMOTE_ADDR}s
    </Location>

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/pbx-error.log
    CustomLog ${APACHE_LOG_DIR}/pbx-access.log combined
</VirtualHost>

# HTTPS Virtual Host - Will be auto-configured by certbot
# <VirtualHost *:443>
#     ServerName DOMAIN_NAME_PLACEHOLDER
#     ServerAdmin EMAIL_PLACEHOLDER
#     
#     SSLEngine on
#     # SSL certificates will be added by certbot
#     
#     # Security Headers
#     Header always set X-Frame-Options "DENY"
#     Header always set X-Content-Type-Options "nosniff"
#     Header always set X-XSS-Protection "1; mode=block"
#     Header always set Referrer-Policy "strict-origin-when-cross-origin"
#     
#     ProxyPreserveHost On
#     ProxyRequests Off
#     ProxyTimeout 300
#     
#     <Location />
#         ProxyPass http://localhost:BACKEND_PORT_PLACEHOLDER/
#         ProxyPassReverse http://localhost:BACKEND_PORT_PLACEHOLDER/
#         RequestHeader set X-Forwarded-Proto "https"
#         RequestHeader set X-Real-IP %{REMOTE_ADDR}s
#     </Location>
#     
#     ErrorLog ${APACHE_LOG_DIR}/pbx-ssl-error.log
#     CustomLog ${APACHE_LOG_DIR}/pbx-ssl-access.log combined
# </VirtualHost>
EOF

# Replace placeholders
sed -i "s/DOMAIN_NAME_PLACEHOLDER/$DOMAIN_NAME/g" /etc/apache2/sites-available/pbx.conf
sed -i "s/EMAIL_PLACEHOLDER/$EMAIL/g" /etc/apache2/sites-available/pbx.conf
sed -i "s/BACKEND_PORT_PLACEHOLDER/$BACKEND_PORT/g" /etc/apache2/sites-available/pbx.conf

# Disable default site if it exists
if [ -f /etc/apache2/sites-enabled/000-default.conf ]; then
    echo "Disabling default Apache site..."
    a2dissite 000-default 2>/dev/null || true
fi

# Enable the PBX site
echo "Enabling Apache PBX site..."
a2ensite pbx.conf

# Test Apache configuration
echo "Testing Apache configuration..."
$APACHE_SERVICE -t 2>&1 | tee /tmp/apache_test.log

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo -e "${RED}Apache configuration test failed!${NC}"
    cat /tmp/apache_test.log
    exit 1
fi

# Restart Apache
echo "Restarting Apache..."
systemctl restart $APACHE_SERVICE

# Verify Apache is running
if ! systemctl is-active --quiet $APACHE_SERVICE; then
    echo -e "${RED}Failed to start Apache${NC}"
    echo "Check logs with: sudo journalctl -xeu $APACHE_SERVICE"
    exit 1
fi

echo -e "${GREEN}Apache is running${NC}"

# Get SSL certificate from Let's Encrypt
echo ""
echo "Obtaining SSL certificate from Let's Encrypt..."
echo "Certbot will automatically configure HTTPS..."
echo "This may take a minute..."

# Try to obtain SSL certificate
CERTBOT_SUCCESS=false
certbot --apache -d $DOMAIN_NAME --non-interactive --agree-tos --email $EMAIL --redirect 2>&1 | tee /tmp/certbot_output.log

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    CERTBOT_SUCCESS=true
    echo -e "${GREEN}Successfully obtained SSL certificate!${NC}"
else
    echo -e "${YELLOW}Warning: Failed to obtain SSL certificate${NC}"
    
    # Check for specific error types
    if grep -q "$CERTBOT_OPENSSL_ERROR_PATTERN" /tmp/certbot_output.log; then
        echo ""
        echo -e "${YELLOW}Detected OpenSSL compatibility issue with certbot${NC}"
        echo ""
        echo "To fix the SSL certificate issue, try:"
        echo "  sudo apt update"
        echo "  sudo apt upgrade certbot python3-certbot-apache"
        echo "  sudo certbot --apache -d $DOMAIN_NAME"
    else
        echo ""
        echo "You can try manually with: sudo certbot --apache -d $DOMAIN_NAME"
        echo "Check the certbot logs at: /var/log/letsencrypt/letsencrypt.log"
    fi
    
    echo ""
    echo -e "${YELLOW}Continuing with HTTP-only configuration...${NC}"
    echo "Your site will be accessible via: http://$DOMAIN_NAME"
fi

# Configure firewall (if ufw is available)
if command -v ufw &> /dev/null; then
    echo "Configuring firewall..."
    ufw allow 'Apache Full' 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}================================================================${NC}"
echo ""

# Display appropriate URL based on SSL status
if [ "$CERTBOT_SUCCESS" = true ]; then
    echo "Your PBX admin panel is now accessible at:"
    echo -e "  ${GREEN}https://$DOMAIN_NAME${NC}"
    echo ""
    echo "SSL Certificate:"
    echo "  Status: Active"
    echo "  Auto-renewal: Enabled (every 90 days)"
else
    echo -e "${YELLOW}Your PBX admin panel is accessible via HTTP (no SSL):${NC}"
    echo -e "  ${YELLOW}http://$DOMAIN_NAME${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  SSL Certificate: Not configured${NC}"
    echo -e "${YELLOW}IMPORTANT: Your connection is not encrypted!${NC}"
fi

echo ""
echo "Next Steps:"
echo "  1. Open your browser and go to: http$([ "$CERTBOT_SUCCESS" = true ] && echo "s")://$DOMAIN_NAME"
echo "  2. You should see the PBX admin login page"
echo "  3. Log in with your admin credentials"
echo ""
echo "Logs:"
echo "  Apache access: /var/log/apache2/pbx-access.log"
echo "  Apache error: /var/log/apache2/pbx-error.log"
echo ""
echo -e "${GREEN}Enjoy your PBX system!${NC}"
