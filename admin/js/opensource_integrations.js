/**
 * Open Source Integrations Management
 * Handles configuration for Jitsi, Matrix, and EspoCRM
 */

// HTML-escape a string for safe insertion into HTML context
function escapeHtml(str) {
    return String(str).replace(/[&<>"'\/]/g, function (s) {
       switch (s) {
          case '&': return '&amp;';
          case '<': return '&lt;';
          case '>': return '&gt;';
          case '"': return '&quot;';
          case "'": return '&#39;';
          case '/': return '&#x2F;';
          default: return s;
       }
    });
}

// Integration names mapping (used across multiple functions)
const INTEGRATION_NAMES = {
    jitsi: 'Jitsi Meet',
    matrix: 'Matrix',
    espocrm: 'EspoCRM'
};

// Show a temporary notification message
function showQuickSetupNotification(message, type = 'info', duration = 5000) {
    // Create notification element if it doesn't exist
    let notificationContainer = document.getElementById('quick-setup-notifications');
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'quick-setup-notifications';
        notificationContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            max-width: 400px;
        `;
        document.body.appendChild(notificationContainer);
    }

    // Create notification
    const notification = document.createElement('div');
    const bgColors = {
        success: '#4CAF50',
        error: '#f44336',
        warning: '#ff9800',
        info: '#2196F3'
    };

    notification.style.cssText = `
        background-color: ${bgColors[type] || bgColors.info};
        color: white;
        padding: 16px 20px;
        margin-bottom: 10px;
        border-radius: 4px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        display: flex;
        align-items: center;
        justify-content: space-between;
        animation: slideIn 0.3s ease-out;
    `;

    notification.innerHTML = `
        <div style="flex: 1; padding-right: 10px;">${escapeHtml(message)}</div>
        <button onclick="this.parentElement.remove()" style="
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            padding: 0;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
        ">×</button>
    `;

    // Add animation keyframes if not already added
    if (!document.getElementById('notification-animations')) {
        const style = document.createElement('style');
        style.id = 'notification-animations';
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(400px);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
        `;
        document.head.appendChild(style);
    }

    notificationContainer.appendChild(notification);

    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            notification.style.animation = 'slideIn 0.3s ease-out reverse';
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }
}

// Initialize open source integrations when tab is shown
function initializeOpenSourceIntegrations() {
    loadJitsiConfig();
    loadMatrixConfig();
    loadEspoCRMConfig();
    updateQuickSetupStatus();
}

// Load all open source integration data (used by refreshAllData)
async function loadOpenSourceIntegrations() {
    // Load individual integration configs
    loadJitsiConfig();
    loadMatrixConfig();
    loadEspoCRMConfig();
    // Update the quick setup status display
    await updateQuickSetupStatus();
}

// =============================================================================
// Quick Setup Functions
// =============================================================================

/**
 * Update the status of quick setup checkboxes based on current config
 */
async function updateQuickSetupStatus() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        const integrations = data.integrations || {};

        // Update Jitsi status
        const jitsiEnabled = integrations.jitsi?.enabled || false;
        const jitsiCheckbox = document.getElementById('quick-jitsi-enabled');
        const jitsiBadge = document.getElementById('jitsi-status-badge');
        if (jitsiCheckbox) {
            jitsiCheckbox.checked = jitsiEnabled;
        }
        if (jitsiBadge) {
            jitsiBadge.style.display = jitsiEnabled ? 'inline-block' : 'none';
            jitsiBadge.style.backgroundColor = '#4CAF50';
            jitsiBadge.style.color = 'white';
            jitsiBadge.textContent = '● Enabled';
        }

        // Update Matrix status
        const matrixEnabled = integrations.matrix?.enabled || false;
        const matrixCheckbox = document.getElementById('quick-matrix-enabled');
        const matrixBadge = document.getElementById('matrix-status-badge');
        if (matrixCheckbox) {
            matrixCheckbox.checked = matrixEnabled;
        }
        if (matrixBadge) {
            matrixBadge.style.display = matrixEnabled ? 'inline-block' : 'none';
            matrixBadge.style.backgroundColor = '#9C27B0';
            matrixBadge.style.color = 'white';
            matrixBadge.textContent = '● Enabled';
        }

        // Update EspoCRM status
        const espocrmEnabled = integrations.espocrm?.enabled || false;
        const espocrmCheckbox = document.getElementById('quick-espocrm-enabled');
        const espocrmBadge = document.getElementById('espocrm-status-badge');
        if (espocrmCheckbox) {
            espocrmCheckbox.checked = espocrmEnabled;
        }
        if (espocrmBadge) {
            espocrmBadge.style.display = espocrmEnabled ? 'inline-block' : 'none';
            espocrmBadge.style.backgroundColor = '#2196F3';
            espocrmBadge.style.color = 'white';
            espocrmBadge.textContent = '● Enabled';
        }

    } catch (error) {
        console.error('Failed to load integration status:', error);
    }
}

/**
 * Quick toggle integration on/off
 */
async function quickToggleIntegration(integration) {
    const checkbox = document.getElementById(`quick-${integration}-enabled`);
    const isEnabled = checkbox.checked;

    if (isEnabled) {
        // Enable with default settings
        await quickSetupIntegration(integration);
    } else {
        // Disable integration
        await disableIntegration(integration);
    }
}

/**
 * Quick setup integration with default settings
 */
async function quickSetupIntegration(integration) {
    const defaults = {
        jitsi: {
            enabled: true,
            server_url: 'https://localhost',
            auto_create_rooms: true,
            app_id: '',
            app_secret: ''
        },
        matrix: {
            enabled: true,
            homeserver_url: 'https://localhost:8008',
            bot_username: '',
            bot_password: '${MATRIX_BOT_PASSWORD}',
            notification_room: '',
            voicemail_room: '',
            missed_call_notifications: true
        },
        espocrm: {
            enabled: true,
            api_url: 'https://localhost/api/v1',
            api_key: '${ESPOCRM_API_KEY}',
            auto_create_contacts: true,
            auto_log_calls: true,
            screen_pop: true
        }
    };

    const config = defaults[integration];

    if (!config) {
        showQuickSetupNotification(`Unknown integration: ${integration}`, 'error');
        return;
    }

    try {
        const response = await fetch('/api/config/section', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                section: 'integrations',
                data: {
                    [integration]: config
                }
            })
        });

        if (response.ok) {
            // Update the checkbox
            const checkbox = document.getElementById(`quick-${integration}-enabled`);
            if (checkbox) {
                checkbox.checked = true;
            }

            // Update status badge
            updateQuickSetupStatus();

            // Show success message
            const basePart = `✅ ${INTEGRATION_NAMES[integration]} enabled with default settings! The integration is now active.`;

            // Show additional info for specific integrations
            if (integration === 'matrix') {
                showQuickSetupNotification(`${basePart} Note: You need to set MATRIX_BOT_PASSWORD in your .env file for Matrix to work.`, 'warning', 8000);
            } else if (integration === 'espocrm') {
                showQuickSetupNotification(`${basePart} Note: You need to set ESPOCRM_API_KEY and api_url in the configuration tab.`, 'warning', 8000);
            } else {
                showQuickSetupNotification(basePart, 'success');
            }

            // Reload the detailed config if on that tab
            if (integration === 'jitsi') {
                loadJitsiConfig();
            } else if (integration === 'matrix') {
                loadMatrixConfig();
            } else if (integration === 'espocrm') {
                loadEspoCRMConfig();
            }
        } else {
            showQuickSetupNotification(`Failed to enable ${INTEGRATION_NAMES[integration]}`, 'error');
            // Revert checkbox
            const checkbox = document.getElementById(`quick-${integration}-enabled`);
            if (checkbox) {
                checkbox.checked = false;
            }
        }
    } catch (error) {
        showQuickSetupNotification(`Error enabling integration: ${error.message}`, 'error');
        // Revert checkbox
        const checkbox = document.getElementById(`quick-${integration}-enabled`);
        if (checkbox) {
            checkbox.checked = false;
        }
    }
}

/**
 * Disable an integration
 */
async function disableIntegration(integration) {
    try {
        // First, get current config
        const response = await fetch('/api/config');
        const data = await response.json();
        const currentConfig = data.integrations?.[integration] ?? {};

        // Set enabled to false
        currentConfig.enabled = false;

        // Update config
        const updateResponse = await fetch('/api/config/section', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                section: 'integrations',
                data: {
                    [integration]: currentConfig
                }
            })
        });

        if (updateResponse.ok) {
            // Update status
            updateQuickSetupStatus();

            showQuickSetupNotification(`${INTEGRATION_NAMES[integration]} has been disabled.`, 'info');

            // Reload the detailed config if on that tab
            if (integration === 'jitsi') {
                loadJitsiConfig();
            } else if (integration === 'matrix') {
                loadMatrixConfig();
            } else if (integration === 'espocrm') {
                loadEspoCRMConfig();
            }
        } else {
            showQuickSetupNotification(`Failed to disable ${INTEGRATION_NAMES[integration]}`, 'error');
            // Revert checkbox
            const checkbox = document.getElementById(`quick-${integration}-enabled`);
            if (checkbox) {
                checkbox.checked = true;
            }
        }
    } catch (error) {
        showQuickSetupNotification(`Error disabling integration: ${error.message}`, 'error');
        // Revert checkbox
        const checkbox = document.getElementById(`quick-${integration}-enabled`);
        if (checkbox) {
            checkbox.checked = true;
        }
    }
}

// =============================================================================
// Jitsi Meet Integration
// =============================================================================

async function loadJitsiConfig() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) {
            if (window.suppressErrorNotifications) {
                console.info('Config endpoint returned error:', response.status, '(feature may not be available or authentication required)');
            } else {
                console.error('Failed to load Jitsi config:', response.status);
            }
            return;
        }

        const data = await response.json();
        const config = data.integrations?.jitsi ?? {};

        document.getElementById('jitsi-enabled').checked = config.enabled ?? false;
        document.getElementById('jitsi-server-url').value = config.server_url ?? 'https://localhost';
        document.getElementById('jitsi-auto-create-rooms').checked = config.auto_create_rooms !== false;
        document.getElementById('jitsi-app-id').value = config.app_id ?? '';
        document.getElementById('jitsi-app-secret').value = config.app_secret ?? '';

        toggleJitsiSettings();
    } catch (error) {
        if (window.suppressErrorNotifications) {
            console.info('Failed to load Jitsi config (expected if not authenticated):', error.message);
        } else {
            console.error('Failed to load Jitsi config:', error);
        }
    }
}

function toggleJitsiSettings() {
    const enabled = document.getElementById('jitsi-enabled').checked;
    document.getElementById('jitsi-settings').style.display = enabled ? 'block' : 'none';
}

document.getElementById('jitsi-enabled')?.addEventListener('change', toggleJitsiSettings);

document.getElementById('jitsi-config-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();

    const config = {
        enabled: document.getElementById('jitsi-enabled').checked,
        server_url: document.getElementById('jitsi-server-url').value,
        auto_create_rooms: document.getElementById('jitsi-auto-create-rooms').checked,
        app_id: document.getElementById('jitsi-app-id').value,
        app_secret: document.getElementById('jitsi-app-secret').value
    };

    try {
        const response = await fetch('/api/config/section', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                section: 'integrations',
                data: { jitsi: config }
            })
        });

        if (response.ok) {
            showJitsiStatus('Configuration saved successfully!', 'success');
            updateQuickSetupStatus(); // Update quick setup checkboxes
        } else {
            showJitsiStatus('Failed to save configuration', 'error');
        }
    } catch (error) {
        showJitsiStatus('Error: ' + error.message, 'error');
    }
});

async function testJitsiConnection() {
    const serverUrl = document.getElementById('jitsi-server-url').value;

    showJitsiStatus(`Testing connection to ${escapeHtml(serverUrl)}...`, 'info');

    try {
        // Test if server is reachable
        const testUrl = `${serverUrl}/external_api.js`;
        const response = await fetch(testUrl, { mode: 'no-cors' });

        // If no error, server is likely reachable
        const testMeetingUrl = `${serverUrl}/test-pbx-${Date.now()}`;
        showJitsiStatus(
            `✅ Connection successful!<br>Test meeting URL: <a href="${escapeHtml(testMeetingUrl)}" target="_blank">${escapeHtml(testMeetingUrl)}</a>`,
            'success'
        );
    } catch (error) {
        showJitsiStatus(`⚠️ Could not verify connection. Server may still be accessible.<br>Error: ${escapeHtml(error.message)}`, 'warning');
    }
}

function showJitsiStatus(message, type) {
    const statusDiv = document.getElementById('jitsi-status');
    statusDiv.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
}

// =============================================================================
// Matrix Integration
// =============================================================================

async function loadMatrixConfig() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) {
            if (window.suppressErrorNotifications) {
                console.info('Config endpoint returned error:', response.status, '(feature may not be available or authentication required)');
            } else {
                console.error('Failed to load Matrix config:', response.status);
            }
            return;
        }

        const data = await response.json();
        const config = data.integrations?.matrix ?? {};

        document.getElementById('matrix-enabled').checked = config.enabled ?? false;
        document.getElementById('matrix-homeserver-url').value = config.homeserver_url ?? 'https://localhost:8008';
        document.getElementById('matrix-bot-username').value = config.bot_username ?? '';
        document.getElementById('matrix-bot-password').value = config.bot_password ?? '';
        document.getElementById('matrix-notification-room').value = config.notification_room ?? '';
        document.getElementById('matrix-voicemail-room').value = config.voicemail_room ?? '';
        document.getElementById('matrix-missed-call-notifications').checked = config.missed_call_notifications !== false;

        toggleMatrixSettings();
    } catch (error) {
        if (window.suppressErrorNotifications) {
            console.info('Failed to load Matrix config (expected if not authenticated):', error.message);
        } else {
            console.error('Failed to load Matrix config:', error);
        }
    }
}

function toggleMatrixSettings() {
    const enabled = document.getElementById('matrix-enabled').checked;
    document.getElementById('matrix-settings').style.display = enabled ? 'block' : 'none';
}

document.getElementById('matrix-enabled')?.addEventListener('change', toggleMatrixSettings);

document.getElementById('matrix-config-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();

    const config = {
        enabled: document.getElementById('matrix-enabled').checked,
        homeserver_url: document.getElementById('matrix-homeserver-url').value,
        bot_username: document.getElementById('matrix-bot-username').value,
        bot_password: document.getElementById('matrix-bot-password').value,
        notification_room: document.getElementById('matrix-notification-room').value,
        voicemail_room: document.getElementById('matrix-voicemail-room').value,
        missed_call_notifications: document.getElementById('matrix-missed-call-notifications').checked
    };

    try {
        const response = await fetch('/api/config/section', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                section: 'integrations',
                data: { matrix: config }
            })
        });

        if (response.ok) {
            showMatrixStatus('Configuration saved successfully!', 'success');
            updateQuickSetupStatus(); // Update quick setup checkboxes
        } else {
            showMatrixStatus('Failed to save configuration', 'error');
        }
    } catch (error) {
        showMatrixStatus('Error: ' + error.message, 'error');
    }
});

async function testMatrixConnection() {
    const homeserverUrl = document.getElementById('matrix-homeserver-url').value;
    const username = document.getElementById('matrix-bot-username').value;
    const password = document.getElementById('matrix-bot-password').value;

    if (!username || !password) {
        showMatrixStatus('Please enter bot username and password', 'error');
        return;
    }

    showMatrixStatus('Testing Matrix connection...', 'info');

    try {
        // Test homeserver connectivity
        const versionUrl = `${homeserverUrl}/_matrix/client/versions`;
        const versionResponse = await fetch(versionUrl);

        if (!versionResponse.ok) {
            throw new Error('Homeserver not accessible');
        }

        const versions = await versionResponse.json();
        const versionList = versions.versions?.join(', ') ?? 'Unknown';

        showMatrixStatus(
            `✅ Homeserver is accessible!<br>Supported versions: ${versionList}<br><small>Note: Full authentication test requires server-side validation</small>`,
            'success'
        );
    } catch (error) {
        showMatrixStatus(`❌ Connection failed: ${error.message}`, 'error');
    }
}

function showMatrixStatus(message, type) {
    const statusDiv = document.getElementById('matrix-status');
    statusDiv.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
}

// =============================================================================
// EspoCRM Integration
// =============================================================================

async function loadEspoCRMConfig() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) {
            if (window.suppressErrorNotifications) {
                console.info('Config endpoint returned error:', response.status, '(feature may not be available or authentication required)');
            } else {
                console.error('Failed to load EspoCRM config:', response.status);
            }
            return;
        }

        const data = await response.json();
        const config = data.integrations?.espocrm ?? {};

        document.getElementById('espocrm-enabled').checked = config.enabled ?? false;
        document.getElementById('espocrm-api-url').value = config.api_url ?? 'https://localhost/api/v1';
        document.getElementById('espocrm-api-key').value = config.api_key ?? '';
        document.getElementById('espocrm-auto-create-contacts').checked = config.auto_create_contacts !== false;
        document.getElementById('espocrm-auto-log-calls').checked = config.auto_log_calls !== false;
        document.getElementById('espocrm-screen-pop').checked = config.screen_pop !== false;

        toggleEspoCRMSettings();
    } catch (error) {
        if (window.suppressErrorNotifications) {
            console.info('Failed to load EspoCRM config (expected if not authenticated):', error.message);
        } else {
            console.error('Failed to load EspoCRM config:', error);
        }
    }
}

function toggleEspoCRMSettings() {
    const enabled = document.getElementById('espocrm-enabled').checked;
    document.getElementById('espocrm-settings').style.display = enabled ? 'block' : 'none';
}

document.getElementById('espocrm-enabled')?.addEventListener('change', toggleEspoCRMSettings);

document.getElementById('espocrm-config-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();

    const config = {
        enabled: document.getElementById('espocrm-enabled').checked,
        api_url: document.getElementById('espocrm-api-url').value,
        api_key: document.getElementById('espocrm-api-key').value,
        auto_create_contacts: document.getElementById('espocrm-auto-create-contacts').checked,
        auto_log_calls: document.getElementById('espocrm-auto-log-calls').checked,
        screen_pop: document.getElementById('espocrm-screen-pop').checked
    };

    try {
        const response = await fetch('/api/config/section', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                section: 'integrations',
                data: { espocrm: config }
            })
        });

        if (response.ok) {
            showEspoCRMStatus('Configuration saved successfully!', 'success');
            updateQuickSetupStatus(); // Update quick setup checkboxes
        } else {
            showEspoCRMStatus('Failed to save configuration', 'error');
        }
    } catch (error) {
        showEspoCRMStatus('Error: ' + error.message, 'error');
    }
});

async function testEspoCRMConnection() {
    const apiUrl = document.getElementById('espocrm-api-url').value;
    const apiKey = document.getElementById('espocrm-api-key').value;

    if (!apiUrl || !apiKey) {
        showEspoCRMStatus('Please enter API URL and API Key', 'error');
        return;
    }

    showEspoCRMStatus('Testing EspoCRM connection...', 'info');

    try {
        // Test API endpoint
        const testUrl = apiUrl + '/App/user';
        const response = await fetch(testUrl, {
            headers: {
                'X-Api-Key': apiKey,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            showEspoCRMStatus(
                '✅ Connection successful!<br>' +
                'Connected as: ' + (data.userName || 'Unknown') + '<br>' +
                'EspoCRM is ready for integration.',
                'success'
            );
        } else {
            throw new Error('API returned status ' + response.status);
        }
    } catch (error) {
        showEspoCRMStatus('❌ Connection failed: ' + error.message + '<br>Check API URL and API Key.', 'error');
    }
}

function showEspoCRMStatus(message, type) {
    const statusDiv = document.getElementById('espocrm-status');
    statusDiv.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
}

// =============================================================================
// Helper function for tab switching
// =============================================================================

function showTab(tabId) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active from all buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    const selectedTab = document.getElementById(tabId);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }

    // Activate button
    const selectedButton = document.querySelector(`[data-tab="${tabId}"]`);
    if (selectedButton) {
        selectedButton.classList.add('active');
    }

    // Initialize if it's an open source integration tab
    if (tabId.includes('integration') || tabId === 'opensource-integrations') {
        initializeOpenSourceIntegrations();
    }
}

// =============================================================================
// Jitsi Interactive Functions
// =============================================================================

/**
 * Create an instant Jitsi meeting
 */
async function createInstantJitsiMeeting() {
    const roomName = document.getElementById('jitsi-instant-room').value || '';

    try {
        const response = await fetch('/api/integrations/jitsi/instant', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                room_name: roomName,
                extension: 'admin'  // Current user extension
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to create meeting');
        }

        const data = await response.json();
        displayJitsiMeetingResult(data.meeting_url);
        showQuickSetupNotification('Meeting created successfully!', 'success');
    } catch (error) {
        showQuickSetupNotification('Failed to create meeting: ' + error.message, 'error');
    }
}

/**
 * Schedule a Jitsi meeting
 */
async function scheduleJitsiMeeting() {
    const subject = document.getElementById('jitsi-schedule-subject').value;
    const duration = document.getElementById('jitsi-schedule-duration').value;

    if (!subject) {
        showQuickSetupNotification('Please enter a meeting subject', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/integrations/jitsi/meetings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                subject: subject,
                duration: parseInt(duration),
                moderator_name: 'Admin'
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to schedule meeting');
        }

        const data = await response.json();
        displayJitsiMeetingResult(data.meeting_url);
        showQuickSetupNotification('Meeting scheduled successfully!', 'success');
    } catch (error) {
        showQuickSetupNotification('Failed to schedule meeting: ' + error.message, 'error');
    }
}

/**
 * Display Jitsi meeting result
 */
function displayJitsiMeetingResult(url) {
    const resultDiv = document.getElementById('jitsi-meeting-result');
    const urlInput = document.getElementById('jitsi-meeting-url');

    urlInput.value = url;
    resultDiv.style.display = 'block';
}

/**
 * Copy Jitsi meeting URL to clipboard
 */
async function copyJitsiMeetingUrl() {
    const urlInput = document.getElementById('jitsi-meeting-url');
    const url = urlInput.value;

    try {
        // Use modern Clipboard API
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(url);
            showQuickSetupNotification('Meeting URL copied to clipboard!', 'success', 3000);
        } else {
            // Fallback for older browsers
            urlInput.select();
            document.execCommand('copy');
            showQuickSetupNotification('Meeting URL copied to clipboard!', 'success', 3000);
        }
    } catch (error) {
        // Fallback for errors
        urlInput.select();
        document.execCommand('copy');
        showQuickSetupNotification('Meeting URL copied to clipboard!', 'success', 3000);
    }
}

/**
 * Open Jitsi meeting in new tab
 */
function openJitsiMeeting() {
    const url = document.getElementById('jitsi-meeting-url').value;
    if (url) {
        window.open(url, '_blank');
    }
}

// =============================================================================
// Matrix Interactive Functions
// =============================================================================

/**
 * Handle Matrix room selection change
 */
document.addEventListener('DOMContentLoaded', function() {
    const roomSelect = document.getElementById('matrix-room-select');
    if (roomSelect) {
        roomSelect.addEventListener('change', function() {
            const customRoom = document.getElementById('matrix-custom-room');
            if (this.value === 'custom') {
                customRoom.style.display = 'block';
            } else {
                customRoom.style.display = 'none';
            }
        });
    }
});

/**
 * Send a message to a Matrix room
 */
async function sendMatrixMessage() {
    const roomSelect = document.getElementById('matrix-room-select').value;
    const customRoomId = document.getElementById('matrix-custom-room-id').value;
    const message = document.getElementById('matrix-message-text').value;

    if (!message) {
        showQuickSetupNotification('Please enter a message', 'warning');
        return;
    }

    // Determine which room to use
    let roomId = null;
    if (roomSelect === 'custom') {
        roomId = customRoomId;
        if (!roomId) {
            showQuickSetupNotification('Please enter a custom room ID', 'warning');
            return;
        }
    } else if (roomSelect === 'notification' || roomSelect === 'voicemail') {
        // Room ID will be determined by the backend based on config
        roomId = null; // Backend will use configured room
    }

    try {
        const response = await fetch('/api/integrations/matrix/messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                room_id: roomId,
                message: message,
                msg_type: 'm.text'
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to send message');
        }

        const data = await response.json();
        showMatrixMessageResult('✅ Message sent successfully!', 'success');
        document.getElementById('matrix-message-text').value = ''; // Clear message
    } catch (error) {
        showMatrixMessageResult('❌ Failed to send message: ' + error.message, 'error');
    }
}

/**
 * Send a test notification to Matrix
 */
async function sendMatrixTestNotification() {
    try {
        const response = await fetch('/api/integrations/matrix/notifications', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: '🧪 Test notification from PBX Admin Panel - ' + new Date().toLocaleString()
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to send notification');
        }

        showMatrixMessageResult('✅ Test notification sent successfully!', 'success');
    } catch (error) {
        showMatrixMessageResult('❌ Failed to send notification: ' + error.message, 'error');
    }
}

/**
 * Create a new Matrix room
 */
async function createMatrixRoom() {
    const roomName = document.getElementById('matrix-new-room-name').value;
    const roomTopic = document.getElementById('matrix-new-room-topic').value;

    if (!roomName) {
        showQuickSetupNotification('Please enter a room name', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/integrations/matrix/rooms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: roomName,
                topic: roomTopic
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to create room');
        }

        const data = await response.json();
        showMatrixRoomResult(data.room_id);
        showQuickSetupNotification('Room created successfully!', 'success');

        // Clear form
        document.getElementById('matrix-new-room-name').value = '';
        document.getElementById('matrix-new-room-topic').value = '';
    } catch (error) {
        showQuickSetupNotification('Failed to create room: ' + error.message, 'error');
    }
}

/**
 * Show Matrix message result
 */
function showMatrixMessageResult(message, type) {
    const resultDiv = document.getElementById('matrix-message-result');
    const textEl = document.getElementById('matrix-message-result-text');

    textEl.innerHTML = message;
    resultDiv.style.display = 'block';
    resultDiv.querySelector('.info-box').style.backgroundColor =
        type === 'success' ? '#e8f5e9' : '#ffebee';

    // Auto-hide after 5 seconds
    setTimeout(() => {
        resultDiv.style.display = 'none';
    }, 5000);
}

/**
 * Show Matrix room creation result
 */
function showMatrixRoomResult(roomId) {
    const resultDiv = document.getElementById('matrix-room-result');
    const roomIdEl = document.getElementById('matrix-new-room-id');

    roomIdEl.textContent = roomId;
    resultDiv.style.display = 'block';
}

// =============================================================================
// EspoCRM Interactive Functions
// =============================================================================

/**
 * Search for a contact in EspoCRM
 */
async function searchEspoCRMContact() {
    const searchType = document.getElementById('espocrm-search-type').value;
    const searchTerm = document.getElementById('espocrm-search-term').value;

    if (!searchTerm) {
        showQuickSetupNotification('Please enter a search term', 'warning');
        return;
    }

    try {
        // Build query parameter based on search type
        const queryParam = searchType === 'phone' ? 'phone' :
                          searchType === 'email' ? 'email' :
                          'name';

        const response = await fetch(`/api/integrations/espocrm/contacts/search?${queryParam}=${encodeURIComponent(searchTerm)}`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to search contact');
        }

        const data = await response.json();
        displayEspoCRMSearchResults(data);
    } catch (error) {
        showQuickSetupNotification('Failed to search contact: ' + error.message, 'error');
    }
}

/**
 * Display EspoCRM search results
 */
function displayEspoCRMSearchResults(data) {
    const resultsDiv = document.getElementById('espocrm-search-results');
    const detailsDiv = document.getElementById('espocrm-contact-details');

    if (!data.success || !data.contact) {
        detailsDiv.innerHTML = '<div class="info-box" style="background-color: #fff3e0;">No contact found</div>';
        resultsDiv.style.display = 'block';
        return;
    }

    const contact = data.contact;
    let html = '<div class="info-box" style="background-color: #e8f5e9;">';
    html += '<h4>✅ Contact Found</h4>';
    html += '<table style="width: 100%; margin-top: 10px;">';

    if (contact.name) html += `<tr><td><strong>Name:</strong></td><td>${escapeHtml(contact.name)}</td></tr>`;
    if (contact.email) html += `<tr><td><strong>Email:</strong></td><td>${escapeHtml(contact.email)}</td></tr>`;
    if (contact.phone) html += `<tr><td><strong>Phone:</strong></td><td>${escapeHtml(contact.phone)}</td></tr>`;
    if (contact.company) html += `<tr><td><strong>Company:</strong></td><td>${escapeHtml(contact.company)}</td></tr>`;
    if (contact.title) html += `<tr><td><strong>Title:</strong></td><td>${escapeHtml(contact.title)}</td></tr>`;
    if (contact.id) html += `<tr><td><strong>CRM ID:</strong></td><td>${escapeHtml(contact.id)}</td></tr>`;

    html += '</table></div>';

    detailsDiv.innerHTML = html;
    resultsDiv.style.display = 'block';
}

/**
 * Create a new contact in EspoCRM
 */
async function createEspoCRMContact() {
    const firstName = document.getElementById('espocrm-new-firstname').value;
    const lastName = document.getElementById('espocrm-new-lastname').value;
    const phone = document.getElementById('espocrm-new-phone').value;
    const email = document.getElementById('espocrm-new-email').value;
    const company = document.getElementById('espocrm-new-company').value;
    const title = document.getElementById('espocrm-new-title').value;

    if (!firstName || !lastName) {
        showQuickSetupNotification('Please enter first and last name', 'warning');
        return;
    }

    if (!phone && !email) {
        showQuickSetupNotification('Please enter at least phone or email', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/integrations/espocrm/contacts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: `${firstName} ${lastName}`,
                phone: phone,
                email: email,
                company: company,
                title: title
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to create contact');
        }

        const data = await response.json();
        showEspoCRMCreateResult('✅ Contact created successfully! CRM ID: ' + (data.contact?.id || 'unknown'));

        // Clear form
        document.getElementById('espocrm-new-firstname').value = '';
        document.getElementById('espocrm-new-lastname').value = '';
        document.getElementById('espocrm-new-phone').value = '';
        document.getElementById('espocrm-new-email').value = '';
        document.getElementById('espocrm-new-company').value = '';
        document.getElementById('espocrm-new-title').value = '';
    } catch (error) {
        showEspoCRMCreateResult('❌ Failed to create contact: ' + error.message);
    }
}

/**
 * Show EspoCRM create contact result
 */
function showEspoCRMCreateResult(message) {
    const resultDiv = document.getElementById('espocrm-create-result');
    const textEl = document.getElementById('espocrm-create-result-text');

    textEl.innerHTML = message;
    resultDiv.style.display = 'block';

    // Auto-hide after 5 seconds
    setTimeout(() => {
        resultDiv.style.display = 'none';
    }, 5000);
}
