# Quick Setup: Automated Test Logging

## What This Does

When you run tests on your server, the system will:
1. ✅ Run all 46 tests automatically
2. ✅ Log any failures to `test_failures.log`
3. ✅ Commit the log file to git
4. ✅ Push to GitHub (if credentials are configured)

## Files Added

- **`run_tests.py`** - Main test runner script
- **`run_startup_tests.sh`** - Shell script wrapper for easy execution
- **`pbx-startup-tests.service`** - Systemd service for automatic startup testing
- **`TESTING_SETUP.md`** - Complete documentation
- **`test_failures.log`** - Generated log file (committed automatically)

## Quick Start on Server

### 1. Run Tests Manually

```bash
cd /opt/pbx  # or your installation directory
python3 run_tests.py
```

Or:

```bash
./run_startup_tests.sh
```

### 2. Configure Git Push (One-Time Setup)

To enable automatic push to GitHub:

```bash
cd /opt/pbx

# Configure git to remember credentials
git config credential.helper store

# Set identity
git config user.name "PBX Server"
git config user.email "pbx@yourserver.com"

# Test push (enter username and Personal Access Token)
git push
```

**Get a Personal Access Token:**
1. GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scope: `repo`
4. Use token as password when prompted

### 3. Enable Automatic Testing on Boot (Optional)

```bash
# Copy service file
sudo cp pbx-startup-tests.service /etc/systemd/system/

# Edit paths if needed
sudo nano /etc/systemd/system/pbx-startup-tests.service
# Update WorkingDirectory and ExecStart to match your paths

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable pbx-startup-tests.service

# Test it
sudo systemctl start pbx-startup-tests.service
sudo systemctl status pbx-startup-tests.service
```

## What You'll See

### Successful Run
```
======================================================================
Running 46 test files...
======================================================================

Running test_auto_attendant.py... ✓ PASSED
Running test_basic.py... ✓ PASSED
...

======================================================================
Results: 33/46 passed, 13/46 failed
======================================================================

✓ Failures logged to: /opt/pbx/test_failures.log
✓ Log file committed to git
✓ Log file pushed to remote repository
```

### Without Git Credentials
```
✓ Log file committed to git
⚠ Warning: Could not push to remote
  → Git credentials not configured. To enable automatic push:
     1. Generate a Personal Access Token (PAT) on GitHub
     2. Configure git credentials:
        git config credential.helper store
        git push (enter username and PAT when prompted)
```

## View Results

### On Server
```bash
cat test_failures.log
```

### On GitHub
Check your repository: `https://github.com/mattiIce/PBX/blob/main/test_failures.log`

## Current Status

As of 2025-12-08:
- **Total Tests:** 46
- **Passing:** 33 (72%)
- **Failing:** 13 (28%)

The log file shows detailed output for all failures.

## Need Help?

See `TESTING_SETUP.md` for complete documentation.
