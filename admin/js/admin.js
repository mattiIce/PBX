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
    tbody.innerHTML = '<tr><td colspan="5" class="loading">Loading extensions...</td></tr>';
    
    try {
        const response = await fetch(`${API_BASE}/api/extensions`);
        const extensions = await response.json();
        currentExtensions = extensions;
        
        if (extensions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="loading">No extensions found</td></tr>';
            return;
        }
        
        tbody.innerHTML = extensions.map(ext => `
            <tr>
                <td><strong>${ext.number}</strong></td>
                <td>${ext.name}</td>
                <td>${ext.email || 'Not set'}</td>
                <td class="${ext.registered ? 'status-online' : 'status-offline'}">
                    ${ext.registered ? '● Online' : '○ Offline'}
                </td>
                <td>
                    <button class="btn btn-primary" onclick="editExtension('${ext.number}')">✏️ Edit</button>
                    <button class="btn btn-danger" onclick="deleteExtension('${ext.number}')">🗑️ Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading extensions:', error);
        tbody.innerHTML = '<tr><td colspan="5" class="loading">Error loading extensions</td></tr>';
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
