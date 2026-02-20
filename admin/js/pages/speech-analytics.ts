/**
 * Speech Analytics and Nomadic E911 page module.
 * Handles E911 sites/locations, location history, and speech analytics
 * configuration modals with full backend API integration.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';
import { escapeHtml } from '../utils/html.ts';

// --- Interfaces ---

interface E911Site {
    id: number;
    site_name: string;
    address: string;
    city: string;
    state: string;
    postal_code: string;
    ip_ranges?: string;
    ip_range_start?: string;
    ip_range_end?: string;
    psap?: string;
    emergency_trunk?: string;
    elin?: string;
    country?: string;
    building?: string;
    floor?: string;
}

interface E911SitesResponse {
    sites?: E911Site[];
}

interface ExtensionLocation {
    extension: string;
    site_name?: string;
    address?: string;
    detection_method?: string;
    last_updated?: string;
}

interface ExtensionLocationsResponse {
    locations?: ExtensionLocation[];
}

interface LocationHistoryEntry {
    timestamp: string;
    extension: string;
    site_name?: string;
    detection_method?: string;
    ip_address?: string;
}

interface LocationHistoryResponse {
    history?: LocationHistoryEntry[];
}

interface SpeechAnalyticsConfig {
    enabled?: boolean;
    transcription_enabled?: boolean;
    sentiment_enabled?: boolean;
    summarization_enabled?: boolean;
    keywords?: string;
    alert_threshold?: number;
}

// --- E911 Sites ---

export async function loadE911Sites(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/framework/nomadic-e911/sites`,
            { headers: getAuthHeaders() }
        );
        const data: E911SitesResponse = await response.json();
        const tableBody = document.getElementById('e911-sites-table') as HTMLElement | null;
        if (!tableBody) return;

        if (!data.sites || data.sites.length === 0) {
            tableBody.innerHTML =
                '<tr><td colspan="5" class="loading">No E911 sites configured</td></tr>';
            return;
        }

        tableBody.innerHTML = data.sites.map((site: E911Site) => `
            <tr>
                <td>${escapeHtml(site.site_name)}</td>
                <td>${escapeHtml(site.address)}, ${escapeHtml(site.city)}, ${escapeHtml(site.state)} ${escapeHtml(site.postal_code)}</td>
                <td>${escapeHtml(site.ip_ranges ?? 'N/A')}</td>
                <td>${escapeHtml(site.psap ?? 'Default')}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editE911Site(${site.id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteE911Site(${site.id})">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error: unknown) {
        console.error('Error loading E911 sites:', error);
        showNotification('Error loading E911 sites', 'error');
    }
}

export async function loadExtensionLocations(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/framework/nomadic-e911/locations`,
            { headers: getAuthHeaders() }
        );
        const data: ExtensionLocationsResponse = await response.json();
        const tableBody = document.getElementById('extension-locations-table') as HTMLElement | null;
        if (!tableBody) return;

        if (!data.locations || data.locations.length === 0) {
            tableBody.innerHTML =
                '<tr><td colspan="5" class="loading">No location data available</td></tr>';
            return;
        }

        tableBody.innerHTML = data.locations.map((loc: ExtensionLocation) => `
            <tr>
                <td>${escapeHtml(loc.extension)}</td>
                <td>${escapeHtml(loc.site_name ?? 'Unknown')} - ${escapeHtml(loc.address ?? 'N/A')}</td>
                <td>${escapeHtml(loc.detection_method ?? 'N/A')}</td>
                <td>${loc.last_updated ? new Date(loc.last_updated).toLocaleString() : 'N/A'}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="updateExtensionLocation('${escapeHtml(loc.extension)}')">Update</button>
                </td>
            </tr>
        `).join('');
    } catch (error: unknown) {
        console.error('Error loading extension locations:', error);
        showNotification('Error loading extension locations', 'error');
    }
}

export async function loadLocationHistory(): Promise<void> {
    const extensionInput = document.getElementById('location-history-extension') as HTMLInputElement | null;
    const extension = extensionInput?.value ?? '';
    const url = extension
        ? `/api/framework/nomadic-e911/history/${extension}`
        : '/api/framework/nomadic-e911/history';

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}${url}`, {
            headers: getAuthHeaders()
        });
        const data: LocationHistoryResponse = await response.json();
        const tableBody = document.getElementById('location-history-table') as HTMLElement | null;
        if (!tableBody) return;

        if (!data.history || data.history.length === 0) {
            tableBody.innerHTML =
                '<tr><td colspan="5" class="loading">No location history available</td></tr>';
            return;
        }

        tableBody.innerHTML = data.history.map((entry: LocationHistoryEntry) => `
            <tr>
                <td>${escapeHtml(new Date(entry.timestamp).toLocaleString())}</td>
                <td>${escapeHtml(entry.extension)}</td>
                <td>${escapeHtml(entry.site_name ?? 'N/A')}</td>
                <td>${escapeHtml(entry.detection_method ?? 'N/A')}</td>
                <td>${escapeHtml(entry.ip_address ?? 'N/A')}</td>
            </tr>
        `).join('');
    } catch (error: unknown) {
        console.error('Error loading location history:', error);
        showNotification('Error loading location history', 'error');
    }
}

// --- E911 Site Modals ---

function removeE911SiteModal(): void {
    const modal = document.getElementById('e911-site-modal');
    if (modal) modal.remove();
}

function buildE911SiteForm(site?: E911Site): string {
    return `
        <div id="e911-site-modal" class="modal" style="display: flex; align-items: center;
             justify-content: center;">
            <div class="modal-content" style="max-width: 600px;">
                <div class="modal-header">
                    <h3>${site ? 'Edit' : 'Add'} E911 Site</h3>
                    <span class="close" onclick="removeE911SiteModal()">&times;</span>
                </div>
                <form id="e911-site-form">
                    ${site ? `<input type="hidden" name="site_id" value="${site.id}">` : ''}
                    <div class="form-group">
                        <label>Site Name:</label>
                        <input type="text" name="site_name" required class="form-control"
                            value="${escapeHtml(site?.site_name ?? '')}">
                    </div>
                    <div class="form-group">
                        <label>Street Address:</label>
                        <input type="text" name="street_address" class="form-control"
                            value="${escapeHtml(site?.address ?? '')}">
                    </div>
                    <div class="form-group">
                        <label>City:</label>
                        <input type="text" name="city" class="form-control"
                            value="${escapeHtml(site?.city ?? '')}">
                    </div>
                    <div class="form-group">
                        <label>State:</label>
                        <input type="text" name="state" class="form-control"
                            value="${escapeHtml(site?.state ?? '')}">
                    </div>
                    <div class="form-group">
                        <label>Postal Code:</label>
                        <input type="text" name="postal_code" class="form-control"
                            value="${escapeHtml(site?.postal_code ?? '')}">
                    </div>
                    <div class="form-group">
                        <label>Country:</label>
                        <input type="text" name="country" class="form-control"
                            value="${escapeHtml(site?.country ?? 'USA')}" placeholder="USA">
                    </div>
                    <div class="form-group">
                        <label>IP Range Start:</label>
                        <input type="text" name="ip_range_start" required class="form-control"
                            value="${escapeHtml(site?.ip_range_start ?? '')}"
                            placeholder="192.168.1.0">
                    </div>
                    <div class="form-group">
                        <label>IP Range End:</label>
                        <input type="text" name="ip_range_end" required class="form-control"
                            value="${escapeHtml(site?.ip_range_end ?? '')}"
                            placeholder="192.168.1.255">
                    </div>
                    <div class="form-group">
                        <label>Emergency Trunk:</label>
                        <input type="text" name="emergency_trunk" class="form-control"
                            value="${escapeHtml(site?.emergency_trunk ?? '')}">
                    </div>
                    <div class="form-group">
                        <label>PSAP Number:</label>
                        <input type="text" name="psap_number" class="form-control"
                            value="${escapeHtml(site?.psap ?? '')}"
                            placeholder="Default PSAP">
                    </div>
                    <div class="form-group">
                        <label>ELIN:</label>
                        <input type="text" name="elin" class="form-control"
                            value="${escapeHtml(site?.elin ?? '')}">
                        <small>Emergency Location Information Number</small>
                    </div>
                    <div class="form-group">
                        <label>Building:</label>
                        <input type="text" name="building" class="form-control"
                            value="${escapeHtml(site?.building ?? '')}">
                    </div>
                    <div class="form-group">
                        <label>Floor:</label>
                        <input type="text" name="floor" class="form-control"
                            value="${escapeHtml(site?.floor ?? '')}">
                    </div>
                    <div class="modal-actions">
                        <button type="submit" class="btn btn-primary">
                            ${site ? 'Update' : 'Create'} Site
                        </button>
                        <button type="button" class="btn btn-secondary"
                            onclick="removeE911SiteModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `;
}

async function submitE911Site(form: HTMLFormElement): Promise<void> {
    const formData = new FormData(form);
    const body: Record<string, string> = {};
    for (const [key, value] of formData.entries()) {
        if (key !== 'site_id' && String(value).trim()) {
            body[key] = String(value).trim();
        }
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/framework/nomadic-e911/create-site`,
            {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(body),
            }
        );
        const data = await response.json() as { success?: boolean; error?: string };
        if (data.success) {
            showNotification('E911 site saved successfully', 'success');
            removeE911SiteModal();
            await loadE911Sites();
        } else {
            showNotification(data.error ?? 'Error saving E911 site', 'error');
        }
    } catch (error: unknown) {
        console.error('Error saving E911 site:', error);
        showNotification('Error saving E911 site', 'error');
    }
}

export function showAddE911SiteModal(): void {
    removeE911SiteModal();
    document.body.insertAdjacentHTML('beforeend', buildE911SiteForm());
    const form = document.getElementById('e911-site-form') as HTMLFormElement;
    form.onsubmit = (e: Event) => {
        e.preventDefault();
        void submitE911Site(form);
    };
}

export function editE911Site(siteId: number): void {
    const API_BASE = getApiBaseUrl();
    void fetchWithTimeout(`${API_BASE}/api/framework/nomadic-e911/sites`, {
        headers: getAuthHeaders(),
    }).then(async (response) => {
        const data: E911SitesResponse = await response.json();
        const site = data.sites?.find((s) => s.id === siteId);
        if (!site) {
            showNotification('Site not found', 'error');
            return;
        }
        removeE911SiteModal();
        document.body.insertAdjacentHTML('beforeend', buildE911SiteForm(site));
        const form = document.getElementById('e911-site-form') as HTMLFormElement;
        form.onsubmit = (e: Event) => {
            e.preventDefault();
            void submitE911Site(form);
        };
    }).catch(() => {
        showNotification('Error loading site details', 'error');
    });
}

export async function deleteE911Site(siteId: number): Promise<void> {
    if (!confirm(`Delete E911 site ${siteId}?`)) {
        return;
    }
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/framework/nomadic-e911/sites/${siteId}`,
            { method: 'DELETE', headers: getAuthHeaders() }
        );
        const data = await response.json() as { success?: boolean; error?: string };
        if (data.success) {
            showNotification('E911 site deleted', 'success');
            await loadE911Sites();
        } else {
            showNotification(data.error ?? 'Error deleting site', 'error');
        }
    } catch (error: unknown) {
        console.error('Error deleting E911 site:', error);
        showNotification('Error deleting E911 site', 'error');
    }
}

// --- Location Update Modals ---

function removeLocationModal(): void {
    const modal = document.getElementById('location-update-modal');
    if (modal) modal.remove();
}

function buildLocationForm(extension?: string): string {
    return `
        <div id="location-update-modal" class="modal" style="display: flex;
             align-items: center; justify-content: center;">
            <div class="modal-content" style="max-width: 600px;">
                <div class="modal-header">
                    <h3>Update Extension Location</h3>
                    <span class="close" onclick="removeLocationModal()">&times;</span>
                </div>
                <form id="location-update-form">
                    <div class="form-group">
                        <label>Extension:</label>
                        <input type="text" name="extension" required class="form-control"
                            value="${escapeHtml(extension ?? '')}"
                            ${extension ? 'readonly' : ''}>
                    </div>
                    <div class="form-group">
                        <label>Location Name:</label>
                        <input type="text" name="location_name" class="form-control"
                            placeholder="Main Office">
                    </div>
                    <div class="form-group">
                        <label>IP Address:</label>
                        <input type="text" name="ip_address" class="form-control"
                            placeholder="192.168.1.100">
                    </div>
                    <div class="form-group">
                        <label>Street Address:</label>
                        <input type="text" name="street_address" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>City:</label>
                        <input type="text" name="city" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>State:</label>
                        <input type="text" name="state" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>Postal Code:</label>
                        <input type="text" name="postal_code" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>Country:</label>
                        <input type="text" name="country" class="form-control"
                            placeholder="USA">
                    </div>
                    <div class="form-group">
                        <label>Building:</label>
                        <input type="text" name="building" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>Floor:</label>
                        <input type="text" name="floor" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>Room:</label>
                        <input type="text" name="room" class="form-control">
                    </div>
                    <div class="modal-actions">
                        <button type="submit" class="btn btn-primary">Update Location</button>
                        <button type="button" class="btn btn-secondary"
                            onclick="removeLocationModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `;
}

async function submitLocationUpdate(form: HTMLFormElement): Promise<void> {
    const formData = new FormData(form);
    const ext = String(formData.get('extension') ?? '').trim();
    if (!ext) {
        showNotification('Extension is required', 'error');
        return;
    }

    const body: Record<string, string> = {};
    for (const [key, value] of formData.entries()) {
        if (key !== 'extension' && String(value).trim()) {
            body[key] = String(value).trim();
        }
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/framework/nomadic-e911/update-location/${encodeURIComponent(ext)}`,
            {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(body),
            }
        );
        const data = await response.json() as { success?: boolean; error?: string };
        if (data.success) {
            showNotification(`Location updated for extension ${ext}`, 'success');
            removeLocationModal();
            await loadExtensionLocations();
        } else {
            showNotification(data.error ?? 'Error updating location', 'error');
        }
    } catch (error: unknown) {
        console.error('Error updating location:', error);
        showNotification('Error updating location', 'error');
    }
}

export function showUpdateLocationModal(): void {
    removeLocationModal();
    document.body.insertAdjacentHTML('beforeend', buildLocationForm());
    const form = document.getElementById('location-update-form') as HTMLFormElement;
    form.onsubmit = (e: Event) => {
        e.preventDefault();
        void submitLocationUpdate(form);
    };
}

export function updateExtensionLocation(extension: string): void {
    removeLocationModal();
    document.body.insertAdjacentHTML('beforeend', buildLocationForm(extension));
    const form = document.getElementById('location-update-form') as HTMLFormElement;
    form.onsubmit = (e: Event) => {
        e.preventDefault();
        void submitLocationUpdate(form);
    };
}

// --- Speech Analytics Config Modals ---

function removeSpeechConfigModal(): void {
    const modal = document.getElementById('speech-config-modal');
    if (modal) modal.remove();
}

function buildSpeechConfigForm(extension?: string, config?: SpeechAnalyticsConfig): string {
    return `
        <div id="speech-config-modal" class="modal" style="display: flex;
             align-items: center; justify-content: center;">
            <div class="modal-content" style="max-width: 600px;">
                <div class="modal-header">
                    <h3>${config ? 'Edit' : 'Add'} Speech Analytics Config</h3>
                    <span class="close" onclick="removeSpeechConfigModal()">&times;</span>
                </div>
                <form id="speech-config-form">
                    <div class="form-group">
                        <label>Extension:</label>
                        <input type="text" name="extension" required class="form-control"
                            value="${escapeHtml(extension ?? '')}"
                            ${extension ? 'readonly' : ''}>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="enabled"
                                ${config?.enabled !== false ? 'checked' : ''}>
                            Enabled
                        </label>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="transcription_enabled"
                                ${config?.transcription_enabled !== false ? 'checked' : ''}>
                            Transcription
                        </label>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="sentiment_enabled"
                                ${config?.sentiment_enabled !== false ? 'checked' : ''}>
                            Sentiment Analysis
                        </label>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="summarization_enabled"
                                ${config?.summarization_enabled !== false ? 'checked' : ''}>
                            Call Summarization
                        </label>
                    </div>
                    <div class="form-group">
                        <label>Keywords (comma-separated):</label>
                        <input type="text" name="keywords" class="form-control"
                            value="${escapeHtml(config?.keywords ?? '')}"
                            placeholder="urgent, escalation, complaint">
                    </div>
                    <div class="form-group">
                        <label>Alert Threshold (0.0 - 1.0):</label>
                        <input type="number" name="alert_threshold" class="form-control"
                            value="${config?.alert_threshold ?? 0.7}"
                            min="0" max="1" step="0.1">
                    </div>
                    <div class="modal-actions">
                        <button type="submit" class="btn btn-primary">
                            ${config ? 'Update' : 'Create'} Config
                        </button>
                        <button type="button" class="btn btn-secondary"
                            onclick="removeSpeechConfigModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `;
}

async function submitSpeechConfig(form: HTMLFormElement): Promise<void> {
    const formData = new FormData(form);
    const ext = String(formData.get('extension') ?? '').trim();
    if (!ext) {
        showNotification('Extension is required', 'error');
        return;
    }

    const body = {
        enabled: formData.get('enabled') === 'on',
        transcription_enabled: formData.get('transcription_enabled') === 'on',
        sentiment_enabled: formData.get('sentiment_enabled') === 'on',
        summarization_enabled: formData.get('summarization_enabled') === 'on',
        keywords: String(formData.get('keywords') ?? '').trim(),
        alert_threshold: parseFloat(String(formData.get('alert_threshold') ?? '0.7')),
    };

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/framework/speech-analytics/config/${encodeURIComponent(ext)}`,
            {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(body),
            }
        );
        const data = await response.json() as { success?: boolean; error?: string };
        if (data.success) {
            showNotification('Speech analytics config saved', 'success');
            removeSpeechConfigModal();
        } else {
            showNotification(data.error ?? 'Error saving config', 'error');
        }
    } catch (error: unknown) {
        console.error('Error saving speech analytics config:', error);
        showNotification('Error saving speech analytics config', 'error');
    }
}

export function showAddSpeechAnalyticsConfigModal(): void {
    removeSpeechConfigModal();
    document.body.insertAdjacentHTML('beforeend', buildSpeechConfigForm());
    const form = document.getElementById('speech-config-form') as HTMLFormElement;
    form.onsubmit = (e: Event) => {
        e.preventDefault();
        void submitSpeechConfig(form);
    };
}

export function editSpeechAnalyticsConfig(extension: string): void {
    removeSpeechConfigModal();
    document.body.insertAdjacentHTML(
        'beforeend',
        buildSpeechConfigForm(extension)
    );
    const form = document.getElementById('speech-config-form') as HTMLFormElement;
    form.onsubmit = (e: Event) => {
        e.preventDefault();
        void submitSpeechConfig(form);
    };
}

export async function deleteSpeechAnalyticsConfig(extension: string): Promise<void> {
    if (!confirm(`Delete speech analytics config for extension ${extension}?`)) {
        return;
    }
    try {
        const API_BASE = getApiBaseUrl();
        const url = `${API_BASE}/api/framework/speech-analytics/config/${encodeURIComponent(extension)}`;
        const response = await fetchWithTimeout(url, {
            method: 'DELETE',
            headers: getAuthHeaders(),
        });
        const data = await response.json() as { success?: boolean; error?: string };
        if (data.success) {
            showNotification('Speech analytics config deleted', 'success');
        } else {
            showNotification(data.error ?? 'Error deleting config', 'error');
        }
    } catch (error: unknown) {
        console.error('Error deleting speech analytics config:', error);
        showNotification('Error deleting speech analytics config', 'error');
    }
}

// Backward compatibility
window.loadE911Sites = loadE911Sites;
window.loadExtensionLocations = loadExtensionLocations;
window.loadLocationHistory = loadLocationHistory;
window.showAddE911SiteModal = showAddE911SiteModal;
window.editE911Site = editE911Site;
window.deleteE911Site = deleteE911Site;
window.removeE911SiteModal = removeE911SiteModal;
window.showUpdateLocationModal = showUpdateLocationModal;
window.updateExtensionLocation = updateExtensionLocation;
window.removeLocationModal = removeLocationModal;
window.showAddSpeechAnalyticsConfigModal = showAddSpeechAnalyticsConfigModal;
window.editSpeechAnalyticsConfig = editSpeechAnalyticsConfig;
window.deleteSpeechAnalyticsConfig = deleteSpeechAnalyticsConfig;
window.removeSpeechConfigModal = removeSpeechConfigModal;
