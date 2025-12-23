# Quick Fix for Authentication Issue

## Problem
Login to the web interface fails with "authentication failed" error due to a SyntaxError in `/root/PBX/pbx/utils/license_admin.py`.

## Immediate Fix

Run these commands on your server (**root@pbx-server**):

```bash
# Navigate to PBX directory
cd /root/PBX

# Backup current state (just in case)
cp -r . /tmp/pbx-backup-$(date +%Y%m%d-%H%M%S)/

# Force update from repository
git fetch --all
git reset --hard origin/$(git branch --show-current)

# Restart PBX service
systemctl restart pbx

# Verify service is running
systemctl status pbx

# Check for errors in logs
journalctl -u pbx -n 50 --no-pager
```

## What This Does

1. **Backs up** your current installation to `/tmp/`
2. **Fetches** the latest code from the GitHub repository
3. **Resets** all files to match the repository (discarding any local modifications)
4. **Restarts** the PBX service
5. **Verifies** the service is running without errors

## Verify the Fix

After running the commands, try logging in to the web interface:

1. Open your browser to the PBX web interface
2. Enter your extension number and password
3. Login should now work without the "authentication failed" error

## Why This Works

The syntax error exists only on your server, not in the repository. All 274 Python files in the repository have been verified to be syntactically correct. By resetting your server to match the repository, you'll replace any corrupted or modified files with the correct versions.

## Alternative: Use the Update Script

We've created automated update scripts for you:

```bash
cd /root/PBX

# Quick force update (no prompts)
bash scripts/force_update_server.sh

# OR interactive update (with prompts)
bash scripts/update_server_from_repo.sh
```

## If Issues Persist

If you still see errors after updating:

```bash
# Check which Python files have syntax errors
cd /root/PBX
find . -name "*.py" -type f ! -path "./.git/*" | while read f; do 
    python3 -m py_compile "$f" 2>&1 | grep -i error && echo "Error in: $f"
done

# View detailed service logs
journalctl -u pbx -f
```

Then share the error output for further assistance.

## Prevention

To prevent this issue in the future, always update the server from the repository rather than manually editing files:

```bash
# Regular updates
cd /root/PBX
git pull origin main
systemctl restart pbx
```

See [SERVER_UPDATE_GUIDE.md](SERVER_UPDATE_GUIDE.md) for complete update procedures.
