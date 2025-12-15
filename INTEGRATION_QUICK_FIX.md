# Integration Quick Fix Guide

**🚨 Fast Solutions for Common Integration Problems**

---

## 🎯 Which Problem Do You Have?

### 1. Jitsi: "I installed Jitsi but it's not working with PBX"

**Quick Fix:**

```bash
# Edit PBX config
nano /home/runner/work/PBX/PBX/config.yml

# Find this section (around line 431) and change:
integrations:
  jitsi:
    enabled: true  # Change from false to true
    server_url: https://YOUR-JITSI-SERVER-URL-HERE  # Your Jitsi URL

# Save and restart PBX
sudo systemctl restart pbx
```

**OR use the Admin Web UI:**
1. Go to `http://your-pbx:8080/admin/`
2. Click "Integrations" → "Jitsi (Video)"
3. Enable and enter your Jitsi server URL
4. Click "Save"

**Full guide:** [INTEGRATION_TROUBLESHOOTING_GUIDE.md - Jitsi Section](INTEGRATION_TROUBLESHOOTING_GUIDE.md#jitsi-self-hosted-integration-complete-guide)

---

### 2. Matrix: "pip3 install worked but python3 command doesn't work"

**The Problem:** The docs show a confusing command that tries to generate config AND run the server at the same time.

**Quick Fix - Do this instead:**

```bash
# Step 1: Generate config ONLY (this is the correct way)
mkdir -p ~/matrix-synapse
cd ~/matrix-synapse
python3 -m synapse.app.homeserver \
  --server-name localhost \
  --config-path homeserver.yaml \
  --generate-config \
  --report-stats=no

# Step 2: NOW start the server (separate command)
python3 -m synapse.app.homeserver --config-path homeserver.yaml
```

**That's it!** The server should now be running on http://localhost:8008

**To run in background:**
```bash
nohup python3 -m synapse.app.homeserver --config-path homeserver.yaml > synapse.log 2>&1 &
```

**Full guide:** [INTEGRATION_TROUBLESHOOTING_GUIDE.md - Matrix Section](INTEGRATION_TROUBLESHOOTING_GUIDE.md#matrix-synapse-proper-startup)

---

### 3. EspoCRM: "Getting 404 Not Found errors"

**The Problem:** EspoCRM is not installed. The documentation shows installation commands but EspoCRM requires a full web installation.

**Quick Fix:**

```bash
# 1. Install prerequisites
sudo apt-get install -y apache2 mysql-server php php-mysql php-curl \
  php-gd php-mbstring php-xml php-zip php-intl unzip

# 2. Download and install
cd /tmp
wget https://www.espocrm.com/downloads/EspoCRM-8.1.3.zip
sudo unzip EspoCRM-8.1.3.zip -d /var/www/espocrm
sudo chown -R www-data:www-data /var/www/espocrm

# 3. Configure Apache
sudo nano /etc/apache2/sites-available/espocrm.conf
```

Add this content:
```apache
<VirtualHost *:80>
    DocumentRoot /var/www/espocrm
    <Directory /var/www/espocrm>
        AllowOverride All
        Require all granted
    </Directory>
</VirtualHost>
```

```bash
# 4. Enable and restart
sudo a2enmod rewrite
sudo a2ensite espocrm
sudo systemctl restart apache2

# 5. Complete installation via web browser
# Go to: http://your-server-ip
# Follow the installation wizard
```

**After web installation is complete**, then configure PBX integration.

**Full guide:** [INTEGRATION_TROUBLESHOOTING_GUIDE.md - EspoCRM Section](INTEGRATION_TROUBLESHOOTING_GUIDE.md#espocrm-installation-and-setup)

---

## ✅ Verify Everything is Working

### Test Jitsi
```bash
# Your Jitsi server should respond
curl https://your-jitsi-server
```

### Test Matrix
```bash
# Should return version info (not an error)
curl http://localhost:8008/_matrix/client/versions
```

### Test EspoCRM
```bash
# Should return HTML or redirect (not 404)
curl http://localhost/
```

---

## 📚 Need More Help?

- **Detailed troubleshooting:** [INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md)
- **Complete integration docs:** [OPEN_SOURCE_INTEGRATIONS.md](OPEN_SOURCE_INTEGRATIONS.md)
- **Implementation summary:** [OPENSOURCE_INTEGRATIONS_SUMMARY.md](OPENSOURCE_INTEGRATIONS_SUMMARY.md)

---

**Last Updated:** December 15, 2025
