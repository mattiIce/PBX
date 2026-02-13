/**
 * License management page module.
 * Handles license status, features, generation, and installation.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';

interface License {
    type?: string;
    valid?: boolean;
    expires_at?: string;
    used_extensions?: number;
    max_extensions?: number | string;
}

interface LicenseStatusResponse {
    success: boolean;
    license?: License;
}

interface LicenseFeaturesResponse {
    licensing_enabled?: boolean;
    features?: Record<string, boolean>;
}

interface InstallLicenseResponse {
    success: boolean;
    error?: string;
}

export async function loadLicenseStatus(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/license/status`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: LicenseStatusResponse = await response.json();

        if (data.success && data.license) {
            const license = data.license;
            const el = (id: string): HTMLElement | null => document.getElementById(id);
            if (el('license-type')) (el('license-type') as HTMLElement).textContent = license.type || 'Unknown';
            if (el('license-status')) {
                (el('license-status') as HTMLElement).textContent = license.valid ? 'Valid' : 'Invalid';
                (el('license-status') as HTMLElement).className = `status-badge ${license.valid ? 'enabled' : 'disabled'}`;
            }
            if (el('license-expires')) (el('license-expires') as HTMLElement).textContent = license.expires_at || 'Never';
            if (el('license-extensions')) (el('license-extensions') as HTMLElement).textContent = `${license.used_extensions || 0} / ${license.max_extensions || 'Unlimited'}`;
        }
    } catch (error: unknown) {
        console.error('Error loading license status:', error);
    }
}

export async function loadLicenseFeatures(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/license/features`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: LicenseFeaturesResponse = await response.json();

        const container = document.getElementById('license-features-list') as HTMLElement | null;
        if (!container) return;

        if (!data.licensing_enabled) {
            container.innerHTML = '<div class="info-box">Licensing disabled - all features available</div>';
            return;
        }

        const features = data.features || {};
        container.innerHTML = Object.entries(features).map(([name, enabled]) =>
            `<div class="feature-item">
                <span>${name.replace(/_/g, ' ')}</span>
                <span class="status-badge ${enabled ? 'enabled' : 'disabled'}">${enabled ? 'Available' : 'Locked'}</span>
            </div>`
        ).join('');
    } catch (error: unknown) {
        console.error('Error loading license features:', error);
    }
}

export async function installLicense(): Promise<void> {
    const keyInput = document.getElementById('license-key-input') as HTMLInputElement | null;
    if (!keyInput || !keyInput.value.trim()) {
        showNotification('Please enter a license key', 'error');
        return;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/license/install`, {
            method: 'POST',
            headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ license_key: keyInput.value.trim() })
        });

        const data: InstallLicenseResponse = await response.json();
        if (data.success) {
            showNotification('License installed successfully', 'success');
            keyInput.value = '';
            loadLicenseStatus();
            loadLicenseFeatures();
        } else {
            showNotification(data.error || 'Failed to install license', 'error');
        }
    } catch (error: unknown) {
        console.error('Error installing license:', error);
        showNotification('Failed to install license', 'error');
    }
}

export function initLicenseManagement(): void {
    loadLicenseStatus();
    loadLicenseFeatures();
}

// Backward compatibility
window.loadLicenseStatus = loadLicenseStatus;
window.loadLicenseFeatures = loadLicenseFeatures;
window.installLicense = installLicense;
window.initLicenseManagement = initLicenseManagement;
