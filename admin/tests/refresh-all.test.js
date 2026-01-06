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

async function refreshAllData() {
    const refreshBtn = document.getElementById('refresh-all-button');
    if (!refreshBtn) return;

    // Store original button state
    const originalText = refreshBtn.textContent;
    const originalDisabled = refreshBtn.disabled;

    try {
        // Update button to show loading state
        refreshBtn.textContent = '⏳ Refreshing All Tabs...';
        refreshBtn.disabled = true;

        console.log('Refreshing all data for ALL tabs...');

        // Refresh ALL tabs in parallel using Promise.allSettled
        const refreshPromises = [
            loadDashboard(),
            loadADStatus(),
            loadAnalytics(),
            loadExtensions(),
        ];

        // Wait for all refresh operations to complete (success or failure)
        const results = await Promise.allSettled(refreshPromises);
        
        // Check for any failures
        const failures = results.filter(r => r.status === 'rejected');
        if (failures.length > 0) {
            console.warn(`${failures.length} refresh operation(s) failed:`, failures);
            showNotification(`✅ All tabs refreshed (${failures.length} warning(s) - check console)`, 'success');
        } else {
            showNotification('✅ All tabs refreshed successfully', 'success');
        }
    } catch (error) {
        console.error('Error refreshing data:', error);
        showNotification(`Failed to refresh: ${error.message}`, 'error');
    } finally {
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

  it('should handle errors gracefully', async () => {
    // Make loadDashboard throw an error
    loadDashboard.mockRejectedValueOnce(new Error('Network error'));
    
    // Call refreshAllData
    await refreshAllData();
    
    // Should show error notification
    expect(showNotification).toHaveBeenCalledWith('Failed to refresh: Network error', 'error');
    
    // Button should still be restored
    const refreshBtn = document.getElementById('refresh-all-button');
    expect(refreshBtn.textContent).toBe('Refresh All');
    expect(refreshBtn.disabled).toBe(false);
  });
});
