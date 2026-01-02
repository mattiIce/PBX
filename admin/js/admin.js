// Constants for API endpoint detection
const STANDARD_HTTP_PORT = '80';
const STANDARD_HTTPS_PORT = '443';
const API_PORT = '9000';

// API Base URL
// If the page is served from the API server, use same origin
// Otherwise, construct URL from hostname and default API port
function getAPIBase() {
    // Check for meta tag override first
    const apiMeta = document.querySelector('meta[name="api-base-url"]');
    if (apiMeta && apiMeta.content) {
        return apiMeta.content;
    }
    
    // If we're on the API port, use current origin
    if (window.location.port === API_PORT) {
        return window.location.origin;
    }
    
    // If accessed through reverse proxy or standard HTTP/HTTPS ports,
    // try same origin first (API should be proxied)
    if (window.location.port === '' || 
        window.location.port === STANDARD_HTTP_PORT || 
        window.location.port === STANDARD_HTTPS_PORT) {
        return window.location.origin;
    }
    
    // Fallback: use current hostname with API port (direct API access)
    const protocol = window.location.protocol;
    const hostname = window.location.hostname || 'localhost';
    return `${protocol}//${hostname}:${API_PORT}`;
}

const API_BASE = getAPIBase();
console.log('API Base URL:', API_BASE);

// Constants
const LOGIN_PAGE_PATH = '/admin/login.html';
const CONFIG_SAVE_SUCCESS_MESSAGE = 'Configuration saved successfully. Restart may be required for some changes.';
const EXTENSION_LOAD_TIMEOUT = 10000; // 10 seconds
const DEFAULT_FETCH_TIMEOUT = 30000; // 30 seconds for general requests
const AD_SYNC_TIMEOUT = 60000; // 60 seconds for AD sync (can take longer with large directories)
const AUTO_REFRESH_INTERVAL_MS = 10000; // 10 seconds - auto-refresh interval for data tabs

// State
let currentExtensions = [];
let currentUser = null; // Stores current extension info including is_admin status
let currentTab = null; // Track the currently active tab
let autoRefreshInterval = null; // Interval for auto-refreshing tab data

// Helper function to fetch with timeout
async function fetchWithTimeout(url, options = {}, timeout = DEFAULT_FETCH_TIMEOUT) {
    // Prevent caller from passing their own signal which would conflict with timeout
    if (options.signal) {
        throw new Error('fetchWithTimeout does not support custom abort signals. Use the timeout parameter instead.');
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        return response;
    } catch (error) {
        if (error.name === 'AbortError') {
            throw new Error('Request timed out');
        }
        throw error;
    } finally {
        // Always clear timeout to prevent memory leaks
        clearTimeout(timeoutId);
    }
}

// Error Display Configuration
const ERROR_DISPLAY_CONFIG = {
    enabled: true,
    displayTime: 8000, // 8 seconds
    maxErrors: 5,
    showStackTrace: true
};

// Error queue
let errorQueue = [];

// HTML escape function to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Display error in a visible notification
function displayError(error, context = '') {
    if (!ERROR_DISPLAY_CONFIG.enabled) return;

    const errorId = 'error-' + Date.now();
    const errorMessage = error.message || error.toString();
    const errorStack = error.stack || '';

    // Add to queue
    errorQueue.push({
        id: errorId,
        message: errorMessage,
        context: context,
        stack: errorStack,
        timestamp: new Date()
    });

    // Keep only max errors
    if (errorQueue.length > ERROR_DISPLAY_CONFIG.maxErrors) {
        errorQueue.shift();
    }

    // Create error notification element
    const errorDiv = document.createElement('div');
    errorDiv.id = errorId;
    errorDiv.className = 'error-notification';
    errorDiv.style.cssText = `
        position: fixed;
        top: 70px;
        right: 20px;
        max-width: 450px;
        background: #f44336;
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
        font-family: monospace;
        font-size: 13px;
        line-height: 1.4;
    `;

    let html = `
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
            <strong style="font-size: 16px;">❌ JavaScript Error</strong>
            <button id="close-${errorId}"
                    style="background: none; border: none; color: white; font-size: 20px; cursor: pointer; padding: 0; margin-left: 10px;">
                ×
            </button>
        </div>
    `;

    if (context) {
        html += `<div style="margin-bottom: 5px;"><strong>Context:</strong> ${escapeHtml(context)}</div>`;
    }

    html += `<div style="margin-bottom: 5px;"><strong>Message:</strong> ${escapeHtml(errorMessage)}</div>`;

    if (ERROR_DISPLAY_CONFIG.showStackTrace && errorStack) {
        html += `
            <details style="margin-top: 10px; cursor: pointer;">
                <summary style="font-weight: bold; margin-bottom: 5px;">Stack Trace (click to expand)</summary>
                <pre style="background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 11px; margin: 5px 0 0 0;">${escapeHtml(errorStack)}</pre>
            </details>
        `;
    }

    html += `
        <div style="margin-top: 10px; font-size: 11px; opacity: 0.9;">
            💡 Tip: Press F12 to open browser console for more details
        </div>
    `;

    errorDiv.innerHTML = html;

    // Add click handler for close button using event listener (not inline onclick)
    const closeBtn = errorDiv.querySelector(`#close-${errorId}`);
    if (closeBtn) {
        closeBtn.addEventListener('click', () => errorDiv.remove());
    }

    // Add to page
    document.body.appendChild(errorDiv);

    // Auto-remove after configured time
    setTimeout(() => {
        if (document.getElementById(errorId)) {
            errorDiv.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => errorDiv.remove(), 300);
        }
    }, ERROR_DISPLAY_CONFIG.displayTime);

    // Also log to console
    console.error(`[${context || 'Error'}]`, errorMessage);
    if (errorStack) {
        console.error('Stack trace:', errorStack);
    }
}

// Global error handler
window.addEventListener('error', function(event) {
    displayError(event.error || new Error(event.message), 'Global Error Handler');
});

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', function(event) {
    // Check if event.reason is already an Error object
    const error = event.reason instanceof Error ? event.reason : new Error(String(event.reason));
    displayError(error, 'Unhandled Promise Rejection');
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(500px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(500px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Helper function to get authentication headers
function getAuthHeaders() {
    const token = localStorage.getItem('pbx_token');
    const headers = {
        'Content-Type': 'application/json'
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', async function() {
    console.log('DOMContentLoaded event fired - starting initialization');
    
    // Initialize user context first (async) - this will call showTab() when ready
    await initializeUserContext();
    console.log('User context initialization awaited');
    
    // Then initialize other components
    console.log('Initializing tabs, forms, and logout');
    initializeTabs();
    initializeForms();
    initializeLogout();
    checkConnection();

    // Auto-refresh every 10 seconds
    setInterval(checkConnection, 10000);
    
    console.log('Page initialization complete');
});

// User Context Management
async function initializeUserContext() {
    console.log('Initializing user context...');
    
    // Check for authentication token first
    const token = localStorage.getItem('pbx_token');

    if (!token) {
        // No token - redirect to login page
        console.log('No authentication token found, redirecting to login...');
        window.location.replace(LOGIN_PAGE_PATH);
        return;
    }

    // Verify token is still valid by making an authenticated request
    try {
        const response = await fetchWithTimeout(`${API_BASE}/api/extensions`, {
            headers: getAuthHeaders()
        }, 5000); // Short timeout for auth check

        if (response.status === 401 || response.status === 403) {
            // Token is invalid or expired - redirect to login
            console.log('Authentication token is invalid, redirecting to login...');
            localStorage.removeItem('pbx_token');
            localStorage.removeItem('pbx_extension');
            localStorage.removeItem('pbx_is_admin');
            localStorage.removeItem('pbx_name');
            window.location.replace(LOGIN_PAGE_PATH);
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        console.error('Error verifying authentication:', error);
        // If we can't verify auth (server down), show error but allow page to load
        showNotification('Unable to verify authentication - server may be starting up', 'error');
    }

    // Get user info from localStorage (set during login)
    const extensionNumber = localStorage.getItem('pbx_extension');
    const isAdmin = localStorage.getItem('pbx_is_admin') === 'true';
    const name = localStorage.getItem('pbx_name') || 'User';

    if (!extensionNumber) {
        // No extension stored - redirect to login
        console.log('No extension number found, redirecting to login...');
        window.location.replace(LOGIN_PAGE_PATH);
        return;
    }

    // Set current user from stored data
    currentUser = {
        number: extensionNumber,
        is_admin: isAdmin,
        name: name
    };

    console.log('User context initialized:', currentUser);

    // Apply role-based UI filtering
    applyRoleBasedUI();

    // Load initial content based on role
    if (currentUser.is_admin) {
        console.log('Admin user - showing dashboard tab');
        showTab('dashboard');
    } else {
        // For regular users, show phone tab by default
        console.log('Regular user - showing webrtc-phone tab');
        showTab('webrtc-phone');
    }
    
    console.log('User context initialization complete');
}

function showExtensionSelectionModal() {
    // Create a simple modal for extension selection
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    modal.innerHTML = `
        <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; text-align: center;">
            <h2 style="margin-top: 0;">📞 Select Your Extension</h2>
            <p>Please enter your extension number to continue:</p>
            <input type="text" id="ext-input" placeholder="Extension (e.g., 1001)"
                   style="width: 100%; padding: 10px; font-size: 16px; margin: 10px 0; text-align: center; border: 2px solid #ddd; border-radius: 4px;"
                   pattern="[0-9]+" maxlength="6">
            <div style="margin-top: 20px;">
                <button id="ext-submit" style="padding: 10px 30px; font-size: 16px; background: #2196f3; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    Continue
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    const input = document.getElementById('ext-input');
    const submitBtn = document.getElementById('ext-submit');

    // Focus on input
    input.focus();

    // Handle submit
    const handleSubmit = () => {
        const extension = input.value.trim();
        if (extension) {
            // Update URL and reload
            const newUrl = new URL(window.location.href);
            newUrl.searchParams.set('ext', extension);
            window.location.href = newUrl.toString();
        }
    };

    submitBtn.addEventListener('click', handleSubmit);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSubmit();
        }
    });
}

function applyRoleBasedUI() {
    const isAdmin = currentUser?.is_admin || false;

    // Define admin-only tabs
    const adminOnlyTabs = [
        'dashboard', 'analytics', 'extensions', 'phones',
        'provisioning', 'auto-attendant', 'calls',
        'qos', 'emergency', 'codecs', 'config'
    ];

    // Define user-accessible tabs (phone and voicemail)
    const userTabs = ['webrtc-phone', 'voicemail'];

    if (!isAdmin) {
        // Hide admin-only tabs for regular users
        adminOnlyTabs.forEach(tabName => {
            const tabButton = document.querySelector(`[data-tab="${tabName}"]`);
            if (tabButton) {
                tabButton.style.display = 'none';
            }
        });

        // Hide admin-only sidebar sections
        const sidebarSections = document.querySelectorAll('.sidebar-section');
        sidebarSections.forEach(section => {
            const sectionTitle = section.querySelector('.sidebar-section-title');
            // Hide sections that only contain admin tabs
            const buttons = section.querySelectorAll('.tab-button');
            const allHidden = Array.from(buttons).every(btn => btn.style.display === 'none');
            if (allHidden && sectionTitle) {
                section.style.display = 'none';
            }
        });

        // Update header to show non-admin status
        const header = document.querySelector('header h1');
        if (header) {
            header.innerHTML = `📞 Warden VoIP User Panel - Extension ${currentUser.number}`;
        }

        // Show info banner for non-admin users
        showNonAdminBanner();
    } else {
        // Update header to show admin status
        const header = document.querySelector('header h1');
        if (header) {
            header.innerHTML = `📞 Warden VoIP Admin Dashboard - ${currentUser.name} (${currentUser.number}) 👑`;
        }
    }

    // Update license management visibility (only for extension 9322)
    updateLicenseManagementVisibility();
}

function showNonAdminBanner() {
    const mainContent = document.querySelector('.main-content');
    if (!mainContent) return;

    // Check if banner already exists
    if (document.getElementById('non-admin-info-banner')) return;

    const banner = document.createElement('div');
    banner.id = 'non-admin-info-banner';
    banner.className = 'info-box';
    banner.style.cssText = 'margin-bottom: 20px; background: #e3f2fd; border-left: 4px solid #2196f3;';
    banner.innerHTML = `
        <p style="margin: 0; font-size: 14px;">
            ℹ️ <strong>Welcome, ${currentUser.name || currentUser.number}!</strong>
            You have access to the <strong>📞 Phone</strong> and <strong>📧 Voicemail</strong> features.
            ${currentUser.email ? `<br>Email: ${currentUser.email}` : ''}
        </p>
    `;

    // Insert banner at the top of main content, before the feature info banner
    const featureBanner = document.getElementById('feature-info-banner');
    if (featureBanner) {
        featureBanner.parentNode.insertBefore(banner, featureBanner);
    } else {
        mainContent.insertBefore(banner, mainContent.firstChild);
    }
}

function initializeLogout() {
    const logoutButton = document.getElementById('logout-button');
    if (!logoutButton) return;

    logoutButton.addEventListener('click', async function() {
        // Get token before clearing it
        const token = localStorage.getItem('pbx_token');

        // Clear local storage
        localStorage.removeItem('pbx_token');
        localStorage.removeItem('pbx_extension');
        localStorage.removeItem('pbx_is_admin');
        localStorage.removeItem('pbx_name');
        localStorage.removeItem('pbx_current_extension');

        // Optionally call logout endpoint
        try {
            if (token) {
                await fetch(`${API_BASE}/api/auth/logout`, {
                    method: 'POST',
                    headers: getAuthHeaders()
                });
            }
        } catch (error) {
            console.error('Logout API error:', error);
        }

        // Redirect to login page
        window.location.href = LOGIN_PAGE_PATH;
    });
}

// Tab Management
function initializeTabs() {
    console.log('Initializing tab click handlers');
    const tabButtons = document.querySelectorAll('.tab-button');
    console.log(`Found ${tabButtons.length} tab buttons`);

    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            console.log(`Tab button clicked: ${tabName}`);
            showTab(tabName);
        });
    });
}

// Setup auto-refresh for tabs that need periodic data updates
function setupAutoRefresh(tabName) {
    // Clear any existing auto-refresh interval
    if (autoRefreshInterval) {
        console.log(`Clearing existing auto-refresh interval for tab: ${currentTab}`);
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }

    // Define which tabs should auto-refresh and their refresh functions
    const autoRefreshTabs = {
        'extensions': loadExtensions,
        'phones': loadRegisteredPhones,
        'dashboard': loadDashboard,
        'calls': loadCalls,
        'voicemail': loadVoicemailTab
    };

    // If the current tab supports auto-refresh, set it up
    if (autoRefreshTabs[tabName]) {
        console.log(`Setting up auto-refresh for tab: ${tabName} (interval: ${AUTO_REFRESH_INTERVAL_MS}ms)`);
        autoRefreshInterval = setInterval(() => {
            console.log(`Auto-refreshing tab: ${tabName}`);
            try {
                const refreshFunction = autoRefreshTabs[tabName];
                if (typeof refreshFunction === 'function') {
                    refreshFunction();
                } else {
                    console.error(`Auto-refresh function for ${tabName} is not a function:`, refreshFunction);
                }
            } catch (error) {
                console.error(`Error during auto-refresh of ${tabName}:`, error);
                // If error is auth-related, user will be redirected to login
                // Otherwise, continue with auto-refresh on next interval
                if (error.message && error.message.includes('401')) {
                    console.warn('Authentication error during auto-refresh - user may need to re-login');
                }
            }
        }, AUTO_REFRESH_INTERVAL_MS);
        console.log(`Auto-refresh interval ID: ${autoRefreshInterval}`);
    } else {
        console.log(`Tab ${tabName} does not support auto-refresh`);
    }
}

function showTab(tabName) {
    console.log(`showTab called with: ${tabName}`);
    
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active from all buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });

    // Show selected tab
    const tabElement = document.getElementById(tabName);
    if (!tabElement) {
        console.error(`⚠️ CRITICAL: Tab element with id '${tabName}' not found in DOM`);
        console.error('This may indicate a UI template issue or incorrect tab name');
        console.error(`Current tab name: "${tabName}"`);
        // Still update currentTab and setup auto-refresh even if element not found
        // This ensures auto-refresh works even if there are DOM issues
        // But log this as a critical issue that should be investigated
    } else {
        tabElement.classList.add('active');
        const tabButton = document.querySelector(`[data-tab="${tabName}"]`);
        if (tabButton) {
            tabButton.classList.add('active');
        } else {
            console.warn(`Tab button for '${tabName}' not found`);
        }
    }

    // Update current tab and setup auto-refresh
    // This happens regardless of whether the tab element was found
    currentTab = tabName;
    setupAutoRefresh(tabName);

    // Load data for the tab
    switch(tabName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'analytics':
            loadAnalytics();
            break;
        case 'extensions':
            loadExtensions();
            break;
        case 'phones':
            loadRegisteredPhones();
            break;
        case 'provisioning':
            loadProvisioning();
            break;
        case 'auto-attendant':
            loadAutoAttendantConfig();
            break;
        case 'voicemail':
            loadVoicemailTab();
            break;
        case 'paging':
            loadPagingData();
            break;
        case 'calls':
            loadCalls();
            break;
        case 'config':
            loadConfig();
            break;
        case 'features-status':
            loadFeaturesStatus();
            break;
        case 'webrtc-phone':
            loadWebRTCPhoneConfig();
            break;
        case 'license-management':
            initLicenseManagement();
            break;
        case 'qos':
            loadQoSMetrics();
            break;
        case 'emergency':
            loadEmergencyContacts();
            loadEmergencyHistory();
            break;
        case 'codecs':
            loadCodecStatus();
            loadDTMFConfig();
            break;
        case 'sip-trunks':
            loadSIPTrunks();
            loadTrunkHealth();
            break;
        case 'least-cost-routing':
            loadLCRRates();
            loadLCRStatistics();
            break;
        case 'find-me-follow-me':
            loadFMFMExtensions();
            break;
        case 'time-routing':
            loadTimeRoutingRules();
            break;
        case 'webhooks':
            loadWebhooks();
            break;
        case 'hot-desking':
            loadHotDeskSessions();
            break;
        case 'recording-retention':
            loadRetentionPolicies();
            break;
        case 'jitsi-integration':
            if (typeof loadJitsiConfig === 'function') {
                loadJitsiConfig();
            }
            break;
        case 'matrix-integration':
            if (typeof loadMatrixConfig === 'function') {
                loadMatrixConfig();
            }
            break;
        case 'espocrm-integration':
            if (typeof loadEspoCRMConfig === 'function') {
                loadEspoCRMConfig();
            }
            break;
        case 'click-to-dial':
            if (typeof loadClickToDialTab === 'function') {
                loadClickToDialTab();
            }
            break;
        case 'fraud-detection':
            if (typeof loadFraudDetectionData === 'function') {
                loadFraudDetectionData();
            }
            break;
        case 'nomadic-e911':
            if (typeof loadNomadicE911Data === 'function') {
                loadNomadicE911Data();
            }
            break;
        case 'callback-queue':
            if (typeof loadCallbackQueue === 'function') {
                loadCallbackQueue();
            }
            break;
        case 'mobile-push':
            if (typeof loadMobilePushConfig === 'function') {
                loadMobilePushConfig();
            }
            break;
        case 'recording-announcements':
            if (typeof loadRecordingAnnouncements === 'function') {
                loadRecordingAnnouncements();
            }
            break;
        case 'speech-analytics':
            if (typeof loadSpeechAnalyticsConfigs === 'function') {
                loadSpeechAnalyticsConfigs();
            }
            break;
        case 'compliance':
            if (typeof loadComplianceData === 'function') {
                loadComplianceData();
            }
            break;
        case 'crm-integrations':
            if (typeof loadCRMActivityLog === 'function') {
                loadCRMActivityLog();
            }
            break;
        case 'opensource-integrations':
            if (typeof loadOpenSourceIntegrations === 'function') {
                loadOpenSourceIntegrations();
            }
            break;
    }
}

// Make switchTab available globally
window.switchTab = showTab;

// Connection Check
async function checkConnection() {
    const statusBadge = document.getElementById('connection-status');
    
    // Always ensure the status badge exists before trying to update it
    if (!statusBadge) {
        console.error('Connection status badge element not found');
        return;
    }
    
    try {
        const response = await fetchWithTimeout(`${API_BASE}/api/status`, {
            headers: getAuthHeaders()
        }, 5000);

        if (response.ok) {
            statusBadge.textContent = '✓ Connected';
            statusBadge.classList.remove('disconnected');
            statusBadge.classList.add('connected');
        } else {
            throw new Error('Connection failed');
        }
    } catch (error) {
        console.error('Connection check failed:', error);
        statusBadge.textContent = '✗ Disconnected';
        statusBadge.classList.remove('connected');
        statusBadge.classList.add('disconnected');
    }
}

// Dashboard Functions
async function loadDashboard() {
    try {
        console.log('Loading dashboard data from API...');
        const response = await fetchWithTimeout(`${API_BASE}/api/status`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Dashboard data loaded:', data);

        document.getElementById('stat-extensions').textContent = data.registered_extensions || 0;
        document.getElementById('stat-calls').textContent = data.active_calls || 0;
        document.getElementById('stat-total-calls').textContent = data.total_calls || 0;
        document.getElementById('stat-recordings').textContent = data.active_recordings || 0;

        const systemStatus = document.getElementById('system-status');
        if (systemStatus) {
            systemStatus.textContent = `System: ${data.running ? 'Running' : 'Stopped'}`;
            systemStatus.classList.remove('connected', 'disconnected');
            systemStatus.classList.add('status-badge', data.running ? 'connected' : 'disconnected');
        }

        // Load AD integration status
        loadADStatus();
    } catch (error) {
        console.error('Error loading dashboard:', error);
        
        // Set error state for stats
        document.getElementById('stat-extensions').textContent = 'Error';
        document.getElementById('stat-calls').textContent = 'Error';
        document.getElementById('stat-total-calls').textContent = 'Error';
        document.getElementById('stat-recordings').textContent = 'Error';
        
        const systemStatus = document.getElementById('system-status');
        if (systemStatus) {
            systemStatus.textContent = 'System: Error';
            systemStatus.classList.remove('connected', 'disconnected');
            systemStatus.classList.add('status-badge', 'disconnected');
        }
        
        showNotification(`Failed to load dashboard: ${error.message}`, 'error');
    }
}

function refreshDashboard() {
    loadDashboard();
    showNotification('Dashboard refreshed', 'success');
}

// AD Integration Functions
async function loadADStatus() {
    try {
        const response = await fetchWithTimeout(`${API_BASE}/api/integrations/ad/status`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();

        // Update status badge
        const statusBadge = document.getElementById('ad-status-badge');
        if (data.enabled) {
            statusBadge.textContent = 'Enabled';
            statusBadge.className = 'status-badge enabled';
        } else {
            statusBadge.textContent = 'Disabled';
            statusBadge.className = 'status-badge disabled';
        }

        // Update connection status
        const connectionStatus = document.getElementById('ad-connection-status');
        if (data.connected) {
            connectionStatus.textContent = '✓ Connected';
            connectionStatus.style.color = '#10b981';
        } else {
            connectionStatus.textContent = '✗ Not Connected';
            connectionStatus.style.color = '#ef4444';
        }

        // Update server
        document.getElementById('ad-server').textContent = data.server || 'Not configured';

        // Update auto provision
        document.getElementById('ad-auto-provision').textContent = data.auto_provision ? 'Yes' : 'No';

        // Update synced users count
        document.getElementById('ad-synced-users').textContent = data.synced_users || 0;

        // Update error message
        const errorElement = document.getElementById('ad-error');
        if (data.error) {
            errorElement.textContent = data.error;
            errorElement.style.color = '#d32f2f';
        } else {
            errorElement.textContent = 'None';
            errorElement.style.color = '#10b981';
        }

        // Enable/disable sync button based on status
        const syncBtn = document.getElementById('ad-sync-btn');
        if (syncBtn) {
            if (data.enabled && data.connected) {
                syncBtn.disabled = false;
            } else {
                syncBtn.disabled = true;
            }
        }
    } catch (error) {
        console.error('Error loading AD status:', error);
        const statusBadge = document.getElementById('ad-status-badge');
        if (statusBadge) {
            statusBadge.textContent = 'Error';
            statusBadge.classList.remove('enabled', 'disabled', 'connected');
            statusBadge.classList.add('status-badge', 'disconnected');
        }
        // Don't show error notification for AD status - it's optional
    }
}

function refreshADStatus() {
    loadADStatus();
    showNotification('AD status refreshed', 'success');
}

async function syncADUsers() {
    const syncBtn = document.getElementById('ad-sync-btn');
    const originalText = syncBtn.textContent;

    // Disable button and show loading state
    syncBtn.disabled = true;
    syncBtn.textContent = '⏳ Syncing...';

    try {
        // AD sync can take a while, so use a longer timeout
        const response = await fetchWithTimeout(`${API_BASE}/api/integrations/ad/sync`, {
            method: 'POST'
        }, AD_SYNC_TIMEOUT);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: `HTTP error! status: ${response.status}` }));
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            showNotification(data.message || `Successfully synced ${data.synced_count} users`, 'success');
            // Refresh both AD status and extensions
            loadADStatus();
            loadExtensions();
        } else {
            showNotification(data.error || 'Failed to sync users', 'error');
        }
    } catch (error) {
        console.error('Error syncing AD users:', error);
        const errorMsg = error.message === 'Request timed out'
            ? 'AD sync timed out. This may happen with large directories. Check the server logs.'
            : 'Error syncing AD users';
        showNotification(errorMsg, 'error');
    } finally {
        // Re-enable button
        syncBtn.textContent = originalText;
        syncBtn.disabled = false;
    }
}

// Helper function to create retry buttons HTML (safe - only uses boolean check)
function getRetryButtonsHtml() {
    const retryBtn = '<button class="btn btn-primary" onclick="loadExtensions()" style="margin-left: 10px;">🔄 Retry</button>';
    // currentUser.is_admin is a boolean, safe for conditional rendering
    const syncBtn = (currentUser && currentUser.is_admin === true)
        ? '<button class="btn btn-success" onclick="syncADUsers()" style="margin-left: 10px;">🔄 Sync from AD</button>'
        : '';
    return retryBtn + syncBtn;
}

// Extensions Functions
async function loadExtensions() {
    const tbody = document.getElementById('extensions-table-body');
    tbody.innerHTML = '<tr><td colspan="7" class="loading">Loading extensions...</td></tr>';

    try {
        const response = await fetchWithTimeout(`${API_BASE}/api/extensions`, {
            headers: getAuthHeaders()
        }, EXTENSION_LOAD_TIMEOUT);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const extensions = await response.json();
        currentExtensions = extensions;

        if (extensions.length === 0) {
            tbody.innerHTML = `
                <tr><td colspan="7" class="loading">
                    No extensions found.
                    ${getRetryButtonsHtml()}
                </td></tr>
            `;
            return;
        }

        // Helper function to escape HTML to prevent XSS
        const escapeHtml = (text) => {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        };

        // Helper function to generate extension badges
        const generateBadges = (ext) => {
            let badges = '';
            if (ext.ad_synced) {
                badges += ' <span class="ad-badge" title="Synced from Active Directory">AD</span>';
            }
            if (ext.is_admin) {
                badges += ' <span class="admin-badge" title="Admin Privileges">👑 Admin</span>';
            }
            return badges;
        };

        tbody.innerHTML = extensions.map(ext => `
            <tr>
                <td><strong>${escapeHtml(ext.number)}</strong>${generateBadges(ext)}</td>
                <td>${escapeHtml(ext.name)}</td>
                <td>${ext.email ? escapeHtml(ext.email) : 'Not set'}</td>
                <td class="${ext.registered ? 'status-online' : 'status-offline'}">
                    ${ext.registered ? '● Online' : '○ Offline'}
                </td>
                <td>${ext.allow_external ? 'Yes' : 'No'}</td>
                <td>${ext.voicemail_pin_hash ? '✓ Set' : '<span style="color: orange;">⚠ Not Set</span>'}</td>
                <td>
                    <button class="btn btn-primary" onclick="editExtension('${escapeHtml(ext.number)}')">✏️ Edit</button>
                    ${ext.registered ? `<button class="btn btn-secondary" onclick="rebootPhone('${escapeHtml(ext.number)}')">🔄 Reboot</button>` : ''}
                    <button class="btn btn-danger" onclick="deleteExtension('${escapeHtml(ext.number)}')">🗑️ Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading extensions:', error);
        const errorMsg = error.message === 'Request timed out'
            ? 'Request timed out. The system may still be starting up.'
            : 'Error loading extensions';
        tbody.innerHTML = `
            <tr><td colspan="7" class="loading">
                ${errorMsg}
                ${getRetryButtonsHtml()}
            </td></tr>
        `;
    }
}

// Add Extension Modal
function showAddExtensionModal() {
    document.getElementById('add-extension-modal').classList.add('active');
    document.getElementById('add-extension-form').reset();
}

function closeAddExtensionModal() {
    document.getElementById('add-extension-modal').classList.remove('active');
}

// Edit Extension Modal
function editExtension(number) {
    const ext = currentExtensions.find(e => e.number === number);
    if (!ext) return;

    document.getElementById('edit-ext-number').value = ext.number;
    document.getElementById('edit-ext-name').value = ext.name;
    document.getElementById('edit-ext-email').value = ext.email || '';
    document.getElementById('edit-ext-allow-external').checked = Boolean(ext.allow_external);
    document.getElementById('edit-ext-is-admin').checked = Boolean(ext.is_admin);
    document.getElementById('edit-ext-password').value = '';

    document.getElementById('edit-extension-modal').classList.add('active');
}

function closeEditExtensionModal() {
    document.getElementById('edit-extension-modal').classList.remove('active');
}

async function deleteExtension(number) {
    if (!confirm(`Are you sure you want to delete extension ${number}?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/extensions/${number}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (response.ok) {
            showNotification('Extension deleted successfully', 'success');
            loadExtensions();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to delete extension', 'error');
        }
    } catch (error) {
        console.error('Error deleting extension:', error);
        showNotification('Failed to delete extension', 'error');
    }
}

// Calls Functions
async function loadCalls() {
    const callsList = document.getElementById('calls-list');
    callsList.innerHTML = '<div class="loading">Loading calls...</div>';

    try {
        const response = await fetchWithTimeout(`${API_BASE}/api/calls`, {
            headers: getAuthHeaders()
        });
        const calls = await response.json();

        if (calls.length === 0) {
            callsList.innerHTML = '<div class="loading">No active calls</div>';
            return;
        }

        callsList.innerHTML = calls.map(call => `
            <div class="call-item">
                <strong>Call:</strong> ${call}
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading calls:', error);
        callsList.innerHTML = '<div class="loading">Error loading calls</div>';
    }
}

// Configuration Functions
async function loadConfig() {
    try {
        const response = await fetchWithTimeout(`${API_BASE}/api/config/full`, {
            headers: getAuthHeaders()
        });
        if (response.ok) {
            const config = await response.json();

            // Feature Toggles
            if (config.features) {
                document.getElementById('feature-call-recording').checked = config.features.call_recording || false;
                document.getElementById('feature-call-transfer').checked = config.features.call_transfer || false;
                document.getElementById('feature-call-hold').checked = config.features.call_hold || false;
                document.getElementById('feature-conference').checked = config.features.conference || false;
                document.getElementById('feature-voicemail').checked = config.features.voicemail || false;
                document.getElementById('feature-call-parking').checked = config.features.call_parking || false;
                document.getElementById('feature-call-queues').checked = config.features.call_queues || false;
                document.getElementById('feature-presence').checked = config.features.presence || false;
                document.getElementById('feature-music-on-hold').checked = config.features.music_on_hold || false;
                document.getElementById('feature-auto-attendant').checked = config.features.auto_attendant || false;
            }

            // Voicemail Settings
            if (config.voicemail) {
                document.getElementById('voicemail-max-duration').value = config.voicemail.max_message_duration || 180;
                document.getElementById('voicemail-max-greeting').value = config.voicemail.max_greeting_duration || 30;
                document.getElementById('voicemail-no-answer-timeout').value = config.voicemail.no_answer_timeout || 30;
                document.getElementById('voicemail-allow-custom-greetings').checked = config.voicemail.allow_custom_greetings || false;
                document.getElementById('voicemail-email-notifications').checked = config.voicemail.email_notifications || false;

                // SMTP Settings
                if (config.voicemail.smtp) {
                    document.getElementById('smtp-host').value = config.voicemail.smtp.host || '';
                    document.getElementById('smtp-port').value = config.voicemail.smtp.port || 587;
                    document.getElementById('smtp-use-tls').checked = config.voicemail.smtp.use_tls !== false;
                    document.getElementById('smtp-username').value = config.voicemail.smtp.username || '';
                }

                // Email Settings
                if (config.voicemail.email) {
                    document.getElementById('email-from').value = config.voicemail.email.from_address || '';
                    document.getElementById('email-from-name').value = config.voicemail.email.from_name || '';
                }
            }

            // Recording Settings
            if (config.recording) {
                document.getElementById('recording-auto-record').checked = config.recording.auto_record || false;
                document.getElementById('recording-format').value = config.recording.format || 'wav';
                document.getElementById('recording-storage-path').value = config.recording.storage_path || 'recordings';
            }

            // Security Settings
            if (config.security) {
                if (config.security.password) {
                    document.getElementById('security-min-password').value = config.security.password.min_length || 12;
                    document.getElementById('security-require-uppercase').checked = config.security.password.require_uppercase || false;
                    document.getElementById('security-require-lowercase').checked = config.security.password.require_lowercase || false;
                    document.getElementById('security-require-digit').checked = config.security.password.require_digit || false;
                    document.getElementById('security-require-special').checked = config.security.password.require_special || false;
                }
                if (config.security.rate_limit) {
                    document.getElementById('security-max-attempts').value = config.security.rate_limit.max_attempts || 5;
                    document.getElementById('security-lockout-duration').value = config.security.rate_limit.lockout_duration || 900;
                }
                document.getElementById('security-fips-mode').checked = config.security.fips_mode || false;
            }

            // Advanced Features
            if (config.features) {
                if (config.features.webrtc) {
                    document.getElementById('advanced-webrtc-enabled').checked = config.features.webrtc.enabled || false;
                }
                if (config.features.webhooks) {
                    document.getElementById('advanced-webhooks-enabled').checked = config.features.webhooks.enabled || false;
                }
                if (config.features.crm_integration) {
                    document.getElementById('advanced-crm-enabled').checked = config.features.crm_integration.enabled || false;
                }
                if (config.features.hot_desking) {
                    document.getElementById('advanced-hot-desking-enabled').checked = config.features.hot_desking.enabled || false;
                    document.getElementById('advanced-hot-desking-require-pin').checked = config.features.hot_desking.require_pin || false;
                }
                if (config.features.voicemail_transcription) {
                    document.getElementById('advanced-transcription-enabled').checked = config.features.voicemail_transcription.enabled || false;
                }
            }

            // Conference Settings
            if (config.conference) {
                document.getElementById('conference-max-participants').value = config.conference.max_participants || 50;
                document.getElementById('conference-record').checked = config.conference.record_conferences || false;
            }

            // Server Info (Read-Only)
            if (config.server) {
                document.getElementById('config-sip-port').value = config.server.sip_port || 5060;
                document.getElementById('config-api-port').value = config.api?.port || 8080;
                document.getElementById('config-external-ip').value = config.server.external_ip || '';
                document.getElementById('config-server-name').value = config.server.server_name || '';

                // Pre-fill SSL hostname with external IP
                const sslHostnameInput = document.getElementById('ssl-hostname');
                if (sslHostnameInput && config.server.external_ip) {
                    sslHostnameInput.value = config.server.external_ip;
                }
            }
        }

        // Load SSL status separately
        await loadSSLStatus();
    } catch (error) {
        console.error('Error loading configuration:', error);
        // Use defaults - this is expected when endpoint hasn't been implemented yet
    }
}

// Load Features Status
async function loadFeaturesStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/config/full`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error('Failed to load configuration');
        }

        const config = await response.json();

        // Define feature mappings
        const coreFeatures = [
            { key: 'call_recording', name: 'Call Recording', description: 'Record calls for quality and compliance' },
            { key: 'call_transfer', name: 'Call Transfer', description: 'Transfer calls between extensions' },
            { key: 'call_hold', name: 'Call Hold', description: 'Put calls on hold' },
            { key: 'conference', name: 'Conference Calling', description: 'Multi-party conference calls' },
            { key: 'voicemail', name: 'Voicemail', description: 'Voicemail system with email notifications' },
            { key: 'call_parking', name: 'Call Parking', description: 'Park and retrieve calls' },
            { key: 'call_queues', name: 'Call Queues', description: 'Queue management for incoming calls' },
            { key: 'presence', name: 'Presence', description: 'Real-time extension status' },
            { key: 'music_on_hold', name: 'Music on Hold', description: 'Play music while calls are on hold' },
            { key: 'auto_attendant', name: 'Auto Attendant', description: 'Automated call routing menu' }
        ];

        const advancedFeatures = [
            { key: 'webrtc.enabled', name: 'WebRTC Phone', description: 'Browser-based phone client' },
            { key: 'webhooks.enabled', name: 'Webhooks', description: 'HTTP callbacks for events' },
            { key: 'crm_integration.enabled', name: 'CRM Integration', description: 'Integration with CRM systems' },
            { key: 'hot_desking.enabled', name: 'Hot Desking', description: 'Flexible workspace login' },
            { key: 'voicemail_transcription.enabled', name: 'Voicemail Transcription', description: 'Convert voicemail to text' }
        ];

        const integrationFeatures = [
            { key: 'ad_integration', name: 'Active Directory', description: 'User sync with AD' },
            { key: 'jitsi_integration', name: 'Jitsi Video', description: 'Video conferencing integration' },
            { key: 'matrix_integration', name: 'Matrix Chat', description: 'Team messaging integration' },
            { key: 'espocrm_integration', name: 'EspoCRM', description: 'Open-source CRM integration' }
        ];

        // Helper function to get nested config value
        const getConfigValue = (obj, path) => {
            const keys = path.split('.');
            let value = obj;
            for (const key of keys) {
                value = value?.[key];
                if (value === undefined) return false;
            }
            return Boolean(value);
        };

        // Helper function to render feature row
        const renderFeatureRow = (feature, config) => {
            const enabled = getConfigValue(config.features || {}, feature.key);
            const statusBadge = enabled ?
                '<span class="status-badge status-online">✅ Enabled</span>' :
                '<span class="status-badge status-offline">❌ Disabled</span>';

            return `
                <tr>
                    <td><strong>${feature.name}</strong></td>
                    <td>${statusBadge}</td>
                    <td>${feature.description}</td>
                </tr>
            `;
        };

        // Update tables
        const coreTableBody = document.getElementById('core-features-table');
        if (coreTableBody) {
            coreTableBody.innerHTML = coreFeatures.map(f => renderFeatureRow(f, config)).join('');
        }

        const advancedTableBody = document.getElementById('advanced-features-table');
        if (advancedTableBody) {
            advancedTableBody.innerHTML = advancedFeatures.map(f => renderFeatureRow(f, config)).join('');
        }

        // For integrations, check different config sections
        const integrationTableBody = document.getElementById('integration-features-table');
        if (integrationTableBody) {
            const integrationRows = integrationFeatures.map(feature => {
                let enabled = false;
                if (feature.key === 'ad_integration') {
                    enabled = config.active_directory?.enabled || false;
                } else if (feature.key === 'jitsi_integration') {
                    enabled = config.integrations?.jitsi?.enabled || false;
                } else if (feature.key === 'matrix_integration') {
                    enabled = config.integrations?.matrix?.enabled || false;
                } else if (feature.key === 'espocrm_integration') {
                    enabled = config.integrations?.espocrm?.enabled || false;
                }

                const statusBadge = enabled ?
                    '<span class="status-badge status-online">✅ Enabled</span>' :
                    '<span class="status-badge status-offline">❌ Disabled</span>';

                return `
                    <tr>
                        <td><strong>${feature.name}</strong></td>
                        <td>${statusBadge}</td>
                        <td>${feature.description}</td>
                    </tr>
                `;
            }).join('');

            integrationTableBody.innerHTML = integrationRows;
        }

    } catch (error) {
        console.error('Error loading features status:', error);
        // Show error in tables
        ['core-features-table', 'advanced-features-table', 'integration-features-table'].forEach(tableId => {
            const table = document.getElementById(tableId);
            if (table) {
                table.innerHTML = '<tr><td colspan="3" class="loading">Error loading features. Check Configuration tab.</td></tr>';
            }
        });
    }
}

// Helper function to save configuration sections
async function saveConfigSection(section, data) {
    try {
        const response = await fetch(`${API_BASE}/api/config/section`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                section: section,
                data: data
            })
        });

        if (response.ok) {
            showNotification(CONFIG_SAVE_SUCCESS_MESSAGE, 'success');
            // Reload configuration to reflect changes
            loadConfig();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to save configuration', 'error');
        }
    } catch (error) {
        console.error('Error saving configuration:', error);
        showNotification('Failed to save configuration', 'error');
    }
}

// Form Initialization
function initializeForms() {
    // Add Extension Form
    document.getElementById('add-extension-form').addEventListener('submit', async function(e) {
        e.preventDefault();

        const extensionData = {
            number: document.getElementById('new-ext-number').value,
            name: document.getElementById('new-ext-name').value,
            email: document.getElementById('new-ext-email').value,
            password: document.getElementById('new-ext-password').value,
            allow_external: document.getElementById('new-ext-allow-external').checked,
            voicemail_pin: document.getElementById('new-ext-voicemail-pin').value,
            is_admin: document.getElementById('new-ext-is-admin').checked
        };

        try {
            const response = await fetch(`${API_BASE}/api/extensions`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(extensionData)
            });

            if (response.ok) {
                showNotification('Extension added successfully', 'success');
                closeAddExtensionModal();
                loadExtensions();
            } else {
                const error = await response.json();
                showNotification(error.error || 'Failed to add extension', 'error');
            }
        } catch (error) {
            console.error('Error adding extension:', error);
            showNotification('Failed to add extension', 'error');
        }
    });

    // Edit Extension Form
    document.getElementById('edit-extension-form').addEventListener('submit', async function(e) {
        e.preventDefault();

        const number = document.getElementById('edit-ext-number').value;
        const extensionData = {
            name: document.getElementById('edit-ext-name').value,
            email: document.getElementById('edit-ext-email').value,
            allow_external: document.getElementById('edit-ext-allow-external').checked,
            is_admin: document.getElementById('edit-ext-is-admin').checked
        };

        const password = document.getElementById('edit-ext-password').value;
        if (password) {
            extensionData.password = password;
        }

        const voicemailPin = document.getElementById('edit-ext-voicemail-pin').value;
        if (voicemailPin) {
            extensionData.voicemail_pin = voicemailPin;
        }

        try {
            const response = await fetch(`${API_BASE}/api/extensions/${number}`, {
                method: 'PUT',
                headers: getAuthHeaders(),
                body: JSON.stringify(extensionData)
            });

            if (response.ok) {
                showNotification('Extension updated successfully', 'success');
                closeEditExtensionModal();
                loadExtensions();
            } else {
                const error = await response.json();
                showNotification(error.error || 'Failed to update extension', 'error');
            }
        } catch (error) {
            console.error('Error updating extension:', error);
            showNotification('Failed to update extension', 'error');
        }
    });

    // Features Config Form
    const featuresForm = document.getElementById('features-config-form');
    if (featuresForm) {
        featuresForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            await saveConfigSection('features', {
                call_recording: document.getElementById('feature-call-recording').checked,
                call_transfer: document.getElementById('feature-call-transfer').checked,
                call_hold: document.getElementById('feature-call-hold').checked,
                conference: document.getElementById('feature-conference').checked,
                voicemail: document.getElementById('feature-voicemail').checked,
                call_parking: document.getElementById('feature-call-parking').checked,
                call_queues: document.getElementById('feature-call-queues').checked,
                presence: document.getElementById('feature-presence').checked,
                music_on_hold: document.getElementById('feature-music-on-hold').checked,
                auto_attendant: document.getElementById('feature-auto-attendant').checked
            });
        });
    }

    // Voicemail Config Form
    const voicemailForm = document.getElementById('voicemail-config-form');
    if (voicemailForm) {
        voicemailForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            await saveConfigSection('voicemail', {
                max_message_duration: parseInt(document.getElementById('voicemail-max-duration').value, 10),
                max_greeting_duration: parseInt(document.getElementById('voicemail-max-greeting').value, 10),
                no_answer_timeout: parseInt(document.getElementById('voicemail-no-answer-timeout').value, 10),
                allow_custom_greetings: document.getElementById('voicemail-allow-custom-greetings').checked,
                email_notifications: document.getElementById('voicemail-email-notifications').checked
            });
        });
    }

    // Email Config Form
    const emailForm = document.getElementById('email-config-form');
    if (emailForm) {
        emailForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            await saveConfigSection('voicemail', {
                smtp: {
                    host: document.getElementById('smtp-host').value,
                    port: parseInt(document.getElementById('smtp-port').value, 10),
                    use_tls: document.getElementById('smtp-use-tls').checked,
                    username: document.getElementById('smtp-username').value,
                    password: document.getElementById('smtp-password').value
                },
                email: {
                    from_address: document.getElementById('email-from').value,
                    from_name: document.getElementById('email-from-name').value
                }
            });
        });
    }

    // Recording Config Form
    const recordingForm = document.getElementById('recording-config-form');
    if (recordingForm) {
        recordingForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            await saveConfigSection('recording', {
                auto_record: document.getElementById('recording-auto-record').checked,
                format: document.getElementById('recording-format').value,
                storage_path: document.getElementById('recording-storage-path').value
            });
        });
    }

    // Security Config Form
    const securityForm = document.getElementById('security-config-form');
    if (securityForm) {
        securityForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            await saveConfigSection('security', {
                password: {
                    min_length: parseInt(document.getElementById('security-min-password').value, 10),
                    require_uppercase: document.getElementById('security-require-uppercase').checked,
                    require_lowercase: document.getElementById('security-require-lowercase').checked,
                    require_digit: document.getElementById('security-require-digit').checked,
                    require_special: document.getElementById('security-require-special').checked
                },
                rate_limit: {
                    max_attempts: parseInt(document.getElementById('security-max-attempts').value, 10),
                    lockout_duration: parseInt(document.getElementById('security-lockout-duration').value, 10)
                },
                fips_mode: document.getElementById('security-fips-mode').checked
            });
        });
    }

    // Advanced Features Form
    const advancedForm = document.getElementById('advanced-features-form');
    if (advancedForm) {
        advancedForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            await saveConfigSection('features', {
                webrtc: {
                    enabled: document.getElementById('advanced-webrtc-enabled').checked
                },
                webhooks: {
                    enabled: document.getElementById('advanced-webhooks-enabled').checked
                },
                crm_integration: {
                    enabled: document.getElementById('advanced-crm-enabled').checked
                },
                hot_desking: {
                    enabled: document.getElementById('advanced-hot-desking-enabled').checked,
                    require_pin: document.getElementById('advanced-hot-desking-require-pin').checked
                },
                voicemail_transcription: {
                    enabled: document.getElementById('advanced-transcription-enabled').checked
                }
            });
        });
    }

    // Conference Config Form
    const conferenceForm = document.getElementById('conference-config-form');
    if (conferenceForm) {
        conferenceForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            await saveConfigSection('conference', {
                max_participants: parseInt(document.getElementById('conference-max-participants').value, 10),
                record_conferences: document.getElementById('conference-record').checked
            });
        });
    }

    // Initialize SSL Config Form
    initializeSSLConfigForm();

    // Add Device Form
    const addDeviceForm = document.getElementById('add-device-form');
    if (addDeviceForm) {
        addDeviceForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const mac = document.getElementById('device-mac').value;
            const extension = document.getElementById('device-extension').value;
            const vendor = document.getElementById('device-vendor').value;
            const model = document.getElementById('device-model').value;

            try {
                const response = await fetch(`${API_BASE}/api/provisioning/devices`, {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({
                        mac_address: mac,
                        extension_number: extension,
                        vendor: vendor,
                        model: model
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    const msg = 'Device registered successfully! Config URL: ' + data.device.config_url;
                    showNotification(msg, 'success');
                    // Reset form and reload devices list
                    addDeviceForm.reset();
                    loadProvisioningDevices();
                    // Re-populate the dropdowns after reset
                    await populateProvisioningFormDropdowns();
                } else {
                    const data = await response.json();
                    showNotification(data.error || 'Failed to register device', 'error');
                }
            } catch (error) {
                console.error('Error registering device:', error);
                showNotification('Error registering device: ' + error.message, 'error');
            }
        });
    }

    // Provisioning settings change handlers
    const serverIPInput = document.getElementById('provisioning-server-ip');
    const portInput = document.getElementById('provisioning-port');

    if (serverIPInput) {
        serverIPInput.addEventListener('input', updateProvisioningUrlFormat);
    }
    if (portInput) {
        portInput.addEventListener('input', updateProvisioningUrlFormat);
    }
}

// Notification System
function showNotification(message, type = 'info') {
    // Log to console for debugging
    console.log(`[${type.toUpperCase()}] ${message}`);

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        max-width: 400px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999;
        animation: slideInRight 0.3s ease-out;
        font-size: 14px;
        line-height: 1.4;
    `;

    const icon = type === 'success' ? '✓' : type === 'error' ? '✗' : type === 'warning' ? '⚠' : 'ℹ';
    notification.innerHTML = `<strong>${icon}</strong> ${escapeHtml(message)}`;

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Add slide animations
const slideStyle = document.createElement('style');
slideStyle.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(slideStyle);

// Voicemail Management Functions
async function loadVoicemailTab() {
    try {
        // Load extensions into dropdown
        const response = await fetch(`${API_BASE}/api/extensions`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const extensions = await response.json();

        const select = document.getElementById('vm-extension-select');
        select.innerHTML = '<option value="">Select Extension</option>';

        extensions.forEach(ext => {
            const option = document.createElement('option');
            option.value = ext.number;
            option.textContent = `${ext.number} - ${ext.name}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading voicemail tab:', error);
        showNotification('Failed to load extensions', 'error');
    }
}

window.loadVoicemailForExtension = async function() {
    const extension = document.getElementById('vm-extension-select').value;

    if (!extension) {
        document.getElementById('voicemail-pin-section').style.display = 'none';
        document.getElementById('voicemail-messages-section').style.display = 'none';
        document.getElementById('voicemail-box-overview').style.display = 'none';
        return;
    }

    // Show sections
    document.getElementById('voicemail-pin-section').style.display = 'block';
    document.getElementById('voicemail-messages-section').style.display = 'block';
    document.getElementById('voicemail-box-overview').style.display = 'block';
    document.getElementById('vm-current-extension').textContent = extension;

    try {
        // Load voicemail messages
        const response = await fetch(`${API_BASE}/api/voicemail/${extension}`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Update both views
        updateVoicemailCardsView(data.messages, extension);
        updateVoicemailTableView(data.messages, extension);

    } catch (error) {
        console.error('Error loading voicemail:', error);
        showNotification('Failed to load voicemail messages', 'error');
    }
};

function updateVoicemailCardsView(messages, extension) {
    const cardsContainer = document.getElementById('voicemail-cards-view');

    if (!messages || messages.length === 0) {
        cardsContainer.innerHTML = '<div class="info-box">No voicemail messages</div>';
        return;
    }

    cardsContainer.innerHTML = messages.map(msg => {
        const timestamp = new Date(msg.timestamp).toLocaleString();
        const duration = msg.duration ? `${msg.duration}s` : 'Unknown';
        const isUnread = !msg.listened;

        let transcriptionHtml = '';
        if (msg.transcription && msg.transcription.text) {
            const confidencePercent = msg.transcription.confidence ?
                (msg.transcription.confidence * 100).toFixed(0) : 'N/A';
            transcriptionHtml = `
                <div class="voicemail-transcription">
                    "${msg.transcription.text}"
                    <span class="voicemail-transcription-confidence">
                        Confidence: ${confidencePercent}%
                    </span>
                </div>
            `;
        }

        return `
            <div class="voicemail-card ${isUnread ? 'unread' : ''}">
                <div class="voicemail-card-header">
                    <div class="voicemail-from">📞 ${msg.caller_id}</div>
                    <span class="voicemail-status-badge ${isUnread ? 'unread' : 'read'}">
                        ${isUnread ? 'NEW' : 'READ'}
                    </span>
                </div>
                <div class="voicemail-meta">
                    <div class="voicemail-meta-item">
                        <span>📅</span> ${timestamp}
                    </div>
                    <div class="voicemail-meta-item">
                        <span>⏱️</span> ${duration}
                    </div>
                </div>
                ${transcriptionHtml}
                <div class="voicemail-actions">
                    <button class="btn btn-sm btn-info" onclick="openVoicemailPlayer('${extension}', '${msg.id}')">
                        ▶️ Play
                    </button>
                    <button class="btn btn-sm btn-success" onclick="downloadVoicemail('${extension}', '${msg.id}')">
                        ⬇️ Download
                    </button>
                    ${isUnread ? `
                        <button class="btn btn-sm btn-secondary" onclick="markVoicemailRead('${extension}', '${msg.id}')">
                            ✓ Mark Read
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-danger" onclick="deleteVoicemail('${extension}', '${msg.id}')">
                        🗑️ Delete
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function updateVoicemailTableView(messages, extension) {
    const tbody = document.getElementById('voicemail-table-body');

    if (!messages || messages.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-data">No voicemail messages</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    messages.forEach(msg => {
        const row = document.createElement('tr');
        const timestamp = new Date(msg.timestamp).toLocaleString();
        const duration = msg.duration ? `${msg.duration}s` : 'Unknown';
        const status = msg.listened ? 'Read' : 'Unread';

        row.innerHTML = `
            <td>${timestamp}</td>
            <td>${msg.caller_id}</td>
            <td>${duration}</td>
            <td><span class="badge ${msg.listened ? 'badge-secondary' : 'badge-primary'}">${status}</span></td>
            <td>
                <button class="btn btn-sm btn-info" onclick="openVoicemailPlayer('${extension}', '${msg.id}')">▶ Play</button>
                <button class="btn btn-sm btn-success" onclick="downloadVoicemail('${extension}', '${msg.id}')">⬇ Download</button>
                ${!msg.listened ? `<button class="btn btn-sm btn-secondary" onclick="markVoicemailRead('${extension}', '${msg.id}')">✓ Mark Read</button>` : ''}
                <button class="btn btn-sm btn-danger" onclick="deleteVoicemail('${extension}', '${msg.id}')">🗑 Delete</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

window.toggleVoicemailView = function() {
    const cardsView = document.getElementById('voicemail-cards-view');
    const tableView = document.getElementById('voicemail-table-view');
    const toggleText = document.getElementById('view-toggle-text');

    if (cardsView.style.display === 'none') {
        // Switch to cards view
        cardsView.style.display = 'grid';
        tableView.style.display = 'none';
        toggleText.textContent = '📋 Switch to Table View';
    } else {
        // Switch to table view
        cardsView.style.display = 'none';
        tableView.style.display = 'block';
        toggleText.textContent = '🎴 Switch to Card View';
    }
};

window.openVoicemailPlayer = async function(extension, messageId) {
    try {
        // Fetch message details
        const response = await fetch(`${API_BASE}/api/voicemail/${extension}`);
        const data = await response.json();
        const message = data.messages.find(m => m.id === messageId);

        if (!message) {
            showNotification('Message not found', 'error');
            return;
        }

        // Update player details
        const detailsDiv = document.getElementById('vm-player-details');
        const timestamp = new Date(message.timestamp).toLocaleString();
        const duration = message.duration ? `${message.duration}s` : 'Unknown';

        detailsDiv.innerHTML = `
            <p><strong>From:</strong> ${message.caller_id}</p>
            <p><strong>Received:</strong> ${timestamp}</p>
            <p><strong>Duration:</strong> ${duration}</p>
            <p><strong>Status:</strong> ${message.listened ? 'Read' : 'Unread'}</p>
        `;

        // Set audio source
        const audioPlayer = document.getElementById('vm-audio-player');
        audioPlayer.src = `${API_BASE}/api/voicemail/${extension}/${messageId}`;

        // Show/hide transcription
        const transcriptionDiv = document.getElementById('vm-transcription-display');
        if (message.transcription && message.transcription.text) {
            document.getElementById('vm-transcription-text').textContent = message.transcription.text;
            const confidence = message.transcription.confidence ?
                `Confidence: ${(message.transcription.confidence * 100).toFixed(0)}%` : '';
            document.getElementById('vm-transcription-confidence').textContent = confidence;
            transcriptionDiv.style.display = 'block';
        } else {
            transcriptionDiv.style.display = 'none';
        }

        // Show modal
        document.getElementById('voicemail-player-modal').style.display = 'block';

        // Mark as read after playing starts
        audioPlayer.onplay = () => {
            markVoicemailRead(extension, messageId, false);
        };

    } catch (error) {
        console.error('Error opening voicemail player:', error);
        showNotification('Failed to open voicemail player', 'error');
    }
};

window.closeVoicemailPlayer = function() {
    const modal = document.getElementById('voicemail-player-modal');
    const audioPlayer = document.getElementById('vm-audio-player');

    audioPlayer.pause();
    audioPlayer.src = '';
    modal.style.display = 'none';

    // Reload messages to update read status
    loadVoicemailForExtension();
};

// Legacy function - maintained for backward compatibility
// Redirects to new modal player
window.playVoicemail = async function(extension, messageId) {
    openVoicemailPlayer(extension, messageId);
};

window.downloadVoicemail = async function(extension, messageId) {
    try {
        const url = `${API_BASE}/api/voicemail/${extension}/${messageId}`;
        const link = document.createElement('a');
        link.href = url;
        link.download = `voicemail_${extension}_${messageId}.wav`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showNotification('Downloading voicemail...', 'info');
    } catch (error) {
        console.error('Error downloading voicemail:', error);
        showNotification('Failed to download voicemail', 'error');
    }
};

window.markVoicemailRead = async function(extension, messageId, showMsg = true) {
    try {
        const response = await fetch(`${API_BASE}/api/voicemail/${extension}/${messageId}/mark-read`, {
            method: 'PUT',
            headers: getAuthHeaders()
        });

        if (response.ok) {
            if (showMsg) {
                showNotification('Message marked as read', 'success');
            }
            loadVoicemailForExtension();
        } else {
            throw new Error('Failed to mark as read');
        }
    } catch (error) {
        console.error('Error marking voicemail as read:', error);
        if (showMsg) {
            showNotification('Failed to mark message as read', 'error');
        }
    }
};

window.deleteVoicemail = async function(extension, messageId) {
    if (!confirm('Are you sure you want to delete this voicemail message?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/voicemail/${extension}/${messageId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showNotification('Voicemail deleted successfully', 'success');
            loadVoicemailForExtension();
        } else {
            throw new Error('Failed to delete');
        }
    } catch (error) {
        console.error('Error deleting voicemail:', error);
        showNotification('Failed to delete voicemail', 'error');
    }
};

// Initialize voicemail PIN form
document.addEventListener('DOMContentLoaded', function() {
    const pinForm = document.getElementById('voicemail-pin-form');
    if (pinForm) {
        pinForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const extension = document.getElementById('vm-extension-select').value;
            const pin = document.getElementById('vm-pin').value;

            if (!extension) {
                showNotification('Please select an extension', 'error');
                return;
            }

            if (!/^\d{4}$/.test(pin)) {
                showNotification('PIN must be exactly 4 digits', 'error');
                return;
            }

            try {
                const response = await fetch(`${API_BASE}/api/voicemail/${extension}/pin`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ pin })
                });

                if (response.ok) {
                    showNotification('Voicemail PIN updated successfully', 'success');
                    document.getElementById('vm-pin').value = '';
                } else {
                    const error = await response.json();
                    showNotification(error.error || 'Failed to update PIN', 'error');
                }
            } catch (error) {
                console.error('Error updating voicemail PIN:', error);
                showNotification('Failed to update PIN', 'error');
            }
        });
    }
});

// Phone Reboot Functions
async function rebootPhone(extension) {
    if (!confirm(`Send reboot signal to phone at extension ${extension}?\n\nThe phone will restart and reload its configuration.`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/phones/${extension}/reboot`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showNotification(`Reboot signal sent to extension ${extension}`, 'success');
        } else {
            showNotification(data.error || 'Failed to send reboot signal', 'error');
        }
    } catch (error) {
        console.error('Error rebooting phone:', error);
        showNotification('Failed to send reboot signal', 'error');
    }
}

async function rebootAllPhones() {
    if (!confirm('Send reboot signal to ALL registered phones?\n\nAll online phones will restart and reload their configurations. This may take a few minutes.')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/phones/reboot`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok && data.success) {
            const message = `Rebooted ${data.success_count} phone(s)` +
                          (data.failed_count > 0 ? `, ${data.failed_count} failed` : '');
            showNotification(message, 'success');

            // Refresh extensions list after a delay to show new status
            setTimeout(loadExtensions, 2000);
        } else {
            showNotification(data.error || 'Failed to reboot phones', 'error');
        }
    } catch (error) {
        console.error('Error rebooting phones:', error);
        showNotification('Failed to reboot phones', 'error');
    }
}

// Registered Phones Functions
async function loadRegisteredPhones() {
    const tbody = document.getElementById('registered-phones-table-body');
    tbody.innerHTML = '<tr><td colspan="5" class="loading">Loading registered phones...</td></tr>';

    try {
        const response = await fetchWithTimeout(`${API_BASE}/api/registered-phones`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            // Try to parse error response from API
            let errorMessage = `HTTP ${response.status}`;
            try {
                const errorData = await response.json();
                if (errorData.error) {
                    errorMessage = errorData.error;
                    if (errorData.details) {
                        errorMessage += ` - ${errorData.details}`;
                    }
                }
            } catch (parseError) {
                // If parsing fails, keep the HTTP status message
            }
            throw new Error(errorMessage);
        }

        const phones = await response.json();

        if (!phones || phones.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="loading">No registered phones found in database</td></tr>';
            return;
        }

        // Clear table body
        tbody.innerHTML = '';

        // Create rows safely using DOM methods to prevent XSS
        phones.forEach(phone => {
            const row = document.createElement('tr');

            // Extension number
            const extCell = document.createElement('td');
            const extStrong = document.createElement('strong');
            extStrong.textContent = phone.extension_number || 'Unknown';
            extCell.appendChild(extStrong);
            row.appendChild(extCell);

            // IP Address
            const ipCell = document.createElement('td');
            ipCell.textContent = phone.ip_address || 'Unknown';
            row.appendChild(ipCell);

            // MAC Address
            const macCell = document.createElement('td');
            macCell.textContent = phone.mac_address || 'Unknown';
            row.appendChild(macCell);

            // User Agent
            const uaCell = document.createElement('td');
            uaCell.textContent = phone.user_agent || 'Unknown';
            row.appendChild(uaCell);

            // Last Registration
            const regCell = document.createElement('td');
            regCell.textContent = phone.last_registered ? new Date(phone.last_registered).toLocaleString() : 'Never';
            row.appendChild(regCell);

            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading registered phones:', error);

        // Display error message in table
        const errorCell = document.createElement('td');
        errorCell.colSpan = 5;
        errorCell.className = 'error-message';
        errorCell.textContent = `Error: ${error.message}`;

        const errorRow = document.createElement('tr');
        errorRow.appendChild(errorCell);

        tbody.innerHTML = '';
        tbody.appendChild(errorRow);

        showNotification(`Failed to load registered phones: ${error.message}`, 'error');
    }
}

// ============================================================================
// Phone Provisioning Functions
// ============================================================================
let supportedVendors = [];
let supportedModels = {};

async function loadProvisioning() {
    await loadProvisioningSettings();
    await loadPhonebookSettings();
    await loadSupportedVendors();
    await loadProvisioningDevices();
    await populateProvisioningFormDropdowns();
}

async function populateProvisioningFormDropdowns() {
    // Populate extension dropdown
    const extensionSelect = document.getElementById('device-extension');
    if (extensionSelect) {
        extensionSelect.innerHTML = '<option value="">Loading extensions...</option>';
        
        try {
            const response = await fetch(`${API_BASE}/api/extensions`, {
                headers: getAuthHeaders()
            });
            if (response.ok) {
                const extensions = await response.json();
                extensionSelect.innerHTML = '<option value="">Select Extension</option>';
                
                extensions.forEach(ext => {
                    const option = document.createElement('option');
                    option.value = ext.number;
                    option.textContent = `${ext.number} - ${ext.name}`;
                    extensionSelect.appendChild(option);
                });
            } else {
                extensionSelect.innerHTML = '<option value="">Error loading extensions</option>';
            }
        } catch (error) {
            console.error('Error loading extensions:', error);
            extensionSelect.innerHTML = '<option value="">Error loading extensions</option>';
        }
    }

    // Populate vendor dropdown
    const vendorSelect = document.getElementById('device-vendor');
    if (vendorSelect && supportedVendors.length > 0) {
        vendorSelect.innerHTML = '<option value="">Select Vendor</option>';
        supportedVendors.forEach(vendor => {
            const option = document.createElement('option');
            option.value = vendor;
            option.textContent = vendor.toUpperCase();
            vendorSelect.appendChild(option);
        });
    }

    // Reset the model dropdown to its default state
    const modelSelect = document.getElementById('device-model');
    if (modelSelect) {
        modelSelect.innerHTML = '<option value="">Select Vendor First</option>';
    }
}

function resetAddDeviceForm() {
    const form = document.getElementById('add-device-form');
    if (!form) {
        return;
    }

    // Reset all form fields to their initial values
    form.reset();

    // Reset the model dropdown to its initial state
    const modelSelect = document.getElementById('device-model');
    if (modelSelect) {
        modelSelect.innerHTML = '<option value="">Select Vendor First</option>';
    }
}

async function loadPhonebookSettings() {
    try {
        // Try to load existing settings from status endpoint or use defaults
        const response = await fetch(`${API_BASE}/api/status`);
        if (response.ok) {
            const data = await response.json();
            const serverIP = data.server_ip || window.location.hostname;
            const port = data.api_port || '8080';
            const protocol = window.location.protocol; // Use current protocol (http: or https:)

            // Pre-populate remote phonebook URL
            document.getElementById('remote-phonebook-url').value = `${protocol}//${serverIP}:${port}/api/phone-book/export/xml`;

            // Set default values
            document.getElementById('ldap-phonebook-port').value = '636';
            document.getElementById('ldap-phonebook-display-name').value = 'Company Directory';
            document.getElementById('remote-phonebook-refresh').value = '60';
        }
    } catch (error) {
        console.error('Error loading phonebook settings:', error);
    }
}

async function loadProvisioningSettings() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        if (response.ok) {
            const data = await response.json();
            // Get current server IP from status or use default
            const serverIP = data.server_ip || window.location.hostname;
            document.getElementById('provisioning-server-ip').value = serverIP;

            // Update URL format display
            updateProvisioningUrlFormat();
        }
    } catch (error) {
        console.error('Error loading provisioning settings:', error);
    }
}

function toggleProvisioningEnabled() {
    const enabled = document.getElementById('provisioning-enabled').checked;
    const settingsDiv = document.getElementById('provisioning-settings');
    settingsDiv.style.display = enabled ? 'block' : 'none';
}

function updateProvisioningUrlFormat() {
    const serverIP = document.getElementById('provisioning-server-ip').value || 'SERVER';
    const port = document.getElementById('provisioning-port').value || '8080';
    const protocol = window.location.protocol; // Use current protocol (http: or https:)
    const urlFormat = `${protocol}//${serverIP}:${port}/provision/{mac}.cfg`;
    document.getElementById('provisioning-url-format').value = urlFormat;
}

async function saveProvisioningSettings() {
    const enabled = document.getElementById('provisioning-enabled').checked;
    const serverIP = document.getElementById('provisioning-server-ip').value;
    const port = document.getElementById('provisioning-port').value;
    const customDir = document.getElementById('provisioning-custom-dir').value;
    const protocol = window.location.protocol; // Use current protocol (http: or https:)

    if (!serverIP) {
        showNotification('Please enter a server IP address', 'error');
        return;
    }

    const configMsg = `Provisioning settings need to be updated in config.yml:\n\n` +
          `provisioning:\n` +
          `  enabled: ${enabled}\n` +
          `  url_format: ${protocol}//${serverIP}:${port}/provision/{mac}.cfg\n` +
          `  custom_templates_dir: "${customDir}"\n\n` +
          'Then restart the PBX server.';

    showNotification('Settings saved. Update config.yml and restart required.', 'info');
    console.log(configMsg);
}

// Phone Book Configuration Functions
function toggleLdapPhonebookSettings() {
    const enabled = document.getElementById('ldap-phonebook-enabled').checked;
    const settingsDiv = document.getElementById('ldap-phonebook-settings');
    settingsDiv.style.display = enabled ? 'block' : 'none';
}

function toggleRemotePhonebookSettings() {
    const enabled = document.getElementById('remote-phonebook-enabled').checked;
    const settingsDiv = document.getElementById('remote-phonebook-settings');
    settingsDiv.style.display = enabled ? 'block' : 'none';

    if (enabled) {
        // Auto-populate remote phonebook URL based on server settings
        const serverIP = document.getElementById('provisioning-server-ip').value || window.location.hostname;
        const port = document.getElementById('provisioning-port').value || '8080';
        const protocol = window.location.protocol; // Use current protocol (http: or https:)
        document.getElementById('remote-phonebook-url').value = `${protocol}//${serverIP}:${port}/api/phone-book/export/xml`;
    }
}

async function savePhonebookSettings() {
    // LDAPS settings
    const ldapEnabled = document.getElementById('ldap-phonebook-enabled').checked ? 1 : 0;
    const ldapServer = document.getElementById('ldap-phonebook-server').value;
    const ldapPort = document.getElementById('ldap-phonebook-port').value || '636';
    const ldapBase = document.getElementById('ldap-phonebook-base').value;
    const ldapUser = document.getElementById('ldap-phonebook-user').value;
    const ldapPassword = document.getElementById('ldap-phonebook-password').value;
    const ldapTls = document.getElementById('ldap-phonebook-tls').checked ? 1 : 0;
    const ldapDisplayName = document.getElementById('ldap-phonebook-display-name').value || 'Company Directory';

    // Remote phonebook settings
    const remoteEnabled = document.getElementById('remote-phonebook-enabled').checked;
    const remoteUrl = document.getElementById('remote-phonebook-url').value;
    const remoteRefresh = document.getElementById('remote-phonebook-refresh').value || '60';

    // Build configuration message
    let configMsg = `Phone Book settings need to be updated in config.yml:\n\n`;
    configMsg += `provisioning:\n`;
    configMsg += `  # ... existing provisioning settings ...\n\n`;

    if (ldapEnabled) {
        configMsg += `  # LDAP/LDAPS Phone Book Configuration\n`;
        configMsg += `  ldap_phonebook:\n`;
        configMsg += `    enable: ${ldapEnabled}\n`;
        configMsg += `    server: ${ldapServer}\n`;
        configMsg += `    port: ${ldapPort}\n`;
        configMsg += `    base: ${ldapBase}\n`;
        configMsg += `    user: ${ldapUser}\n`;
        configMsg += `    password: \${LDAP_PHONEBOOK_PASSWORD}  # Set in .env file\n`;
        configMsg += `    version: 3\n`;
        configMsg += `    tls_mode: ${ldapTls}\n`;
        configMsg += `    name_filter: (|(cn=%)(sn=%))\n`;
        configMsg += `    number_filter: (|(telephoneNumber=%)(mobile=%))\n`;
        configMsg += `    name_attr: cn\n`;
        configMsg += `    number_attr: telephoneNumber\n`;
        configMsg += `    display_name: ${ldapDisplayName}\n\n`;

        if (ldapPassword) {
            configMsg += `Also add to .env file:\n`;
            configMsg += `LDAP_PHONEBOOK_PASSWORD=${ldapPassword}\n\n`;
        }
    }

    if (remoteEnabled) {
        configMsg += `  # Remote Phone Book URL (Fallback)\n`;
        configMsg += `  remote_phonebook:\n`;
        configMsg += `    url: ${remoteUrl}\n`;
        configMsg += `    refresh_interval: ${remoteRefresh}\n\n`;
    }

    configMsg += `Then restart the PBX server for changes to take effect.\n`;
    configMsg += `\nPhones will need to be reprovisioned to receive the new phone book settings.`;

    // Show notification
    showNotification('Phone Book settings saved. Update config.yml and restart required.', 'info');
    console.log(configMsg);

    // Also show in alert for easy copy-paste
    alert(configMsg);
}

async function loadSupportedVendors() {
    const vendorsList = document.getElementById('supported-vendors-list');
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/vendors`, {
            headers: getAuthHeaders()
        });
        if (response.ok) {
            const data = await response.json();
            supportedVendors = data.vendors || [];
            supportedModels = data.models || {};

            // Display supported vendors
            if (supportedVendors.length > 0) {
                let html = '<ul>';
                for (const vendor of supportedVendors) {
                    html += `<li><strong>${vendor.toUpperCase()}</strong>: `;
                    const models = supportedModels[vendor] || [];
                    html += models.map(m => m.toUpperCase()).join(', ');
                    html += '</li>';
                }
                html += '</ul>';
                vendorsList.innerHTML = html;
            } else {
                vendorsList.innerHTML = '<p>No vendors available. Check PBX configuration.</p>';
            }
        } else {
            // Handle non-ok response (e.g., 401, 403, 500)
            let errorMsg = `Error loading vendors: HTTP ${response.status}`;
            try {
                const errorData = await response.json();
                if (errorData.error) {
                    errorMsg = `Error loading vendors: ${escapeHtml(errorData.error)}`;
                }
            } catch (e) {
                // Unable to parse error response, use generic message
            }
            vendorsList.innerHTML = `<p class="error">${errorMsg}</p>`;
            console.error('Error loading supported vendors:', errorMsg);
        }
    } catch (error) {
        console.error('Error loading supported vendors:', error);
        vendorsList.innerHTML = '<p class="error">Error loading vendors: ' + escapeHtml(error.message) + '</p>';
    }
}

async function loadProvisioningDevices() {
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/devices`, {
            headers: getAuthHeaders()
        });
        const tbody = document.getElementById('provisioning-devices-table-body');

        if (response.ok) {
            const devices = await response.json();

            if (devices.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="no-data">No devices provisioned yet. Fill out the form above to register phones.</td></tr>';
            } else {
                tbody.innerHTML = devices.map(device => {
                    const createdDate = device.created_at ? new Date(device.created_at).toLocaleString() : '-';
                    const provisionedDate = device.last_provisioned ? new Date(device.last_provisioned).toLocaleString() : 'Never';

                    return `
                        <tr>
                            <td><code>${device.mac_address}</code></td>
                            <td>${device.extension_number}</td>
                            <td>${device.vendor.toUpperCase()}</td>
                            <td>${device.model.toUpperCase()}</td>
                            <td>${createdDate}</td>
                            <td>${provisionedDate}</td>
                            <td>
                                <button class="btn btn-small btn-danger" onclick="deleteDevice('${device.mac_address}')">🗑️ Delete</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        } else {
            tbody.innerHTML = '<tr><td colspan="7" class="error">Error loading devices</td></tr>';
        }
    } catch (error) {
        console.error('Error loading provisioning devices:', error);
        document.getElementById('provisioning-devices-table-body').innerHTML =
            '<tr><td colspan="7" class="error">Error: ' + error.message + '</td></tr>';
    }
}

function updateModelOptions() {
    const vendor = document.getElementById('device-vendor').value;
    const modelSelect = document.getElementById('device-model');

    if (!vendor) {
        modelSelect.innerHTML = '<option value="">Select Vendor First</option>';
        return;
    }

    const models = supportedModels[vendor] || [];
    modelSelect.innerHTML = '<option value="">Select Model</option>';

    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model.toUpperCase();
        modelSelect.appendChild(option);
    });
}

async function deleteDevice(mac) {
    if (!confirm(`Are you sure you want to delete device ${mac}?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/provisioning/devices/${mac}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showNotification('Device deleted successfully', 'success');
            loadProvisioningDevices();
        } else {
            const data = await response.json();
            showNotification('Failed to delete device: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error deleting device:', error);
        showNotification('Error deleting device: ' + error.message, 'error');
    }
}

// Template management functions
async function loadProvisioningTemplates() {
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/templates`, {
            headers: getAuthHeaders()
        });
        if (response.ok) {
            const data = await response.json();
            displayTemplatesList(data.templates || []);
        } else {
            showNotification('Error loading templates', 'error');
        }
    } catch (error) {
        console.error('Error loading templates:', error);
        showNotification('Error loading templates: ' + error.message, 'error');
    }
}

function displayTemplatesList(templates) {
    const tbody = document.getElementById('templates-table-body');
    if (!tbody) return;

    if (templates.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5">No templates found</td></tr>';
        return;
    }

    // Clear existing content
    tbody.innerHTML = '';

    // Create rows safely without XSS vulnerabilities
    templates.forEach(template => {
        const row = document.createElement('tr');

        // Vendor cell
        const vendorCell = document.createElement('td');
        vendorCell.textContent = template.vendor;
        row.appendChild(vendorCell);

        // Model cell
        const modelCell = document.createElement('td');
        modelCell.textContent = template.model;
        row.appendChild(modelCell);

        // Type cell
        const typeCell = document.createElement('td');
        const badge = document.createElement('span');
        badge.className = template.is_custom ? 'badge badge-success' : 'badge badge-info';
        badge.textContent = template.is_custom ? 'Custom' : 'Built-in';
        typeCell.appendChild(badge);
        row.appendChild(typeCell);

        // Size cell
        const sizeCell = document.createElement('td');
        sizeCell.textContent = (template.size / 1024).toFixed(1) + ' KB';
        row.appendChild(sizeCell);

        // Actions cell
        const actionsCell = document.createElement('td');

        // View button
        const viewBtn = document.createElement('button');
        viewBtn.className = 'btn btn-sm btn-primary';
        viewBtn.textContent = '👁️ View';
        viewBtn.onclick = () => viewTemplate(template.vendor, template.model);
        actionsCell.appendChild(viewBtn);

        // Export button
        const exportBtn = document.createElement('button');
        exportBtn.className = 'btn btn-sm btn-success';
        exportBtn.textContent = '💾 Export';
        exportBtn.onclick = () => exportTemplate(template.vendor, template.model);
        actionsCell.appendChild(exportBtn);

        // Edit button (only for custom templates)
        if (template.is_custom) {
            const editBtn = document.createElement('button');
            editBtn.className = 'btn btn-sm btn-warning';
            editBtn.textContent = '✏️ Edit';
            editBtn.onclick = () => editTemplate(template.vendor, template.model);
            actionsCell.appendChild(editBtn);
        }

        row.appendChild(actionsCell);
        tbody.appendChild(row);
    });
}

async function viewTemplate(vendor, model) {
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/templates/${vendor}/${model}`, {
            headers: getAuthHeaders()
        });
        if (response.ok) {
            const data = await response.json();
            showTemplateViewModal(vendor, model, data.content, data.placeholders, false);
        } else {
            showNotification('Error loading template', 'error');
        }
    } catch (error) {
        console.error('Error viewing template:', error);
        showNotification('Error viewing template: ' + error.message, 'error');
    }
}

async function exportTemplate(vendor, model) {
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/templates/${vendor}/${model}/export`, {
            method: 'POST'
        });
        if (response.ok) {
            const data = await response.json();
            showNotification(`Template exported to: ${data.filepath}`, 'success');
            loadProvisioningTemplates(); // Refresh list
        } else {
            const error = await response.json();
            showNotification('Error exporting template: ' + error.error, 'error');
        }
    } catch (error) {
        console.error('Error exporting template:', error);
        showNotification('Error exporting template: ' + error.message, 'error');
    }
}

async function editTemplate(vendor, model) {
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/templates/${vendor}/${model}`, {
            headers: getAuthHeaders()
        });
        if (response.ok) {
            const data = await response.json();
            showTemplateViewModal(vendor, model, data.content, data.placeholders, true);
        } else {
            showNotification('Error loading template', 'error');
        }
    } catch (error) {
        console.error('Error loading template:', error);
        showNotification('Error loading template: ' + error.message, 'error');
    }
}

function showTemplateViewModal(vendor, model, content, placeholders, editable) {
    const modal = document.getElementById('template-view-modal');
    const title = document.getElementById('template-modal-title');
    const textarea = document.getElementById('template-content');
    const placeholdersDiv = document.getElementById('template-placeholders');
    const saveBtn = document.getElementById('save-template-btn');

    if (!modal) return;

    title.textContent = editable ?
        `Edit Template: ${vendor} ${model}` :
        `View Template: ${vendor} ${model}`;

    textarea.value = content;
    textarea.readOnly = !editable;

    // Display available placeholders safely
    placeholdersDiv.innerHTML = ''; // Clear first

    const strong = document.createElement('strong');
    strong.textContent = 'Available Placeholders:';
    placeholdersDiv.appendChild(strong);

    const ul = document.createElement('ul');
    placeholders.forEach(p => {
        const li = document.createElement('li');
        const code = document.createElement('code');
        code.textContent = p;
        li.appendChild(code);
        ul.appendChild(li);
    });
    placeholdersDiv.appendChild(ul);

    const p = document.createElement('p');
    const small = document.createElement('small');
    small.textContent = 'These placeholders will be automatically replaced with device-specific information when a phone requests configuration.';
    p.appendChild(small);
    placeholdersDiv.appendChild(p);

    // Set up save button
    saveBtn.style.display = editable ? 'inline-block' : 'none';
    saveBtn.onclick = async () => {
        await saveTemplateContent(vendor, model, textarea.value);
    };

    modal.style.display = 'block';
}

function closeTemplateViewModal() {
    const modal = document.getElementById('template-view-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function saveTemplateContent(vendor, model, content) {
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/templates/${vendor}/${model}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            showNotification('Template updated successfully', 'success');
            closeTemplateViewModal();
            loadProvisioningTemplates(); // Refresh list
        } else {
            const error = await response.json();
            showNotification('Error updating template: ' + error.error, 'error');
        }
    } catch (error) {
        console.error('Error saving template:', error);
        showNotification('Error saving template: ' + error.message, 'error');
    }
}

async function reloadTemplates() {
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/reload-templates`, {
            method: 'POST'
        });

        if (response.ok) {
            const data = await response.json();
            showNotification(`Templates reloaded: ${data.statistics.total_templates} templates from ${data.statistics.vendors} vendors`, 'success');
            loadProvisioningTemplates(); // Refresh list
        } else {
            const error = await response.json();
            showNotification('Error reloading templates: ' + error.error, 'error');
        }
    } catch (error) {
        console.error('Error reloading templates:', error);
        showNotification('Error reloading templates: ' + error.message, 'error');
    }
}

// ============================================================================
// Analytics and Statistics Functions
// ============================================================================
let analyticsCharts = {};

/**
 * Check if Chart.js library is available
 * @param {HTMLElement} ctx - Canvas context element (optional, for inline error display)
 * @returns {boolean} - True if Chart.js is available, false otherwise
 */
function isChartJsAvailable(ctx = null) {
    // Check if Chart.js is loaded, accounting for potential delay from fallback CDNs
    if (typeof Chart === 'undefined') {
        // Check if we know loading failed completely
        if (window.chartJsLoadFailed) {
            console.warn('Chart.js library failed to load from all CDN sources');
            if (ctx && ctx.parentElement) {
                const msg = document.createElement('p');
                msg.style.padding = '20px';
                msg.style.textAlign = 'center';
                msg.style.color = '#666';
                msg.style.fontSize = '14px';
                msg.innerHTML = '📊 Chart visualization unavailable in offline mode<br><small>Data is still available in tables below</small>';
                ctx.parentElement.innerHTML = '';
                ctx.parentElement.appendChild(msg);
            }
        }
        return false;
    }
    return true;
}

async function loadAnalytics() {
    const days = document.getElementById('analytics-period')?.value || 7;

    // Check if Chart.js is loaded
    const chartJsAvailable = isChartJsAvailable();

    // Show warning if Chart.js is not available, but continue to load data
    if (!chartJsAvailable) {
        showNotification('Chart library not available - displaying data in tables only. Charts require internet connection.', 'warning');
        // Hide chart containers
        const chartContainers = document.querySelectorAll('.chart-box');
        chartContainers.forEach(container => {
            container.style.display = 'none';
        });
    } else {
        // Show chart containers if they were hidden
        const chartContainers = document.querySelectorAll('.chart-box');
        chartContainers.forEach(container => {
            container.style.display = '';
        });
    }

    try {
        const response = await fetch(`${API_BASE}/api/statistics?days=${days}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Update overview stats (always available)
        updateAnalyticsOverview(data.overview);

        // Render charts only if Chart.js is available
        if (chartJsAvailable) {
            renderDailyTrendsChart(data.daily_trends);
            renderHourlyDistributionChart(data.hourly_distribution);
            renderDispositionChart(data.call_disposition);
            renderQualityChart(data.call_quality);
        }

        // Update top callers table (always available)
        updateTopCallersTable(data.top_callers);

        // Update peak hours display (always available)
        updatePeakHours(data.peak_hours);

        if (chartJsAvailable) {
            showNotification('Analytics refreshed successfully', 'success');
        } else {
            showNotification('Analytics data loaded (charts unavailable - offline mode)', 'info');
        }
    } catch (error) {
        console.error('Error loading analytics:', error);
        showNotification('Failed to load analytics: ' + error.message, 'error');
    }
}

function updateAnalyticsOverview(overview) {
    document.getElementById('analytics-total-calls').textContent = overview.total_calls || 0;
    document.getElementById('analytics-answered-calls').textContent = overview.answered_calls || 0;
    document.getElementById('analytics-answer-rate').textContent = (overview.answer_rate || 0) + '%';
    document.getElementById('analytics-avg-duration').textContent = (overview.avg_call_duration || 0).toFixed(1) + 's';
}

function renderDailyTrendsChart(trends) {
    const ctx = document.getElementById('daily-trends-chart');
    if (!ctx) return;

    // Check if Chart.js is available
    if (!isChartJsAvailable(ctx)) return;

    // Destroy existing chart if it exists
    if (analyticsCharts.dailyTrends) {
        analyticsCharts.dailyTrends.destroy();
    }

    const labels = trends.map(t => t.date);
    const totalData = trends.map(t => t.total_calls);
    const answeredData = trends.map(t => t.answered);
    const missedData = trends.map(t => t.missed);

    analyticsCharts.dailyTrends = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total Calls',
                    data: totalData,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Answered',
                    data: answeredData,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Missed',
                    data: missedData,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function renderHourlyDistributionChart(distribution) {
    const ctx = document.getElementById('hourly-distribution-chart');
    if (!ctx) return;

    // Check if Chart.js is available
    if (!isChartJsAvailable(ctx)) return;

    if (analyticsCharts.hourlyDistribution) {
        analyticsCharts.hourlyDistribution.destroy();
    }

    const labels = distribution.map(d => `${d.hour}:00`);
    const data = distribution.map(d => d.calls);

    analyticsCharts.hourlyDistribution = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Calls by Hour',
                data: data,
                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                borderColor: '#667eea',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function renderDispositionChart(dispositions) {
    const ctx = document.getElementById('disposition-chart');
    if (!ctx) return;

    // Check if Chart.js is available
    if (!isChartJsAvailable(ctx)) return;

    if (analyticsCharts.disposition) {
        analyticsCharts.disposition.destroy();
    }

    const labels = dispositions.map(d => d.disposition);
    const data = dispositions.map(d => d.count);
    const colors = {
        'answered': '#10b981',
        'no_answer': '#f59e0b',
        'busy': '#ef4444',
        'failed': '#6c757d',
        'cancelled': '#3b82f6'
    };

    const backgroundColors = labels.map(label => colors[label] || '#667eea');

    analyticsCharts.disposition = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels.map(l => l.replace('_', ' ').toUpperCase()),
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'right',
                }
            }
        }
    });
}

function renderQualityChart(quality) {
    const ctx = document.getElementById('quality-chart');
    if (!ctx) return;

    // Check if Chart.js is available
    if (!isChartJsAvailable(ctx)) return;

    if (analyticsCharts.quality) {
        analyticsCharts.quality.destroy();
    }

    const qualityDist = quality.quality_distribution || {};

    analyticsCharts.quality = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['MOS Score', 'Jitter (ms)', 'Packet Loss (%)', 'Latency (ms)'],
            datasets: [{
                label: 'Quality Metrics',
                data: [
                    quality.average_mos || 0,
                    quality.average_jitter || 0,
                    quality.average_packet_loss || 0,
                    quality.average_latency || 0
                ],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.6)',
                    'rgba(59, 130, 246, 0.6)',
                    'rgba(239, 68, 68, 0.6)',
                    'rgba(245, 158, 11, 0.6)'
                ],
                borderColor: [
                    '#10b981',
                    '#3b82f6',
                    '#ef4444',
                    '#f59e0b'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function updateTopCallersTable(topCallers) {
    const tbody = document.getElementById('top-callers-table');
    if (!tbody) return;

    if (!topCallers || topCallers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="no-data">No call data available</td></tr>';
        return;
    }

    tbody.innerHTML = topCallers.map(caller => `
        <tr>
            <td><strong>${caller.extension}</strong></td>
            <td>${caller.calls}</td>
            <td>${(caller.total_duration / 60).toFixed(1)}</td>
            <td>${caller.avg_duration.toFixed(1)}</td>
        </tr>
    `).join('');
}

function updatePeakHours(peakHours) {
    const display = document.getElementById('peak-hours-display');
    if (!display) return;

    if (!peakHours || peakHours.length === 0) {
        display.innerHTML = '<p>No peak hours data available</p>';
        return;
    }

    const html = '<ul>' + peakHours.map((peak, index) =>
        `<li><strong>#${index + 1}:</strong> ${peak.hour} with ${peak.calls} calls</li>`
    ).join('') + '</ul>';

    display.innerHTML = html;
}

// ============================================================================
// SSL/HTTPS Configuration Functions
// ============================================================================

async function loadSSLStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/ssl/status`);
        const data = await response.json();

        if (response.ok) {
            updateSSLStatusDisplay(data);

            // Update form fields
            document.getElementById('ssl-enabled').checked = data.enabled;
            document.getElementById('ssl-cert-file').value = data.cert_file || 'certs/server.crt';
            document.getElementById('ssl-key-file').value = data.key_file || 'certs/server.key';

            // Show/hide certificate section based on enabled status
            const certSection = document.getElementById('ssl-certificate-section');
            if (certSection) {
                certSection.style.display = data.enabled ? 'block' : 'none';
            }

            // Show certificate details if available
            if (data.cert_details) {
                displayCertificateDetails(data.cert_details);
            }
        } else {
            console.error('Failed to load SSL status:', data.error);
        }
    } catch (error) {
        console.error('Error loading SSL status:', error);
    }
}

function updateSSLStatusDisplay(data) {
    const statusInfo = document.getElementById('ssl-status-info');
    if (!statusInfo) return;

    let statusHtml = '';

    if (data.enabled) {
        if (data.cert_exists && data.key_exists) {
            if (data.cert_details) {
                const isExpired = data.cert_details.is_expired;
                const daysLeft = data.cert_details.days_until_expiry;

                if (isExpired) {
                    statusHtml = `<p>❌ <strong>HTTPS Enabled</strong> but certificate has <strong>EXPIRED</strong></p>`;
                } else if (daysLeft < 30) {
                    statusHtml = `<p>⚠️ <strong>HTTPS Enabled</strong> - Certificate expires in <strong>${daysLeft} days</strong></p>`;
                } else {
                    statusHtml = `<p>✅ <strong>HTTPS Enabled</strong> - Certificate valid for <strong>${daysLeft} days</strong></p>`;
                }
            } else {
                statusHtml = '<p>✅ <strong>HTTPS Enabled</strong> - Certificate files found</p>';
            }
        } else {
            statusHtml = '<p>⚠️ <strong>HTTPS Enabled</strong> but certificate files are missing</p>';
            if (!data.cert_exists) {
                statusHtml += `<p style="color: #d32f2f;">Missing: ${data.cert_file}</p>`;
            }
            if (!data.key_exists) {
                statusHtml += `<p style="color: #d32f2f;">Missing: ${data.key_file}</p>`;
            }
        }
    } else {
        statusHtml = '<p>⚠️ <strong>HTTPS Disabled</strong> - Using unencrypted HTTP</p>';
    }

    statusInfo.innerHTML = statusHtml;
}

function displayCertificateDetails(details) {
    const certDetailsSection = document.getElementById('cert-details-section');
    if (!certDetailsSection) return;

    certDetailsSection.style.display = 'block';

    document.getElementById('cert-subject').value = details.subject || 'N/A';
    document.getElementById('cert-issuer').value = details.issuer || 'N/A';
    document.getElementById('cert-valid-from').value = formatDate(details.valid_from) || 'N/A';
    document.getElementById('cert-valid-until').value = formatDate(details.valid_until) || 'N/A';

    const daysField = document.getElementById('cert-days-expiry');
    const daysLeft = details.days_until_expiry;

    if (details.is_expired) {
        daysField.value = 'EXPIRED';
        daysField.style.color = '#d32f2f';
        daysField.style.fontWeight = 'bold';
    } else if (daysLeft < 30) {
        daysField.value = `${daysLeft} days (⚠️ Expires soon!)`;
        daysField.style.color = '#ff9800';
        daysField.style.fontWeight = 'bold';
    } else {
        daysField.value = `${daysLeft} days`;
        daysField.style.color = '#4CAF50';
        daysField.style.fontWeight = 'normal';
    }
}

function formatDate(dateString) {
    if (!dateString) return '';
    try {
        const date = new Date(dateString);
        return date.toLocaleString();
    } catch (error) {
        return dateString;
    }
}

async function generateSSLCertificate() {
    const hostname = document.getElementById('ssl-hostname').value.trim();
    const daysValid = parseInt(document.getElementById('ssl-days-valid').value) || 365;

    if (!hostname) {
        alert('Please enter a hostname or IP address');
        return;
    }

    if (!confirm(`Generate self-signed SSL certificate for ${hostname}?\n\nThis will create new certificate files and may overwrite existing ones.`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/ssl/generate-certificate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                hostname: hostname,
                days_valid: daysValid
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert(`✅ SSL certificate generated successfully!\n\n` +
                  `Certificate: ${data.cert_file}\n` +
                  `Private Key: ${data.key_file}\n` +
                  `Valid for: ${data.valid_days} days\n\n` +
                  `⚠️ You must restart the PBX server for HTTPS to take effect.`);

            // Reload SSL status
            await loadSSLStatus();
        } else {
            alert(`❌ Failed to generate certificate: ${data.error}`);
        }
    } catch (error) {
        console.error('Error generating certificate:', error);
        alert(`❌ Error generating certificate: ${error.message}`);
    }
}

async function refreshSSLStatus() {
    await loadSSLStatus();
}

// Initialize SSL config form
function initializeSSLConfigForm() {
    const sslConfigForm = document.getElementById('ssl-config-form');
    if (sslConfigForm) {
        sslConfigForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await saveSSLSettings();
        });
    }

    // Toggle certificate section visibility
    const sslEnabledCheckbox = document.getElementById('ssl-enabled');
    if (sslEnabledCheckbox) {
        sslEnabledCheckbox.addEventListener('change', (e) => {
            const certSection = document.getElementById('ssl-certificate-section');
            if (certSection) {
                certSection.style.display = e.target.checked ? 'block' : 'none';
            }
        });
    }
}

async function saveSSLSettings() {
    const enabled = document.getElementById('ssl-enabled').checked;

    try {
        const response = await fetch(`${API_BASE}/api/config/section`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                section: 'api',
                data: {
                    ssl: {
                        enabled: enabled
                    }
                }
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert('✅ SSL settings saved successfully!\n\n⚠️ Server restart required for changes to take effect.');
            await loadSSLStatus();
        } else {
            alert(`❌ Failed to save SSL settings: ${data.error}`);
        }
    } catch (error) {
        console.error('Error saving SSL settings:', error);
        alert(`❌ Error saving SSL settings: ${error.message}`);
    }
}

// ====================================
// QoS Monitoring Functions
// ====================================

async function loadQoSMetrics() {
    try {
        // Load statistics
        const statsResponse = await fetch(`${API_BASE}/api/qos/statistics`);
        const stats = await statsResponse.json();

        // Update overview stats
        document.getElementById('qos-active-calls').textContent = stats.active_calls || 0;
        document.getElementById('qos-total-calls').textContent = stats.total_calls || 0;
        document.getElementById('qos-avg-mos').textContent = stats.average_mos ? stats.average_mos.toFixed(2) : '-';
        document.getElementById('qos-calls-with-issues').textContent = stats.calls_with_issues || 0;

        // Load active call metrics
        const activeResponse = await fetch(`${API_BASE}/api/qos/metrics`);
        const activeData = await activeResponse.json();
        const activeMetrics = activeData.metrics || [];
        const activeTable = document.getElementById('qos-active-calls-table');

        if (activeMetrics.length === 0) {
            activeTable.innerHTML = '<tr><td colspan="7" class="no-data">No active calls being monitored</td></tr>';
        } else {
            // Group bidirectional calls and detect one-way audio issues
            const callGroups = groupBidirectionalCalls(activeMetrics);
            activeTable.innerHTML = callGroups.map(group => generateCallRowsWithDiagnostics(group)).join('');
        }

        // Load alerts
        const alertsResponse = await fetch(`${API_BASE}/api/qos/alerts`);
        const alertsData = await alertsResponse.json();
        const alerts = alertsData.alerts || [];
        const alertsContainer = document.getElementById('qos-alerts-container');

        if (alerts.length === 0) {
            alertsContainer.innerHTML = '<div class="info-box">✅ No quality alerts</div>';
        } else {
            alertsContainer.innerHTML = alerts.map(alert => `
                <div class="alert-box ${alert.severity}">
                    <strong>[${alert.type}]</strong> ${alert.message}
                    <br><small>Call: ${alert.call_id} | Time: ${new Date(alert.timestamp).toLocaleString()}</small>
                </div>
            `).join('');
        }

        // Load historical metrics
        const historyResponse = await fetch(`${API_BASE}/api/qos/history?limit=50`);
        const historyData = await historyResponse.json();
        const history = historyData.metrics || [];
        const historyTable = document.getElementById('qos-history-table');

        if (history.length === 0) {
            historyTable.innerHTML = '<tr><td colspan="8" class="no-data">No historical data available</td></tr>';
        } else {
            // Group bidirectional calls for history view
            const callGroups = groupBidirectionalCalls(history);
            historyTable.innerHTML = callGroups.map(group => generateCallRowsWithDiagnostics(group, true)).join('');
        }

    } catch (error) {
        console.error('Error loading QoS metrics:', error);
        showNotification('Failed to load QoS metrics', 'error');
    }
}

/**
 * Group bidirectional calls (a_to_b and b_to_a) together
 * Returns an array of call groups, each containing either a single call or paired bidirectional calls
 */
function groupBidirectionalCalls(metrics) {
    const groups = [];
    const processed = new Set();

    for (const call of metrics) {
        if (processed.has(call.call_id)) {
            continue;
        }

        // Check if this is a bidirectional call (ends with _a_to_b or _b_to_a)
        const baseCallId = call.call_id.replace(/_a_to_b$|_b_to_a$/, '');
        const isDirectional = call.call_id.endsWith('_a_to_b') || call.call_id.endsWith('_b_to_a');

        if (isDirectional) {
            // Look for the paired direction
            const pairedCallId = call.call_id.endsWith('_a_to_b')
                ? `${baseCallId}_b_to_a`
                : `${baseCallId}_a_to_b`;

            const pairedCall = metrics.find(c => c.call_id === pairedCallId);

            if (pairedCall) {
                // Both directions found - create a group
                groups.push({
                    baseCallId,
                    isBidirectional: true,
                    a_to_b: call.call_id.endsWith('_a_to_b') ? call : pairedCall,
                    b_to_a: call.call_id.endsWith('_b_to_a') ? call : pairedCall
                });
                processed.add(call.call_id);
                processed.add(pairedCall.call_id);
            } else {
                // Only one direction found
                groups.push({
                    baseCallId,
                    isBidirectional: false,
                    call
                });
                processed.add(call.call_id);
            }
        } else {
            // Not a bidirectional call, treat as standalone
            groups.push({
                baseCallId: call.call_id,
                isBidirectional: false,
                call
            });
            processed.add(call.call_id);
        }
    }

    return groups;
}

/**
 * Generate table rows for a call group with diagnostic information
 */
function generateCallRowsWithDiagnostics(group, includeStartTime = false) {
    if (!group.isBidirectional) {
        // Single direction or non-directional call
        const call = group.call;
        const cols = includeStartTime
            ? `<td>${call.call_id}</td>
               <td>${new Date(call.start_time).toLocaleString()}</td>
               <td>${call.duration_seconds}s</td>`
            : `<td>${call.call_id}</td>
               <td>${call.duration_seconds}s</td>`;

        return `<tr>
            ${cols}
            <td class="${getQualityClass(call.mos_score)}">${call.mos_score.toFixed(2)}</td>
            <td>${call.quality_rating}</td>
            <td>${call.packet_loss_percentage.toFixed(2)}%</td>
            <td>${call.jitter_avg_ms.toFixed(1)}</td>
            <td>${call.latency_avg_ms.toFixed(1)}</td>
        </tr>`;
    }

    // Bidirectional call - show both directions and diagnostics
    const { baseCallId, a_to_b, b_to_a } = group;

    // Detect one-way audio issues (check packets_received exists and is > 0)
    const aToBAudioOK = a_to_b.mos_score > 1.0 && (a_to_b.packets_received || 0) > 0;
    const bToAAudioOK = b_to_a.mos_score > 1.0 && (b_to_a.packets_received || 0) > 0;
    const hasOneWayAudio = !aToBAudioOK || !bToAAudioOK;

    // Diagnostic message templates
    const DIAGNOSTIC_MESSAGES = {
        bothDirections: '⚠️ <strong>No Audio in Both Directions</strong> - No RTP packets received',
        aToB: '⚠️ <strong>One-Way Audio Issue</strong> - No audio A→B (only B→A working)',
        bToA: '⚠️ <strong>One-Way Audio Issue</strong> - No audio B→A (only A→B working)'
    };

    const TROUBLESHOOTING_STEPS = `1) Check firewall/NAT rules for RTP ports (10000-20000)
                    2) Verify symmetric RTP is working
                    3) Check endpoint is sending RTP packets
                    4) Verify network path with tcpdump`;

    // Generate diagnostic message
    let diagnosticHTML = '';
    if (hasOneWayAudio) {
        let issueDesc = '';
        if (!aToBAudioOK && !bToAAudioOK) {
            issueDesc = DIAGNOSTIC_MESSAGES.bothDirections;
        } else if (!aToBAudioOK) {
            issueDesc = DIAGNOSTIC_MESSAGES.aToB;
        } else {
            issueDesc = DIAGNOSTIC_MESSAGES.bToA;
        }

        diagnosticHTML = `<tr class="diagnostic-row">
            <td colspan="${includeStartTime ? 8 : 7}" class="diagnostic-cell">
                <div class="diagnostic-alert">
                    ${issueDesc}
                    <br><small><strong>Troubleshooting:</strong>
                    ${TROUBLESHOOTING_STEPS}
                    </small>
                </div>
            </td>
        </tr>`;
    }

    // Build call ID cell with direction indicator
    const callIdWithDirection = `${baseCallId}<br><small style="color: #6b7280;">↳ A→B</small>`;

    // Generate rows for both directions
    const aToRowCols = includeStartTime
        ? `<td>${callIdWithDirection}</td>
           <td>${new Date(a_to_b.start_time).toLocaleString()}</td>
           <td>${a_to_b.duration_seconds}s</td>`
        : `<td>${callIdWithDirection}</td>
           <td>${a_to_b.duration_seconds}s</td>`;

    const aToRow = `<tr ${!aToBAudioOK ? 'class="one-way-audio-issue"' : ''}>
        ${aToRowCols}
        <td class="${getQualityClass(a_to_b.mos_score)}">${a_to_b.mos_score.toFixed(2)}</td>
        <td>${a_to_b.quality_rating} ${!aToBAudioOK ? '⚠️' : ''}</td>
        <td>${a_to_b.packet_loss_percentage.toFixed(2)}%</td>
        <td>${a_to_b.jitter_avg_ms.toFixed(1)}</td>
        <td>${a_to_b.latency_avg_ms.toFixed(1)}</td>
    </tr>`;

    const bToRow = `<tr ${!bToAAudioOK ? 'class="one-way-audio-issue"' : ''}>
        ${includeStartTime
            ? `<td style="padding-left: 20px;">↳ B→A</td>
               <td>${new Date(b_to_a.start_time).toLocaleString()}</td>
               <td>${b_to_a.duration_seconds}s</td>`
            : `<td style="padding-left: 20px;">↳ B→A</td>
               <td>${b_to_a.duration_seconds}s</td>`}
        <td class="${getQualityClass(b_to_a.mos_score)}">${b_to_a.mos_score.toFixed(2)}</td>
        <td>${b_to_a.quality_rating} ${!bToAAudioOK ? '⚠️' : ''}</td>
        <td>${b_to_a.packet_loss_percentage.toFixed(2)}%</td>
        <td>${b_to_a.jitter_avg_ms.toFixed(1)}</td>
        <td>${b_to_a.latency_avg_ms.toFixed(1)}</td>
    </tr>`;

    return diagnosticHTML + aToRow + bToRow;
}

function getQualityClass(mosScore) {
    if (mosScore >= 4.3) return 'quality-excellent';
    if (mosScore >= 4.0) return 'quality-good';
    if (mosScore >= 3.6) return 'quality-fair';
    if (mosScore >= 3.1) return 'quality-poor';
    return 'quality-bad';
}

async function clearQoSAlerts() {
    if (!confirm('Are you sure you want to clear all QoS alerts?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/qos/clear-alerts`, {
            method: 'POST'
        });

        if (response.ok) {
            showNotification('QoS alerts cleared successfully', 'success');
            await loadQoSMetrics();
        } else {
            showNotification('Failed to clear QoS alerts', 'error');
        }
    } catch (error) {
        console.error('Error clearing QoS alerts:', error);
        showNotification('Error clearing QoS alerts', 'error');
    }
}

async function saveQoSThresholds(event) {
    event.preventDefault();

    const thresholds = {
        mos_min: parseFloat(document.getElementById('qos-threshold-mos').value),
        packet_loss_max: parseFloat(document.getElementById('qos-threshold-loss').value),
        jitter_max: parseFloat(document.getElementById('qos-threshold-jitter').value),
        latency_max: parseFloat(document.getElementById('qos-threshold-latency').value)
    };

    try {
        const response = await fetch(`${API_BASE}/api/qos/thresholds`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(thresholds)
        });

        if (response.ok) {
            showNotification('QoS thresholds updated successfully', 'success');
        } else {
            showNotification('Failed to update QoS thresholds', 'error');
        }
    } catch (error) {
        console.error('Error saving QoS thresholds:', error);
        showNotification('Error saving QoS thresholds', 'error');
    }
}

// ====================================
// Emergency Notification Functions
// ====================================

async function loadEmergencyContacts() {
    try {
        const response = await fetch(`${API_BASE}/api/emergency/contacts`);
        const data = await response.json();

        // Update stats
        document.getElementById('emergency-contacts-count').textContent = data.total || 0;

        // Update contacts table
        const tbody = document.getElementById('emergency-contacts-table');

        if (!data.contacts || data.contacts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="no-data">No emergency contacts configured</td></tr>';
            return;
        }

        tbody.innerHTML = data.contacts.map(contact => {
            const priorityBadge = getPriorityBadge(contact.priority);
            const methods = contact.notification_methods.map(m => {
                const icons = { call: '📞', page: '📢', email: '📧', sms: '💬' };
                return `<span style="margin-right: 5px;" title="${m}">${icons[m] || m}</span>`;
            }).join('');

            return `
                <tr>
                    <td>${priorityBadge}</td>
                    <td><strong>${contact.name}</strong></td>
                    <td>${contact.extension || '-'}</td>
                    <td>${contact.phone || '-'}</td>
                    <td>${contact.email || '-'}</td>
                    <td>${methods}</td>
                    <td>
                        <button class="btn btn-sm btn-danger" onclick="deleteEmergencyContact('${contact.id}', '${contact.name}')">
                            🗑️ Delete
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        // Load notification history
        await loadEmergencyHistory();

    } catch (error) {
        console.error('Error loading emergency contacts:', error);
        showNotification('Failed to load emergency contacts', 'error');
    }
}

function getPriorityBadge(priority) {
    const badges = {
        1: '<span class="badge" style="background: #ef4444;">1 - Highest</span>',
        2: '<span class="badge" style="background: #f97316;">2 - High</span>',
        3: '<span class="badge" style="background: #eab308;">3 - Medium</span>',
        4: '<span class="badge" style="background: #3b82f6;">4 - Low</span>',
        5: '<span class="badge" style="background: #6b7280;">5 - Lowest</span>'
    };
    return badges[priority] || `<span class="badge">${priority}</span>`;
}

async function loadEmergencyHistory() {
    try {
        const response = await fetch(`${API_BASE}/api/emergency/history?limit=20`);
        const data = await response.json();

        // Update notifications sent stat
        document.getElementById('emergency-notifications-sent').textContent = data.total || 0;

        // Update last test
        if (data.history && data.history.length > 0) {
            const lastNotification = data.history[data.history.length - 1];
            const lastTime = new Date(lastNotification.timestamp).toLocaleString();
            document.getElementById('emergency-last-test').textContent = lastTime;
        } else {
            document.getElementById('emergency-last-test').textContent = 'Never';
        }

        // Update history table
        const tbody = document.getElementById('emergency-history-table');

        if (!data.history || data.history.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="no-data">No emergency notifications sent</td></tr>';
            return;
        }

        tbody.innerHTML = data.history.slice().reverse().map(notification => {
            const timestamp = new Date(notification.timestamp).toLocaleString();
            const triggerType = notification.trigger_type;
            const details = JSON.stringify(notification.details);
            const contactsNotified = notification.contacts_notified.join(', ') || 'None';
            const methods = notification.methods_used.join(', ') || 'None';

            return `
                <tr>
                    <td>${timestamp}</td>
                    <td><span class="badge">${triggerType}</span></td>
                    <td title="${details}">${truncate(details, 50)}</td>
                    <td>${contactsNotified}</td>
                    <td>${methods}</td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading emergency history:', error);
    }
}

function truncate(str, length) {
    if (str.length <= length) return str;
    return str.substring(0, length) + '...';
}

function showAddEmergencyContactModal() {
    document.getElementById('add-emergency-contact-modal').style.display = 'block';
    // Reset form
    document.getElementById('add-emergency-contact-form').reset();
    document.getElementById('method-call').checked = true;
}

function closeAddEmergencyContactModal() {
    document.getElementById('add-emergency-contact-modal').style.display = 'none';
}

async function addEmergencyContact(event) {
    event.preventDefault();

    const name = document.getElementById('emergency-contact-name').value;
    const extension = document.getElementById('emergency-contact-extension').value;
    const phone = document.getElementById('emergency-contact-phone').value;
    const email = document.getElementById('emergency-contact-email').value;
    const priority = parseInt(document.getElementById('emergency-contact-priority').value);

    // Get selected notification methods
    const methods = [];
    if (document.getElementById('method-call').checked) methods.push('call');
    if (document.getElementById('method-page').checked) methods.push('page');
    if (document.getElementById('method-email').checked) methods.push('email');
    if (document.getElementById('method-sms').checked) methods.push('sms');

    if (methods.length === 0) {
        showNotification('Please select at least one notification method', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/emergency/contacts`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                extension: extension || null,
                phone: phone || null,
                email: email || null,
                priority: priority,
                notification_methods: methods
            })
        });

        if (response.ok) {
            showNotification('Emergency contact added successfully', 'success');
            closeAddEmergencyContactModal();
            loadEmergencyContacts();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to add emergency contact', 'error');
        }

    } catch (error) {
        console.error('Error adding emergency contact:', error);
        showNotification('Failed to add emergency contact', 'error');
    }
}

async function deleteEmergencyContact(contactId, contactName) {
    if (!confirm(`Delete emergency contact "${contactName}"?\n\nThis contact will no longer receive emergency notifications.`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/emergency/contacts/${contactId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showNotification('Emergency contact deleted successfully', 'success');
            loadEmergencyContacts();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to delete emergency contact', 'error');
        }

    } catch (error) {
        console.error('Error deleting emergency contact:', error);
        showNotification('Failed to delete emergency contact', 'error');
    }
}

function showTriggerEmergencyModal() {
    document.getElementById('trigger-emergency-modal').style.display = 'block';
    document.getElementById('trigger-emergency-form').reset();
}

function closeTriggerEmergencyModal() {
    document.getElementById('trigger-emergency-modal').style.display = 'none';
}

async function triggerEmergency(event) {
    event.preventDefault();

    const triggerType = document.getElementById('trigger-type').value;
    const location = document.getElementById('trigger-details').value;
    const additionalInfo = document.getElementById('trigger-info').value;

    // Extra confirmation for non-test emergencies
    if (triggerType !== 'test') {
        if (!confirm('⚠️ This will send REAL emergency notifications to all contacts.\n\nAre you sure you want to continue?')) {
            return;
        }
    }

    try {
        const response = await fetch(`${API_BASE}/api/emergency/trigger`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                trigger_type: triggerType,
                details: {
                    location: location,
                    additional_info: additionalInfo,
                    triggered_by: 'Admin Panel',
                    timestamp: new Date().toISOString()
                }
            })
        });

        if (response.ok) {
            showNotification('🚨 Emergency notification sent to all contacts', 'success');
            closeTriggerEmergencyModal();
            loadEmergencyContacts();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to trigger emergency notification', 'error');
        }

    } catch (error) {
        console.error('Error triggering emergency:', error);
        showNotification('Failed to trigger emergency notification', 'error');
    }
}

async function testEmergencyNotification() {
    if (!confirm('Test the emergency notification system?\n\nThis will send a clearly marked TEST notification to all configured contacts.')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/emergency/test`);
        const data = await response.json();

        if (data.success) {
            showNotification(`✅ ${data.message}\n\nContacts configured: ${data.contacts_configured}\nMethods: ${data.notification_methods.join(', ')}`, 'success');
            loadEmergencyContacts();
        } else {
            showNotification('Emergency notification test failed', 'error');
        }

    } catch (error) {
        console.error('Error testing emergency notification:', error);
        showNotification('Failed to test emergency notification', 'error');
    }
}

// ====================================
// Codec Management Functions
// ====================================

async function loadCodecStatus() {
    try {
        // For now, show static codec information
        // In production, this would query the PBX for actual codec status

        document.getElementById('codecs-supported').textContent = '4';
        document.getElementById('codecs-enabled').textContent = '3';
        document.getElementById('codecs-active').textContent = '0';
        document.getElementById('codecs-quality').textContent = 'Yes';

        showNotification('Codec status loaded', 'info');

    } catch (error) {
        console.error('Error loading codec status:', error);
        showNotification('Failed to load codec status', 'error');
    }
}

async function saveCodecConfig(event) {
    event.preventDefault();

    const g722Enabled = document.getElementById('codec-g722-enabled').checked;
    const g722Bitrate = parseInt(document.getElementById('codec-g722-bitrate').value);
    const opusEnabled = document.getElementById('codec-opus-enabled').checked;
    const preferenceOrder = document.getElementById('codec-preference-order').value
        .split('\n')
        .map(c => c.trim())
        .filter(c => c.length > 0);

    const codecConfig = {
        codecs: {
            g722: {
                enabled: g722Enabled,
                bitrate: g722Bitrate
            },
            opus: {
                enabled: opusEnabled
            },
            preference_order: preferenceOrder
        }
    };

    try {
        // In production, this would save to config via API
        // For now, just show success message

        console.log('Codec configuration:', codecConfig);

        showNotification('✅ Codec configuration saved\n\n⚠️ PBX restart required for changes to take effect', 'success');

    } catch (error) {
        console.error('Error saving codec config:', error);
        showNotification('Failed to save codec configuration', 'error');
    }
}

// ==================== DTMF Configuration ====================

/**
 * Load current DTMF configuration from server
 */
async function loadDTMFConfig() {
    try {
        const response = await fetch('/api/config/dtmf');

        if (!response.ok) {
            console.error('Failed to load DTMF config:', response.status);
            showNotification('Failed to load DTMF configuration', 'error');
            return;
        }

        const config = await response.json();

        // Populate form fields
        if (document.getElementById('dtmf-mode')) {
            document.getElementById('dtmf-mode').value = config.mode;
        }
        if (document.getElementById('dtmf-payload-type')) {
            document.getElementById('dtmf-payload-type').value = config.payload_type.toString();
        }
        if (document.getElementById('dtmf-duration')) {
            document.getElementById('dtmf-duration').value = config.duration;
        }
        if (document.getElementById('dtmf-sip-info-fallback')) {
            document.getElementById('dtmf-sip-info-fallback').checked = config.sip_info_fallback;
        }
        if (document.getElementById('dtmf-inband-fallback')) {
            document.getElementById('dtmf-inband-fallback').checked = config.inband_fallback;
        }
        if (document.getElementById('dtmf-detection-threshold')) {
            document.getElementById('dtmf-detection-threshold').value = config.detection_threshold;
            document.getElementById('dtmf-threshold-value').textContent = config.detection_threshold;
        }
        if (document.getElementById('dtmf-relay-enabled')) {
            document.getElementById('dtmf-relay-enabled').checked = config.relay_enabled;
        }

        console.log('DTMF configuration loaded:', config);

    } catch (error) {
        console.error('Error loading DTMF config:', error);
        showNotification('Failed to load DTMF configuration', 'error');
    }
}

/**
 * Save DTMF configuration to server
 */
async function saveDTMFConfig(event) {
    event.preventDefault();

    // Get and validate DOM elements
    const modeEl = document.getElementById('dtmf-mode');
    const payloadTypeEl = document.getElementById('dtmf-payload-type');
    const durationEl = document.getElementById('dtmf-duration');
    const sipInfoFallbackEl = document.getElementById('dtmf-sip-info-fallback');
    const inbandFallbackEl = document.getElementById('dtmf-inband-fallback');
    const detectionThresholdEl = document.getElementById('dtmf-detection-threshold');
    const relayEnabledEl = document.getElementById('dtmf-relay-enabled');

    if (!modeEl || !payloadTypeEl || !durationEl || !sipInfoFallbackEl ||
        !inbandFallbackEl || !detectionThresholdEl || !relayEnabledEl) {
        showNotification('Error: DTMF configuration form elements not found', 'error');
        return;
    }

    // Get values from form
    const mode = modeEl.value;
    const payloadType = parseInt(payloadTypeEl.value, 10);
    const duration = parseInt(durationEl.value, 10);
    const sipInfoFallback = sipInfoFallbackEl.checked;
    const inbandFallback = inbandFallbackEl.checked;
    const detectionThreshold = parseFloat(detectionThresholdEl.value);
    const relayEnabled = relayEnabledEl.checked;

    // Validate parsed numbers
    if (isNaN(payloadType) || payloadType < 96 || payloadType > 127) {
        showNotification('Error: Invalid payload type. Must be between 96 and 127', 'error');
        return;
    }
    if (isNaN(duration) || duration < 80 || duration > 500) {
        showNotification('Error: Invalid duration. Must be between 80 and 500ms', 'error');
        return;
    }
    if (isNaN(detectionThreshold) || detectionThreshold < 0.1 || detectionThreshold > 0.9) {
        showNotification('Error: Invalid detection threshold. Must be between 0.1 and 0.9', 'error');
        return;
    }

    const dtmfConfig = {
        dtmf: {
            mode: mode,
            payload_type: payloadType,
            duration: duration,
            sip_info_fallback: sipInfoFallback,
            inband_fallback: inbandFallback,
            detection_threshold: detectionThreshold,
            relay_enabled: relayEnabled
        }
    };

    try {
        const response = await fetch('/api/config/dtmf', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(dtmfConfig)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Use simple message for notification since it uses textContent
            showNotification(
                `✅ DTMF configuration saved (Mode: ${mode}, Payload: ${payloadType}). ⚠️ PBX restart required.`,
                'success'
            );
        } else {
            showNotification(result.error || 'Failed to save DTMF configuration', 'error');
        }

    } catch (error) {
        console.error('Error saving DTMF config:', error);
        showNotification('Failed to save DTMF configuration', 'error');
    }
}

/**
 * Update threshold display value in real-time
 */
function updateDTMFThresholdDisplay() {
    const thresholdSlider = document.getElementById('dtmf-detection-threshold');
    const thresholdValue = document.getElementById('dtmf-threshold-value');

    // Validate both elements exist
    if (!thresholdSlider || !thresholdValue) {
        return;
    }

    // Set initial value
    thresholdValue.textContent = thresholdSlider.value;

    // Add event listener only once (check if already attached)
    if (!thresholdSlider.dataset.listenerAttached) {
        thresholdSlider.addEventListener('input', function() {
            thresholdValue.textContent = this.value;
        });
        thresholdSlider.dataset.listenerAttached = 'true';
    }
}

// Constant for tab loading delay
const TAB_CONTENT_LOAD_DELAY_MS = 100;

// Initialize DTMF threshold display update on page load
document.addEventListener('DOMContentLoaded', function() {
    updateDTMFThresholdDisplay();

    // Load DTMF config when Codecs tab is shown
    const codecsTab = document.querySelector('[data-tab="codecs"]');
    if (codecsTab) {
        codecsTab.addEventListener('click', function() {
            // Small delay to ensure tab content is visible
            setTimeout(loadDTMFConfig, TAB_CONTENT_LOAD_DELAY_MS);
        });
    }

    // Load SIP trunks when SIP Trunks tab is shown
    const trunksTab = document.querySelector('[data-tab="sip-trunks"]');
    if (trunksTab) {
        trunksTab.addEventListener('click', function() {
            setTimeout(loadSIPTrunks, TAB_CONTENT_LOAD_DELAY_MS);
        });
    }

    // Load FMFM when Find Me/Follow Me tab is shown
    const fmfmTab = document.querySelector('[data-tab="find-me-follow-me"]');
    if (fmfmTab) {
        fmfmTab.addEventListener('click', function() {
            setTimeout(loadFMFMExtensions, TAB_CONTENT_LOAD_DELAY_MS);
        });
    }

    // Load time routing when Time-Based Routing tab is shown
    const timeRoutingTab = document.querySelector('[data-tab="time-routing"]');
    if (timeRoutingTab) {
        timeRoutingTab.addEventListener('click', function() {
            setTimeout(loadTimeRoutingRules, TAB_CONTENT_LOAD_DELAY_MS);
        });
    }

    // Load webhooks when Webhooks tab is shown
    const webhooksTab = document.querySelector('[data-tab="webhooks"]');
    if (webhooksTab) {
        webhooksTab.addEventListener('click', function() {
            setTimeout(loadWebhooks, TAB_CONTENT_LOAD_DELAY_MS);
        });
    }

    // Load hot desk sessions when Hot Desking tab is shown
    const hotDeskTab = document.querySelector('[data-tab="hot-desking"]');
    if (hotDeskTab) {
        hotDeskTab.addEventListener('click', function() {
            setTimeout(loadHotDeskSessions, TAB_CONTENT_LOAD_DELAY_MS);
        });
    }

    // Load retention policies when Recording Retention tab is shown
    const retentionTab = document.querySelector('[data-tab="recording-retention"]');
    if (retentionTab) {
        retentionTab.addEventListener('click', function() {
            setTimeout(loadRetentionPolicies, TAB_CONTENT_LOAD_DELAY_MS);
        });
    }

    // Load fraud alerts when Fraud Detection tab is shown
    const fraudTab = document.querySelector('[data-tab="fraud-detection"]');
    if (fraudTab) {
        fraudTab.addEventListener('click', function() {
            setTimeout(loadFraudAlerts, TAB_CONTENT_LOAD_DELAY_MS);
        });
    }
});

// ============================================================================
// SIP Trunk Management Functions
// ============================================================================

function loadSIPTrunks() {
    fetch('/api/sip-trunks')
        .then(response => response.json())
        .then(data => {
            if (data.trunks) {
                // Update stats
                document.getElementById('trunk-total').textContent = data.count || 0;

                const healthyCount = data.trunks.filter(t => t.health_status === 'healthy').length;
                const registeredCount = data.trunks.filter(t => t.status === 'registered').length;
                const totalChannels = data.trunks.reduce((sum, t) => sum + t.channels_available, 0);

                document.getElementById('trunk-healthy').textContent = healthyCount;
                document.getElementById('trunk-registered').textContent = registeredCount;
                document.getElementById('trunk-channels').textContent = totalChannels;

                // Update table
                const tbody = document.getElementById('trunks-list');
                if (data.trunks.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No SIP trunks configured</td></tr>';
                } else {
                    tbody.innerHTML = data.trunks.map(trunk => {
                        const statusBadge = getStatusBadge(trunk.status);
                        const healthBadge = getHealthBadge(trunk.health_status);
                        const successRate = (trunk.success_rate * 100).toFixed(1);

                        return `
                            <tr>
                                <td><strong>${escapeHtml(trunk.name)}</strong><br/><small>${escapeHtml(trunk.trunk_id)}</small></td>
                                <td>${escapeHtml(trunk.host)}:${trunk.port}</td>
                                <td>${statusBadge}</td>
                                <td>${healthBadge}</td>
                                <td>${trunk.priority}</td>
                                <td>${trunk.channels_in_use}/${trunk.max_channels}</td>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 5px;">
                                        <div style="flex: 1; background: #e5e7eb; border-radius: 4px; height: 20px; overflow: hidden;">
                                            <div style="background: ${successRate >= 95 ? '#10b981' : successRate >= 80 ? '#f59e0b' : '#ef4444'}; height: 100%; width: ${successRate}%;"></div>
                                        </div>
                                        <span>${successRate}%</span>
                                    </div>
                                    <small>${trunk.successful_calls}/${trunk.total_calls} calls</small>
                                </td>
                                <td>
                                    <button class="btn-small btn-primary" onclick="testTrunk('${escapeHtml(trunk.trunk_id)}')">🧪 Test</button>
                                    <button class="btn-small btn-danger" onclick="deleteTrunk('${escapeHtml(trunk.trunk_id)}', '${escapeHtml(trunk.name)}')">🗑️</button>
                                </td>
                            </tr>
                        `;
                    }).join('');
                }
            }
        })
        .catch(error => {
            console.error('Error loading SIP trunks:', error);
            showNotification('Error loading SIP trunks', 'error');
        });
}

function getStatusBadge(status) {
    const badges = {
        'registered': '<span class="badge" style="background: #10b981;">✅ Registered</span>',
        'unregistered': '<span class="badge" style="background: #6b7280;">⚪ Unregistered</span>',
        'failed': '<span class="badge" style="background: #ef4444;">❌ Failed</span>',
        'disabled': '<span class="badge" style="background: #9ca3af;">⏸️ Disabled</span>',
        'degraded': '<span class="badge" style="background: #f59e0b;">⚠️ Degraded</span>'
    };
    return badges[status] || status;
}

function getHealthBadge(health) {
    const badges = {
        'healthy': '<span class="badge" style="background: #10b981;">💚 Healthy</span>',
        'warning': '<span class="badge" style="background: #f59e0b;">⚠️ Warning</span>',
        'critical': '<span class="badge" style="background: #f59e0b;">🔴 Critical</span>',
        'down': '<span class="badge" style="background: #ef4444;">💀 Down</span>'
    };
    return badges[health] || health;
}

function loadTrunkHealth() {
    fetch('/api/sip-trunks/health')
        .then(response => response.json())
        .then(data => {
            if (data.health) {
                const section = document.getElementById('trunk-health-section');
                const container = document.getElementById('trunk-health-container');

                section.style.display = 'block';

                container.innerHTML = data.health.map(h => `
                    <div class="config-section" style="margin-bottom: 15px;">
                        <h4>${escapeHtml(h.name)} (${escapeHtml(h.trunk_id)})</h4>
                        <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));">
                            <div class="stat-card">
                                <div class="stat-value">${getHealthBadge(h.health_status)}</div>
                                <div class="stat-label">Health Status</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${(h.success_rate * 100).toFixed(1)}%</div>
                                <div class="stat-label">Success Rate</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${h.consecutive_failures}</div>
                                <div class="stat-label">Consecutive Failures</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${h.average_setup_time.toFixed(2)}s</div>
                                <div class="stat-label">Avg Setup Time</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${h.failover_count}</div>
                                <div class="stat-label">Failover Count</div>
                            </div>
                        </div>
                        <div style="margin-top: 10px;">
                            <p><strong>Total Calls:</strong> ${h.total_calls} (${h.successful_calls} successful, ${h.failed_calls} failed)</p>
                            ${h.last_successful_call ? `<p><strong>Last Success:</strong> ${new Date(h.last_successful_call).toLocaleString()}</p>` : ''}
                            ${h.last_failed_call ? `<p><strong>Last Failure:</strong> ${new Date(h.last_failed_call).toLocaleString()}</p>` : ''}
                            ${h.last_health_check ? `<p><strong>Last Check:</strong> ${new Date(h.last_health_check).toLocaleString()}</p>` : ''}
                        </div>
                    </div>
                `).join('');

                showNotification('Health metrics loaded', 'success');
            }
        })
        .catch(error => {
            console.error('Error loading trunk health:', error);
            showNotification('Error loading trunk health', 'error');
        });
}

function showAddTrunkModal() {
    document.getElementById('add-trunk-modal').style.display = 'block';
}

function closeAddTrunkModal() {
    document.getElementById('add-trunk-modal').style.display = 'none';
    document.getElementById('add-trunk-form').reset();
}

function addSIPTrunk(event) {
    event.preventDefault();

    const selectedCodecs = Array.from(document.querySelectorAll('input[name="trunk-codecs"]:checked'))
        .map(cb => cb.value);

    const trunkData = {
        trunk_id: document.getElementById('trunk-id').value,
        name: document.getElementById('trunk-name').value,
        host: document.getElementById('trunk-host').value,
        port: parseInt(document.getElementById('trunk-port').value),
        username: document.getElementById('trunk-username').value,
        password: document.getElementById('trunk-password').value,
        priority: parseInt(document.getElementById('trunk-priority').value),
        max_channels: parseInt(document.getElementById('trunk-channels').value),
        codec_preferences: selectedCodecs.length > 0 ? selectedCodecs : ['G.711', 'G.729']
    };

    fetch('/api/sip-trunks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(trunkData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Trunk ${trunkData.name} added successfully`, 'success');
            closeAddTrunkModal();
            loadSIPTrunks();
        } else {
            showNotification(data.error || 'Error adding trunk', 'error');
        }
    })
    .catch(error => {
        console.error('Error adding trunk:', error);
        showNotification('Error adding trunk', 'error');
    });
}

function deleteTrunk(trunkId, trunkName) {
    if (!confirm(`Are you sure you want to delete trunk "${trunkName}"?`)) {
        return;
    }

    fetch(`/api/sip-trunks/${trunkId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Trunk ${trunkName} deleted`, 'success');
            loadSIPTrunks();
        } else {
            showNotification(data.error || 'Error deleting trunk', 'error');
        }
    })
    .catch(error => {
        console.error('Error deleting trunk:', error);
        showNotification('Error deleting trunk', 'error');
    });
}

function testTrunk(trunkId) {
    showNotification('Testing trunk...', 'info');

    fetch('/api/sip-trunks/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trunk_id: trunkId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const health = data.health_status;
            showNotification(`Trunk test complete: ${health}`, health === 'healthy' ? 'success' : 'warning');
            loadSIPTrunks();
            loadTrunkHealth();
        } else {
            showNotification(data.error || 'Error testing trunk', 'error');
        }
    })
    .catch(error => {
        console.error('Error testing trunk:', error);
        showNotification('Error testing trunk', 'error');
    });
}

// ============================================================================
// Least-Cost Routing (LCR) Functions
// ============================================================================

function loadLCRRates() {
    fetch('/api/lcr/rates')
        .then(response => response.json())
        .then(data => {
            if (data.rates !== undefined) {
                // Update stats
                document.getElementById('lcr-total-rates').textContent = data.count || 0;
                document.getElementById('lcr-time-rates').textContent = data.time_rates ? data.time_rates.length : 0;

                // Update rate entries table
                const ratesBody = document.getElementById('lcr-rates-list');
                if (data.rates.length === 0) {
                    ratesBody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No rates configured</td></tr>';
                } else {
                    ratesBody.innerHTML = data.rates.map(rate => `
                        <tr>
                            <td><strong>${escapeHtml(rate.trunk_id)}</strong></td>
                            <td><code>${escapeHtml(rate.pattern)}</code></td>
                            <td>${escapeHtml(rate.description)}</td>
                            <td>$${rate.rate_per_minute.toFixed(4)}</td>
                            <td>$${rate.connection_fee.toFixed(4)}</td>
                            <td>${rate.minimum_seconds}s</td>
                            <td>${rate.billing_increment}s</td>
                        </tr>
                    `).join('');
                }

                // Update time-based rates table
                const timeRatesBody = document.getElementById('lcr-time-rates-list');
                if (!data.time_rates || data.time_rates.length === 0) {
                    timeRatesBody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No time-based rates configured</td></tr>';
                } else {
                    timeRatesBody.innerHTML = data.time_rates.map(tr => {
                        const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
                        const days = tr.days_of_week.map(d => dayNames[d]).join(', ');

                        return `
                            <tr>
                                <td><strong>${escapeHtml(tr.name)}</strong></td>
                                <td>${tr.start_time}</td>
                                <td>${tr.end_time}</td>
                                <td>${days}</td>
                                <td>${tr.rate_multiplier}x</td>
                            </tr>
                        `;
                    }).join('');
                }
            }

            // Load statistics
            loadLCRStatistics();
        })
        .catch(error => {
            console.error('Error loading LCR rates:', error);
            showNotification('Error loading LCR rates', 'error');
        });
}

function loadLCRStatistics() {
    fetch('/api/lcr/statistics')
        .then(response => response.json())
        .then(data => {
            // Update stats
            document.getElementById('lcr-total-routes').textContent = data.total_routes || 0;
            document.getElementById('lcr-status').innerHTML = data.enabled ?
                '<span class="badge" style="background: #10b981;">✅ Enabled</span>' :
                '<span class="badge" style="background: #6b7280;">⏸️ Disabled</span>';

            // Update recent decisions table
            const decisionsBody = document.getElementById('lcr-decisions-list');
            if (!data.recent_decisions || data.recent_decisions.length === 0) {
                decisionsBody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No recent decisions</td></tr>';
            } else {
                decisionsBody.innerHTML = data.recent_decisions.map(d => {
                    const timestamp = new Date(d.timestamp).toLocaleString();
                    return `
                        <tr>
                            <td>${timestamp}</td>
                            <td>${escapeHtml(d.number)}</td>
                            <td><strong>${escapeHtml(d.selected_trunk)}</strong></td>
                            <td>$${d.estimated_cost.toFixed(4)}</td>
                            <td>${d.alternatives}</td>
                        </tr>
                    `;
                }).join('');
            }
        })
        .catch(error => {
            console.error('Error loading LCR statistics:', error);
        });
}

function showAddLCRRateModal() {
    const modal = `
        <div id="lcr-rate-modal" class="modal" style="display: block;">
            <div class="modal-content" style="max-width: 600px;">
                <h2>➕ Add LCR Rate</h2>
                <form id="add-lcr-rate-form" onsubmit="addLCRRate(event)">
                    <div class="form-group">
                        <label for="lcr-trunk-id">Trunk ID:</label>
                        <input type="text" id="lcr-trunk-id" required>
                        <small>The SIP trunk ID this rate applies to</small>
                    </div>

                    <div class="form-group">
                        <label for="lcr-pattern">Dial Pattern (Regex):</label>
                        <input type="text" id="lcr-pattern" required placeholder="^\\d{10}$">
                        <small>Regex pattern to match dialed numbers (e.g., ^\\d{10}$ for US local)</small>
                    </div>

                    <div class="form-group">
                        <label for="lcr-description">Description:</label>
                        <input type="text" id="lcr-description" placeholder="US Local Calls">
                    </div>

                    <div class="form-group">
                        <label for="lcr-rate-per-minute">Rate per Minute ($):</label>
                        <input type="number" id="lcr-rate-per-minute" step="0.0001" min="0" required placeholder="0.0100">
                    </div>

                    <div class="form-group">
                        <label for="lcr-connection-fee">Connection Fee ($):</label>
                        <input type="number" id="lcr-connection-fee" step="0.0001" min="0" value="0.0000">
                    </div>

                    <div class="form-group">
                        <label for="lcr-minimum-seconds">Minimum Billable Seconds:</label>
                        <input type="number" id="lcr-minimum-seconds" min="0" value="0">
                    </div>

                    <div class="form-group">
                        <label for="lcr-billing-increment">Billing Increment (seconds):</label>
                        <input type="number" id="lcr-billing-increment" min="1" value="1">
                        <small>Round up billing to this increment (e.g., 6 for 6-second increments)</small>
                    </div>

                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">Add Rate</button>
                        <button type="button" class="btn btn-secondary" onclick="closeLCRRateModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modal);
}

function closeLCRRateModal() {
    const modal = document.getElementById('lcr-rate-modal');
    if (modal) modal.remove();
}

function addLCRRate(event) {
    event.preventDefault();

    const rateData = {
        trunk_id: document.getElementById('lcr-trunk-id').value,
        pattern: document.getElementById('lcr-pattern').value,
        description: document.getElementById('lcr-description').value,
        rate_per_minute: parseFloat(document.getElementById('lcr-rate-per-minute').value),
        connection_fee: parseFloat(document.getElementById('lcr-connection-fee').value),
        minimum_seconds: parseInt(document.getElementById('lcr-minimum-seconds').value),
        billing_increment: parseInt(document.getElementById('lcr-billing-increment').value)
    };

    fetch('/api/lcr/rate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rateData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('LCR rate added successfully', 'success');
            closeLCRRateModal();
            loadLCRRates();
        } else {
            showNotification(data.error || 'Error adding LCR rate', 'error');
        }
    })
    .catch(error => {
        console.error('Error adding LCR rate:', error);
        showNotification('Error adding LCR rate', 'error');
    });
}

function showAddTimeRateModal() {
    const modal = `
        <div id="lcr-time-rate-modal" class="modal" style="display: block;">
            <div class="modal-content" style="max-width: 600px;">
                <h2>⏰ Add Time-Based Rate Modifier</h2>
                <form id="add-time-rate-form" onsubmit="addTimeRate(event)">
                    <div class="form-group">
                        <label for="time-rate-name">Period Name:</label>
                        <input type="text" id="time-rate-name" required placeholder="Peak Hours">
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="time-rate-start-hour">Start Hour (0-23):</label>
                            <input type="number" id="time-rate-start-hour" min="0" max="23" required value="9">
                        </div>
                        <div class="form-group">
                            <label for="time-rate-start-minute">Start Minute:</label>
                            <input type="number" id="time-rate-start-minute" min="0" max="59" required value="0">
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="time-rate-end-hour">End Hour (0-23):</label>
                            <input type="number" id="time-rate-end-hour" min="0" max="23" required value="17">
                        </div>
                        <div class="form-group">
                            <label for="time-rate-end-minute">End Minute:</label>
                            <input type="number" id="time-rate-end-minute" min="0" max="59" required value="0">
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Days of Week:</label>
                        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                            <label><input type="checkbox" name="time-days" value="0" checked> Mon</label>
                            <label><input type="checkbox" name="time-days" value="1" checked> Tue</label>
                            <label><input type="checkbox" name="time-days" value="2" checked> Wed</label>
                            <label><input type="checkbox" name="time-days" value="3" checked> Thu</label>
                            <label><input type="checkbox" name="time-days" value="4" checked> Fri</label>
                            <label><input type="checkbox" name="time-days" value="5"> Sat</label>
                            <label><input type="checkbox" name="time-days" value="6"> Sun</label>
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="time-rate-multiplier">Rate Multiplier:</label>
                        <input type="number" id="time-rate-multiplier" step="0.1" min="0.1" required value="1.0">
                        <small>Multiply rates by this factor during this period (e.g., 1.2 for 20% increase)</small>
                    </div>

                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">Add Time Rate</button>
                        <button type="button" class="btn btn-secondary" onclick="closeTimeRateModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modal);
}

function closeTimeRateModal() {
    const modal = document.getElementById('lcr-time-rate-modal');
    if (modal) modal.remove();
}

function addTimeRate(event) {
    event.preventDefault();

    const selectedDays = Array.from(document.querySelectorAll('input[name="time-days"]:checked'))
        .map(cb => parseInt(cb.value));

    const timeRateData = {
        name: document.getElementById('time-rate-name').value,
        start_hour: parseInt(document.getElementById('time-rate-start-hour').value),
        start_minute: parseInt(document.getElementById('time-rate-start-minute').value),
        end_hour: parseInt(document.getElementById('time-rate-end-hour').value),
        end_minute: parseInt(document.getElementById('time-rate-end-minute').value),
        days: selectedDays,
        multiplier: parseFloat(document.getElementById('time-rate-multiplier').value)
    };

    fetch('/api/lcr/time-rate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(timeRateData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Time-based rate added successfully', 'success');
            closeTimeRateModal();
            loadLCRRates();
        } else {
            showNotification(data.error || 'Error adding time-based rate', 'error');
        }
    })
    .catch(error => {
        console.error('Error adding time-based rate:', error);
        showNotification('Error adding time-based rate', 'error');
    });
}

function clearLCRRates() {
    if (!confirm('Are you sure you want to clear all LCR rates? This cannot be undone.')) {
        return;
    }

    fetch('/api/lcr/clear-rates', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('All LCR rates cleared', 'success');
            loadLCRRates();
        } else {
            showNotification(data.error || 'Error clearing LCR rates', 'error');
        }
    })
    .catch(error => {
        console.error('Error clearing LCR rates:', error);
        showNotification('Error clearing LCR rates', 'error');
    });
}

// ============================================================================
// Find Me/Follow Me Functions
// ============================================================================

function loadFMFMExtensions() {
    fetch('/api/fmfm/extensions', {
        headers: getAuthHeaders()
    })
        .then(response => response.json())
        .then(data => {
            if (data.extensions) {
                // Update stats
                document.getElementById('fmfm-total-extensions').textContent = data.count || 0;

                const sequentialCount = data.extensions.filter(e => e.mode === 'sequential').length;
                const simultaneousCount = data.extensions.filter(e => e.mode === 'simultaneous').length;
                const enabledCount = data.extensions.filter(e => e.enabled !== false).length;

                document.getElementById('fmfm-sequential').textContent = sequentialCount;
                document.getElementById('fmfm-simultaneous').textContent = simultaneousCount;
                document.getElementById('fmfm-enabled').textContent = enabledCount;

                // Update table
                const tbody = document.getElementById('fmfm-list');
                if (data.extensions.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No Find Me/Follow Me configurations</td></tr>';
                } else {
                    tbody.innerHTML = data.extensions.map(config => {
                        const enabled = config.enabled !== false;
                        const modeBadge = config.mode === 'sequential'
                            ? '<span class="badge" style="background: #3b82f6;">⏩ Sequential</span>'
                            : '<span class="badge" style="background: #10b981;">🔀 Simultaneous</span>';
                        const statusBadge = enabled
                            ? '<span class="badge" style="background: #10b981;">✅ Active</span>'
                            : '<span class="badge" style="background: #6b7280;">⏸️ Disabled</span>';

                        const destinations = config.destinations || [];
                        const destList = destinations.map(d =>
                            `${escapeHtml(d.number)}${d.ring_time ? ` (${d.ring_time}s)` : ''}`
                        ).join(', ');

                        const updated = config.updated_at ? new Date(config.updated_at).toLocaleString() : 'N/A';

                        return `
                            <tr>
                                <td><strong>${escapeHtml(config.extension)}</strong></td>
                                <td>${modeBadge}</td>
                                <td>
                                    <div style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(destList)}">
                                        ${destinations.length} destination(s): ${escapeHtml(destList) || 'None'}
                                    </div>
                                </td>
                                <td>${statusBadge}</td>
                                <td><small>${updated}</small></td>
                                <td>
                                    <button class="btn-small btn-primary" data-config='${escapeHtml(JSON.stringify(config))}' onclick="editFMFMConfig(JSON.parse(this.getAttribute('data-config')))">✏️ Edit</button>
                                    <button class="btn-small btn-danger" onclick="deleteFMFMConfig('${escapeHtml(config.extension)}')">🗑️</button>
                                </td>
                            </tr>
                        `;
                    }).join('');
                }
            }
        })
        .catch(error => {
            console.error('Error loading FMFM extensions:', error);
            showNotification('Error loading FMFM configurations', 'error');
        });
}

function showAddFMFMModal() {
    document.getElementById('add-fmfm-modal').style.display = 'block';
    document.getElementById('fmfm-extension').value = '';
    document.getElementById('fmfm-mode').value = 'sequential';
    document.getElementById('fmfm-enabled').checked = true;
    document.getElementById('fmfm-no-answer').value = '';
    document.getElementById('fmfm-destinations-list').innerHTML = '';
    addFMFMDestinationRow();  // Add one empty row
}

function closeAddFMFMModal() {
    document.getElementById('add-fmfm-modal').style.display = 'none';
    document.getElementById('add-fmfm-form').reset();
}

let fmfmDestinationCounter = 0;

function addFMFMDestinationRow() {
    const container = document.getElementById('fmfm-destinations-list');
    const rowId = `fmfm-dest-${fmfmDestinationCounter++}`;

    const row = document.createElement('div');
    row.id = rowId;
    row.style.cssText = 'display: flex; gap: 10px; margin-bottom: 10px; align-items: center;';
    row.innerHTML = `
        <input type="text" class="fmfm-dest-number" placeholder="Phone number or extension" required style="flex: 2;">
        <input type="number" class="fmfm-dest-ringtime" placeholder="Ring time (s)" value="20" min="5" max="120" style="flex: 1;">
        <button type="button" class="btn-small btn-danger" onclick="document.getElementById('${rowId}').remove()">🗑️</button>
    `;
    container.appendChild(row);
}

function saveFMFMConfig(event) {
    event.preventDefault();

    console.log('saveFMFMConfig called');

    const extension = document.getElementById('fmfm-extension').value;
    const mode = document.getElementById('fmfm-mode').value;
    const enabled = document.getElementById('fmfm-enabled').checked;
    const noAnswer = document.getElementById('fmfm-no-answer').value;

    console.log('FMFM form values:', { extension, mode, enabled, noAnswer });

    // Collect destinations
    const destNumbers = Array.from(document.querySelectorAll('.fmfm-dest-number'));
    const destRingTimes = Array.from(document.querySelectorAll('.fmfm-dest-ringtime'));

    const destinations = destNumbers.map((input, idx) => ({
        number: input.value,
        ring_time: parseInt(destRingTimes[idx].value) || 20
    })).filter(d => d.number);

    console.log('FMFM destinations collected:', destinations);

    if (destinations.length === 0) {
        showNotification('At least one destination is required', 'error');
        return;
    }

    const configData = {
        extension: extension,
        mode: mode,
        enabled: enabled,
        destinations: destinations
    };

    if (noAnswer) {
        configData.no_answer_destination = noAnswer;
    }

    console.log('FMFM config data to send:', configData);

    fetch('/api/fmfm/config', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(configData)
    })
    .then(response => {
        console.log('FMFM save response status:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('FMFM save response data:', data);
        if (data.success) {
            showNotification(`FMFM configured for extension ${extension}`, 'success');
            closeAddFMFMModal();
            loadFMFMExtensions();
        } else {
            showNotification(data.error || 'Error configuring FMFM', 'error');
        }
    })
    .catch(error => {
        console.error('Error saving FMFM config:', error);
        displayError(error, 'Saving FMFM configuration');
        showNotification('Error saving FMFM configuration', 'error');
    });
}

function editFMFMConfig(config) {
    showAddFMFMModal();

    document.getElementById('fmfm-extension').value = config.extension;
    document.getElementById('fmfm-extension').readOnly = true;  // Don't allow changing extension
    document.getElementById('fmfm-mode').value = config.mode;
    document.getElementById('fmfm-enabled').checked = config.enabled !== false;
    document.getElementById('fmfm-no-answer').value = config.no_answer_destination || '';

    // Clear and add destination rows
    const container = document.getElementById('fmfm-destinations-list');
    container.innerHTML = '';

    if (config.destinations && config.destinations.length > 0) {
        config.destinations.forEach(dest => {
            addFMFMDestinationRow();
            const rows = container.children;
            const lastRow = rows[rows.length - 1];
            lastRow.querySelector('.fmfm-dest-number').value = dest.number;
            lastRow.querySelector('.fmfm-dest-ringtime').value = dest.ring_time || 20;
        });
    } else {
        addFMFMDestinationRow();
    }
}

function deleteFMFMConfig(extension) {
    if (!confirm(`Are you sure you want to delete FMFM configuration for extension ${extension}?`)) {
        return;
    }

    fetch(`/api/fmfm/config/${extension}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`FMFM configuration deleted for ${extension}`, 'success');
            loadFMFMExtensions();
        } else {
            showNotification(data.error || 'Error deleting FMFM configuration', 'error');
        }
    })
    .catch(error => {
        console.error('Error deleting FMFM config:', error);
        showNotification('Error deleting FMFM configuration', 'error');
    });
}

// ============================================================================
// Time-Based Routing Functions
// ============================================================================

function loadTimeRoutingRules() {
    fetch('/api/time-routing/rules')
        .then(response => response.json())
        .then(data => {
            if (data.rules) {
                // Update stats
                document.getElementById('time-routing-total').textContent = data.count || 0;

                const activeCount = data.rules.filter(r => r.enabled !== false).length;
                const businessCount = data.rules.filter(r =>
                    r.name && (r.name.toLowerCase().includes('business') || r.name.toLowerCase().includes('hours'))
                ).length;
                const afterCount = data.rules.filter(r =>
                    r.name && (r.name.toLowerCase().includes('after') || r.name.toLowerCase().includes('closed'))
                ).length;

                document.getElementById('time-routing-active').textContent = activeCount;
                document.getElementById('time-routing-business').textContent = businessCount;
                document.getElementById('time-routing-after').textContent = afterCount;

                // Update table
                const tbody = document.getElementById('time-routing-list');
                if (data.rules.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No time-based routing rules</td></tr>';
                } else {
                    tbody.innerHTML = data.rules.map(rule => {
                        const enabled = rule.enabled !== false;
                        const statusBadge = enabled
                            ? '<span class="badge" style="background: #10b981;">✅ Active</span>'
                            : '<span class="badge" style="background: #6b7280;">⏸️ Disabled</span>';

                        const conditions = rule.time_conditions || {};
                        const schedule = getScheduleDescription(conditions);

                        return `
                            <tr>
                                <td><strong>${escapeHtml(rule.name)}</strong></td>
                                <td>${escapeHtml(rule.destination)}</td>
                                <td>${escapeHtml(rule.route_to)}</td>
                                <td><small>${escapeHtml(schedule)}</small></td>
                                <td>${rule.priority || 100}</td>
                                <td>${statusBadge}</td>
                                <td>
                                    <button class="btn-small btn-danger" onclick="deleteTimeRoutingRule('${escapeHtml(rule.rule_id)}', '${escapeHtml(rule.name)}')">🗑️</button>
                                </td>
                            </tr>
                        `;
                    }).join('');
                }
            }
        })
        .catch(error => {
            console.error('Error loading time routing rules:', error);
            showNotification('Error loading time routing rules', 'error');
        });
}

function getScheduleDescription(conditions) {
    const parts = [];

    if (conditions.days_of_week) {
        const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        const days = conditions.days_of_week.map(d => dayNames[d]).join(', ');
        parts.push(days);
    }

    if (conditions.start_time && conditions.end_time) {
        parts.push(`${conditions.start_time}-${conditions.end_time}`);
    }

    if (conditions.holidays === true) {
        parts.push('Holidays');
    } else if (conditions.holidays === false) {
        parts.push('Non-holidays');
    }

    return parts.length > 0 ? parts.join(' | ') : 'Always';
}

function showAddTimeRuleModal() {
    document.getElementById('add-time-rule-modal').style.display = 'block';
}

function closeAddTimeRuleModal() {
    document.getElementById('add-time-rule-modal').style.display = 'none';
    document.getElementById('add-time-rule-form').reset();
}

function saveTimeRoutingRule(event) {
    event.preventDefault();

    const name = document.getElementById('time-rule-name').value;
    const destination = document.getElementById('time-rule-destination').value;
    const routeTo = document.getElementById('time-rule-route-to').value;
    const startTime = document.getElementById('time-rule-start').value;
    const endTime = document.getElementById('time-rule-end').value;
    const priority = parseInt(document.getElementById('time-rule-priority').value);
    const enabled = document.getElementById('time-rule-enabled').checked;

    // Collect selected days
    const selectedDays = Array.from(document.querySelectorAll('input[name="time-rule-days"]:checked'))
        .map(cb => parseInt(cb.value));

    if (selectedDays.length === 0) {
        showNotification('Please select at least one day of the week', 'error');
        return;
    }

    const ruleData = {
        name: name,
        destination: destination,
        route_to: routeTo,
        priority: priority,
        enabled: enabled,
        time_conditions: {
            days_of_week: selectedDays,
            start_time: startTime,
            end_time: endTime
        }
    };

    fetch('/api/time-routing/rule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ruleData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Time routing rule "${name}" added successfully`, 'success');
            closeAddTimeRuleModal();
            loadTimeRoutingRules();
        } else {
            showNotification(data.error || 'Error adding time routing rule', 'error');
        }
    })
    .catch(error => {
        console.error('Error saving time routing rule:', error);
        showNotification('Error saving time routing rule', 'error');
    });
}

function deleteTimeRoutingRule(ruleId, ruleName) {
    if (!confirm(`Are you sure you want to delete time routing rule "${ruleName}"?`)) {
        return;
    }

    fetch(`/api/time-routing/rule/${ruleId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Time routing rule "${ruleName}" deleted`, 'success');
            loadTimeRoutingRules();
        } else {
            showNotification(data.error || 'Error deleting time routing rule', 'error');
        }
    })
    .catch(error => {
        console.error('Error deleting time routing rule:', error);
        showNotification('Error deleting time routing rule', 'error');
    });
}

// ============================================================================
// Webhook Functions
// ============================================================================

function loadWebhooks() {
    fetch('/api/webhooks')
        .then(response => response.json())
        .then(data => {
            if (data.subscriptions) {
                const tbody = document.getElementById('webhooks-list');
                if (data.subscriptions.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No webhooks configured</td></tr>';
                } else {
                    tbody.innerHTML = data.subscriptions.map(webhook => {
                        const enabled = webhook.enabled !== false;
                        const statusBadge = enabled
                            ? '<span class="badge" style="background: #10b981;">✅ Active</span>'
                            : '<span class="badge" style="background: #6b7280;">⏸️ Disabled</span>';

                        const events = webhook.event_types || [];
                        const eventList = events.join(', ');
                        const hasSecret = webhook.secret ? '🔒 Yes' : '🔓 No';

                        return `
                            <tr>
                                <td>
                                    <div style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(webhook.url)}">
                                        ${escapeHtml(webhook.url)}
                                    </div>
                                </td>
                                <td>
                                    <div style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(eventList)}">
                                        <small>${escapeHtml(eventList)}</small>
                                    </div>
                                </td>
                                <td>${hasSecret}</td>
                                <td>${statusBadge}</td>
                                <td>
                                    <button class="btn-small btn-danger" onclick="deleteWebhook('${escapeHtml(webhook.url)}')">🗑️</button>
                                </td>
                            </tr>
                        `;
                    }).join('');
                }
            }
        })
        .catch(error => {
            console.error('Error loading webhooks:', error);
            showNotification('Error loading webhooks', 'error');
        });
}

function showAddWebhookModal() {
    document.getElementById('add-webhook-modal').style.display = 'block';
}

function closeAddWebhookModal() {
    document.getElementById('add-webhook-modal').style.display = 'none';
    document.getElementById('add-webhook-form').reset();
}

function addWebhook(event) {
    event.preventDefault();

    const url = document.getElementById('webhook-url').value;
    const secret = document.getElementById('webhook-secret').value;
    const enabled = document.getElementById('webhook-enabled').checked;

    // Collect selected events
    const selectedEvents = Array.from(document.querySelectorAll('input[name="webhook-events"]:checked'))
        .map(cb => cb.value);

    if (selectedEvents.length === 0) {
        showNotification('Please select at least one event type', 'error');
        return;
    }

    const webhookData = {
        url: url,
        event_types: selectedEvents,
        enabled: enabled
    };

    if (secret) {
        webhookData.secret = secret;
    }

    fetch('/api/webhooks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(webhookData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Webhook added successfully', 'success');
            closeAddWebhookModal();
            loadWebhooks();
        } else {
            showNotification(data.error || 'Error adding webhook', 'error');
        }
    })
    .catch(error => {
        console.error('Error adding webhook:', error);
        showNotification('Error adding webhook', 'error');
    });
}

function deleteWebhook(url) {
    if (!confirm(`Are you sure you want to delete webhook for ${url}?`)) {
        return;
    }

    // URL encode the webhook URL for the path
    const encodedUrl = encodeURIComponent(url);

    fetch(`/api/webhooks/${encodedUrl}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Webhook deleted', 'success');
            loadWebhooks();
        } else {
            showNotification(data.error || 'Error deleting webhook', 'error');
        }
    })
    .catch(error => {
        console.error('Error deleting webhook:', error);
        showNotification('Error deleting webhook', 'error');
    });
}

// ============================================================================
// Hot Desking Functions
// ============================================================================

function loadHotDeskSessions() {
    fetch('/api/hot-desk/sessions')
        .then(response => response.json())
        .then(data => {
            if (data.sessions) {
                // Update stats
                const activeSessions = data.sessions.filter(s => s.active !== false);
                document.getElementById('hotdesk-active').textContent = activeSessions.length;
                document.getElementById('hotdesk-total').textContent = data.sessions.length;

                // Update table
                const tbody = document.getElementById('hotdesk-sessions-list');
                if (activeSessions.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No active hot desk sessions</td></tr>';
                } else {
                    tbody.innerHTML = activeSessions.map(session => {
                        const loginTime = session.login_time ? new Date(session.login_time).toLocaleString() : 'N/A';
                        const duration = session.login_time ? getDuration(new Date(session.login_time)) : 'N/A';

                        return `
                            <tr>
                                <td><strong>${escapeHtml(session.extension)}</strong></td>
                                <td>${escapeHtml(session.device_mac || 'N/A')}</td>
                                <td>${escapeHtml(session.device_ip || 'N/A')}</td>
                                <td><small>${loginTime}</small></td>
                                <td>${duration}</td>
                                <td>
                                    <button class="btn-small btn-warning" onclick="logoutHotDesk('${escapeHtml(session.extension)}')">🚪 Logout</button>
                                </td>
                            </tr>
                        `;
                    }).join('');
                }
            }
        })
        .catch(error => {
            console.error('Error loading hot desk sessions:', error);
            showNotification('Error loading hot desk sessions', 'error');
        });
}

function getDuration(startTime) {
    const now = new Date();
    const diff = now - startTime;

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
}

function logoutHotDesk(extension) {
    if (!confirm(`Are you sure you want to log out extension ${extension} from hot desk?`)) {
        return;
    }

    fetch('/api/hot-desk/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ extension: extension })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Extension ${extension} logged out`, 'success');
            loadHotDeskSessions();
        } else {
            showNotification(data.error || 'Error logging out', 'error');
        }
    })
    .catch(error => {
        console.error('Error logging out hot desk:', error);
        showNotification('Error logging out hot desk', 'error');
    });
}

// ============================================================================
// Recording Retention Functions
// ============================================================================

function loadRetentionPolicies() {
    Promise.all([
        fetch('/api/recording-retention/policies'),
        fetch('/api/recording-retention/statistics')
    ])
    .then(([policiesRes, statsRes]) => Promise.all([policiesRes.json(), statsRes.json()]))
    .then(([policiesData, statsData]) => {
        // Update stats
        if (statsData) {
            document.getElementById('retention-policies-count').textContent = statsData.total_policies || 0;
            document.getElementById('retention-recordings').textContent = statsData.total_recordings || 0;
            document.getElementById('retention-deleted').textContent = statsData.deleted_count || 0;
            const lastCleanup = statsData.last_cleanup ? new Date(statsData.last_cleanup).toLocaleDateString() : 'Never';
            document.getElementById('retention-last-cleanup').textContent = lastCleanup;
        }

        // Update policies table
        if (policiesData && policiesData.policies) {
            const tbody = document.getElementById('retention-policies-list');
            if (policiesData.policies.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No retention policies configured</td></tr>';
            } else {
                tbody.innerHTML = policiesData.policies.map(policy => {
                    const created = policy.created_at ? new Date(policy.created_at).toLocaleDateString() : 'N/A';
                    const tags = policy.tags ? policy.tags.join(', ') : 'None';

                    return `
                        <tr>
                            <td><strong>${escapeHtml(policy.name)}</strong></td>
                            <td>${policy.retention_days} days</td>
                            <td><small>${escapeHtml(tags)}</small></td>
                            <td><small>${created}</small></td>
                            <td>
                                <button class="btn-small btn-danger" onclick="deleteRetentionPolicy('${escapeHtml(policy.policy_id)}', '${escapeHtml(policy.name)}')">🗑️</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
    })
    .catch(error => {
        console.error('Error loading retention policies:', error);
        showNotification('Error loading retention policies', 'error');
    });
}

function showAddRetentionPolicyModal() {
    document.getElementById('add-retention-policy-modal').style.display = 'block';
}

function closeAddRetentionPolicyModal() {
    document.getElementById('add-retention-policy-modal').style.display = 'none';
    document.getElementById('add-retention-policy-form').reset();
}

function addRetentionPolicy(event) {
    event.preventDefault();

    const name = document.getElementById('retention-policy-name').value;
    const retentionDays = parseInt(document.getElementById('retention-days').value);
    const tagsInput = document.getElementById('retention-tags').value;

    // Validate input
    if (!name.match(/^[a-zA-Z0-9_\s-]+$/)) {
        showNotification('Policy name contains invalid characters', 'error');
        return;
    }

    if (retentionDays < 1 || retentionDays > 3650) {
        showNotification('Retention days must be between 1 and 3650', 'error');
        return;
    }

    const policyData = {
        name: name,
        retention_days: retentionDays
    };

    // Parse tags if provided
    if (tagsInput.trim()) {
        policyData.tags = tagsInput.split(',').map(t => t.trim()).filter(t => t);
    }

    fetch('/api/recording-retention/policy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(policyData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Retention policy "${name}" added successfully`, 'success');
            closeAddRetentionPolicyModal();
            loadRetentionPolicies();
        } else {
            showNotification(data.error || 'Error adding retention policy', 'error');
        }
    })
    .catch(error => {
        console.error('Error adding retention policy:', error);
        showNotification('Error adding retention policy', 'error');
    });
}

function deleteRetentionPolicy(policyId, policyName) {
    if (!confirm(`Are you sure you want to delete retention policy "${policyName}"?`)) {
        return;
    }

    fetch(`/api/recording-retention/policy/${encodeURIComponent(policyId)}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Retention policy "${policyName}" deleted`, 'success');
            loadRetentionPolicies();
        } else {
            showNotification(data.error || 'Error deleting retention policy', 'error');
        }
    })
    .catch(error => {
        console.error('Error deleting retention policy:', error);
        showNotification('Error deleting retention policy', 'error');
    });
}

// ============================================================================
// Fraud Detection Functions
// ============================================================================

function loadFraudAlerts() {
    Promise.all([
        fetch('/api/fraud-detection/alerts?hours=24'),
        fetch('/api/fraud-detection/statistics')
    ])
    .then(([alertsRes, statsRes]) => Promise.all([alertsRes.json(), statsRes.json()]))
    .then(([alertsData, statsData]) => {
        // Update stats
        if (statsData) {
            document.getElementById('fraud-total-alerts').textContent = statsData.total_alerts || 0;
            document.getElementById('fraud-high-risk').textContent = statsData.high_risk_alerts || 0;
            document.getElementById('fraud-blocked-patterns').textContent = statsData.blocked_patterns_count || 0;
            document.getElementById('fraud-extensions-flagged').textContent = statsData.extensions_flagged || 0;
        }

        // Update alerts table
        if (alertsData && alertsData.alerts) {
            const tbody = document.getElementById('fraud-alerts-list');
            if (alertsData.alerts.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No fraud alerts detected</td></tr>';
            } else {
                tbody.innerHTML = alertsData.alerts.map(alert => {
                    const timestamp = new Date(alert.timestamp).toLocaleString();
                    const scoreColor = alert.fraud_score > 0.8 ? '#ef4444' : alert.fraud_score > 0.5 ? '#f59e0b' : '#10b981';
                    const scorePercent = (alert.fraud_score * 100).toFixed(0);
                    const alertTypes = (alert.alert_types || []).join(', ');

                    return `
                        <tr>
                            <td><small>${timestamp}</small></td>
                            <td><strong>${escapeHtml(alert.extension)}</strong></td>
                            <td><small>${escapeHtml(alertTypes)}</small></td>
                            <td>
                                <div style="display: flex; align-items: center; gap: 5px;">
                                    <div style="flex: 1; background: #e5e7eb; border-radius: 4px; height: 20px; overflow: hidden;">
                                        <div style="background: ${scoreColor}; height: 100%; width: ${scorePercent}%;"></div>
                                    </div>
                                    <span>${scorePercent}%</span>
                                </div>
                            </td>
                            <td><small>${escapeHtml(alert.details || 'No details')}</small></td>
                        </tr>
                    `;
                }).join('');
            }
        }

        // Load blocked patterns from statistics response
        if (statsData && statsData.blocked_patterns) {
            const tbody = document.getElementById('blocked-patterns-list');
            if (statsData.blocked_patterns.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3" style="text-align: center;">No blocked patterns</td></tr>';
            } else {
                tbody.innerHTML = statsData.blocked_patterns.map((pattern, index) => `
                    <tr>
                        <td><code>${escapeHtml(pattern.pattern)}</code></td>
                        <td>${escapeHtml(pattern.reason)}</td>
                        <td>
                            <button class="btn-small btn-danger" onclick="deleteBlockedPattern(${index}, '${escapeHtml(pattern.pattern)}')">🗑️</button>
                        </td>
                    </tr>
                `).join('');
            }
        }
    })
    .catch(error => {
        console.error('Error loading fraud detection data:', error);
        showNotification('Error loading fraud detection data', 'error');
    });
}

function showAddBlockedPatternModal() {
    document.getElementById('add-blocked-pattern-modal').style.display = 'block';
}

function closeAddBlockedPatternModal() {
    document.getElementById('add-blocked-pattern-modal').style.display = 'none';
    document.getElementById('add-blocked-pattern-form').reset();
}

function addBlockedPattern(event) {
    event.preventDefault();

    const pattern = document.getElementById('blocked-pattern').value;
    const reason = document.getElementById('blocked-reason').value;

    // Client-side validation: test if pattern is a valid regex
    try {
        new RegExp(pattern);
    } catch (e) {
        showNotification('Invalid regex pattern: ' + e.message, 'error');
        return;
    }

    const patternData = {
        pattern: pattern,
        reason: reason
    };

    fetch('/api/fraud-detection/blocked-pattern', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patternData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Blocked pattern added successfully', 'success');
            closeAddBlockedPatternModal();
            loadFraudAlerts();
        } else {
            showNotification(data.error || 'Error adding blocked pattern', 'error');
        }
    })
    .catch(error => {
        console.error('Error adding blocked pattern:', error);
        showNotification('Error adding blocked pattern', 'error');
    });
}

function deleteBlockedPattern(patternIndex, pattern) {
    if (!confirm(`Are you sure you want to unblock pattern "${pattern}"?`)) {
        return;
    }

    fetch(`/api/fraud-detection/blocked-pattern/${patternIndex}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Blocked pattern removed', 'success');
            loadFraudAlerts();
        } else {
            showNotification(data.error || 'Error removing blocked pattern', 'error');
        }
    })
    .catch(error => {
        console.error('Error removing blocked pattern:', error);
        showNotification('Error removing blocked pattern', 'error');
    });
}

// Callback Queue Functions
function loadCallbackQueue() {
    Promise.all([
        fetch('/api/callback-queue/list'),
        fetch('/api/callback-queue/statistics')
    ])
    .then(([listRes, statsRes]) => Promise.all([listRes.json(), statsRes.json()]))
    .then(([listData, statsData]) => {
        // Update statistics
        if (statsData) {
            document.getElementById('callback-total').textContent = statsData.total_callbacks || 0;

            const statusBreakdown = statsData.status_breakdown || {};
            document.getElementById('callback-scheduled').textContent = statusBreakdown.scheduled || 0;
            document.getElementById('callback-in-progress').textContent = statusBreakdown.in_progress || 0;
            document.getElementById('callback-completed').textContent = statusBreakdown.completed || 0;
            document.getElementById('callback-failed').textContent = statusBreakdown.failed || 0;
        }

        // Update callback list table
        if (listData && listData.callbacks) {
            const tbody = document.getElementById('callback-list');
            if (listData.callbacks.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No callbacks in queue</td></tr>';
            } else {
                tbody.innerHTML = listData.callbacks.map(callback => {
                    const requestedTime = new Date(callback.requested_at).toLocaleString();
                    const callbackTime = new Date(callback.callback_time).toLocaleString();

                    // Status badge color
                    let statusClass = '';
                    switch(callback.status) {
                        case 'scheduled': statusClass = 'badge-info'; break;
                        case 'in_progress': statusClass = 'badge-warning'; break;
                        case 'completed': statusClass = 'badge-success'; break;
                        case 'failed': statusClass = 'badge-danger'; break;
                        case 'cancelled': statusClass = 'badge-secondary'; break;
                        default: statusClass = 'badge-info';
                    }

                    return `
                        <tr>
                            <td><code>${escapeHtml(callback.callback_id)}</code></td>
                            <td>${escapeHtml(callback.queue_id)}</td>
                            <td>
                                <strong>${escapeHtml(callback.caller_number)}</strong><br>
                                <small>${escapeHtml(callback.caller_name || 'N/A')}</small>
                            </td>
                            <td><small>${requestedTime}</small></td>
                            <td><small>${callbackTime}</small></td>
                            <td><span class="badge ${statusClass}">${escapeHtml(callback.status)}</span></td>
                            <td>${callback.attempts}</td>
                            <td>
                                ${callback.status === 'scheduled' ? `
                                    <button class="btn-small btn-primary" onclick="startCallback('${escapeHtml(callback.callback_id)}')">▶️ Start</button>
                                    <button class="btn-small btn-danger" onclick="cancelCallback('${escapeHtml(callback.callback_id)}')">❌</button>
                                ` : callback.status === 'in_progress' ? `
                                    <button class="btn-small btn-success" onclick="completeCallback('${escapeHtml(callback.callback_id)}', true)">✅ Done</button>
                                    <button class="btn-small btn-warning" onclick="completeCallback('${escapeHtml(callback.callback_id)}', false)">🔄 Retry</button>
                                ` : '-'}
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
    })
    .catch(error => {
        console.error('Error loading callback queue:', error);
        showNotification('Error loading callback queue', 'error');
    });
}

function showRequestCallbackModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'request-callback-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="closeRequestCallbackModal()">&times;</span>
            <h2>📞 Request Callback</h2>
            <form id="request-callback-form" onsubmit="requestCallback(event)">
                <div class="form-group">
                    <label for="callback-queue-id">Queue ID: *</label>
                    <input type="text" id="callback-queue-id" required
                           placeholder="e.g., sales, support, general">
                </div>
                <div class="form-group">
                    <label for="callback-caller-number">Caller Number: *</label>
                    <input type="tel" id="callback-caller-number" required
                           placeholder="e.g., +1234567890">
                </div>
                <div class="form-group">
                    <label for="callback-caller-name">Caller Name:</label>
                    <input type="text" id="callback-caller-name"
                           placeholder="Optional">
                </div>
                <div class="form-group">
                    <label for="callback-preferred-time">Preferred Time:</label>
                    <input type="datetime-local" id="callback-preferred-time">
                    <small>Leave empty for ASAP callback</small>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeRequestCallbackModal()">Cancel</button>
                    <button type="submit" class="btn btn-success">Request Callback</button>
                </div>
            </form>
        </div>
    `;
    document.body.appendChild(modal);
    modal.style.display = 'block';
}

function closeRequestCallbackModal() {
    const modal = document.getElementById('request-callback-modal');
    if (modal) {
        modal.remove();
    }
}

function requestCallback(event) {
    event.preventDefault();

    const queueId = document.getElementById('callback-queue-id').value;
    const callerNumber = document.getElementById('callback-caller-number').value;
    const callerName = document.getElementById('callback-caller-name').value;
    const preferredTime = document.getElementById('callback-preferred-time').value;

    const callbackData = {
        queue_id: queueId,
        caller_number: callerNumber
    };

    if (callerName) {
        callbackData.caller_name = callerName;
    }

    if (preferredTime) {
        // Convert to ISO format
        callbackData.preferred_time = new Date(preferredTime).toISOString();
    }

    fetch('/api/callback-queue/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(callbackData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Callback requested successfully', 'success');
            closeRequestCallbackModal();
            loadCallbackQueue();
        } else {
            showNotification(data.error || 'Error requesting callback', 'error');
        }
    })
    .catch(error => {
        console.error('Error requesting callback:', error);
        showNotification('Error requesting callback', 'error');
    });
}

function startCallback(callbackId) {
    // Prompt for agent ID
    const agentId = prompt('Enter your agent ID/extension:');
    if (!agentId) {
        return;
    }

    fetch('/api/callback-queue/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            callback_id: callbackId,
            agent_id: agentId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Started callback to ${data.caller_number}`, 'success');
            loadCallbackQueue();
        } else {
            showNotification(data.error || 'Error starting callback', 'error');
        }
    })
    .catch(error => {
        console.error('Error starting callback:', error);
        showNotification('Error starting callback', 'error');
    });
}

function completeCallback(callbackId, success) {
    let notes = '';
    if (!success) {
        notes = prompt('Enter reason for failure (optional):') || '';
    }

    fetch('/api/callback-queue/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            callback_id: callbackId,
            success: success,
            notes: notes
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(success ? 'Callback completed' : 'Callback will be retried', 'success');
            loadCallbackQueue();
        } else {
            showNotification(data.error || 'Error completing callback', 'error');
        }
    })
    .catch(error => {
        console.error('Error completing callback:', error);
        showNotification('Error completing callback', 'error');
    });
}

function cancelCallback(callbackId) {
    if (!confirm('Are you sure you want to cancel this callback request?')) {
        return;
    }

    fetch('/api/callback-queue/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            callback_id: callbackId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Callback cancelled', 'success');
            loadCallbackQueue();
        } else {
            showNotification(data.error || 'Error cancelling callback', 'error');
        }
    })
    .catch(error => {
        console.error('Error cancelling callback:', error);
        showNotification('Error cancelling callback', 'error');
    });
}

// Mobile Push Notification Functions
function loadMobilePushDevices() {
    Promise.all([
        fetch('/api/mobile-push/devices'),
        fetch('/api/mobile-push/statistics'),
        fetch('/api/mobile-push/history')
    ])
    .then(([devicesRes, statsRes, historyRes]) => Promise.all([devicesRes.json(), statsRes.json(), historyRes.json()]))
    .then(([devicesData, statsData, historyData]) => {
        // Update statistics
        if (statsData) {
            document.getElementById('push-total-devices').textContent = statsData.total_devices || 0;
            document.getElementById('push-total-users').textContent = statsData.total_users || 0;

            const platforms = statsData.platforms || {};
            document.getElementById('push-ios-devices').textContent = platforms.ios || 0;
            document.getElementById('push-android-devices').textContent = platforms.android || 0;
            document.getElementById('push-recent-notifications').textContent = statsData.recent_notifications || 0;
        }

        // Update devices table
        if (devicesData && devicesData.devices) {
            const tbody = document.getElementById('mobile-devices-list');
            if (devicesData.devices.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No devices registered</td></tr>';
            } else {
                tbody.innerHTML = devicesData.devices.map(device => {
                    const registeredTime = new Date(device.registered_at).toLocaleString();
                    const lastSeenTime = new Date(device.last_seen).toLocaleString();

                    let platformBadge = '';
                    if (device.platform === 'ios') {
                        platformBadge = '<span class="badge badge-info">📱 iOS</span>';
                    } else if (device.platform === 'android') {
                        platformBadge = '<span class="badge badge-success">🤖 Android</span>';
                    } else {
                        platformBadge = `<span class="badge badge-secondary">${escapeHtml(device.platform)}</span>`;
                    }

                    return `
                        <tr>
                            <td><strong>${escapeHtml(device.user_id)}</strong></td>
                            <td>${platformBadge}</td>
                            <td><small>${registeredTime}</small></td>
                            <td><small>${lastSeenTime}</small></td>
                            <td>
                                <button class="btn-small btn-primary" onclick="sendTestNotification('${escapeHtml(device.user_id)}')">🧪 Test</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }

        // Update history table
        if (historyData && historyData.history) {
            const tbody = document.getElementById('push-history-list');
            if (historyData.history.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No notifications sent</td></tr>';
            } else {
                tbody.innerHTML = historyData.history.slice(0, 50).map(notif => {
                    const sentTime = new Date(notif.sent_at).toLocaleString();
                    const successCount = notif.success_count || 0;
                    const failureCount = notif.failure_count || 0;

                    return `
                        <tr>
                            <td>${escapeHtml(notif.user_id)}</td>
                            <td><strong>${escapeHtml(notif.title)}</strong></td>
                            <td><small>${escapeHtml(notif.body)}</small></td>
                            <td><small>${sentTime}</small></td>
                            <td>
                                <span class="badge badge-success">${successCount} ✓</span>
                                ${failureCount > 0 ? `<span class="badge badge-danger">${failureCount} ✗</span>` : ''}
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
    })
    .catch(error => {
        console.error('Error loading mobile push data:', error);
        showNotification('Error loading mobile push data', 'error');
    });
}

function showRegisterDeviceModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'register-device-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="closeRegisterDeviceModal()">&times;</span>
            <h2>📱 Register Mobile Device</h2>
            <form id="register-device-form" onsubmit="registerDevice(event)">
                <div class="form-group">
                    <label for="device-user-id">User ID / Extension: *</label>
                    <input type="text" id="device-user-id" required
                           placeholder="e.g., 1001 or user@example.com">
                </div>
                <div class="form-group">
                    <label for="device-token">Device Token: *</label>
                    <textarea id="device-token" required rows="4"
                              placeholder="FCM device registration token"></textarea>
                    <small>Obtain from mobile app after FCM SDK initialization</small>
                </div>
                <div class="form-group">
                    <label for="device-platform">Platform: *</label>
                    <select id="device-platform" required>
                        <option value="">Select Platform</option>
                        <option value="ios">iOS</option>
                        <option value="android">Android</option>
                        <option value="other">Other</option>
                    </select>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeRegisterDeviceModal()">Cancel</button>
                    <button type="submit" class="btn btn-success">Register Device</button>
                </div>
            </form>
        </div>
    `;
    document.body.appendChild(modal);
    modal.style.display = 'block';
}

function closeRegisterDeviceModal() {
    const modal = document.getElementById('register-device-modal');
    if (modal) {
        modal.remove();
    }
}

function registerDevice(event) {
    event.preventDefault();

    const userId = document.getElementById('device-user-id').value;
    const deviceToken = document.getElementById('device-token').value.trim();
    const platform = document.getElementById('device-platform').value;

    const deviceData = {
        user_id: userId,
        device_token: deviceToken,
        platform: platform
    };

    fetch('/api/mobile-push/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(deviceData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Device registered successfully', 'success');
            closeRegisterDeviceModal();
            loadMobilePushDevices();
        } else {
            showNotification(data.error || 'Error registering device', 'error');
        }
    })
    .catch(error => {
        console.error('Error registering device:', error);
        showNotification('Error registering device', 'error');
    });
}

function showTestNotificationModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'test-notification-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="closeTestNotificationModal()">&times;</span>
            <h2>🧪 Send Test Notification</h2>
            <form id="test-notification-form" onsubmit="sendTestNotificationForm(event)">
                <div class="form-group">
                    <label for="test-user-id">User ID / Extension: *</label>
                    <input type="text" id="test-user-id" required
                           placeholder="e.g., 1001 or user@example.com">
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeTestNotificationModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Send Test</button>
                </div>
            </form>
        </div>
    `;
    document.body.appendChild(modal);
    modal.style.display = 'block';
}

function closeTestNotificationModal() {
    const modal = document.getElementById('test-notification-modal');
    if (modal) {
        modal.remove();
    }
}

function sendTestNotificationForm(event) {
    event.preventDefault();
    const userId = document.getElementById('test-user-id').value;
    sendTestNotification(userId);
    closeTestNotificationModal();
}

function sendTestNotification(userId) {
    fetch('/api/mobile-push/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success || data.stub_mode) {
            if (data.stub_mode) {
                showNotification('Test notification logged (Firebase not configured)', 'warning');
            } else {
                showNotification(`Test notification sent: ${data.success_count} succeeded, ${data.failure_count} failed`, 'success');
            }
            loadMobilePushDevices();
        } else {
            showNotification(data.error || 'Error sending test notification', 'error');
        }
    })
    .catch(error => {
        console.error('Error sending test notification:', error);
        showNotification('Error sending test notification', 'error');
    });
}

// Recording Announcements Functions
function loadRecordingAnnouncementsStats() {
    Promise.all([
        fetch('/api/recording-announcements/statistics'),
        fetch('/api/recording-announcements/config')
    ])
    .then(([statsRes, configRes]) => Promise.all([statsRes.json(), configRes.json()]))
    .then(([statsData, configData]) => {
        // Update statistics
        if (statsData) {
            document.getElementById('announcements-enabled').textContent = statsData.enabled ? '✅ Enabled' : '❌ Disabled';
            document.getElementById('announcements-played').textContent = statsData.announcements_played || 0;
            document.getElementById('consent-accepted').textContent = statsData.consent_accepted || 0;
            document.getElementById('consent-declined').textContent = statsData.consent_declined || 0;

            document.getElementById('announcement-type').textContent = statsData.announcement_type || 'N/A';
            document.getElementById('require-consent').textContent = statsData.require_consent ? 'Yes' : 'No';
        }

        // Update configuration
        if (configData) {
            document.getElementById('audio-file-path').textContent = configData.audio_path || 'N/A';
            document.getElementById('announcement-text').textContent = configData.announcement_text || 'N/A';
        }
    })
    .catch(error => {
        console.error('Error loading recording announcements data:', error);
        showNotification('Error loading recording announcements data', 'error');
    });
}

// ============================================================================
// Speech Analytics Functions
// ============================================================================

function loadSpeechAnalyticsConfigs() {
    fetch('/api/framework/speech-analytics/configs', {
        headers: getAuthHeaders()
    })
    .then(response => response.json())
    .then(data => {
        const tableBody = document.getElementById('speech-analytics-configs-table');
        if (!data.configs || data.configs.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="loading">No extension-specific configurations. Using system defaults.</td></tr>';
            return;
        }

        tableBody.innerHTML = data.configs.map(config => `
            <tr>
                <td>${config.extension}</td>
                <td>${config.transcription_enabled ? '✅ Enabled' : '❌ Disabled'}</td>
                <td>${config.sentiment_enabled ? '✅ Enabled' : '❌ Disabled'}</td>
                <td>${config.summarization_enabled ? '✅ Enabled' : '❌ Disabled'}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editSpeechAnalyticsConfig('${config.extension}')">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteSpeechAnalyticsConfig('${config.extension}')">Delete</button>
                </td>
            </tr>
        `).join('');
    })
    .catch(error => {
        console.error('Error loading speech analytics configs:', error);
        showNotification('Error loading speech analytics configurations', 'error');
    });
}

// Handle speech analytics config form submission
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('speech-analytics-config-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();

            const config = {
                enabled: document.getElementById('speech-analytics-enabled').checked,
                engine: document.getElementById('speech-engine').value,
                sentiment_enabled: document.getElementById('sentiment-analysis-enabled').checked,
                summarization_enabled: document.getElementById('call-summarization-enabled').checked
            };

            fetch('/api/framework/speech-analytics/config', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(config)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Speech analytics configuration saved successfully', 'success');
                } else {
                    showNotification(data.error || 'Error saving configuration', 'error');
                }
            })
            .catch(error => {
                console.error('Error saving speech analytics config:', error);
                showNotification('Error saving configuration', 'error');
            });
        });
    }
});

// ============================================================================
// CRM Integration Functions (HubSpot & Zendesk)
// ============================================================================

function loadCRMActivityLog() {
    fetch('/api/framework/integrations/activity-log', {
        headers: getAuthHeaders()
    })
    .then(response => response.json())
    .then(data => {
        const tableBody = document.getElementById('crm-activity-log-table');
        if (!data.activities || data.activities.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="loading">No integration activity yet</td></tr>';
            return;
        }

        tableBody.innerHTML = data.activities.map(activity => {
            const statusClass = activity.status === 'success' ? 'success' : 'error';
            const statusIcon = activity.status === 'success' ? '✅' : '❌';
            return `
                <tr>
                    <td>${new Date(activity.timestamp).toLocaleString()}</td>
                    <td>${activity.integration}</td>
                    <td>${activity.action}</td>
                    <td class="${statusClass}">${statusIcon} ${activity.status}</td>
                    <td>${activity.details || '-'}</td>
                </tr>
            `;
        }).join('');
    })
    .catch(error => {
        console.error('Error loading CRM activity log:', error);
        showNotification('Error loading CRM activity log', 'error');
    });
}

function clearCRMActivityLog() {
    if (!confirm('Clear old activity log entries? This will remove entries older than 30 days.')) {
        return;
    }

    fetch('/api/framework/integrations/activity-log/clear', {
        method: 'POST',
        headers: getAuthHeaders()
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Cleared ${data.deleted_count} old entries`, 'success');
            loadCRMActivityLog();
        } else {
            showNotification(data.error || 'Error clearing activity log', 'error');
        }
    })
    .catch(error => {
        console.error('Error clearing CRM activity log:', error);
        showNotification('Error clearing activity log', 'error');
    });
}

// Handle HubSpot config form submission
document.addEventListener('DOMContentLoaded', function() {
    const hubspotForm = document.getElementById('hubspot-config-form');
    if (hubspotForm) {
        // Toggle settings visibility
        const hubspotEnabled = document.getElementById('hubspot-enabled');
        const hubspotSettings = document.getElementById('hubspot-settings');
        if (hubspotEnabled) {
            hubspotEnabled.addEventListener('change', function() {
                hubspotSettings.style.display = this.checked ? 'block' : 'none';
            });
        }

        hubspotForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const config = {
                enabled: document.getElementById('hubspot-enabled').checked,
                api_key: document.getElementById('hubspot-api-key').value,
                portal_id: document.getElementById('hubspot-portal-id').value,
                sync_contacts: document.getElementById('hubspot-sync-contacts').checked,
                create_deals: document.getElementById('hubspot-create-deals').checked,
                log_calls: document.getElementById('hubspot-log-calls').checked
            };

            fetch('/api/framework/integrations/hubspot/config', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(config)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('HubSpot configuration saved successfully', 'success');
                } else {
                    showNotification(data.error || 'Error saving HubSpot configuration', 'error');
                }
            })
            .catch(error => {
                console.error('Error saving HubSpot config:', error);
                showNotification('Error saving HubSpot configuration', 'error');
            });
        });
    }
});

// Handle Zendesk config form submission
document.addEventListener('DOMContentLoaded', function() {
    const zendeskForm = document.getElementById('zendesk-config-form');
    if (zendeskForm) {
        // Toggle settings visibility
        const zendeskEnabled = document.getElementById('zendesk-enabled');
        const zendeskSettings = document.getElementById('zendesk-settings');
        if (zendeskEnabled) {
            zendeskEnabled.addEventListener('change', function() {
                zendeskSettings.style.display = this.checked ? 'block' : 'none';
            });
        }

        zendeskForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const config = {
                enabled: document.getElementById('zendesk-enabled').checked,
                subdomain: document.getElementById('zendesk-subdomain').value,
                email: document.getElementById('zendesk-email').value,
                api_token: document.getElementById('zendesk-api-token').value,
                create_tickets: document.getElementById('zendesk-create-tickets').checked,
                update_tickets: document.getElementById('zendesk-update-tickets').checked,
                default_priority: document.getElementById('zendesk-default-priority').value
            };

            fetch('/api/framework/integrations/zendesk/config', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(config)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Zendesk configuration saved successfully', 'success');
                } else {
                    showNotification(data.error || 'Error saving Zendesk configuration', 'error');
                }
            })
            .catch(error => {
                console.error('Error saving Zendesk config:', error);
                showNotification('Error saving Zendesk configuration', 'error');
            });
        });
    }
});

// ============================================================================
// Nomadic E911 Functions
// ============================================================================

function loadE911Sites() {
    fetch('/api/framework/nomadic-e911/sites', {
        headers: getAuthHeaders()
    })
    .then(response => response.json())
    .then(data => {
        const tableBody = document.getElementById('e911-sites-table');
        if (!data.sites || data.sites.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="loading">No E911 sites configured</td></tr>';
            return;
        }

        tableBody.innerHTML = data.sites.map(site => `
            <tr>
                <td>${site.site_name}</td>
                <td>${site.address}, ${site.city}, ${site.state} ${site.postal_code}</td>
                <td>${site.ip_ranges || 'N/A'}</td>
                <td>${site.psap || 'Default'}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editE911Site(${site.id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteE911Site(${site.id})">Delete</button>
                </td>
            </tr>
        `).join('');
    })
    .catch(error => {
        console.error('Error loading E911 sites:', error);
        showNotification('Error loading E911 sites', 'error');
    });
}

function loadExtensionLocations() {
    fetch('/api/framework/nomadic-e911/locations', {
        headers: getAuthHeaders()
    })
    .then(response => response.json())
    .then(data => {
        const tableBody = document.getElementById('extension-locations-table');
        if (!data.locations || data.locations.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="loading">No location data available</td></tr>';
            return;
        }

        tableBody.innerHTML = data.locations.map(loc => `
            <tr>
                <td>${loc.extension}</td>
                <td>${loc.site_name || 'Unknown'} - ${loc.address || 'N/A'}</td>
                <td>${loc.detection_method || 'N/A'}</td>
                <td>${loc.last_updated ? new Date(loc.last_updated).toLocaleString() : 'N/A'}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="updateExtensionLocation('${loc.extension}')">Update</button>
                </td>
            </tr>
        `).join('');
    })
    .catch(error => {
        console.error('Error loading extension locations:', error);
        showNotification('Error loading extension locations', 'error');
    });
}

function loadLocationHistory() {
    const extension = document.getElementById('location-history-extension')?.value || '';
    const url = extension
        ? `/api/framework/nomadic-e911/history/${extension}`
        : '/api/framework/nomadic-e911/history';

    fetch(url, {
        headers: getAuthHeaders()
    })
    .then(response => response.json())
    .then(data => {
        const tableBody = document.getElementById('location-history-table');
        if (!data.history || data.history.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="loading">No location history available</td></tr>';
            return;
        }

        tableBody.innerHTML = data.history.map(entry => `
            <tr>
                <td>${new Date(entry.timestamp).toLocaleString()}</td>
                <td>${entry.extension}</td>
                <td>${entry.site_name || 'N/A'}</td>
                <td>${entry.detection_method || 'N/A'}</td>
                <td>${entry.ip_address || 'N/A'}</td>
            </tr>
        `).join('');
    })
    .catch(error => {
        console.error('Error loading location history:', error);
        showNotification('Error loading location history', 'error');
    });
}

// ============================================================================
// Paging System Functions
// ============================================================================

async function loadPagingData() {
    loadActivePages();
    loadPagingZones();
    loadPagingDevices();
}

async function loadActivePages() {
    const tableBody = document.getElementById('active-pages-table-body');
    if (!tableBody) return;

    try {
        const response = await fetch('/api/paging/active');
        const data = await response.json();

        if (!data.active_pages || data.active_pages.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="empty-state">No active paging sessions</td></tr>';
            return;
        }

        tableBody.innerHTML = data.active_pages.map(page => `
            <tr>
                <td>${escapeHtml(page.page_id)}</td>
                <td>${escapeHtml(page.from_extension)}</td>
                <td>${escapeHtml(page.zone_names)}</td>
                <td>${new Date(page.started_at).toLocaleString()}</td>
                <td><span class="status-badge status-active">${escapeHtml(page.status)}</span></td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading active pages:', error);
        tableBody.innerHTML = '<tr><td colspan="5" class="error">Error loading active pages</td></tr>';
    }
}

async function loadPagingZones() {
    const tableBody = document.getElementById('paging-zones-table-body');
    const zoneSelect = document.getElementById('test-page-zone');
    if (!tableBody) return;

    try {
        const response = await fetch('/api/paging/zones');
        const data = await response.json();

        if (!data.zones || data.zones.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="empty-state">No paging zones configured. Click "Add Zone" to create one.</td></tr>';
            if (zoneSelect) {
                zoneSelect.innerHTML = '<option value="">No zones configured</option>';
            }
            return;
        }

        tableBody.innerHTML = data.zones.map(zone => `
            <tr>
                <td>${escapeHtml(zone.extension)}</td>
                <td>${escapeHtml(zone.name)}</td>
                <td>${escapeHtml(zone.description || '-')}</td>
                <td>${escapeHtml(zone.device_id || '-')}</td>
                <td>
                    <button class="btn-icon btn-delete-zone" data-extension="${escapeHtml(zone.extension)}" title="Delete">🗑️</button>
                </td>
            </tr>
        `).join('');

        // Populate test zone select
        if (zoneSelect) {
            zoneSelect.innerHTML = '<option value="">Select Zone</option>' +
                (data.all_call_extension ? `<option value="${data.all_call_extension}">All Zones (${data.all_call_extension})</option>` : '') +
                data.zones.map(zone => `<option value="${zone.extension}">${zone.name} (${zone.extension})</option>`).join('');
        }

        // Add event listeners for delete buttons
        document.querySelectorAll('.btn-delete-zone').forEach(btn => {
            btn.addEventListener('click', function() {
                const extension = this.getAttribute('data-extension');
                deletePagingZone(extension);
            });
        });
    } catch (error) {
        console.error('Error loading paging zones:', error);
        tableBody.innerHTML = '<tr><td colspan="5" class="error">Error loading paging zones</td></tr>';
    }
}

async function loadPagingDevices() {
    const tableBody = document.getElementById('paging-devices-table-body');
    if (!tableBody) return;

    try {
        const response = await fetch('/api/paging/devices');
        const data = await response.json();

        if (!data.devices || data.devices.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="empty-state">No DAC devices configured. Click "Add Device" to create one.</td></tr>';
            return;
        }

        tableBody.innerHTML = data.devices.map(device => `
            <tr>
                <td>${escapeHtml(device.device_id)}</td>
                <td>${escapeHtml(device.name)}</td>
                <td>${escapeHtml(device.type)}</td>
                <td>${escapeHtml(device.sip_address || '-')}</td>
                <td><span class="status-badge">${escapeHtml(device.status || 'Unknown')}</span></td>
                <td>
                    <button class="btn-icon btn-delete-device" data-device-id="${escapeHtml(device.device_id)}" title="Delete">🗑️</button>
                </td>
            </tr>
        `).join('');

        // Add event listeners for delete buttons
        document.querySelectorAll('.btn-delete-device').forEach(btn => {
            btn.addEventListener('click', function() {
                const deviceId = this.getAttribute('data-device-id');
                deletePagingDevice(deviceId);
            });
        });
    } catch (error) {
        console.error('Error loading paging devices:', error);
        tableBody.innerHTML = '<tr><td colspan="6" class="error">Error loading paging devices</td></tr>';
    }
}

function showAddZoneModal() {
    const extension = prompt('Zone Extension (e.g., 701):');
    if (!extension) return;

    const name = prompt('Zone Name (e.g., "Warehouse"):');
    if (!name) return;

    const description = prompt('Description (optional):') || '';
    const deviceId = prompt('Device ID (optional):') || '';

    const zoneData = {
        extension: extension,
        name: name,
        description: description,
        device_id: deviceId
    };

    fetch('/api/paging/zones', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(zoneData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Zone ${name} added successfully`, 'success');
            loadPagingZones();
        } else {
            showNotification(data.message || 'Failed to add zone', 'error');
        }
    })
    .catch(error => {
        console.error('Error adding zone:', error);
        showNotification('Error adding zone', 'error');
    });
}

function deletePagingZone(extension) {
    if (!confirm(`Delete paging zone ${extension}?`)) return;

    fetch(`/api/paging/zones/${extension}`, { method: 'DELETE' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(`Zone ${extension} deleted`, 'success');
                loadPagingZones();
            } else {
                showNotification(data.message || 'Failed to delete zone', 'error');
            }
        })
        .catch(error => {
            console.error('Error deleting zone:', error);
            showNotification('Error deleting zone', 'error');
        });
}

function showAddDeviceModal() {
    const deviceId = prompt('Device ID (e.g., "dac-1"):');
    if (!deviceId) return;

    const name = prompt('Device Name (e.g., "Main PA System"):');
    if (!name) return;

    const type = prompt('Device Type (e.g., "sip_gateway"):') || 'sip_gateway';
    const sipAddress = prompt('SIP Address (e.g., "paging@192.168.1.10:5060"):') || '';

    const deviceData = {
        device_id: deviceId,
        name: name,
        type: type,
        sip_address: sipAddress
    };

    fetch('/api/paging/devices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(deviceData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Device ${name} added successfully`, 'success');
            loadPagingDevices();
        } else {
            showNotification(data.message || 'Failed to add device', 'error');
        }
    })
    .catch(error => {
        console.error('Error adding device:', error);
        showNotification('Error adding device', 'error');
    });
}

function deletePagingDevice(deviceId) {
    if (!confirm(`Delete paging device ${deviceId}?`)) return;

    fetch(`/api/paging/devices/${deviceId}`, { method: 'DELETE' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(`Device ${deviceId} deleted`, 'success');
                loadPagingDevices();
            } else {
                showNotification(data.message || 'Failed to delete device', 'error');
            }
        })
        .catch(error => {
            console.error('Error deleting device:', error);
            showNotification('Error deleting device', 'error');
        });
}

// Handle test paging form submission
document.addEventListener('DOMContentLoaded', function() {
    const testPagingForm = document.getElementById('test-paging-form');
    if (testPagingForm) {
        testPagingForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const fromExt = document.getElementById('test-page-from').value;
            const zoneExt = document.getElementById('test-page-zone').value;

            if (!fromExt || !zoneExt) {
                showNotification('Please fill in all fields', 'error');
                return;
            }

            showNotification(`To test paging: Dial ${zoneExt} from extension ${fromExt}. Note: This form doesn't initiate the actual SIP call - you need to dial from a phone.`, 'info');
        });
    }
});

// ============================================================================
// Helper placeholder functions for modal dialogs (to be implemented as needed)
// ============================================================================

function showAddSpeechAnalyticsConfigModal() {
    // Coming soon
}

function editSpeechAnalyticsConfig(extension) {
    // Coming soon
}

function deleteSpeechAnalyticsConfig(extension) {
    if (!confirm(`Delete speech analytics config for extension ${extension}?`)) {
        return;
    }
    // Coming soon
}

function showAddE911SiteModal() {
    // Coming soon
}

function editE911Site(siteId) {
    // Coming soon
}

function deleteE911Site(siteId) {
    if (!confirm(`Delete E911 site ${siteId}?`)) {
        return;
    }
    // Coming soon
}

function showUpdateLocationModal() {
    // Coming soon
}

function updateExtensionLocation(extension) {
    // Coming soon
}

// ============================================================================
// Click-to-Dial Functions
// ============================================================================

/**
 * Load all click-to-dial configurations
 */
async function loadClickToDialConfigs() {
    try {
        const response = await fetch(`${API_BASE}/api/framework/click-to-dial/configs`);
        const data = await response.json();

        if (data.error) {
            console.error('Error loading click-to-dial configs:', data.error);
            return;
        }

        // Populate extension selects
        const extensionSelect = document.getElementById('ctd-extension-select');
        const historyExtensionSelect = document.getElementById('ctd-history-extension');

        if (extensionSelect && currentExtensions) {
            extensionSelect.innerHTML = '<option value="">Select Extension</option>';
            currentExtensions.forEach(ext => {
                const option = document.createElement('option');
                option.value = ext.number;
                option.textContent = `${ext.number} - ${ext.name}`;
                extensionSelect.appendChild(option);
            });
        }

        if (historyExtensionSelect && currentExtensions) {
            historyExtensionSelect.innerHTML = '<option value="">All Extensions</option>';
            currentExtensions.forEach(ext => {
                const option = document.createElement('option');
                option.value = ext.number;
                option.textContent = `${ext.number} - ${ext.name}`;
                historyExtensionSelect.appendChild(option);
            });
        }

        // Populate configurations table
        const tbody = document.getElementById('ctd-configs-table');
        if (!tbody) return;

        if (!data.configs || data.configs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No configurations found. Configure extensions above.</td></tr>';
            return;
        }

        tbody.innerHTML = data.configs.map(config => `
            <tr>
                <td>${escapeHtml(config.extension)}</td>
                <td><span class="status-badge ${config.enabled ? 'success' : 'error'}">${config.enabled ? '✓ Enabled' : '✗ Disabled'}</span></td>
                <td>${config.default_caller_id ? escapeHtml(config.default_caller_id) : '-'}</td>
                <td>${config.auto_answer ? '✓ Yes' : '✗ No'}</td>
                <td>${config.browser_notification ? '✓ Yes' : '✗ No'}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editClickToDialConfig('${escapeHtml(config.extension)}')">Edit</button>
                </td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error loading click-to-dial configs:', error);
        displayError(error, 'Loading click-to-dial configurations');
    }
}

/**
 * Helper function to toggle click-to-dial config sections
 */
function toggleClickToDialConfigSections(showConfig) {
    const configSection = document.getElementById('ctd-config-section');
    const noExtensionSection = document.getElementById('ctd-no-extension');

    if (configSection && noExtensionSection) {
        configSection.style.display = showConfig ? 'block' : 'none';
        noExtensionSection.style.display = showConfig ? 'none' : 'block';
    }
}

/**
 * Load click-to-dial configuration for specific extension
 */
async function loadClickToDialConfig() {
    const extension = document.getElementById('ctd-extension-select')?.value;

    if (!extension) {
        toggleClickToDialConfigSections(false);
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/framework/click-to-dial/config/${extension}`);
        const data = await response.json();

        if (data.error) {
            console.error('Error loading config:', data.error);
            // Show default config for new extension
            document.getElementById('ctd-current-extension').textContent = extension;
            document.getElementById('ctd-enabled').checked = true;
            document.getElementById('ctd-caller-id').value = '';
            document.getElementById('ctd-auto-answer').checked = false;
            document.getElementById('ctd-browser-notification').checked = true;
        } else {
            document.getElementById('ctd-current-extension').textContent = extension;
            document.getElementById('ctd-enabled').checked = data.config.enabled;
            document.getElementById('ctd-caller-id').value = data.config.default_caller_id || '';
            document.getElementById('ctd-auto-answer').checked = data.config.auto_answer;
            document.getElementById('ctd-browser-notification').checked = data.config.browser_notification;
        }

        toggleClickToDialConfigSections(true);

    } catch (error) {
        console.error('Error loading click-to-dial config:', error);
        displayError(error, 'Loading click-to-dial configuration');
    }
}

/**
 * Save click-to-dial configuration
 */
async function saveClickToDialConfig(event) {
    event.preventDefault();

    const extension = document.getElementById('ctd-current-extension')?.textContent;
    if (!extension) {
        showNotification('No extension selected', 'error');
        return;
    }

    const config = {
        enabled: document.getElementById('ctd-enabled').checked,
        default_caller_id: document.getElementById('ctd-caller-id').value.trim() || null,
        auto_answer: document.getElementById('ctd-auto-answer').checked,
        browser_notification: document.getElementById('ctd-browser-notification').checked
    };

    try {
        const response = await fetch(`${API_BASE}/api/framework/click-to-dial/config/${extension}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (data.error) {
            showNotification(`Error: ${data.error}`, 'error');
        } else {
            showNotification('Configuration saved successfully', 'success');
            loadClickToDialConfigs();
        }
    } catch (error) {
        console.error('Error saving config:', error);
        displayError(error, 'Saving click-to-dial configuration');
        showNotification('Error saving configuration', 'error');
    }
}

/**
 * Edit click-to-dial configuration for extension
 */
async function editClickToDialConfig(extension) {
    // Set the extension in the select
    const select = document.getElementById('ctd-extension-select');
    if (select) {
        select.value = extension;
        await loadClickToDialConfig();
        // Scroll to config section
        document.getElementById('ctd-config-section').scrollIntoView({ behavior: 'smooth' });
    }
}

/**
 * Initiate a click-to-dial call
 */
async function initiateClickToDial() {
    const extension = document.getElementById('ctd-extension-select')?.value;
    const phoneNumber = document.getElementById('ctd-phone-number')?.value.trim();

    if (!extension) {
        showNotification('Please select an extension', 'error');
        return;
    }

    if (!phoneNumber) {
        showNotification('Please enter a phone number', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/framework/click-to-dial/call/${extension}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                destination: phoneNumber
            })
        });

        const data = await response.json();

        if (data.error) {
            showNotification(`Error: ${data.error}`, 'error');
        } else {
            showNotification(`Call initiated from extension ${extension} to ${phoneNumber}`, 'success');
            // Clear the phone number field
            document.getElementById('ctd-phone-number').value = '';
            // Reload history after a short delay
            setTimeout(() => loadClickToDialHistory(), 1000);
        }
    } catch (error) {
        console.error('Error initiating call:', error);
        displayError(error, 'Initiating click-to-dial call');
        showNotification('Error initiating call', 'error');
    }
}

/**
 * Load click-to-dial history for extension
 */
async function loadClickToDialHistory() {
    const extension = document.getElementById('ctd-history-extension')?.value;
    const tbody = document.getElementById('ctd-history-table');

    if (!tbody) return;

    if (!extension) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">Select an extension to view history</td></tr>';
        return;
    }

    // Status to CSS class mapping
    const statusClassMap = {
        'completed': 'success',
        'failed': 'error',
        'cancelled': 'warning',
        'busy': 'warning',
        'no-answer': 'warning'
    };

    try {
        const response = await fetch(`${API_BASE}/api/framework/click-to-dial/history/${extension}`);
        const data = await response.json();

        if (data.error) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;">Error: ${escapeHtml(data.error)}</td></tr>`;
            return;
        }

        if (!data.history || data.history.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No call history found</td></tr>';
            return;
        }

        tbody.innerHTML = data.history.map(call => {
            const timestamp = new Date(call.timestamp).toLocaleString();
            const duration = call.duration ? `${call.duration}s` : '-';
            const statusClass = statusClassMap[call.status] || 'warning';

            return `
                <tr>
                    <td>${timestamp}</td>
                    <td>${escapeHtml(call.extension)}</td>
                    <td>${escapeHtml(call.destination)}</td>
                    <td>${duration}</td>
                    <td><span class="status-badge ${statusClass}">${escapeHtml(call.status)}</span></td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading history:', error);
        displayError(error, 'Loading click-to-dial history');
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">Error loading history</td></tr>';
    }
}

// ========== WebRTC Phone Configuration ==========

// Note: DEFAULT_WEBRTC_EXTENSION is defined in webrtc_phone.js

async function loadWebRTCPhoneConfig() {
    try {
        const response = await fetch('/api/webrtc/phone-config');
        const data = await response.json();

        if (data.success) {
            const extensionInput = document.getElementById('webrtc-phone-extension');
            if (extensionInput) {
                extensionInput.value = data.extension || DEFAULT_WEBRTC_EXTENSION;
            }

            // Reinitialize the WebRTC phone with the new extension
            if (typeof initWebRTCPhone === 'function') {
                initWebRTCPhone();
            }
        } else {
            console.error('Failed to load WebRTC phone config:', data.error);
        }
    } catch (error) {
        console.error('Error loading WebRTC phone config:', error);
    }
}

async function saveWebRTCPhoneConfig(event) {
    event.preventDefault();

    const extensionInput = document.getElementById('webrtc-phone-extension');
    const extension = extensionInput.value.trim();

    if (!extension) {
        alert('Please enter an extension');
        return;
    }

    try {
        const response = await fetch('/api/webrtc/phone-config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({extension})
        });

        const data = await response.json();

        if (data.success) {
            alert('Phone extension saved successfully! Reloading phone...');
            // Reinitialize the WebRTC phone with the new extension
            if (typeof initWebRTCPhone === 'function') {
                initWebRTCPhone();
            }
        } else {
            alert('Error: ' + (data.error || 'Failed to save phone extension'));
        }
    } catch (error) {
        console.error('Error saving WebRTC phone config:', error);
        alert('Error: ' + error.message);
    }
}

// ============================================================================
// License Management Functions
// ============================================================================

/**
 * Load and display current license status
 */
async function loadLicenseStatus() {
    const container = document.getElementById('license-status-container');
    if (!container) return;

    container.innerHTML = '<div class="loading">Loading license status...</div>';

    try {
        const response = await fetchWithTimeout(`${API_BASE}/api/license/status`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success && data.license) {
            const license = data.license;

            // Build status display
            let html = '<div style="background: #f9f9f9; padding: 15px; border-radius: 4px;">';

            // Licensing enabled/disabled status
            const statusColor = license.enabled ? '#4caf50' : '#ff9800';
            html += `<div style="margin-bottom: 15px;">
                <strong>Licensing Status:</strong>
                <span style="color: ${statusColor}; font-weight: bold;">
                    ${license.enabled ? '✅ ENABLED' : '❌ DISABLED (Open-Source Mode)'}
                </span>
            </div>`;

            if (license.enabled) {
                // License status
                const statusBadgeColor =
                    license.status === 'active' ? '#4caf50' :
                    license.status === 'grace_period' ? '#ff9800' :
                    license.status === 'expired' ? '#f44336' : '#9e9e9e';

                html += `<div style="margin-bottom: 10px;">
                    <strong>License Status:</strong>
                    <span style="color: ${statusBadgeColor}; font-weight: bold; text-transform: uppercase;">
                        ${license.status}
                    </span>
                </div>`;

                html += `<div style="margin-bottom: 10px;">
                    <strong>Message:</strong> ${escapeHtml(license.message)}
                </div>`;

                // License details if available
                if (license.type && license.type !== 'disabled') {
                    html += `<div style="margin-bottom: 10px;">
                        <strong>Type:</strong> ${escapeHtml(license.type).toUpperCase()}
                    </div>`;
                }

                if (license.issued_to) {
                    html += `<div style="margin-bottom: 10px;">
                        <strong>Issued To:</strong> ${escapeHtml(license.issued_to)}
                    </div>`;
                    html += `<div style="margin-bottom: 10px;">
                        <strong>Issued Date:</strong> ${escapeHtml(license.issued_date)}
                    </div>`;
                    html += `<div style="margin-bottom: 10px;">
                        <strong>Expiration:</strong> ${escapeHtml(license.expiration || 'Never (Perpetual)')}
                    </div>`;
                    html += `<div style="margin-bottom: 10px;">
                        <strong>License Key:</strong> <code>${escapeHtml(license.key || 'N/A')}</code>
                    </div>`;
                }

                // Limits
                if (license.limits) {
                    html += '<div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd;">';
                    html += '<strong>Limits:</strong><ul style="margin: 10px 0; padding-left: 20px;">';

                    for (const [key, value] of Object.entries(license.limits)) {
                        const displayValue = value === null ? 'Unlimited' : value.toLocaleString();
                        const limitName = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        html += `<li><strong>${limitName}:</strong> ${displayValue}</li>`;
                    }

                    html += '</ul></div>';
                }
            } else {
                html += '<div style="margin-top: 10px; color: #666;">All features are available in open-source mode.</div>';
            }

            html += '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = `<div style="color: #f44336;">Error loading license status: ${escapeHtml(data.error || 'Unknown error')}</div>`;
        }
    } catch (error) {
        console.error('Error loading license status:', error);
        container.innerHTML = `<div style="color: #f44336;">Error: ${escapeHtml(error.message)}</div>`;
    }
}

/**
 * Load and display available features for current license
 */
async function loadLicenseFeatures() {
    const container = document.getElementById('license-features-container');
    if (!container) return;

    container.innerHTML = '<div class="loading">Loading features...</div>';

    try {
        const response = await fetchWithTimeout(`${API_BASE}/api/license/features`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            let html = '<div style="background: #f9f9f9; padding: 15px; border-radius: 4px;">';

            if (!data.licensing_enabled) {
                html += '<div style="color: #4caf50; font-weight: bold; margin-bottom: 10px;">✅ All features available (Licensing disabled)</div>';
            } else {
                html += `<div style="margin-bottom: 15px;">
                    <strong>License Type:</strong> ${escapeHtml(data.license_type || 'N/A').toUpperCase()}
                </div>`;

                // Features list
                if (data.features && data.features !== 'all') {
                    html += '<div style="margin-bottom: 15px;"><strong>Available Features:</strong>';
                    html += '<ul style="margin: 10px 0; padding-left: 20px; columns: 2; column-gap: 20px;">';

                    data.features.sort().forEach(feature => {
                        const displayName = feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        html += `<li>✓ ${escapeHtml(displayName)}</li>`;
                    });

                    html += '</ul></div>';
                }

                // Limits
                if (data.limits) {
                    html += '<div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd;">';
                    html += '<strong>Limits:</strong><ul style="margin: 10px 0; padding-left: 20px;">';

                    for (const [key, value] of Object.entries(data.limits)) {
                        const displayValue = value === null ? 'Unlimited' : value.toLocaleString();
                        const limitName = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        html += `<li><strong>${limitName}:</strong> ${displayValue}</li>`;
                    }

                    html += '</ul></div>';
                }
            }

            html += '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = `<div style="color: #f44336;">Error loading features: ${escapeHtml(data.error || 'Unknown error')}</div>`;
        }
    } catch (error) {
        console.error('Error loading license features:', error);
        container.innerHTML = `<div style="color: #f44336;">Error: ${escapeHtml(error.message)}</div>`;
    }
}

/**
 * Toggle licensing enforcement on/off
 */
async function toggleLicensing(enabled) {
    const resultDiv = document.getElementById('licensing-toggle-result');
    if (!resultDiv) return;

    const action = enabled ? 'enable' : 'disable';
    const confirmMsg = enabled
        ? 'Enable licensing enforcement? This will require a valid license for features.'
        : 'Disable licensing? This will make all features available for free (open-source mode).';

    if (!confirm(confirmMsg)) {
        return;
    }

    resultDiv.innerHTML = '<div class="loading">Processing...</div>';

    try {
        const response = await fetchWithTimeout(`${API_BASE}/api/license/toggle`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({enabled: enabled})
        });

        const data = await response.json();

        if (data.success) {
            resultDiv.innerHTML = `<div style="color: #4caf50; padding: 10px; background: #e8f5e9; border-radius: 4px;">
                ✅ ${escapeHtml(data.message || `Licensing ${action}d successfully`)}
                <br><small>Note: Restart PBX system for changes to take full effect</small>
            </div>`;
            // Reload status
            setTimeout(() => {
                loadLicenseStatus();
                loadLicenseFeatures();
            }, 1000);
        } else {
            resultDiv.innerHTML = `<div style="color: #f44336; padding: 10px; background: #ffebee; border-radius: 4px;">
                ❌ Error: ${escapeHtml(data.error || 'Failed to toggle licensing')}
            </div>`;
        }
    } catch (error) {
        console.error('Error toggling licensing:', error);
        resultDiv.innerHTML = `<div style="color: #f44336; padding: 10px; background: #ffebee; border-radius: 4px;">
            ❌ Error: ${escapeHtml(error.message)}
        </div>`;
    }
}

/**
 * Generate a new license
 */
async function generateLicense(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const resultDiv = document.getElementById('generate-license-result');

    // Build request data
    const requestData = {
        type: formData.get('type'),
        issued_to: formData.get('issued_to')
    };

    // Add optional fields if provided
    if (formData.get('expiration_days')) {
        requestData.expiration_days = parseInt(formData.get('expiration_days'));
    }
    if (formData.get('max_extensions')) {
        requestData.max_extensions = parseInt(formData.get('max_extensions'));
    }
    if (formData.get('max_concurrent_calls')) {
        requestData.max_concurrent_calls = parseInt(formData.get('max_concurrent_calls'));
    }

    resultDiv.innerHTML = '<div class="loading">Generating license...</div>';

    try {
        const response = await fetchWithTimeout(`${API_BASE}/api/license/generate`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(requestData)
        });

        const data = await response.json();

        if (data.success && data.license) {
            const license = data.license;

            // Display generated license
            let html = '<div style="background: #e8f5e9; padding: 15px; border-radius: 4px; margin-bottom: 15px;">';
            html += '<h4 style="margin-top: 0; color: #4caf50;">✅ License Generated Successfully!</h4>';
            html += `<p><strong>License Key:</strong> <code style="background: white; padding: 2px 6px; border-radius: 3px;">${escapeHtml(license.key)}</code></p>`;
            html += `<p><strong>Type:</strong> ${escapeHtml(license.type)}</p>`;
            html += `<p><strong>Issued To:</strong> ${escapeHtml(license.issued_to)}</p>`;
            html += `<p><strong>Expiration:</strong> ${escapeHtml(license.expiration || 'Never (Perpetual)')}</p>`;
            html += '</div>';

            // Add JSON download option
            html += '<div style="margin-bottom: 15px;">';
            html += '<p><strong>License Data (JSON):</strong></p>';
            html += `<textarea readonly style="width: 100%; height: 200px; font-family: monospace; font-size: 12px; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">${JSON.stringify(license, null, 2)}</textarea>`;
            html += '</div>';

            html += '<div class="action-buttons">';
            html += `<button class="btn btn-primary" onclick="copyToClipboard(${escapeHtml(JSON.stringify(JSON.stringify(license)))})">📋 Copy JSON</button>`;
            html += `<button class="btn btn-success" onclick="downloadLicense(${escapeHtml(JSON.stringify(license))})">💾 Download JSON</button>`;
            html += '</div>';

            resultDiv.innerHTML = html;
        } else {
            resultDiv.innerHTML = `<div style="color: #f44336; padding: 10px; background: #ffebee; border-radius: 4px;">
                ❌ Error: ${escapeHtml(data.error || 'Failed to generate license')}
            </div>`;
        }
    } catch (error) {
        console.error('Error generating license:', error);
        resultDiv.innerHTML = `<div style="color: #f44336; padding: 10px; background: #ffebee; border-radius: 4px;">
            ❌ Error: ${escapeHtml(error.message)}
        </div>`;
    }
}

/**
 * Install a license
 */
async function installLicense(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const resultDiv = document.getElementById('install-license-result');

    // Parse JSON
    let licenseData;
    try {
        licenseData = JSON.parse(formData.get('license_data'));
    } catch (error) {
        resultDiv.innerHTML = `<div style="color: #f44336; padding: 10px; background: #ffebee; border-radius: 4px;">
            ❌ Invalid JSON format. Please check the license data.
        </div>`;
        return;
    }

    const enforceLicensing = formData.get('enforce_licensing') === 'on';

    resultDiv.innerHTML = '<div class="loading">Installing license...</div>';

    try {
        const response = await fetchWithTimeout(`${API_BASE}/api/license/install`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                license_data: licenseData,
                enforce_licensing: enforceLicensing
            })
        });

        const data = await response.json();

        if (data.success) {
            let html = '<div style="color: #4caf50; padding: 10px; background: #e8f5e9; border-radius: 4px;">';
            html += `<p style="margin: 0 0 10px 0;"><strong>✅ ${escapeHtml(data.message)}</strong></p>`;

            if (data.enforcement_locked) {
                html += '<p style="margin: 0; color: #ff9800;">⚠️ License lock file created - licensing cannot be disabled</p>';
            }

            html += '</div>';
            resultDiv.innerHTML = html;

            // Clear form and reload status
            form.reset();
            setTimeout(() => {
                loadLicenseStatus();
                loadLicenseFeatures();
            }, 1000);
        } else {
            resultDiv.innerHTML = `<div style="color: #f44336; padding: 10px; background: #ffebee; border-radius: 4px;">
                ❌ Error: ${escapeHtml(data.error || 'Failed to install license')}
            </div>`;
        }
    } catch (error) {
        console.error('Error installing license:', error);
        resultDiv.innerHTML = `<div style="color: #f44336; padding: 10px; background: #ffebee; border-radius: 4px;">
            ❌ Error: ${escapeHtml(error.message)}
        </div>`;
    }
}

/**
 * Revoke current license
 */
async function revokeLicense() {
    if (!confirm('Are you sure you want to revoke the current license? This action cannot be undone.')) {
        return;
    }

    const resultDiv = document.getElementById('revoke-license-result');
    resultDiv.innerHTML = '<div class="loading">Revoking license...</div>';

    try {
        const response = await fetchWithTimeout(`${API_BASE}/api/license/revoke`, {
            method: 'POST',
            headers: getAuthHeaders()
        });

        const data = await response.json();

        if (data.success) {
            resultDiv.innerHTML = `<div style="color: #4caf50; padding: 10px; background: #e8f5e9; border-radius: 4px;">
                ✅ ${escapeHtml(data.message || 'License revoked successfully')}
            </div>`;

            // Reload status
            setTimeout(() => {
                loadLicenseStatus();
                loadLicenseFeatures();
            }, 1000);
        } else {
            resultDiv.innerHTML = `<div style="color: #f44336; padding: 10px; background: #ffebee; border-radius: 4px;">
                ❌ Error: ${escapeHtml(data.error || 'Failed to revoke license')}
            </div>`;
        }
    } catch (error) {
        console.error('Error revoking license:', error);
        resultDiv.innerHTML = `<div style="color: #f44336; padding: 10px; background: #ffebee; border-radius: 4px;">
            ❌ Error: ${escapeHtml(error.message)}
        </div>`;
    }
}

/**
 * Remove license lock file
 */
async function removeLicenseLock() {
    if (!confirm('Remove license lock file? This will allow disabling licensing. Only use when transitioning from commercial to open-source deployment.')) {
        return;
    }

    const resultDiv = document.getElementById('remove-lock-result');
    resultDiv.innerHTML = '<div class="loading">Removing lock file...</div>';

    try {
        const response = await fetchWithTimeout(`${API_BASE}/api/license/remove_lock`, {
            method: 'POST',
            headers: getAuthHeaders()
        });

        const data = await response.json();

        if (data.success) {
            resultDiv.innerHTML = `<div style="color: #4caf50; padding: 10px; background: #e8f5e9; border-radius: 4px;">
                ✅ ${escapeHtml(data.message || 'License lock removed successfully')}
            </div>`;
        } else {
            resultDiv.innerHTML = `<div style="color: #f44336; padding: 10px; background: #ffebee; border-radius: 4px;">
                ❌ Error: ${escapeHtml(data.error || 'Failed to remove license lock')}
            </div>`;
        }
    } catch (error) {
        console.error('Error removing license lock:', error);
        resultDiv.innerHTML = `<div style="color: #f44336; padding: 10px; background: #ffebee; border-radius: 4px;">
            ❌ Error: ${escapeHtml(error.message)}
        </div>`;
    }
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();

    try {
        document.execCommand('copy');
        alert('License data copied to clipboard!');
    } catch (error) {
        console.error('Error copying to clipboard:', error);
        alert('Failed to copy to clipboard');
    } finally {
        document.body.removeChild(textarea);
    }
}

/**
 * Download license as JSON file
 */
function downloadLicense(licenseData) {
    const dataStr = JSON.stringify(licenseData, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    const url = URL.createObjectURL(dataBlob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `license_${licenseData.issued_to.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase()}_${new Date().toISOString().split('T')[0]}.json`;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
}

/**
 * Initialize license management tab when it's shown
 */
function initLicenseManagement() {
    loadLicenseStatus();
    loadLicenseFeatures();
}

/**
 * Check if current user is the license administrator
 */
function isLicenseAdmin() {
    // Check if current user is extension 9322 (license admin)
    if (currentUser && currentUser.number === '9322') {
        return true;
    }
    return false;
}

/**
 * Show or hide license management tab based on user permissions
 */
function updateLicenseManagementVisibility() {
    const licenseTab = document.querySelector('[data-tab="license-management"]');
    if (licenseTab) {
        if (isLicenseAdmin()) {
            licenseTab.style.display = '';  // Show the tab
        } else {
            licenseTab.style.display = 'none';  // Hide the tab
        }
    }
}

// Add event listener for license management tab
document.addEventListener('DOMContentLoaded', function() {
    const licenseTab = document.querySelector('[data-tab="license-management"]');
    if (licenseTab) {
        licenseTab.addEventListener('click', function() {
            // Verify user is license admin before loading
            if (!isLicenseAdmin()) {
                alert('Access Denied: License management is restricted to authorized administrators only.');
                return;
            }
            // Load license info when tab is opened
            setTimeout(initLicenseManagement, 100);
        });
    }
});
