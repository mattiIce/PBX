/**
 * Emergency page module.
 * Handles emergency contacts, E911 sites, and location management.
 */

import { getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';
import { escapeHtml } from '../utils/html.ts';

interface EmergencyContact {
    id: string;
    name?: string;
    phone?: string;
    role?: string;
    priority?: string;
}

interface EmergencyContactsResponse {
    contacts?: EmergencyContact[];
}

interface HistoryEntry {
    timestamp: string;
    description?: string;
}

interface EmergencyHistoryResponse {
    history?: HistoryEntry[];
}

interface E911Site {
    id: string;
    name?: string;
    address?: string;
}

interface E911SitesResponse {
    sites?: E911Site[];
}

interface ExtensionLocation {
    extension: string;
    site_name?: string;
}

interface ExtensionLocationsResponse {
    locations?: ExtensionLocation[];
}

export async function loadEmergencyContacts(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/emergency/contacts`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: EmergencyContactsResponse = await response.json();

        const tbody = document.getElementById('emergency-contacts-table') as HTMLElement | null;
        if (!tbody) return;

        const contacts = data.contacts ?? [];
        if (contacts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No emergency contacts</td></tr>';
            return;
        }

        tbody.innerHTML = contacts.map(c => `
            <tr>
                <td>${escapeHtml(c.name || '')}</td>
                <td>${escapeHtml(c.phone || '')}</td>
                <td>${escapeHtml(c.role || '')}</td>
                <td>${getPriorityBadge(c.priority)}</td>
                <td><button class="btn btn-danger btn-sm" onclick="deleteEmergencyContact('${c.id}')">Delete</button></td>
            </tr>
        `).join('');
    } catch (error: unknown) {
        console.error('Error loading emergency contacts:', error);
    }
}

function getPriorityBadge(priority: string | undefined): string {
    const classes: Record<string, string> = { high: 'danger', medium: 'warning', low: 'info' };
    return `<span class="status-badge ${classes[priority ?? ''] ?? 'info'}">${priority ?? 'normal'}</span>`;
}

export async function loadEmergencyHistory(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/emergency/history`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data: EmergencyHistoryResponse = await response.json();

        const container = document.getElementById('emergency-history-table') as HTMLElement | null;
        if (!container) return;

        const history = data.history ?? [];
        container.innerHTML = history.length === 0
            ? '<div class="info-box">No emergency history</div>'
            : history.map(h => `
                <div class="history-item">
                    <strong>${new Date(h.timestamp).toLocaleString()}</strong> - ${escapeHtml(h.description || '')}
                </div>
            `).join('');
    } catch (error: unknown) {
        console.error('Error loading emergency history:', error);
    }
}

export async function deleteEmergencyContact(contactId: string): Promise<void> {
    if (!confirm('Delete this emergency contact?')) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/emergency/contacts/${contactId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (response.ok) {
            showNotification('Emergency contact deleted', 'success');
            loadEmergencyContacts();
        }
    } catch (error: unknown) {
        console.error('Error deleting contact:', error);
        showNotification('Failed to delete contact', 'error');
    }
}

export async function loadE911Sites(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/emergency/e911/sites`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data: E911SitesResponse = await response.json();

        const container = document.getElementById('e911-sites-table') as HTMLElement | null;
        if (!container) return;

        const sites = data.sites ?? [];
        container.innerHTML = sites.length === 0
            ? '<div class="info-box">No E911 sites configured</div>'
            : sites.map(s => `
                <div class="site-item">
                    <strong>${escapeHtml(s.name || '')}</strong> - ${escapeHtml(s.address || '')}
                    <button class="btn btn-sm btn-secondary" onclick="editE911Site('${s.id}')">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteE911Site('${s.id}')">Delete</button>
                </div>
            `).join('');
    } catch (error: unknown) {
        console.error('Error loading E911 sites:', error);
    }
}

export async function loadExtensionLocations(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/emergency/e911/locations`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data: ExtensionLocationsResponse = await response.json();

        const container = document.getElementById('extension-locations-table') as HTMLElement | null;
        if (container) {
            const locations = data.locations ?? [];
            container.innerHTML = locations.length === 0
                ? '<div class="info-box">No locations assigned</div>'
                : locations.map(l => `
                    <div class="location-item">
                        Extension ${escapeHtml(l.extension)} - ${escapeHtml(l.site_name || 'Unassigned')}
                    </div>
                `).join('');
        }
    } catch (error: unknown) {
        console.error('Error loading extension locations:', error);
    }
}

export function showAddEmergencyContactModal(): void {
    const modal = document.getElementById('add-emergency-contact-modal') as HTMLElement | null;
    if (modal) modal.classList.add('active');
}

export function closeAddEmergencyContactModal(): void {
    const modal = document.getElementById('add-emergency-contact-modal') as HTMLElement | null;
    if (modal) modal.classList.remove('active');
}

export function showTriggerEmergencyModal(): void {
    const modal = document.getElementById('trigger-emergency-modal') as HTMLElement | null;
    if (modal) modal.classList.add('active');
}

export function closeTriggerEmergencyModal(): void {
    const modal = document.getElementById('trigger-emergency-modal') as HTMLElement | null;
    if (modal) modal.classList.remove('active');
}

export async function addEmergencyContact(event: Event): Promise<void> {
    event.preventDefault();
    const val = (id: string): string => (document.getElementById(id) as HTMLInputElement)?.value ?? '';

    const data = {
        name: val('emergency-contact-name'),
        phone: val('emergency-contact-phone'),
        role: val('emergency-contact-role'),
        priority: val('emergency-contact-priority'),
    };

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/emergency/contacts`, {
            method: 'POST',
            headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (response.ok) {
            showNotification('Emergency contact added', 'success');
            closeAddEmergencyContactModal();
            loadEmergencyContacts();
        } else {
            showNotification('Failed to add emergency contact', 'error');
        }
    } catch (error: unknown) {
        console.error('Error adding emergency contact:', error);
        showNotification('Failed to add emergency contact', 'error');
    }
}

export async function triggerEmergency(event: Event): Promise<void> {
    event.preventDefault();
    const val = (id: string): string => (document.getElementById(id) as HTMLInputElement)?.value ?? '';

    const data = {
        message: val('emergency-message'),
        type: val('emergency-type'),
    };

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/emergency/trigger`, {
            method: 'POST',
            headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (response.ok) {
            showNotification('Emergency notification sent', 'success');
            closeTriggerEmergencyModal();
            loadEmergencyHistory();
        } else {
            showNotification('Failed to trigger emergency', 'error');
        }
    } catch (error: unknown) {
        console.error('Error triggering emergency:', error);
        showNotification('Failed to trigger emergency', 'error');
    }
}

export async function testEmergencyNotification(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/emergency/test`, {
            method: 'POST',
            headers: getAuthHeaders(),
        });
        if (response.ok) {
            showNotification('Test notification sent successfully', 'success');
        } else {
            showNotification('Failed to send test notification', 'error');
        }
    } catch (error: unknown) {
        console.error('Error testing emergency notification:', error);
        showNotification('Failed to send test notification', 'error');
    }
}

// Backward compatibility
window.loadEmergencyContacts = loadEmergencyContacts;
window.loadEmergencyHistory = loadEmergencyHistory;
window.deleteEmergencyContact = deleteEmergencyContact;
window.loadE911Sites = loadE911Sites;
window.loadExtensionLocations = loadExtensionLocations;
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- legacy backward compat
(window as any).showAddEmergencyContactModal = showAddEmergencyContactModal;
(window as any).closeAddEmergencyContactModal = closeAddEmergencyContactModal;
(window as any).showTriggerEmergencyModal = showTriggerEmergencyModal;
(window as any).closeTriggerEmergencyModal = closeTriggerEmergencyModal;
(window as any).addEmergencyContact = addEmergencyContact;
(window as any).triggerEmergency = triggerEmergency;
(window as any).testEmergencyNotification = testEmergencyNotification;
