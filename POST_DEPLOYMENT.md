# Post-Deployment Guide

**📌 START HERE after running `bash scripts/deploy_production_pilot.sh`**

This guide walks you through the essential next steps after your production pilot deployment completes successfully.

---

## ✅ What Was Just Deployed

The deployment script has configured:
- ✓ PostgreSQL database
- ✓ Python virtual environment
- ✓ Nginx reverse proxy
- ✓ Firewall (UFW)
- ✓ Daily backup system (2 AM)
- ✓ Monitoring (Prometheus)
- ✓ Systemd service (pbx.service)

---

## 🔐 CRITICAL: First Steps (Do These Now)

### 1. Update Database Password

During deployment, a random database password was generated and displayed **once**. If you didn't save it:

```bash
# Generate a new password
NEW_PASSWORD=$(openssl rand -base64 32)
echo "New password: $NEW_PASSWORD"

# Update PostgreSQL
sudo -u postgres psql -c "ALTER USER pbxuser WITH PASSWORD '$NEW_PASSWORD';"
```

**Then update your config.yml:**

```bash
cd /path/to/PBX
nano config.yml
```

Update the database section:
```yaml
database:
  type: postgresql
  host: localhost
  port: 5432
  name: pbx
  user: pbxuser
  password: "YOUR_NEW_PASSWORD_HERE"  # ← Update this
```

### 2. Initialize the Database

```bash
# Activate virtual environment
cd /path/to/PBX
source venv/bin/activate

# Initialize database schema
python scripts/init_database.py

# Seed initial extensions
python scripts/seed_extensions.py

# Verify extensions
python scripts/list_extensions_from_db.py
```

### 3. Configure SSL/TLS Certificate

**For Production (Recommended):**
```bash
# Use Let's Encrypt for free SSL certificate
sudo certbot --nginx -d your-domain.com

# Follow the prompts to configure automatic HTTPS
```

**For Development/Testing:**
```bash
# Generate self-signed certificate
python scripts/generate_ssl_cert.py --hostname your-domain.com
```

### 4. Start the PBX Service

```bash
# Start the service
sudo systemctl start pbx

# Check status
sudo systemctl status pbx

# View live logs
sudo journalctl -u pbx -f
```

---

## 📖 Essential Documentation (Read in Order)

Now that deployment is complete, read these guides in order:

### 1. Configuration (5 minutes)
- **[QUICK_START.md](QUICK_START.md)** - Basic configuration checklist
- **[ENV_SETUP_GUIDE.md](ENV_SETUP_GUIDE.md)** - Environment variables setup

### 2. Extension Setup (10 minutes)
- **[VOICEMAIL_DATABASE_SETUP.md](VOICEMAIL_DATABASE_SETUP.md)** - Database-backed extension management
- Extensions are stored in the database, not in config.yml files

### 3. Voice Prompts (15 minutes - REQUIRED)
Voice files are **NOT** included in the repository. You **MUST** generate them:

```bash
# Install dependencies
pip install gTTS pydub
sudo apt-get install ffmpeg

# Generate voice prompts
python scripts/generate_tts_prompts.py --company "Your Company Name"

# Verify files created
ls -lh auto_attendant/*.wav voicemail_prompts/*.wav
```

See **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** for detailed voice generation options.

### 4. Security Hardening (20 minutes)
- **[SECURITY_GUIDE.md](SECURITY_GUIDE.md)** - Complete security guide
- **[HTTPS_SETUP_GUIDE.md](HTTPS_SETUP_GUIDE.md)** - SSL/TLS configuration

---

## 🔧 Common Configuration Tasks

### Add Extensions

```bash
# Use the API
curl -X POST http://localhost:8080/api/extensions \
  -H "Content-Type: application/json" \
  -d '{"number":"1005","name":"John Doe","email":"john@company.com","password":"securepass123","allow_external":true}'

# Or use the admin panel
# Access at: https://your-domain/admin/
```

### Configure Email for Voicemail

Edit `config.yml`:
```yaml
voicemail:
  email_notifications: true
  smtp:
    host: "smtp.gmail.com"
    port: 587
    use_tls: true
    username: "your-email@gmail.com"
    password: "your-app-password"
  email:
    from_address: "pbx@yourcompany.com"
    from_name: "PBX Voicemail"
```

Restart the service:
```bash
sudo systemctl restart pbx
```

### Configure Phone Provisioning

For auto-configuration of IP phones (Zultys, Yealink, Polycom, etc.):

```bash
# Run provisioning setup
python scripts/setup_phone_provisioning.py

# Verify templates
ls -lh provisioning_templates/
```

See **[PHONE_PROVISIONING.md](PHONE_PROVISIONING.md)** for detailed instructions.

---

## 🔍 Monitoring & Troubleshooting

### Access Monitoring Tools

- **Prometheus**: http://your-domain/prometheus/ or http://localhost:9090
- **Node Exporter**: http://your-domain/metrics or http://localhost:9100/metrics
- **Admin Panel**: https://your-domain/admin/ or https://localhost:8080/admin/

### View Logs

```bash
# System logs
sudo journalctl -u pbx -f

# Deployment log
tail -f /var/log/pbx-deployment.log

# Backup logs
tail -f /var/log/pbx-backup.log

# Application logs
tail -f /path/to/PBX/logs/pbx.log
```

### Check Service Status

```bash
# PBX service
sudo systemctl status pbx

# PostgreSQL
sudo systemctl status postgresql

# Nginx
sudo systemctl status nginx

# Prometheus
sudo systemctl status prometheus
```

### Test Database Connection

```bash
# Connect to database
sudo -u postgres psql -d pbx

# List tables
\dt

# Check extensions
SELECT * FROM extensions;

# Exit
\q
```

---

## 🧪 Testing Your Deployment

### 1. Test PBX Startup

```bash
# Stop service for manual test
sudo systemctl stop pbx

# Run manually to see logs
cd /path/to/PBX
source venv/bin/activate
python main.py

# Look for:
# ✓ SIP server started on 0.0.0.0:5060
# ✓ PBX system started successfully
```

### 2. Test SIP Registration

From a phone or SIP client:
- Server: your-domain or server-ip
- Port: 5060
- Extension: 1001 (or your extension)
- Password: (from database)

### 3. Test Admin Panel

Visit: https://your-domain/admin/
- Check that extensions are listed
- Verify system status
- Test adding/editing extensions

### 4. Test Auto Attendant

1. Call your PBX
2. Dial `0` to access auto attendant
3. Verify voice prompt plays
4. Test menu options (press 1, 2, etc.)

---

## 📚 Optional Documentation (As Needed)

Read these when you need specific features:

### Integrations
- **[FREE_INTEGRATION_OPTIONS.md](FREE_INTEGRATION_OPTIONS.md)** - Free/open-source integrations
- **[ENTERPRISE_INTEGRATIONS.md](ENTERPRISE_INTEGRATIONS.md)** - Zoom, Active Directory, Teams

### Advanced Features
- **[PHONE_BOOK_GUIDE.md](PHONE_BOOK_GUIDE.md)** - Centralized directory
- **[PAGING_SYSTEM_GUIDE.md](PAGING_SYSTEM_GUIDE.md)** - Overhead paging
- **[WEBHOOK_SYSTEM_GUIDE.md](WEBHOOK_SYSTEM_GUIDE.md)** - Event notifications

### Compliance & Security
- **[REGULATIONS_COMPLIANCE_GUIDE.md](REGULATIONS_COMPLIANCE_GUIDE.md)** - E911, STIR/SHAKEN
- **[FIPS_COMPLIANCE_STATUS.md](FIPS_COMPLIANCE_STATUS.md)** - Government compliance

### Troubleshooting
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - General troubleshooting
- **[QOS_TROUBLESHOOTING_ONE_WAY_AUDIO.md](QOS_TROUBLESHOOTING_ONE_WAY_AUDIO.md)** - Audio issues

### Complete Documentation Index
- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - Full documentation catalog

---

## 🚨 Security Checklist

Before going live, complete these security tasks:

- [ ] Change default database password ✅ (done in step 1)
- [ ] Configure SSL/TLS certificate ✅ (done in step 3)
- [ ] Review firewall rules: `sudo ufw status`
- [ ] Enable fail2ban for SSH: `sudo systemctl enable fail2ban`
- [ ] Set up log rotation
- [ ] Review user permissions
- [ ] Test backup restoration: `sudo /usr/local/bin/pbx-backup.sh`
- [ ] Document admin passwords (store securely)
- [ ] Set up monitoring alerts

---

## 💾 Backup Information

### Automatic Backups

The deployment configured daily backups at 2 AM:

```bash
# Backup locations
/var/backups/pbx/db_*.sql.gz      # Database backups
/var/backups/pbx/config_*.tar.gz  # Configuration backups

# Retention: 7 days
```

### Manual Backup

```bash
# Run backup now
sudo /usr/local/bin/pbx-backup.sh

# List backups
ls -lh /var/backups/pbx/
```

### Restore from Backup

```bash
# Find latest backup
ls -lt /var/backups/pbx/db_*.sql.gz | head -1

# Restore database
gunzip -c /var/backups/pbx/db_TIMESTAMP.sql.gz | sudo -u postgres psql pbx

# Restore configuration
sudo tar -xzf /var/backups/pbx/config_TIMESTAMP.tar.gz -C /
```

---

## 🆘 Getting Help

### Check Logs First

Most issues can be diagnosed from logs:
```bash
sudo journalctl -u pbx -n 100 --no-pager
```

### Common Issues

**PBX won't start:**
```bash
# Check for port conflicts
sudo netstat -tulpn | grep -E "5060|8080"

# Check database connection
python scripts/verify_database.py
```

**No audio on calls:**
- Check firewall allows UDP ports 10000-20000
- Verify voice prompts were generated
- See [QOS_TROUBLESHOOTING_ONE_WAY_AUDIO.md](QOS_TROUBLESHOOTING_ONE_WAY_AUDIO.md)

**Phones won't register:**
- Verify extension exists in database
- Check password is correct
- Verify firewall allows UDP port 5060

### Documentation Resources

- **Quick Issues**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Integration Issues**: [INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md)
- **Full Documentation**: [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)

### Support

For issues and questions, open a GitHub issue at:
https://github.com/mattiIce/PBX/issues

---

## ✅ Deployment Complete Checklist

Before considering your deployment complete:

- [ ] Database password updated in config.yml
- [ ] Database initialized and extensions seeded
- [ ] SSL/TLS certificate configured
- [ ] PBX service started successfully
- [ ] Voice prompts generated
- [ ] Admin panel accessible
- [ ] Test extension registered successfully
- [ ] Test call completed successfully
- [ ] Auto attendant tested
- [ ] Voicemail tested
- [ ] Backups tested
- [ ] Monitoring accessible
- [ ] Security checklist completed
- [ ] Documentation reviewed

---

## 🎯 Next Steps

Once everything is working:

1. **Add Your Extensions** - Using admin panel or API
2. **Configure Features** - Voicemail, queues, conferencing
3. **Set Up Integrations** - CRM, Active Directory, etc.
4. **Train Users** - Distribute phone configuration guides
5. **Monitor System** - Check Prometheus for health metrics
6. **Schedule Maintenance** - Plan for updates and backups

**Welcome to your production PBX system! 🎉**
