// API Base URL
const API_BASE = window.location.origin;

// State
let currentExtensions = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    initializeForms();
    checkConnection();
    loadDashboard();
    
    // Auto-refresh every 10 seconds
    setInterval(checkConnection, 10000);
});

// Tab Management
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            showTab(tabName);
        });
    });
}

function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active from all buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Load data for the tab
    switch(tabName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'extensions':
            loadExtensions();
            break;
        case 'phones':
            loadRegisteredPhones();
            break;
        case 'voicemail':
            loadVoicemailTab();
            break;
        case 'calls':
            loadCalls();
            break;
        case 'config':
            loadConfig();
            break;
    }
}

// Connection Check
async function checkConnection() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        const statusBadge = document.getElementById('connection-status');
        
        if (response.ok) {
            statusBadge.textContent = '✓ Connected';
            statusBadge.classList.remove('disconnected');
            statusBadge.classList.add('connected');
        } else {
            throw new Error('Connection failed');
        }
    } catch (error) {
        const statusBadge = document.getElementById('connection-status');
        statusBadge.textContent = '✗ Disconnected';
        statusBadge.classList.remove('connected');
        statusBadge.classList.add('disconnected');
    }
}

// Dashboard Functions
async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        const data = await response.json();
        
        document.getElementById('stat-extensions').textContent = data.registered_extensions || 0;
        document.getElementById('stat-calls').textContent = data.active_calls || 0;
        document.getElementById('stat-total-calls').textContent = data.total_calls || 0;
        document.getElementById('stat-recordings').textContent = data.active_recordings || 0;
        
        const systemStatus = document.getElementById('system-status');
        systemStatus.textContent = `System: ${data.running ? 'Running' : 'Stopped'}`;
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showNotification('Failed to load dashboard data', 'error');
    }
}

function refreshDashboard() {
    loadDashboard();
    showNotification('Dashboard refreshed', 'success');
}

// Extensions Functions
async function loadExtensions() {
    const tbody = document.getElementById('extensions-table-body');
    tbody.innerHTML = '<tr><td colspan="6" class="loading">Loading extensions...</td></tr>';
    
    try {
        const response = await fetch(`${API_BASE}/api/extensions`);
        const extensions = await response.json();
        currentExtensions = extensions;
        
        if (extensions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="loading">No extensions found</td></tr>';
            return;
        }
        
        // Helper function to escape HTML to prevent XSS
        const escapeHtml = (text) => {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        };
        
        tbody.innerHTML = extensions.map(ext => `
            <tr>
                <td><strong>${escapeHtml(ext.number)}</strong>${ext.ad_synced ? ' <span class="ad-badge" title="Synced from Active Directory">AD</span>' : ''}</td>
                <td>${escapeHtml(ext.name)}</td>
                <td>${ext.email ? escapeHtml(ext.email) : 'Not set'}</td>
                <td class="${ext.registered ? 'status-online' : 'status-offline'}">
                    ${ext.registered ? '● Online' : '○ Offline'}
                </td>
                <td>${ext.allow_external ? 'Yes' : 'No'}</td>
                <td>
                    <button class="btn btn-primary" onclick="editExtension('${escapeHtml(ext.number)}')">✏️ Edit</button>
                    ${ext.registered ? `<button class="btn btn-secondary" onclick="rebootPhone('${escapeHtml(ext.number)}')">🔄 Reboot</button>` : ''}
                    <button class="btn btn-danger" onclick="deleteExtension('${escapeHtml(ext.number)}')">🗑️ Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading extensions:', error);
        tbody.innerHTML = '<tr><td colspan="6" class="loading">Error loading extensions</td></tr>';
    }
}

// Add Extension Modal
function showAddExtensionModal() {
    document.getElementById('add-extension-modal').classList.add('active');
    document.getElementById('add-extension-form').reset();
}

function closeAddExtensionModal() {
    document.getElementById('add-extension-modal').classList.remove('active');
}

// Edit Extension Modal
function editExtension(number) {
    const ext = currentExtensions.find(e => e.number === number);
    if (!ext) return;
    
    document.getElementById('edit-ext-number').value = ext.number;
    document.getElementById('edit-ext-name').value = ext.name;
    document.getElementById('edit-ext-email').value = ext.email || '';
    document.getElementById('edit-ext-allow-external').checked = Boolean(ext.allow_external);
    document.getElementById('edit-ext-password').value = '';
    
    document.getElementById('edit-extension-modal').classList.add('active');
}

function closeEditExtensionModal() {
    document.getElementById('edit-extension-modal').classList.remove('active');
}

async function deleteExtension(number) {
    if (!confirm(`Are you sure you want to delete extension ${number}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/extensions/${number}`, {
            method: 'DELETE'
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

// Calls Functions
async function loadCalls() {
    const callsList = document.getElementById('calls-list');
    callsList.innerHTML = '<div class="loading">Loading calls...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/api/calls`);
        const calls = await response.json();
        
        if (calls.length === 0) {
            callsList.innerHTML = '<div class="loading">No active calls</div>';
            return;
        }
        
        callsList.innerHTML = calls.map(call => `
            <div class="call-item">
                <strong>Call:</strong> ${call}
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading calls:', error);
        callsList.innerHTML = '<div class="loading">Error loading calls</div>';
    }
}

// Configuration Functions
async function loadConfig() {
    // Load current configuration (if API endpoint exists)
    // For now, we'll just initialize with default values
    try {
        const response = await fetch(`${API_BASE}/api/config`);
        if (response.ok) {
            const config = await response.json();
            
            if (config.smtp) {
                document.getElementById('smtp-host').value = config.smtp.host || '';
                document.getElementById('smtp-port').value = config.smtp.port || 587;
                document.getElementById('smtp-username').value = config.smtp.username || '';
            }
            
            if (config.email) {
                document.getElementById('email-from').value = config.email.from_address || '';
                document.getElementById('email-notifications-enabled').checked = config.email_notifications || false;
            }
        }
    } catch (error) {
        // Config endpoint not available, silently use defaults
        // This is expected when the endpoint hasn't been implemented yet
    }
}

// Form Initialization
function initializeForms() {
    // Add Extension Form
    document.getElementById('add-extension-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const extensionData = {
            number: document.getElementById('new-ext-number').value,
            name: document.getElementById('new-ext-name').value,
            email: document.getElementById('new-ext-email').value,
            password: document.getElementById('new-ext-password').value,
            allow_external: document.getElementById('new-ext-allow-external').checked
        };
        
        try {
            const response = await fetch(`${API_BASE}/api/extensions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(extensionData)
            });
            
            if (response.ok) {
                showNotification('Extension added successfully', 'success');
                closeAddExtensionModal();
                loadExtensions();
            } else {
                const error = await response.json();
                showNotification(error.error || 'Failed to add extension', 'error');
            }
        } catch (error) {
            console.error('Error adding extension:', error);
            showNotification('Failed to add extension', 'error');
        }
    });
    
    // Edit Extension Form
    document.getElementById('edit-extension-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const number = document.getElementById('edit-ext-number').value;
        const extensionData = {
            name: document.getElementById('edit-ext-name').value,
            email: document.getElementById('edit-ext-email').value,
            allow_external: document.getElementById('edit-ext-allow-external').checked
        };
        
        const password = document.getElementById('edit-ext-password').value;
        if (password) {
            extensionData.password = password;
        }
        
        try {
            const response = await fetch(`${API_BASE}/api/extensions/${number}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(extensionData)
            });
            
            if (response.ok) {
                showNotification('Extension updated successfully', 'success');
                closeEditExtensionModal();
                loadExtensions();
            } else {
                const error = await response.json();
                showNotification(error.error || 'Failed to update extension', 'error');
            }
        } catch (error) {
            console.error('Error updating extension:', error);
            showNotification('Failed to update extension', 'error');
        }
    });
    
    // Email Config Form
    document.getElementById('email-config-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const configData = {
            smtp: {
                host: document.getElementById('smtp-host').value,
                port: parseInt(document.getElementById('smtp-port').value),
                username: document.getElementById('smtp-username').value,
                password: document.getElementById('smtp-password').value
            },
            email: {
                from_address: document.getElementById('email-from').value
            },
            email_notifications: document.getElementById('email-notifications-enabled').checked
        };
        
        try {
            const response = await fetch(`${API_BASE}/api/config`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(configData)
            });
            
            if (response.ok) {
                showNotification('Configuration saved successfully. Restart required.', 'success');
            } else {
                const error = await response.json();
                showNotification(error.error || 'Failed to save configuration', 'error');
            }
        } catch (error) {
            console.error('Error saving configuration:', error);
            showNotification('Failed to save configuration', 'error');
        }
    });
}

// Notification System
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 5px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        animation: slideInRight 0.3s;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    `;
    
    // Set background color based on type
    switch(type) {
        case 'success':
            notification.style.background = '#10b981';
            break;
        case 'error':
            notification.style.background = '#ef4444';
            break;
        default:
            notification.style.background = '#667eea';
    }
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add slide animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Voicemail Management Functions
async function loadVoicemailTab() {
    try {
        // Load extensions into dropdown
        const response = await fetch(`${API_BASE}/api/extensions`);
        const extensions = await response.json();
        
        const select = document.getElementById('vm-extension-select');
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

async function loadVoicemailForExtension() {
    const extension = document.getElementById('vm-extension-select').value;
    
    if (!extension) {
        document.getElementById('voicemail-pin-section').style.display = 'none';
        document.getElementById('voicemail-messages-section').style.display = 'none';
        return;
    }
    
    // Show sections
    document.getElementById('voicemail-pin-section').style.display = 'block';
    document.getElementById('voicemail-messages-section').style.display = 'block';
    document.getElementById('vm-current-extension').textContent = extension;
    
    try {
        // Load voicemail messages
        const response = await fetch(`${API_BASE}/api/voicemail/${extension}`);
        const data = await response.json();
        
        const tbody = document.getElementById('voicemail-table-body');
        
        if (!data.messages || data.messages.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="no-data">No voicemail messages</td></tr>';
            return;
        }
        
        tbody.innerHTML = '';
        data.messages.forEach(msg => {
            const row = document.createElement('tr');
            const timestamp = new Date(msg.timestamp).toLocaleString();
            const duration = msg.duration ? `${msg.duration}s` : 'Unknown';
            const status = msg.listened ? 'Read' : 'Unread';
            
            row.innerHTML = `
                <td>${timestamp}</td>
                <td>${msg.caller_id}</td>
                <td>${duration}</td>
                <td><span class="badge ${msg.listened ? 'badge-secondary' : 'badge-primary'}">${status}</span></td>
                <td>
                    <button class="btn btn-sm btn-info" onclick="playVoicemail('${extension}', '${msg.id}')">▶ Play</button>
                    <button class="btn btn-sm btn-success" onclick="downloadVoicemail('${extension}', '${msg.id}')">⬇ Download</button>
                    ${!msg.listened ? `<button class="btn btn-sm btn-secondary" onclick="markVoicemailRead('${extension}', '${msg.id}')">✓ Mark Read</button>` : ''}
                    <button class="btn btn-sm btn-danger" onclick="deleteVoicemail('${extension}', '${msg.id}')">🗑 Delete</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading voicemail:', error);
        showNotification('Failed to load voicemail messages', 'error');
    }
}

async function playVoicemail(extension, messageId) {
    try {
        const audioUrl = `${API_BASE}/api/voicemail/${extension}/${messageId}`;
        const audio = new Audio(audioUrl);
        audio.play();
        showNotification('Playing voicemail...', 'info');
        
        // Mark as read after playing
        setTimeout(() => markVoicemailRead(extension, messageId, false), 1000);
    } catch (error) {
        console.error('Error playing voicemail:', error);
        showNotification('Failed to play voicemail', 'error');
    }
}

async function downloadVoicemail(extension, messageId) {
    try {
        const url = `${API_BASE}/api/voicemail/${extension}/${messageId}`;
        const link = document.createElement('a');
        link.href = url;
        link.download = `voicemail_${extension}_${messageId}.wav`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showNotification('Downloading voicemail...', 'info');
    } catch (error) {
        console.error('Error downloading voicemail:', error);
        showNotification('Failed to download voicemail', 'error');
    }
}

async function markVoicemailRead(extension, messageId, showMsg = true) {
    try {
        const response = await fetch(`${API_BASE}/api/voicemail/${extension}/${messageId}/mark-read`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            if (showMsg) {
                showNotification('Message marked as read', 'success');
            }
            loadVoicemailForExtension();
        } else {
            throw new Error('Failed to mark as read');
        }
    } catch (error) {
        console.error('Error marking voicemail as read:', error);
        if (showMsg) {
            showNotification('Failed to mark message as read', 'error');
        }
    }
}

async function deleteVoicemail(extension, messageId) {
    if (!confirm('Are you sure you want to delete this voicemail message?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/voicemail/${extension}/${messageId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showNotification('Voicemail deleted successfully', 'success');
            loadVoicemailForExtension();
        } else {
            throw new Error('Failed to delete');
        }
    } catch (error) {
        console.error('Error deleting voicemail:', error);
        showNotification('Failed to delete voicemail', 'error');
    }
}

// Initialize voicemail PIN form
document.addEventListener('DOMContentLoaded', function() {
    const pinForm = document.getElementById('voicemail-pin-form');
    if (pinForm) {
        pinForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const extension = document.getElementById('vm-extension-select').value;
            const pin = document.getElementById('vm-pin').value;
            
            if (!extension) {
                showNotification('Please select an extension', 'error');
                return;
            }
            
            if (!/^\d{4}$/.test(pin)) {
                showNotification('PIN must be exactly 4 digits', 'error');
                return;
            }
            
            try {
                const response = await fetch(`${API_BASE}/api/voicemail/${extension}/pin`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ pin })
                });
                
                if (response.ok) {
                    showNotification('Voicemail PIN updated successfully', 'success');
                    document.getElementById('vm-pin').value = '';
                } else {
                    const error = await response.json();
                    showNotification(error.error || 'Failed to update PIN', 'error');
                }
            } catch (error) {
                console.error('Error updating voicemail PIN:', error);
                showNotification('Failed to update PIN', 'error');
            }
        });
    }
});

// Phone Reboot Functions
async function rebootPhone(extension) {
    if (!confirm(`Send reboot signal to phone at extension ${extension}?\n\nThe phone will restart and reload its configuration.`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/phones/${extension}/reboot`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showNotification(`Reboot signal sent to extension ${extension}`, 'success');
        } else {
            showNotification(data.error || 'Failed to send reboot signal', 'error');
        }
    } catch (error) {
        console.error('Error rebooting phone:', error);
        showNotification('Failed to send reboot signal', 'error');
    }
}

async function rebootAllPhones() {
    if (!confirm('Send reboot signal to ALL registered phones?\n\nAll online phones will restart and reload their configurations. This may take a few minutes.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/phones/reboot`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            const message = `Rebooted ${data.success_count} phone(s)` + 
                          (data.failed_count > 0 ? `, ${data.failed_count} failed` : '');
            showNotification(message, 'success');
            
            // Refresh extensions list after a delay to show new status
            setTimeout(loadExtensions, 2000);
        } else {
            showNotification(data.error || 'Failed to reboot phones', 'error');
        }
    } catch (error) {
        console.error('Error rebooting phones:', error);
        showNotification('Failed to reboot phones', 'error');
    }
}

// Registered Phones Functions
async function loadRegisteredPhones() {
    const tbody = document.getElementById('registered-phones-table-body');
    tbody.innerHTML = '<tr><td colspan="5" class="loading">Loading registered phones...</td></tr>';
    
    try {
        const response = await fetch(`${API_BASE}/api/registered-phones`);
        
        if (!response.ok) {
            // Try to parse error response from API
            let errorMessage = `HTTP ${response.status}`;
            try {
                const errorData = await response.json();
                if (errorData.error) {
                    errorMessage = errorData.error;
                    if (errorData.details) {
                        errorMessage += ` - ${errorData.details}`;
                    }
                }
            } catch (parseError) {
                // If parsing fails, keep the HTTP status message
            }
            throw new Error(errorMessage);
        }
        
        const phones = await response.json();
        
        if (!phones || phones.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="loading">No registered phones found in database</td></tr>';
            return;
        }
        
        // Clear table body
        tbody.innerHTML = '';
        
        // Create rows safely using DOM methods to prevent XSS
        phones.forEach(phone => {
            const row = document.createElement('tr');
            
            // Extension number
            const extCell = document.createElement('td');
            const extStrong = document.createElement('strong');
            extStrong.textContent = phone.extension_number || 'Unknown';
            extCell.appendChild(extStrong);
            row.appendChild(extCell);
            
            // IP Address
            const ipCell = document.createElement('td');
            ipCell.textContent = phone.ip_address || 'Unknown';
            row.appendChild(ipCell);
            
            // MAC Address
            const macCell = document.createElement('td');
            macCell.textContent = phone.mac_address || 'Unknown';
            row.appendChild(macCell);
            
            // User Agent
            const uaCell = document.createElement('td');
            uaCell.textContent = phone.user_agent || 'Unknown';
            row.appendChild(uaCell);
            
            // Last Registration
            const regCell = document.createElement('td');
            regCell.textContent = phone.last_registered ? new Date(phone.last_registered).toLocaleString() : 'Never';
            row.appendChild(regCell);
            
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading registered phones:', error);
        
        // Display error message in table
        const errorCell = document.createElement('td');
        errorCell.colSpan = 5;
        errorCell.className = 'error-message';
        errorCell.textContent = `Error: ${error.message}`;
        
        const errorRow = document.createElement('tr');
        errorRow.appendChild(errorCell);
        
        tbody.innerHTML = '';
        tbody.appendChild(errorRow);
        
        showNotification(`Failed to load registered phones: ${error.message}`, 'error');
    }
}
