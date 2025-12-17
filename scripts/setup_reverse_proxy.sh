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

# Helper function to check if port 80 is in use
is_port_80_in_use() {
    netstat -tuln 2>/dev/null | grep -q ':80 ' || ss -tuln 2>/dev/null | grep -q ':80 '
}

# Helper function to check if nginx processes are running
has_nginx_processes() {
    pgrep nginx >/dev/null 2>&1
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
            # Use awk instead of grep -oP for better compatibility
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
            
            # Check if it's an nginx process
            if [[ "$process_name" == *"nginx"* ]]; then
                echo ""
                echo -e "${YELLOW}An nginx process is already running on port 80${NC}"
                
                # Check if nginx service thinks it's running
                local nginx_service_state=$(systemctl is-active nginx 2>/dev/null || echo "inactive")
                
                if [ "$nginx_service_state" = "active" ]; then
                    echo "Nginx service is active and healthy."
                    echo "This is normal - nginx will reload the new configuration."
                    return 0
                else
                    echo -e "${YELLOW}Warning: Nginx process exists but service state is: $nginx_service_state${NC}"
                    echo "This suggests a stale nginx process. Attempting to clean up..."
                    
                    # Try to stop all nginx processes
                    echo "Stopping stale nginx processes..."
                    systemctl stop nginx 2>/dev/null || true
                    
                    # Wait a moment for processes to stop
                    sleep 2
                    
                    # If nginx processes still exist, force kill them
                    if has_nginx_processes; then
                        echo "Force killing remaining nginx processes..."
                        pkill -9 nginx 2>/dev/null || true
                        sleep 1
                    fi
                    
                    # Verify port 80 is now free
                    if is_port_80_in_use; then
                        echo -e "${RED}Error: Unable to free port 80 even after stopping nginx${NC}"
                        echo "Please manually investigate and stop the process using port 80"
                        return 1
                    fi
                    
                    echo -e "${GREEN}Successfully cleaned up stale nginx processes${NC}"
                    return 0
                fi
            else
                # Not nginx - could be Apache, another web server, or something else
                echo ""
                echo -e "${YELLOW}Port 80 is in use by a non-nginx process${NC}"
                echo ""
                
                # Check if it's a known service that we can offer to stop automatically
                local is_systemd_service=false
                local service_name=""
                
                # Common web servers that might be running as services
                for svc in apache2 httpd lighttpd; do
                    if systemctl is-active --quiet "$svc" 2>/dev/null; then
                        is_systemd_service=true
                        service_name="$svc"
                        break
                    fi
                done
                
                if [ "$is_systemd_service" = true ] && [ -n "$service_name" ]; then
                    echo "Detected $service_name service is running on port 80."
                    echo ""
                    echo "Would you like to automatically stop $service_name to free port 80?"
                    echo -e "${YELLOW}Warning: This will stop the $service_name service.${NC}"
                    echo "You can restart it later if needed with: sudo systemctl start $service_name"
                    echo ""
                    read -p "Stop $service_name now? (y/n): " STOP_SERVICE
                    
                    if [ "$STOP_SERVICE" = "y" ] || [ "$STOP_SERVICE" = "Y" ]; then
                        echo "Stopping $service_name..."
                        if systemctl stop "$service_name"; then
                            echo -e "${GREEN}Successfully stopped $service_name${NC}"
                            
                            # Optionally disable the service from starting on boot
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
                                echo "Please check what else might be using port 80"
                                return 1
                            fi
                            
                            echo -e "${GREEN}Port 80 is now available${NC}"
                            return 0
                        else
                            echo -e "${RED}Failed to stop $service_name${NC}"
                            return 1
                        fi
                    else
                        echo ""
                        echo "Setup cancelled. To fix this manually, you need to:"
                        echo "  1. Stop the process using port 80:"
                        echo "     sudo systemctl stop $service_name"
                        echo ""
                        echo "  2. Or, configure that service to use a different port"
                        echo "  3. Then run this script again"
                        return 1
                    fi
                else
                    # Unknown service or not a systemd service
                    echo -e "${RED}Error: Port 80 is in use by a non-nginx process${NC}"
                    echo ""
                    echo "To fix this, you need to:"
                    echo "  1. Stop the process using port 80:"
                    echo "     sudo systemctl stop $process_name  (if it's a service)"
                    echo "     or"
                    echo "     sudo kill $port_80_process  (to stop the specific process)"
                    echo ""
                    echo "  2. Or, configure that service to use a different port"
                    echo "  3. Then run this script again"
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

# Function to manage nginx service (start/reload)
manage_nginx_service() {
    local action_description="${1:-Starting/reloading}"
    
    echo "$action_description nginx..."
    
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
                return 1
            }
        fi
    else
        # Nginx is not active (could be inactive, failed, or not loaded)
        echo "Nginx is not active (state: $NGINX_STATE), starting service..."
        
        # Check if there are any stale nginx processes running
        if has_nginx_processes; then
            echo -e "${YELLOW}Warning: Found nginx processes running but service state is $NGINX_STATE${NC}"
            echo "Cleaning up stale nginx processes..."
            
            # Try graceful stop first
            systemctl stop nginx 2>/dev/null || true
            sleep 2
            
            # If processes still exist, force kill them
            if has_nginx_processes; then
                echo "Nginx processes still running, force terminating..."
                pkill -9 nginx 2>/dev/null || true
                sleep 1
            fi
            
            # Verify processes are gone
            if has_nginx_processes; then
                echo -e "${RED}Error: Unable to stop nginx processes${NC}"
                echo "Please manually kill nginx processes and try again"
                return 1
            fi
            echo -e "${GREEN}Stale nginx processes cleaned up${NC}"
        fi
        
        # If nginx is in a failed state, reset it first
        if systemctl is-failed --quiet nginx; then
            echo "Resetting failed nginx service..."
            systemctl reset-failed nginx
        fi
        
        # Start nginx
        if ! systemctl start nginx; then
            echo -e "${RED}Failed to start nginx${NC}"
            echo "Checking for detailed error information..."
            journalctl -xeu nginx.service --no-pager -n 50
            return 1
        fi
        
        # Enable nginx to start on boot
        systemctl enable nginx
    fi
    
    return 0
}

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

# Check if port 80 is available and handle conflicts
check_port_80 || exit 1

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
manage_nginx_service "Starting/reloading" || exit 1

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
manage_nginx_service "Final nginx reload" || exit 1

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

