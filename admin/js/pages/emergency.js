/**
 * Emergency page module.
 * Handles emergency contacts, E911 sites, and location management.
 */

import { getAuthHeaders, getApiBaseUrl } from '../api/client.js';
import { showNotification } from '../ui/notifications.js';
import { escapeHtml } from '../utils/html.js';

export async function loadEmergencyContacts() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/emergency/contacts`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        const tbody = document.getElementById('emergency-contacts-body');
        if (!tbody) return;

        const contacts = data.contacts || [];
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
    } catch (error) {
        console.error('Error loading emergency contacts:', error);
    }
}

function getPriorityBadge(priority) {
    const classes = { high: 'danger', medium: 'warning', low: 'info' };
    return `<span class="status-badge ${classes[priority] || 'info'}">${priority || 'normal'}</span>`;
}

export async function loadEmergencyHistory() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/emergency/history`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data = await response.json();

        const container = document.getElementById('emergency-history');
        if (!container) return;

        const history = data.history || [];
        container.innerHTML = history.length === 0
            ? '<div class="info-box">No emergency history</div>'
            : history.map(h => `
                <div class="history-item">
                    <strong>${new Date(h.timestamp).toLocaleString()}</strong> - ${escapeHtml(h.description || '')}
                </div>
            `).join('');
    } catch (error) {
        console.error('Error loading emergency history:', error);
    }
}

export async function deleteEmergencyContact(contactId) {
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
    } catch (error) {
        console.error('Error deleting contact:', error);
        showNotification('Failed to delete contact', 'error');
    }
}

export async function loadE911Sites() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/emergency/e911/sites`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data = await response.json();

        const container = document.getElementById('e911-sites-list');
        if (!container) return;

        const sites = data.sites || [];
        container.innerHTML = sites.length === 0
            ? '<div class="info-box">No E911 sites configured</div>'
            : sites.map(s => `
                <div class="site-item">
                    <strong>${escapeHtml(s.name || '')}</strong> - ${escapeHtml(s.address || '')}
                    <button class="btn btn-sm btn-secondary" onclick="editE911Site('${s.id}')">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteE911Site('${s.id}')">Delete</button>
                </div>
            `).join('');
    } catch (error) {
        console.error('Error loading E911 sites:', error);
    }
}

export async function loadExtensionLocations() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/emergency/e911/locations`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data = await response.json();

        const container = document.getElementById('extension-locations-list');
        if (container) {
            const locations = data.locations || [];
            container.innerHTML = locations.length === 0
                ? '<div class="info-box">No locations assigned</div>'
                : locations.map(l => `
                    <div class="location-item">
                        Extension ${escapeHtml(l.extension)} - ${escapeHtml(l.site_name || 'Unassigned')}
                    </div>
                `).join('');
        }
    } catch (error) {
        console.error('Error loading extension locations:', error);
    }
}

// Backward compatibility
window.loadEmergencyContacts = loadEmergencyContacts;
window.loadEmergencyHistory = loadEmergencyHistory;
window.deleteEmergencyContact = deleteEmergencyContact;
window.loadE911Sites = loadE911Sites;
window.loadExtensionLocations = loadExtensionLocations;
