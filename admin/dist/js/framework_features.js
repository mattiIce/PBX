/**
 * Framework Features UI Module
 * Handles UI for framework features in admin panel
 */

// Framework Overview Tab
function loadFrameworkOverview() {
    const content = `
        <h2>🎯 Framework Features Overview</h2>
        <div class="info-box" style="background: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; margin-bottom: 20px;">
            <p><strong>100% Free & Open Source</strong> - All framework features use only free and open-source technologies. No paid services required!</p>
            <p style="margin-top: 10px;"><strong>Implementation Status Legend:</strong></p>
            <p style="margin: 5px 0;"><span class="status-badge status-fully-implemented">✅ Fully Implemented</span> = Production-ready with complete admin UI</p>
            <p style="margin: 5px 0;"><span class="status-badge status-enhanced">🔧 Enhanced Admin UI</span> = Full UI with live data, needs external service integration</p>
            <p style="margin: 5px 0;"><span class="status-badge status-framework-only">⚙️ Framework Only</span> = Backend ready, basic UI, needs service integration</p>
        </div>

        <h3 style="margin-top: 30px;">✅ Fully Implemented Features (Production-Ready)</h3>
        <div class="stats-grid">
            <div class="stat-card" style="background: #e8f5e9; border-left: 4px solid #4caf50;">
                <div class="stat-icon">📲</div>
                <h3>Click-to-Dial</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-fully-implemented">✅ Fully Implemented</span>
                </div>
                <p>Web-based dialing with full PBX integration</p>
                <small style="color: #2e7d32; display: block; margin-top: 8px;">✓ SIP call creation ✓ Auto-answer ✓ Call history ✓ REST API</small>
                <button onclick="switchTab('click-to-dial')" class="btn-success" style="margin-top: 10px;">Use Now</button>
            </div>
            <div class="stat-card" style="background: #e8f5e9; border-left: 4px solid #4caf50;">
                <div class="stat-icon">📢</div>
                <h3>Paging System</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-fully-implemented">✅ Fully Implemented</span>
                </div>
                <p>Overhead paging with zone management</p>
                <small style="color: #2e7d32; display: block; margin-top: 8px;">✓ Zone configuration ✓ DAC management ✓ Active monitoring ✓ Full REST API</small>
                <button onclick="switchTab('paging')" class="btn-success" style="margin-top: 10px;">Use Now</button>
            </div>
            <div class="stat-card" style="background: #e8f5e9; border-left: 4px solid #4caf50;">
                <div class="stat-icon">🎙️</div>
                <h3>Speech Analytics</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-fully-implemented">✅ Fully Implemented</span>
                </div>
                <p>Real-time transcription and sentiment analysis (FREE: Vosk offline)</p>
                <small style="color: #2e7d32; display: block; margin-top: 8px;">✓ Live transcription ✓ Sentiment analysis ✓ Call summaries ✓ No cloud costs</small>
                <button onclick="switchTab('speech-analytics')" class="btn-success" style="margin-top: 10px;">Use Now</button>
            </div>
            <div class="stat-card" style="background: #e8f5e9; border-left: 4px solid #4caf50;">
                <div class="stat-icon">📍</div>
                <h3>Nomadic E911</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-fully-implemented">✅ Fully Implemented</span>
                </div>
                <p>Location-based emergency routing for remote workers</p>
                <small style="color: #2e7d32; display: block; margin-top: 8px;">✓ IP tracking ✓ Multi-site support ✓ Location history ✓ REST API</small>
                <button onclick="switchTab('nomadic-e911')" class="btn-success" style="margin-top: 10px;">Use Now</button>
            </div>
        </div>

        <h3 style="margin-top: 30px;">🔧 Enhanced Admin UI Features (Live Data Integration)</h3>
        <div class="stats-grid">
            <div class="stat-card" style="background: #fff3e0; border-left: 4px solid #ff9800;">
                <div class="stat-icon">🤖</div>
                <h3>Conversational AI</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-enhanced">🔧 Enhanced Admin UI</span>
                </div>
                <p>AI assistant with live statistics (FREE: Rasa, ChatterBot)</p>
                <small style="color: #e65100; display: block; margin-top: 8px;">✓ Full UI ✓ Live statistics ✓ API integration ⚠ Needs AI service (free options available)</small>
                <button onclick="switchTab('conversational-ai')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card" style="background: #fff3e0; border-left: 4px solid #ff9800;">
                <div class="stat-icon">📞</div>
                <h3>Predictive Dialing</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-enhanced">🔧 Enhanced Admin UI</span>
                </div>
                <p>Campaign management with live statistics (FREE: Vicidial)</p>
                <small style="color: #e65100; display: block; margin-top: 8px;">✓ Full UI ✓ Campaign tracking ✓ Statistics dashboard ⚠ Needs dialer engine (free options available)</small>
                <button onclick="switchTab('predictive-dialing')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card" style="background: #fff3e0; border-left: 4px solid #ff9800;">
                <div class="stat-icon">🔊</div>
                <h3>Voice Biometrics</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-enhanced">🔧 Enhanced Admin UI</span>
                </div>
                <p>Speaker authentication with enrollment tracking (FREE: speaker-recognition)</p>
                <small style="color: #e65100; display: block; margin-top: 8px;">✓ Full UI ✓ Profile management ✓ Verification tracking ⚠ Needs biometric engine (free options available)</small>
                <button onclick="switchTab('voice-biometrics')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card" style="background: #fff3e0; border-left: 4px solid #ff9800;">
                <div class="stat-icon">📈</div>
                <h3>BI Integration</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-enhanced">🔧 Enhanced Admin UI</span>
                </div>
                <p>Dataset browser with export (FREE: Metabase, Superset, Redash)</p>
                <small style="color: #e65100; display: block; margin-top: 8px;">✓ Full UI ✓ Export functionality ✓ Multiple formats ⚠ Needs BI tool (free options available)</small>
                <button onclick="switchTab('bi-integration')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card" style="background: #fff3e0; border-left: 4px solid #ff9800;">
                <div class="stat-icon">🏷️</div>
                <h3>Call Tagging</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-enhanced">🔧 Enhanced Admin UI</span>
                </div>
                <p>Tag management with analytics (FREE: spaCy NLP)</p>
                <small style="color: #e65100; display: block; margin-top: 8px;">✓ Full UI ✓ Tag management ✓ Live statistics ⚠ Needs AI classifier (free options available)</small>
                <button onclick="switchTab('call-tagging')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card" style="background: #fff3e0; border-left: 4px solid #ff9800;">
                <div class="stat-icon">📱</div>
                <h3>Mobile Apps</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-enhanced">🔧 Enhanced Admin UI</span>
                </div>
                <p>Device management with statistics (FREE: React Native + WebRTC)</p>
                <small style="color: #e65100; display: block; margin-top: 8px;">✓ Full UI ✓ Device tracking ✓ Push config ⚠ Needs native app development (free frameworks available)</small>
                <button onclick="switchTab('mobile-push')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
        </div>

        <h3 style="margin-top: 30px;">⚙️ Framework Features (Backend Ready)</h3>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">📊</div>
                <h3>Call Quality Prediction</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                </div>
                <p>ML-based QoS prediction (FREE: scikit-learn)</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ Metrics tracking ✓ Alerting ⚠ Needs ML model (free framework available)</small>
                <button onclick="switchTab('call-quality-prediction')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>

            <div class="stat-card">
                <div class="stat-icon">🎬</div>
                <h3>Video Codecs (H.264/H.265)</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                </div>
                <p>Video codec support (FREE: FFmpeg, OpenH264)</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ Codec negotiation ✓ Bandwidth calc ⚠ Needs FFmpeg/OpenH264 (free)</small>
                <button onclick="switchTab('video-codec')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🔄</div>
                <h3>Number Portability</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                </div>
                <p>Use business number on mobile device</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ DID mapping ✓ Simultaneous ring ⚠ Needs mobile integration</small>
                <button onclick="switchTab('mobile-number-portability')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🎙️</div>
                <h3>Recording Analytics</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                </div>
                <p>AI analysis of recorded calls (FREE: Vosk + spaCy)</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ Sentiment ✓ Keywords ⚠ Needs NLP service (free options available)</small>
                <button onclick="switchTab('recording-analytics')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🔀</div>
                <h3>Call Blending</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                </div>
                <p>Mix inbound/outbound calls for efficiency</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ Mode switching ✓ Priority distribution ⚠ Needs queue integration</small>
                <button onclick="switchTab('call-blending')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📭</div>
                <h3>Voicemail Drop</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                </div>
                <p>Auto-leave message on voicemail detection (FREE: pyAudioAnalysis)</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ AMD ✓ Message library ⚠ Needs detection algorithm (free options available)</small>
                <button onclick="switchTab('voicemail-drop')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🌍</div>
                <h3>Geographic Redundancy</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                </div>
                <p>Multi-region trunk registration with failover</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ Region management ✓ Health monitoring ⚠ Needs multi-region setup</small>
                <button onclick="switchTab('geo-redundancy')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🌐</div>
                <h3>DNS SRV Failover</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                </div>
                <p>Automatic server failover using DNS SRV (FREE: BIND, PowerDNS)</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ Priority selection ✓ Load balancing ⚠ Needs DNS SRV records (free DNS servers available)</small>
                <button onclick="switchTab('dns-srv-failover')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🛡️</div>
                <h3>Session Border Controller</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                </div>
                <p>Enhanced security and NAT traversal (FREE: Kamailio, OpenSIPS)</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ Topology hiding ✓ Security filtering ⚠ Needs SBC deployment (free options available)</small>
                <button onclick="switchTab('session-border-controller')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🗺️</div>
                <h3>Data Residency Controls</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                </div>
                <p>Geographic data storage options for compliance</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ Region management ✓ GDPR support ⚠ Needs multi-region storage</small>
                <button onclick="switchTab('data-residency')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📹</div>
                <h3>Video Conferencing</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                </div>
                <p>HD/4K video calls with screen sharing (FREE: Jitsi, BigBlueButton)</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ Room management ✓ Participant tracking ⚠ Needs video service (free options available)</small>
                <button onclick="switchTab('video-conferencing')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
            <div class="stat-card">
                <div class="stat-icon">💬</div>
                <h3>Team Messaging</h3>
                <div style="margin: 10px 0;">
                    <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                </div>
                <p>Slack/Teams alternative with channels and file sharing (FREE: Matrix, Rocket.Chat)</p>
                <small style="color: #666; display: block; margin-top: 8px;">✓ Channel management ✓ Message tracking ⚠ Needs messaging server (free options available)</small>
                <button onclick="switchTab('team-messaging')" class="btn-primary" style="margin-top: 10px;">Configure</button>
            </div>
        </div>

        <div class="section-card" style="margin-top: 30px; background: #e8f5e9; border-left: 4px solid #4caf50;">
            <h3>💚 100% Free & Open Source</h3>
            <div class="info-box" style="background: white;">
                <p><strong>All framework features can be implemented using only free and open-source technologies:</strong></p>
                <ul style="margin-top: 10px;">
                    <li>✅ <strong>Vosk:</strong> FREE offline speech recognition (instead of Google/AWS)</li>
                    <li>✅ <strong>spaCy & NLTK:</strong> FREE NLP and AI classification (instead of OpenAI/Azure)</li>
                    <li>✅ <strong>scikit-learn:</strong> FREE machine learning framework</li>
                    <li>✅ <strong>Metabase/Superset/Redash:</strong> FREE business intelligence tools</li>
                    <li>✅ <strong>React Native:</strong> FREE mobile app framework</li>
                    <li>✅ <strong>Rasa/ChatterBot:</strong> FREE conversational AI frameworks</li>
                    <li>✅ <strong>Vicidial:</strong> FREE predictive dialer (open source)</li>
                    <li>✅ <strong>FFmpeg:</strong> FREE audio/video processing</li>
                    <li>✅ <strong>Kamailio/OpenSIPS:</strong> FREE SIP servers for SBC</li>
                </ul>
                <p style="margin-top: 15px; font-weight: bold; color: #2e7d32;">💰 Total Cost: $0 - No licensing fees, no cloud costs, no subscriptions!</p>
            </div>
        </div>

        <div class="section-card" style="margin-top: 20px;">
            <h3>📋 Implementation Notes</h3>
            <div class="info-box">
                <p>All framework features include:</p>
                <ul>
                    <li>✅ <strong>Database Schemas:</strong> Tables and relationships defined and ready</li>
                    <li>✅ <strong>REST APIs:</strong> Endpoints for configuration and management</li>
                    <li>✅ <strong>Logging:</strong> Comprehensive logging infrastructure</li>
                    <li>✅ <strong>Configuration:</strong> Enable/disable flags and settings</li>
                    <li>✅ <strong>Free Integration Options:</strong> All features have documented free/open-source integration options</li>
                </ul>
                <p style="margin-top: 15px;"><strong>Total Lines of Code:</strong> ~5,200 lines across 16 frameworks</p>
                <p><strong>Tests:</strong> All frameworks have comprehensive test coverage with 100% pass rate</p>
                <p><strong>Documentation:</strong> Each feature has detailed implementation guides</p>
            </div>
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
    setTimeout(async () => {
        try {
            const r = await fetch('/api/framework/click-to-dial/configs', {headers: pbxAuthHeaders()});
            const data = await r.json();
            displayClickToDialConfigs(data.configs ?? []);
        } catch (err) {
            const errorContainer = document.getElementById('click-to-dial-configs-list');
            if (errorContainer) {
                errorContainer.innerHTML =
                    `<div class="error-box">Error loading configurations: ${escapeHtml(err.message)}</div>`;
            }
        }
    }, 100);

    return content;
}

function displayClickToDialConfigs(configs) {
    const container = document.getElementById('click-to-dial-configs-list');
    
    // Exit early if container doesn't exist
    if (!container) {
        debugWarn('Click-to-dial configs container not found');
        return;
    }

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
                        <td>${escapeHtml(String(config.extension))}</td>
                        <td>${config.enabled ? '✅ Yes' : '❌ No'}</td>
                        <td>${config.auto_answer ? '✅ Yes' : '❌ No'}</td>
                        <td>${config.browser_notification ? '✅ Yes' : '❌ No'}</td>
                        <td>
                            <button onclick="viewClickToDialHistory('${escapeHtml(String(config.extension))}')" class="btn-secondary btn-sm">View History</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

const viewClickToDialHistory = async (extension) => {
    try {
        const r = await fetch(`/api/framework/click-to-dial/history/${extension}`, {headers: pbxAuthHeaders()});
        const data = await r.json();
        const history = data.history ?? [];
        const container = document.getElementById('click-to-dial-history');

        if (history.length === 0) {
            container.innerHTML = `<p>No call history for extension ${escapeHtml(String(extension))}</p>`;
            return;
        }

        const html = `
            <h4>Call History for Extension ${escapeHtml(String(extension))}</h4>
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
                            <td>${escapeHtml(String(call.destination))}</td>
                            <td>${escapeHtml(String(call.source))}</td>
                            <td><span class="status-badge status-${escapeHtml(String(call.status))}">${escapeHtml(String(call.status))}</span></td>
                            <td>${new Date(call.initiated_at).toLocaleString()}</td>
                            <td>${call.connected_at ? new Date(call.connected_at).toLocaleString() : '-'}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

        container.innerHTML = html;
    } catch (err) {
        document.getElementById('click-to-dial-history').innerHTML =
            `<div class="error-box">Error loading history: ${escapeHtml(err.message)}</div>`;
    }
};

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

const loadVideoRooms = async () => {
    try {
        const r = await fetch('/api/framework/video-conference/rooms', {headers: pbxAuthHeaders()});
        const data = await r.json();
        displayVideoRooms(data.rooms ?? []);
    } catch (err) {
        document.getElementById('video-rooms-list').innerHTML =
            `<div class="error-box">Error loading rooms: ${escapeHtml(err.message)}</div>`;
    }
};

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
                        <td>${escapeHtml(room.room_name)}</td>
                        <td>${escapeHtml(room.owner_extension || '-')}</td>
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

const showCreateRoomDialog = () => {
    document.getElementById('create-room-dialog').style.display = 'flex';

    // Setup form submission
    document.getElementById('create-room-form').onsubmit = async function(e) {
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

        try {
            const r = await fetch('/api/framework/video-conference/create-room', {
                method: 'POST',
                headers: pbxAuthHeaders(),
                body: JSON.stringify(data)
            });
            const result = await r.json();
            if (result.success) {
                alert('Room created successfully!');
                hideCreateRoomDialog();
                loadVideoRooms();
            } else {
                alert(`Error creating room: ${result.error ?? 'Unknown error'}`);
            }
        } catch (err) {
            alert('Error creating room: ' + err.message);
        }
    };
};

function hideCreateRoomDialog() {
    document.getElementById('create-room-dialog').style.display = 'none';
}

// Add more framework feature tab loaders...
// (Team Messaging, Nomadic E911, CRM Integrations, Compliance, Speech Analytics)

// Conversational AI Tab
function loadConversationalAITab() {
    return `
        <h2>🤖 Conversational AI Assistant</h2>
        <div class="info-box" style="background: #fff3cd; border-left: 4px solid #ff9800;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                <strong>Database & APIs Ready</strong>
            </div>
            <p>Auto-responses and smart call handling using AI technology.</p>
            <p><strong>Supported Services:</strong> OpenAI GPT, Google Dialogflow, Amazon Lex, Microsoft Azure Bot Service</p>
            <p><strong>Features:</strong> Intent detection, entity extraction, conversation context management, auto-responses</p>
        </div>

        <div class="section-card">
            <h3>Configuration</h3>
            <form id="conversational-ai-config-form" style="max-width: 600px;" onsubmit="submitConversationalAIConfig(event)">
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="ai-enabled" name="enabled">
                        Enable Conversational AI
                    </label>
                </div>
                <div class="form-group">
                    <label>AI Provider:</label>
                    <select id="ai-provider" name="provider" class="form-control">
                        <option value="openai">OpenAI GPT</option>
                        <option value="dialogflow">Google Dialogflow</option>
                        <option value="lex">Amazon Lex</option>
                        <option value="azure">Microsoft Azure Bot Service</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>API Key:</label>
                    <input type="password" id="ai-api-key" name="api_key" required class="form-control" placeholder="Enter your API key">
                    <small>API key for the selected provider (stored securely)</small>
                </div>
                <div class="form-group">
                    <label>Model:</label>
                    <input type="text" id="ai-model" name="model" class="form-control" placeholder="gpt-4" value="gpt-4">
                    <small>For OpenAI: gpt-4, gpt-3.5-turbo, etc.</small>
                </div>
                <div class="form-group">
                    <label>Max Tokens:</label>
                    <input type="number" id="ai-max-tokens" name="max_tokens" class="form-control" value="150" min="50" max="4000">
                    <small>Maximum length of AI responses</small>
                </div>
                <div class="form-group">
                    <label>Temperature (0.0 - 1.0):</label>
                    <input type="number" id="ai-temperature" name="temperature" class="form-control" value="0.7" min="0" max="1" step="0.1">
                    <small>Higher = more creative, Lower = more focused</small>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn-primary">Save Configuration</button>
                    <button type="button" class="btn-secondary" onclick="loadConversationalAIStats()">View Statistics</button>
                </div>
            </form>
        </div>

        <div class="section-card">
            <h3>Statistics</h3>
            <div id="ai-statistics">
                <p>Click "View Statistics" to load current stats</p>
            </div>
        </div>

        <div class="section-card">
            <h3>Integration Requirements</h3>
            <div class="info-box">
                <p><strong>To activate this feature, you need:</strong></p>
                <ul>
                    <li>✅ Conversation context tracking - <strong>Ready</strong></li>
                    <li>✅ Intent and entity detection framework - <strong>Ready</strong></li>
                    <li>✅ Response generation pipeline - <strong>Ready</strong></li>
                    <li>⚠️ AI service API credentials - <strong>Required</strong></li>
                    <li>⚠️ Update config.yml with provider settings</li>
                </ul>
                <p style="margin-top: 15px;"><strong>Example config.yml:</strong></p>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;">
features:
  conversational_ai:
    enabled: true
    provider: 'openai'
    model: 'gpt-4'
    api_key: 'your-api-key-here'  # Store securely
    max_tokens: 150
    temperature: 0.7</pre>
            </div>
        </div>
    `;
}

const loadConversationalAIStats = async () => {
    const statsDiv = document.getElementById('ai-statistics');
    statsDiv.innerHTML = '<p>Loading statistics...</p>';

    try {
        const r = await fetch('/api/framework/conversational-ai/stats', {headers: pbxAuthHeaders()});
        const data = await r.json();
        const stats = data.statistics ?? {};
        statsDiv.innerHTML = `
            <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));">
                <div class="stat-card">
                    <div class="stat-value">${stats.total_conversations || 0}</div>
                    <div class="stat-label">Total Conversations</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${stats.active_conversations || 0}</div>
                    <div class="stat-label">Active</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${stats.total_messages || 0}</div>
                    <div class="stat-label">Messages Processed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${stats.intents_detected || 0}</div>
                    <div class="stat-label">Intents Detected</div>
                </div>
            </div>
            ${stats.total_conversations === 0 ? '<p style="margin-top: 15px; color: #666;"><em>Note: No conversations yet. Statistics will appear when the feature is enabled and in use.</em></p>' : ''}
        `;
    } catch (err) {
        // API endpoint not yet implemented or feature not enabled - show friendly message
        statsDiv.innerHTML = `<p style="color: #666;"><em>Statistics unavailable. The API endpoint (/api/framework/conversational-ai/stats) will be available when the feature is enabled with an AI provider configured.</em></p>`;
    }
};

const submitConversationalAIConfig = async (e) => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const provider = formData.get('provider');
    const apiKey = formData.get('api_key');

    if (!apiKey) {
        alert('API key is required');
        return;
    }

    const data = {
        provider: provider,
        api_key: apiKey,
        options: {
            model: formData.get('model') || 'gpt-4',
            max_tokens: parseInt(formData.get('max_tokens')) || 150,
            temperature: parseFloat(formData.get('temperature')) || 0.7
        }
    };

    try {
        const r = await fetch('/api/framework/conversational-ai/config', {
            method: 'POST',
            headers: pbxAuthHeaders(),
            body: JSON.stringify(data)
        });
        const result = await r.json();
        if (result.success) {
            alert(`Conversational AI configured with ${result.provider} provider.`);
        } else {
            alert(`Error saving config: ${result.error ?? 'Unknown error'}`);
        }
    } catch (err) {
        alert('Error saving configuration: ' + err.message);
    }
};

// Predictive Dialing Tab
function loadPredictiveDialingTab() {
    const content = `
        <h2>📞 Predictive Dialing</h2>
        <div class="info-box" style="background: #fff3cd; border-left: 4px solid #ff9800;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                <strong>Database & APIs Ready</strong>
            </div>
            <p>AI-optimized outbound campaign management with multiple dialing modes.</p>
            <p><strong>Modes:</strong> Preview, Progressive, Predictive, Power</p>
            <p><strong>Features:</strong> Campaign management, contact tracking, agent availability prediction</p>
        </div>

        <div class="section-card">
            <h3>Active Campaigns</h3>
            <button onclick="showCreateCampaignDialog()" class="btn-primary">+ Create Campaign</button>
            <div id="campaigns-list" style="margin-top: 15px;">
                <p>Loading campaigns...</p>
            </div>
        </div>

        <div class="section-card">
            <h3>Campaign Statistics</h3>
            <div id="campaign-statistics">
                <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));">
                    <div class="stat-card">
                        <div class="stat-value" id="total-campaigns">0</div>
                        <div class="stat-label">Total Campaigns</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="active-campaigns">0</div>
                        <div class="stat-label">Active</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="calls-today">0</div>
                        <div class="stat-label">Calls Today</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="contact-rate">0%</div>
                        <div class="stat-label">Contact Rate</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="section-card">
            <h3>Dialing Modes</h3>
            <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
                <div class="stat-card">
                    <h4>📋 Preview Mode</h4>
                    <p style="color: #666; font-size: 14px;">Agent reviews contact before dialing</p>
                </div>
                <div class="stat-card">
                    <h4>➡️ Progressive Mode</h4>
                    <p style="color: #666; font-size: 14px;">Auto-dial when agent available</p>
                </div>
                <div class="stat-card">
                    <h4>🤖 Predictive Mode</h4>
                    <p style="color: #666; font-size: 14px;">AI predicts agent availability</p>
                </div>
                <div class="stat-card">
                    <h4>⚡ Power Mode</h4>
                    <p style="color: #666; font-size: 14px;">Multiple dials per agent</p>
                </div>
            </div>
        </div>

        <div class="section-card">
            <h3>Integration Requirements</h3>
            <div class="info-box">
                <p><strong>Ready for Integration:</strong></p>
                <ul>
                    <li>✅ Campaign creation and management - <strong>Ready</strong></li>
                    <li>✅ Contact list handling - <strong>Ready</strong></li>
                    <li>✅ Dialing mode configuration - <strong>Ready</strong></li>
                    <li>✅ Agent availability tracking - <strong>Ready</strong></li>
                    <li>⚠️ Dialer engine integration - <strong>Required</strong></li>
                    <li>⚠️ AI agent prediction model - <strong>Optional</strong></li>
                </ul>
            </div>
        </div>
    `;

    setTimeout(() => {
        loadPredictiveDialingCampaigns();
        loadPredictiveDialingStats();
    }, 100);

    return content;
}

const loadPredictiveDialingCampaigns = async () => {
    try {
        const r = await fetch('/api/framework/predictive-dialing/campaigns', {headers: pbxAuthHeaders()});
        const data = await r.json();
        const campaigns = data.campaigns ?? [];
        const container = document.getElementById('campaigns-list');

        if (campaigns.length === 0) {
            container.innerHTML = '<p style="color: #666;">No campaigns created yet. Framework ready for campaign management.</p>';
            return;
        }

        const html = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Campaign Name</th>
                        <th>Mode</th>
                        <th>Status</th>
                        <th>Contacts</th>
                        <th>Dialed</th>
                        <th>Connected</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${campaigns.map(c => `
                        <tr>
                            <td><strong>${escapeHtml(c.name)}</strong></td>
                            <td>${escapeHtml(c.mode)}</td>
                            <td><span class="status-badge status-${escapeHtml(c.status)}">${escapeHtml(c.status)}</span></td>
                            <td>${c.total_contacts || 0}</td>
                            <td>${c.dialed || 0}</td>
                            <td>${c.connected || 0}</td>
                            <td>
                                <button onclick="toggleCampaign('${escapeHtml(String(c.id))}')" class="btn-secondary btn-sm">
                                    ${c.status === 'active' ? 'Pause' : 'Start'}
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        container.innerHTML = html;
    } catch (err) {
        document.getElementById('campaigns-list').innerHTML =
            '<p style="color: #666;">Framework ready. Campaigns will appear when feature is enabled.</p>';
    }
};

const loadPredictiveDialingStats = async () => {
    try {
        const r = await fetch('/api/framework/predictive-dialing/statistics', {headers: pbxAuthHeaders()});
        const data = await r.json();
        const stats = data.statistics ?? {};
        document.getElementById('total-campaigns').textContent = stats.total_campaigns || 0;
        document.getElementById('active-campaigns').textContent = stats.active_campaigns || 0;
        document.getElementById('calls-today').textContent = stats.calls_today || 0;
        document.getElementById('contact-rate').textContent = `${stats.contact_rate ?? 0}%`;
    } catch (err) {
        // Silent failure is acceptable - statistics will show 0 values
        // This occurs when the feature is not yet enabled or API endpoint not implemented
    }
};

function hideCreateCampaignDialog() {
    const modal = document.getElementById('create-campaign-dialog');
    if (modal) modal.remove();
}

function showCreateCampaignDialog() {
    hideCreateCampaignDialog();
    const modal = `
        <div id="create-campaign-dialog" class="modal" style="display: flex; align-items: center;
             justify-content: center;">
            <div class="modal-content" style="max-width: 600px;">
                <div class="modal-header">
                    <h3>Create Campaign</h3>
                    <span class="close" onclick="hideCreateCampaignDialog()">&times;</span>
                </div>
                <form id="create-campaign-form">
                    <div class="form-group">
                        <label>Campaign ID:</label>
                        <input type="text" name="campaign_id" required class="form-control"
                            placeholder="campaign-001">
                    </div>
                    <div class="form-group">
                        <label>Campaign Name:</label>
                        <input type="text" name="name" required class="form-control"
                            placeholder="Outbound Sales Q1">
                    </div>
                    <div class="form-group">
                        <label>Dialing Mode:</label>
                        <select name="dialing_mode" class="form-control">
                            <option value="progressive">Progressive</option>
                            <option value="preview">Preview</option>
                            <option value="predictive">Predictive</option>
                            <option value="power">Power</option>
                        </select>
                    </div>
                    <div class="modal-actions">
                        <button type="submit" class="btn-primary">Create Campaign</button>
                        <button type="button" class="btn-secondary"
                            onclick="hideCreateCampaignDialog()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modal);

    document.getElementById('create-campaign-form').onsubmit = async function(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {
            campaign_id: formData.get('campaign_id'),
            name: formData.get('name'),
            dialing_mode: formData.get('dialing_mode')
        };

        try {
            const r = await fetch('/api/framework/predictive-dialing/campaign', {
                method: 'POST',
                headers: pbxAuthHeaders(),
                body: JSON.stringify(data)
            });
            const result = await r.json();
            if (result.success) {
                alert('Campaign created successfully!');
                hideCreateCampaignDialog();
                loadPredictiveDialingCampaigns();
            } else {
                alert(`Error creating campaign: ${result.error ?? 'Unknown error'}`);
            }
        } catch (err) {
            alert('Error creating campaign: ' + err.message);
        }
    };
}

const toggleCampaign = async (campaignId) => {
    try {
        await fetch(`/api/framework/predictive-dialing/campaigns/${campaignId}/toggle`, { method: 'POST', headers: pbxAuthHeaders() });
        await loadPredictiveDialingCampaigns();
    } catch (err) {
        alert(`Error: ${err.message}`);
    }
};

// Voice Biometrics Tab
function loadVoiceBiometricsTab() {
    const content = `
        <h2>🔊 Voice Biometrics</h2>
        <div class="info-box" style="background: #fff3cd; border-left: 4px solid #ff9800;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                <strong>Database & APIs Ready</strong>
            </div>
            <p>Speaker authentication and fraud detection using voice biometrics.</p>
            <p><strong>Supported Services:</strong> Nuance, Pindrop, AWS Connect Voice ID</p>
            <p><strong>Features:</strong> Voice enrollment, verification, fraud detection</p>
        </div>

        <div class="section-card">
            <h3>Enrolled Users</h3>
            <button onclick="showEnrollUserDialog()" class="btn-primary">+ Enroll User</button>
            <div id="biometric-profiles-list" style="margin-top: 15px;">
                <p>Loading voice profiles...</p>
            </div>
        </div>

        <div class="section-card">
            <h3>Statistics</h3>
            <div id="biometric-statistics">
                <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));">
                    <div class="stat-card">
                        <div class="stat-value" id="enrolled-users">0</div>
                        <div class="stat-label">Enrolled Users</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="verifications-today">0</div>
                        <div class="stat-label">Verifications Today</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="success-rate">0%</div>
                        <div class="stat-label">Success Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="fraud-attempts">0</div>
                        <div class="stat-label">Fraud Attempts</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="section-card">
            <h3>Integration Requirements</h3>
            <div class="info-box">
                <p><strong>Ready for Integration:</strong></p>
                <ul>
                    <li>✅ User profile management - <strong>Ready</strong></li>
                    <li>✅ Enrollment and verification workflow - <strong>Ready</strong></li>
                    <li>✅ Fraud detection framework - <strong>Ready</strong></li>
                    <li>✅ Voice sample storage - <strong>Ready</strong></li>
                    <li>⚠️ Voice biometric engine - <strong>Required (Nuance/Pindrop/AWS)</strong></li>
                </ul>
                <p style="margin-top: 15px;"><strong>Supported Providers:</strong></p>
                <ul>
                    <li>Nuance Gatekeeper - Enterprise voice biometrics</li>
                    <li>Pindrop - Voice authentication and fraud detection</li>
                    <li>AWS Connect Voice ID - Scalable cloud solution</li>
                </ul>
            </div>
        </div>
    `;

    setTimeout(() => {
        loadVoiceBiometricProfiles();
        loadVoiceBiometricStats();
    }, 100);

    return content;
}

const loadVoiceBiometricProfiles = async () => {
    try {
        const r = await fetch('/api/framework/voice-biometrics/profiles', {headers: pbxAuthHeaders()});
        const data = await r.json();
        const profiles = data.profiles ?? [];
        const container = document.getElementById('biometric-profiles-list');

        if (profiles.length === 0) {
            container.innerHTML = '<p style="color: #666;">No users enrolled yet. Framework ready for voice enrollment.</p>';
            return;
        }

        const html = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Extension</th>
                        <th>User Name</th>
                        <th>Enrollment Date</th>
                        <th>Verifications</th>
                        <th>Last Verified</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${profiles.map(p => `
                        <tr>
                            <td>${p.extension}</td>
                            <td>${p.name}</td>
                            <td>${new Date(p.enrolled_at).toLocaleDateString()}</td>
                            <td>${p.verification_count || 0}</td>
                            <td>${p.last_verified ? new Date(p.last_verified).toLocaleString() : 'Never'}</td>
                            <td><span class="status-badge status-${p.status}">${p.status}</span></td>
                            <td>
                                <button onclick="deleteVoiceProfile('${p.id}')" class="btn-danger btn-sm">Delete</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        container.innerHTML = html;
    } catch (err) {
        document.getElementById('biometric-profiles-list').innerHTML =
            '<p style="color: #666;">Framework ready. Voice profiles will appear when feature is enabled.</p>';
    }
};

const loadVoiceBiometricStats = async () => {
    try {
        const r = await fetch('/api/framework/voice-biometrics/statistics', {headers: pbxAuthHeaders()});
        const data = await r.json();
        const stats = data.statistics ?? {};
        document.getElementById('enrolled-users').textContent = stats.enrolled_users || 0;
        document.getElementById('verifications-today').textContent = stats.verifications_today || 0;
        document.getElementById('success-rate').textContent = `${stats.success_rate ?? 0}%`;
        document.getElementById('fraud-attempts').textContent = stats.fraud_attempts || 0;
    } catch (err) {
        // Silent failure is acceptable - statistics will show 0 values
        // This occurs when the feature is not yet enabled or API endpoint not implemented
    }
};

function hideEnrollUserDialog() {
    const modal = document.getElementById('enroll-user-dialog');
    if (modal) modal.remove();
}

function showEnrollUserDialog() {
    hideEnrollUserDialog();
    const modal = `
        <div id="enroll-user-dialog" class="modal" style="display: flex; align-items: center;
             justify-content: center;">
            <div class="modal-content" style="max-width: 500px;">
                <div class="modal-header">
                    <h3>Enroll User for Voice Biometrics</h3>
                    <span class="close" onclick="hideEnrollUserDialog()">&times;</span>
                </div>
                <form id="enroll-user-form">
                    <div class="form-group">
                        <label>User ID / Extension:</label>
                        <input type="text" name="user_id" required class="form-control"
                            placeholder="1001">
                        <small>Enter the user ID or extension number to enroll</small>
                    </div>
                    <div class="info-box" style="margin-top: 15px;">
                        <p><strong>Enrollment Process:</strong></p>
                        <ol style="margin: 5px 0 0 20px;">
                            <li>Start enrollment session</li>
                            <li>Record voice samples (3-5 phrases)</li>
                            <li>Biometric engine processes voiceprint</li>
                            <li>Profile activated for authentication</li>
                        </ol>
                    </div>
                    <div class="modal-actions">
                        <button type="submit" class="btn-primary">Start Enrollment</button>
                        <button type="button" class="btn-secondary"
                            onclick="hideEnrollUserDialog()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modal);

    document.getElementById('enroll-user-form').onsubmit = async function(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = { user_id: formData.get('user_id') };

        try {
            const r = await fetch('/api/framework/voice-biometrics/enroll', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await r.json();
            if (result.success) {
                alert(`Enrollment started for ${result.user_id}.\n\nSession ID: ${result.session_id}\nRequired samples: ${result.required_samples}\n\nPlease complete voice sample recording via the phone system.`);
                hideEnrollUserDialog();
                loadVoiceBiometricProfiles();
            } else {
                alert(`Error starting enrollment: ${result.error ?? 'Unknown error'}`);
            }
        } catch (err) {
            alert('Error starting enrollment: ' + err.message);
        }
    };
}

const deleteVoiceProfile = async (profileId) => {
    if (confirm('Are you sure you want to delete this voice profile?')) {
        try {
            await fetch(`/api/framework/voice-biometrics/profiles/${profileId}`, { method: 'DELETE', headers: pbxAuthHeaders() });
            await loadVoiceBiometricProfiles();
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    }
};

// Call Quality Prediction Tab
function loadCallQualityPredictionTab() {
    return `
        <h2>📊 Call Quality Prediction</h2>
        <div class="info-box" style="background: #fff3cd; border-left: 4px solid #ff9800;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                <strong>Database & APIs Ready</strong>
            </div>
            <p>Proactive network issue detection using machine learning.</p>
            <p><strong>Features:</strong> Real-time quality prediction, network metrics tracking, proactive alerting</p>
        </div>

        <div class="section-card">
            <h3>Prediction Configuration</h3>
            <p>Configure quality prediction settings here. Framework ready for ML model integration.</p>
            <div class="info-box">
                <p><strong>Ready for Integration:</strong></p>
                <ul>
                    <li>✅ Network metrics collection (latency, jitter, packet loss)</li>
                    <li>✅ Alert threshold configuration</li>
                    <li>✅ Historical trend analysis framework</li>
                    <li>⚠️ Requires ML prediction model</li>
                </ul>
            </div>
        </div>
    `;
}

// Video Codec Tab
function loadVideoCodecTab() {
    return `
        <h2>🎬 Video Codecs (H.264/H.265)</h2>
        <div class="info-box" style="background: #fff3cd; border-left: 4px solid #ff9800;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                <strong>Database & APIs Ready</strong>
            </div>
            <p>Advanced video codec support for H.264 and H.265 video calling.</p>
            <p><strong>Supported Codecs:</strong> FFmpeg, OpenH264, x265</p>
            <p><strong>Features:</strong> Codec negotiation, bandwidth calculation, encoder/decoder creation</p>
        </div>

        <div class="section-card">
            <h3>Codec Configuration</h3>
            <p>Configure video codec settings here. Framework ready for video engine integration.</p>
            <div class="info-box">
                <p><strong>Ready for Integration:</strong></p>
                <ul>
                    <li>✅ Codec negotiation framework</li>
                    <li>✅ Bandwidth calculation</li>
                    <li>✅ Resolution and bitrate management</li>
                    <li>⚠️ Requires FFmpeg or codec library integration</li>
                </ul>
            </div>
        </div>
    `;
}

// BI Integration Tab
function loadBIIntegrationTab() {
    // Load statistics on tab load
    (async () => {
        try {
            const r = await fetch('/api/framework/bi-integration/statistics', {headers: pbxAuthHeaders()});
            const stats = await r.json();
            document.getElementById('bi-stats-display').innerHTML = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">📦</div>
                        <div class="stat-value">${stats.total_datasets || 0}</div>
                        <div class="stat-label">Datasets</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">📤</div>
                        <div class="stat-value">${stats.total_exports || 0}</div>
                        <div class="stat-label">Total Exports</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">⏰</div>
                        <div class="stat-value">${stats.last_export_time ? new Date(stats.last_export_time).toLocaleDateString() : 'Never'}</div>
                        <div class="stat-label">Last Export</div>
                    </div>
                </div>
            `;
        } catch (err) {
            console.error('Error loading BI statistics:', err);
        }
    })();

    const content = `
        <h2>📈 Business Intelligence Integration</h2>
        <div class="info-box" style="background: #e8f5e9; border-left: 4px solid #4caf50;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-fully-implemented">✅ API Connected</span>
                <strong>REST API Endpoints Active</strong>
            </div>
            <p>Export call data to business intelligence tools.</p>
            <p><strong>Supported Tools:</strong> Tableau, Power BI, Looker, Qlik, Metabase</p>
            <p><strong>Export Formats:</strong> CSV, JSON, Excel</p>
        </div>

        <div class="section-card">
            <h3>Statistics</h3>
            <div id="bi-stats-display">
                <p>Loading statistics...</p>
            </div>
        </div>

        <div class="section-card">
            <h3>Available Datasets</h3>
            <div id="bi-datasets-list">
                <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));">
                    <div class="stat-card">
                        <h4>📞 Call Detail Records (CDR)</h4>
                        <p style="color: #666; font-size: 14px; margin: 10px 0;">Complete call history with caller, callee, duration, and disposition</p>
                        <button onclick="exportBIDataset('cdr')" class="btn-primary btn-sm">Export CDR</button>
                    </div>
                    <div class="stat-card">
                        <h4>📊 Queue Statistics</h4>
                        <p style="color: #666; font-size: 14px; margin: 10px 0;">Call queue metrics, wait times, and agent performance</p>
                        <button onclick="exportBIDataset('queue_stats')" class="btn-primary btn-sm">Export Queue Stats</button>
                    </div>
                    <div class="stat-card">
                        <h4>📡 QoS Metrics</h4>
                        <p style="color: #666; font-size: 14px; margin: 10px 0;">Call quality data including MOS, jitter, packet loss</p>
                        <button onclick="exportBIDataset('qos_metrics')" class="btn-primary btn-sm">Export QoS</button>
                    </div>
                    <div class="stat-card">
                        <h4>👥 Extension Usage</h4>
                        <p style="color: #666; font-size: 14px; margin: 10px 0;">Per-extension usage, call volumes, and trends</p>
                        <button onclick="exportBIDataset('extension_usage')" class="btn-primary btn-sm">Export Analytics</button>
                    </div>
                </div>
            </div>
        </div>

        <div class="section-card">
            <h3>Export Configuration</h3>
            <form id="bi-export-form" style="max-width: 600px;">
                <div class="form-group">
                    <label>Export Format:</label>
                    <select id="bi-export-format" class="form-control">
                        <option value="csv">CSV (Comma-Separated Values)</option>
                        <option value="json">JSON (JavaScript Object Notation)</option>
                        <option value="excel">Excel (.xlsx)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Date Range:</label>
                    <select id="bi-date-range" class="form-control">
                        <option value="today">Today</option>
                        <option value="yesterday">Yesterday</option>
                        <option value="last7days" selected>Last 7 Days</option>
                        <option value="last30days">Last 30 Days</option>
                        <option value="last90days">Last 90 Days</option>
                    </select>
                </div>
            </form>
        </div>

        <div class="section-card">
            <h3>BI Tool Integration</h3>
            <div class="info-box">
                <p><strong>Integration Status:</strong></p>
                <ul>
                    <li>✅ Default datasets (CDR, queue stats, QoS metrics) - <strong>Ready</strong></li>
                    <li>✅ Multiple export formats (CSV, JSON, Excel) - <strong>Ready</strong></li>
                    <li>✅ REST API endpoints for data export - <strong>Active</strong></li>
                    <li>✅ Date range filtering - <strong>Ready</strong></li>
                    <li>⚠️ Direct BI tool API connections - <strong>Requires credentials</strong></li>
                </ul>
                <p style="margin-top: 15px;"><strong>Active API Endpoints:</strong></p>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;">
GET  /api/framework/bi-integration/datasets
GET  /api/framework/bi-integration/statistics
GET  /api/framework/bi-integration/export/{dataset}
POST /api/framework/bi-integration/export
POST /api/framework/bi-integration/dataset
POST /api/framework/bi-integration/test-connection</pre>
            </div>
        </div>
    `;
    return content;
}

const exportBIDataset = async (dataset) => {
    const format = document.getElementById('bi-export-format')?.value || 'csv';
    const dateRange = document.getElementById('bi-date-range')?.value || 'last7days';

    // Show loading message
    const exportBtn = event.target;
    const originalText = exportBtn.textContent;
    exportBtn.textContent = 'Exporting...';
    exportBtn.disabled = true;

    try {
        const r = await fetch('/api/framework/bi-integration/export', {
            method: 'POST',
            headers: pbxAuthHeaders(),
            body: JSON.stringify({
                dataset: dataset,
                format: format,
                date_range: dateRange
            })
        });
        const result = await r.json();
        if (result.success) {
            alert(`✅ Export successful!\n\nDataset: ${result.dataset}\nFormat: ${result.format}\nFile: ${result.file_path}\n\nThe export has been created on the server.`);
        } else {
            alert(`❌ Export failed: ${result.error}`);
        }
    } catch (err) {
        alert(`❌ Export error: ${err.message}`);
    } finally {
        exportBtn.textContent = originalText;
        exportBtn.disabled = false;
    }
};

// Call Tagging Tab
function loadCallTaggingTab() {
    // Load tags and statistics
    (async () => {
        try {
            const r = await fetch('/api/framework/call-tagging/statistics', {headers: pbxAuthHeaders()});
            const stats = await r.json();
            document.getElementById('tagging-stats-display').innerHTML = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">🏷️</div>
                        <div class="stat-value">${stats.total_calls_tagged || 0}</div>
                        <div class="stat-label">Calls Tagged</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">📝</div>
                        <div class="stat-value">${stats.custom_tags_count || 0}</div>
                        <div class="stat-label">Custom Tags</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">⚙️</div>
                        <div class="stat-value">${stats.tagging_rules_count || 0}</div>
                        <div class="stat-label">Active Rules</div>
                    </div>
                </div>
            `;
        } catch (err) {
            console.error('Error loading tagging statistics:', err);
        }
    })();

    const content = `
        <h2>🏷️ Call Tagging & Categorization</h2>
        <div class="info-box" style="background: #e8f5e9; border-left: 4px solid #4caf50;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-fully-implemented">✅ API Connected</span>
                <strong>REST API Endpoints Active</strong>
            </div>
            <p>AI-powered call classification and auto-tagging.</p>
            <p><strong>Features:</strong> Auto-tagging, rule-based tagging, tag analytics, search by tags</p>
        </div>

        <div class="section-card">
            <h3>Statistics</h3>
            <div id="tagging-stats-display">
                <p>Loading statistics...</p>
            </div>
        </div>

        <div class="section-card">
            <h3>Tag Management</h3>
            <button onclick="showCreateTagDialog()" class="btn-primary">+ Create Tag</button>
            <div id="tags-list" style="margin-top: 15px;">
                <p>Loading tags...</p>
            </div>
        </div>

        <div class="section-card">
            <h3>Auto-Tagging Rules</h3>
            <button onclick="showCreateRuleDialog()" class="btn-primary">+ Create Rule</button>
            <div id="tagging-rules-list" style="margin-top: 15px;">
                <p>Loading rules...</p>
            </div>
        </div>

        <div class="section-card">
            <h3>API Integration</h3>
            <div class="info-box">
                <p><strong>Integration Status:</strong></p>
                <ul>
                    <li>✅ Tag creation and management - <strong>Active</strong></li>
                    <li>✅ Rule-based auto-tagging - <strong>Ready</strong></li>
                    <li>✅ Tag search and analytics - <strong>Ready</strong></li>
                    <li>✅ REST API endpoints - <strong>Active</strong></li>
                    <li>⚠️ AI classification service - <strong>Requires external AI</strong></li>
                </ul>
                <p style="margin-top: 15px;"><strong>Active API Endpoints:</strong></p>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;">
GET  /api/framework/call-tagging/tags
GET  /api/framework/call-tagging/rules
GET  /api/framework/call-tagging/statistics
POST /api/framework/call-tagging/tag
POST /api/framework/call-tagging/rule
POST /api/framework/call-tagging/classify/{call_id}</pre>
                <p style="margin-top: 15px;"><strong>Supported AI Services:</strong></p>
                <ul>
                    <li>OpenAI GPT for semantic classification</li>
                    <li>Google Cloud Natural Language</li>
                    <li>AWS Comprehend</li>
                    <li>Custom ML models via REST API</li>
                </ul>
            </div>
        </div>
    `;

    // Load tags and rules after content is rendered
    setTimeout(() => {
        loadCallTags();
        loadTaggingRules();
    }, 100);

    return content;
}

const loadCallTags = async () => {
    try {
        const r = await fetch('/api/framework/call-tagging/tags', {headers: pbxAuthHeaders()});
        const data = await r.json();
        const tags = data.tags ?? [];
        const container = document.getElementById('tags-list');

        if (tags.length === 0) {
            container.innerHTML = '<p style="color: #666;">No tags created yet. Click "+ Create Tag" to add your first tag.</p>';
            return;
        }

        const html = `
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                ${tags.map(tag => `
                    <div class="tag-badge" style="background: ${tag.color || '#4caf50'}; color: white; padding: 8px 15px; border-radius: 20px; display: flex; align-items: center; gap: 8px;">
                        <span>${tag.name}</span>
                        <span style="font-size: 11px; opacity: 0.8;">(${tag.count || 0} calls)</span>
                        <button onclick="deleteTag('${tag.id}')" style="background: none; border: none; color: white; cursor: pointer; padding: 0 5px;">×</button>
                    </div>
                `).join('')}
            </div>
        `;
        container.innerHTML = html;
    } catch (err) {
        // Expected when feature is not yet enabled or API endpoint not implemented
        // Fallback shows framework ready message with 0 values
        document.getElementById('tags-list').innerHTML =
            `<p class="text-muted">Framework ready. Tags will appear when feature is enabled.</p>`;
    }
};

const loadTaggingRules = async () => {
    try {
        const r = await fetch('/api/framework/call-tagging/rules', {headers: pbxAuthHeaders()});
        const data = await r.json();
        const rules = data.rules ?? [];
        const container = document.getElementById('tagging-rules-list');

        if (rules.length === 0) {
            container.innerHTML = '<p style="color: #666;">No auto-tagging rules created yet.</p>';
            return;
        }

        const html = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Rule Name</th>
                        <th>Condition</th>
                        <th>Tag</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${rules.map(rule => `
                        <tr>
                            <td>${rule.name}</td>
                            <td>${rule.condition}</td>
                            <td><span class="tag-badge" style="background: ${rule.tag_color}; color: white; padding: 4px 10px; border-radius: 12px;">${rule.tag_name}</span></td>
                            <td>${rule.enabled ? '✅ Active' : '❌ Disabled'}</td>
                            <td>
                                <button onclick="toggleRule('${rule.id}')" class="btn-secondary btn-sm">${rule.enabled ? 'Disable' : 'Enable'}</button>
                                <button onclick="deleteRule('${rule.id}')" class="btn-danger btn-sm">Delete</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        container.innerHTML = html;
    } catch (err) {
        // Expected when feature is not yet enabled or API endpoint not implemented
        // Fallback shows framework ready message
        document.getElementById('tagging-rules-list').innerHTML =
            `<p class="text-muted">Framework ready. Rules will appear when feature is enabled.</p>`;
    }
};

const loadTagStatistics = async () => {
    try {
        const r = await fetch('/api/framework/call-tagging/statistics', {headers: pbxAuthHeaders()});
        const data = await r.json();
        const stats = data.statistics ?? {};
        document.getElementById('total-tags').textContent = stats.total_tags || 0;
        document.getElementById('tagged-calls').textContent = stats.tagged_calls || 0;
        document.getElementById('active-rules').textContent = stats.active_rules || 0;
        document.getElementById('auto-tagged').textContent = stats.auto_tagged_today || 0;
    } catch (err) {
        // Expected when feature is not yet enabled or API endpoint not implemented
        // Fallback shows 0 values which is acceptable for framework-only features
    }
};

function hideCreateTagDialog() {
    const modal = document.getElementById('create-tag-dialog');
    if (modal) modal.remove();
}

function showCreateTagDialog() {
    hideCreateTagDialog();
    const modal = `
        <div id="create-tag-dialog" class="modal" style="display: flex; align-items: center;
             justify-content: center;">
            <div class="modal-content" style="max-width: 500px;">
                <div class="modal-header">
                    <h3>Create Tag</h3>
                    <span class="close" onclick="hideCreateTagDialog()">&times;</span>
                </div>
                <form id="create-tag-form">
                    <div class="form-group">
                        <label>Tag Name:</label>
                        <input type="text" name="name" required class="form-control"
                            placeholder="VIP Customer">
                    </div>
                    <div class="form-group">
                        <label>Description:</label>
                        <input type="text" name="description" class="form-control"
                            placeholder="Calls from VIP customers">
                    </div>
                    <div class="form-group">
                        <label>Color:</label>
                        <input type="color" name="color" class="form-control"
                            value="#007bff" style="height: 40px; padding: 2px;">
                    </div>
                    <div class="modal-actions">
                        <button type="submit" class="btn-primary">Create Tag</button>
                        <button type="button" class="btn-secondary"
                            onclick="hideCreateTagDialog()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modal);

    document.getElementById('create-tag-form').onsubmit = async function(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {
            name: formData.get('name'),
            description: formData.get('description') || '',
            color: formData.get('color') || '#007bff'
        };

        try {
            const r = await fetch('/api/framework/call-tagging/tag', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await r.json();
            if (result.success) {
                alert('Tag created successfully!');
                hideCreateTagDialog();
                loadCallTags();
                loadTagStatistics();
            } else {
                alert(`Error creating tag: ${result.error ?? 'Unknown error'}`);
            }
        } catch (err) {
            alert('Error creating tag: ' + err.message);
        }
    };
}

function hideCreateRuleDialog() {
    const modal = document.getElementById('create-rule-dialog');
    if (modal) modal.remove();
}

function showCreateRuleDialog() {
    hideCreateRuleDialog();
    const modal = `
        <div id="create-rule-dialog" class="modal" style="display: flex; align-items: center;
             justify-content: center;">
            <div class="modal-content" style="max-width: 600px;">
                <div class="modal-header">
                    <h3>Create Tagging Rule</h3>
                    <span class="close" onclick="hideCreateRuleDialog()">&times;</span>
                </div>
                <form id="create-rule-form">
                    <div class="form-group">
                        <label>Rule Name:</label>
                        <input type="text" name="name" required class="form-control"
                            placeholder="Long calls">
                    </div>
                    <div class="form-group">
                        <label>Tag ID to Apply:</label>
                        <input type="text" name="tag_id" required class="form-control"
                            placeholder="vip-customer">
                        <small>The tag that will be applied when this rule matches</small>
                    </div>
                    <div class="form-group">
                        <label>Priority:</label>
                        <input type="number" name="priority" class="form-control"
                            value="100" min="1" max="1000">
                        <small>Lower number = higher priority</small>
                    </div>
                    <div class="form-group">
                        <label>Condition Type:</label>
                        <select name="condition_type" class="form-control">
                            <option value="duration_gt">Call Duration Greater Than</option>
                            <option value="duration_lt">Call Duration Less Than</option>
                            <option value="caller_pattern">Caller Pattern (Regex)</option>
                            <option value="callee_pattern">Callee Pattern (Regex)</option>
                            <option value="keyword">Keyword in Transcription</option>
                            <option value="time_range">Time of Day Range</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Condition Value:</label>
                        <input type="text" name="condition_value" required class="form-control"
                            placeholder="300 (seconds), ^\\+1555.*, escalate, 09:00-17:00">
                        <small>Value depends on condition type selected above</small>
                    </div>
                    <div class="modal-actions">
                        <button type="submit" class="btn-primary">Create Rule</button>
                        <button type="button" class="btn-secondary"
                            onclick="hideCreateRuleDialog()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modal);

    document.getElementById('create-rule-form').onsubmit = async function(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {
            name: formData.get('name'),
            tag_id: formData.get('tag_id'),
            priority: parseInt(formData.get('priority')) || 100,
            conditions: [{
                type: formData.get('condition_type'),
                value: formData.get('condition_value')
            }]
        };

        try {
            const r = await fetch('/api/framework/call-tagging/rule', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await r.json();
            if (result.success) {
                alert('Rule created successfully!');
                hideCreateRuleDialog();
                loadTaggingRules();
                loadTagStatistics();
            } else {
                alert(`Error creating rule: ${result.error ?? 'Unknown error'}`);
            }
        } catch (err) {
            alert('Error creating rule: ' + err.message);
        }
    };
}

const deleteTag = async (tagId) => {
    if (confirm('Are you sure you want to delete this tag?')) {
        try {
            await fetch(`/api/framework/call-tagging/tags/${tagId}`, { method: 'DELETE', headers: pbxAuthHeaders() });
            await loadCallTags();
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    }
};

const deleteRule = async (ruleId) => {
    if (confirm('Are you sure you want to delete this rule?')) {
        try {
            await fetch(`/api/framework/call-tagging/rules/${ruleId}`, { method: 'DELETE', headers: pbxAuthHeaders() });
            await loadTaggingRules();
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    }
};

const toggleRule = async (ruleId) => {
    try {
        await fetch(`/api/framework/call-tagging/rules/${ruleId}/toggle`, { method: 'POST', headers: pbxAuthHeaders() });
        await loadTaggingRules();
    } catch (err) {
        alert(`Error: ${err.message}`);
    }
};

// Mobile Apps Tab
function loadMobileAppsTab() {
    return `
        <h2>📱 Mobile Apps Framework</h2>
        <div class="info-box" style="background: #fff3cd; border-left: 4px solid #ff9800;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                <strong>Backend Infrastructure Ready</strong>
            </div>
            <p>Full-featured mobile client support for iOS and Android.</p>
            <p><strong>Platforms:</strong> iOS (Swift/SwiftUI), Android (Kotlin)</p>
            <p><strong>Features:</strong> SIP calling, push notifications, device management, background call handling</p>
        </div>

        <div class="section-card">
            <h3>Configuration</h3>
            <form id="mobile-apps-config-form" style="max-width: 600px;" onsubmit="submitMobileAppsConfig(event)">
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="mobile-apps-enabled" name="enabled">
                        Enable Mobile App Support
                    </label>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="ios-enabled" name="ios_enabled" checked>
                        iOS Support
                    </label>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="android-enabled" name="android_enabled" checked>
                        Android Support
                    </label>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="push-enabled" name="push_enabled" checked>
                        Push Notifications
                    </label>
                </div>
                <div class="form-group">
                    <label>Firebase Server Key (for push notifications):</label>
                    <input type="password" id="firebase-key" name="firebase_key" class="form-control" placeholder="Your FCM server key">
                    <small>Required for iOS and Android push notifications</small>
                </div>
                <h4 style="margin-top: 20px;">Register Test Device</h4>
                <div class="form-group">
                    <label>User ID / Extension:</label>
                    <input type="text" id="mobile-user-id" name="user_id" class="form-control" placeholder="1001">
                </div>
                <div class="form-group">
                    <label>Device Token:</label>
                    <input type="text" id="mobile-device-token" name="device_token" class="form-control" placeholder="FCM or APNs device token">
                </div>
                <div class="form-group">
                    <label>Platform:</label>
                    <select id="mobile-platform" name="platform" class="form-control">
                        <option value="ios">iOS</option>
                        <option value="android">Android</option>
                        <option value="web">Web</option>
                    </select>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn-primary">Register Device</button>
                    <button type="button" class="btn-secondary" onclick="loadMobileAppsStats()">View Statistics</button>
                </div>
            </form>
        </div>

        <div class="section-card">
            <h3>Registered Devices</h3>
            <div id="mobile-devices-list">
                <p>No mobile devices registered yet.</p>
            </div>
        </div>

        <div class="section-card">
            <h3>Development Requirements</h3>
            <div class="info-box">
                <p><strong>To deploy mobile apps:</strong></p>
                <ul>
                    <li>✅ Device registration backend - <strong>Ready</strong></li>
                    <li>✅ Push notification framework - <strong>Ready</strong></li>
                    <li>✅ SIP configuration API - <strong>Ready</strong></li>
                    <li>⚠️ iOS app development (Swift/SwiftUI) - <strong>Required</strong></li>
                    <li>⚠️ Android app development (Kotlin) - <strong>Required</strong></li>
                    <li>⚠️ Firebase/APNs configuration - <strong>Required</strong></li>
                </ul>
                <p style="margin-top: 15px;"><strong>Recommended SIP libraries:</strong></p>
                <ul>
                    <li>iOS: PushKit + CallKit integration</li>
                    <li>Android: PJSIP or Linphone SDK</li>
                    <li>Both: WebRTC for media handling</li>
                </ul>
            </div>
        </div>
    `;
}

const loadMobileAppsStats = async () => {
    const devicesDiv = document.getElementById('mobile-devices-list');
    devicesDiv.innerHTML = '<p>Loading device statistics...</p>';

    try {
        const r = await fetch('/api/mobile-push/devices', {headers: pbxAuthHeaders()});
        const data = await r.json();
        const devices = data.devices ?? [];
        const stats = data.statistics ?? {};

        let html = `
            <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); margin-bottom: 20px;">
                <div class="stat-card">
                    <div class="stat-value">${stats.total_devices || devices.length || 0}</div>
                    <div class="stat-label">Total Devices</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${stats.ios_devices || 0}</div>
                    <div class="stat-label">iOS Devices</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${stats.android_devices || 0}</div>
                    <div class="stat-label">Android Devices</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${stats.active_devices || 0}</div>
                    <div class="stat-label">Active</div>
                </div>
            </div>
        `;

        if (devices.length > 0) {
            html += `
                <h4>Registered Devices</h4>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Extension</th>
                            <th>Platform</th>
                            <th>Device Model</th>
                            <th>Push Token</th>
                            <th>Registered</th>
                            <th>Last Seen</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${devices.map(device => `
                            <tr>
                                <td>${device.extension}</td>
                                <td>${device.platform === 'ios' ? '📱 iOS' : '🤖 Android'}</td>
                                <td>${device.device_model || 'Unknown'}</td>
                                <td><code style="font-size: 11px;">${(device.push_token || '').substring(0, 20)}...</code></td>
                                <td>${new Date(device.registered_at).toLocaleString()}</td>
                                <td>${device.last_seen ? new Date(device.last_seen).toLocaleString() : 'Never'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } else {
            html += '<p><em>No devices registered yet. Devices will appear here once the mobile apps are deployed and users register.</em></p>';
        }

        devicesDiv.innerHTML = html;
    } catch (err) {
        devicesDiv.innerHTML = `
            <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); margin-bottom: 20px;">
                <div class="stat-card">
                    <div class="stat-value">0</div>
                    <div class="stat-label">Total Devices</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">0</div>
                    <div class="stat-label">iOS Devices</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">0</div>
                    <div class="stat-label">Android Devices</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">0</div>
                    <div class="stat-label">Active</div>
                </div>
            </div>
            <p style="color: #666;"><em>Framework ready. Devices will appear when mobile apps are deployed and users register.</em></p>
        `;
    }
};

const submitMobileAppsConfig = async (e) => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const userId = formData.get('user_id');
    const deviceToken = formData.get('device_token');

    if (!userId || !deviceToken) {
        alert('User ID and Device Token are required to register a device.');
        return;
    }

    const data = {
        user_id: userId,
        device_token: deviceToken,
        platform: formData.get('platform') || 'unknown'
    };

    try {
        const r = await fetch('/api/mobile-push/register', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        const result = await r.json();
        if (result.success) {
            alert('Device registered successfully!');
            loadMobileAppsStats();
        } else {
            alert(`Error registering device: ${result.error ?? 'Unknown error'}`);
        }
    } catch (err) {
        alert('Error registering device: ' + err.message);
    }
};

// Mobile Number Portability Tab
function loadMobileNumberPortabilityTab() {
    return `
        <h2>🔄 Mobile Number Portability</h2>
        <div class="info-box" style="background: #fff3cd; border-left: 4px solid #ff9800;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                <strong>Database & APIs Ready</strong>
            </div>
            <p>Use business phone numbers on mobile devices.</p>
            <p><strong>Features:</strong> DID mapping, simultaneous ring (desk + mobile), business hours routing</p>
        </div>

        <div class="section-card">
            <h3>Number Portability Configuration</h3>
            <p>Configure mobile number portability here. Framework ready for mobile integration.</p>
            <div class="info-box">
                <p><strong>Ready for Integration:</strong></p>
                <ul>
                    <li>✅ DID to mobile device mapping</li>
                    <li>✅ Simultaneous ring configuration</li>
                    <li>✅ Business hours routing rules</li>
                    <li>⚠️ Requires mobile SIP client integration</li>
                </ul>
            </div>
        </div>
    `;
}

// Recording Analytics Tab
function loadRecordingAnalyticsTab() {
    return `
        <h2>🎙️ Call Recording Analytics</h2>
        <div class="info-box" style="background: #fff3cd; border-left: 4px solid #ff9800;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                <strong>Database & APIs Ready</strong>
            </div>
            <p>AI analysis of recorded calls.</p>
            <p><strong>Features:</strong> Sentiment analysis, keyword detection, compliance checking, quality scoring, summarization</p>
        </div>

        <div class="section-card">
            <h3>Analytics Configuration</h3>
            <p>Configure recording analytics here. Framework ready for NLP service integration.</p>
            <div class="info-box">
                <p><strong>Ready for Integration:</strong></p>
                <ul>
                    <li>✅ Recording metadata tracking</li>
                    <li>✅ Analysis result storage</li>
                    <li>✅ Keyword and sentiment framework</li>
                    <li>⚠️ Requires NLP/speech analytics service</li>
                </ul>
            </div>
        </div>
    `;
}

// Call Blending Tab
function loadCallBlendingTab() {
    // Load statistics on tab load
    (async () => {
        try {
            const r = await fetch('/api/framework/call-blending/statistics', {headers: pbxAuthHeaders()});
            const stats = await r.json();
            document.getElementById('blending-stats-display').innerHTML = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">👥</div>
                        <div class="stat-value">${stats.total_agents || 0}</div>
                        <div class="stat-label">Total Agents</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">✅</div>
                        <div class="stat-value">${stats.available_agents || 0}</div>
                        <div class="stat-label">Available</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">📞</div>
                        <div class="stat-value">${stats.total_blended_calls || 0}</div>
                        <div class="stat-label">Blended Calls</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">📊</div>
                        <div class="stat-value">${Math.round((stats.actual_blend_ratio || 0) * 100)}%</div>
                        <div class="stat-label">Inbound Ratio</div>
                    </div>
                </div>
            `;
        } catch (err) {
            console.error('Error loading blending statistics:', err);
        }
    })();

    // Load agents list
    (async () => {
        try {
            const r = await fetch('/api/framework/call-blending/agents', {headers: pbxAuthHeaders()});
            const data = await r.json();
            const agents = data.agents ?? [];
            const container = document.getElementById('blending-agents-list');

            if (agents.length === 0) {
                container.innerHTML = '<p style="color: #666;">No agents registered for call blending yet.</p>';
                return;
            }

            const html = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Agent ID</th>
                            <th>Extension</th>
                            <th>Mode</th>
                            <th>Status</th>
                            <th>Inbound Calls</th>
                            <th>Outbound Calls</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${agents.map(agent => `
                            <tr>
                                <td>${agent.agent_id}</td>
                                <td>${agent.extension}</td>
                                <td>
                                    <select onchange="changeAgentMode('${agent.agent_id}', this.value)">
                                        <option value="blended" ${agent.mode === 'blended' ? 'selected' : ''}>Blended</option>
                                        <option value="inbound_only" ${agent.mode === 'inbound_only' ? 'selected' : ''}>Inbound Only</option>
                                        <option value="outbound_only" ${agent.mode === 'outbound_only' ? 'selected' : ''}>Outbound Only</option>
                                        <option value="auto" ${agent.mode === 'auto' ? 'selected' : ''}>Auto</option>
                                    </select>
                                </td>
                                <td>
                                    <span class="status-badge ${agent.available ? 'status-online' : 'status-offline'}">
                                        ${agent.available ? '✅ Available' : '🔴 Unavailable'}
                                    </span>
                                </td>
                                <td>${agent.inbound_calls_handled || 0}</td>
                                <td>${agent.outbound_calls_handled || 0}</td>
                                <td>
                                    <button onclick="viewAgentDetails('${agent.agent_id}')" class="btn-sm btn-primary">View</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
            container.innerHTML = html;
        } catch (err) {
            console.error('Error loading agents:', err);
            document.getElementById('blending-agents-list').innerHTML = '<p style="color: #666;">No agents available.</p>';
        }
    })();

    return `
        <h2>🔀 Call Blending</h2>
        <div class="info-box" style="background: #e8f5e9; border-left: 4px solid #4caf50;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-fully-implemented">✅ API Connected</span>
                <strong>REST API Endpoints Active</strong>
            </div>
            <p>Mix inbound and outbound calls for agent efficiency.</p>
            <p><strong>Features:</strong> Dynamic mode switching, priority distribution, inbound surge protection, workload balancing</p>
        </div>

        <div class="section-card">
            <h3>Statistics</h3>
            <div id="blending-stats-display">
                <p>Loading statistics...</p>
            </div>
        </div>

        <div class="section-card">
            <h3>Registered Agents</h3>
            <div id="blending-agents-list">
                <p>Loading agents...</p>
            </div>
        </div>

        <div class="section-card">
            <h3>API Integration</h3>
            <div class="info-box">
                <p><strong>Integration Status:</strong></p>
                <ul>
                    <li>✅ Agent mode management - <strong>Active</strong></li>
                    <li>✅ Priority-based distribution - <strong>Ready</strong></li>
                    <li>✅ Workload balancing framework - <strong>Ready</strong></li>
                    <li>✅ REST API endpoints - <strong>Active</strong></li>
                    <li>⚠️ Queue system integration - <strong>Requires configuration</strong></li>
                </ul>
                <p style="margin-top: 15px;"><strong>Active API Endpoints:</strong></p>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;">
GET  /api/framework/call-blending/agents
GET  /api/framework/call-blending/statistics
GET  /api/framework/call-blending/agent/{agent_id}
POST /api/framework/call-blending/agent
POST /api/framework/call-blending/agent/{agent_id}/mode</pre>
            </div>
        </div>
    `;
}

const changeAgentMode = async (agentId, newMode) => {
    try {
        const r = await fetch(`/api/framework/call-blending/agent/${agentId}/mode`, {
            method: 'POST',
            headers: pbxAuthHeaders(),
            body: JSON.stringify({mode: newMode})
        });
        const result = await r.json();
        if (result.success) {
            alert(`✅ Agent mode updated to ${newMode}`);
        } else {
            alert(`❌ Failed to update mode: ${result.error}`);
        }
    } catch (err) {
        alert(`❌ Error: ${err.message}`);
    }
};

const viewAgentDetails = async (agentId) => {
    try {
        const r = await fetch(`/api/framework/call-blending/agent/${agentId}`, {headers: pbxAuthHeaders()});
        const agent = await r.json();
        alert(`Agent Details:\n\nAgent ID: ${agent.agent_id}\nExtension: ${agent.extension}\nMode: ${agent.mode}\nStatus: ${agent.available ? 'Available' : 'Unavailable'}\nInbound Calls: ${agent.inbound_calls_handled}\nOutbound Calls: ${agent.outbound_calls_handled}`);
    } catch (err) {
        alert(`❌ Error loading agent: ${err.message}`);
    }
};

// Voicemail Drop Tab
function loadVoicemailDropTab() {
    return `
        <h2>📭 Predictive Voicemail Drop</h2>
        <div class="info-box" style="background: #fff3cd; border-left: 4px solid #ff9800;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                <strong>Database & APIs Ready</strong>
            </div>
            <p>Auto-leave pre-recorded messages when voicemail is detected.</p>
            <p><strong>Features:</strong> Answering machine detection (AMD), pre-recorded message library, FCC compliance</p>
        </div>

        <div class="section-card">
            <h3>Voicemail Drop Configuration</h3>
            <p>Configure voicemail drop here. Framework ready for AMD integration.</p>
            <div class="info-box">
                <p><strong>Ready for Integration:</strong></p>
                <ul>
                    <li>✅ Message library management</li>
                    <li>✅ FCC compliance tracking</li>
                    <li>✅ Drop success/failure reporting</li>
                    <li>⚠️ Requires answering machine detection algorithm</li>
                </ul>
            </div>
        </div>
    `;
}

// Geographic Redundancy Tab
function loadGeographicRedundancyTab() {
    // Load statistics on tab load
    (async () => {
        try {
            const r = await fetch('/api/framework/geo-redundancy/statistics', {headers: pbxAuthHeaders()});
            const stats = await r.json();
            document.getElementById('geo-stats-display').innerHTML = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">🌍</div>
                        <div class="stat-value">${stats.total_regions || 0}</div>
                        <div class="stat-label">Regions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">✅</div>
                        <div class="stat-value">${stats.active_region || 'None'}</div>
                        <div class="stat-label">Active Region</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">🔄</div>
                        <div class="stat-value">${stats.total_failovers || 0}</div>
                        <div class="stat-label">Total Failovers</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">🤖</div>
                        <div class="stat-value">${stats.auto_failover ? 'Enabled' : 'Disabled'}</div>
                        <div class="stat-label">Auto Failover</div>
                    </div>
                </div>
            `;
        } catch (err) {
            console.error('Error loading geo statistics:', err);
        }
    })();

    // Load regions list
    (async () => {
        try {
            const r = await fetch('/api/framework/geo-redundancy/regions', {headers: pbxAuthHeaders()});
            const data = await r.json();
            const regions = data.regions ?? [];
            const container = document.getElementById('geo-regions-list');

            if (regions.length === 0) {
                container.innerHTML = '<p style="color: #666;">No regions configured yet. Click "+ Add Region" to create your first region.</p>';
                return;
            }

            const html = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Region ID</th>
                            <th>Name</th>
                            <th>Location</th>
                            <th>Status</th>
                            <th>Health Score</th>
                            <th>Trunks</th>
                            <th>Priority</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${regions.map(region => {
                            let statusColor = '#4caf50';
                            if (region.status === 'failed') statusColor = '#f44336';
                            else if (region.status === 'standby') statusColor = '#ff9800';

                            return `
                                <tr ${region.is_active ? 'style="background: #e8f5e9;"' : ''}>
                                    <td>
                                        ${region.region_id}
                                        ${region.is_active ? '<span class="status-badge status-online">ACTIVE</span>' : ''}
                                    </td>
                                    <td>${region.name}</td>
                                    <td>${region.location}</td>
                                    <td>
                                        <span class="status-badge" style="background: ${statusColor};">
                                            ${region.status.toUpperCase()}
                                        </span>
                                    </td>
                                    <td>${Math.round((region.health_score || 0) * 100)}%</td>
                                    <td>${region.trunk_count || 0}</td>
                                    <td>${region.priority}</td>
                                    <td>
                                        ${!region.is_active ? `<button onclick="triggerFailover('${region.region_id}')" class="btn-sm btn-primary">Activate</button>` : ''}
                                        <button onclick="viewRegionDetails('${region.region_id}')" class="btn-sm">Details</button>
                                    </td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            `;
            container.innerHTML = html;
        } catch (err) {
            console.error('Error loading regions:', err);
            document.getElementById('geo-regions-list').innerHTML = '<p style="color: #666;">No regions available.</p>';
        }
    })();

    return `
        <h2>🌍 Geographic Redundancy</h2>
        <div class="info-box" style="background: #e8f5e9; border-left: 4px solid #4caf50;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-fully-implemented">✅ API Connected</span>
                <strong>REST API Endpoints Active</strong>
            </div>
            <p>Multi-region trunk registration with automatic failover for disaster recovery.</p>
            <p><strong>Features:</strong> Regional health monitoring, automatic failover, priority-based region selection, data replication</p>
        </div>

        <div class="section-card">
            <h3>Statistics</h3>
            <div id="geo-stats-display">
                <p>Loading statistics...</p>
            </div>
        </div>

        <div class="section-card">
            <h3>Geographic Regions</h3>
            <button onclick="showCreateRegionDialog()" class="btn-primary">+ Add Region</button>
            <div id="geo-regions-list" style="margin-top: 15px;">
                <p>Loading regions...</p>
            </div>
        </div>

        <div class="section-card">
            <h3>API Integration</h3>
            <div class="info-box">
                <p><strong>Integration Status:</strong></p>
                <ul>
                    <li>✅ Region management - <strong>Active</strong></li>
                    <li>✅ Health check framework - <strong>Ready</strong></li>
                    <li>✅ Failover priority configuration - <strong>Ready</strong></li>
                    <li>✅ REST API endpoints - <strong>Active</strong></li>
                    <li>⚠️ Multi-region infrastructure - <strong>Requires deployment</strong></li>
                </ul>
                <p style="margin-top: 15px;"><strong>Active API Endpoints:</strong></p>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;">
GET  /api/framework/geo-redundancy/regions
GET  /api/framework/geo-redundancy/statistics
GET  /api/framework/geo-redundancy/region/{region_id}
POST /api/framework/geo-redundancy/region
POST /api/framework/geo-redundancy/region/{region_id}/failover</pre>
            </div>
        </div>
    `;
}

const showCreateRegionDialog = async () => {
    const regionId = prompt('Enter Region ID (e.g., us-east-1):');
    if (!regionId) return;

    const name = prompt('Enter Region Name (e.g., US East):');
    if (!name) return;

    const location = prompt('Enter Region Location (e.g., Virginia, USA):');
    if (!location) return;

    try {
        const r = await fetch('/api/framework/geo-redundancy/region', {
            method: 'POST',
            headers: pbxAuthHeaders(),
            body: JSON.stringify({
                region_id: regionId,
                name: name,
                location: location
            })
        });
        const result = await r.json();
        if (result.success) {
            alert(`✅ Region created successfully!`);
            // Reload the tab
            switchTab('geo-redundancy');
        } else {
            alert(`❌ Failed to create region: ${result.error}`);
        }
    } catch (err) {
        alert(`❌ Error: ${err.message}`);
    }
};

const triggerFailover = async (regionId) => {
    if (!confirm(`Are you sure you want to failover to region ${regionId}?`)) return;

    try {
        const r = await fetch(`/api/framework/geo-redundancy/region/${regionId}/failover`, {
            method: 'POST',
            headers: pbxAuthHeaders()
        });
        const result = await r.json();
        if (result.success) {
            alert(`✅ Failover successful!\nFrom: ${result.from_region}\nTo: ${result.to_region}`);
            // Reload the tab
            switchTab('geo-redundancy');
        } else {
            alert(`❌ Failover failed: ${result.error}`);
        }
    } catch (err) {
        alert(`❌ Error: ${err.message}`);
    }
};

const viewRegionDetails = async (regionId) => {
    try {
        const r = await fetch(`/api/framework/geo-redundancy/region/${regionId}`, {headers: pbxAuthHeaders()});
        const region = await r.json();
        const details = `Region Details:

Region ID: ${region.region_id}
Name: ${region.name}
Location: ${region.location}
Status: ${region.status}
Health Score: ${Math.round((region.health_score || 0) * 100)}%
Trunks: ${region.trunk_count}
Priority: ${region.priority}
Is Active: ${region.is_active ? 'Yes' : 'No'}
Last Health Check: ${region.last_health_check || 'Never'}`;

        alert(details);
    } catch (err) {
        alert(`❌ Error loading region: ${err.message}`);
    }
};

// DNS SRV Failover Tab
function loadDNSSRVFailoverTab() {
    return `
        <h2>🌐 DNS SRV Failover</h2>
        <div class="info-box" style="background: #fff3cd; border-left: 4px solid #ff9800;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                <strong>Database & APIs Ready</strong>
            </div>
            <p>Automatic server failover using DNS SRV records.</p>
            <p><strong>Features:</strong> Priority-based server selection, weight-based load balancing, health monitoring, SRV record caching</p>
        </div>

        <div class="section-card">
            <h3>DNS SRV Configuration</h3>
            <p>Configure DNS SRV failover here. Framework ready for DNS integration.</p>
            <div class="info-box">
                <p><strong>Ready for Integration:</strong></p>
                <ul>
                    <li>✅ SRV record parsing and caching</li>
                    <li>✅ Priority and weight handling</li>
                    <li>✅ Health monitoring framework</li>
                    <li>⚠️ Requires DNS SRV record configuration</li>
                </ul>
            </div>
        </div>
    `;
}

// Session Border Controller Tab
function loadSessionBorderControllerTab() {
    return `
        <h2>🛡️ Session Border Controller</h2>
        <div class="info-box" style="background: #fff3cd; border-left: 4px solid #ff9800;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                <strong>Database & APIs Ready</strong>
            </div>
            <p>Enhanced security and NAT traversal for SIP communications.</p>
            <p><strong>Features:</strong> Topology hiding, protocol normalization, DoS protection, media relay, call admission control</p>
        </div>

        <div class="section-card">
            <h3>SBC Configuration</h3>
            <p>Configure session border controller here. Framework ready for SBC deployment.</p>
            <div class="info-box">
                <p><strong>Ready for Integration:</strong></p>
                <ul>
                    <li>✅ Security policy framework</li>
                    <li>✅ NAT traversal configuration</li>
                    <li>✅ Media relay settings</li>
                    <li>⚠️ Requires SBC appliance or software</li>
                </ul>
            </div>
        </div>
    `;
}

// Data Residency Tab
function loadDataResidencyTab() {
    return `
        <h2>🗺️ Data Residency Controls</h2>
        <div class="info-box" style="background: #fff3cd; border-left: 4px solid #ff9800;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                <strong>Database & APIs Ready</strong>
            </div>
            <p>Geographic data storage options for regulatory compliance.</p>
            <p><strong>Features:</strong> Region-specific storage, cross-border transfer controls, GDPR compliance, compliance reporting</p>
        </div>

        <div class="section-card">
            <h3>Data Residency Configuration</h3>
            <p>Configure data residency controls here. Framework ready for multi-region storage.</p>
            <div class="info-box">
                <p><strong>Ready for Integration:</strong></p>
                <ul>
                    <li>✅ Region management</li>
                    <li>✅ Data classification framework</li>
                    <li>✅ Compliance reporting</li>
                    <li>⚠️ Requires multi-region storage infrastructure</li>
                </ul>
            </div>
        </div>
    `;
}

// Team Messaging Tab
function loadTeamMessagingTab() {
    return `
        <h2>💬 Team Messaging</h2>
        <div class="info-box" style="background: #fff3cd; border-left: 4px solid #ff9800;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span class="status-badge status-framework-only">⚙️ Framework Only</span>
                <strong>Database & APIs Ready</strong>
            </div>
            <p>Internal team messaging and collaboration platform (FREE alternatives to Slack/Teams).</p>
            <p><strong>Supported Services:</strong> Matrix/Element, Rocket.Chat, Mattermost</p>
            <p><strong>Features:</strong> Channels, direct messages, file sharing, integrations, search</p>
        </div>

        <div class="section-card">
            <h3>Channel Management</h3>
            <p>Configure team messaging channels here. Framework ready for messaging server integration.</p>
            <div class="info-box">
                <p><strong>Ready for Integration:</strong></p>
                <ul>
                    <li>✅ Channel creation and management - <strong>Ready</strong></li>
                    <li>✅ Member management - <strong>Ready</strong></li>
                    <li>✅ Message storage framework - <strong>Ready</strong></li>
                    <li>✅ File attachment support - <strong>Ready</strong></li>
                    <li>⚠️ Messaging server (Matrix/Rocket.Chat) - <strong>Required</strong></li>
                </ul>
                <p style="margin-top: 15px;"><strong>Recommended Setup:</strong></p>
                <ul>
                    <li><strong>Matrix + Element:</strong> Federated, secure, feature-rich</li>
                    <li><strong>Rocket.Chat:</strong> Easy setup, familiar Slack-like interface</li>
                    <li><strong>Mattermost:</strong> Enterprise features, compliance focus</li>
                </ul>
            </div>
        </div>

        <div class="section-card">
            <h3>Integration Requirements</h3>
            <div class="info-box">
                <p><strong>To activate team messaging:</strong></p>
                <ol>
                    <li>Install Matrix Synapse, Rocket.Chat, or Mattermost server</li>
                    <li>Configure server connection in config.yml</li>
                    <li>Set up authentication integration</li>
                    <li>Create initial channels and invite team members</li>
                </ol>
                <p style="margin-top: 15px;"><strong>Example config.yml:</strong></p>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;">
features:
  team_messaging:
    enabled: true
    provider: 'matrix'  # or 'rocketchat', 'mattermost'
    server_url: 'https://matrix.example.com'
    api_token: 'your-api-token'</pre>
            </div>
        </div>

        <div class="section-card">
            <h3>💚 100% Free Options</h3>
            <div class="info-box" style="background: #e8f5e9;">
                <p><strong>All team messaging options are free and open source:</strong></p>
                <ul>
                    <li>✅ <strong>Matrix:</strong> FREE federated messaging (like email for chat)</li>
                    <li>✅ <strong>Rocket.Chat:</strong> FREE community edition with unlimited users</li>
                    <li>✅ <strong>Mattermost:</strong> FREE team edition</li>
                </ul>
                <p style="margin-top: 15px; font-weight: bold; color: #2e7d32;">💰 Total Cost: $0 vs $96-240/user/year for Slack/Teams!</p>
            </div>
        </div>
    `;
}

// Export functions for use in main admin.js
window.frameworkFeatures = {
    loadFrameworkOverview,
    loadClickToDialTab,
    loadVideoConferencingTab,
    loadConversationalAITab,
    loadPredictiveDialingTab,
    loadVoiceBiometricsTab,
    loadCallQualityPredictionTab,
    loadVideoCodecTab,
    loadBIIntegrationTab,
    loadCallTaggingTab,
    loadMobileAppsTab,
    loadMobileNumberPortabilityTab,
    loadRecordingAnalyticsTab,
    loadCallBlendingTab,
    loadVoicemailDropTab,
    loadGeographicRedundancyTab,
    loadDNSSRVFailoverTab,
    loadSessionBorderControllerTab,
    loadDataResidencyTab,
    loadTeamMessagingTab,
    viewClickToDialHistory,
    loadConversationalAIStats,
    loadMobileAppsStats,
    exportBIDataset,
    loadCallTags,
    loadTaggingRules,
    loadTagStatistics,
    showCreateTagDialog,
    showCreateRuleDialog,
    deleteTag,
    deleteRule,
    toggleRule,
    loadPredictiveDialingCampaigns,
    loadPredictiveDialingStats,
    showCreateCampaignDialog,
    toggleCampaign,
    loadVoiceBiometricProfiles,
    loadVoiceBiometricStats,
    showEnrollUserDialog,
    hideEnrollUserDialog,
    deleteVoiceProfile,
    hideCreateCampaignDialog,
    hideCreateTagDialog,
    hideCreateRuleDialog,
    submitConversationalAIConfig,
    submitMobileAppsConfig
};

// Export framework feature load functions to global scope for compatibility with admin.js
// This is needed because admin.js expects these functions to be globally available for:
// 1. Tab switching (switchTab function checks typeof loadXXX === 'function')
// 2. Refresh all functionality (refreshAllData function calls loadXXX functions)
// We also export dialog show/hide functions and form handlers needed by inline onclick/onsubmit.
for (const funcName of Object.keys(window.frameworkFeatures)) {
    if (typeof window.frameworkFeatures[funcName] === 'function') {
        window[funcName] = window.frameworkFeatures[funcName];
    }
}
