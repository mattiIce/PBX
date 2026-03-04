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

function verboseLog(...args) {
    if (window.WEBRTC_VERBOSE_LOGGING) {
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

        // Tone generation state
        this._audioCtx = null;
        this._ringbackNodes = null; // {osc1, osc2, gain} for ringback tone
        this._ringbackTimer = null; // interval for 2s-on/4s-off cadence
        this._callStatusPollTimer = null; // poll timer for call progress
        this._currentCallState = null; // last known server-side call state

        verboseLog('WebRTC Phone constructor called:', {
            apiUrl: this.apiUrl,
            extension: this.extension
        });

        // Initialize UI elements
        this.initializeUI();
    }

    // ---- Web Audio helpers ----

    /**
     * Lazily create or resume the AudioContext.
     * Must be called from a user-gesture context the first time.
     */
    _ensureAudioCtx() {
        if (!this._audioCtx) {
            this._audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (this._audioCtx.state === 'suspended') {
            this._audioCtx.resume();
        }
        return this._audioCtx;
    }

    /**
     * Play a North American ringback tone (440 Hz + 480 Hz, 2 s on / 4 s off).
     * The tone continues until stopRingbackTone() is called.
     */
    startRingbackTone() {
        if (this._ringbackNodes) return; // already playing
        try {
            const ctx = this._ensureAudioCtx();
            const gain = ctx.createGain();
            gain.gain.value = 0; // start silent
            gain.connect(ctx.destination);

            const osc1 = ctx.createOscillator();
            osc1.frequency.value = 440;
            osc1.connect(gain);
            osc1.start();

            const osc2 = ctx.createOscillator();
            osc2.frequency.value = 480;
            osc2.connect(gain);
            osc2.start();

            this._ringbackNodes = { osc1, osc2, gain };

            // Cadence: 2 s on, 4 s off (total period 6 s)
            const RING_ON_MS = 2000;
            const RING_OFF_MS = 4000;
            let on = true;
            gain.gain.value = 0.15; // start with tone on

            this._ringbackTimer = setInterval(() => {
                on = !on;
                gain.gain.value = on ? 0.15 : 0;
            }, on ? RING_ON_MS : RING_OFF_MS);

            // Use a more precise cadence with two alternating timeouts
            clearInterval(this._ringbackTimer);
            const cycle = () => {
                if (!this._ringbackNodes) return;
                this._ringbackNodes.gain.gain.value = 0.15;
                this._ringbackTimer = setTimeout(() => {
                    if (!this._ringbackNodes) return;
                    this._ringbackNodes.gain.gain.value = 0;
                    this._ringbackTimer = setTimeout(cycle, RING_OFF_MS);
                }, RING_ON_MS);
            };
            cycle();

            verboseLog('Ringback tone started');
        } catch (err) {
            console.error('[WebRTC Phone] Error starting ringback tone:', err);
        }
    }

    /**
     * Stop the ringback tone.
     */
    stopRingbackTone() {
        if (this._ringbackTimer) {
            clearTimeout(this._ringbackTimer);
            this._ringbackTimer = null;
        }
        if (this._ringbackNodes) {
            try {
                this._ringbackNodes.osc1.stop();
                this._ringbackNodes.osc2.stop();
                this._ringbackNodes.gain.disconnect();
            } catch (_) { /* already stopped */ }
            this._ringbackNodes = null;
            verboseLog('Ringback tone stopped');
        }
    }

    /**
     * Play a short DTMF-style tone for a keypad press.
     * Uses the standard DTMF dual-tone frequency pairs.
     * @param {string} digit - 0-9, *, or #
     */
    playDTMFTone(digit) {
        // Standard DTMF frequency pairs
        const DTMF_FREQS = {
            '1': [697, 1209], '2': [697, 1336], '3': [697, 1477],
            '4': [770, 1209], '5': [770, 1336], '6': [770, 1477],
            '7': [852, 1209], '8': [852, 1336], '9': [852, 1477],
            '*': [941, 1209], '0': [941, 1336], '#': [941, 1477],
        };
        const freqs = DTMF_FREQS[digit];
        if (!freqs) return;

        try {
            const ctx = this._ensureAudioCtx();
            const gain = ctx.createGain();
            gain.gain.value = 0.15;
            gain.connect(ctx.destination);

            const osc1 = ctx.createOscillator();
            osc1.frequency.value = freqs[0];
            osc1.connect(gain);

            const osc2 = ctx.createOscillator();
            osc2.frequency.value = freqs[1];
            osc2.connect(gain);

            const now = ctx.currentTime;
            osc1.start(now);
            osc2.start(now);
            // Stop after 150 ms
            osc1.stop(now + 0.15);
            osc2.stop(now + 0.15);
            // Ramp down to avoid click
            gain.gain.setValueAtTime(0.15, now + 0.12);
            gain.gain.linearRampToValueAtTime(0, now + 0.15);

            verboseLog('DTMF tone played for digit:', digit);
        } catch (err) {
            console.error('[WebRTC Phone] Error playing DTMF tone:', err);
        }
    }

    // ---- Call status polling ----

    /**
     * Start polling the server for call status changes.
     * Detects ringing → connected → ended transitions so we can
     * start/stop the ringback tone and update the UI.
     */
    _startCallStatusPolling() {
        if (this._callStatusPollTimer) return;
        this._currentCallState = 'calling';

        const poll = async () => {
            if (!this.callId) {
                this._stopCallStatusPolling();
                return;
            }
            try {
                const response = await fetch(
                    `${this.apiUrl}/api/webrtc/call-status?call_id=${encodeURIComponent(this.callId)}`,
                    { headers: this.getAuthHeaders() }
                );
                if (!response.ok) return;
                const data = await response.json();
                if (data.error) return;

                const newState = data.status;
                if (newState === this._currentCallState) return;

                verboseLog('Call state changed:', this._currentCallState, '->', newState);
                const prevState = this._currentCallState;
                this._currentCallState = newState;

                if (newState === 'ringing' && prevState === 'calling') {
                    // Callee's phone is ringing – play ringback tone
                    this.startRingbackTone();
                    this.updateStatus(`Ringing...`, 'info');
                } else if (newState === 'connected') {
                    // Call answered – stop ringback
                    this.stopRingbackTone();
                    this.updateStatus('Call connected', 'success');
                    this.updateUIState('connected');
                } else if (newState === 'ended') {
                    // Call ended remotely
                    this.stopRingbackTone();
                    this._stopCallStatusPolling();
                    this.updateStatus('Call ended by remote party', 'info');
                    this.hangup();
                }
            } catch (err) {
                verboseLog('Call status poll error:', err);
            }
        };

        // Poll every 500 ms for responsive feedback
        this._callStatusPollTimer = setInterval(poll, 500);
        // Also run immediately
        poll();
    }

    _stopCallStatusPolling() {
        if (this._callStatusPollTimer) {
            clearInterval(this._callStatusPollTimer);
            this._callStatusPollTimer = null;
        }
    }

    /**
     * Get authorization headers including the stored JWT token
     * @returns {Object} Headers object with Content-Type and Authorization
     */
    getAuthHeaders() {
        const headers = {'Content-Type': 'application/json'};
        const token = localStorage.getItem('pbx_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
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
            this.remoteAudio.playsInline = true;
            document.body.appendChild(this.remoteAudio);
        }

        // Ensure audio element is ready for playback
        this.remoteAudio.autoplay = true;
        this.remoteAudio.playsInline = true;
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
                    // Play local DTMF tone for audible feedback
                    this.playDTMFTone(digit);
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
                headers: this.getAuthHeaders(),
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
                    // WebRTC media path to the PBX RTP relay is ready.
                    // This does NOT mean the remote party has answered —
                    // actual call progress (ringing → connected) is driven
                    // by SIP signaling and reported via _startCallStatusPolling().
                    verboseLog('WebRTC media path ready (waiting for SIP call progress)');
                } else if (this.peerConnection.connectionState === 'failed') {
                    verboseLog('Connection FAILED - checking stats...');
                    this.stopRingbackTone();
                    this.updateStatus('Connection failed', 'error');
                    this.hangup();
                } else if (this.peerConnection.connectionState === 'disconnected') {
                    verboseLog('Connection DISCONNECTED');
                    this.stopRingbackTone();
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

            // Wait for ICE gathering to complete so all candidates are
            // included in the SDP.  Without this, the offer may lack
            // server-reflexive / relay candidates required for NAT traversal
            // and the aiortc server-side PC will never establish connectivity.
            debugLog('Waiting for ICE gathering to complete...');
            await new Promise((resolve) => {
                if (this.peerConnection.iceGatheringState === 'complete') {
                    resolve();
                    return;
                }
                const checkState = () => {
                    if (this.peerConnection.iceGatheringState === 'complete') {
                        this.peerConnection.removeEventListener(
                            'icegatheringstatechange', checkState);
                        resolve();
                    }
                };
                this.peerConnection.addEventListener(
                    'icegatheringstatechange', checkState);
                // Timeout after 5 seconds so we don't block forever
                setTimeout(() => {
                    this.peerConnection.removeEventListener(
                        'icegatheringstatechange', checkState);
                    debugLog('ICE gathering timed out after 5 s, proceeding with available candidates');
                    resolve();
                }, 5000);
            });

            // Use the complete local description which now includes all
            // gathered ICE candidates
            const completeOffer = this.peerConnection.localDescription;
            debugLog('SDP Offer created (ICE gathering done):', completeOffer.sdp);
            verboseLog('Full SDP Offer:', completeOffer.sdp);

            // Send offer to PBX
            verboseLog('Sending offer to PBX:', {
                url: `${this.apiUrl}/api/webrtc/offer`,
                sessionId: this.sessionId
            });

            const offerResponse = await fetch(`${this.apiUrl}/api/webrtc/offer`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify({
                    session_id: this.sessionId,
                    sdp: completeOffer.sdp
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

            // Set the SDP answer from the server as the remote description
            // This completes the WebRTC handshake (ICE + DTLS)
            if (offerData.answer_sdp) {
                verboseLog('Setting remote description from server SDP answer');
                const answer = new RTCSessionDescription({
                    type: 'answer',
                    sdp: offerData.answer_sdp,
                });
                await this.peerConnection.setRemoteDescription(answer);
                verboseLog('Remote description set successfully');
            } else {
                verboseLog('No SDP answer from server (legacy mode)');
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
                headers: this.getAuthHeaders(),
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
                this.updateStatus(`Calling ${targetExt}...`, 'info');
                verboseLog('Call initiated successfully:', {
                    callId: callData.call_id
                });

                // Start ringback tone immediately so the caller gets
                // audible feedback while the call is being set up.
                // Polling will stop it once the call connects or ends.
                this.startRingbackTone();

                // Start polling for call status to detect ringing/connected/ended
                this._startCallStatusPolling();
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
                headers: this.getAuthHeaders(),
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
                headers: this.getAuthHeaders(),
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
                const currentStatus = this.statusDiv?.textContent ?? '';
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

        // Stop any local tones and polling
        this.stopRingbackTone();
        this._stopCallStatusPolling();

        // Notify server to terminate the call
        if (this.sessionId || this.callId) {
            try {
                verboseLog('Notifying server of hangup:', {
                    sessionId: this.sessionId,
                    callId: this.callId
                });

                const hangupResponse = await fetch(`${this.apiUrl}/api/webrtc/hangup`, {
                    method: 'POST',
                    headers: this.getAuthHeaders(),
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

    // ------------------------------------------------------------------
    // Ringback tone – standard North American cadence (2s on, 4s off)
    // using 440 Hz + 480 Hz dual-tone via Web Audio API
    // ------------------------------------------------------------------

    _startRingback() {
        if (this._ringbackOsc) return; // already playing
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const gain = ctx.createGain();
            gain.gain.value = 0.15; // gentle volume

            // Two oscillators for the dual-tone ringback
            const osc1 = ctx.createOscillator();
            osc1.frequency.value = 440;
            const osc2 = ctx.createOscillator();
            osc2.frequency.value = 480;

            osc1.connect(gain);
            osc2.connect(gain);
            gain.connect(ctx.destination);

            osc1.start();
            osc2.start();

            this._ringbackCtx = ctx;
            this._ringbackOsc = [osc1, osc2];
            this._ringbackGain = gain;

            // Cadence: 2s on, 4s off, repeat
            let on = true;
            this._ringbackTimer = setInterval(() => {
                on = !on;
                gain.gain.setValueAtTime(on ? 0.15 : 0, ctx.currentTime);
            }, on ? 2000 : 4000);

            // Better cadence: schedule precisely
            clearInterval(this._ringbackTimer);
            const cycle = () => {
                if (!this._ringbackCtx) return;
                gain.gain.setValueAtTime(0.15, ctx.currentTime);
                gain.gain.setValueAtTime(0, ctx.currentTime + 2.0);
                this._ringbackTimer = setTimeout(cycle, 6000);
            };
            cycle();

            debugLog('Ringback tone started');
        } catch (err) {
            debugWarn('Could not start ringback tone:', err);
        }
    }

    _stopRingback() {
        if (this._ringbackTimer) {
            clearTimeout(this._ringbackTimer);
            this._ringbackTimer = null;
        }
        if (this._ringbackOsc) {
            this._ringbackOsc.forEach(o => { try { o.stop(); } catch (_e) { /* ok */ } });
            this._ringbackOsc = null;
        }
        if (this._ringbackCtx) {
            try { this._ringbackCtx.close(); } catch (_e) { /* ok */ }
            this._ringbackCtx = null;
        }
        this._ringbackGain = null;
    }

    // ------------------------------------------------------------------
    // Call status polling – detects ringing / connected / ended
    // ------------------------------------------------------------------

    _startStatusPolling() {
        if (this._statusPollTimer) return;
        this._statusPollTimer = setInterval(() => this._pollCallStatus(), 1000);
        verboseLog('Call status polling started');
    }

    _stopStatusPolling() {
        if (this._statusPollTimer) {
            clearInterval(this._statusPollTimer);
            this._statusPollTimer = null;
            verboseLog('Call status polling stopped');
        }
    }

    async _pollCallStatus() {
        if (!this.sessionId) return;
        try {
            const resp = await fetch(`${this.apiUrl}/api/webrtc/call-status`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify({
                    session_id: this.sessionId,
                    call_id: this.callId
                })
            });
            if (!resp.ok) return;
            const data = await resp.json();
            verboseLog('Call status poll:', data);

            if (data.status === 'ringing') {
                this._startRingback();
                this.updateStatus('Ringing...', 'info');
            } else if (data.status === 'connected') {
                this._stopRingback();
                this.updateStatus('Call connected', 'success');
                this.updateUIState('connected');
            } else if (data.status === 'ended') {
                this._stopRingback();
                this._stopStatusPolling();
                this.updateStatus('Call ended by remote', 'info');
                this.hangup();
            }
        } catch (_err) {
            // Network blip – ignore, will retry on next tick
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
        const token = localStorage.getItem('pbx_token');
        const configHeaders = token ? {'Authorization': `Bearer ${token}`} : {};
        const response = await fetch('/api/webrtc/phone-config', {headers: configHeaders});
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
