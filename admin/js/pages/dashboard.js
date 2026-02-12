/**
 * Dashboard page module.
 * Handles dashboard stats, AD integration status, and global refresh.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.js';
import { showNotification } from '../ui/notifications.js';

const AD_SYNC_TIMEOUT = 60000;

export async function loadDashboard() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/status`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

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

        loadADStatus();
    } catch (error) {
        console.error('Error loading dashboard:', error);
        ['stat-extensions', 'stat-calls', 'stat-total-calls', 'stat-recordings'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = 'Error';
        });
        showNotification(`Failed to load dashboard: ${error.message}`, 'error');
    }
}

export function refreshDashboard() {
    loadDashboard();
    showNotification('Dashboard refreshed', 'success');
}

export async function loadADStatus() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/integrations/ad/status`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        const statusBadge = document.getElementById('ad-status-badge');
        if (statusBadge) {
            statusBadge.textContent = data.enabled ? 'Enabled' : 'Disabled';
            statusBadge.className = `status-badge ${data.enabled ? 'enabled' : 'disabled'}`;
        }

        const connectionStatus = document.getElementById('ad-connection-status');
        if (connectionStatus) {
            connectionStatus.textContent = data.connected ? '\u2713 Connected' : '\u2717 Not Connected';
            connectionStatus.style.color = data.connected ? '#10b981' : '#ef4444';
        }

        const el = (id) => document.getElementById(id);
        if (el('ad-server')) el('ad-server').textContent = data.server || 'Not configured';
        if (el('ad-auto-provision')) el('ad-auto-provision').textContent = data.auto_provision ? 'Yes' : 'No';
        if (el('ad-synced-users')) el('ad-synced-users').textContent = data.synced_users || 0;

        const errorElement = el('ad-error');
        if (errorElement) {
            errorElement.textContent = data.error || 'None';
            errorElement.style.color = data.error ? '#d32f2f' : '#10b981';
        }

        const syncBtn = el('ad-sync-btn');
        if (syncBtn) syncBtn.disabled = !(data.enabled && data.connected);
    } catch (error) {
        console.error('Error loading AD status:', error);
    }
}

export function refreshADStatus() {
    loadADStatus();
    showNotification('AD status refreshed', 'success');
}

export async function syncADUsers() {
    const syncBtn = document.getElementById('ad-sync-btn');
    if (!syncBtn) return;
    const originalText = syncBtn.textContent;
    syncBtn.disabled = true;
    syncBtn.textContent = 'Syncing...';

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/integrations/ad/sync`, {
            method: 'POST'
        }, AD_SYNC_TIMEOUT);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }

        const data = await response.json();
        if (data.success) {
            showNotification(data.message || `Successfully synced ${data.synced_count} users`, 'success');
            loadADStatus();
        } else {
            showNotification(data.error || 'Failed to sync users', 'error');
        }
    } catch (error) {
        console.error('Error syncing AD users:', error);
        const errorMsg = error.message === 'Request timed out'
            ? 'AD sync timed out. Check server logs.'
            : 'Error syncing AD users';
        showNotification(errorMsg, 'error');
    } finally {
        syncBtn.textContent = originalText;
        syncBtn.disabled = false;
    }
}

// Backward compatibility
window.loadDashboard = loadDashboard;
window.refreshDashboard = refreshDashboard;
window.loadADStatus = loadADStatus;
window.refreshADStatus = refreshADStatus;
window.syncADUsers = syncADUsers;
