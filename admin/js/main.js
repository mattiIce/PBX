// Module imports
import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl, DEFAULT_FETCH_TIMEOUT } from './api/client.js';
import { store } from './state/store.js';
import { showNotification, displayError, setSuppressErrorNotifications } from './ui/notifications.js';
import { showTab, initializeTabs } from './ui/tabs.js';
import { escapeHtml, copyToClipboard } from './utils/html.js';

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
};
