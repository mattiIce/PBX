/**
 * Phone book page module.
 * Handles phone book entries management.
 */

import { getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';
import { escapeHtml } from '../utils/html.ts';

interface PhoneBookEntry {
    id: string;
    name?: string;
    number?: string;
    email?: string;
    group?: string;
}

interface PhoneBookResponse {
    entries?: PhoneBookEntry[];
}

export async function loadPhoneBook(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/phone-book`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: PhoneBookResponse = await response.json();

        const tbody = document.getElementById('phone-book-body') as HTMLElement | null;
        if (!tbody) return;

        const entries = data.entries ?? [];
        if (entries.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No phone book entries</td></tr>';
            return;
        }

        tbody.innerHTML = entries.map(e => `
            <tr>
                <td>${escapeHtml(e.name || '')}</td>
                <td>${escapeHtml(e.number || '')}</td>
                <td>${escapeHtml(e.email || '')}</td>
                <td>${escapeHtml(e.group || 'General')}</td>
                <td>
                    <button class="btn btn-primary btn-sm" onclick="editPhoneBookEntry('${e.id}')">Edit</button>
                    <button class="btn btn-danger btn-sm" onclick="deletePhoneBookEntry('${e.id}')">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error: unknown) {
        console.error('Error loading phone book:', error);
    }
}

export async function deletePhoneBookEntry(entryId: string): Promise<void> {
    if (!confirm('Delete this phone book entry?')) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/phone-book/${entryId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (response.ok) {
            showNotification('Phone book entry deleted', 'success');
            loadPhoneBook();
        }
    } catch (error: unknown) {
        console.error('Error deleting entry:', error);
        showNotification('Failed to delete entry', 'error');
    }
}

// Backward compatibility
window.loadPhoneBook = loadPhoneBook;
window.deletePhoneBookEntry = deletePhoneBookEntry;
