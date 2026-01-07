# Warden VoIP PBX - Ubuntu Setup Guide

This guide explains how to use the interactive setup wizard to install the Warden VoIP PBX system on Ubuntu.

## Quick Start

The easiest way to install the Warden VoIP PBX system on Ubuntu is to use the interactive setup wizard:

```bash
sudo python3 setup_ubuntu.py
```

That's it! The wizard will guide you through the entire installation process.

## What the Setup Wizard Does

The interactive setup wizard automates the following tasks:

1. **System Checks**
   - Verifies Ubuntu version (24.04 LTS recommended)
   - Checks Python version (3.12+ required)
   - Verifies root/sudo access

2. **System Dependencies**
   - Installs `espeak` (Text-to-speech engine)
   - Installs `ffmpeg` (Audio/video processing)
   - Installs `libopus-dev` (Opus codec library)
   - Installs `portaudio19-dev` (Audio I/O library)
   - Installs `libspeex-dev` (Speex codec library)
   - Installs `postgresql` (Database server)
   - Installs Python virtual environment tools

3. **Python Environment**
   - Creates a Python virtual environment
   - Installs all required Python packages
   - Upgrades pip to the latest version

4. **PostgreSQL Database**
   - Starts PostgreSQL service
   - Creates database user
   - Creates PBX database
   - Grants necessary privileges

5. **Configuration**
   - Creates `.env` file with database credentials
   - Sets up environment variables
   - Configures database connection

6. **Database Schema**
   - Initializes database tables
   - Creates required schema

7. **SSL Certificate**
   - Generates self-signed SSL certificate
   - Configures HTTPS for the admin interface

8. **Voice Prompts**
   - Generates voice prompts for voicemail
   - Generates voice prompts for auto-attendant
   - Uses text-to-speech (TTS) engine

9. **Verification**
   - Verifies all components are installed
   - Checks that services are running
   - Validates the setup

## Prerequisites

### Operating System

- **Recommended**: Ubuntu 24.04 LTS
- **Supported**: Ubuntu 22.04 LTS and newer
- **Not Recommended**: Other Linux distributions (untested)

### System Requirements

- **CPU**: 2+ cores recommended
- **RAM**: 4+ GB recommended
- **Disk**: 20+ GB free space recommended
- **Network**: Internet connection for downloading packages

### Software Requirements

- **Python**: 3.12 or newer
- **Root Access**: sudo or root privileges required

## Installation Steps

### Step 1: Download the Repository

If you haven't already, clone the repository:

```bash
git clone https://github.com/mattiIce/PBX.git
cd PBX
```

### Step 2: Run the Setup Wizard

Execute the setup script with sudo:

```bash
sudo python3 setup_ubuntu.py
```

### Step 3: Follow the Interactive Prompts

The wizard will ask you several questions:

1. **Database Name**: Name for the PBX database (default: `pbx_system`)
2. **Database User**: PostgreSQL username (default: `pbx_user`)
3. **Database Password**: Password for the database user (required)
4. **Hostname**: Hostname or IP address for SSL certificate (default: system hostname)
5. **Voice Prompts**: Whether to generate voice prompts now (recommended: yes)

### Step 4: Wait for Installation

The wizard will:
- Download and install packages
- Set up the Python environment
- Configure the database
- Generate certificates and voice prompts

This typically takes 5-15 minutes depending on your system and internet connection.

### Step 5: Review the Results

After installation, the wizard will display:
- Setup verification results
- Any warnings or errors encountered
- Next steps for using the system

## After Installation

### Starting the PBX Server

To start the PBX server manually:

```bash
# Activate the virtual environment
source venv/bin/activate

# Start the server
python main.py
```

### Installing as a System Service

For production use, install as a systemd service:

```bash
# Copy the service file
sudo cp pbx.service /etc/systemd/system/

# Edit the service file to set the correct paths
sudo nano /etc/systemd/system/pbx.service

# Enable and start the service
sudo systemctl enable pbx
sudo systemctl start pbx

# Check the status
sudo systemctl status pbx
```

### Accessing the Admin Interface

Open your web browser and navigate to:

```
https://localhost:8080
```

or

```
https://YOUR_SERVER_IP:8080
```

**Note**: You'll need to accept the self-signed SSL certificate warning in your browser.

## Configuration

### Editing Configuration Files

After installation, you may want to customize:

1. **config.yml**: Main PBX configuration
   - Extensions
   - Dialplan rules
   - Feature settings
   - SIP configuration

2. **.env**: Environment variables
   - Database credentials
   - SMTP settings (for voicemail-to-email)
   - API keys for integrations

### Setting Up Extensions

Edit `config.yml` to add extensions:

```yaml
extensions:
  - extension: "1001"
    name: "John Doe"
    password: "secure_password"
    email: "john@example.com"
  
  - extension: "1002"
    name: "Jane Smith"
    password: "another_password"
    email: "jane@example.com"
```

### Configuring Features

Enable or disable features in `config.yml`:

```yaml
features:
  voicemail:
    enabled: true
    max_message_length: 300
    email_notifications: true
  
  auto_attendant:
    enabled: true
    greeting_file: "auto_attendant/greeting.wav"
  
  call_recording:
    enabled: true
    format: "wav"
```

## Troubleshooting

### Setup Fails at System Dependencies

If the setup fails during system dependency installation:

```bash
# Update package lists manually
sudo apt-get update

# Try installing packages individually
sudo apt-get install -y espeak
sudo apt-get install -y ffmpeg
sudo apt-get install -y postgresql
# ... etc
```

### Setup Fails at Python Packages

If Python package installation fails:

```bash
# Create virtual environment manually
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

### PostgreSQL Connection Issues

If you can't connect to PostgreSQL:

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL if not running
sudo systemctl start postgresql

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### Voice Prompts Generation Fails

If voice prompt generation fails:

```bash
# Check if espeak is installed
which espeak

# Test espeak
espeak "Testing voice synthesis"

# Generate prompts manually
source venv/bin/activate
python scripts/generate_tts_prompts.py
```

### SSL Certificate Issues

If SSL certificate generation fails:

```bash
# Generate manually
source venv/bin/activate
python scripts/generate_ssl_cert.py --hostname YOUR_HOSTNAME
```

## Re-running the Setup

If you need to re-run the setup:

1. The wizard will detect existing installations
2. It will ask if you want to overwrite existing files
3. You can choose to skip certain steps

To completely reset:

```bash
# Remove virtual environment
rm -rf venv

# Remove .env file
rm .env

# Drop the database (WARNING: This deletes all data!)
sudo -u postgres psql -c "DROP DATABASE pbx_system;"
sudo -u postgres psql -c "DROP USER pbx_user;"

# Run setup again
sudo python3 setup_ubuntu.py
```

## Advanced Options

### Custom Installation Paths

By default, the setup wizard installs everything in the current directory. To use a custom path:

```bash
# Clone to your desired location
cd /opt
sudo git clone https://github.com/mattiIce/PBX.git pbx
cd pbx

# Run setup
sudo python3 setup_ubuntu.py
```

### Using Existing PostgreSQL Instance

If you have an existing PostgreSQL instance:

1. Run the setup wizard
2. When prompted for database host, enter your PostgreSQL server address
3. Provide credentials for an existing user with database creation privileges

### Skipping Voice Prompts

If you want to skip voice prompt generation during setup:

1. Run the setup wizard
2. When prompted "Generate voice prompts now?", answer "n"
3. Generate them later:
   ```bash
   source venv/bin/activate
   python scripts/generate_tts_prompts.py
   ```

## Getting Help

If you encounter issues not covered in this guide:

1. **Check the main documentation**:
   - `README.md` - Project overview
   - `COMPLETE_GUIDE.md` - Comprehensive documentation
   - `TROUBLESHOOTING.md` - Common issues and solutions

2. **Check the logs**:
   - Setup wizard output
   - `/var/log/postgresql/` - PostgreSQL logs
   - System logs: `journalctl -xe`

3. **Verify system requirements**:
   - Ubuntu version: `lsb_release -a`
   - Python version: `python3 --version`
   - Disk space: `df -h`
   - Memory: `free -h`

4. **Contact support**:
   - GitHub Issues: https://github.com/mattiIce/PBX/issues
   - Documentation: https://github.com/mattiIce/PBX

## Next Steps

After successful installation:

1. **Configure Your System**: Edit `config.yml` to set up extensions, dialplan rules, and features
2. **Test the System**: Make test calls between extensions
3. **Set Up Phones**: Configure IP phones or softphones to connect to the PBX
4. **Enable Features**: Configure voicemail, auto-attendant, and other features
5. **Integrate**: Set up integrations with Active Directory, CRM, etc.
6. **Monitor**: Set up monitoring and logging for production use

## Uninstallation

To completely remove the Warden VoIP PBX system:

```bash
# Stop the service (if running)
sudo systemctl stop pbx
sudo systemctl disable pbx
sudo rm /etc/systemd/system/pbx.service

# Remove the installation directory
cd /path/to/PBX
cd ..
sudo rm -rf PBX

# Remove the database
sudo -u postgres psql -c "DROP DATABASE pbx_system;"
sudo -u postgres psql -c "DROP USER pbx_user;"

# Optionally remove PostgreSQL if not used by other applications
sudo apt-get remove postgresql postgresql-contrib
sudo apt-get autoremove
```

---

**Note**: This setup wizard is designed for Ubuntu. For other operating systems, please refer to the manual installation instructions in `COMPLETE_GUIDE.md`.
