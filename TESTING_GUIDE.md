# PBX System Testing Guide

**Last Updated**: December 29, 2025  
**Purpose**: Complete guide for testing PBX functionality, automated testing, and integration testing

## Table of Contents
- [Automated Testing Setup](#automated-testing-setup)
- [Active Directory Integration Testing](#active-directory-integration-testing)
- [Phone-to-Phone Audio Testing](#phone-to-phone-audio-testing)
- [General Testing Procedures](#general-testing-procedures)

---

## Automated Testing Setup

### Overview

The PBX system includes an automated test runner that:
- Runs all tests in the `tests/` directory
- Logs failures to `test_failures.log`
- Automatically commits the log file to git (optional)
- Pushes changes to the remote repository (optional)

### Manual Testing

Run tests manually at any time:

```bash
cd /path/to/PBX
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

#### Step 2: Configure Git Credentials (Optional)

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
git remote set-url origin git@github.com:your-username/PBX.git
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

# Start the service now (optional)
sudo systemctl start pbx-startup-tests.service

# Check status
sudo systemctl status pbx-startup-tests.service
```

### Test Output

Tests create a `test_failures.log` file with results:

```bash
# View test results
cat test_failures.log

# Monitor in real-time
tail -f test_failures.log
```

---

## Active Directory Integration Testing

### Prerequisites

Before testing, ensure you have:
- [ ] Active Directory server accessible
- [ ] Service account credentials
- [ ] Users in AD with `telephoneNumber` attribute set
- [ ] `ldap3` Python library installed: `pip install ldap3`
- [ ] Database configured (SQLite or PostgreSQL)

### Step 1: Test AD Connection and Configuration

Run the comprehensive AD integration test:

```bash
python scripts/test_ad_integration.py
```

**What it tests:**
- ✓ Configuration is valid and complete
- ✓ Required dependencies (ldap3) are installed
- ✓ Connection to AD server succeeds
- ✓ Authentication with bind credentials works
- ✓ User search and discovery functions
- ✓ User attributes are retrieved correctly
- ✓ Extensions can be synced without conflicts
- ✓ Overall integration readiness

**Expected output:**
```
======================================================================
Test Summary
======================================================================
Total tests: 15
Passed: 13
Failed: 0
Warnings: 2

✓ ALL TESTS PASSED

Active Directory integration is configured correctly!
```

**If tests fail:**
- Check server address and credentials in `config.yml`
- Verify network connectivity to AD server
- Ensure service account has read permissions
- Review error messages for specific issues

### Step 2: Run AD User Sync (Dry Run)

Test what would be synced without making changes:

```bash
python scripts/sync_ad_users.py --dry-run
```

**What to look for:**
- Number of users found in AD
- List of users that would be synced
- Any users that would be skipped (missing phone numbers, etc.)
- Extension number mappings

**Example output:**
```
Found 15 users in Active Directory

Synchronizing users...
Creating extension 5551234 for user jdoe
Creating extension 5555678 for user jsmith
...

Synchronization Complete: 15 users would be synchronized
```

### Step 3: Perform Actual Sync

Run the real sync to create extensions:

```bash
python scripts/sync_ad_users.py
```

**What happens:**
- ✅ Connects to database (or falls back to config.yml)
- ✅ Searches AD for users with phone numbers
- ✅ Creates new extensions in database
- ✅ Updates existing extensions
- ✅ Marks all synced extensions with `ad_synced=true`
- ✅ Stores AD username for tracking

**Success indicators:**
```
✓ Connected to database - extensions will be synced to database
✓ Found 15 users in Active Directory
✓ Synchronized 15 extensions
✓ Sync completed successfully
```

### Step 4: Verify Synced Extensions

Check the database or API:

```bash
# List all extensions
python scripts/list_extensions_from_db.py

# Or use the API
curl http://localhost:8080/api/extensions
```

### Troubleshooting AD Integration

**Connection fails:**
- Verify AD server address and port in config.yml
- Check network connectivity: `telnet ad-server.domain.com 389`
- Ensure firewall allows LDAP traffic

**Authentication fails:**
- Verify bind DN format: `CN=Service Account,OU=Users,DC=domain,DC=com`
- Check bind password is correct
- Ensure service account is not disabled or expired

**No users found:**
- Verify search base DN is correct
- Check users have `telephoneNumber` attribute set
- Review search filter in config.yml

**Sync creates duplicate extensions:**
- Use `--dry-run` first to preview
- Check for existing extensions with same numbers
- Review conflict resolution strategy in config

---

## Phone-to-Phone Audio Testing

### Problem Summary
You reported that with your Zultys ZIP 37G and other Zultys phones:
- ✅ Server IP is 192.168.1.14
- ✅ Phones register successfully
- ❌ When calling phone to phone, it's silent (no audio)
- ❌ The other phone rings but there's no audio in either direction

## What Was Fixed

The root cause was **missing SDP (Session Description Protocol) handling**. The PBX was not:
1. Parsing where phones wanted to send/receive RTP audio
2. Telling phones where to send their audio (to the PBX relay)
3. Setting up bidirectional audio relay between the two phones

### Changes Made

1. **Added SDP Support** - The PBX now:
   - Parses SDP from INVITE messages to learn phone RTP endpoints
   - Builds SDP to tell phones where to send audio (to PBX relay)
   - Properly negotiates codecs (PCMU, PCMA)

2. **Added RTP Relay** - The PBX now:
   - Allocates RTP ports for each call (from pool 10000-20000)
   - Receives audio from both phones
   - Forwards audio bidirectionally between them

3. **Fixed SIP Signaling** - The PBX now:
   - Forwards INVITE with proper SDP to callee
   - Returns 200 OK with proper SDP to caller
   - Forwards ACK to complete the handshake

4. **Added Configuration** - Set external IP:
   ```yaml
   server:
     external_ip: "192.168.1.14"
   ```

## How to Test

### Step 1: Verify Configuration

Check `config.yml` has the correct settings:

```yaml
server:
  sip_host: "0.0.0.0"          # Binds to all interfaces
  sip_port: 5060
  external_ip: "192.168.1.14"  # YOUR SERVER IP - phones will send RTP here
  rtp_port_range_start: 10000
  rtp_port_range_end: 20000
```

### Step 2: Start the PBX

```bash
cd /home/runner/work/PBX/PBX
python main.py
```

Expected output:
```
============================================================
InHouse PBX System v1.0.0
============================================================
2025-XX-XX XX:XX:XX - PBX - INFO - Loaded extension 1001 (Office Extension 1)
2025-XX-XX XX:XX:XX - PBX - INFO - Loaded extension 1002 (Office Extension 2)
2025-XX-XX XX:XX:XX - PBX - INFO - SIP server started on 0.0.0.0:5060
2025-XX-XX XX:XX:XX - PBX - INFO - PBX system started successfully
```

### Step 3: Configure Your Zultys Phones

**Phone 1 (Extension 1001):**
- SIP Server: 192.168.1.14
- SIP Port: 5060
- Extension/Username: 1001
- Password: password1001

**Phone 2 (Extension 1002):**
- SIP Server: 192.168.1.14
- SIP Port: 5060
- Extension/Username: 1002
- Password: password1002

### Step 4: Register Phones

Watch the PBX logs for:
```
INFO - Extension 1001 registered from ('192.168.1.X', 5060)
INFO - Extension 1002 registered from ('192.168.1.Y', 5060)
```

### Step 5: Make a Test Call

1. **From phone 1001, dial: 1002**

2. **Expected PBX logs:**
   ```
   INFO - INVITE request from ('192.168.1.X', 5060)
   INFO - Caller RTP: 192.168.1.X:XXXXX
   INFO - RTP relay allocated on port 10000
   INFO - Forwarded INVITE to 1002 at ('192.168.1.Y', 5060)
   INFO - Routing call xxx: 1001 -> 1002 via RTP relay 10000
   ```

3. **Phone 1002 should ring**

4. **Expected PBX logs (ringing):**
   ```
   INFO - Callee ringing for call xxx
   ```

5. **Answer on phone 1002**

6. **Expected PBX logs (answer):**
   ```
   INFO - Callee answered call xxx
   INFO - Callee RTP: 192.168.1.Y:YYYYY
   INFO - RTP relay connected for call xxx
   INFO - Sent 200 OK to caller for call xxx
   DEBUG - Forwarded ACK to callee for call xxx
   ```

7. **Expected audio behavior:**
   - ✅ **Both phones should hear each other**
   - ✅ Audio should be clear (G.711 codec)
   - ✅ Bidirectional audio (both can talk and hear)

8. **During the call, you should see:**
   ```
   DEBUG - Relayed 160 bytes: A->B
   DEBUG - Relayed 160 bytes: B->A
   DEBUG - Relayed 160 bytes: A->B
   DEBUG - Relayed 160 bytes: B->A
   ```

### Step 6: End the Call

Hang up from either phone. Expected logs:
```
INFO - BYE request from ('192.168.1.X', 5060)
INFO - Ending call xxx
INFO - Released RTP relay for call xxx
```

## Troubleshooting

### Issue: Still No Audio

**Check 1: Network Configuration**
```bash
# On PBX server, verify IP address
ip addr show

# Verify UDP ports are open
sudo netstat -ulnp | grep python
# Should show port 5060 and ports from 10000-20000
```

**Check 2: Configuration**
```bash
# Verify external_ip is set correctly
grep external_ip config.yml
# Should show: external_ip: "192.168.1.14"
```

**Check 3: Phone Configuration**
- Ensure phones are pointed to 192.168.1.14:5060
- Ensure phones are on same network (192.168.1.x)
- Check phones can ping 192.168.1.14

**Check 4: Firewall**
```bash
# If using firewall, open ports
sudo ufw allow 5060/udp     # SIP signaling
sudo ufw allow 10000:20000/udp  # RTP media
```

### Issue: One-Way Audio

**Symptoms:** Can hear in one direction only

**Check:** Look for asymmetric RTP relay logs:
```
DEBUG - Relayed 160 bytes: A->B
DEBUG - Relayed 160 bytes: A->B
# If you only see A->B and never B->A, phone B isn't sending
```

**Solutions:**
1. Check phone B's network settings
2. Verify phone B received correct SDP (check logs)
3. Test network connectivity from phone B to 192.168.1.14

### Issue: Phones Don't Ring

**Check 1:** Verify extension is registered:
```
# In logs, look for:
INFO - Extension 1002 registered from ...
```

**Check 2:** Verify extension exists in config.yml:
```bash
grep -A 3 "number: \"1002\"" config.yml
```

**Check 3:** Enable DEBUG logging in config.yml:
```yaml
logging:
  level: "DEBUG"  # Change from INFO to DEBUG
```

## Expected Call Flow

```
Phone 1001              PBX (192.168.1.14)              Phone 1002
(192.168.1.100)         RTP Port: 10000             (192.168.1.101)
    |                        |                             |
    | INVITE                 |                             |
    | SDP: 192.168.1.100:X   |                             |
    |----------------------->|                             |
    |                        | INVITE                      |
    |                        | SDP: 192.168.1.14:10000     |
    |                        |---------------------------->|
    |                        |                             |
    |                 180 Ringing                   180 Ringing
    |<-----------------------|<----------------------------|
    |                        |                             |
    |                        |                      200 OK |
    |                        | SDP: 192.168.1.101:Y        |
    |                        |<----------------------------|
    |                 200 OK |                             |
    | SDP: 192.168.1.14:10000|                             |
    |<-----------------------|                             |
    |                        |                             |
    | ACK                    |                             |
    |----------------------->| ACK                         |
    |                        |---------------------------->|
    |                        |                             |
    | RTP Audio              |              RTP Audio      |
    |=======================>|============================>|
    |                        |                             |
    |              RTP Audio |              RTP Audio      |
    |<======================|<============================|
    |                        |                             |
```

## Verification Checklist

- [ ] PBX starts without errors
- [ ] Both phones register successfully
- [ ] Call from 1001 to 1002 makes phone ring
- [ ] Answering the call connects both parties
- [ ] **Audio works in BOTH directions** ← Main fix!
- [ ] Call can be ended from either phone
- [ ] RTP relay logs show bidirectional traffic

## Additional Notes

### Supported Codecs
Your Zultys phones will negotiate one of:
- **PCMU (G.711 μ-law)** - Most common in North America
- **PCMA (G.711 A-law)** - Most common in Europe
- **telephone-event** - For DTMF tones

### Network Requirements
- All devices on same subnet (192.168.1.0/24) is simplest
- No NAT between phones and PBX
- UDP ports not blocked by firewalls
- Reasonable latency (<100ms) for good voice quality

### Log Levels
- **INFO** - Normal operation, shows call flow
- **DEBUG** - Detailed, shows every RTP packet relay
- **WARNING** - Problems but system continues
- **ERROR** - Serious issues

## Getting Help

If audio still doesn't work after following this guide:

1. **Collect logs** with DEBUG level enabled
2. **Test network** connectivity between phones and PBX
3. **Verify** SDP is being sent correctly (check logs for "RTP:" entries)
4. **Check** that RTP relay shows bidirectional traffic

The fix is in the code - it's now a matter of configuration and network setup!

---

## General Testing Procedures

### Unit Testing

Run Python unit tests:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_sip.py

# Run with coverage
pytest --cov=pbx --cov-report=html

# Run with verbose output
pytest -v
```

### Integration Testing

Test complete call flows:

```bash
# Test SIP registration
python scripts/test_sip_registration.py

# Test call routing
python scripts/test_call_routing.py

# Test voicemail
python scripts/test_voicemail.py
```

### Performance Testing

Test system under load:

```bash
# Simulate multiple concurrent calls
python scripts/load_test.py --calls 10

# Monitor system resources
htop
```

### Manual Testing Checklist

**Basic Functionality:**
- [ ] PBX starts without errors
- [ ] Extensions register successfully
- [ ] Internal calls work (extension to extension)
- [ ] External calls work (if configured)
- [ ] Voicemail works (dial *extension_number)
- [ ] Auto attendant works (dial 0)
- [ ] Call transfer works
- [ ] Call forwarding works
- [ ] Conference calling works

**Audio Quality:**
- [ ] Audio is clear in both directions
- [ ] No echo or feedback
- [ ] No choppy or robotic audio
- [ ] DTMF tones work (menu navigation)
- [ ] Music on hold plays correctly

**Admin Panel:**
- [ ] Can login to admin panel
- [ ] Can view extensions
- [ ] Can add/edit/delete extensions
- [ ] Can configure auto attendant
- [ ] Can manage voicemail boxes
- [ ] Can view call logs

**Integrations:**
- [ ] Jitsi video conferencing works (if enabled)
- [ ] Matrix messaging works (if enabled)
- [ ] EspoCRM integration works (if enabled)
- [ ] Active Directory sync works (if enabled)
- [ ] Email notifications work (if enabled)

### Continuous Integration

Set up automated testing in CI/CD:

```yaml
# Example GitHub Actions workflow
name: PBX Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest
```

### Test Data Management

**Create test extensions:**

```bash
python scripts/seed_extensions.py
```

**Reset test data:**

```bash
# Backup current database
cp pbx.db pbx.db.backup

# Reset to clean state
rm pbx.db
python scripts/init_database.py
python scripts/seed_extensions.py
```

### Debugging Failed Tests

**Enable debug logging:**

```yaml
# In config.yml
logging:
  level: DEBUG
```

**Capture detailed logs:**

```bash
# Run tests with verbose logging
pytest -v --log-cli-level=DEBUG > test_output.log 2>&1

# View logs
less test_output.log
```

**Common test failures:**

1. **Database connection errors**: Check database is running and accessible
2. **Network timeouts**: Verify network connectivity and firewall rules
3. **Missing dependencies**: Run `pip install -r requirements.txt`
4. **Permission errors**: Check file permissions and user access
5. **Port conflicts**: Ensure ports 5060, 8080, 10000-20000 are available

---

**For additional testing resources, see:**
- [E911_TESTING_PROCEDURES.md](E911_TESTING_PROCEDURES.md) - Emergency call testing
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Troubleshooting guide
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - Complete documentation

---

**Last Updated**: December 29, 2025  
**Status**: Production Ready
