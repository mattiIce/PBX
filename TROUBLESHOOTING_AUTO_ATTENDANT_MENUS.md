# Troubleshooting Auto-Attendant Menu Issues

## Quick Diagnostic Script

We've provided a test script to quickly diagnose API endpoint issues:

```bash
# Run from the PBX directory
python3 scripts/test_menu_endpoints.py

# Test a remote server
python3 scripts/test_menu_endpoints.py --host abps.albl.com --port 9000

# Test with HTTPS
python3 scripts/test_menu_endpoints.py --protocol https --port 9000
```

This script will test all the menu-related API endpoints and report which ones are working and which are not. It's the fastest way to diagnose whether the issue is with the server configuration or the code deployment.

## Common Issues and Solutions

### Issue 1: 404 Errors on Menu API Endpoints

**Symptoms:**
- Browser console shows errors like: `/api/auto-attendant/menus:1 Failed to load resource: the server responded with a status of 404 (Not Found)`
- Parent menu dropdown is empty when creating a submenu
- Tree view shows "Failed to load menu tree" error
- Nothing appears in submenu selection dropdowns

**Root Cause:**
The API server is running an older version of the code that doesn't include the hierarchical menu API endpoints, or the server hasn't been restarted after the code was updated.

**Solution:**
1. **Verify the code version on the server:**
   ```bash
   cd /path/to/PBX
   git log --oneline -1 -- pbx/api/rest_api.py
   ```
   You should see a commit related to auto-attendant submenu implementation.

2. **If code is up to date, restart the PBX service:**
   ```bash
   sudo systemctl restart pbx
   # Or if running manually:
   sudo systemctl restart pbx-api
   ```

3. **Verify the API server is running:**
   ```bash
   sudo systemctl status pbx
   # Check if the API server is listening on the configured port (default 9000)
   sudo netstat -tulpn | grep 9000
   ```

4. **Check the API logs for errors:**
   ```bash
   sudo journalctl -u pbx -f
   # Or check application logs:
   tail -f /path/to/pbx/logs/pbx.log
   ```

5. **Test the endpoints directly:**
   ```bash
   # Test the menus endpoint
   curl -X GET http://localhost:9000/api/auto-attendant/menus
   
   # Test the menu tree endpoint
   curl -X GET http://localhost:9000/api/auto-attendant/menu-tree
   ```

### Issue 2: Regex Pattern Validation Error in Browser Console

**Symptoms:**
- Browser console shows: `Pattern attribute value [a-z0-9_-]+ is not a valid regular expression`
- Error occurs when viewing the Create Submenu modal

**Root Cause:**
The HTML5 pattern attribute in older browsers may have issues with unescaped hyphens in character classes.

**Solution:**
This has been fixed in the latest code. The pattern is now `[a-z0-9_-]+` with the hyphen placed at the end of the character class, which is the conventional and safer approach.

If you're still seeing this error:
1. Clear your browser cache (Ctrl+Shift+Delete)
2. Hard refresh the page (Ctrl+F5)
3. Verify the HTML file has been updated on the server

### Issue 3: Empty Dropdowns When Creating Submenu

**Symptoms:**
- The "Parent Menu" dropdown is empty when trying to create a submenu
- No options appear when selecting "Submenu" as a destination type

**Root Cause:**
The API endpoint `/api/auto-attendant/menus` is not returning any data, usually because:
- The endpoint is returning a 404 (see Issue 1)
- The auto_attendant database tables haven't been initialized
- The auto_attendant feature is not enabled in the PBX core

**Solution:**
1. **Check if auto_attendant tables exist in the database:**
   ```bash
   sqlite3 pbx.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'auto_attendant%';"
   ```
   You should see:
   - `auto_attendant_config`
   - `auto_attendant_menus`
   - `auto_attendant_menu_items`
   - `auto_attendant_menu_options` (legacy)

2. **If tables don't exist, they will be created automatically when the auto_attendant feature initializes. Check if auto_attendant is enabled:**
   ```yaml
   # In config.yml
   auto_attendant:
     enabled: true
     extension: "0"
   ```

3. **Verify the main menu exists:**
   ```bash
   sqlite3 pbx.db "SELECT * FROM auto_attendant_menus WHERE menu_id='main';"
   ```
   If no rows are returned, insert the main menu manually:
   ```bash
   sqlite3 pbx.db "INSERT INTO auto_attendant_menus (menu_id, parent_menu_id, menu_name, prompt_text) VALUES ('main', NULL, 'Main Menu', 'Main menu options');"
   ```

4. **Restart the PBX service:**
   ```bash
   sudo systemctl restart pbx
   ```

### Issue 4: Menu Tree Shows "Failed to Load"

**Symptoms:**
- Clicking "View Menu Tree" button shows error message
- Error: "Failed to load menu tree"

**Root Cause:**
Same as Issue 1 - the API endpoint is not available or returning an error.

**Solution:**
1. Follow the solutions in Issue 1 to ensure API endpoints are available
2. Check browser console for specific error messages
3. Verify the `get_menu_tree` method exists in `pbx/features/auto_attendant.py`
4. Test the endpoint directly:
   ```bash
   curl -X GET http://localhost:9000/api/auto-attendant/menu-tree
   ```

## Deployment Checklist

When deploying auto-attendant menu features to a server:

- [ ] Pull latest code from repository
- [ ] Verify Python dependencies are up to date: `pip install -r requirements.txt`
- [ ] Check that database migrations have run (tables created)
- [ ] Restart the PBX service
- [ ] Clear browser cache on client side
- [ ] Test API endpoints directly with curl
- [ ] Check for any errors in application logs
- [ ] Verify auto_attendant is enabled in config.yml

## API Endpoints Reference

The following API endpoints should be available for hierarchical menu management:

**GET Endpoints:**
- `GET /api/auto-attendant/menus` - List all menus
- `GET /api/auto-attendant/menus/{menu_id}` - Get specific menu details
- `GET /api/auto-attendant/menus/{menu_id}/items` - Get items for a menu
- `GET /api/auto-attendant/menu-tree` - Get complete menu hierarchy

**POST Endpoints:**
- `POST /api/auto-attendant/menus` - Create a new menu/submenu
- `POST /api/auto-attendant/menus/{menu_id}/items` - Add item to a menu

**PUT Endpoints:**
- `PUT /api/auto-attendant/menus/{menu_id}` - Update menu details
- `PUT /api/auto-attendant/menus/{menu_id}/items/{digit}` - Update menu item

**DELETE Endpoints:**
- `DELETE /api/auto-attendant/menus/{menu_id}` - Delete a menu
- `DELETE /api/auto-attendant/menus/{menu_id}/items/{digit}` - Delete menu item

## Quick Fix for Production

If you need a quick fix in production and can't immediately update the code:

1. **Restart the service** - This often resolves stale route issues:
   ```bash
   sudo systemctl restart pbx
   ```

2. **Check for Python syntax errors:**
   ```bash
   python3 -m py_compile pbx/api/rest_api.py
   ```

3. **Verify file permissions:**
   ```bash
   ls -la pbx/api/rest_api.py
   # Should be readable by the PBX service user
   ```

## Getting More Help

If none of these solutions work:

1. **Enable debug logging** in `config.yml`:
   ```yaml
   logging:
     level: DEBUG
   ```

2. **Restart and capture full logs:**
   ```bash
   sudo systemctl restart pbx
   sudo journalctl -u pbx -f > debug.log
   ```

3. **Test in a development environment first:**
   - Run the PBX locally with `python3 main.py`
   - Test the admin interface at `http://localhost:9000/admin/`
   - Check console for errors

4. **Verify browser compatibility:**
   - Use a modern browser (Chrome, Firefox, Edge)
   - Ensure JavaScript is enabled
   - Try in incognito mode to rule out extensions

## Related Documentation

- [Auto-Attendant Implementation Guide](ADMIN_PANEL_AUTO_ATTENDANT.md)
- [API Documentation](API_DOCUMENTATION.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [General Troubleshooting](TROUBLESHOOTING.md)
