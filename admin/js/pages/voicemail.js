/**
 * Voicemail page module.
 * Handles voicemail listing, playback, download, and management.
 */

import { getAuthHeaders, getApiBaseUrl } from '../api/client.js';
import { showNotification } from '../ui/notifications.js';

export async function loadVoicemailTab() {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/extensions`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const extensions = await response.json();

        const select = document.getElementById('vm-extension-select');
        if (!select) return;
        select.innerHTML = '<option value="">Select Extension</option>';

        extensions.forEach(ext => {
            const option = document.createElement('option');
            option.value = ext.number;
            option.textContent = `${ext.number} - ${ext.name}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading voicemail tab:', error);
        showNotification('Failed to load extensions', 'error');
    }
}

export async function loadVoicemailForExtension() {
    const extension = document.getElementById('vm-extension-select')?.value;
    if (!extension) {
        ['voicemail-pin-section', 'voicemail-messages-section', 'voicemail-box-overview'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
        return;
    }

    ['voicemail-pin-section', 'voicemail-messages-section', 'voicemail-box-overview'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'block';
    });

    const currentExt = document.getElementById('vm-current-extension');
    if (currentExt) currentExt.textContent = extension;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/voicemail/${extension}`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();

        updateVoicemailView(data.messages, extension);
    } catch (error) {
        console.error('Error loading voicemail:', error);
        showNotification('Failed to load voicemail messages', 'error');
    }
}

function updateVoicemailView(messages, extension) {
    const container = document.getElementById('voicemail-cards-view');
    if (!container) return;

    if (!messages || messages.length === 0) {
        container.innerHTML = '<div class="info-box">No voicemail messages</div>';
        return;
    }

    container.innerHTML = messages.map(msg => {
        const timestamp = new Date(msg.timestamp).toLocaleString();
        const duration = msg.duration ? `${msg.duration}s` : 'Unknown';
        const isUnread = !msg.listened;

        return `
            <div class="voicemail-card ${isUnread ? 'unread' : ''}">
                <div class="voicemail-card-header">
                    <div class="voicemail-from">${msg.caller_id}</div>
                    <span class="voicemail-status-badge ${isUnread ? 'unread' : 'read'}">
                        ${isUnread ? 'NEW' : 'READ'}
                    </span>
                </div>
                <div class="voicemail-card-body">
                    <div>Time: ${timestamp}</div>
                    <div>Duration: ${duration}</div>
                </div>
                <div class="voicemail-card-actions">
                    <button class="btn btn-primary btn-sm" onclick="playVoicemail('${extension}', '${msg.id}')">Play</button>
                    <button class="btn btn-secondary btn-sm" onclick="downloadVoicemail('${extension}', '${msg.id}')">Download</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteVoicemail('${extension}', '${msg.id}')">Delete</button>
                </div>
            </div>
        `;
    }).join('');
}

export async function playVoicemail(extension, messageId) {
    try {
        const API_BASE = getApiBaseUrl();
        const url = `${API_BASE}/api/voicemail/${extension}/${messageId}/audio`;
        const player = document.getElementById('voicemail-audio-player');
        if (player) {
            player.src = url;
            player.play();
        }
        await markVoicemailRead(extension, messageId);
    } catch (error) {
        console.error('Error playing voicemail:', error);
        showNotification('Failed to play voicemail', 'error');
    }
}

export async function downloadVoicemail(extension, messageId) {
    const API_BASE = getApiBaseUrl();
    window.open(`${API_BASE}/api/voicemail/${extension}/${messageId}/audio?download=1`, '_blank');
}

export async function markVoicemailRead(extension, messageId) {
    try {
        const API_BASE = getApiBaseUrl();
        await fetch(`${API_BASE}/api/voicemail/${extension}/${messageId}/read`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
    } catch (error) {
        console.error('Error marking voicemail read:', error);
    }
}

export async function deleteVoicemail(extension, messageId) {
    if (!confirm('Delete this voicemail message?')) return;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/voicemail/${extension}/${messageId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (response.ok) {
            showNotification('Voicemail deleted', 'success');
            loadVoicemailForExtension();
        } else {
            showNotification('Failed to delete voicemail', 'error');
        }
    } catch (error) {
        console.error('Error deleting voicemail:', error);
        showNotification('Failed to delete voicemail', 'error');
    }
}

// Backward compatibility
window.loadVoicemailTab = loadVoicemailTab;
window.loadVoicemailForExtension = loadVoicemailForExtension;
window.playVoicemail = playVoicemail;
window.downloadVoicemail = downloadVoicemail;
window.deleteVoicemail = deleteVoicemail;
window.markVoicemailRead = markVoicemailRead;
