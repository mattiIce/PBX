# PBX Systemd Service Installation

This directory contains the systemd service file for running the PBX system as a service.

## Quick Installation

1. **Edit the service file** to match your installation:
   ```bash
   nano pbx.service
   ```
   
   Update these fields:
   - `WorkingDirectory`: Set to your PBX installation directory (e.g., `/root/PBX`, `/opt/pbx`, `/home/username/PBX`)
   - `ExecStart`: Update the path to your Python executable and main.py
   - `User`: Set to the user that owns the PBX files (e.g., `root`, `pbx`, your username)
   - `Group`: Set to the group that owns the PBX files

2. **Copy the service file** to systemd directory:
   ```bash
   sudo cp pbx.service /etc/systemd/system/
   ```

3. **Reload systemd** to recognize the new service:
   ```bash
   sudo systemctl daemon-reload
   ```

4. **Enable the service** to start on boot:
   ```bash
   sudo systemctl enable pbx
   ```

5. **Start the service**:
   ```bash
   sudo systemctl start pbx
   ```

6. **Check the service status**:
   ```bash
   sudo systemctl status pbx
   ```

## Common Installation Paths

The service file template uses `/root/PBX` as the default path. Here are common alternatives:

- **Root user installation**: `/root/PBX`
- **System-wide installation**: `/opt/pbx`
- **User installation**: `/home/username/PBX`
- **Dedicated PBX user**: `/home/pbx/PBX`

## Troubleshooting

### Service fails to start with "CHDIR" error

This error occurs when the `WorkingDirectory` is not set or points to a non-existent directory.

**Solution**: Verify that:
1. The `WorkingDirectory` path exists
2. The path is absolute (starts with `/`)
3. The user specified in `User` has read access to the directory

### Service fails with "Permission denied"

**Solution**: Check that:
1. The `User` and `Group` have permission to access the PBX directory
2. The Python executable path in `ExecStart` is correct
3. The virtual environment (if using one) is accessible

### View service logs

```bash
# Real-time logs
sudo journalctl -u pbx -f

# Recent logs
sudo journalctl -u pbx -n 100

# Logs since last boot
sudo journalctl -u pbx -b
```

## Using Virtual Environment

The default service file uses system Python (`/usr/bin/python3`), which works with the standard installation process.

If you're using a Python virtual environment, update the `ExecStart` line:

```ini
ExecStart=/root/PBX/venv/bin/python3 /root/PBX/main.py
```

Or:

```ini
ExecStart=/opt/pbx/venv/bin/python3 /opt/pbx/main.py
```

**Important**: Always use absolute paths in the service file.

**Note**: The standard installation uses `install_requirements.sh`, which installs packages system-wide (not in a venv), so the default `/usr/bin/python3` works out of the box.

## See Also

- `pbx-startup-tests.service` - Optional service for running startup tests
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Full deployment documentation
- [INSTALLATION.md](INSTALLATION.md) - Installation instructions
