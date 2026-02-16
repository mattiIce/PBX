/**
 * Calls page module.
 * Handles active calls display, codec status, and DTMF configuration.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';
import { escapeHtml } from '../utils/html.ts';

interface Codec {
    name: string;
    enabled: boolean;
}

interface CodecResponse {
    codecs?: Codec[];
}

interface DTMFConfig {
    mode?: string;
    threshold?: number;
}

export async function loadCalls(): Promise<void> {
    const callsList = document.getElementById('calls-list') as HTMLElement | null;
    if (!callsList) return;
    callsList.innerHTML = '<div class="loading">Loading calls...</div>';

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/calls`, {
            headers: getAuthHeaders()
        });
        const calls: unknown[] = await response.json();

        if (calls.length === 0) {
            callsList.innerHTML = '<div class="loading">No active calls</div>';
            return;
        }

        callsList.innerHTML = calls.map(call => `
            <div class="call-item"><strong>Call:</strong> ${escapeHtml(String(call))}</div>
        `).join('');
    } catch (error: unknown) {
        console.error('Error loading calls:', error);
        callsList.innerHTML = '<div class="loading">Error loading calls</div>';
    }
}

export async function loadCodecStatus(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/config/codecs`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: CodecResponse = await response.json();

        const container = document.getElementById('codec-status') as HTMLElement | null;
        if (container && data.codecs) {
            container.innerHTML = data.codecs.map(c =>
                `<div class="codec-item">${escapeHtml(c.name)} - ${c.enabled ? 'Enabled' : 'Disabled'}</div>`
            ).join('');
        }
    } catch (error: unknown) {
        console.error('Error loading codec status:', error);
    }
}

export async function loadDTMFConfig(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/config/dtmf`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: DTMFConfig = await response.json();

        const modeSelect = document.getElementById('dtmf-mode') as HTMLSelectElement | null;
        if (modeSelect) modeSelect.value = data.mode ?? 'rfc2833';

        const threshold = document.getElementById('dtmf-threshold') as HTMLInputElement | null;
        if (threshold) threshold.value = String(data.threshold ?? -30);
    } catch (error: unknown) {
        console.error('Error loading DTMF config:', error);
    }
}

export async function saveDTMFConfig(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const config = {
            mode: (document.getElementById('dtmf-mode') as HTMLSelectElement | null)?.value ?? 'rfc2833',
            threshold: parseInt((document.getElementById('dtmf-threshold') as HTMLInputElement | null)?.value ?? '-30')
        };

        const response = await fetch(`${API_BASE}/api/config/dtmf`, {
            method: 'POST',
            headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            showNotification('DTMF configuration saved', 'success');
        } else {
            showNotification('Failed to save DTMF configuration', 'error');
        }
    } catch (error: unknown) {
        console.error('Error saving DTMF config:', error);
        showNotification('Failed to save DTMF configuration', 'error');
    }
}

// Backward compatibility
window.loadCalls = loadCalls;
window.loadCodecStatus = loadCodecStatus;
window.loadDTMFConfig = loadDTMFConfig;
window.saveDTMFConfig = saveDTMFConfig;
