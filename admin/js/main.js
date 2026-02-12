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
