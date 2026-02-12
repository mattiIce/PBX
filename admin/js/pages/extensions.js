/**
 * Extensions page module.
 * Handles extension CRUD, reboot, and form management.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.js';
import { showNotification } from '../ui/notifications.js';
import { escapeHtml } from '../utils/html.js';

const EXTENSION_LOAD_TIMEOUT = 10000;

export async function loadExtensions() {
    const tbody = document.getElementById('extensions-table-body');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="7" class="loading">Loading extensions...</td></tr>';

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/extensions`, {
            headers: getAuthHeaders()
        }, EXTENSION_LOAD_TIMEOUT);

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const extensions = await response.json();
        window.currentExtensions = extensions;

        if (extensions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="loading">No extensions found.</td></tr>';
            return;
        }

        const generateBadges = (ext) => {
            let badges = '';
            if (ext.ad_synced) badges += ' <span class="ad-badge" title="Synced from Active Directory">AD</span>';
            if (ext.is_admin) badges += ' <span class="admin-badge" title="Admin Privileges">Admin</span>';
            return badges;
        };

        tbody.innerHTML = extensions.map(ext => `
            <tr>
                <td><strong>${escapeHtml(ext.number)}</strong>${generateBadges(ext)}</td>
                <td>${escapeHtml(ext.name)}</td>
                <td>${ext.email ? escapeHtml(ext.email) : 'Not set'}</td>
                <td class="${ext.registered ? 'status-online' : 'status-offline'}">
                    ${ext.registered ? 'Online' : 'Offline'}
                </td>
                <td>${ext.allow_external ? 'Yes' : 'No'}</td>
                <td>${ext.voicemail_pin_hash ? 'Set' : 'Not Set'}</td>
                <td>
                    <button class="btn btn-primary" onclick="editExtension('${escapeHtml(ext.number)}')">Edit</button>
                    ${ext.registered ? `<button class="btn btn-secondary" onclick="rebootPhone('${escapeHtml(ext.number)}')">Reboot</button>` : ''}
                    <button class="btn btn-danger" onclick="deleteExtension('${escapeHtml(ext.number)}')">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading extensions:', error);
        const errorMsg = error.message === 'Request timed out'
            ? 'Request timed out. System may still be starting.'
            : 'Error loading extensions';
        tbody.innerHTML = `<tr><td colspan="7" class="loading">${errorMsg}</td></tr>`;
    }
}

export function showAddExtensionModal() {
    const modal = document.getElementById('add-extension-modal');
    if (modal) modal.classList.add('active');
    const form = document.getElementById('add-extension-form');
    if (form) form.reset();
}

export function closeAddExtensionModal() {
    const modal = document.getElementById('add-extension-modal');
    if (modal) modal.classList.remove('active');
}

export function editExtension(number) {
    const ext = (window.currentExtensions || []).find(e => e.number === number);
    if (!ext) return;

    const el = (id) => document.getElementById(id);
    if (el('edit-ext-number')) el('edit-ext-number').value = ext.number;
    if (el('edit-ext-name')) el('edit-ext-name').value = ext.name;
    if (el('edit-ext-email')) el('edit-ext-email').value = ext.email || '';
    if (el('edit-ext-allow-external')) el('edit-ext-allow-external').checked = Boolean(ext.allow_external);
    if (el('edit-ext-is-admin')) el('edit-ext-is-admin').checked = Boolean(ext.is_admin);
    if (el('edit-ext-password')) el('edit-ext-password').value = '';

    const modal = document.getElementById('edit-extension-modal');
    if (modal) modal.classList.add('active');
}

export function closeEditExtensionModal() {
    const modal = document.getElementById('edit-extension-modal');
    if (modal) modal.classList.remove('active');
}

export async function deleteExtension(number) {
    if (!confirm(`Are you sure you want to delete extension ${number}?`)) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/extensions/${number}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (response.ok) {
            showNotification('Extension deleted successfully', 'success');
            loadExtensions();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to delete extension', 'error');
        }
    } catch (error) {
        console.error('Error deleting extension:', error);
        showNotification('Failed to delete extension', 'error');
    }
}

export async function rebootPhone(extension) {
    if (!confirm(`Reboot phone for extension ${extension}?`)) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/phones/reboot/${extension}`, {
            method: 'POST',
            headers: getAuthHeaders()
        });

        if (response.ok) {
            showNotification(`Reboot command sent to ${extension}`, 'success');
        } else {
            showNotification('Failed to reboot phone', 'error');
        }
    } catch (error) {
        console.error('Error rebooting phone:', error);
        showNotification('Failed to reboot phone', 'error');
    }
}

export async function rebootAllPhones() {
    if (!confirm('Reboot ALL registered phones?')) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/phones/reboot-all`, {
            method: 'POST',
            headers: getAuthHeaders()
        });

        if (response.ok) {
            showNotification('Reboot command sent to all phones', 'success');
        } else {
            showNotification('Failed to reboot phones', 'error');
        }
    } catch (error) {
        console.error('Error rebooting all phones:', error);
        showNotification('Failed to reboot phones', 'error');
    }
}

// Backward compatibility
window.loadExtensions = loadExtensions;
window.showAddExtensionModal = showAddExtensionModal;
window.closeAddExtensionModal = closeAddExtensionModal;
window.editExtension = editExtension;
window.closeEditExtensionModal = closeEditExtensionModal;
window.deleteExtension = deleteExtension;
window.rebootPhone = rebootPhone;
window.rebootAllPhones = rebootAllPhones;
