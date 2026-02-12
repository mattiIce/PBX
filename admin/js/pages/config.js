/**
 * Configuration page module.
 * Handles system configuration, feature toggles, and SSL management.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.js';
import { showNotification } from '../ui/notifications.js';

const CONFIG_SAVE_SUCCESS_MESSAGE = 'Configuration saved successfully. Restart may be required for some changes.';

export async function loadConfig() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/config/full`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const config = await response.json();

        // Feature Toggles
        if (config.features) {
            const featureIds = [
                'call-recording', 'call-transfer', 'call-hold', 'conference',
                'voicemail', 'call-parking', 'call-queues', 'presence',
                'music-on-hold', 'auto-attendant'
            ];
            featureIds.forEach(id => {
                const el = document.getElementById(`feature-${id}`);
                const key = id.replace(/-/g, '_');
                if (el) el.checked = config.features[key] || false;
            });
        }

        // Populate other config sections
        if (config.voicemail) {
            const el = (id) => document.getElementById(id);
            if (el('vm-max-duration')) el('vm-max-duration').value = config.voicemail.max_duration || 120;
            if (el('vm-max-messages')) el('vm-max-messages').value = config.voicemail.max_messages || 100;
        }
    } catch (error) {
        console.error('Error loading config:', error);
        showNotification('Failed to load configuration', 'error');
    }
}

export async function loadFeaturesStatus() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/config/features`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        if (data.features) {
            Object.entries(data.features).forEach(([key, enabled]) => {
                const el = document.getElementById(`feature-${key.replace(/_/g, '-')}`);
                if (el) el.checked = enabled;
            });
        }
    } catch (error) {
        console.error('Error loading features status:', error);
    }
}

export async function saveConfigSection(section) {
    try {
        const API_BASE = getApiBaseUrl();
        const form = document.getElementById(`${section}-form`);
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
            const error = await response.json();
            showNotification(error.error || 'Failed to save configuration', 'error');
        }
    } catch (error) {
        console.error(`Error saving ${section} config:`, error);
        showNotification('Failed to save configuration', 'error');
    }
}

export async function loadSSLStatus() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/ssl/status`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        const statusEl = document.getElementById('ssl-status');
        if (statusEl) {
            statusEl.textContent = data.enabled ? 'Enabled' : 'Disabled';
            statusEl.className = `status-badge ${data.enabled ? 'enabled' : 'disabled'}`;
        }

        if (data.certificate) {
            const certEl = document.getElementById('ssl-cert-details');
            if (certEl) {
                certEl.innerHTML = `
                    <div>Subject: ${data.certificate.subject || 'N/A'}</div>
                    <div>Issuer: ${data.certificate.issuer || 'N/A'}</div>
                    <div>Expires: ${data.certificate.expires || 'N/A'}</div>
                `;
            }
        }
    } catch (error) {
        console.error('Error loading SSL status:', error);
    }
}

export async function generateSSLCertificate() {
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
    } catch (error) {
        console.error('Error generating SSL certificate:', error);
        showNotification('Failed to generate SSL certificate', 'error');
    }
}

// Backward compatibility
window.loadConfig = loadConfig;
window.loadFeaturesStatus = loadFeaturesStatus;
window.saveConfigSection = saveConfigSection;
window.loadSSLStatus = loadSSLStatus;
window.generateSSLCertificate = generateSSLCertificate;
