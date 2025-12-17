#!/bin/bash
# Setup Nginx Reverse Proxy for PBX System
# This script automates the configuration of nginx for accessing PBX via a domain name

set -e

# Cleanup temporary files on exit
trap 'rm -f /tmp/nginx_test.log' EXIT

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================================"
echo "PBX Reverse Proxy Setup Script"
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

# Install nginx if not installed
echo "Checking for nginx..."
if ! command -v nginx &> /dev/null; then
    echo "Installing nginx..."
    apt update
    apt install -y nginx
else
    echo "nginx is already installed"
fi

# Install certbot if not installed
echo "Checking for certbot..."
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    apt install -y certbot python3-certbot-nginx
else
    echo "certbot is already installed"
fi

# Create nginx configuration
echo "Creating nginx configuration for $DOMAIN_NAME..."

# First, add rate limiting zone to nginx.conf if not already present
if ! grep -q "limit_req_zone.*api_limit" /etc/nginx/nginx.conf; then
    echo "Adding rate limiting zone to nginx.conf..."
    sed -i '/http {/a \    # Rate limiting zone for PBX API\n    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;' /etc/nginx/nginx.conf
fi

# Create initial HTTP-only configuration (certbot will add HTTPS later)
cat > /etc/nginx/sites-available/$DOMAIN_NAME << EOF
# HTTP configuration - certbot will configure HTTPS
server {
    listen 80;
    server_name $DOMAIN_NAME;
    
    # Allow certbot to verify domain ownership
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Logging
    access_log /var/log/nginx/${DOMAIN_NAME}-access.log;
    error_log /var/log/nginx/${DOMAIN_NAME}-error.log;

    # Proxy to PBX backend
    location / {
        proxy_pass http://localhost:$BACKEND_PORT;
        proxy_http_version 1.1;
        
        # WebSocket support (for WebRTC phone)
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Forward original request information
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts for long-running connections
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
    
    # API endpoint with rate limiting
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://localhost:$BACKEND_PORT/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable the site
echo "Enabling nginx site..."
ln -sf /etc/nginx/sites-available/$DOMAIN_NAME /etc/nginx/sites-enabled/

# Test nginx configuration
echo "Testing nginx configuration..."
nginx -t 2>&1 | tee /tmp/nginx_test.log

# Check for critical errors (ignore warnings about duplicate MIME types from other configs)
if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo -e "${RED}Nginx configuration test failed!${NC}"
    exit 1
fi

# Inform user about non-critical warnings
if grep -q "duplicate.*MIME type\|duplicate extension" /tmp/nginx_test.log; then
    echo -e "${YELLOW}Note: Warnings about duplicate MIME types from other nginx configs can be safely ignored.${NC}"
fi

# Start or reload nginx to serve HTTP traffic
echo "Starting/reloading nginx..."

# Check nginx service state
NGINX_STATE=$(systemctl is-active nginx 2>/dev/null || echo "inactive")

if [ "$NGINX_STATE" = "active" ]; then
    # Nginx is running, reload configuration
    echo "Nginx is active, reloading configuration..."
    if ! systemctl reload nginx; then
        echo -e "${RED}Failed to reload nginx${NC}"
        echo "Attempting to restart nginx instead..."
        systemctl restart nginx || {
            echo -e "${RED}Failed to restart nginx. Check 'journalctl -xeu nginx.service' for details.${NC}"
            exit 1
        }
    fi
else
    # Nginx is not active (could be inactive, failed, or not loaded)
    echo "Nginx is not active (state: $NGINX_STATE), starting service..."
    
    # If nginx is in a failed state, reset it first
    if systemctl is-failed --quiet nginx 2>/dev/null; then
        echo "Resetting failed nginx service..."
        systemctl reset-failed nginx
    fi
    
    # Start nginx
    if ! systemctl start nginx; then
        echo -e "${RED}Failed to start nginx${NC}"
        echo "Checking for detailed error information..."
        journalctl -xeu nginx.service --no-pager -n 50
        exit 1
    fi
    
    # Enable nginx to start on boot
    systemctl enable nginx
fi

# Get SSL certificate from Let's Encrypt
echo ""
echo "Obtaining SSL certificate from Let's Encrypt..."
echo "Certbot will automatically configure HTTPS and add redirect from HTTP..."
echo "This may take a minute..."

certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email $EMAIL --redirect

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to obtain SSL certificate${NC}"
    echo "You can try manually with: sudo certbot --nginx -d $DOMAIN_NAME"
    exit 1
fi

# Configure firewall (if ufw is available)
if command -v ufw &> /dev/null; then
    echo "Configuring firewall..."
    ufw allow 'Nginx Full' 2>/dev/null || true
fi

# Final nginx reload
echo "Final nginx reload..."

# Check nginx service state
NGINX_STATE=$(systemctl is-active nginx 2>/dev/null || echo "inactive")

if [ "$NGINX_STATE" = "active" ]; then
    # Nginx is running, reload configuration
    if ! systemctl reload nginx; then
        echo -e "${RED}Failed to reload nginx${NC}"
        echo "Attempting to restart nginx instead..."
        systemctl restart nginx || {
            echo -e "${RED}Failed to restart nginx. Check 'journalctl -xeu nginx.service' for details.${NC}"
            exit 1
        }
    fi
else
    # Nginx is not active (could be inactive, failed, or not loaded)
    echo "Nginx is not active (state: $NGINX_STATE), starting service..."
    
    # If nginx is in a failed state, reset it first
    if systemctl is-failed --quiet nginx 2>/dev/null; then
        echo "Resetting failed nginx service..."
        systemctl reset-failed nginx
    fi
    
    # Start nginx
    if ! systemctl start nginx; then
        echo -e "${RED}Failed to start nginx${NC}"
        echo "Checking for detailed error information..."
        journalctl -xeu nginx.service --no-pager -n 50
        exit 1
    fi
    
    # Enable nginx to start on boot
    systemctl enable nginx
fi

echo ""
echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}================================================================${NC}"
echo ""
echo "Your PBX admin panel is now accessible at:"
echo -e "  ${GREEN}https://$DOMAIN_NAME${NC}"
echo ""
echo "SSL Certificate:"
echo "  Status: Active"
echo "  Auto-renewal: Enabled (every 90 days)"
echo ""
echo "Next Steps:"
echo "  1. Open your browser and go to: https://$DOMAIN_NAME"
echo "  2. You should see the PBX admin login page"
echo "  3. Log in with your admin credentials"
echo ""
echo "Logs:"
echo "  Nginx access: /var/log/nginx/${DOMAIN_NAME}-access.log"
echo "  Nginx error: /var/log/nginx/${DOMAIN_NAME}-error.log"
echo "  PBX: [PBX_INSTALL_DIR]/logs/pbx.log"
echo ""
echo "SSL Certificate Management:"
echo "  Check status: sudo certbot certificates"
echo "  Renew manually: sudo certbot renew"
echo "  Test renewal: sudo certbot renew --dry-run"
echo ""
echo -e "${GREEN}Enjoy your PBX system!${NC}"

