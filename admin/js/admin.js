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
        case 'analytics':
            loadAnalytics();
            break;
        case 'extensions':
            loadExtensions();
            break;
        case 'phones':
            loadRegisteredPhones();
            break;
        case 'provisioning':
            loadProvisioning();
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
        
        // Load AD integration status
        loadADStatus();
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showNotification('Failed to load dashboard data', 'error');
    }
}

function refreshDashboard() {
    loadDashboard();
    showNotification('Dashboard refreshed', 'success');
}

// AD Integration Functions
async function loadADStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/integrations/ad/status`);
        const data = await response.json();
        
        // Update status badge
        const statusBadge = document.getElementById('ad-status-badge');
        if (data.enabled) {
            statusBadge.textContent = 'Enabled';
            statusBadge.className = 'status-badge enabled';
        } else {
            statusBadge.textContent = 'Disabled';
            statusBadge.className = 'status-badge disabled';
        }
        
        // Update connection status
        const connectionStatus = document.getElementById('ad-connection-status');
        if (data.connected) {
            connectionStatus.textContent = '✓ Connected';
            connectionStatus.style.color = '#10b981';
        } else {
            connectionStatus.textContent = '✗ Not Connected';
            connectionStatus.style.color = '#ef4444';
        }
        
        // Update server
        document.getElementById('ad-server').textContent = data.server || 'Not configured';
        
        // Update auto provision
        document.getElementById('ad-auto-provision').textContent = data.auto_provision ? 'Yes' : 'No';
        
        // Update synced users count
        document.getElementById('ad-synced-users').textContent = data.synced_users || 0;
        
        // Update error message
        const errorElement = document.getElementById('ad-error');
        if (data.error) {
            errorElement.textContent = data.error;
            errorElement.style.color = '#d32f2f';
        } else {
            errorElement.textContent = 'None';
            errorElement.style.color = '#10b981';
        }
        
        // Enable/disable sync button based on status
        const syncBtn = document.getElementById('ad-sync-btn');
        if (data.enabled && data.connected) {
            syncBtn.disabled = false;
        } else {
            syncBtn.disabled = true;
        }
    } catch (error) {
        console.error('Error loading AD status:', error);
        document.getElementById('ad-status-badge').textContent = 'Error';
        document.getElementById('ad-status-badge').className = 'status-badge disconnected';
    }
}

function refreshADStatus() {
    loadADStatus();
    showNotification('AD status refreshed', 'success');
}

async function syncADUsers() {
    const syncBtn = document.getElementById('ad-sync-btn');
    const originalText = syncBtn.textContent;
    
    // Disable button and show loading state
    syncBtn.disabled = true;
    syncBtn.textContent = '⏳ Syncing...';
    
    try {
        const response = await fetch(`${API_BASE}/api/integrations/ad/sync`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: `HTTP error! status: ${response.status}` }));
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(data.message || `Successfully synced ${data.synced_count} users`, 'success');
            // Refresh both AD status and extensions
            loadADStatus();
            loadExtensions();
        } else {
            showNotification(data.error || 'Failed to sync users', 'error');
        }
    } catch (error) {
        console.error('Error syncing AD users:', error);
        showNotification('Error syncing AD users', 'error');
    } finally {
        // Re-enable button
        syncBtn.textContent = originalText;
        syncBtn.disabled = false;
    }
}

// Extensions Functions
async function loadExtensions() {
    const tbody = document.getElementById('extensions-table-body');
    tbody.innerHTML = '<tr><td colspan="6" class="loading">Loading extensions...</td></tr>';
    
    try {
        const response = await fetch(`${API_BASE}/api/extensions`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
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
    
    // Add Device Form
    const addDeviceForm = document.getElementById('add-device-form');
    if (addDeviceForm) {
        addDeviceForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const mac = document.getElementById('device-mac').value;
            const extension = document.getElementById('device-extension').value;
            const vendor = document.getElementById('device-vendor').value;
            const model = document.getElementById('device-model').value;
            
            try {
                const response = await fetch(`${API_BASE}/api/provisioning/devices`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        mac_address: mac,
                        extension_number: extension,
                        vendor: vendor,
                        model: model
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    const msg = 'Device registered successfully! Config URL: ' + data.device.config_url;
                    showNotification(msg, 'success');
                    closeAddDeviceModal();
                    loadProvisioningDevices();
                } else {
                    const data = await response.json();
                    showNotification(data.error || 'Failed to register device', 'error');
                }
            } catch (error) {
                console.error('Error registering device:', error);
                showNotification('Error registering device: ' + error.message, 'error');
            }
        });
    }
    
    // Provisioning settings change handlers
    const serverIPInput = document.getElementById('provisioning-server-ip');
    const portInput = document.getElementById('provisioning-port');
    
    if (serverIPInput) {
        serverIPInput.addEventListener('input', updateProvisioningUrlFormat);
    }
    if (portInput) {
        portInput.addEventListener('input', updateProvisioningUrlFormat);
    }
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

// ============================================================================
// Phone Provisioning Functions
// ============================================================================
let supportedVendors = [];
let supportedModels = {};

async function loadProvisioning() {
    await loadProvisioningSettings();
    await loadSupportedVendors();
    await loadProvisioningDevices();
}

async function loadProvisioningSettings() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        if (response.ok) {
            const data = await response.json();
            // Get current server IP from status or use default
            const serverIP = data.server_ip || window.location.hostname;
            document.getElementById('provisioning-server-ip').value = serverIP;
            
            // Update URL format display
            updateProvisioningUrlFormat();
        }
    } catch (error) {
        console.error('Error loading provisioning settings:', error);
    }
}

function toggleProvisioningEnabled() {
    const enabled = document.getElementById('provisioning-enabled').checked;
    const settingsDiv = document.getElementById('provisioning-settings');
    settingsDiv.style.display = enabled ? 'block' : 'none';
}

function updateProvisioningUrlFormat() {
    const serverIP = document.getElementById('provisioning-server-ip').value || 'SERVER';
    const port = document.getElementById('provisioning-port').value || '8080';
    const urlFormat = `http://${serverIP}:${port}/provision/{mac}.cfg`;
    document.getElementById('provisioning-url-format').value = urlFormat;
}

async function saveProvisioningSettings() {
    const enabled = document.getElementById('provisioning-enabled').checked;
    const serverIP = document.getElementById('provisioning-server-ip').value;
    const port = document.getElementById('provisioning-port').value;
    const customDir = document.getElementById('provisioning-custom-dir').value;
    
    if (!serverIP) {
        showNotification('Please enter a server IP address', 'error');
        return;
    }
    
    const configMsg = `Provisioning settings need to be updated in config.yml:\n\n` +
          `provisioning:\n` +
          `  enabled: ${enabled}\n` +
          `  url_format: http://${serverIP}:${port}/provision/{mac}.cfg\n` +
          `  custom_templates_dir: "${customDir}"\n\n` +
          'Then restart the PBX server.';
    
    showNotification('Settings saved. Update config.yml and restart required.', 'info');
    console.log(configMsg);
}

async function loadSupportedVendors() {
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/vendors`);
        if (response.ok) {
            const data = await response.json();
            supportedVendors = data.vendors || [];
            supportedModels = data.models || {};
            
            // Display supported vendors
            const vendorsList = document.getElementById('supported-vendors-list');
            if (supportedVendors.length > 0) {
                let html = '<ul>';
                for (const vendor of supportedVendors) {
                    html += `<li><strong>${vendor.toUpperCase()}</strong>: `;
                    const models = supportedModels[vendor] || [];
                    html += models.map(m => m.toUpperCase()).join(', ');
                    html += '</li>';
                }
                html += '</ul>';
                vendorsList.innerHTML = html;
            } else {
                vendorsList.innerHTML = '<p>No vendors available. Check PBX configuration.</p>';
            }
        }
    } catch (error) {
        console.error('Error loading supported vendors:', error);
        document.getElementById('supported-vendors-list').innerHTML = 
            '<p class="error">Error loading vendors: ' + error.message + '</p>';
    }
}

async function loadProvisioningDevices() {
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/devices`);
        const tbody = document.getElementById('provisioning-devices-table-body');
        
        if (response.ok) {
            const devices = await response.json();
            
            if (devices.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="no-data">No devices provisioned yet. Click "Add Device" to register phones.</td></tr>';
            } else {
                tbody.innerHTML = devices.map(device => {
                    const createdDate = device.created_at ? new Date(device.created_at).toLocaleString() : '-';
                    const provisionedDate = device.last_provisioned ? new Date(device.last_provisioned).toLocaleString() : 'Never';
                    
                    return `
                        <tr>
                            <td><code>${device.mac_address}</code></td>
                            <td>${device.extension_number}</td>
                            <td>${device.vendor.toUpperCase()}</td>
                            <td>${device.model.toUpperCase()}</td>
                            <td>${createdDate}</td>
                            <td>${provisionedDate}</td>
                            <td>
                                <button class="btn btn-small btn-danger" onclick="deleteDevice('${device.mac_address}')">🗑️ Delete</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        } else {
            tbody.innerHTML = '<tr><td colspan="7" class="error">Error loading devices</td></tr>';
        }
    } catch (error) {
        console.error('Error loading provisioning devices:', error);
        document.getElementById('provisioning-devices-table-body').innerHTML = 
            '<tr><td colspan="7" class="error">Error: ' + error.message + '</td></tr>';
    }
}

async function showAddDeviceModal() {
    // Populate extension dropdown
    const extensionSelect = document.getElementById('device-extension');
    extensionSelect.innerHTML = '<option value="">Loading extensions...</option>';
    
    // Fetch extensions if not already loaded
    try {
        const response = await fetch(`${API_BASE}/api/extensions`);
        if (response.ok) {
            const extensions = await response.json();
            extensionSelect.innerHTML = '<option value="">Select Extension</option>';
            
            extensions.forEach(ext => {
                const option = document.createElement('option');
                option.value = ext.number;
                option.textContent = `${ext.number} - ${ext.name}`;
                extensionSelect.appendChild(option);
            });
        } else {
            extensionSelect.innerHTML = '<option value="">Error loading extensions</option>';
        }
    } catch (error) {
        console.error('Error loading extensions:', error);
        extensionSelect.innerHTML = '<option value="">Error loading extensions</option>';
    }
    
    // Populate vendor dropdown
    const vendorSelect = document.getElementById('device-vendor');
    vendorSelect.innerHTML = '<option value="">Select Vendor</option>';
    
    supportedVendors.forEach(vendor => {
        const option = document.createElement('option');
        option.value = vendor;
        option.textContent = vendor.toUpperCase();
        vendorSelect.appendChild(option);
    });
    
    // Reset model dropdown
    document.getElementById('device-model').innerHTML = '<option value="">Select Vendor First</option>';
    
    // Show modal
    document.getElementById('add-device-modal').style.display = 'block';
}

function closeAddDeviceModal() {
    document.getElementById('add-device-modal').style.display = 'none';
    document.getElementById('add-device-form').reset();
}

function updateModelOptions() {
    const vendor = document.getElementById('device-vendor').value;
    const modelSelect = document.getElementById('device-model');
    
    if (!vendor) {
        modelSelect.innerHTML = '<option value="">Select Vendor First</option>';
        return;
    }
    
    const models = supportedModels[vendor] || [];
    modelSelect.innerHTML = '<option value="">Select Model</option>';
    
    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model.toUpperCase();
        modelSelect.appendChild(option);
    });
}

async function deleteDevice(mac) {
    if (!confirm(`Are you sure you want to delete device ${mac}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/devices/${mac}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showNotification('Device deleted successfully', 'success');
            loadProvisioningDevices();
        } else {
            const data = await response.json();
            showNotification('Failed to delete device: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error deleting device:', error);
        showNotification('Error deleting device: ' + error.message, 'error');
    }
}

// Template management functions
async function loadProvisioningTemplates() {
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/templates`);
        if (response.ok) {
            const data = await response.json();
            displayTemplatesList(data.templates || []);
        } else {
            showNotification('Error loading templates', 'error');
        }
    } catch (error) {
        console.error('Error loading templates:', error);
        showNotification('Error loading templates: ' + error.message, 'error');
    }
}

function displayTemplatesList(templates) {
    const tbody = document.getElementById('templates-table-body');
    if (!tbody) return;
    
    if (templates.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5">No templates found</td></tr>';
        return;
    }
    
    // Clear existing content
    tbody.innerHTML = '';
    
    // Create rows safely without XSS vulnerabilities
    templates.forEach(template => {
        const row = document.createElement('tr');
        
        // Vendor cell
        const vendorCell = document.createElement('td');
        vendorCell.textContent = template.vendor;
        row.appendChild(vendorCell);
        
        // Model cell
        const modelCell = document.createElement('td');
        modelCell.textContent = template.model;
        row.appendChild(modelCell);
        
        // Type cell
        const typeCell = document.createElement('td');
        const badge = document.createElement('span');
        badge.className = template.is_custom ? 'badge badge-success' : 'badge badge-info';
        badge.textContent = template.is_custom ? 'Custom' : 'Built-in';
        typeCell.appendChild(badge);
        row.appendChild(typeCell);
        
        // Size cell
        const sizeCell = document.createElement('td');
        sizeCell.textContent = (template.size / 1024).toFixed(1) + ' KB';
        row.appendChild(sizeCell);
        
        // Actions cell
        const actionsCell = document.createElement('td');
        
        // View button
        const viewBtn = document.createElement('button');
        viewBtn.className = 'btn btn-sm btn-primary';
        viewBtn.textContent = '👁️ View';
        viewBtn.onclick = () => viewTemplate(template.vendor, template.model);
        actionsCell.appendChild(viewBtn);
        
        // Export button
        const exportBtn = document.createElement('button');
        exportBtn.className = 'btn btn-sm btn-success';
        exportBtn.textContent = '💾 Export';
        exportBtn.onclick = () => exportTemplate(template.vendor, template.model);
        actionsCell.appendChild(exportBtn);
        
        // Edit button (only for custom templates)
        if (template.is_custom) {
            const editBtn = document.createElement('button');
            editBtn.className = 'btn btn-sm btn-warning';
            editBtn.textContent = '✏️ Edit';
            editBtn.onclick = () => editTemplate(template.vendor, template.model);
            actionsCell.appendChild(editBtn);
        }
        
        row.appendChild(actionsCell);
        tbody.appendChild(row);
    });
}

async function viewTemplate(vendor, model) {
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/templates/${vendor}/${model}`);
        if (response.ok) {
            const data = await response.json();
            showTemplateViewModal(vendor, model, data.content, data.placeholders, false);
        } else {
            showNotification('Error loading template', 'error');
        }
    } catch (error) {
        console.error('Error viewing template:', error);
        showNotification('Error viewing template: ' + error.message, 'error');
    }
}

async function exportTemplate(vendor, model) {
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/templates/${vendor}/${model}/export`, {
            method: 'POST'
        });
        if (response.ok) {
            const data = await response.json();
            showNotification(`Template exported to: ${data.filepath}`, 'success');
            loadProvisioningTemplates(); // Refresh list
        } else {
            const error = await response.json();
            showNotification('Error exporting template: ' + error.error, 'error');
        }
    } catch (error) {
        console.error('Error exporting template:', error);
        showNotification('Error exporting template: ' + error.message, 'error');
    }
}

async function editTemplate(vendor, model) {
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/templates/${vendor}/${model}`);
        if (response.ok) {
            const data = await response.json();
            showTemplateViewModal(vendor, model, data.content, data.placeholders, true);
        } else {
            showNotification('Error loading template', 'error');
        }
    } catch (error) {
        console.error('Error loading template:', error);
        showNotification('Error loading template: ' + error.message, 'error');
    }
}

function showTemplateViewModal(vendor, model, content, placeholders, editable) {
    const modal = document.getElementById('template-view-modal');
    const title = document.getElementById('template-modal-title');
    const textarea = document.getElementById('template-content');
    const placeholdersDiv = document.getElementById('template-placeholders');
    const saveBtn = document.getElementById('save-template-btn');
    
    if (!modal) return;
    
    title.textContent = editable ? 
        `Edit Template: ${vendor} ${model}` : 
        `View Template: ${vendor} ${model}`;
    
    textarea.value = content;
    textarea.readOnly = !editable;
    
    // Display available placeholders safely
    placeholdersDiv.innerHTML = ''; // Clear first
    
    const strong = document.createElement('strong');
    strong.textContent = 'Available Placeholders:';
    placeholdersDiv.appendChild(strong);
    
    const ul = document.createElement('ul');
    placeholders.forEach(p => {
        const li = document.createElement('li');
        const code = document.createElement('code');
        code.textContent = p;
        li.appendChild(code);
        ul.appendChild(li);
    });
    placeholdersDiv.appendChild(ul);
    
    const p = document.createElement('p');
    const small = document.createElement('small');
    small.textContent = 'These placeholders will be automatically replaced with device-specific information when a phone requests configuration.';
    p.appendChild(small);
    placeholdersDiv.appendChild(p);
    
    // Set up save button
    saveBtn.style.display = editable ? 'inline-block' : 'none';
    saveBtn.onclick = async () => {
        await saveTemplateContent(vendor, model, textarea.value);
    };
    
    modal.style.display = 'block';
}

function closeTemplateViewModal() {
    const modal = document.getElementById('template-view-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function saveTemplateContent(vendor, model, content) {
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/templates/${vendor}/${model}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content })
        });
        
        if (response.ok) {
            showNotification('Template updated successfully', 'success');
            closeTemplateViewModal();
            loadProvisioningTemplates(); // Refresh list
        } else {
            const error = await response.json();
            showNotification('Error updating template: ' + error.error, 'error');
        }
    } catch (error) {
        console.error('Error saving template:', error);
        showNotification('Error saving template: ' + error.message, 'error');
    }
}

async function reloadTemplates() {
    try {
        const response = await fetch(`${API_BASE}/api/provisioning/reload-templates`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const data = await response.json();
            showNotification(`Templates reloaded: ${data.statistics.total_templates} templates from ${data.statistics.vendors} vendors`, 'success');
            loadProvisioningTemplates(); // Refresh list
        } else {
            const error = await response.json();
            showNotification('Error reloading templates: ' + error.error, 'error');
        }
    } catch (error) {
        console.error('Error reloading templates:', error);
        showNotification('Error reloading templates: ' + error.message, 'error');
    }
}

// ============================================================================
// Analytics and Statistics Functions
// ============================================================================
let analyticsCharts = {};

/**
 * Check if Chart.js library is available
 * @param {HTMLElement} ctx - Canvas context element (optional, for inline error display)
 * @returns {boolean} - True if Chart.js is available, false otherwise
 */
function isChartJsAvailable(ctx = null) {
    // Check if Chart.js is loaded, accounting for potential delay from fallback CDNs
    if (typeof Chart === 'undefined') {
        // Check if we know loading failed completely
        if (window.chartJsLoadFailed === true) {
            console.warn('Chart.js library failed to load from all CDN sources');
            if (ctx && ctx.parentElement) {
                const msg = document.createElement('p');
                msg.className = 'info-message';
                msg.style.padding = '20px';
                msg.style.textAlign = 'center';
                msg.style.color = '#666';
                msg.innerHTML = '📊 Chart visualization unavailable in offline mode<br><small>Data is still available in tables below</small>';
                ctx.parentElement.innerHTML = '';
                ctx.parentElement.appendChild(msg);
            }
        }
        return false;
    }
    return true;
}

async function loadAnalytics() {
    const days = document.getElementById('analytics-period')?.value || 7;
    
    // Check if Chart.js is loaded
    const chartJsAvailable = isChartJsAvailable();
    
    // Show warning if Chart.js is not available, but continue to load data
    if (!chartJsAvailable) {
        showNotification('Chart library not available - displaying data in tables only. Charts require internet connection.', 'warning');
        // Hide chart containers
        const chartContainers = document.querySelectorAll('.chart-box');
        chartContainers.forEach(container => {
            container.style.display = 'none';
        });
    } else {
        // Show chart containers if they were hidden
        const chartContainers = document.querySelectorAll('.chart-box');
        chartContainers.forEach(container => {
            container.style.display = '';
        });
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/statistics?days=${days}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update overview stats (always available)
        updateAnalyticsOverview(data.overview);
        
        // Render charts only if Chart.js is available
        if (chartJsAvailable) {
            renderDailyTrendsChart(data.daily_trends);
            renderHourlyDistributionChart(data.hourly_distribution);
            renderDispositionChart(data.call_disposition);
            renderQualityChart(data.call_quality);
        }
        
        // Update top callers table (always available)
        updateTopCallersTable(data.top_callers);
        
        // Update peak hours display (always available)
        updatePeakHours(data.peak_hours);
        
        if (chartJsAvailable) {
            showNotification('Analytics refreshed successfully', 'success');
        } else {
            showNotification('Analytics data loaded (charts unavailable - offline mode)', 'info');
        }
    } catch (error) {
        console.error('Error loading analytics:', error);
        showNotification('Failed to load analytics: ' + error.message, 'error');
    }
}

function updateAnalyticsOverview(overview) {
    document.getElementById('analytics-total-calls').textContent = overview.total_calls || 0;
    document.getElementById('analytics-answered-calls').textContent = overview.answered_calls || 0;
    document.getElementById('analytics-answer-rate').textContent = (overview.answer_rate || 0) + '%';
    document.getElementById('analytics-avg-duration').textContent = (overview.avg_call_duration || 0).toFixed(1) + 's';
}

function renderDailyTrendsChart(trends) {
    const ctx = document.getElementById('daily-trends-chart');
    if (!ctx) return;
    
    // Check if Chart.js is available
    if (!isChartJsAvailable(ctx)) return;
    
    // Destroy existing chart if it exists
    if (analyticsCharts.dailyTrends) {
        analyticsCharts.dailyTrends.destroy();
    }
    
    const labels = trends.map(t => t.date);
    const totalData = trends.map(t => t.total_calls);
    const answeredData = trends.map(t => t.answered);
    const missedData = trends.map(t => t.missed);
    
    analyticsCharts.dailyTrends = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total Calls',
                    data: totalData,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Answered',
                    data: answeredData,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Missed',
                    data: missedData,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function renderHourlyDistributionChart(distribution) {
    const ctx = document.getElementById('hourly-distribution-chart');
    if (!ctx) return;
    
    // Check if Chart.js is available
    if (!isChartJsAvailable(ctx)) return;
    
    if (analyticsCharts.hourlyDistribution) {
        analyticsCharts.hourlyDistribution.destroy();
    }
    
    const labels = distribution.map(d => `${d.hour}:00`);
    const data = distribution.map(d => d.calls);
    
    analyticsCharts.hourlyDistribution = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Calls by Hour',
                data: data,
                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                borderColor: '#667eea',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function renderDispositionChart(dispositions) {
    const ctx = document.getElementById('disposition-chart');
    if (!ctx) return;
    
    // Check if Chart.js is available
    if (!isChartJsAvailable(ctx)) return;
    
    if (analyticsCharts.disposition) {
        analyticsCharts.disposition.destroy();
    }
    
    const labels = dispositions.map(d => d.disposition);
    const data = dispositions.map(d => d.count);
    const colors = {
        'answered': '#10b981',
        'no_answer': '#f59e0b',
        'busy': '#ef4444',
        'failed': '#6c757d',
        'cancelled': '#3b82f6'
    };
    
    const backgroundColors = labels.map(label => colors[label] || '#667eea');
    
    analyticsCharts.disposition = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels.map(l => l.replace('_', ' ').toUpperCase()),
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'right',
                }
            }
        }
    });
}

function renderQualityChart(quality) {
    const ctx = document.getElementById('quality-chart');
    if (!ctx) return;
    
    // Check if Chart.js is available
    if (!isChartJsAvailable(ctx)) return;
    
    if (analyticsCharts.quality) {
        analyticsCharts.quality.destroy();
    }
    
    const qualityDist = quality.quality_distribution || {};
    
    analyticsCharts.quality = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['MOS Score', 'Jitter (ms)', 'Packet Loss (%)', 'Latency (ms)'],
            datasets: [{
                label: 'Quality Metrics',
                data: [
                    quality.average_mos || 0,
                    quality.average_jitter || 0,
                    quality.average_packet_loss || 0,
                    quality.average_latency || 0
                ],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.6)',
                    'rgba(59, 130, 246, 0.6)',
                    'rgba(239, 68, 68, 0.6)',
                    'rgba(245, 158, 11, 0.6)'
                ],
                borderColor: [
                    '#10b981',
                    '#3b82f6',
                    '#ef4444',
                    '#f59e0b'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function updateTopCallersTable(topCallers) {
    const tbody = document.getElementById('top-callers-table');
    if (!tbody) return;
    
    if (!topCallers || topCallers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="no-data">No call data available</td></tr>';
        return;
    }
    
    tbody.innerHTML = topCallers.map(caller => `
        <tr>
            <td><strong>${caller.extension}</strong></td>
            <td>${caller.calls}</td>
            <td>${(caller.total_duration / 60).toFixed(1)}</td>
            <td>${caller.avg_duration.toFixed(1)}</td>
        </tr>
    `).join('');
}

function updatePeakHours(peakHours) {
    const display = document.getElementById('peak-hours-display');
    if (!display) return;
    
    if (!peakHours || peakHours.length === 0) {
        display.innerHTML = '<p>No peak hours data available</p>';
        return;
    }
    
    const html = '<ul>' + peakHours.map((peak, index) => 
        `<li><strong>#${index + 1}:</strong> ${peak.hour} with ${peak.calls} calls</li>`
    ).join('') + '</ul>';
    
    display.innerHTML = html;
}
