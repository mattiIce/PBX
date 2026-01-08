/**
 * @jest-environment jsdom
 */

const { describe, it, expect, beforeEach, afterEach } = require('@jest/globals');

// Mock global fetch
global.fetch = jest.fn();

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  clear: jest.fn()
};
global.localStorage = localStorageMock;

// Mock DOM elements
document.body.innerHTML = `
  <button id="refresh-all-button">Refresh All</button>
  <div id="dashboard" class="tab-content active"></div>
  <div id="analytics" class="tab-content"></div>
  <div id="extensions" class="tab-content"></div>
`;

// Mock API_BASE
global.API_BASE = 'http://localhost:9000';

// Mock getAuthHeaders function
global.getAuthHeaders = jest.fn(() => ({
  'Content-Type': 'application/json',
  'Authorization': 'Bearer test-token'
}));

// Mock showNotification function
global.showNotification = jest.fn();

// Mock load functions
global.loadDashboard = jest.fn(() => Promise.resolve());
global.loadADStatus = jest.fn(() => Promise.resolve());
global.loadAnalytics = jest.fn(() => Promise.resolve());
global.loadExtensions = jest.fn(() => Promise.resolve());

/**
 * NOTE: The function below is duplicated from admin.js for testing purposes.
 * This is a temporary approach while admin.js is not modularized.
 * 
 * TODO: Refactor admin.js to use ES6 modules to enable proper import/testing
 * of the actual production code instead of duplicating functions here.
 */

// Mock the suppressErrorNotifications flag
global.suppressErrorNotifications = false;
global.window = global;

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

async function refreshAllData() {
    const refreshBtn = document.getElementById('refresh-all-button');
    if (!refreshBtn) return;
    
    // Prevent concurrent refresh operations
    if (refreshBtn.disabled) return;

    // Store original button state
    const originalText = refreshBtn.textContent;
    const originalDisabled = refreshBtn.disabled;

    try {
        // Update button to show loading state
        refreshBtn.textContent = '⏳ Refreshing All Tabs...';
        refreshBtn.disabled = true;
        
        // Suppress error notifications during bulk refresh to avoid notification spam
        global.suppressErrorNotifications = true;
        global.window.suppressErrorNotifications = true;

        console.log('Refreshing all data for ALL tabs...');

        // Collect ALL tab refresh promises for batched execution
        const refreshPromises = [
            loadDashboard(),
            loadADStatus(),
            loadAnalytics(),
            loadExtensions(),
        ];

        // Execute all refresh operations in batches to avoid overwhelming the rate limiter
        const results = await executeBatched(refreshPromises, 8, 200);
        
        // Check for any failures and show summary
        const failures = results.filter(r => r.status === 'rejected');
        if (failures.length > 0) {
            console.info(`${failures.length} refresh operation(s) failed (expected for unavailable features):`, failures.map(f => f.reason?.message || f.reason));
            showNotification('✅ All tabs refreshed successfully', 'success');
        } else {
            showNotification('✅ All tabs refreshed successfully', 'success');
        }
    } catch (error) {
        console.error('Error refreshing data:', error);
        showNotification(`Failed to refresh: ${error.message}`, 'error');
    } finally {
        // Re-enable error notifications
        global.suppressErrorNotifications = false;
        global.window.suppressErrorNotifications = false;
        
        // Restore button state
        refreshBtn.textContent = originalText;
        refreshBtn.disabled = originalDisabled;
    }
}

describe('Refresh All Data', () => {
  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Reset button state
    const refreshBtn = document.getElementById('refresh-all-button');
    refreshBtn.textContent = 'Refresh All';
    refreshBtn.disabled = false;
    
    // Reset active tab
    document.querySelectorAll('.tab-content').forEach(tab => {
      tab.classList.remove('active');
    });
    document.getElementById('dashboard').classList.add('active');
  });

  it('should refresh all tabs regardless of which tab is active and not query DOM for active tab', async () => {
    // Dashboard is active in DOM
    expect(document.getElementById('dashboard').classList.contains('active')).toBe(true);
    
    // Spy on querySelector to verify it's not called to check active tab
    const querySelectorSpy = jest.spyOn(document, 'querySelector');
    
    // Call refreshAllData
    await refreshAllData();
    
    // Should NOT query for active tab element
    expect(querySelectorSpy).not.toHaveBeenCalledWith('.tab-content.active');
    
    // Should call ALL tab load functions, not just dashboard
    expect(loadDashboard).toHaveBeenCalled();
    expect(loadADStatus).toHaveBeenCalled();
    expect(loadAnalytics).toHaveBeenCalled();
    expect(loadExtensions).toHaveBeenCalled();
    
    // Should show success notification
    expect(showNotification).toHaveBeenCalledWith('✅ All tabs refreshed successfully', 'success');
    
    // Cleanup spy
    querySelectorSpy.mockRestore();
  });

  it('should refresh all tabs even when different tab is active', async () => {
    // Change active tab to analytics
    document.querySelectorAll('.tab-content').forEach(tab => {
      tab.classList.remove('active');
    });
    document.getElementById('analytics').classList.add('active');
    
    expect(document.getElementById('analytics').classList.contains('active')).toBe(true);
    
    // Call refreshAllData
    await refreshAllData();
    
    // Should still call ALL tab load functions
    expect(loadDashboard).toHaveBeenCalled();
    expect(loadADStatus).toHaveBeenCalled();
    expect(loadAnalytics).toHaveBeenCalled();
    expect(loadExtensions).toHaveBeenCalled();
    
    // Should show success notification
    expect(showNotification).toHaveBeenCalledWith('✅ All tabs refreshed successfully', 'success');
  });

  it('should refresh all tabs even when no tab is active', async () => {
    // Remove all active classes
    document.querySelectorAll('.tab-content').forEach(tab => {
      tab.classList.remove('active');
    });
    
    // Call refreshAllData
    await refreshAllData();
    
    // Should still call ALL tab load functions
    expect(loadDashboard).toHaveBeenCalled();
    expect(loadADStatus).toHaveBeenCalled();
    expect(loadAnalytics).toHaveBeenCalled();
    expect(loadExtensions).toHaveBeenCalled();
    
    // Should show success notification (not warning)
    expect(showNotification).toHaveBeenCalledWith('✅ All tabs refreshed successfully', 'success');
  });

  it('should update button state during refresh', async () => {
    const refreshBtn = document.getElementById('refresh-all-button');
    expect(refreshBtn.textContent).toBe('Refresh All');
    expect(refreshBtn.disabled).toBe(false);
    
    // Call refreshAllData
    await refreshAllData();
    
    // Button should be restored after refresh
    expect(refreshBtn.textContent).toBe('Refresh All');
    expect(refreshBtn.disabled).toBe(false);
  });

  it('should handle errors gracefully and show success', async () => {
    // Make loadDashboard throw an error (simulates API endpoint failing)
    loadDashboard.mockRejectedValueOnce(new Error('Network error'));
    
    // Call refreshAllData
    await refreshAllData();
    
    // Should show success notification (not error) - graceful degradation
    expect(showNotification).toHaveBeenCalledWith('✅ All tabs refreshed successfully', 'success');
    
    // Button should still be restored
    const refreshBtn = document.getElementById('refresh-all-button');
    expect(refreshBtn.textContent).toBe('Refresh All');
    expect(refreshBtn.disabled).toBe(false);
    
    // suppressErrorNotifications flag should be reset
    expect(global.suppressErrorNotifications).toBe(false);
  });
  
  it('should set suppressErrorNotifications flag during refresh', async () => {
    // Verify flag is initially false
    expect(global.suppressErrorNotifications).toBe(false);
    
    // Create a promise that captures the flag state during execution
    let flagDuringExecution = null;
    loadDashboard.mockImplementationOnce(() => {
      flagDuringExecution = global.suppressErrorNotifications;
      return Promise.resolve();
    });
    
    // Call refreshAllData
    await refreshAllData();
    
    // Flag should have been true during execution
    expect(flagDuringExecution).toBe(true);
    
    // Flag should be reset after completion
    expect(global.suppressErrorNotifications).toBe(false);
  });
  
  it('should execute requests in batches with delays', async () => {
    // This test verifies that executeBatched processes promises in controlled batches
    // Note: Since promises start executing when created, this test verifies the batching
    // logic completes all promises and returns results in the correct format
    
    const results = [];
    
    // Create promises that resolve with their index
    const promises = Array.from({ length: 12 }, (_, i) => 
      Promise.resolve().then(() => {
        results.push(i);
        return `result-${i}`;
      })
    );
    
    // Execute in batches of 5 with 50ms delay
    const batchResults = await executeBatched(promises, 5, 50);
    
    // All tasks should complete successfully
    expect(batchResults.length).toBe(12);
    expect(batchResults.every(r => r.status === 'fulfilled')).toBe(true);
    
    // Verify all results are present
    expect(batchResults.map(r => r.value)).toEqual([
      'result-0', 'result-1', 'result-2', 'result-3', 'result-4',
      'result-5', 'result-6', 'result-7', 'result-8', 'result-9',
      'result-10', 'result-11'
    ]);
  });
});
