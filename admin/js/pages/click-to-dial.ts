/**
 * Click-to-Dial page module.
 * Handles click-to-dial configurations, call initiation, history,
 * and WebRTC phone configuration.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';
import { displayError } from '../ui/notifications.ts';
import { escapeHtml } from '../utils/html.ts';

// --- Interfaces ---

interface ExtensionEntry {
    number: string;
    name: string;
}

interface ClickToDialConfig {
    extension: string;
    enabled: boolean;
    default_caller_id?: string;
    auto_answer: boolean;
    browser_notification: boolean;
}

interface ClickToDialConfigsResponse {
    configs?: ClickToDialConfig[];
    error?: string;
}

interface ClickToDialConfigResponse {
    config: ClickToDialConfig;
    error?: string;
}

interface ClickToDialCallResponse {
    error?: string;
}

interface ClickToDialHistoryEntry {
    timestamp: string;
    extension: string;
    destination: string;
    duration?: number;
    status: string;
}

interface ClickToDialHistoryResponse {
    history?: ClickToDialHistoryEntry[];
    error?: string;
}

interface WebRTCPhoneConfigResponse {
    success: boolean;
    extension?: string;
    error?: string;
}

// Status to CSS class mapping
const STATUS_CLASS_MAP: Record<string, string> = {
    'completed': 'success',
    'failed': 'error',
    'cancelled': 'warning',
    'busy': 'warning',
    'no-answer': 'warning'
};

// --- Helper Functions ---

async function loadExtensionsForClickToDial(): Promise<ExtensionEntry[]> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/extensions`,
            { headers: getAuthHeaders() }
        );
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: { extensions?: ExtensionEntry[] } = await response.json();
        return data.extensions ?? [];
    } catch (error: unknown) {
        console.error('Error loading extensions for click-to-dial:', error);
        // Fall back to window.currentExtensions if available
        return (window as { currentExtensions?: ExtensionEntry[] }).currentExtensions ?? [];
    }
}

// --- Click-to-Dial Configs ---

export async function loadClickToDialConfigs(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/framework/click-to-dial/configs`,
            { headers: getAuthHeaders() }
        );
        const data: ClickToDialConfigsResponse = await response.json();

        if (data.error) {
            console.error('Error loading click-to-dial configs:', data.error);
            return;
        }

        // Load extensions from API instead of relying on window global
        const currentExtensions = await loadExtensionsForClickToDial();

        // Populate extension selects
        const extensionSelect = document.getElementById('ctd-extension-select') as HTMLSelectElement | null;
        const historyExtensionSelect = document.getElementById('ctd-history-extension') as HTMLSelectElement | null;

        if (extensionSelect && currentExtensions.length > 0) {
            extensionSelect.innerHTML = '<option value="">Select Extension</option>';
            for (const ext of currentExtensions) {
                const option = document.createElement('option');
                option.value = ext.number;
                option.textContent = `${ext.number} - ${ext.name}`;
                extensionSelect.appendChild(option);
            }
        } else if (extensionSelect) {
            extensionSelect.innerHTML = '<option value="">No extensions available</option>';
        }

        if (historyExtensionSelect && currentExtensions.length > 0) {
            historyExtensionSelect.innerHTML = '<option value="">All Extensions</option>';
            for (const ext of currentExtensions) {
                const option = document.createElement('option');
                option.value = ext.number;
                option.textContent = `${ext.number} - ${ext.name}`;
                historyExtensionSelect.appendChild(option);
            }
        } else if (historyExtensionSelect) {
            historyExtensionSelect.innerHTML = '<option value="">No extensions available</option>';
        }

        // Populate configurations table
        const tbody = document.getElementById('ctd-configs-table') as HTMLElement | null;
        if (!tbody) return;

        if (!data.configs || data.configs.length === 0) {
            tbody.innerHTML =
                '<tr><td colspan="6" style="text-align: center;">No configurations found. Configure extensions above.</td></tr>';
            return;
        }

        tbody.innerHTML = data.configs.map((config: ClickToDialConfig) => `
            <tr>
                <td>${escapeHtml(config.extension)}</td>
                <td><span class="status-badge ${config.enabled ? 'success' : 'error'}">${config.enabled ? 'Enabled' : 'Disabled'}</span></td>
                <td>${config.default_caller_id ? escapeHtml(config.default_caller_id) : '-'}</td>
                <td>${config.auto_answer ? 'Yes' : 'No'}</td>
                <td>${config.browser_notification ? 'Yes' : 'No'}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editClickToDialConfig('${escapeHtml(config.extension)}')">Edit</button>
                </td>
            </tr>
        `).join('');

    } catch (error: unknown) {
        console.error('Error loading click-to-dial configs:', error);
        if (error instanceof Error) {
            displayError(error, 'Loading click-to-dial configurations');
        }
    }
}

export function toggleClickToDialConfigSections(showConfig: boolean): void {
    const configSection = document.getElementById('ctd-config-section') as HTMLElement | null;
    const noExtensionSection = document.getElementById('ctd-no-extension') as HTMLElement | null;

    if (configSection && noExtensionSection) {
        configSection.style.display = showConfig ? 'block' : 'none';
        noExtensionSection.style.display = showConfig ? 'none' : 'block';
    }
}

export async function loadClickToDialConfig(): Promise<void> {
    const extensionSelect = document.getElementById('ctd-extension-select') as HTMLSelectElement | null;
    const extension = extensionSelect?.value;

    if (!extension) {
        toggleClickToDialConfigSections(false);
        return;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/framework/click-to-dial/config/${extension}`,
            { headers: getAuthHeaders() }
        );
        const data: ClickToDialConfigResponse = await response.json();

        if (data.error) {
            console.error('Error loading config:', data.error);
            // Show default config for new extension
            const currentExtEl = document.getElementById('ctd-current-extension') as HTMLElement | null;
            if (currentExtEl) currentExtEl.textContent = extension;
            const enabledEl = document.getElementById('ctd-enabled') as HTMLInputElement | null;
            if (enabledEl) enabledEl.checked = true;
            const callerIdEl = document.getElementById('ctd-caller-id') as HTMLInputElement | null;
            if (callerIdEl) callerIdEl.value = '';
            const autoAnswerEl = document.getElementById('ctd-auto-answer') as HTMLInputElement | null;
            if (autoAnswerEl) autoAnswerEl.checked = false;
            const browserNotifEl = document.getElementById('ctd-browser-notification') as HTMLInputElement | null;
            if (browserNotifEl) browserNotifEl.checked = true;
        } else {
            const currentExtEl = document.getElementById('ctd-current-extension') as HTMLElement | null;
            if (currentExtEl) currentExtEl.textContent = extension;
            const enabledEl = document.getElementById('ctd-enabled') as HTMLInputElement | null;
            if (enabledEl) enabledEl.checked = data.config.enabled;
            const callerIdEl = document.getElementById('ctd-caller-id') as HTMLInputElement | null;
            if (callerIdEl) callerIdEl.value = data.config.default_caller_id ?? '';
            const autoAnswerEl = document.getElementById('ctd-auto-answer') as HTMLInputElement | null;
            if (autoAnswerEl) autoAnswerEl.checked = data.config.auto_answer;
            const browserNotifEl = document.getElementById('ctd-browser-notification') as HTMLInputElement | null;
            if (browserNotifEl) browserNotifEl.checked = data.config.browser_notification;
        }

        toggleClickToDialConfigSections(true);

    } catch (error: unknown) {
        console.error('Error loading click-to-dial config:', error);
        if (error instanceof Error) {
            displayError(error, 'Loading click-to-dial configuration');
        }
    }
}

export async function saveClickToDialConfig(event: Event): Promise<void> {
    event.preventDefault();

    const currentExtEl = document.getElementById('ctd-current-extension') as HTMLElement | null;
    const extension = currentExtEl?.textContent;
    if (!extension) {
        showNotification('No extension selected', 'error');
        return;
    }

    const config = {
        enabled: (document.getElementById('ctd-enabled') as HTMLInputElement | null)?.checked ?? false,
        default_caller_id: (document.getElementById('ctd-caller-id') as HTMLInputElement | null)?.value.trim() || null,
        auto_answer: (document.getElementById('ctd-auto-answer') as HTMLInputElement | null)?.checked ?? false,
        browser_notification: (document.getElementById('ctd-browser-notification') as HTMLInputElement | null)?.checked ?? false
    };

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/framework/click-to-dial/config/${extension}`,
            {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(config)
            }
        );

        const data: ClickToDialCallResponse = await response.json();

        if (data.error) {
            showNotification(`Error: ${data.error}`, 'error');
        } else {
            showNotification('Configuration saved successfully', 'success');
            loadClickToDialConfigs();
        }
    } catch (error: unknown) {
        console.error('Error saving config:', error);
        if (error instanceof Error) {
            displayError(error, 'Saving click-to-dial configuration');
        }
        showNotification('Error saving configuration', 'error');
    }
}

export async function editClickToDialConfig(extension: string): Promise<void> {
    const select = document.getElementById('ctd-extension-select') as HTMLSelectElement | null;
    if (select) {
        select.value = extension;
        await loadClickToDialConfig();
        const configSection = document.getElementById('ctd-config-section') as HTMLElement | null;
        if (configSection) {
            configSection.scrollIntoView({ behavior: 'smooth' });
        }
    }
}

export async function initiateClickToDial(): Promise<void> {
    const extensionSelect = document.getElementById('ctd-extension-select') as HTMLSelectElement | null;
    const extension = extensionSelect?.value;
    const phoneNumberInput = document.getElementById('ctd-phone-number') as HTMLInputElement | null;
    const phoneNumber = phoneNumberInput?.value.trim();

    if (!extension) {
        showNotification('Please select an extension', 'error');
        return;
    }

    if (!phoneNumber) {
        showNotification('Please enter a phone number', 'error');
        return;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/framework/click-to-dial/call/${extension}`,
            {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ destination: phoneNumber })
            }
        );

        const data: ClickToDialCallResponse = await response.json();

        if (data.error) {
            showNotification(`Error: ${data.error}`, 'error');
        } else {
            showNotification(
                `Call initiated from extension ${extension} to ${phoneNumber}`,
                'success'
            );
            // Clear the phone number field
            if (phoneNumberInput) {
                phoneNumberInput.value = '';
            }
            // Reload history after a short delay
            setTimeout(() => loadClickToDialHistory(), 1000);
        }
    } catch (error: unknown) {
        console.error('Error initiating call:', error);
        if (error instanceof Error) {
            displayError(error, 'Initiating click-to-dial call');
        }
        showNotification('Error initiating call', 'error');
    }
}

export async function loadClickToDialHistory(): Promise<void> {
    const extensionSelect = document.getElementById('ctd-history-extension') as HTMLSelectElement | null;
    const extension = extensionSelect?.value;
    const tbody = document.getElementById('ctd-history-table') as HTMLElement | null;

    if (!tbody) return;

    if (!extension) {
        tbody.innerHTML =
            '<tr><td colspan="5" style="text-align: center;">Select an extension to view history</td></tr>';
        return;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/framework/click-to-dial/history/${extension}`,
            { headers: getAuthHeaders() }
        );
        const data: ClickToDialHistoryResponse = await response.json();

        if (data.error) {
            tbody.innerHTML =
                `<tr><td colspan="5" style="text-align: center;">Error: ${escapeHtml(data.error)}</td></tr>`;
            return;
        }

        if (!data.history || data.history.length === 0) {
            tbody.innerHTML =
                '<tr><td colspan="5" style="text-align: center;">No call history found</td></tr>';
            return;
        }

        tbody.innerHTML = data.history.map((call: ClickToDialHistoryEntry) => {
            const timestamp = new Date(call.timestamp).toLocaleString();
            const duration = call.duration ? `${call.duration}s` : '-';
            const statusClass = STATUS_CLASS_MAP[call.status] ?? 'warning';

            return `
                <tr>
                    <td>${escapeHtml(timestamp)}</td>
                    <td>${escapeHtml(call.extension)}</td>
                    <td>${escapeHtml(call.destination)}</td>
                    <td>${duration}</td>
                    <td><span class="status-badge ${statusClass}">${escapeHtml(call.status)}</span></td>
                </tr>
            `;
        }).join('');

    } catch (error: unknown) {
        console.error('Error loading history:', error);
        if (error instanceof Error) {
            displayError(error, 'Loading click-to-dial history');
        }
        if (tbody) {
            tbody.innerHTML =
                '<tr><td colspan="5" style="text-align: center;">Error loading history</td></tr>';
        }
    }
}

// --- WebRTC Phone Configuration ---

declare const DEFAULT_WEBRTC_EXTENSION: string | undefined;
declare function initWebRTCPhone(): void;

export async function loadWebRTCPhoneConfig(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/webrtc/phone-config`, {
            headers: getAuthHeaders()
        });
        const data: WebRTCPhoneConfigResponse = await response.json();

        if (data.success) {
            const extensionInput = document.getElementById('webrtc-phone-extension') as HTMLInputElement | null;
            if (extensionInput) {
                extensionInput.value = data.extension ?? (typeof DEFAULT_WEBRTC_EXTENSION !== 'undefined' ? DEFAULT_WEBRTC_EXTENSION : '');
            }

            // Reinitialize the WebRTC phone with the new extension
            if (typeof initWebRTCPhone === 'function') {
                initWebRTCPhone();
            }
        } else {
            console.error('Failed to load WebRTC phone config:', data.error);
        }
    } catch (error: unknown) {
        console.error('Error loading WebRTC phone config:', error);
    }
}

export async function saveWebRTCPhoneConfig(event: Event): Promise<void> {
    event.preventDefault();

    const extensionInput = document.getElementById('webrtc-phone-extension') as HTMLInputElement | null;
    const extension = extensionInput?.value.trim() ?? '';

    if (!extension) {
        showNotification('Please enter an extension', 'error');
        return;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/webrtc/phone-config`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ extension })
        });

        const data: WebRTCPhoneConfigResponse = await response.json();

        if (data.success) {
            showNotification('Phone extension saved successfully! Reloading phone...', 'success');
            // Reinitialize the WebRTC phone with the new extension
            if (typeof initWebRTCPhone === 'function') {
                initWebRTCPhone();
            }
        } else {
            showNotification(
                `Error: ${data.error ?? 'Failed to save phone extension'}`,
                'error'
            );
        }
    } catch (error: unknown) {
        console.error('Error saving WebRTC phone config:', error);
        const message = error instanceof Error ? error.message : String(error);
        showNotification(`Error: ${message}`, 'error');
    }
}

// Backward compatibility
window.loadClickToDialConfigs = loadClickToDialConfigs;
window.toggleClickToDialConfigSections = toggleClickToDialConfigSections;
window.loadClickToDialConfig = loadClickToDialConfig;
window.saveClickToDialConfig = saveClickToDialConfig;
window.editClickToDialConfig = editClickToDialConfig;
window.initiateClickToDial = initiateClickToDial;
window.loadClickToDialHistory = loadClickToDialHistory;
window.loadWebRTCPhoneConfig = loadWebRTCPhoneConfig;
window.saveWebRTCPhoneConfig = saveWebRTCPhoneConfig;
