/**
 * Provisioning page module.
 * Handles device provisioning, templates, and phonebook settings.
 */

import { getAuthHeaders, getApiBaseUrl } from '../api/client.js';
import { showNotification } from '../ui/notifications.js';
import { escapeHtml } from '../utils/html.js';

let supportedVendors = [];
let supportedModels = {};

export async function loadProvisioning() {
    await Promise.all([
        loadSupportedVendors(),
        loadProvisioningDevices(),
        loadProvisioningTemplates(),
        loadProvisioningSettings(),
        loadPhonebookSettings()
    ]);
}

export async function loadSupportedVendors() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/provisioning/vendors`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        supportedVendors = data.vendors || [];
        populateProvisioningFormDropdowns();
    } catch (error) {
        console.error('Error loading vendors:', error);
    }
}

export async function loadProvisioningDevices() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/provisioning/devices`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        const tbody = document.getElementById('provisioning-devices-body');
        if (!tbody) return;

        const devices = data.devices || [];
        if (devices.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No provisioned devices</td></tr>';
            return;
        }

        tbody.innerHTML = devices.map(d => `
            <tr>
                <td>${escapeHtml(d.mac_address || '')}</td>
                <td>${escapeHtml(d.model || '')}</td>
                <td>${escapeHtml(d.extension || '')}</td>
                <td>${escapeHtml(d.label || '')}</td>
                <td><span class="status-badge ${d.status === 'active' ? 'enabled' : 'disabled'}">${d.status || 'unknown'}</span></td>
                <td><button class="btn btn-danger btn-sm" onclick="deleteDevice('${escapeHtml(d.mac_address)}')">Delete</button></td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading devices:', error);
    }
}

export async function loadProvisioningTemplates() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/provisioning/templates`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        const container = document.getElementById('provisioning-templates-list');
        if (!container) return;

        const templates = data.templates || [];
        if (templates.length === 0) {
            container.innerHTML = '<div class="info-box">No templates configured</div>';
            return;
        }

        container.innerHTML = templates.map(t => `
            <div class="template-item">
                <strong>${escapeHtml(t.name)}</strong> - ${escapeHtml(t.manufacturer || 'Generic')}
                <button class="btn btn-sm btn-secondary" onclick="viewTemplate('${escapeHtml(t.name)}')">View</button>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading templates:', error);
    }
}

export async function loadProvisioningSettings() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/provisioning/settings`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data = await response.json();

        const el = (id) => document.getElementById(id);
        if (el('provisioning-enabled')) el('provisioning-enabled').checked = data.enabled || false;
        if (el('provisioning-url-format')) el('provisioning-url-format').value = data.url_format || '';
    } catch (error) {
        console.error('Error loading provisioning settings:', error);
    }
}

export async function loadPhonebookSettings() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/provisioning/phonebook-settings`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data = await response.json();

        const el = (id) => document.getElementById(id);
        if (el('ldap-phonebook-enabled')) el('ldap-phonebook-enabled').checked = data.ldap_enabled || false;
        if (el('remote-phonebook-enabled')) el('remote-phonebook-enabled').checked = data.remote_enabled || false;
    } catch (error) {
        console.error('Error loading phonebook settings:', error);
    }
}

export async function deleteDevice(macAddress) {
    if (!confirm(`Delete device ${macAddress}?`)) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/provisioning/devices/${macAddress}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (response.ok) {
            showNotification('Device deleted', 'success');
            loadProvisioningDevices();
        } else {
            showNotification('Failed to delete device', 'error');
        }
    } catch (error) {
        console.error('Error deleting device:', error);
        showNotification('Failed to delete device', 'error');
    }
}

function populateProvisioningFormDropdowns() {
    const vendorSelect = document.getElementById('device-vendor');
    if (!vendorSelect) return;
    vendorSelect.innerHTML = '<option value="">Select Vendor</option>';
    supportedVendors.forEach(v => {
        const option = document.createElement('option');
        option.value = v;
        option.textContent = v;
        vendorSelect.appendChild(option);
    });
}

export function viewTemplate(name) {
    showNotification(`Viewing template: ${name}`, 'info');
}

// Backward compatibility
window.loadProvisioning = loadProvisioning;
window.loadSupportedVendors = loadSupportedVendors;
window.loadProvisioningDevices = loadProvisioningDevices;
window.loadProvisioningTemplates = loadProvisioningTemplates;
window.loadProvisioningSettings = loadProvisioningSettings;
window.loadPhonebookSettings = loadPhonebookSettings;
window.deleteDevice = deleteDevice;
window.viewTemplate = viewTemplate;
