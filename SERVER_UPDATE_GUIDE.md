# Server Update and Synchronization Guide

This guide explains how to update your PBX server with the latest code from the repository.

## ⚠️ Important: Clear Browser Cache After Update

After updating the server, **you MUST clear your browser cache** or the admin panel may not work correctly!

**Quick Fix**: Press `Ctrl + Shift + R` (Windows/Linux) or `Cmd + Shift + R` (Mac) to hard refresh the page.

See [BROWSER_CACHE_FIX.md](BROWSER_CACHE_FIX.md) for detailed instructions if the admin panel is not working after update.

## Quick Update (Recommended)

If you trust the repository and want to quickly sync your server:

```bash
cd /root/PBX
sudo bash scripts/force_update_server.sh
```

This will:
1. Create a backup in `/tmp/pbx-backup-TIMESTAMP/`
2. Hard reset to match the repository exactly
3. Verify all Python files for syntax errors
4. Restart the PBX service automatically

**⚠️ After Update**: Clear your browser cache with `Ctrl + Shift + R` to see the latest changes!

## Interactive Update

For more control over the update process:

```bash
cd /root/PBX
sudo bash scripts/update_server_from_repo.sh
```

This interactive script will:
1. Show you what files will be changed
2. Ask if you want to create a backup
3. Let you choose between hard reset or merge
4. Verify all Python files
5. Ask before restarting the service

## Manual Update Steps

If you prefer to update manually:

```bash
# Navigate to PBX directory
cd /root/PBX

# Check current status
git status

# See what will be updated
git fetch --all
git log HEAD..origin/$(git branch --show-current) --oneline

# Option 1: Hard reset (discards all local changes)
git reset --hard origin/$(git branch --show-current)
git clean -fd

# Option 2: Pull and merge (keeps local changes)
git pull origin $(git branch --show-current)

# Verify Python syntax
find . -name "*.py" -type f ! -path "./.git/*" -exec python3 -m py_compile {} \;

# Restart the service
sudo systemctl restart pbx

# Check status
sudo systemctl status pbx
```

## Fixing the Current Login Issue

The current authentication failure is caused by a syntax error on your server. To fix it immediately:

```bash
# Update from repository
cd /root/PBX
git fetch --all
git reset --hard origin/$(git branch --show-current)

# Restart PBX service
sudo systemctl restart pbx

# Verify it's running
sudo systemctl status pbx

# Check logs
sudo journalctl -u pbx -f
```

## Troubleshooting

### If update fails with "local changes" error:

```bash
# Stash local changes
git stash

# Update
git pull origin $(git branch --show-current)

# Or hard reset
git reset --hard origin/$(git branch --show-current)
```

### If syntax errors appear after update:

```bash
# Check which files have errors
find . -name "*.py" -type f ! -path "./.git/*" -exec python3 -m py_compile {} \; 2>&1 | grep -i error

# Review the specific file
# The error message will show the file and line number
```

### If service won't start after update:

```bash
# Check service status
sudo systemctl status pbx

# View recent logs
sudo journalctl -u pbx -n 50

# View real-time logs
sudo journalctl -u pbx -f
```

## Rollback to Previous Version

If the update causes issues:

```bash
# Find backup directory
ls -lt /tmp/pbx-backup-* | head -1

# Or rollback to a specific commit
cd /root/PBX
git log --oneline -10
git reset --hard <commit-hash>
sudo systemctl restart pbx
```

## Automated Updates

To set up automated updates (use with caution in production):

```bash
# Create a cron job
sudo crontab -e

# Add this line to update daily at 3 AM:
0 3 * * * cd /root/PBX && bash scripts/force_update_server.sh >> /var/log/pbx-update.log 2>&1
```

## Best Practices

1. **Always create backups** before updating production systems
2. **Test updates** in a staging environment first if possible
3. **Monitor logs** after updates for any issues
4. **Keep track of backups** in `/tmp/pbx-backup-*` directories
5. **Review changes** before applying updates: `git log HEAD..origin/main`

## Emergency Recovery

If everything breaks:

```bash
# Restore from the latest backup
LATEST_BACKUP=$(ls -t /tmp/pbx-backup-* | head -1)
cd /root/PBX
cp -r "$LATEST_BACKUP"/* .
sudo systemctl restart pbx
```
