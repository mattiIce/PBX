/**
 * Paging page module.
 * Handles paging zones, devices, and active pages.
 */

import { getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';
import { escapeHtml } from '../utils/html.ts';

interface PagingZone {
    id: string;
    name?: string;
    number?: string;
    devices?: string[];
}

interface PagingZonesResponse {
    zones?: PagingZone[];
}

interface PagingDevice {
    id: string;
    name?: string;
    type?: string;
    sip_address?: string;
    status?: string;
    device_id?: string;
}

interface ApiResponse {
    success?: boolean;
    message?: string;
}

interface PagingDevicesResponse {
    devices?: PagingDevice[];
}

interface ActivePage {
    zone: string;
    initiator: string;
}

interface ActivePagesResponse {
    pages?: ActivePage[];
}

export async function loadPagingData(): Promise<void> {
    await Promise.all([loadPagingZones(), loadPagingDevices(), loadActivePages()]);
}

export async function loadPagingZones(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/paging/zones`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: PagingZonesResponse = await response.json();

        const tbody = document.getElementById('paging-zones-body') as HTMLElement | null;
        if (!tbody) return;

        const zones = data.zones ?? [];
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
    } catch (error: unknown) {
        console.error('Error loading paging zones:', error);
    }
}

export async function loadPagingDevices(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/paging/devices`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data: PagingDevicesResponse = await response.json();

        const container = document.getElementById('paging-devices-list') as HTMLElement | null;
        if (container) {
            const devices = data.devices ?? [];
            container.innerHTML = devices.length === 0
                ? '<div class="info-box">No paging devices</div>'
                : devices.map(d => `<div class="device-item">${escapeHtml(d.name || d.id)}</div>`).join('');
        }
    } catch (error: unknown) {
        console.error('Error loading paging devices:', error);
    }
}

export async function loadActivePages(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/paging/active`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data: ActivePagesResponse = await response.json();

        const container = document.getElementById('active-pages') as HTMLElement | null;
        if (container) {
            const pages = data.pages ?? [];
            container.innerHTML = pages.length === 0
                ? '<div class="info-box">No active pages</div>'
                : pages.map(p => `<div class="page-item">${escapeHtml(p.zone)} - ${escapeHtml(p.initiator)}</div>`).join('');
        }
    } catch (error: unknown) {
        console.error('Error loading active pages:', error);
    }
}

export async function deletePagingZone(zoneId: string): Promise<void> {
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
    } catch (error: unknown) {
        console.error('Error deleting paging zone:', error);
        showNotification('Failed to delete zone', 'error');
    }
}

export async function showAddZoneModal(): Promise<void> {
    const extension = prompt('Zone Extension (e.g., 701):');
    if (!extension) return;

    const name = prompt('Zone Name (e.g., "Warehouse"):');
    if (!name) return;

    const description = prompt('Description (optional):') ?? '';
    const deviceId = prompt('Device ID (optional):') ?? '';

    const zoneData = {
        extension: extension,
        name: name,
        description: description,
        device_id: deviceId
    };

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/paging/zones`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(zoneData)
        });
        const data: ApiResponse = await response.json();
        if (data.success) {
            showNotification(`Zone ${name} added successfully`, 'success');
            loadPagingZones();
        } else {
            showNotification(data.message ?? 'Failed to add zone', 'error');
        }
    } catch (error: unknown) {
        console.error('Error adding zone:', error);
        showNotification('Error adding zone', 'error');
    }
}

export async function showAddDeviceModal(): Promise<void> {
    const deviceId = prompt('Device ID (e.g., "dac-1"):');
    if (!deviceId) return;

    const name = prompt('Device Name (e.g., "Main PA System"):');
    if (!name) return;

    const type = prompt('Device Type (e.g., "sip_gateway"):') ?? 'sip_gateway';
    const sipAddress = prompt('SIP Address (e.g., "paging@192.168.1.10:5060"):') ?? '';

    const deviceData = {
        device_id: deviceId,
        name: name,
        type: type,
        sip_address: sipAddress
    };

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/paging/devices`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(deviceData)
        });
        const data: ApiResponse = await response.json();
        if (data.success) {
            showNotification(`Device ${name} added successfully`, 'success');
            loadPagingDevices();
        } else {
            showNotification(data.message ?? 'Failed to add device', 'error');
        }
    } catch (error: unknown) {
        console.error('Error adding device:', error);
        showNotification('Error adding device', 'error');
    }
}

export async function deletePagingDevice(deviceId: string): Promise<void> {
    if (!confirm(`Delete paging device ${deviceId}?`)) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/paging/devices/${deviceId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        const data: ApiResponse = await response.json();
        if (data.success) {
            showNotification(`Device ${deviceId} deleted`, 'success');
            loadPagingDevices();
        } else {
            showNotification(data.message ?? 'Failed to delete device', 'error');
        }
    } catch (error: unknown) {
        console.error('Error deleting device:', error);
        showNotification('Error deleting device', 'error');
    }
}

// Backward compatibility
window.loadPagingData = loadPagingData;
window.loadPagingZones = loadPagingZones;
window.loadPagingDevices = loadPagingDevices;
window.loadActivePages = loadActivePages;
window.deletePagingZone = deletePagingZone;
window.showAddZoneModal = showAddZoneModal;
window.showAddDeviceModal = showAddDeviceModal;
window.deletePagingDevice = deletePagingDevice;
