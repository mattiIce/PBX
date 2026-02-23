/**
 * Registered phones page module.
 * Handles display of registered phones and ATAs.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';
import { escapeHtml } from '../utils/html.ts';

interface RegisteredPhone {
    extension_number?: string;
    ip_address?: string;
    mac_address?: string;
    user_agent?: string;
    last_registered?: string;
}

interface RegisteredATA {
    extension_number?: string;
    ip_address?: string;
    mac_address?: string;
    vendor?: string;
    model?: string;
    user_agent?: string;
    last_registered?: string;
}

export async function loadRegisteredPhones(): Promise<void> {
    const tbody = document.getElementById('registered-phones-table-body') as HTMLElement | null;
    if (!tbody) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/registered-phones`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const phones: RegisteredPhone[] = await response.json();

        if (phones.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No registered phones</td></tr>';
            return;
        }

        tbody.innerHTML = phones.map(p => `
            <tr>
                <td>${escapeHtml(p.extension_number || '')}</td>
                <td>${escapeHtml(p.ip_address || '')}</td>
                <td>${escapeHtml(p.mac_address || '')}</td>
                <td>${escapeHtml(p.user_agent || '')}</td>
                <td>${escapeHtml(p.last_registered || '')}</td>
            </tr>
        `).join('');
    } catch (error: unknown) {
        console.error('Error loading registered phones:', error);
        tbody.innerHTML = '<tr><td colspan="5">Error loading phones</td></tr>';
    }
}

export async function loadRegisteredATAs(): Promise<void> {
    const tbody = document.getElementById('registered-atas-table-body') as HTMLElement | null;
    if (!tbody) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/registered-phones/atas`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const atas: RegisteredATA[] = await response.json();

        if (atas.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No registered ATAs</td></tr>';
            return;
        }

        tbody.innerHTML = atas.map(a => {
            const vendorModel = [a.vendor, a.model].filter(Boolean).join(' ');
            return `
            <tr>
                <td>${escapeHtml(a.extension_number || '')}</td>
                <td>${escapeHtml(a.ip_address || '')}</td>
                <td>${escapeHtml(a.mac_address || '')}</td>
                <td>${escapeHtml(vendorModel)}</td>
                <td>${escapeHtml(a.user_agent || '')}</td>
                <td>${escapeHtml(a.last_registered || '')}</td>
            </tr>
        `}).join('');
    } catch (error: unknown) {
        console.error('Error loading ATAs:', error);
        tbody.innerHTML = '<tr><td colspan="6">Error loading ATAs</td></tr>';
    }
}

// Backward compatibility
window.loadRegisteredPhones = loadRegisteredPhones;
window.loadRegisteredATAs = loadRegisteredATAs;
