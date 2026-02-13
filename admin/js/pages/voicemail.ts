/**
 * Voicemail page module.
 * Handles voicemail listing, playback, download, and management.
 */

import { getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';

interface VoicemailExtension {
    number: string;
    name: string;
}

interface VoicemailMessage {
    id: string;
    caller_id: string;
    timestamp: string;
    duration?: number;
    listened?: boolean;
}

interface VoicemailResponse {
    messages?: VoicemailMessage[];
}

export async function loadVoicemailTab(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/extensions`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const extensions: VoicemailExtension[] = await response.json();

        const select = document.getElementById('vm-extension-select') as HTMLSelectElement | null;
        if (!select) return;
        select.innerHTML = '<option value="">Select Extension</option>';

        extensions.forEach(ext => {
            const option = document.createElement('option');
            option.value = ext.number;
            option.textContent = `${ext.number} - ${ext.name}`;
            select.appendChild(option);
        });
    } catch (error: unknown) {
        console.error('Error loading voicemail tab:', error);
        showNotification('Failed to load extensions', 'error');
    }
}

export async function loadVoicemailForExtension(): Promise<void> {
    const extension = (document.getElementById('vm-extension-select') as HTMLSelectElement | null)?.value;
    if (!extension) {
        ['voicemail-pin-section', 'voicemail-messages-section', 'voicemail-box-overview'].forEach(id => {
            const el = document.getElementById(id) as HTMLElement | null;
            if (el) el.style.display = 'none';
        });
        return;
    }

    ['voicemail-pin-section', 'voicemail-messages-section', 'voicemail-box-overview'].forEach(id => {
        const el = document.getElementById(id) as HTMLElement | null;
        if (el) el.style.display = 'block';
    });

    const currentExt = document.getElementById('vm-current-extension') as HTMLElement | null;
    if (currentExt) currentExt.textContent = extension;

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/voicemail/${extension}`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data: VoicemailResponse = await response.json();

        updateVoicemailView(data.messages, extension);
    } catch (error: unknown) {
        console.error('Error loading voicemail:', error);
        showNotification('Failed to load voicemail messages', 'error');
    }
}

function updateVoicemailView(messages: VoicemailMessage[] | undefined, extension: string): void {
    const container = document.getElementById('voicemail-cards-view') as HTMLElement | null;
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

export async function playVoicemail(extension: string, messageId: string): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const url = `${API_BASE}/api/voicemail/${extension}/${messageId}/audio`;
        const player = document.getElementById('voicemail-audio-player') as HTMLAudioElement | null;
        if (player) {
            player.src = url;
            player.play();
        }
        await markVoicemailRead(extension, messageId);
    } catch (error: unknown) {
        console.error('Error playing voicemail:', error);
        showNotification('Failed to play voicemail', 'error');
    }
}

export async function downloadVoicemail(extension: string, messageId: string): Promise<void> {
    const API_BASE = getApiBaseUrl();
    window.open(`${API_BASE}/api/voicemail/${extension}/${messageId}/audio?download=1`, '_blank');
}

export async function markVoicemailRead(extension: string, messageId: string): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        await fetch(`${API_BASE}/api/voicemail/${extension}/${messageId}/read`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
    } catch (error: unknown) {
        console.error('Error marking voicemail read:', error);
    }
}

export async function deleteVoicemail(extension: string, messageId: string): Promise<void> {
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
    } catch (error: unknown) {
        console.error('Error deleting voicemail:', error);
        showNotification('Failed to delete voicemail', 'error');
    }
}

// Backward compatibility
(window as any).loadVoicemailTab = loadVoicemailTab;
(window as any).loadVoicemailForExtension = loadVoicemailForExtension;
(window as any).playVoicemail = playVoicemail;
(window as any).downloadVoicemail = downloadVoicemail;
(window as any).deleteVoicemail = deleteVoicemail;
(window as any).markVoicemailRead = markVoicemailRead;
