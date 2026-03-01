/**
 * Provisioning page module.
 * Handles device provisioning, templates, and phonebook settings.
 */

import { getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';
import { escapeHtml } from '../utils/html.ts';

interface ProvisioningDevice {
    mac_address?: string;
    model?: string;
    vendor?: string;
    extension?: string;
    extension_number?: string;
    label?: string;
    status?: string;
    created_at?: string;
    last_provisioned?: string;
    config_url?: string;
    device_type?: string;
}

interface VendorsResponse {
    vendors?: string[];
    models?: Record<string, string[]>;
}

interface ProvisioningTemplate {
    name?: string;
    vendor?: string;
    model?: string;
    manufacturer?: string;
    is_custom?: boolean;
    template_path?: string;
    type?: string;
    size?: number;
}

interface TemplatesResponse {
    templates?: ProvisioningTemplate[];
}

interface ProvisioningSettingsResponse {
    enabled?: boolean;
    url_format?: string;
}

interface PhonebookSettingsResponse {
    ldap_enabled?: boolean;
    remote_enabled?: boolean;
}

interface ExtensionEntry {
    number: string;
    name: string;
}

let supportedVendors: string[] = [];
let supportedModels: Record<string, string[]> = {};

export async function loadProvisioning(): Promise<void> {
    await Promise.all([
        loadSupportedVendors(),
        loadExtensionsForProvisioning(),
        loadProvisioningDevices(),
        loadProvisioningTemplates(),
        loadProvisioningSettings(),
        loadPhonebookSettings()
    ]);
}

export async function loadSupportedVendors(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/provisioning/vendors`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: VendorsResponse = await response.json();
        supportedVendors = data.vendors || [];
        supportedModels = data.models || {};
        populateProvisioningFormDropdowns();
        populateSupportedVendorsList();
    } catch (error: unknown) {
        console.error('Error loading vendors:', error);
        const container = document.getElementById('supported-vendors-list');
        if (container) {
            container.innerHTML = '<p>Failed to load supported vendors.</p>';
        }
    }
}

async function loadExtensionsForProvisioning(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/extensions`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const extensions: ExtensionEntry[] = await response.json();

        const select = document.getElementById('device-extension') as HTMLSelectElement | null;
        if (!select) return;
        select.innerHTML = '<option value="">Select Extension</option>';

        for (const ext of extensions) {
            const option = document.createElement('option');
            option.value = ext.number;
            option.textContent = `${ext.number} - ${ext.name}`;
            select.appendChild(option);
        }
    } catch (error: unknown) {
        console.error('Error loading extensions for provisioning:', error);
    }
}

export async function loadProvisioningDevices(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/provisioning/devices`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const raw: ProvisioningDevice[] | { devices?: ProvisioningDevice[] } = await response.json();

        const tbody = document.getElementById('provisioning-devices-table-body') as HTMLElement | null;
        if (!tbody) return;

        // API returns a plain array; handle both shapes defensively
        const devices: ProvisioningDevice[] = Array.isArray(raw) ? raw : (raw.devices || []);
        if (devices.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8">No provisioned devices</td></tr>';
            return;
        }

        tbody.innerHTML = devices.map(d => `
            <tr>
                <td>${escapeHtml(d.mac_address || '')}</td>
                <td>${escapeHtml(d.extension_number || d.extension || '')}</td>
                <td>${escapeHtml(d.device_type || 'phone')}</td>
                <td>${escapeHtml(d.vendor || '')}</td>
                <td>${escapeHtml(d.model || '')}</td>
                <td>${escapeHtml(d.created_at || '')}</td>
                <td>${escapeHtml(d.last_provisioned || 'Never')}</td>
                <td><button class="btn btn-danger btn-sm" onclick="deleteDevice('${escapeHtml(d.mac_address || '')}')">Delete</button></td>
            </tr>
        `).join('');
    } catch (error: unknown) {
        console.error('Error loading devices:', error);
    }
}

export async function loadProvisioningTemplates(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/provisioning/templates`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: TemplatesResponse = await response.json();

        const container = document.getElementById('templates-table-body') as HTMLElement | null;
        if (!container) return;

        const templates = data.templates || [];
        if (templates.length === 0) {
            container.innerHTML = '<tr><td colspan="5">No templates configured</td></tr>';
            return;
        }

        container.innerHTML = templates.map(t => {
            const templateName = t.name || `${t.vendor || 'unknown'}_${t.model || 'unknown'}`;
            return `
            <tr>
                <td>${escapeHtml(t.vendor || t.manufacturer || 'Generic')}</td>
                <td>${escapeHtml(t.model || '')}</td>
                <td>${escapeHtml(t.is_custom ? 'custom' : 'built-in')}</td>
                <td>${t.size ? `${t.size} bytes` : '-'}</td>
                <td><button class="btn btn-sm btn-secondary" onclick="viewTemplate('${escapeHtml(templateName)}')">View</button></td>
            </tr>`;
        }).join('');
    } catch (error: unknown) {
        console.error('Error loading templates:', error);
    }
}

export async function loadProvisioningSettings(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/provisioning/settings`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data: ProvisioningSettingsResponse = await response.json();

        const el = (id: string): HTMLElement | null => document.getElementById(id);
        if (el('provisioning-enabled')) (el('provisioning-enabled') as HTMLInputElement).checked = data.enabled ?? false;
        if (el('provisioning-url-format')) (el('provisioning-url-format') as HTMLInputElement).value = data.url_format ?? '';

        toggleProvisioningEnabled();
    } catch (error: unknown) {
        console.error('Error loading provisioning settings:', error);
    }
}

export async function loadPhonebookSettings(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/provisioning/phonebook-settings`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data: PhonebookSettingsResponse = await response.json();

        const el = (id: string): HTMLElement | null => document.getElementById(id);
        if (el('ldap-phonebook-enabled')) (el('ldap-phonebook-enabled') as HTMLInputElement).checked = data.ldap_enabled ?? false;
        if (el('remote-phonebook-enabled')) (el('remote-phonebook-enabled') as HTMLInputElement).checked = data.remote_enabled ?? false;

        toggleLdapPhonebookSettings();
        toggleRemotePhonebookSettings();
    } catch (error: unknown) {
        console.error('Error loading phonebook settings:', error);
    }
}

export async function deleteDevice(macAddress: string): Promise<void> {
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
    } catch (error: unknown) {
        console.error('Error deleting device:', error);
        showNotification('Failed to delete device', 'error');
    }
}

function populateProvisioningFormDropdowns(): void {
    const vendorSelect = document.getElementById('device-vendor') as HTMLSelectElement | null;
    if (!vendorSelect) return;
    vendorSelect.innerHTML = '<option value="">Select Vendor</option>';
    for (const v of supportedVendors) {
        const option = document.createElement('option');
        option.value = v;
        option.textContent = v;
        vendorSelect.appendChild(option);
    }
}

function populateSupportedVendorsList(): void {
    const container = document.getElementById('supported-vendors-list');
    if (!container) return;

    if (supportedVendors.length === 0) {
        container.innerHTML = '<p>No supported vendors found.</p>';
        return;
    }

    const vendorSections = supportedVendors.map(vendor => {
        const models = supportedModels[vendor] || supportedModels[vendor.toLowerCase()] || [];
        const modelList = models.length > 0
            ? models.map(m => `<span class="badge">${escapeHtml(m.toUpperCase())}</span>`).join(' ')
            : '<em>No models</em>';
        return `<div style="margin-bottom: 8px;">
            <strong>${escapeHtml(vendor.charAt(0).toUpperCase() + vendor.slice(1))}</strong>: ${modelList}
        </div>`;
    }).join('');

    container.innerHTML = vendorSections;
}

export function updateModelOptions(): void {
    const vendorSelect = document.getElementById('device-vendor') as HTMLSelectElement | null;
    const modelSelect = document.getElementById('device-model') as HTMLSelectElement | null;
    if (!vendorSelect || !modelSelect) return;

    const vendor = vendorSelect.value;
    modelSelect.innerHTML = '';

    if (!vendor) {
        modelSelect.innerHTML = '<option value="">Select Vendor First</option>';
        return;
    }

    const models = supportedModels[vendor] || supportedModels[vendor.toLowerCase()] || [];
    if (models.length === 0) {
        modelSelect.innerHTML = '<option value="">No models available</option>';
        return;
    }

    modelSelect.innerHTML = '<option value="">Select Model</option>';
    for (const m of models) {
        const option = document.createElement('option');
        option.value = m;
        option.textContent = m;
        modelSelect.appendChild(option);
    }
}

export function toggleProvisioningEnabled(): void {
    const checkbox = document.getElementById('provisioning-enabled') as HTMLInputElement | null;
    const settings = document.getElementById('provisioning-settings') as HTMLElement | null;
    if (checkbox && settings) {
        settings.style.display = checkbox.checked ? 'block' : 'none';
    }
}

export async function saveProvisioningSettings(): Promise<void> {
    try {
        const val = (id: string): string => (document.getElementById(id) as HTMLInputElement)?.value ?? '';
        const chk = (id: string): boolean => (document.getElementById(id) as HTMLInputElement)?.checked ?? false;

        const data = {
            enabled: chk('provisioning-enabled'),
            server_ip: val('provisioning-server-ip'),
            port: parseInt(val('provisioning-port'), 10) || 9000,
            custom_templates_dir: val('provisioning-custom-dir'),
        };

        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/provisioning/settings`, {
            method: 'PUT',
            headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (response.ok) {
            showNotification('Provisioning settings saved', 'success');
        } else {
            showNotification('Failed to save provisioning settings', 'error');
        }
    } catch (error: unknown) {
        console.error('Error saving provisioning settings:', error);
        showNotification('Failed to save provisioning settings', 'error');
    }
}

export function toggleLdapPhonebookSettings(): void {
    const checkbox = document.getElementById('ldap-phonebook-enabled') as HTMLInputElement | null;
    const settings = document.getElementById('ldap-phonebook-settings') as HTMLElement | null;
    if (checkbox && settings) {
        settings.style.display = checkbox.checked ? 'block' : 'none';
    }
}

export function toggleRemotePhonebookSettings(): void {
    const checkbox = document.getElementById('remote-phonebook-enabled') as HTMLInputElement | null;
    const settings = document.getElementById('remote-phonebook-settings') as HTMLElement | null;
    if (checkbox && settings) {
        settings.style.display = checkbox.checked ? 'block' : 'none';
    }
}

export async function savePhonebookSettings(): Promise<void> {
    try {
        const val = (id: string): string => (document.getElementById(id) as HTMLInputElement)?.value ?? '';
        const chk = (id: string): boolean => (document.getElementById(id) as HTMLInputElement)?.checked ?? false;

        const data = {
            ldap_enabled: chk('ldap-phonebook-enabled'),
            ldap_server: val('ldap-phonebook-server'),
            ldap_port: parseInt(val('ldap-phonebook-port'), 10) || 636,
            ldap_base_dn: val('ldap-phonebook-base'),
            ldap_bind_user: val('ldap-phonebook-user'),
            ldap_bind_password: val('ldap-phonebook-password'),
            ldap_use_tls: chk('ldap-phonebook-tls'),
            ldap_display_name: val('ldap-phonebook-display-name'),
            remote_enabled: chk('remote-phonebook-enabled'),
            remote_refresh_interval: parseInt(val('remote-phonebook-refresh'), 10) || 60,
        };

        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/provisioning/phonebook-settings`, {
            method: 'PUT',
            headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (response.ok) {
            showNotification('Phone book settings saved', 'success');
        } else {
            showNotification('Failed to save phone book settings', 'error');
        }
    } catch (error: unknown) {
        console.error('Error saving phonebook settings:', error);
        showNotification('Failed to save phone book settings', 'error');
    }
}

export async function reloadTemplates(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/provisioning/reload-templates`, {
            method: 'POST',
            headers: getAuthHeaders(),
        });

        if (response.ok) {
            showNotification('Templates reloaded from disk', 'success');
            loadProvisioningTemplates();
        } else {
            showNotification('Failed to reload templates', 'error');
        }
    } catch (error: unknown) {
        console.error('Error reloading templates:', error);
        showNotification('Failed to reload templates', 'error');
    }
}

export function resetAddDeviceForm(): void {
    const form = document.getElementById('add-device-form') as HTMLFormElement | null;
    if (form) form.reset();

    const modelSelect = document.getElementById('device-model') as HTMLSelectElement | null;
    if (modelSelect) modelSelect.innerHTML = '<option value="">Select Vendor First</option>';
}

export function viewTemplate(name: string): void {
    showNotification(`Viewing template: ${name}`, 'info');
}

function initProvisioningForms(): void {
    const addForm = document.getElementById('add-device-form') as HTMLFormElement | null;
    if (addForm) {
        addForm.addEventListener('submit', async (e: Event) => {
            e.preventDefault();
            const val = (id: string): string => (document.getElementById(id) as HTMLInputElement)?.value ?? '';

            const data = {
                mac_address: val('device-mac'),
                extension_number: val('device-extension'),
                vendor: val('device-vendor'),
                model: val('device-model'),
            };

            if (!data.mac_address || !data.extension_number || !data.vendor || !data.model) {
                showNotification('Please fill in all required fields', 'error');
                return;
            }

            try {
                const API_BASE = getApiBaseUrl();
                const response = await fetch(`${API_BASE}/api/provisioning/devices`, {
                    method: 'POST',
                    headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
                    body: JSON.stringify(data),
                });
                const result = await response.json();
                if (response.ok && result.success) {
                    showNotification(result.message || 'Device added successfully', 'success');
                    resetAddDeviceForm();
                    loadProvisioningDevices();
                } else {
                    showNotification(result.error || 'Failed to add device', 'error');
                }
            } catch (err: unknown) {
                console.error('Error adding device:', err);
                showNotification('Failed to add device', 'error');
            }
        });
    }
}

// Backward compatibility
window.loadProvisioning = loadProvisioning;
window.loadSupportedVendors = loadSupportedVendors;
window.loadProvisioningDevices = loadProvisioningDevices;
window.loadProvisioningTemplates = loadProvisioningTemplates;
window.loadProvisioningSettings = loadProvisioningSettings;
window.loadPhonebookSettings = loadPhonebookSettings;
window.deleteDevice = deleteDevice;
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- legacy backward compat shim, overridden by admin.js at runtime
(window as any).viewTemplate = viewTemplate;
window.updateModelOptions = updateModelOptions;
window.toggleProvisioningEnabled = toggleProvisioningEnabled;
window.saveProvisioningSettings = saveProvisioningSettings;
window.toggleLdapPhonebookSettings = toggleLdapPhonebookSettings;
window.toggleRemotePhonebookSettings = toggleRemotePhonebookSettings;
window.savePhonebookSettings = savePhonebookSettings;
window.reloadTemplates = reloadTemplates;
window.resetAddDeviceForm = resetAddDeviceForm;

// Self-initialize form handlers once the DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initProvisioningForms);
} else {
    initProvisioningForms();
}
