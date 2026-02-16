/**
 * Speech Analytics and Nomadic E911 page module.
 * Handles E911 sites/locations, location history, and speech analytics
 * configuration modal placeholders.
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
    psap?: string;
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

// --- E911 Site Modal Placeholders ---

export function showAddE911SiteModal(): void {
    // Coming soon
    showNotification('Add E911 site modal coming soon', 'info');
}

export function editE911Site(siteId: number): void {
    // Coming soon
    showNotification(`Edit E911 site ${siteId} coming soon`, 'info');
}

export function deleteE911Site(siteId: number): void {
    if (!confirm(`Delete E911 site ${siteId}?`)) {
        return;
    }
    // Coming soon
    showNotification(`Delete E911 site ${siteId} coming soon`, 'info');
}

export function showUpdateLocationModal(): void {
    // Coming soon
    showNotification('Update location modal coming soon', 'info');
}

export function updateExtensionLocation(extension: string): void {
    // Coming soon
    showNotification(`Update location for extension ${extension} coming soon`, 'info');
}

// --- Speech Analytics Config Modal Placeholders ---

export function showAddSpeechAnalyticsConfigModal(): void {
    // Coming soon
    showNotification('Add speech analytics config modal coming soon', 'info');
}

export function editSpeechAnalyticsConfig(extension: string): void {
    // Coming soon
    showNotification(`Edit speech analytics config for ${extension} coming soon`, 'info');
}

export function deleteSpeechAnalyticsConfig(extension: string): void {
    if (!confirm(`Delete speech analytics config for extension ${extension}?`)) {
        return;
    }
    // Coming soon
    showNotification(`Delete speech analytics config for ${extension} coming soon`, 'info');
}

// Backward compatibility
window.loadE911Sites = loadE911Sites;
window.loadExtensionLocations = loadExtensionLocations;
window.loadLocationHistory = loadLocationHistory;
window.showAddE911SiteModal = showAddE911SiteModal;
window.editE911Site = editE911Site;
window.deleteE911Site = deleteE911Site;
window.showUpdateLocationModal = showUpdateLocationModal;
window.updateExtensionLocation = updateExtensionLocation;
window.showAddSpeechAnalyticsConfigModal = showAddSpeechAnalyticsConfigModal;
window.editSpeechAnalyticsConfig = editSpeechAnalyticsConfig;
window.deleteSpeechAnalyticsConfig = deleteSpeechAnalyticsConfig;
