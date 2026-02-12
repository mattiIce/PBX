/**
 * Registered phones page module.
 * Handles display of registered phones and ATAs.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.js';
import { showNotification } from '../ui/notifications.js';
import { escapeHtml } from '../utils/html.js';

export async function loadRegisteredPhones() {
    const tbody = document.getElementById('registered-phones-body');
    if (!tbody) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/registered-phones`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        const phones = data.phones || [];

        if (phones.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No registered phones</td></tr>';
            return;
        }

        tbody.innerHTML = phones.map(p => `
            <tr>
                <td>${escapeHtml(p.extension || '')}</td>
                <td>${escapeHtml(p.name || '')}</td>
                <td>${escapeHtml(p.ip_address || '')}</td>
                <td>${escapeHtml(p.user_agent || '')}</td>
                <td>${escapeHtml(p.registered_at || '')}</td>
                <td><span class="status-badge ${p.status === 'online' ? 'connected' : 'disconnected'}">${p.status || 'unknown'}</span></td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading registered phones:', error);
        tbody.innerHTML = '<tr><td colspan="6">Error loading phones</td></tr>';
    }
}

export async function loadRegisteredATAs() {
    const tbody = document.getElementById('registered-atas-body');
    if (!tbody) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/registered-phones/atas`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        const atas = data.atas || [];

        if (atas.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No registered ATAs</td></tr>';
            return;
        }

        tbody.innerHTML = atas.map(a => `
            <tr>
                <td>${escapeHtml(a.mac_address || '')}</td>
                <td>${escapeHtml(a.model || '')}</td>
                <td>${escapeHtml(a.ip_address || '')}</td>
                <td>${escapeHtml(a.ports?.toString() || '')}</td>
                <td><span class="status-badge ${a.status === 'online' ? 'connected' : 'disconnected'}">${a.status || 'unknown'}</span></td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading ATAs:', error);
    }
}

// Backward compatibility
window.loadRegisteredPhones = loadRegisteredPhones;
window.loadRegisteredATAs = loadRegisteredATAs;
