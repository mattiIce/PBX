// ============================================================================
// Enhanced Voicemail Management Functions
// ============================================================================

// Override the original loadVoicemailForExtension to add new features
const original_loadVoicemailForExtension = window.loadVoicemailForExtension;

window.loadVoicemailForExtension = async function() {
    // Call original function
    if (original_loadVoicemailForExtension) {
        await original_loadVoicemailForExtension();
    }

    const extension = document.getElementById('vm-extension-select').value;

    if (!extension) {
        document.getElementById('voicemail-box-overview').style.display = 'none';
        return;
    }

    // Show overview section
    document.getElementById('voicemail-box-overview').style.display = 'block';

    // Load mailbox details
    try {
        const response = await fetch(`${API_BASE}/api/voicemail-boxes/${extension}`, {headers: pbxAuthHeaders()});
        if (response.ok) {
            const data = await response.json();

            // Update overview stats
            document.getElementById('vm-total-messages').textContent = data.total_messages || 0;
            document.getElementById('vm-unread-messages').textContent = data.unread_messages || 0;
            document.getElementById('vm-has-greeting').textContent = data.has_custom_greeting ? 'Yes' : 'No';
        } else {
            console.error('Failed to load mailbox details:', response.status, response.statusText);
            // Still show the overview section with default values
            document.getElementById('vm-total-messages').textContent = '0';
            document.getElementById('vm-unread-messages').textContent = '0';
            document.getElementById('vm-has-greeting').textContent = 'Unknown';
        }
    } catch (error) {
        console.error('Error loading mailbox details:', error);
        // Still show the overview section with default values
        document.getElementById('vm-total-messages').textContent = '0';
        document.getElementById('vm-unread-messages').textContent = '0';
        document.getElementById('vm-has-greeting').textContent = 'Unknown';
    }
};

window.exportVoicemailBox = async function() {
    const extension = document.getElementById('vm-extension-select').value;

    if (!extension) {
        showNotification('Please select an extension first', 'error');
        return;
    }

    if (!confirm(`Export all voicemails for extension ${extension}?\n\nThis will download a ZIP file containing all voicemail messages and a manifest file.`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/voicemail-boxes/${extension}/export`, {
            method: 'POST',
            headers: pbxAuthHeaders()
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to export voicemail box');
        }

        // Get the blob from response
        const blob = await response.blob();

        // Extract filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `voicemail_${extension}_export.zip`;
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }

        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showNotification('Voicemail box exported successfully', 'success');
    } catch (error) {
        console.error('Error exporting voicemail box:', error);
        showNotification(`Failed to export voicemail box: ${error.message}`, 'error');
    }
};

window.clearVoicemailBox = async function() {
    const extension = document.getElementById('vm-extension-select').value;

    if (!extension) {
        showNotification('Please select an extension first', 'error');
        return;
    }

    if (!confirm(`⚠️ WARNING: Clear ALL voicemail messages for extension ${extension}?\n\nThis action cannot be undone!\n\nConsider exporting the voicemail box first.`)) {
        return;
    }

    // Ask for confirmation again
    if (!confirm('Are you absolutely sure? All voicemail messages will be permanently deleted.')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/voicemail-boxes/${extension}/clear`, {
            method: 'DELETE',
            headers: pbxAuthHeaders()
        });

        if (response.ok) {
            const data = await response.json();
            showNotification(data.message || 'Voicemail box cleared successfully', 'success');
            loadVoicemailForExtension();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to clear voicemail box', 'error');
        }
    } catch (error) {
        console.error('Error clearing voicemail box:', error);
        showNotification('Failed to clear voicemail box', 'error');
    }
};

window.uploadCustomGreeting = async function() {
    const extension = document.getElementById('vm-extension-select').value;

    if (!extension) {
        showNotification('Please select an extension first', 'error');
        return;
    }

    // Create file input
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'audio/wav';

    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        if (!file.name.endsWith('.wav')) {
            showNotification('Please upload a WAV file', 'error');
            return;
        }

        try {
            const token = localStorage.getItem('pbx_token');
            const greetingHeaders = token ? {'Authorization': 'Bearer ' + token} : {};
            const response = await fetch(`${API_BASE}/api/voicemail-boxes/${extension}/greeting`, {
                method: 'PUT',
                headers: greetingHeaders,
                body: await file.arrayBuffer()
            });

            if (response.ok) {
                showNotification('Custom greeting uploaded successfully', 'success');
                loadVoicemailForExtension();
            } else {
                const error = await response.json();
                showNotification(error.error || 'Failed to upload greeting', 'error');
            }
        } catch (error) {
            console.error('Error uploading greeting:', error);
            showNotification('Failed to upload greeting', 'error');
        }
    };

    input.click();
};

window.downloadCustomGreeting = async function() {
    const extension = document.getElementById('vm-extension-select').value;

    if (!extension) {
        showNotification('Please select an extension first', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/voicemail-boxes/${extension}/greeting`, {headers: pbxAuthHeaders()});

        if (!response.ok) {
            throw new Error('No custom greeting found');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `greeting_${extension}.wav`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showNotification('Greeting downloaded', 'success');
    } catch (error) {
        console.error('Error downloading greeting:', error);
        showNotification('No custom greeting found for this extension', 'error');
    }
};

window.deleteCustomGreeting = async function() {
    const extension = document.getElementById('vm-extension-select').value;

    if (!extension) {
        showNotification('Please select an extension first', 'error');
        return;
    }

    if (!confirm(`Delete custom greeting for extension ${extension}?\n\nThe default system greeting will be used.`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/voicemail-boxes/${extension}/greeting`, {
            method: 'DELETE',
            headers: pbxAuthHeaders()
        });

        if (response.ok) {
            showNotification('Custom greeting deleted successfully', 'success');
            loadVoicemailForExtension();
        } else {
            const error = await response.json();
            showNotification(error.error ?? 'Failed to delete greeting', 'error');
        }
    } catch (error) {
        console.error('Error deleting greeting:', error);
        showNotification('Failed to delete greeting', 'error');
    }
};

// Show all voicemail boxes overview
window.loadAllVoicemailBoxes = async function() {
    try {
        const response = await fetch(`${API_BASE}/api/voicemail-boxes`, {headers: pbxAuthHeaders()});
        if (!response.ok) {
            throw new Error('Failed to load voicemail boxes');
        }

        const data = await response.json();
        // This could be used to display a summary table of all mailboxes
        debugLog('All voicemail boxes:', data.voicemail_boxes);
        return data.voicemail_boxes;
    } catch (error) {
        console.error('Error loading voicemail boxes:', error);
        return [];
    }
};
