/**
 * Security page module.
 * Handles fraud detection, blocked patterns, callback queue, and mobile push.
 */

import { getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';
import { escapeHtml } from '../utils/html.ts';

interface FraudAlert {
    type?: string;
    description?: string;
    severity?: string;
    timestamp: string;
}

interface FraudAlertsResponse {
    alerts?: FraudAlert[];
}

interface CallbackEntry {
    id: string;
    caller?: string;
    number?: string;
    status?: string;
    requested_at: string;
}

interface CallbackQueueResponse {
    queue?: CallbackEntry[];
}

interface MobilePushDevice {
    device_id: string;
    name?: string;
    platform?: string;
    active?: boolean;
}

interface MobilePushDevicesResponse {
    devices?: MobilePushDevice[];
}

interface SpeechAnalyticsResponse {
    configs?: unknown[];
}

export async function loadFraudAlerts(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/security/fraud-alerts`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: FraudAlertsResponse = await response.json();

        const container = document.getElementById('fraud-alerts-list') as HTMLElement | null;
        if (!container) return;

        const alerts = data.alerts ?? [];
        if (alerts.length === 0) {
            container.innerHTML = '<div class="info-box">No fraud alerts</div>';
            return;
        }

        container.innerHTML = alerts.map(a => `
            <div class="alert-item ${a.severity || 'info'}">
                <strong>${escapeHtml(a.type || 'Alert')}</strong> - ${escapeHtml(a.description || '')}
                <span class="alert-time">${new Date(a.timestamp).toLocaleString()}</span>
            </div>
        `).join('');
    } catch (error: unknown) {
        console.error('Error loading fraud alerts:', error);
    }
}

export async function loadCallbackQueue(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/calls/callback-queue`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: CallbackQueueResponse = await response.json();

        const tbody = document.getElementById('callback-queue-body') as HTMLElement | null;
        if (!tbody) return;

        const queue = data.queue ?? [];
        if (queue.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No callbacks in queue</td></tr>';
            return;
        }

        tbody.innerHTML = queue.map(cb => `
            <tr>
                <td>${escapeHtml(cb.caller || '')}</td>
                <td>${escapeHtml(cb.number || '')}</td>
                <td>${escapeHtml(cb.status || '')}</td>
                <td>${new Date(cb.requested_at).toLocaleString()}</td>
                <td>
                    <button class="btn btn-primary btn-sm" onclick="startCallback('${cb.id}')">Start</button>
                    <button class="btn btn-danger btn-sm" onclick="cancelCallback('${cb.id}')">Cancel</button>
                </td>
            </tr>
        `).join('');
    } catch (error: unknown) {
        console.error('Error loading callback queue:', error);
    }
}

export async function startCallback(callbackId: string): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/calls/callback/${callbackId}/start`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if (response.ok) {
            showNotification('Callback initiated', 'success');
            loadCallbackQueue();
        }
    } catch (error: unknown) {
        console.error('Error starting callback:', error);
        showNotification('Failed to start callback', 'error');
    }
}

export async function cancelCallback(callbackId: string): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/calls/callback/${callbackId}/cancel`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if (response.ok) {
            showNotification('Callback cancelled', 'success');
            loadCallbackQueue();
        }
    } catch (error: unknown) {
        console.error('Error cancelling callback:', error);
        showNotification('Failed to cancel callback', 'error');
    }
}

export async function loadMobilePushDevices(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/integrations/mobile-push/devices`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data: MobilePushDevicesResponse = await response.json();

        const container = document.getElementById('mobile-push-devices') as HTMLElement | null;
        if (!container) return;

        const devices = data.devices ?? [];
        if (devices.length === 0) {
            container.innerHTML = '<div class="info-box">No registered devices</div>';
            return;
        }

        container.innerHTML = devices.map(d => `
            <div class="device-item">
                <strong>${escapeHtml(d.name || d.device_id)}</strong> - ${escapeHtml(d.platform || 'Unknown')}
                <span class="status-badge ${d.active ? 'enabled' : 'disabled'}">${d.active ? 'Active' : 'Inactive'}</span>
            </div>
        `).join('');
    } catch (error: unknown) {
        console.error('Error loading mobile push devices:', error);
    }
}

export async function loadSpeechAnalyticsConfigs(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/framework/speech-analytics/configs`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data: SpeechAnalyticsResponse = await response.json();

        const container = document.getElementById('speech-analytics-configs') as HTMLElement | null;
        if (container) {
            container.innerHTML = JSON.stringify(data.configs ?? [], null, 2);
        }
    } catch (error: unknown) {
        console.error('Error loading speech analytics:', error);
    }
}

// Backward compatibility
window.loadFraudAlerts = loadFraudAlerts;
window.loadCallbackQueue = loadCallbackQueue;
window.startCallback = startCallback;
window.cancelCallback = cancelCallback;
window.loadMobilePushDevices = loadMobilePushDevices;
window.loadSpeechAnalyticsConfigs = loadSpeechAnalyticsConfigs;
