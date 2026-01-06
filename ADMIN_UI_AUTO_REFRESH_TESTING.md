# Manual Testing Plan for Auto-Refresh Fix

## Test Scenario 1: Dashboard Tab (Already Had Auto-Refresh)
**Expected Behavior:**
1. User loads admin panel → `initializeUserContext()` called
2. For admin user: `showTab('dashboard')` is called
3. `setupAutoRefresh('dashboard')` sets up interval
4. `loadDashboard()` called immediately
5. Every 10 seconds, `loadDashboard()` called again via interval
6. Console logs: "Auto-refreshing tab: dashboard"

**Verification:**
- Check browser console for auto-refresh messages
- Watch network tab for `/api/status` calls every 10 seconds
- Verify dashboard stats update without manual refresh

## Test Scenario 2: Analytics Tab (Newly Added)
**Expected Behavior:**
1. User clicks Analytics tab → `showTab('analytics')` called
2. Previous interval (dashboard) cleared
3. `setupAutoRefresh('analytics')` sets up new interval
4. `loadAnalytics()` called immediately
5. Every 10 seconds, `loadAnalytics()` called again
6. Console logs: "Auto-refreshing tab: analytics"

**Verification:**
- Switch to Analytics tab
- Watch for `/api/analytics` API calls every 10 seconds
- Verify charts and stats update automatically

## Test Scenario 3: Emergency Tab (Wrapper Function)
**Expected Behavior:**
1. User clicks Emergency tab → `showTab('emergency')` called
2. `setupAutoRefresh('emergency')` sets up interval
3. `refreshEmergencyTab()` wrapper called, which calls:
   - `loadEmergencyContacts()`
   - `loadEmergencyHistory()`
4. Both functions called every 10 seconds
5. Console logs: "Auto-refreshing tab: emergency"

**Verification:**
- Switch to Emergency tab
- Watch for TWO API calls every 10 seconds:
  - `/api/emergency/contacts`
  - `/api/emergency/history`

## Test Scenario 4: Auto-Attendant Tab (Should NOT Auto-Refresh)
**Expected Behavior:**
1. User clicks Auto-Attendant tab
2. `setupAutoRefresh('auto-attendant')` called
3. Tab NOT in autoRefreshTabs object
4. Console logs: "Tab auto-attendant does not support auto-refresh"
5. No interval set up
6. Data loaded once via `loadAutoAttendantConfig()`

**Verification:**
- Switch to Auto-Attendant tab
- Verify only ONE API call made (initial load)
- No subsequent API calls every 10 seconds
- Console should show "does not support auto-refresh"

## Test Scenario 5: Tab Switching
**Expected Behavior:**
1. User on Dashboard (auto-refreshing)
2. Switch to Analytics
3. Console logs: "Clearing existing auto-refresh interval for tab: dashboard"
4. Dashboard interval stopped
5. New interval created for Analytics
6. Only Analytics refreshes, not Dashboard

**Verification:**
- Start on Dashboard tab
- Watch API calls to /api/status every 10 seconds
- Switch to Analytics tab
- Verify /api/status calls STOP
- Verify /api/analytics calls START every 10 seconds
- Only ONE tab auto-refreshing at a time

## Test Scenario 6: Error Handling
**Expected Behavior:**
1. User on Extensions tab (auto-refreshing)
2. Backend server goes down
3. Auto-refresh tries to call `/api/extensions`
4. Request fails
5. Error logged to console
6. Auto-refresh CONTINUES (doesn't stop)
7. When server comes back up, auto-refresh works again

**Verification:**
- Have Extensions tab open
- Stop the PBX server
- Watch console for errors every 10 seconds
- Start PBX server again
- Verify auto-refresh resumes successfully

## Browser Console Checks

Expected log pattern for a tab with auto-refresh:
```
showTab called with: dashboard
Setting up auto-refresh for tab: dashboard (interval: 10000ms)
Auto-refresh interval ID: 123
Loading dashboard data from API...
Dashboard data loaded: {...}
[10 seconds later]
Auto-refreshing tab: dashboard
Loading dashboard data from API...
Dashboard data loaded: {...}
```

Expected log pattern for tab WITHOUT auto-refresh:
```
showTab called with: config
Tab config does not support auto-refresh
Loading config...
[No further messages]
```

## Network Tab Verification

For tabs with auto-refresh, should see API calls every 10 seconds:
- Dashboard: GET /api/status every 10s
- Extensions: GET /api/extensions every 10s
- Phones: GET /api/phones every 10s
- ATAs: GET /api/atas every 10s
- Calls: GET /api/calls every 10s
- QoS: GET /api/qos/metrics every 10s
- Analytics: GET /api/analytics every 10s
- Voicemail: GET /api/voicemail/* every 10s
- Emergency: GET /api/emergency/contacts + /api/emergency/history every 10s
- Hot Desking: GET /api/hotdesk/sessions every 10s
- Callback Queue: (check actual endpoint)
- Fraud Detection: (check actual endpoint)

## Performance Checks

Monitor over 5 minutes:
1. Memory usage should remain stable (no leaks)
2. Only one setInterval active per browser tab
3. Network activity only for currently displayed tab
4. CPU usage should be minimal (< 5%)

## Edge Cases

1. **Rapid Tab Switching**: Switch tabs quickly multiple times
   - Should cleanly clear old intervals
   - No memory leaks
   - No overlapping auto-refreshes

2. **Browser Tab Inactive**: Put browser tab in background
   - Auto-refresh continues (browsers may throttle intervals)
   - No errors when tab becomes active again

3. **Network Offline**: Disconnect network
   - Errors logged gracefully
   - Auto-refresh continues trying
   - Reconnect works smoothly
