/**
 * Registered phones page module.
 * Handles display of registered phones and ATAs.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.js';
import { showNotification } from '../ui/notifications.js';
import { escapeHtml } from '../utils/html.js';

interface RegisteredPhone {
    extension?: string;
    name?: string;
    ip_address?: string;
    user_agent?: string;
    registered_at?: string;
    status?: string;
}

interface RegisteredPhonesResponse {
    phones?: RegisteredPhone[];
}

interface RegisteredATA {
    mac_address?: string;
    model?: string;
    ip_address?: string;
    ports?: number;
    status?: string;
}

interface RegisteredATAsResponse {
    atas?: RegisteredATA[];
}

export async function loadRegisteredPhones(): Promise<void> {
    const tbody = document.getElementById('registered-phones-body') as HTMLElement | null;
    if (!tbody) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/registered-phones`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: RegisteredPhonesResponse = await response.json();
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
    } catch (error: unknown) {
        console.error('Error loading registered phones:', error);
        tbody.innerHTML = '<tr><td colspan="6">Error loading phones</td></tr>';
    }
}

export async function loadRegisteredATAs(): Promise<void> {
    const tbody = document.getElementById('registered-atas-body') as HTMLElement | null;
    if (!tbody) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/registered-phones/atas`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: RegisteredATAsResponse = await response.json();
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
    } catch (error: unknown) {
        console.error('Error loading ATAs:', error);
    }
}

// Backward compatibility
(window as any).loadRegisteredPhones = loadRegisteredPhones;
(window as any).loadRegisteredATAs = loadRegisteredATAs;
