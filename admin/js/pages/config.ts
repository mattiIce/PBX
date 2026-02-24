/**
 * Configuration page module.
 * Handles system configuration, feature toggles, and SSL management.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';

interface VoicemailConfig {
    max_duration?: number;
    max_messages?: number;
}

interface FullConfig {
    features?: Record<string, boolean>;
    voicemail?: VoicemailConfig;
}

interface FeaturesResponse {
    features?: Record<string, boolean>;
}

interface SSLCertificate {
    subject?: string;
    issuer?: string;
    expires?: string;
}

interface SSLStatus {
    enabled: boolean;
    certificate?: SSLCertificate;
}

interface ErrorResponse {
    error?: string;
}

const CONFIG_SAVE_SUCCESS_MESSAGE = 'Configuration saved successfully. Restart may be required for some changes.';

export async function loadConfig(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/config/full`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const config: FullConfig = await response.json();

        // Feature Toggles
        if (config.features) {
            const featureIds = [
                'call-recording', 'call-transfer', 'call-hold', 'conference',
                'voicemail', 'call-parking', 'call-queues', 'presence',
                'music-on-hold', 'auto-attendant',
            ] as const;
            for (const id of featureIds) {
                const el = document.getElementById(`feature-${id}`) as HTMLInputElement | null;
                const key = id.replace(/-/g, '_');
                if (el) el.checked = config.features[key] ?? false;
            }
        }

        // Populate other config sections
        if (config.voicemail) {
            const el = (id: string): HTMLElement | null => document.getElementById(id);
            if (el('voicemail-max-duration')) (el('voicemail-max-duration') as HTMLInputElement).value = String(config.voicemail.max_duration ?? 120);
        }
    } catch (error: unknown) {
        console.error('Error loading config:', error);
        showNotification('Failed to load configuration', 'error');
    }
}

export async function loadFeaturesStatus(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/config/features`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: FeaturesResponse = await response.json();

        if (data.features) {
            for (const [key, enabled] of Object.entries(data.features)) {
                const el = document.getElementById(`feature-${key.replace(/_/g, '-')}`) as HTMLInputElement | null;
                if (el) el.checked = enabled;
            }
        }
    } catch (error: unknown) {
        console.error('Error loading features status:', error);
    }
}

export async function saveConfigSection(section: string): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const form = document.getElementById(`${section}-form`) as HTMLFormElement | null;
        if (!form) return;

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        const response = await fetch(`${API_BASE}/api/config/${section}`, {
            method: 'POST',
            headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            showNotification(CONFIG_SAVE_SUCCESS_MESSAGE, 'success');
        } else {
            const error: ErrorResponse = await response.json();
            showNotification(error.error || 'Failed to save configuration', 'error');
        }
    } catch (error: unknown) {
        console.error(`Error saving ${section} config:`, error);
        showNotification('Failed to save configuration', 'error');
    }
}

export async function loadSSLStatus(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/ssl/status`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: SSLStatus = await response.json();

        const statusEl = document.getElementById('ssl-status-info') as HTMLElement | null;
        if (statusEl) {
            statusEl.textContent = data.enabled ? 'Enabled' : 'Disabled';
            statusEl.className = `status-badge ${data.enabled ? 'enabled' : 'disabled'}`;
        }

        if (data.certificate) {
            const certEl = document.getElementById('ssl-cert-details') as HTMLElement | null;
            if (certEl) {
                certEl.innerHTML = `
                    <div>Subject: ${data.certificate.subject || 'N/A'}</div>
                    <div>Issuer: ${data.certificate.issuer || 'N/A'}</div>
                    <div>Expires: ${data.certificate.expires || 'N/A'}</div>
                `;
            }
        }
    } catch (error: unknown) {
        console.error('Error loading SSL status:', error);
    }
}

export async function generateSSLCertificate(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/ssl/generate`, {
            method: 'POST',
            headers: getAuthHeaders()
        });

        if (response.ok) {
            showNotification('SSL certificate generated successfully', 'success');
            loadSSLStatus();
        } else {
            showNotification('Failed to generate SSL certificate', 'error');
        }
    } catch (error: unknown) {
        console.error('Error generating SSL certificate:', error);
        showNotification('Failed to generate SSL certificate', 'error');
    }
}

export async function refreshSSLStatus(): Promise<void> {
    await loadSSLStatus();
    showNotification('SSL status refreshed', 'success');
}

const CONFIG_FORM_SECTIONS = [
    'features-config',
    'voicemail-config',
    'email-config',
    'recording-config',
    'security-config',
    'advanced-features',
    'conference-config',
    'ssl-config',
] as const;

function initConfigForms(): void {
    for (const section of CONFIG_FORM_SECTIONS) {
        const form = document.getElementById(`${section}-form`) as HTMLFormElement | null;
        if (form) {
            form.addEventListener('submit', async (e: Event) => {
                e.preventDefault();
                await saveConfigSection(section);
            });
        }
    }
}

// Backward compatibility
window.loadConfig = loadConfig;
window.loadFeaturesStatus = loadFeaturesStatus;
window.saveConfigSection = saveConfigSection;
window.loadSSLStatus = loadSSLStatus;
window.generateSSLCertificate = generateSSLCertificate;
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- legacy backward compat
(window as any).refreshSSLStatus = refreshSSLStatus;

// Self-initialize form handlers once the DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initConfigForms);
} else {
    initConfigForms();
}
