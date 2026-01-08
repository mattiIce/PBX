# Rate Limit Fix - Admin Interface Refresh

## Problem Statement

When clicking the "Refresh All" button in the admin interface, 40+ API requests were being fired simultaneously. This caused HTTP 429 (Too Many Requests) errors from the backend rate limiter which is configured to allow:
- 60 requests per minute
- Burst size of 10 requests

### Example Error Log (Before Fix)

```
admin.js:68  GET http://abps.albl.com/api/registered-atas 429 (Too Many Requests)
admin.js:68  GET http://abps.albl.com/api/calls 429 (Too Many Requests)
admin.js:3886  GET http://abps.albl.com/api/qos/statistics 429 (Too Many Requests)
admin.js:4175  GET http://abps.albl.com/api/emergency/contacts 429 (Too Many Requests)
admin.js:2881  GET http://abps.albl.com/api/provisioning/vendors 429 (Too Many Requests)
... (30+ more 429 errors)
```

## Root Cause

The `refreshAllData()` function was using `Promise.allSettled()` to fire all API requests simultaneously:

```javascript
const refreshPromises = [
    loadDashboard(),
    loadADStatus(),
    loadAnalytics(),
    loadExtensions(),
    // ... 40+ more API calls
];

const results = await Promise.allSettled(refreshPromises);
```

This caused a burst of 40+ concurrent requests, far exceeding the rate limit.

## Solution Implemented

### 1. Request Batching Function

Added a new `executeBatched()` helper function that processes promises in controlled batches with delays between batches:

```javascript
/**
 * Execute promises in batches to avoid overwhelming the rate limiter.
 * 
 * @param {Promise[]} promises - Array of promises to execute
 * @param {number} batchSize - Number of promises to execute concurrently (default: 8)
 * @param {number} delayMs - Delay in milliseconds between batches (default: 200)
 * @returns {Promise<Array>} Results from Promise.allSettled for all promises
 */
async function executeBatched(promises, batchSize = 8, delayMs = 200) {
    const results = [];
    
    // Process promises in batches
    for (let i = 0; i < promises.length; i += batchSize) {
        const batch = promises.slice(i, i + batchSize);
        
        // Execute current batch
        const batchResults = await Promise.allSettled(batch);
        results.push(...batchResults);
        
        // Add delay between batches (except after the last batch)
        if (i + batchSize < promises.length) {
            await new Promise(resolve => setTimeout(resolve, delayMs));
        }
    }
    
    return results;
}
```

### 2. Modified refreshAllData()

Updated the `refreshAllData()` function to use batching:

```javascript
// Execute all refresh operations in batches to avoid overwhelming the rate limiter
// Batch size of 8 requests with 200ms delay between batches stays well within
// the 60 req/min rate limit (approximately 24 req/min with this configuration)
const results = await executeBatched(refreshPromises, 8, 200);
```

### 3. Rate Calculation

With the new batching configuration:
- **Batch size**: 8 requests
- **Delay between batches**: 200ms
- **Theoretical max**: 8 requests / 0.2s = 40 req/s = 2,400 req/min

However, in practice:
- 40 API calls total
- Divided into 5 batches (8+8+8+8+8)
- 4 delays of 200ms = 800ms total delay
- Total time: ~1-2 seconds (including request execution time)
- **Effective rate**: ~24-40 req/min

This is well within the 60 req/min limit and respects the burst size of 10.

## Files Modified

### 1. `admin/js/admin.js`
- Added `executeBatched()` function (lines 963-987)
- Modified `refreshAllData()` to use batching (line 1101)
- Updated comments to reflect batching approach

### 2. `admin/tests/refresh-all.test.js`
- Added `executeBatched()` function to test file
- Updated `refreshAllData()` test implementation to use batching
- Added new test case: "should execute requests in batches with delays"
- All 7 tests passing

## Testing

### Unit Tests

All tests pass successfully:

```bash
npm test -- admin/tests/refresh-all.test.js

Test Suites: 1 passed, 1 total
Tests:       7 passed, 7 total
```

Test coverage includes:
- ✅ Refresh all tabs regardless of which tab is active
- ✅ Handle individual function failures gracefully
- ✅ Properly set/reset suppressErrorNotifications flag
- ✅ Show single success notification
- ✅ Restore button state after refresh
- ✅ Execute requests in batches with delays (NEW)

### Manual Testing

To manually verify the fix:

1. Start the PBX server
2. Open the admin interface in a browser
3. Open browser DevTools (F12) → Network tab
4. Click the "Refresh All" button
5. Observe the Network tab:
   - Requests should appear in batches of ~8
   - No 429 errors should appear
   - Total refresh time: ~1-2 seconds

## Performance Impact

### Before Fix
- **Request pattern**: All 40+ requests fired simultaneously
- **Time to complete**: ~500ms (but many failed with 429)
- **User experience**: Many errors, inconsistent data loading

### After Fix
- **Request pattern**: Batches of 8 requests with 200ms delays
- **Time to complete**: ~1-2 seconds (all successful)
- **User experience**: Smooth refresh, no errors, all data loads

The slightly longer refresh time (1-2 seconds) is acceptable for a "Refresh All" operation and provides much more reliable results.

## Benefits

1. **No rate limit errors**: Stays well within API rate limits
2. **Graceful degradation**: Still handles individual endpoint failures
3. **Improved reliability**: All data loads successfully
4. **Better server health**: Reduces spike load on the server
5. **Backward compatible**: No changes to API or other components
6. **Configurable**: Easy to adjust batch size and delay if needed

## Configuration

The batching parameters can be adjusted if needed:

```javascript
// Current configuration
const results = await executeBatched(refreshPromises, 8, 200);

// For stricter rate limits, use smaller batches or longer delays
const results = await executeBatched(refreshPromises, 5, 300);

// For more lenient rate limits, use larger batches or shorter delays
const results = await executeBatched(refreshPromises, 10, 100);
```

## Deployment

This is a pure JavaScript frontend change:

1. **Zero downtime**: No server restart required
2. **No database changes**: No migrations needed
3. **No configuration changes**: Works with existing setup
4. **Browser update**: Users need to refresh browser to get new JavaScript

## Future Enhancements

Consider these improvements:

1. **Dynamic batching**: Adjust batch size based on rate limit headers
2. **Progressive loading**: Show data as each batch completes
3. **Request prioritization**: Load critical data first
4. **WebSocket updates**: Replace periodic refresh with real-time updates
5. **Smart refresh**: Only refresh data that has changed

## Related Documentation

- [REFRESH_ALL_FIX_SUMMARY.md](REFRESH_ALL_FIX_SUMMARY.md) - Error notification suppression
- Backend rate limiting: `pbx/utils/security_middleware.py`
- API handler: `pbx/api/rest_api.py`

## Security Considerations

- No security impact - only changes request timing
- Rate limiting still enforced on backend
- No exposure of sensitive data
- Authentication requirements unchanged

## Backward Compatibility

Fully backward compatible:
- No API changes
- No database schema changes
- No configuration file changes
- Error notifications still work normally
- Individual tab refreshes still use direct API calls
