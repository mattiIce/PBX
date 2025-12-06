# Environment Variable Setup Guide

## Quick Start

### Where is the .env file?

The `.env` file is located in the **root directory** of the PBX project.

If your PBX project is installed at `/path/to/your/pbx/project`, then the `.env` file would be at:

```
/path/to/your/pbx/project/.env
```

Or if you're in the project directory, it's simply:

```
.env
```

**Important**: This file does NOT exist by default. You need to create it using one of the methods below.

## Method 1: Interactive Setup Script (Recommended)

Use the interactive setup script to create and update your `.env` file:

```bash
python scripts/setup_env.py
```

### What the script does:

1. **Detects existing .env file** - Shows current values if file exists
2. **Guides you through each variable** - Clear descriptions and examples
3. **Protects sensitive data** - Masks passwords when displaying
4. **Creates .env file** - Saves everything in the correct format
5. **Validates required fields** - Ensures you don't miss critical settings

### Setup Options:

- **Full setup**: Configure all environment variables (database, AD, SMTP, integrations)
- **Quick setup**: Configure only required variables (mainly AD password)
- **Update specific**: Update only selected variables
- **Update all**: Review and update all variables

### Example Session:

```
$ python scripts/setup_env.py

======================================================================
PBX System - Environment Variable Setup
======================================================================

This script will help you set up the .env file with your credentials.
The .env file location: .env (in the project root directory)

ℹ No existing .env file found. Will create new one at: .env

Options:
  1. Full setup (all variables)
  2. Quick setup (only required variables)
  3. Cancel

Choose an option (1-3): 2

======================================================================
Active Directory Configuration
======================================================================

AD_BIND_PASSWORD
  Description: Active Directory bind password
  Note: Password for the AD service account (bind_dn) configured in config.yml
  Example: YourADPassword
  New value [REQUIRED]: MyPassword123!

======================================================================
Summary
======================================================================

The following variables will be saved to: .env

Active Directory Configuration:
  AD_BIND_PASSWORD: ********

Save these settings? (yes/no): yes

✓ Environment variables saved to: .env

Next steps:
  1. The .env file is now ready to use
  2. Start the PBX system: python main.py
  3. Or sync AD users: python scripts/sync_ad_users.py
```

## Method 2: Manual Setup

### Step 1: Copy the example file

```bash
cp .env.example .env
```

### Step 2: Edit the .env file

```bash
nano .env
# or
vim .env
# or use any text editor
```

### Step 3: Set required values

At minimum, you need to set:

```bash
# Active Directory (Required for AD sync)
AD_BIND_PASSWORD=YourActualPassword
```

### Step 4: Optional - Set other values

```bash
# Database (if using PostgreSQL)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pbx_system
DB_USER=pbx_user
DB_PASSWORD=YourDatabasePassword

# SMTP (for voicemail emails)
SMTP_HOST=smtp.yourserver.com
SMTP_PORT=587
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password

# Zoom Integration (optional)
ZOOM_CLIENT_ID=your-zoom-client-id
ZOOM_CLIENT_SECRET=your-zoom-client-secret

# Microsoft Outlook/Teams Integration (optional)
OUTLOOK_CLIENT_ID=your-outlook-client-id
OUTLOOK_CLIENT_SECRET=your-outlook-client-secret
TEAMS_CLIENT_ID=your-teams-client-id
TEAMS_CLIENT_SECRET=your-teams-client-secret
```

## Method 3: Direct Command Line

Create the .env file directly from the command line:

```bash
# Create .env file with AD password
cat > .env << 'EOF'
# Active Directory Configuration
AD_BIND_PASSWORD=YourActualPassword
EOF
```

## Verifying Your Setup

### Check if .env file exists:

```bash
ls -la .env
```

### View .env file contents (be careful - contains passwords):

```bash
cat .env
```

### Test that environment variables are loaded:

```bash
# Run a sync to test AD connection
python scripts/sync_ad_users.py
```

If the connection succeeds, your credentials are working!

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AD_BIND_PASSWORD` | Active Directory bind password | `MyPassword123!` |

### Database Variables (Optional - only needed for PostgreSQL)

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |
| `DB_NAME` | Database name | `pbx_system` |
| `DB_USER` | Database user | `pbx_user` |
| `DB_PASSWORD` | Database password | (none) |

**Note**: If using SQLite (default), you don't need database variables.

### SMTP Variables (Optional - for voicemail emails)

| Variable | Description | Example |
|----------|-------------|---------|
| `SMTP_HOST` | SMTP server | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` or `465` |
| `SMTP_USERNAME` | SMTP username | `user@company.com` |
| `SMTP_PASSWORD` | SMTP password | `your-password` |

### Integration Variables (Optional)

| Variable | Description |
|----------|-------------|
| `ZOOM_CLIENT_ID` | Zoom API client ID |
| `ZOOM_CLIENT_SECRET` | Zoom API client secret |
| `OUTLOOK_CLIENT_ID` | Outlook API client ID |
| `OUTLOOK_CLIENT_SECRET` | Outlook API client secret |
| `TEAMS_CLIENT_ID` | Teams API client ID |
| `TEAMS_CLIENT_SECRET` | Teams API client secret |

## How It Works

### 1. File Loading

When the PBX system starts, it automatically:
- Looks for `.env` file in the project root
- Loads all variables into the environment
- Makes them available to the system

### 2. Variable Substitution

The `config.yml` file uses special syntax to reference environment variables:

```yaml
bind_password: ${AD_BIND_PASSWORD}
```

This gets replaced with the actual value from your `.env` file.

### 3. Security

- ✅ `.env` file is automatically ignored by Git (listed in `.gitignore`)
- ✅ Passwords are never committed to version control
- ✅ Each environment can have different values
- ✅ Safe to have different passwords for dev/staging/production

## Troubleshooting

### Problem: "Active Directory credentials not configured properly"

**Solution**: Make sure you've set `AD_BIND_PASSWORD` in the `.env` file:

```bash
# Run the setup script
python scripts/setup_env.py

# Or create .env manually
echo "AD_BIND_PASSWORD=YourPassword" > .env
```

### Problem: "Environment variable AD_BIND_PASSWORD not found"

**Solution**: The `.env` file doesn't exist or the variable isn't set. Run:

```bash
python scripts/setup_env.py
```

### Problem: ".env file not found"

**Solution**: You're probably in the wrong directory. Navigate to the project root:

```bash
cd /path/to/your/pbx/project
# For example: cd /opt/pbx or cd ~/PBX

# Then run setup
python scripts/setup_env.py
```

### Problem: "Permission denied"

**Solution**: Make sure the script is executable:

```bash
chmod +x scripts/setup_env.py
python scripts/setup_env.py
```

### Problem: Changes not taking effect

**Solution**: After updating `.env`, restart the PBX system:

```bash
# Stop the PBX (Ctrl+C if running)
# Then start again
python main.py
```

## Best Practices

1. **Never commit .env file** - It's already in `.gitignore`, don't remove it
2. **Use strong passwords** - Especially for AD and database credentials
3. **Backup your .env file** - Store it securely (password manager, encrypted storage)
4. **Different passwords per environment** - Don't reuse production passwords in dev
5. **Rotate credentials regularly** - Update passwords periodically
6. **Restrict file permissions** - On Linux/Mac: `chmod 600 .env`

## Quick Reference Commands

```bash
# Create/update .env file interactively
python scripts/setup_env.py

# Quick setup (only required variables)
python scripts/setup_env.py  # then choose option 2

# Check if .env exists
ls -la .env

# Create from example
cp .env.example .env

# Edit manually
nano .env

# Test AD connection
python scripts/sync_ad_users.py

# View current environment variables (without exposing values)
python -c "from pbx.utils.env_loader import get_env_loader; loader = get_env_loader(); print('Loaded:', loader.get_loaded_vars())"
```

## Related Documentation

- [AD_USER_SYNC_GUIDE.md](AD_USER_SYNC_GUIDE.md) - Active Directory sync setup
- [QUICK_START.md](QUICK_START.md) - General setup guide
- [SECURITY.md](SECURITY.md) - Security best practices

## Support

If you're still having issues:

1. Check the logs: `logs/pbx.log`
2. Run sync with verbose flag: `python scripts/sync_ad_users.py --verbose`
3. Verify AD credentials are correct in Active Directory
4. Review this guide and the AD sync guide
