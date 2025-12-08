# PBX System Testing Setup

This document explains how to set up automated testing that runs on server startup and commits results to GitHub.

## Overview

The PBX system includes an automated test runner that:
- Runs all tests in the `tests/` directory
- Logs failures to `test_failures.log`
- Automatically commits the log file to git
- Pushes changes to the remote repository

## Quick Start

### Manual Testing

Run tests manually at any time:

```bash
cd /opt/pbx  # or wherever your PBX is installed
python3 run_tests.py
```

Or use the shell script:

```bash
./run_startup_tests.sh
```

### Automatic Testing on Server Startup

To run tests automatically when the server boots:

#### Step 1: Install the PBX System

```bash
# Clone or copy the PBX repository to the server
git clone https://github.com/mattiIce/PBX.git /opt/pbx
cd /opt/pbx
```

#### Step 2: Configure Git Credentials

For automatic push to work, configure git credentials:

**Option A: Personal Access Token (Recommended)**

```bash
cd /opt/pbx

# Configure git to store credentials
git config credential.helper store

# Set your git identity
git config user.name "PBX Server"
git config user.email "pbx@yourcompany.com"

# Test push (you'll be prompted for username and PAT)
git push
# Username: your-github-username
# Password: ghp_your_personal_access_token
```

To generate a Personal Access Token:
1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scopes: `repo` (full control of private repositories)
4. Copy the token and use it as the password

**Option B: SSH Keys**

```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "pbx@yourcompany.com"

# Add the public key to GitHub
cat ~/.ssh/id_ed25519.pub
# Copy output and add to GitHub → Settings → SSH keys

# Configure git to use SSH
cd /opt/pbx
git remote set-url origin git@github.com:mattiIce/PBX.git
```

#### Step 3: Install the Systemd Service

```bash
# Copy the service file
sudo cp /opt/pbx/pbx-startup-tests.service /etc/systemd/system/

# Edit the service file to match your installation paths
sudo nano /etc/systemd/system/pbx-startup-tests.service
# Update WorkingDirectory and ExecStart paths
# Update User to match your PBX user

# Reload systemd
sudo systemctl daemon-reload

# Enable the service to run on boot
sudo systemctl enable pbx-startup-tests.service

# Test the service
sudo systemctl start pbx-startup-tests.service

# Check status and logs
sudo systemctl status pbx-startup-tests.service
sudo journalctl -u pbx-startup-tests.service
```

#### Step 4: Test the Setup

Reboot the server and verify:

```bash
# Reboot
sudo reboot

# After reboot, check if tests ran
sudo systemctl status pbx-startup-tests.service

# Check if log was committed
cd /opt/pbx
git log --oneline -1
# Should show: "Update test failures log - YYYY-MM-DD HH:MM:SS"

# Check GitHub to see if the log was pushed
```

## Files

### `run_tests.py`

The main test runner script that:
- Discovers all test files in `tests/` directory
- Runs each test and captures output
- Writes failures to `test_failures.log`
- Commits and pushes the log file

### `run_startup_tests.sh`

A shell script wrapper for easy execution:
- Checks prerequisites (Python)
- Runs the test runner
- Provides clear output

### `pbx-startup-tests.service`

Systemd service file for automatic execution on boot:
- Runs after network is available
- Executes the test script
- Logs output to system journal
- Doesn't block boot if tests fail

### `test_failures.log`

The generated log file containing:
- Timestamp of test run
- Summary of passed/failed tests
- Detailed output for each failed test
- Both stdout and stderr for debugging

## Troubleshooting

### Tests Don't Run on Startup

Check service status:
```bash
sudo systemctl status pbx-startup-tests.service
sudo journalctl -u pbx-startup-tests.service -n 50
```

Common issues:
- Service not enabled: `sudo systemctl enable pbx-startup-tests.service`
- Wrong paths in service file: Edit `/etc/systemd/system/pbx-startup-tests.service`
- Missing dependencies: Check Python and required modules are installed

### Log File Not Pushed to GitHub

Check git configuration:
```bash
cd /opt/pbx
git config --list | grep -E "credential|user"
```

Test push manually:
```bash
cd /opt/pbx
git pull
touch test_push.txt
git add test_push.txt
git commit -m "Test commit"
git push
# Should succeed without prompting for credentials
rm test_push.txt
git add test_push.txt
git commit -m "Remove test file"
git push
```

### Authentication Issues

If you see "Authentication failed":
1. Verify your Personal Access Token is valid
2. Ensure the token has `repo` scope
3. Re-configure credentials: `git config credential.helper store`
4. Try pushing manually to store credentials

### File Permission Issues

Ensure proper ownership:
```bash
sudo chown -R pbx:pbx /opt/pbx
sudo chmod +x /opt/pbx/run_tests.py
sudo chmod +x /opt/pbx/run_startup_tests.sh
```

## Viewing Test Results

### On the Server

```bash
# View the log file
cat /opt/pbx/test_failures.log

# View recent test runs
git log --oneline --grep="test failures log"

# View a specific test run
git show <commit-hash>:test_failures.log
```

### On GitHub

1. Go to your repository: https://github.com/mattiIce/PBX
2. View the `test_failures.log` file
3. Check commit history to see test runs over time

## Running Individual Tests

Run a specific test file:
```bash
cd /opt/pbx
python3 tests/test_basic.py
```

## Disabling Automatic Testing

To disable automatic testing on boot:
```bash
sudo systemctl disable pbx-startup-tests.service
sudo systemctl stop pbx-startup-tests.service
```

## Customization

### Change Test Timeout

Edit `run_tests.py` and modify the timeout:
```python
timeout=60,  # Change this value (in seconds)
```

### Disable Auto-Commit

Comment out the commit call in `run_tests.py`:
```python
# commit_log_file()  # Disable auto-commit
```

### Change Log File Location

Edit `run_tests.py`:
```python
LOG_FILE = Path("/var/log/pbx/test_failures.log")  # Custom location
```

## Integration with CI/CD

The test runner can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
name: PBX Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: python3 run_tests.py
```

## Security Considerations

- Store GitHub credentials securely (use PAT, not password)
- Limit PAT scope to only required permissions
- Consider using deploy keys for server deployments
- Review commit history regularly for unauthorized changes
- Use SSH keys when possible for better security

## Support

For issues or questions:
1. Check the log file: `test_failures.log`
2. Check service logs: `sudo journalctl -u pbx-startup-tests.service`
3. Review this documentation
4. Contact the PBX system maintainer
