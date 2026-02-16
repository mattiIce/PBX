/**
 * Dashboard page module.
 * Handles dashboard stats, AD integration status, and global refresh.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';

interface DashboardStatus {
    registered_extensions?: number;
    active_calls?: number;
    total_calls?: number;
    active_recordings?: number;
    running?: boolean;
}

interface ADStatus {
    enabled: boolean;
    connected: boolean;
    server?: string;
    auto_provision?: boolean;
    synced_users?: number;
    error?: string;
}

interface ADSyncResponse {
    success: boolean;
    message?: string;
    synced_count?: number;
    error?: string;
}

const AD_SYNC_TIMEOUT = 60000;

export async function loadDashboard(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/status`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: DashboardStatus = await response.json();

        (document.getElementById('stat-extensions') as HTMLElement).textContent = String(data.registered_extensions ?? 0);
        (document.getElementById('stat-calls') as HTMLElement).textContent = String(data.active_calls ?? 0);
        (document.getElementById('stat-total-calls') as HTMLElement).textContent = String(data.total_calls ?? 0);
        (document.getElementById('stat-recordings') as HTMLElement).textContent = String(data.active_recordings ?? 0);

        const systemStatus = document.getElementById('system-status') as HTMLElement | null;
        if (systemStatus) {
            systemStatus.textContent = `System: ${data.running ? 'Running' : 'Stopped'}`;
            systemStatus.classList.remove('connected', 'disconnected');
            systemStatus.classList.add('status-badge', data.running ? 'connected' : 'disconnected');
        }

        loadADStatus();
    } catch (error: unknown) {
        console.error('Error loading dashboard:', error);
        for (const id of ['stat-extensions', 'stat-calls', 'stat-total-calls', 'stat-recordings']) {
            const el = document.getElementById(id);
            if (el) el.textContent = 'Error';
        }
        const message = error instanceof Error ? error.message : String(error);
        showNotification(`Failed to load dashboard: ${message}`, 'error');
    }
}

export function refreshDashboard(): void {
    loadDashboard();
    showNotification('Dashboard refreshed', 'success');
}

export async function loadADStatus(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/integrations/ad/status`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: ADStatus = await response.json();

        const statusBadge = document.getElementById('ad-status-badge') as HTMLElement | null;
        if (statusBadge) {
            statusBadge.textContent = data.enabled ? 'Enabled' : 'Disabled';
            statusBadge.className = `status-badge ${data.enabled ? 'enabled' : 'disabled'}`;
        }

        const connectionStatus = document.getElementById('ad-connection-status') as HTMLElement | null;
        if (connectionStatus) {
            connectionStatus.textContent = data.connected ? '\u2713 Connected' : '\u2717 Not Connected';
            connectionStatus.style.color = data.connected ? '#10b981' : '#ef4444';
        }

        const el = (id: string): HTMLElement | null => document.getElementById(id);
        if (el('ad-server')) (el('ad-server') as HTMLElement).textContent = data.server ?? 'Not configured';
        if (el('ad-auto-provision')) (el('ad-auto-provision') as HTMLElement).textContent = data.auto_provision ? 'Yes' : 'No';
        if (el('ad-synced-users')) (el('ad-synced-users') as HTMLElement).textContent = String(data.synced_users ?? 0);

        const errorElement = el('ad-error') as HTMLElement | null;
        if (errorElement) {
            errorElement.textContent = data.error ?? 'None';
            errorElement.style.color = data.error ? '#d32f2f' : '#10b981';
        }

        const syncBtn = el('ad-sync-btn') as HTMLButtonElement | null;
        if (syncBtn) syncBtn.disabled = !(data.enabled && data.connected);
    } catch (error: unknown) {
        console.error('Error loading AD status:', error);
    }
}

export function refreshADStatus(): void {
    loadADStatus();
    showNotification('AD status refreshed', 'success');
}

export async function syncADUsers(): Promise<void> {
    const syncBtn = document.getElementById('ad-sync-btn') as HTMLButtonElement | null;
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

        const data: ADSyncResponse = await response.json();
        if (data.success) {
            showNotification(data.message || `Successfully synced ${data.synced_count} users`, 'success');
            loadADStatus();
        } else {
            showNotification(data.error || 'Failed to sync users', 'error');
        }
    } catch (error: unknown) {
        console.error('Error syncing AD users:', error);
        const message = error instanceof Error ? error.message : String(error);
        const errorMsg = message === 'Request timed out'
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
