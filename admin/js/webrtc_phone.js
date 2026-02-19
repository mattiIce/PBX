/**
 * WebRTC Phone Widget for Admin Panel
 * Enables browser-based calling to extension 1001 without hardware phone
 *
 * To enable verbose logging:
 * 1. Open browser console (F12)
 * 2. Type: window.WEBRTC_VERBOSE_LOGGING = true
 * 3. Press Enter
 * 4. Make your call - you'll see detailed [VERBOSE] logs in the console
 */

// Verbose logging flag - can be enabled via environment or console
// Set window.WEBRTC_VERBOSE_LOGGING = true in browser console for verbose logs
const VERBOSE_LOGGING = window.WEBRTC_VERBOSE_LOGGING || false;

function verboseLog(...args) {
    if (VERBOSE_LOGGING) {
        debugLog('[VERBOSE]', ...args);
    }
}

class WebRTCPhone {
    constructor(apiUrl, extension) {
        this.apiUrl = apiUrl;
        this.extension = extension; // Admin's extension for making calls
        this.sessionId = null;
        this.callId = null;
        this.peerConnection = null;
        this.localStream = null;
        this.isCallActive = false;
        this.remoteAudio = null;

        verboseLog('WebRTC Phone constructor called:', {
            apiUrl: this.apiUrl,
            extension: this.extension
        });

        // Initialize UI elements
        this.initializeUI();
    }

    initializeUI() {
        // Get UI elements
        this.callButton = document.getElementById('webrtc-call-btn');
        this.hangupButton = document.getElementById('webrtc-hangup-btn');
        this.muteButton = document.getElementById('webrtc-mute-btn');
        this.volumeSlider = document.getElementById('webrtc-volume');
        this.statusDiv = document.getElementById('webrtc-status');
        this.targetExtension = document.getElementById('webrtc-target-ext');
        this.keypadSection = document.getElementById('webrtc-keypad-section');

        // Create remote audio element
        this.remoteAudio = document.getElementById('webrtc-remote-audio');
        if (!this.remoteAudio) {
            this.remoteAudio = document.createElement('audio');
            this.remoteAudio.id = 'webrtc-remote-audio';
            this.remoteAudio.autoplay = true;
            this.remoteAudio.playsinline = true;
            document.body.appendChild(this.remoteAudio);
        }

        // Ensure audio element is ready for playback
        this.remoteAudio.autoplay = true;
        this.remoteAudio.playsinline = true;
        this.remoteAudio.volume = 0.8; // Set initial volume

        // Set up event listeners
        if (this.callButton) {
            this.callButton.addEventListener('click', () => this.makeCall());
        }
        if (this.hangupButton) {
            this.hangupButton.addEventListener('click', () => this.hangup());
        }
        if (this.muteButton) {
            this.muteButton.addEventListener('click', () => this.toggleMute());
        }
        if (this.volumeSlider) {
            this.volumeSlider.addEventListener('input', (e) => this.setVolume(e.target.value));
        }

        // Set up keypad buttons
        this.setupKeypad();

        this.updateUIState('idle');
    }

    setupKeypad() {
        // Add event listeners to all keypad buttons
        const keypadButtons = document.querySelectorAll('.keypad-btn');
        keypadButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const digit = e.currentTarget.getAttribute('data-digit');
                if (digit && this.isCallActive) {
                    this.sendDTMF(digit);
                    // Visual feedback
                    e.currentTarget.classList.add('pressed');
                    setTimeout(() => {
                        e.currentTarget.classList.remove('pressed');
                    }, 300);
                }
            });
        });

        verboseLog('Keypad initialized with', keypadButtons.length, 'buttons');
    }

    updateStatus(message, type = 'info') {
        if (this.statusDiv) {
            this.statusDiv.textContent = message;
            this.statusDiv.className = `webrtc-status ${type}`;
            debugLog(`[WebRTC Phone] ${message}`);
            verboseLog('Status update:', { message, type });
        }
    }

    updateUIState(state) {
        // state can be: idle, connecting, calling, connected
        if (this.callButton) {
            this.callButton.disabled = (state !== 'idle');
        }
        if (this.hangupButton) {
            this.hangupButton.disabled = (state === 'idle');
        }
        if (this.muteButton) {
            this.muteButton.disabled = (state === 'idle');
        }

        // Show keypad and enable buttons when call is active (calling or connected)
        const isCallActive = (state === 'connected' || state === 'calling');

        if (this.keypadSection) {
            this.keypadSection.style.display = isCallActive ? 'block' : 'none';
        }

        // Enable/disable keypad buttons based on call state
        const keypadButtons = document.querySelectorAll('.keypad-btn');
        keypadButtons.forEach(button => {
            button.disabled = !isCallActive;
        });
    }

    /**
     * Check if browser supports WebRTC getUserMedia
     * @returns {boolean} True if WebRTC is supported, false otherwise
     */
    _checkWebRTCSupport() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            const errorMsg = 'WebRTC not supported in this browser or context. Try using HTTPS or a modern browser.';
            this.updateStatus(errorMsg, 'error');
            console.error('[WebRTC Phone]', errorMsg);
            return false;
        }
        return true;
    }

    /**
     * Request microphone access automatically on page load
     * @description Provides a better user experience by prompting for permissions upfront.
     *              Matches Zultys ZIP33G behavior where the phone is always ready to use.
     * @returns {Promise<boolean>} True if access granted, false otherwise
     */
    async requestMicrophoneAccess() {
        try {
            this.updateStatus('Requesting microphone access...', 'info');

            // Check if browser supports getUserMedia
            if (!this._checkWebRTCSupport()) {
                return false;
            }

            // Request microphone access with ZIP33G-compatible audio settings
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,   // Matches ZIP33G echo_cancellation
                    noiseSuppression: true,   // Matches ZIP33G noise_reduction
                    autoGainControl: true     // Matches ZIP33G auto gain control
                },
                video: false
            });

            // Stop the tracks immediately - we just wanted to get permission
            // The actual stream will be created when a call is made
            stream.getTracks().forEach(track => track.stop());

            this.updateStatus('Ready to call (microphone access granted)', 'success');
            debugLog('[WebRTC Phone] Microphone access granted');
            return true;

        } catch (err) {
            console.error('[WebRTC Phone] Microphone access denied:', err);
            this.updateStatus('Microphone access denied. Please allow microphone access in browser settings.', 'error');
            return false;
        }
    }

    async createSession() {
        try {
            this.updateStatus('Creating WebRTC session...', 'info');

            verboseLog('Creating WebRTC session:', {
                url: `${this.apiUrl}/api/webrtc/session`,
                extension: this.extension
            });

            const response = await fetch(`${this.apiUrl}/api/webrtc/session`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({extension: this.extension})
            });

            verboseLog('Session creation response:', {
                status: response.status,
                statusText: response.statusText,
                ok: response.ok
            });

            if (!response.ok) {
                const errorText = await response.text();
                verboseLog('Session creation failed - response text:', errorText);
                throw new Error(`Failed to create session: ${response.statusText} - ${errorText}`);
            }

            const data = await response.json();
            verboseLog('Session creation response data:', data);

            if (!data.success) {
                throw new Error('Session creation failed');
            }

            this.sessionId = data.session.session_id;
            this.updateStatus(`Session created: ${this.sessionId}`, 'success');

            verboseLog('Session created successfully:', {
                sessionId: this.sessionId,
                iceServers: data.ice_servers
            });

            // Create peer connection with ICE servers
            this.peerConnection = new RTCPeerConnection(data.ice_servers);

            verboseLog('RTCPeerConnection created with configuration:', data.ice_servers);

            // Handle ICE candidates
            this.peerConnection.onicecandidate = (event) => {
                verboseLog('ICE candidate event:', {
                    candidate: event.candidate,
                    url: event.url
                });
                if (event.candidate) {
                    this.sendICECandidate(event.candidate);
                }
            };

            // Handle connection state changes
            this.peerConnection.onconnectionstatechange = () => {
                debugLog(`Connection state: ${this.peerConnection.connectionState}`);
                verboseLog('Connection state changed:', {
                    connectionState: this.peerConnection.connectionState,
                    iceConnectionState: this.peerConnection.iceConnectionState,
                    iceGatheringState: this.peerConnection.iceGatheringState,
                    signalingState: this.peerConnection.signalingState
                });

                if (this.peerConnection.connectionState === 'connected') {
                    this.updateStatus('Call connected', 'success');
                    this.updateUIState('connected');
                } else if (this.peerConnection.connectionState === 'failed') {
                    verboseLog('Connection FAILED - checking stats...');
                    this.updateStatus('Connection failed', 'error');
                    this.hangup();
                } else if (this.peerConnection.connectionState === 'disconnected') {
                    verboseLog('Connection DISCONNECTED');
                    this.updateStatus('Call disconnected', 'warning');
                    this.hangup();
                }
            };

            // Handle ICE connection state
            this.peerConnection.oniceconnectionstatechange = () => {
                debugLog(`ICE connection state: ${this.peerConnection.iceConnectionState}`);
                verboseLog('ICE connection state changed:', {
                    iceConnectionState: this.peerConnection.iceConnectionState,
                    iceGatheringState: this.peerConnection.iceGatheringState
                });

                if (this.peerConnection.iceConnectionState === 'failed') {
                    verboseLog('ICE connection FAILED - this usually means network connectivity issues');
                }
            };

            // Handle remote track (incoming audio)
            this.peerConnection.ontrack = (event) => {
                debugLog('Received remote track');
                verboseLog('Remote track received:', {
                    track: event.track,
                    streams: event.streams,
                    trackKind: event.track.kind,
                    trackId: event.track.id
                });

                if (this.remoteAudio && event.streams?.length > 0) {
                    this.remoteAudio.srcObject = event.streams[0];

                    // Ensure audio plays - modern browsers require user interaction
                    // Try to play, handling any errors
                    const playPromise = this.remoteAudio.play();
                    if (playPromise !== undefined) {
                        playPromise.then(() => {
                            debugLog('Remote audio playback started successfully');
                            this.updateStatus('Audio connected', 'success');
                        }).catch(err => {
                            debugWarn('Audio autoplay prevented:', err);
                            this.updateStatus('Audio ready (click to unmute if needed)', 'warning');
                        });
                    }
                } else {
                    debugWarn('No remote audio element or streams available');
                }
            };

            return true;
        } catch (error) {
            console.error('Error creating session:', error);
            verboseLog('Error in createSession:', {
                error: error,
                message: error.message,
                stack: error.stack
            });
            this.updateStatus(`Error: ${error.message}`, 'error');
            return false;
        }
    }

    async makeCall() {
        try {
            const targetExt = this.targetExtension?.value ?? '1001';

            verboseLog('makeCall() called:', {
                targetExtension: targetExt
            });

            if (!targetExt) {
                this.updateStatus('Please enter target extension', 'error');
                return;
            }

            this.updateUIState('connecting');
            this.updateStatus('Requesting microphone access...', 'info');

            // Check if browser supports getUserMedia
            if (!this._checkWebRTCSupport()) {
                this.updateUIState('idle');
                return;
            }

            // Get user media (microphone)
            try {
                verboseLog('Requesting user media...');
                this.localStream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true
                    },
                    video: false
                });
                verboseLog('User media granted:', {
                    streamId: this.localStream.id,
                    audioTracks: this.localStream.getAudioTracks().map(t => ({
                        id: t.id,
                        kind: t.kind,
                        label: t.label,
                        enabled: t.enabled,
                        muted: t.muted,
                        readyState: t.readyState
                    }))
                });
                this.updateStatus('Microphone access granted', 'success');
            } catch (err) {
                console.error('Microphone access denied:', err);
                verboseLog('Microphone access error:', {
                    error: err,
                    name: err.name,
                    message: err.message
                });
                this.updateStatus('Microphone access denied. Please allow microphone access.', 'error');
                this.updateUIState('idle');
                return;
            }

            // Create WebRTC session
            verboseLog('Creating WebRTC session...');
            const sessionCreated = await this.createSession();
            if (!sessionCreated) {
                verboseLog('Session creation failed');
                this.updateUIState('idle');
                return;
            }

            // Add local stream to peer connection
            verboseLog('Adding local tracks to peer connection...');
            for (const track of this.localStream.getTracks()) {
                this.peerConnection.addTrack(track, this.localStream);
                debugLog('Added local track to peer connection');
                verboseLog('Track added:', {
                    trackId: track.id,
                    kind: track.kind,
                    label: track.label
                });
            }

            // Create and send offer
            this.updateStatus('Creating call offer...', 'info');
            verboseLog('Creating RTC offer...');
            const offer = await this.peerConnection.createOffer();
            verboseLog('Offer created:', {
                type: offer.type,
                sdpLength: offer.sdp.length
            });

            await this.peerConnection.setLocalDescription(offer);
            verboseLog('Local description set');

            debugLog('SDP Offer created:', offer.sdp);
            verboseLog('Full SDP Offer:', offer.sdp);

            // Send offer to PBX
            verboseLog('Sending offer to PBX:', {
                url: `${this.apiUrl}/api/webrtc/offer`,
                sessionId: this.sessionId
            });

            const offerResponse = await fetch(`${this.apiUrl}/api/webrtc/offer`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    session_id: this.sessionId,
                    sdp: offer.sdp
                })
            });

            verboseLog('Offer response:', {
                status: offerResponse.status,
                statusText: offerResponse.statusText,
                ok: offerResponse.ok
            });

            if (!offerResponse.ok) {
                const errorText = await offerResponse.text();
                verboseLog('Offer failed - response text:', errorText);
                throw new Error(`Failed to send offer: ${offerResponse.statusText} - ${errorText}`);
            }

            const offerData = await offerResponse.json();
            verboseLog('Offer response data:', offerData);

            if (!offerData.success) {
                throw new Error('Offer was rejected by server');
            }

            this.updateStatus(`Calling extension ${targetExt}...`, 'info');
            this.updateUIState('calling');

            // Initiate call to target extension
            verboseLog('Initiating call to target extension:', {
                url: `${this.apiUrl}/api/webrtc/call`,
                sessionId: this.sessionId,
                targetExtension: targetExt
            });

            const callResponse = await fetch(`${this.apiUrl}/api/webrtc/call`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    session_id: this.sessionId,
                    target_extension: targetExt
                })
            });

            verboseLog('Call response:', {
                status: callResponse.status,
                statusText: callResponse.statusText,
                ok: callResponse.ok
            });

            const callData = await callResponse.json();
            verboseLog('Call response data:', callData);

            if (callData.success) {
                this.isCallActive = true;
                this.callId = callData.call_id; // Store call ID for hangup
                this.updateStatus(`Calling ${targetExt}... (Call ID: ${callData.call_id})`, 'success');
                verboseLog('Call initiated successfully:', {
                    callId: callData.call_id
                });
            } else {
                verboseLog('Call initiation failed:', callData);
                throw new Error(callData.error ?? 'Failed to initiate call');
            }

        } catch (error) {
            console.error('Error making call:', error);
            verboseLog('Error in makeCall:', {
                error: error,
                message: error.message,
                stack: error.stack
            });
            this.updateStatus(`Call failed: ${error.message}`, 'error');
            this.hangup();
        }
    }

    async sendICECandidate(candidate) {
        try {
            // Validate session exists before sending ICE candidate
            if (!this.sessionId) {
                debugWarn('Cannot send ICE candidate: no active session');
                verboseLog('ICE candidate send skipped - no session');
                return;
            }

            verboseLog('Sending ICE candidate:', {
                sessionId: this.sessionId,
                candidate: candidate.candidate,
                sdpMid: candidate.sdpMid,
                sdpMLineIndex: candidate.sdpMLineIndex
            });

            await fetch(`${this.apiUrl}/api/webrtc/ice-candidate`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    session_id: this.sessionId,
                    candidate: {
                        candidate: candidate.candidate,
                        sdpMid: candidate.sdpMid,
                        sdpMLineIndex: candidate.sdpMLineIndex
                    }
                })
            });
            debugLog('ICE candidate sent');
            verboseLog('ICE candidate sent successfully');
        } catch (error) {
            console.error('Error sending ICE candidate:', error);
            verboseLog('Error sending ICE candidate:', {
                error: error,
                message: error.message
            });
        }
    }

    /**
     * Send DTMF tone during an active call
     * @param {string} digit - The digit to send (0-9, *, #)
     */
    async sendDTMF(digit) {
        if (!this.isCallActive || !this.sessionId) {
            debugWarn('Cannot send DTMF: No active call');
            return;
        }

        try {
            verboseLog('Sending DTMF digit:', digit);

            // Send DTMF via API
            const response = await fetch(`${this.apiUrl}/api/webrtc/dtmf`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    session_id: this.sessionId,
                    digit: digit,
                    duration: 160  // milliseconds (standard duration)
                })
            });

            verboseLog('DTMF response:', {
                status: response.status,
                statusText: response.statusText
            });

            if (response.ok) {
                const data = await response.json();
                debugLog(`DTMF '${digit}' sent successfully`);
                verboseLog('DTMF send result:', data);

                // Brief visual feedback in status
                const currentStatus = this.statusDiv.textContent;
                this.updateStatus(`Sent: ${digit}`, 'info');
                setTimeout(() => {
                    if (this.isCallActive) {
                        this.updateStatus(currentStatus, 'success');
                    }
                }, 500);
            } else {
                console.error(`Failed to send DTMF '${digit}':`, response.statusText);
                this.updateStatus(`Failed to send: ${digit}`, 'error');
            }
        } catch (error) {
            console.error('Error sending DTMF:', error);
            verboseLog('DTMF send error:', {
                error: error,
                message: error.message
            });
        }
    }

    async hangup() {
        debugLog('Hanging up call');

        // Notify server to terminate the call
        if (this.sessionId || this.callId) {
            try {
                verboseLog('Notifying server of hangup:', {
                    sessionId: this.sessionId,
                    callId: this.callId
                });

                const hangupResponse = await fetch(`${this.apiUrl}/api/webrtc/hangup`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        session_id: this.sessionId,
                        call_id: this.callId
                    })
                });

                if (hangupResponse.ok) {
                    const hangupData = await hangupResponse.json();
                    verboseLog('Server hangup response:', hangupData);
                    debugLog('Server notified of call termination');
                } else {
                    debugWarn('Failed to notify server of hangup:', hangupResponse.statusText);
                    verboseLog('Hangup notification failed:', {
                        status: hangupResponse.status,
                        statusText: hangupResponse.statusText
                    });
                }
            } catch (error) {
                console.error('Error notifying server of hangup:', error);
                verboseLog('Error in hangup notification:', {
                    error: error,
                    message: error.message
                });
            }
        }

        // Stop local stream
        if (this.localStream) {
            for (const track of this.localStream.getTracks()) {
                track.stop();
            }
            this.localStream = null;
        }

        // Close peer connection
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }

        // Reset state
        this.sessionId = null;
        this.callId = null;
        this.isCallActive = false;

        this.updateStatus('Call ended', 'info');
        this.updateUIState('idle');
    }

    toggleMute() {
        if (!this.localStream) return;

        const audioTrack = this.localStream.getAudioTracks()[0];
        if (audioTrack) {
            audioTrack.enabled = !audioTrack.enabled;
            if (this.muteButton) {
                this.muteButton.textContent = audioTrack.enabled ? '🔇 Mute' : '🔊 Unmute';
                this.muteButton.classList.toggle('muted', !audioTrack.enabled);
            }
            this.updateStatus(audioTrack.enabled ? 'Unmuted' : 'Muted', 'info');
        }
    }

    setVolume(value) {
        if (this.remoteAudio) {
            this.remoteAudio.volume = value / 100;
            debugLog(`Volume set to ${value}%`);
        }
    }
}

// Initialize WebRTC phone when admin panel loads
let webrtcPhone = null;

// Default extension for the WebRTC phone if no configuration is set
const DEFAULT_WEBRTC_EXTENSION = 'webrtc-admin';

async function initWebRTCPhone() {
    const apiUrl = window.location.origin;

    // Fetch the configured extension from the server
    let adminExtension = DEFAULT_WEBRTC_EXTENSION; // default fallback

    try {
        const response = await fetch('/api/webrtc/phone-config');
        const data = await response.json();

        if (data.success && data.extension) {
            adminExtension = data.extension;
            debugLog('WebRTC Phone using configured extension:', adminExtension);
        } else {
            debugLog('WebRTC Phone using default extension:', adminExtension);
        }
    } catch (error) {
        debugWarn('Failed to load WebRTC phone config, using default:', error);
    }

    // Create or recreate the WebRTC phone with the configured extension
    if (webrtcPhone) {
        // Clean up existing phone
        if (webrtcPhone.isCallActive) {
            await webrtcPhone.hangup();
        }
    }

    webrtcPhone = new WebRTCPhone(apiUrl, adminExtension);
    debugLog('WebRTC Phone initialized with extension:', adminExtension);

    // Automatically request microphone access on load
    // This prompts the user for permission immediately rather than waiting for a call
    await webrtcPhone.requestMicrophoneAccess();

    // Update the UI to show the configured extension
    const statusDiv = document.getElementById('webrtc-status');
    if (statusDiv) {
        if (adminExtension !== DEFAULT_WEBRTC_EXTENSION) {
            statusDiv.textContent = `Ready to call (Extension: ${adminExtension})`;
        } else {
            statusDiv.textContent = `Ready to call (Default extension)`;
        }
    }
}

// Call this after DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWebRTCPhone);
} else {
    initWebRTCPhone();
}
