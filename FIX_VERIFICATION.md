# Admin Portal Connection Error - Fix Verification

## Problem
Users experienced a "connection error" when trying to log into the admin portal.

## Root Cause
Content-Security-Policy (CSP) header had a typo in `pbx/api/rest_api.py`:
- **Line 128**: `script-src 'sel' 'unsafe-inline' ...` (should be `'self'`)
- **Line 129**: `style-src 'sel' 'unsafe-inline'` (should be `'self'`)

The typo `'sel'` instead of `'self'` caused browsers to:
1. Block inline JavaScript from executing
2. Block inline styles from applying
3. Prevent the login page from functioning properly
4. Display "connection error" to users

## Fix Applied
Changed `'sel'` to `'self'` in both lines of the CSP header.

## Testing Instructions

### 1. Automated Tests
Run the CSP header test:
```bash
python -m unittest tests.test_csp_header -v
```

All tests should pass.

### 2. Manual Testing (Recommended)
1. Start the PBX server:
   ```bash
   python main.py
   ```

2. Open a browser and navigate to:
   ```
   http://localhost:9000/admin/login.html
   ```

3. Open browser Developer Tools (F12)

4. Check the **Console** tab:
   - Before fix: CSP violations like "Refused to execute inline script because it violates CSP directive 'script-src 'sel' ...'"
   - After fix: No CSP violations

5. Check the **Network** tab:
   - Look for the login.html response
   - Click on it and view Headers
   - Find "Content-Security-Policy" header
   - Verify it contains `'self'` not `'sel'`

6. Test login functionality:
   - Enter extension number (e.g., 1001)
   - Enter password (voicemail PIN)
   - Click Login
   - Should successfully log in to admin dashboard

### 3. Browser Console Test
In browser console (F12), you can check the CSP:
```javascript
// Should show the correct CSP with 'self' not 'sel'
fetch('http://localhost:9000/api/status')
  .then(response => {
    console.log('CSP:', response.headers.get('Content-Security-Policy'));
  });
```

## Expected Behavior After Fix
- Login page JavaScript executes normally
- Login page styles apply correctly
- No CSP violations in browser console
- Login functionality works as expected
- Users can successfully authenticate and access the admin portal

## Related Files
- **Fixed**: `pbx/api/rest_api.py` (lines 128-129)
- **Test**: `tests/test_csp_header.py`
- **Affected**: `admin/login.html`, `admin/js/admin.js`
