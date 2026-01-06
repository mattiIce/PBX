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

let currentTab = null;

async function refreshAllData() {
    const refreshBtn = document.getElementById('refresh-all-button');
    if (!refreshBtn) return;

    // Store original button state
    const originalText = refreshBtn.textContent;
    const originalDisabled = refreshBtn.disabled;

    try {
        // Update button to show loading state
        refreshBtn.textContent = '⏳ Refreshing...';
        refreshBtn.disabled = true;

        console.log(`Refreshing all data for current tab: ${currentTab}`);

        // Refresh the current tab based on what's active
        // If currentTab is not set, try to detect it from the DOM
        let tabToRefresh = currentTab;
        if (!tabToRefresh) {
            // Find the active tab element in the DOM
            const activeTabElement = document.querySelector('.tab-content.active');
            if (activeTabElement) {
                tabToRefresh = activeTabElement.id;
                // Update currentTab to keep it in sync
                currentTab = tabToRefresh;
                console.log(`Detected active tab from DOM: ${tabToRefresh}`);
            } else {
                showNotification('No active tab to refresh', 'warning');
                return;
            }
        }

        // Execute all load functions for the current tab
        switch(tabToRefresh) {
            case 'dashboard':
                await loadDashboard();
                await loadADStatus();
                break;
            case 'analytics':
                await loadAnalytics();
                break;
            case 'extensions':
                await loadExtensions();
                break;
            default:
                console.log(`No specific refresh handler for tab: ${tabToRefresh}`);
                showNotification(`No data to refresh for ${tabToRefresh}`, 'info');
                return;
        }

        showNotification('✅ All data refreshed successfully', 'success');
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
    
    // Reset currentTab
    currentTab = null;
    
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

  it('should detect active tab from DOM when currentTab is null', async () => {
    // currentTab is null (not set during initialization)
    expect(currentTab).toBeNull();
    
    // Call refreshAllData
    await refreshAllData();
    
    // Should detect 'dashboard' as active tab
    expect(currentTab).toBe('dashboard');
    
    // Should call dashboard load functions
    expect(loadDashboard).toHaveBeenCalled();
    expect(loadADStatus).toHaveBeenCalled();
    
    // Should show success notification
    expect(showNotification).toHaveBeenCalledWith('✅ All data refreshed successfully', 'success');
  });

  it('should use currentTab when it is already set', async () => {
    // Set currentTab to analytics
    currentTab = 'analytics';
    
    // Change active tab in DOM to dashboard (but currentTab should take precedence)
    document.getElementById('dashboard').classList.add('active');
    
    // Call refreshAllData
    await refreshAllData();
    
    // Should use currentTab value
    expect(currentTab).toBe('analytics');
    
    // Should call analytics load function
    expect(loadAnalytics).toHaveBeenCalled();
    
    // Should NOT call dashboard functions
    expect(loadDashboard).not.toHaveBeenCalled();
    expect(loadADStatus).not.toHaveBeenCalled();
  });

  it('should show warning when no active tab found in DOM', async () => {
    // Remove all active classes
    document.querySelectorAll('.tab-content').forEach(tab => {
      tab.classList.remove('active');
    });
    
    // currentTab is null
    currentTab = null;
    
    // Call refreshAllData
    await refreshAllData();
    
    // Should show warning notification
    expect(showNotification).toHaveBeenCalledWith('No active tab to refresh', 'warning');
    
    // Should NOT call any load functions
    expect(loadDashboard).not.toHaveBeenCalled();
    expect(loadAnalytics).not.toHaveBeenCalled();
    expect(loadExtensions).not.toHaveBeenCalled();
  });

  it('should update button state during refresh', async () => {
    currentTab = 'dashboard';
    
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
    currentTab = 'dashboard';
    
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
