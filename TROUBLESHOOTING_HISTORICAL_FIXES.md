# Historical Bug Fixes and Solutions

This document archives significant bug fixes and their solutions for future reference. For current troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Table of Contents

1. [Admin Panel Display Issues (Browser Cache)](#admin-panel-display-issues-browser-cache)
2. [API Connection Timeout (Reverse Proxy)](#api-connection-timeout-reverse-proxy)
3. [Login Connection Errors](#login-connection-errors)
4. [Admin Portal CSP Issues](#admin-portal-csp-issues)
5. [Monitoring Access Fix](#monitoring-access-fix)

---

## Admin Panel Display Issues (Browser Cache)

**Date:** December 23, 2025  
**Status:** ✅ RESOLVED  
**Reference:** See [BROWSER_CACHE_FIX.md](BROWSER_CACHE_FIX.md)

### Problem
After running server updates, the admin panel displayed incorrectly with non-functional buttons. Only the login component worked.

### Root Cause
Browser caching old CSS and JavaScript files after server code updates, creating mismatches between HTML structure and styles/scripts.

### Solution
1. **Immediate Fix:** Hard refresh with `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
2. **Prevention:** 
   - Added cache-control meta tags to HTML files
   - Added version query parameters to CSS/JS includes (`?v=YYYYMMDD`)
   - Automatic detection with warning banner
3. **Tools:** Created `/admin/status-check.html` diagnostic page

### Files Modified
- `admin/index.html` - Cache control and version parameters
- `admin/login.html` - Cache control headers
- `admin/status-check.html` - NEW diagnostic page
- `BROWSER_CACHE_FIX.md` - NEW comprehensive guide
- `scripts/update_server_from_repo.sh` - Added cache warnings
- `scripts/force_update_server.sh` - Added cache warnings

---

## API Connection Timeout (Reverse Proxy)

**Date:** December 23, 2025  
**Status:** ✅ RESOLVED

### Problem
When accessing admin portal through reverse proxy (e.g., `http://abps.albl.com`), login page failed with `ERR_CONNECTION_TIMED_OUT` on port 9000.

### Root Cause
The `getAPIBase()` function incorrectly defaulted to port 9000 for all non-9000 ports, bypassing the reverse proxy.

### Solution
Updated API detection logic to recognize reverse proxy scenarios:

```javascript
function getAPIBase() {
    // 1. Check for meta tag override
    const apiMeta = document.querySelector('meta[name="api-base-url"]');
    if (apiMeta && apiMeta.content) {
        return apiMeta.content;
    }
    
    // 2. API port 9000 - use same origin
    if (window.location.port === '9000') {
        return window.location.origin;
    }
    
    // 3. Standard ports (80/443/empty) - reverse proxy detected
    if (window.location.port === '' || 
        window.location.port === '80' || 
        window.location.port === '443') {
        return window.location.origin;  // Use reverse proxy
    }
    
    // 4. Fallback for non-standard ports
    return `${protocol}//${hostname}:9000`;
}
```

### Deployment Scenarios
- **Reverse Proxy (nginx):** `http://abps.albl.com` → API calls to `http://abps.albl.com/api/*` ✅
- **Direct Access:** `http://server:9000` → API calls to `http://server:9000/api/*` ✅
- **HTTPS Proxy:** `https://abps.albl.com` → API calls to `https://abps.albl.com/api/*` ✅
- **Custom Config:** Meta tag override supported ✅

### Files Modified
- `admin/login.html` - Updated `getAPIBase()` function
- `admin/js/admin.js` - Updated `getAPIBase()` function
- `LOGIN_CONNECTION_TROUBLESHOOTING.md` - Updated with new logic

---

## Login Connection Errors

**Date:** December 23, 2025  
**Status:** ✅ RESOLVED  
**Reference:** See [LOGIN_CONNECTION_TROUBLESHOOTING.md](LOGIN_CONNECTION_TROUBLESHOOTING.md)

### Problem
Users unable to login with generic error: "connection error please try again"

### Root Cause
- Generic error messages that didn't indicate actual problem
- No validation of API responses before parsing JSON
- No automatic connectivity testing
- No user guidance for troubleshooting

### Solution
1. **Enhanced Error Handling:**
   - Validate `Content-Type` header before parsing JSON
   - Differentiate error types (network, JSON parsing, server errors)
   - Context-specific error messages

2. **Automatic Diagnostics:**
   - API connectivity test on page load
   - Console logging with detailed diagnostics
   - Visual troubleshooting section

3. **Security Improvements:**
   - Use `textContent` instead of `innerHTML` (prevents XSS)
   - Sanitize error messages
   - No sensitive data in error messages

### Files Modified
- `admin/login.html` - Enhanced error handling and diagnostics
- `LOGIN_CONNECTION_TROUBLESHOOTING.md` - NEW comprehensive guide
- `README.md` - Added to Known Issues section

### Common Scenarios Handled
1. **PBX Server Not Running:** Clear message to start server
2. **Firewall Blocking Port:** Connection timeout with firewall checks
3. **Server Error (500):** Invalid response with log checking guidance
4. **Wrong Port:** API base URL detection with correction steps

---

## Admin Portal CSP Issues

**Date:** December 2025  
**Status:** ✅ RESOLVED

### Problem
Content Security Policy (CSP) header had typo: `'sel'` instead of `'self'`

### Root Cause
Typing error in CSP header configuration

### Solution
```python
# Before (incorrect)
"Content-Security-Policy": "default-src 'sel'; ..."

# After (correct)
"Content-Security-Policy": "default-src 'self'; ..."
```

### Files Modified
- `pbx/api/rest_api.py` - Fixed CSP header typo

---

## Monitoring Access Fix

**Date:** December 2025  
**Status:** ✅ RESOLVED

### Problem
Monitoring endpoints not accessible through admin interface

### Root Cause
Missing routes or permission checks in API layer

### Solution
- Added proper routing for monitoring endpoints
- Updated permission checks to allow admin access
- Added monitoring tab to admin UI

### Files Modified
- `pbx/api/rest_api.py` - Added monitoring routes
- `admin/index.html` - Added monitoring tab
- `admin/js/admin.js` - Added monitoring functions

---

## Quick Fix Login Issues

**Summary of QUICK_FIX_LOGIN.md**

### Common Login Issues and Rapid Fixes

1. **Cannot Reach API Server**
   - Check: `sudo systemctl status pbx`
   - Fix: `sudo systemctl start pbx`

2. **Firewall Blocking**
   - Check: `sudo ufw status`
   - Fix: `sudo ufw allow 9000/tcp`

3. **Browser Cache**
   - Fix: Press `Ctrl+Shift+R` (force refresh)

4. **Reverse Proxy Issues**
   - Check nginx: `sudo systemctl status nginx`
   - Check config: `/etc/nginx/sites-available/pbx`

5. **Database Connection**
   - Check: `sudo systemctl status postgresql`
   - Fix: `sudo systemctl start postgresql`

---

## Key Takeaways

### Prevention Strategies
1. **Browser Cache:** Use version parameters on CSS/JS files
2. **API Detection:** Smart port detection for reverse proxy scenarios
3. **Error Handling:** Validate responses before parsing
4. **Diagnostics:** Automatic connectivity testing on page load
5. **Security:** Always use `textContent` for user-facing messages

### Diagnostic Tools
1. **Status Check Page:** `/admin/status-check.html`
2. **Browser Console:** F12 → Console for detailed logs
3. **System Logs:** `sudo journalctl -u pbx -n 50`
4. **API Test:** `curl http://localhost:9000/api/status`

### Documentation
For current issues, always refer to:
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Main troubleshooting guide
- [LOGIN_CONNECTION_TROUBLESHOOTING.md](LOGIN_CONNECTION_TROUBLESHOOTING.md) - Login-specific issues
- [BROWSER_CACHE_FIX.md](BROWSER_CACHE_FIX.md) - Cache-related problems
- [REVERSE_PROXY_SETUP.md](REVERSE_PROXY_SETUP.md) - Proxy configuration

---

**Last Updated:** December 29, 2025  
**Purpose:** Historical reference for resolved issues  
**Note:** This document is for reference only. Current issues should be reported as GitHub issues.
