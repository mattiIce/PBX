/**
 * Paging page module.
 * Handles paging zones, devices, and active pages.
 */

import { getAuthHeaders, getApiBaseUrl } from '../api/client.js';
import { showNotification } from '../ui/notifications.js';
import { escapeHtml } from '../utils/html.js';

export async function loadPagingData() {
    await Promise.all([loadPagingZones(), loadPagingDevices(), loadActivePages()]);
}

export async function loadPagingZones() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/paging/zones`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        const tbody = document.getElementById('paging-zones-body');
        if (!tbody) return;

        const zones = data.zones || [];
        if (zones.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4">No paging zones</td></tr>';
            return;
        }

        tbody.innerHTML = zones.map(z => `
            <tr>
                <td>${escapeHtml(z.name || '')}</td>
                <td>${escapeHtml(z.number || '')}</td>
                <td>${z.devices?.length || 0} devices</td>
                <td><button class="btn btn-danger btn-sm" onclick="deletePagingZone('${z.id}')">Delete</button></td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading paging zones:', error);
    }
}

export async function loadPagingDevices() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/paging/devices`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data = await response.json();

        const container = document.getElementById('paging-devices-list');
        if (container) {
            const devices = data.devices || [];
            container.innerHTML = devices.length === 0
                ? '<div class="info-box">No paging devices</div>'
                : devices.map(d => `<div class="device-item">${escapeHtml(d.name || d.id)}</div>`).join('');
        }
    } catch (error) {
        console.error('Error loading paging devices:', error);
    }
}

export async function loadActivePages() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/paging/active`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data = await response.json();

        const container = document.getElementById('active-pages');
        if (container) {
            const pages = data.pages || [];
            container.innerHTML = pages.length === 0
                ? '<div class="info-box">No active pages</div>'
                : pages.map(p => `<div class="page-item">${escapeHtml(p.zone)} - ${escapeHtml(p.initiator)}</div>`).join('');
        }
    } catch (error) {
        console.error('Error loading active pages:', error);
    }
}

export async function deletePagingZone(zoneId) {
    if (!confirm('Delete this paging zone?')) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/paging/zones/${zoneId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (response.ok) {
            showNotification('Paging zone deleted', 'success');
            loadPagingZones();
        }
    } catch (error) {
        console.error('Error deleting paging zone:', error);
        showNotification('Failed to delete zone', 'error');
    }
}

// Backward compatibility
window.loadPagingData = loadPagingData;
window.loadPagingZones = loadPagingZones;
window.loadPagingDevices = loadPagingDevices;
window.loadActivePages = loadActivePages;
window.deletePagingZone = deletePagingZone;
