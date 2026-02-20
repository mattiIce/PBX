/**
 * License management page module.
 * Handles license status, features, generation, installation, toggling, and revocation.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';

export async function loadLicenseStatus(): Promise<void> {
    const container = document.getElementById('license-status-container') as HTMLElement | null;
    if (!container) return;

    container.innerHTML = '<div class="loading">Loading license information...</div>';

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/license/status`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        if (data.success && data.license) {
            const license = data.license;
            const statusClass = license.status === 'active' || license.valid ? 'badge-success' : 'badge-danger';
            const statusText = license.status || (license.valid ? 'Active' : 'Invalid');

            container.innerHTML = `
                <div class="ad-status-grid">
                    <div class="ad-status-item">
                        <strong>License Type</strong>
                        <span>${(license.type || 'Unknown').toUpperCase()}</span>
                    </div>
                    <div class="ad-status-item">
                        <strong>Status</strong>
                        <span class="badge ${statusClass}">${statusText}</span>
                    </div>
                    <div class="ad-status-item">
                        <strong>Issued To</strong>
                        <span>${license.issued_to || 'N/A'}</span>
                    </div>
                    <div class="ad-status-item">
                        <strong>Expires</strong>
                        <span>${license.expires_at || license.expiration || 'Never'}</span>
                    </div>
                    <div class="ad-status-item">
                        <strong>Extensions</strong>
                        <span>${license.used_extensions ?? 0} / ${license.max_extensions ?? 'Unlimited'}</span>
                    </div>
                    <div class="ad-status-item">
                        <strong>Concurrent Calls</strong>
                        <span>${license.max_concurrent_calls ?? 'Unlimited'}</span>
                    </div>
                    <div class="ad-status-item">
                        <strong>Licensing Enabled</strong>
                        <span class="badge ${license.licensing_enabled !== false ? 'badge-success' : 'badge-warning'}">${license.licensing_enabled !== false ? 'Yes' : 'No (Open Source Mode)'}</span>
                    </div>
                    ${license.key ? `<div class="ad-status-item" style="grid-column: 1 / -1;">
                        <strong>License Key</strong>
                        <span style="font-family: monospace; font-size: 12px; word-break: break-all;">${license.key}</span>
                    </div>` : ''}
                </div>
            `;
        } else {
            container.innerHTML = '<div class="info-box">No license installed. System is running in open-source mode with all features available.</div>';
        }
    } catch (error: unknown) {
        console.error('Error loading license status:', error);
        container.innerHTML = '<div class="error-message">Failed to load license status</div>';
    }
}

export async function loadLicenseFeatures(): Promise<void> {
    const container = document.getElementById('license-features-container') as HTMLElement | null;
    if (!container) return;

    container.innerHTML = '<div class="loading">Loading features...</div>';

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/license/features`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        if (!data.licensing_enabled) {
            container.innerHTML = '<div class="info-box">Licensing disabled &mdash; all features are available (open-source mode).</div>';
            return;
        }

        const features: string[] = data.features ?? [];
        const limits: Record<string, number | null> = data.limits ?? {};

        let html = `<p style="margin-bottom: 10px;"><strong>License Type:</strong> ${(data.license_type || 'unknown').toUpperCase()}</p>`;

        if (Object.keys(limits).length > 0) {
            html += '<h4 style="margin: 15px 0 8px;">Limits</h4><div class="ad-status-grid">';
            for (const [name, value] of Object.entries(limits)) {
                html += `<div class="ad-status-item"><strong>${name.replace(/_/g, ' ')}</strong><span>${value ?? 'Unlimited'}</span></div>`;
            }
            html += '</div>';
        }

        if (features.length > 0) {
            html += '<h4 style="margin: 15px 0 8px;">Included Features</h4><div style="display: flex; flex-wrap: wrap; gap: 8px;">';
            for (const feature of features) {
                html += `<span class="badge badge-success" style="padding: 4px 10px;">${feature.replace(/_/g, ' ')}</span>`;
            }
            html += '</div>';
        }

        container.innerHTML = html;
    } catch (error: unknown) {
        console.error('Error loading license features:', error);
        container.innerHTML = '<div class="error-message">Failed to load license features</div>';
    }
}

export async function generateLicense(event?: Event): Promise<void> {
    if (event) event.preventDefault();

    const resultDiv = document.getElementById('generate-license-result') as HTMLElement | null;

    const licenseType = (document.getElementById('license-type') as HTMLSelectElement | null)?.value;
    const issuedTo = (document.getElementById('issued-to') as HTMLInputElement | null)?.value?.trim();
    const expirationDays = (document.getElementById('expiration-days') as HTMLInputElement | null)?.value;
    const maxExtensions = (document.getElementById('max-extensions') as HTMLInputElement | null)?.value;
    const maxConcurrentCalls = (document.getElementById('max-concurrent-calls') as HTMLInputElement | null)?.value;

    if (!licenseType || !issuedTo) {
        showNotification('License type and organization/person are required', 'error');
        return;
    }

    const body: Record<string, unknown> = {
        type: licenseType,
        issued_to: issuedTo,
    };
    if (expirationDays) body.expiration_days = parseInt(expirationDays, 10);
    if (maxExtensions) body.max_extensions = parseInt(maxExtensions, 10);
    if (maxConcurrentCalls) body.max_concurrent_calls = parseInt(maxConcurrentCalls, 10);

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/license/generate`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });

        const data = await response.json();
        if (data.success && data.license) {
            showNotification('License generated successfully', 'success');
            const licenseJson = JSON.stringify(data.license, null, 2);
            if (resultDiv) {
                resultDiv.innerHTML = `
                    <div class="config-section" style="margin-top: 10px; background: #e8f5e9; border: 1px solid #4caf50;">
                        <h4 style="margin-top: 0; color: #2e7d32;">Generated License</h4>
                        <pre style="background: #263238; color: #eeffff; padding: 15px; border-radius: 4px; overflow-x: auto; font-size: 12px; max-height: 300px;">${licenseJson}</pre>
                        <div class="action-buttons" style="margin-top: 10px;">
                            <button class="btn btn-primary" onclick="navigator.clipboard.writeText(document.getElementById('generated-license-json').textContent).then(()=>alert('Copied!'))">📋 Copy to Clipboard</button>
                            <button class="btn btn-success" onclick="autoInstallGeneratedLicense()">📥 Install This License</button>
                        </div>
                        <pre id="generated-license-json" style="display:none;">${licenseJson}</pre>
                    </div>
                `;
            }
        } else {
            showNotification(data.error || 'Failed to generate license', 'error');
            if (resultDiv) {
                resultDiv.innerHTML = `<div class="error-message">${data.error || 'Failed to generate license'}</div>`;
            }
        }
    } catch (error: unknown) {
        console.error('Error generating license:', error);
        showNotification('Failed to generate license', 'error');
        if (resultDiv) {
            resultDiv.innerHTML = '<div class="error-message">Failed to generate license</div>';
        }
    }
}

export async function autoInstallGeneratedLicense(): Promise<void> {
    const pre = document.getElementById('generated-license-json') as HTMLPreElement | null;
    if (!pre) return;

    try {
        const licenseData = JSON.parse(pre.textContent || '{}');
        await doInstallLicense(licenseData, false);
    } catch (error: unknown) {
        console.error('Error auto-installing license:', error);
        showNotification('Failed to install generated license', 'error');
    }
}

export async function installLicense(event?: Event): Promise<void> {
    if (event) event.preventDefault();

    const textarea = document.getElementById('license-data') as HTMLTextAreaElement | null;
    const enforceCheckbox = document.getElementById('enforce-licensing') as HTMLInputElement | null;
    const resultDiv = document.getElementById('install-license-result') as HTMLElement | null;

    if (!textarea || !textarea.value.trim()) {
        showNotification('Please enter license data (JSON)', 'error');
        return;
    }

    let licenseData: Record<string, unknown>;
    try {
        licenseData = JSON.parse(textarea.value.trim());
    } catch {
        showNotification('Invalid JSON format. Please check the license data.', 'error');
        return;
    }

    const enforceLicensing = enforceCheckbox?.checked ?? false;

    try {
        await doInstallLicense(licenseData, enforceLicensing);
        textarea.value = '';
        if (enforceCheckbox) enforceCheckbox.checked = false;
    } catch (error: unknown) {
        console.error('Error installing license:', error);
        showNotification('Failed to install license', 'error');
        if (resultDiv) {
            resultDiv.innerHTML = '<div class="error-message">Failed to install license</div>';
        }
    }
}

async function doInstallLicense(licenseData: Record<string, unknown>, enforceLicensing: boolean): Promise<void> {
    const resultDiv = document.getElementById('install-license-result') as HTMLElement | null;
    const API_BASE = getApiBaseUrl();

    const response = await fetchWithTimeout(`${API_BASE}/api/license/install`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
            license_data: licenseData,
            enforce_licensing: enforceLicensing
        })
    });

    const data = await response.json();
    if (data.success) {
        showNotification(data.message || 'License installed successfully', 'success');
        if (resultDiv) {
            resultDiv.innerHTML = `<div class="info-box" style="border-left-color: #4caf50;">${data.message || 'License installed successfully'}</div>`;
        }
        loadLicenseStatus();
        loadLicenseFeatures();
    } else {
        showNotification(data.error || 'Failed to install license', 'error');
        if (resultDiv) {
            resultDiv.innerHTML = `<div class="error-message">${data.error || 'Failed to install license'}</div>`;
        }
    }
}

export async function toggleLicensing(enabled: boolean): Promise<void> {
    const resultDiv = document.getElementById('licensing-toggle-result') as HTMLElement | null;
    const action = enabled ? 'enable' : 'disable';

    if (!confirm(`Are you sure you want to ${action} licensing?`)) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/license/toggle`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ enabled })
        });

        const data = await response.json();
        if (data.success) {
            showNotification(data.message || `Licensing ${action}d successfully`, 'success');
            if (resultDiv) {
                resultDiv.innerHTML = `<div class="info-box" style="border-left-color: #4caf50;">${data.message || `Licensing ${action}d successfully`}</div>`;
            }
            loadLicenseStatus();
            loadLicenseFeatures();
        } else {
            showNotification(data.error || `Failed to ${action} licensing`, 'error');
            if (resultDiv) {
                resultDiv.innerHTML = `<div class="error-message">${data.error || `Failed to ${action} licensing`}</div>`;
            }
        }
    } catch (error: unknown) {
        console.error(`Error toggling licensing:`, error);
        showNotification(`Failed to ${action} licensing`, 'error');
        if (resultDiv) {
            resultDiv.innerHTML = `<div class="error-message">Failed to ${action} licensing</div>`;
        }
    }
}

export async function revokeLicense(): Promise<void> {
    if (!confirm('Are you sure you want to revoke the current license? This action cannot be undone.')) return;

    const resultDiv = document.getElementById('revoke-license-result') as HTMLElement | null;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/license/revoke`, {
            method: 'POST',
            headers: getAuthHeaders()
        });

        const data = await response.json();
        if (data.success) {
            showNotification('License revoked successfully', 'success');
            if (resultDiv) {
                resultDiv.innerHTML = '<div class="info-box" style="border-left-color: #4caf50;">License revoked successfully</div>';
            }
            loadLicenseStatus();
            loadLicenseFeatures();
        } else {
            showNotification(data.error || 'Failed to revoke license', 'error');
            if (resultDiv) {
                resultDiv.innerHTML = `<div class="error-message">${data.error || 'Failed to revoke license'}</div>`;
            }
        }
    } catch (error: unknown) {
        console.error('Error revoking license:', error);
        showNotification('Failed to revoke license', 'error');
        if (resultDiv) {
            resultDiv.innerHTML = '<div class="error-message">Failed to revoke license</div>';
        }
    }
}

export async function removeLicenseLock(): Promise<void> {
    if (!confirm('Are you sure you want to remove the license lock? This will allow licensing to be disabled.')) return;

    const resultDiv = document.getElementById('remove-lock-result') as HTMLElement | null;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/license/remove_lock`, {
            method: 'POST',
            headers: getAuthHeaders()
        });

        const data = await response.json();
        if (data.success) {
            showNotification(data.message || 'License lock removed', 'success');
            if (resultDiv) {
                resultDiv.innerHTML = `<div class="info-box" style="border-left-color: #4caf50;">${data.message || 'License lock removed'}</div>`;
            }
        } else {
            showNotification(data.error || 'Failed to remove license lock', 'error');
            if (resultDiv) {
                resultDiv.innerHTML = `<div class="error-message">${data.error || 'Failed to remove license lock'}</div>`;
            }
        }
    } catch (error: unknown) {
        console.error('Error removing license lock:', error);
        showNotification('Failed to remove license lock', 'error');
        if (resultDiv) {
            resultDiv.innerHTML = '<div class="error-message">Failed to remove license lock</div>';
        }
    }
}

export function initLicenseManagement(): void {
    loadLicenseStatus();
    loadLicenseFeatures();
}

// Register all functions on window for onclick handlers in HTML
window.loadLicenseStatus = loadLicenseStatus;
window.loadLicenseFeatures = loadLicenseFeatures;
window.generateLicense = generateLicense;
window.autoInstallGeneratedLicense = autoInstallGeneratedLicense;
window.installLicense = installLicense;
window.toggleLicensing = toggleLicensing;
window.revokeLicense = revokeLicense;
window.removeLicenseLock = removeLicenseLock;
window.initLicenseManagement = initLicenseManagement;
