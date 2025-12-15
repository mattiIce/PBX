# Automated Integration Installation Guide

**Last Updated**: December 15, 2025  
**Purpose**: Guide for automatic installation of Jitsi, Matrix Synapse, and EspoCRM

---

## Overview

The PBX system now includes an automatic installation script that handles:
- ✅ Installation of all required services (Jitsi, Matrix Synapse, EspoCRM)
- ✅ SSL certificate generation for localhost
- ✅ Dependency installation and configuration
- ✅ Database setup (for EspoCRM and Matrix)
- ✅ Basic service configuration

## Quick Start

### One-Command Installation

```bash
# Install all integrations automatically
sudo python3 scripts/install_integrations.py

# Or install specific service
sudo python3 scripts/install_integrations.py --service jitsi
sudo python3 scripts/install_integrations.py --service matrix
sudo python3 scripts/install_integrations.py --service espocrm
```

### Complete Setup Flow

```bash
# Step 1: Install all services
sudo python3 scripts/install_integrations.py

# Step 2: Check installation status
python3 scripts/setup_integrations.py --status

# Step 3: Enable integrations (already configured with local URLs)
python3 scripts/setup_integrations.py --interactive

# Step 4: Create Matrix bot account (if using Matrix)
sudo register_new_matrix_user -c /etc/matrix-synapse/homeserver.yaml http://localhost:8008

# Step 5: Complete EspoCRM setup in browser
# Navigate to: http://localhost/espocrm
# Database: espocrm, User: espocrm_user, Password: (in certs/espocrm_db_password.txt)
# After setup, delete the password file for security
```

## What Gets Installed

### 1. Jitsi Meet
- **Location**: System-wide installation
- **URL**: https://localhost
- **Services**: jitsi-videobridge2, jicofo, prosody
- **SSL**: Self-signed certificate generated automatically

**Verification:**
```bash
sudo systemctl status jitsi-videobridge2
sudo systemctl status jicofo
curl -k https://localhost  # Should return Jitsi page
```

### 2. Matrix Synapse
- **Location**: /etc/matrix-synapse/
- **URL**: https://localhost:8008
- **Service**: matrix-synapse
- **Database**: SQLite (auto-configured)

**Verification:**
```bash
sudo systemctl status matrix-synapse
curl http://localhost:8008/_matrix/client/versions  # Should return JSON
```

**Create Bot Account:**
```bash
sudo register_new_matrix_user -c /etc/matrix-synapse/homeserver.yaml http://localhost:8008
# Follow prompts to create @pbxbot:localhost
# Remember the password for configuration
```

### 3. EspoCRM
- **Location**: /var/www/html/espocrm
- **URL**: http://localhost/espocrm
- **Services**: apache2, mysql-server
- **Database**: espocrm (auto-created)
- **Credentials**: Stored in `/home/runner/work/PBX/PBX/certs/espocrm_db_password.txt`

**Post-Installation Steps:**
1. Navigate to http://localhost/espocrm in browser
2. Complete installation wizard:
   - Database: espocrm
   - Username: espocrm_user
   - Password: (found in certs/espocrm_db_password.txt)
   - Host: localhost
3. Create admin account
4. **Delete password file** after setup: `rm certs/espocrm_db_password.txt`
5. Generate API key:
   - Go to Administration → API Users
   - Create new API User
   - Copy the API key

**Verification:**
```bash
sudo systemctl status apache2
sudo systemctl status mysql
curl http://localhost/espocrm  # Should return HTML
```

### 4. SSL Certificates
- **Location**: /home/runner/work/PBX/PBX/certs/
- **Files**: server.crt, server.key
- **Type**: Self-signed (valid for localhost and 127.0.0.1)
- **Validity**: 365 days

## System Requirements

### Supported Operating Systems
- ✅ Ubuntu 20.04 LTS or later
- ✅ Debian 10 or later
- ⚠️  Other Linux distributions (may work, not tested)

### Minimum Hardware
- **CPU**: 2 cores
- **RAM**: 4 GB (8 GB recommended)
- **Disk**: 10 GB free space
- **Network**: Internet connection (for package downloads)

### Required Permissions
- Must run as root (use `sudo`)
- Package installation permissions
- Service management permissions

## Installation Options

### Full Installation (Recommended)
Installs all three services at once:
```bash
sudo python3 scripts/install_integrations.py
```

### Selective Installation
Install only specific services:
```bash
# Just Jitsi
sudo python3 scripts/install_integrations.py --service jitsi

# Just Matrix
sudo python3 scripts/install_integrations.py --service matrix

# Just EspoCRM
sudo python3 scripts/install_integrations.py --service espocrm
```

### Dry Run
See what would be installed without making changes:
```bash
python3 scripts/install_integrations.py --dry-run
```

### Verbose Mode
Get detailed output during installation:
```bash
sudo python3 scripts/install_integrations.py --verbose
```

## Post-Installation Configuration

### Quick Configure (Admin Panel)

1. **Open Admin Panel**: https://your-pbx-server:8080/admin/
2. **Navigate to Integrations** → Open Source (Free)
3. **Check the box** next to each integration to enable
4. **Result**: Automatically configured with local HTTPS URLs:
   - Jitsi: https://localhost
   - Matrix: https://localhost:8008
   - EspoCRM: https://localhost/api/v1

### Manual Configuration (CLI)

```bash
# Enable all integrations with defaults
python3 scripts/setup_integrations.py --enable jitsi,matrix,espocrm

# Or use interactive wizard
python3 scripts/setup_integrations.py --interactive

# Check status
python3 scripts/setup_integrations.py --status
```

### Environment Variables

Update `.env` file with credentials:

```bash
# For Matrix
MATRIX_BOT_PASSWORD=your-bot-password-from-registration

# For EspoCRM
ESPOCRM_API_KEY=your-api-key-from-espocrm
```

## Troubleshooting

### Installation Fails

**Check Prerequisites:**
```bash
# Verify OS
lsb_release -a

# Check disk space
df -h

# Check permissions
whoami  # Should be root or use sudo
```

**Common Issues:**

1. **"Command not found" errors**
   - Solution: Install missing packages manually
   ```bash
   sudo apt-get update
   sudo apt-get install -y curl wget gnupg
   ```

2. **Repository errors**
   - Solution: Update package lists
   ```bash
   sudo apt-get update
   sudo apt-get upgrade
   ```

3. **Port conflicts**
   - Solution: Check if ports are already in use
   ```bash
   sudo netstat -tulpn | grep -E ':(80|443|8008|10000)'
   ```

### Service Not Starting

**Jitsi:**
```bash
sudo systemctl status jitsi-videobridge2
sudo journalctl -xeu jitsi-videobridge2

# Restart services
sudo systemctl restart jitsi-videobridge2
sudo systemctl restart jicofo
sudo systemctl restart prosody
```

**Matrix:**
```bash
sudo systemctl status matrix-synapse
sudo journalctl -xeu matrix-synapse

# Check configuration
sudo -u matrix-synapse python3 -m synapse.app.homeserver -c /etc/matrix-synapse/homeserver.yaml --generate-keys

# Restart service
sudo systemctl restart matrix-synapse
```

**EspoCRM:**
```bash
sudo systemctl status apache2
sudo systemctl status mysql

# Check Apache error logs
sudo tail -f /var/log/apache2/espocrm_error.log

# Restart services
sudo systemctl restart apache2
sudo systemctl restart mysql
```

### SSL Certificate Issues

**Regenerate Certificates:**
```bash
cd /home/runner/work/PBX/PBX
rm -rf certs/
sudo python3 scripts/install_integrations.py --service ssl
```

**Trust Self-Signed Certificates:**
For development/testing, you may need to accept self-signed certificates in your browser.

### Connection Refused Errors

**Check Service Status:**
```bash
sudo systemctl is-active jitsi-videobridge2
sudo systemctl is-active matrix-synapse
sudo systemctl is-active apache2
```

**Check Firewall:**
```bash
sudo ufw status
# If firewall is active, allow necessary ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8008/tcp
```

## Uninstallation

To remove installed services:

### Remove Jitsi
```bash
sudo apt-get purge jitsi-meet jitsi-videobridge2 jicofo
sudo apt-get autoremove
```

### Remove Matrix Synapse
```bash
sudo apt-get purge matrix-synapse-py3
sudo rm -rf /etc/matrix-synapse
```

### Remove EspoCRM
```bash
sudo rm -rf /var/www/html/espocrm
sudo a2dissite espocrm
sudo systemctl reload apache2
# Optionally remove database
mysql -u root -e "DROP DATABASE espocrm; DROP USER 'espocrm_user'@'localhost';"
```

## Security Considerations

### Self-Signed Certificates
- ⚠️  Self-signed certificates are for development/testing only
- ✅ For production, use proper SSL certificates from Let's Encrypt or a trusted CA

### Default Credentials
- ⚠️  EspoCRM database password is randomly generated and stored in `certs/espocrm_db_password.txt`
- ⚠️  Delete the password file after completing EspoCRM setup
- ⚠️  Create strong Matrix bot password during account creation
- ✅ Store credentials securely in `.env` file

### Firewall Configuration
```bash
# For local-only access (recommended for testing)
sudo ufw deny 8008/tcp  # Block external Matrix access
sudo ufw deny 80/tcp    # Block external HTTP
sudo ufw deny 443/tcp   # Block external HTTPS

# For network access (production)
sudo ufw allow from 192.168.1.0/24 to any port 8008  # Allow LAN
```

## Advanced Configuration

### Custom SSL Certificates

Replace auto-generated certificates with your own:
```bash
# Copy your certificates
sudo cp your-cert.crt /home/runner/work/PBX/PBX/certs/server.crt
sudo cp your-key.key /home/runner/work/PBX/PBX/certs/server.key

# Update Jitsi configuration
sudo cp your-cert.crt /etc/jitsi/meet/localhost.crt
sudo cp your-key.key /etc/jitsi/meet/localhost.key
sudo systemctl restart jitsi-videobridge2
```

### Network Access

To access from other machines on your network:

1. **Find your IP address:**
   ```bash
   ip addr show | grep "inet 192"
   ```

2. **Update integration URLs:**
   - Instead of `https://localhost`, use `https://192.168.1.X`
   - Configure through Admin Panel or config.yml

3. **Update firewall:**
   ```bash
   sudo ufw allow from 192.168.1.0/24
   ```

## Support

- **Installation Issues**: See [INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md)
- **Configuration Help**: See [QUICK_SETUP_GUIDE.md](QUICK_SETUP_GUIDE.md)
- **SSL Setup**: See [HTTPS_SETUP_GUIDE.md](HTTPS_SETUP_GUIDE.md)
- **General Guide**: See [OPEN_SOURCE_INTEGRATIONS.md](OPEN_SOURCE_INTEGRATIONS.md)

---

**Status**: ✅ Production Ready  
**Last Tested**: December 15, 2025
