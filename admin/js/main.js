// Module imports
import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl, DEFAULT_FETCH_TIMEOUT } from './api/client.ts';
import { store } from './state/store.ts';
import { showNotification, displayError, setSuppressErrorNotifications } from './ui/notifications.ts';
import { showTab, initializeTabs } from './ui/tabs.ts';
import {
    escapeHtml,
    copyToClipboard,
    formatDate,
    truncate,
    getDuration,
    getStatusBadge,
    getHealthBadge,
    getPriorityBadge,
    getQualityClass,
    getScheduleDescription,
    downloadLicense,
} from './utils/html.ts';

// Re-export to window for backward compatibility with non-modular code
window.fetchWithTimeout = fetchWithTimeout;
window.getAuthHeaders = getAuthHeaders;
window.getApiBaseUrl = getApiBaseUrl;
window.DEFAULT_FETCH_TIMEOUT = DEFAULT_FETCH_TIMEOUT;
window.store = store;
window.showNotification = showNotification;
window.displayError = displayError;
window.setSuppressErrorNotifications = setSuppressErrorNotifications;
window.showTab = showTab;
window.switchTab = showTab;
window.initializeTabs = initializeTabs;
window.escapeHtml = escapeHtml;
window.copyToClipboard = copyToClipboard;
window.formatDate = formatDate;
window.truncate = truncate;
window.getDuration = getDuration;
window.getStatusBadge = getStatusBadge;
window.getHealthBadge = getHealthBadge;
window.getPriorityBadge = getPriorityBadge;
window.getQualityClass = getQualityClass;
window.getScheduleDescription = getScheduleDescription;
window.downloadLicense = downloadLicense;

// Page module imports — each module self-registers window.* exports
import './pages/dashboard.ts';
import './pages/extensions.ts';
import './pages/voicemail.ts';
import './pages/calls.ts';
import './pages/config.ts';
import './pages/provisioning.ts';
import './pages/phones.ts';
import './pages/security.ts';
import './pages/emergency.ts';
import './pages/phone_book.ts';
import './pages/paging.ts';
import './pages/license.ts';
import './pages/analytics.ts';
import './pages/sip-trunks.ts';
import './pages/call-routing.ts';
import './pages/recordings.ts';
import './pages/click-to-dial.ts';
import './pages/speech-analytics.ts';

// Constants
const LOGIN_PAGE_PATH = '/admin/login.html';

// Application initialization
async function initializeUserContext() {
    console.log('Initializing user context...');

    // Check for authentication token first
    const token = localStorage.getItem('pbx_token');

    if (!token) {
        console.log('No authentication token found, redirecting to login...');
        window.location.replace(LOGIN_PAGE_PATH);
        return;
    }

    // Verify token is still valid by making an authenticated request
    try {
        const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/extensions`, {
            headers: getAuthHeaders(),
        }, 5000);

        if (response.status === 401 || response.status === 403) {
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
        showNotification('Unable to verify authentication - server may be starting up', 'error');
    }

    // Get user info from localStorage (set during login)
    const extensionNumber = localStorage.getItem('pbx_extension');
    const isAdmin = localStorage.getItem('pbx_is_admin') === 'true';
    const name = localStorage.getItem('pbx_name') || 'User';

    if (!extensionNumber) {
        console.log('No extension number found, redirecting to login...');
        window.location.replace(LOGIN_PAGE_PATH);
        return;
    }

    // Store current user in the global store
    store.set('currentUser', { number: extensionNumber, is_admin: isAdmin, name: name });

    console.log('User context initialized:', { number: extensionNumber, is_admin: isAdmin, name });

    // Load initial content based on role
    if (isAdmin) {
        console.log('Admin user - showing dashboard tab');
        showTab('dashboard');
    } else {
        console.log('Regular user - showing webrtc-phone tab');
        showTab('webrtc-phone');
    }

    console.log('User context initialization complete');
}

function initializeForms() {
    // Attach submit handlers to any forms present in the DOM.
    // Individual page modules register their own specific form handlers,
    // so this function handles shared / cross-cutting form behaviour.
    const forms = document.querySelectorAll('form[data-ajax]');
    for (const form of forms) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            console.log('Ajax form submitted:', form.id);
        });
    }
}

function initializeLogout() {
    const logoutButton = document.getElementById('logout-button');
    if (!logoutButton) return;

    logoutButton.addEventListener('click', async () => {
        const token = localStorage.getItem('pbx_token');

        localStorage.removeItem('pbx_token');
        localStorage.removeItem('pbx_extension');
        localStorage.removeItem('pbx_is_admin');
        localStorage.removeItem('pbx_name');
        localStorage.removeItem('pbx_current_extension');

        try {
            if (token) {
                await fetch(`${getApiBaseUrl()}/api/auth/logout`, {
                    method: 'POST',
                    headers: getAuthHeaders(),
                });
            }
        } catch (error) {
            console.error('Logout API error:', error);
        }

        window.location.href = LOGIN_PAGE_PATH;
    });
}

async function checkConnection() {
    const statusBadge = document.getElementById('connection-status');

    if (!statusBadge) {
        console.error('Connection status badge element not found');
        return;
    }

    try {
        const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/status`, {
            headers: getAuthHeaders(),
        }, 5000);

        if (response.ok) {
            statusBadge.textContent = 'Connected';
            statusBadge.classList.remove('disconnected');
            statusBadge.classList.add('connected');
        } else {
            throw new Error('Connection failed');
        }
    } catch (error) {
        console.error('Connection check failed:', error);
        statusBadge.textContent = 'Disconnected';
        statusBadge.classList.remove('connected');
        statusBadge.classList.add('disconnected');
    }
}

// DOMContentLoaded — main application entry point
document.addEventListener('DOMContentLoaded', async () => {
    console.log('DOMContentLoaded event fired - starting initialization');

    // Initialize user context first (async) — this will call showTab() when ready
    await initializeUserContext();
    console.log('User context initialization awaited');

    // Then initialize other components
    console.log('Initializing tabs, forms, and logout');
    initializeTabs();
    initializeForms();
    initializeLogout();
    checkConnection();

    // Auto-refresh connection status every 10 seconds
    setInterval(checkConnection, 10000);

    console.log('Page initialization complete');
});

// Named exports for use by other ES modules
export {
    fetchWithTimeout,
    getAuthHeaders,
    getApiBaseUrl,
    DEFAULT_FETCH_TIMEOUT,
    store,
    showNotification,
    displayError,
    setSuppressErrorNotifications,
    showTab,
    initializeTabs,
    escapeHtml,
    copyToClipboard,
    formatDate,
    truncate,
    getDuration,
    getStatusBadge,
    getHealthBadge,
    getPriorityBadge,
    getQualityClass,
    getScheduleDescription,
    downloadLicense,
};
