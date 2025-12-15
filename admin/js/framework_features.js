/**
 * Framework Features UI Module
 * Handles UI for framework features in admin panel
 */

// Framework Overview Tab
function loadFrameworkOverview() {
    const content = `
        <h2>🎯 Framework Features Overview</h2>
        <div class="info-box">
            <p>Welcome to the Framework Features section. These are advanced features that provide frameworks for future enhancements.</p>
            <p>All configurations are stored in the PostgreSQL database and can be managed through this admin panel.</p>
        </div>

        <div class="info-box" style="margin-bottom: 20px; background: #e8f5e9; border-left: 4px solid #4caf50;">
            <h3 style="margin-top: 0;">📊 Implementation Status Legend</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px;">
                <div><span class="status-badge status-fully-implemented">✅ Fully Implemented</span> - Ready for production use</div>
                <div><span class="status-badge status-framework-only">⚙️ Framework Only</span> - Database & APIs ready, needs integration</div>
                <div><span class="status-badge status-integration-required">🔌 Integration Required</span> - Requires external service setup</div>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">📲</div>
                <h3>Click-to-Dial</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-fully-implemented">✅ Fully Implemented</span>
                </div>
                <p>Web-based dialing from browser or CRM with PBX integration</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ Database schema ✓ REST APIs ✓ PBX integration ✓ Call history</small>
                <button onclick="switchTab('click-to-dial')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📹</div>
                <h3>Video Conferencing</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                </div>
                <p>HD/4K video calls with screen sharing</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ Database schema ✓ REST APIs ⚠ Video handled by Zoom/Teams</small>
                <button onclick="switchTab('video-conferencing')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">💬</div>
                <h3>Team Messaging</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                </div>
                <p>Built-in chat and collaboration</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ Database schema ✓ REST APIs ⚠ UI frontend needed</small>
                <button onclick="switchTab('team-messaging')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📍</div>
                <h3>Nomadic E911</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-fully-implemented">✅ Fully Implemented</span>
                </div>
                <p>Location-based emergency routing</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ IP-based location detection ✓ Multi-site support ✓ Location history ✓ Manual updates</small>
                <button onclick="switchTab('nomadic-e911')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🔗</div>
                <h3>CRM Integrations</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-fully-implemented">✅ Fully Implemented</span>
                </div>
                <p>HubSpot and Zendesk connectivity</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ Contact sync ✓ Deal creation ✓ Ticket management ✓ Activity logging ✓ API integration</small>
                <button onclick="switchTab('crm-integrations')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">✅</div>
                <h3>Compliance</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-fully-implemented">✅ SOC 2 Type II</span>
                </div>
                <p>Security and compliance controls</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ SOC 2 controls ✓ Audit logging ✓ Test evidence ⚠ GDPR/PCI DSS disabled</small>
                <button onclick="switchTab('compliance')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🎙️</div>
                <h3>Speech Analytics</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-fully-implemented">✅ Fully Implemented</span>
                </div>
                <p>Real-time transcription and sentiment</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ Vosk offline transcription ✓ Sentiment analysis ✓ Call summarization ✓ Production ready</small>
                <button onclick="switchTab('speech-analytics')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
        </div>

        <div class="section-card" style="margin-top: 20px;">
            <h3>📋 Implementation Summary</h3>
            <p>All framework features include:</p>
            <ul>
                <li>✅ <strong>Database Schema:</strong> PostgreSQL tables with full CRUD operations</li>
                <li>✅ <strong>REST API Endpoints:</strong> 40+ endpoints for configuration and management</li>
                <li>✅ <strong>Python Backend:</strong> Feature classes with error handling and logging</li>
                <li>✅ <strong>Admin Panel UI:</strong> Configuration interfaces and dashboards</li>
            </ul>
        </div>

        <div class="section-card" style="margin-top: 20px;">
            <h3>🔌 External Service Integration Examples</h3>
            <p>Framework features support integration with external services:</p>
            <ul>
                <li><strong>Speech Analytics:</strong> ✅ Vosk offline (included), optional: Google Speech-to-Text, Azure, OpenAI Whisper, AWS Transcribe</li>
                <li><strong>CRM Integration:</strong> ✅ HubSpot Contacts/Deals API (fully operational), ✅ Zendesk Tickets API (fully operational)</li>
                <li><strong>Video Conferencing:</strong> WebRTC infrastructure, H.264/H.265 codecs, STUN/TURN servers (requires external video service)</li>
                <li><strong>Compliance:</strong> ✅ SOC 2 Type 2 audit logging and security controls (fully operational)</li>
                <li><strong>Nomadic E911:</strong> ✅ IP-based location detection (fully operational), optional: GPS integration</li>
            </ul>
        </div>

        <div class="info-box" style="margin-top: 20px; background: #fff3cd; border-left: 4px solid #ff9800;">
            <h3 style="margin-top: 0;">⚠️ Next Steps for Framework Features</h3>
            <p>To activate framework features for production use:</p>
            <ol>
                <li><strong>Click-to-Dial:</strong> Already fully operational - configure extensions in the tab</li>
                <li><strong>SOC 2 Compliance:</strong> Already fully operational - review controls in the tab</li>
                <li><strong>Speech Analytics:</strong> Already fully operational - configure Vosk transcription settings</li>
                <li><strong>CRM Integrations:</strong> Already fully operational - configure HubSpot/Zendesk API credentials</li>
                <li><strong>Nomadic E911:</strong> Already fully operational - configure sites and IP ranges for location detection</li>
                <li><strong>Video Conferencing:</strong> Create rooms and integrate with external video service (Zoom/Teams)</li>
                <li><strong>Team Messaging:</strong> Build or integrate a frontend UI for messaging</li>
            </ol>
        </div>
    `;
    return content;
}

// Click-to-Dial Tab
function loadClickToDialTab() {
    const content = `
        <h2>📲 Click-to-Dial Configuration</h2>
        <div class="info-box" style="background: #e8f5e9; border-left: 4px solid #4caf50;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-fully-implemented">✅ Fully Implemented</span>
                <strong>Production Ready</strong>
            </div>
            <p>Click-to-Dial is fully implemented with PBX integration. Users can initiate calls from web browsers, CRM systems, or mobile apps.</p>
            <p><strong>Features:</strong> Auto-answer, browser notifications, call history tracking, WebRTC integration</p>
        </div>

        <div class="section-card">
            <h3>Extension Configurations</h3>
            <div id="click-to-dial-configs-list">Loading...</div>
        </div>

        <div class="section-card">
            <h3>Call History</h3>
            <div id="click-to-dial-history">
                <p>Select an extension to view call history</p>
            </div>
        </div>
    `;
    
    // Load configurations
    setTimeout(() => {
        fetch('/api/framework/click-to-dial/configs')
            .then(r => r.json())
            .then(data => {
                displayClickToDialConfigs(data.configs || []);
            })
            .catch(err => {
                document.getElementById('click-to-dial-configs-list').innerHTML = 
                    `<div class="error-box">Error loading configurations: ${err.message}</div>`;
            });
    }, 100);
    
    return content;
}

function displayClickToDialConfigs(configs) {
    const container = document.getElementById('click-to-dial-configs-list');
    
    if (configs.length === 0) {
        container.innerHTML = '<p>No configurations found. Configurations are created automatically when extensions use click-to-dial.</p>';
        return;
    }
    
    const html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Extension</th>
                    <th>Enabled</th>
                    <th>Auto Answer</th>
                    <th>Browser Notifications</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${configs.map(config => `
                    <tr>
                        <td>${config.extension}</td>
                        <td>${config.enabled ? '✅ Yes' : '❌ No'}</td>
                        <td>${config.auto_answer ? '✅ Yes' : '❌ No'}</td>
                        <td>${config.browser_notification ? '✅ Yes' : '❌ No'}</td>
                        <td>
                            <button onclick="viewClickToDialHistory('${config.extension}')" class="btn-secondary btn-sm">View History</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

function viewClickToDialHistory(extension) {
    fetch(`/api/framework/click-to-dial/history/${extension}`)
        .then(r => r.json())
        .then(data => {
            const history = data.history || [];
            const container = document.getElementById('click-to-dial-history');
            
            if (history.length === 0) {
                container.innerHTML = `<p>No call history for extension ${extension}</p>`;
                return;
            }
            
            const html = `
                <h4>Call History for Extension ${extension}</h4>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Destination</th>
                            <th>Source</th>
                            <th>Status</th>
                            <th>Initiated</th>
                            <th>Connected</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${history.map(call => `
                            <tr>
                                <td>${call.destination}</td>
                                <td>${call.source}</td>
                                <td><span class="status-badge status-${call.status}">${call.status}</span></td>
                                <td>${new Date(call.initiated_at).toLocaleString()}</td>
                                <td>${call.connected_at ? new Date(call.connected_at).toLocaleString() : '-'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
            
            container.innerHTML = html;
        })
        .catch(err => {
            document.getElementById('click-to-dial-history').innerHTML = 
                `<div class="error-box">Error loading history: ${err.message}</div>`;
        });
}

// Video Conferencing Tab
function loadVideoConferencingTab() {
    const content = `
        <h2>📹 Video Conferencing</h2>
        <div class="info-box" style="background: #fff3cd; border-left: 4px solid #ff9800;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                <strong>Database & APIs Ready</strong>
            </div>
            <p>Video conferencing framework with support for HD/4K video calls and screen sharing.</p>
            <p><strong>Note:</strong> This framework provides database tracking only. Video conferencing is typically handled by external services like Zoom, Microsoft Teams, or custom WebRTC implementation.</p>
            <p><strong>Available:</strong> Room management, participant tracking, configuration storage</p>
        </div>

        <div class="section-card">
            <h3>Conference Rooms</h3>
            <button onclick="showCreateRoomDialog()" class="btn-primary">+ Create Room</button>
            <div id="video-rooms-list" style="margin-top: 15px;">Loading...</div>
        </div>

        <div id="create-room-dialog" style="display: none;" class="modal-overlay">
            <div class="modal-content">
                <h3>Create Video Conference Room</h3>
                <form id="create-room-form">
                    <div class="form-group">
                        <label>Room Name:</label>
                        <input type="text" name="room_name" required class="form-control">
                    </div>
                    <div class="form-group">
                        <label>Owner Extension:</label>
                        <input type="text" name="owner_extension" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>Max Participants:</label>
                        <input type="number" name="max_participants" value="10" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="enable_4k"> Enable 4K Video
                        </label>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="enable_screen_share" checked> Enable Screen Sharing
                        </label>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="recording_enabled"> Enable Recording
                        </label>
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn-primary">Create Room</button>
                        <button type="button" onclick="hideCreateRoomDialog()" class="btn-secondary">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    // Load rooms
    setTimeout(() => {
        loadVideoRooms();
    }, 100);
    
    return content;
}

function loadVideoRooms() {
    fetch('/api/framework/video-conference/rooms')
        .then(r => r.json())
        .then(data => {
            displayVideoRooms(data.rooms || []);
        })
        .catch(err => {
            document.getElementById('video-rooms-list').innerHTML = 
                `<div class="error-box">Error loading rooms: ${err.message}</div>`;
        });
}

function displayVideoRooms(rooms) {
    const container = document.getElementById('video-rooms-list');
    
    if (rooms.length === 0) {
        container.innerHTML = '<p>No conference rooms created yet.</p>';
        return;
    }
    
    const html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Room Name</th>
                    <th>Owner</th>
                    <th>Max Participants</th>
                    <th>4K Enabled</th>
                    <th>Screen Share</th>
                    <th>Recording</th>
                    <th>Created</th>
                </tr>
            </thead>
            <tbody>
                ${rooms.map(room => `
                    <tr>
                        <td>${room.room_name}</td>
                        <td>${room.owner_extension || '-'}</td>
                        <td>${room.max_participants}</td>
                        <td>${room.enable_4k ? '✅' : '❌'}</td>
                        <td>${room.enable_screen_share ? '✅' : '❌'}</td>
                        <td>${room.recording_enabled ? '✅' : '❌'}</td>
                        <td>${new Date(room.created_at).toLocaleDateString()}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

function showCreateRoomDialog() {
    document.getElementById('create-room-dialog').style.display = 'flex';
    
    // Setup form submission
    document.getElementById('create-room-form').onsubmit = function(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const data = {
            room_name: formData.get('room_name'),
            owner_extension: formData.get('owner_extension'),
            max_participants: parseInt(formData.get('max_participants')),
            enable_4k: formData.get('enable_4k') === 'on',
            enable_screen_share: formData.get('enable_screen_share') === 'on',
            recording_enabled: formData.get('recording_enabled') === 'on'
        };
        
        fetch('/api/framework/video-conference/create-room', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        })
        .then(r => r.json())
        .then(result => {
            if (result.success) {
                alert('Room created successfully!');
                hideCreateRoomDialog();
                loadVideoRooms();
            } else {
                alert('Error creating room: ' + (result.error || 'Unknown error'));
            }
        })
        .catch(err => {
            alert('Error creating room: ' + err.message);
        });
    };
}

function hideCreateRoomDialog() {
    document.getElementById('create-room-dialog').style.display = 'none';
}

// Add more framework feature tab loaders...
// (Team Messaging, Nomadic E911, CRM Integrations, Compliance, Speech Analytics)

// Export functions for use in main admin.js
window.frameworkFeatures = {
    loadFrameworkOverview,
    loadClickToDialTab,
    loadVideoConferencingTab,
    viewClickToDialHistory
};
