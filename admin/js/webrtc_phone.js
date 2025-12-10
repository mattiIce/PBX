/**
 * WebRTC Phone Widget for Admin Panel
 * Enables browser-based calling to extension 1001 without hardware phone
 */

class WebRTCPhone {
    constructor(apiUrl, extension) {
        this.apiUrl = apiUrl;
        this.extension = extension; // Admin's extension for making calls
        this.sessionId = null;
        this.peerConnection = null;
        this.localStream = null;
        this.isCallActive = false;
        this.remoteAudio = null;
        
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
        
        // Create remote audio element
        this.remoteAudio = document.getElementById('webrtc-remote-audio');
        if (!this.remoteAudio) {
            this.remoteAudio = document.createElement('audio');
            this.remoteAudio.id = 'webrtc-remote-audio';
            this.remoteAudio.autoplay = true;
            document.body.appendChild(this.remoteAudio);
        }
        
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
        
        this.updateUIState('idle');
    }
    
    updateStatus(message, type = 'info') {
        if (this.statusDiv) {
            this.statusDiv.textContent = message;
            this.statusDiv.className = `webrtc-status ${type}`;
            console.log(`[WebRTC Phone] ${message}`);
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
            console.log('[WebRTC Phone] Microphone access granted');
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
            
            const response = await fetch(`${this.apiUrl}/api/webrtc/session`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({extension: this.extension})
            });
            
            if (!response.ok) {
                throw new Error(`Failed to create session: ${response.statusText}`);
            }
            
            const data = await response.json();
            if (!data.success) {
                throw new Error('Session creation failed');
            }
            
            this.sessionId = data.session.session_id;
            this.updateStatus(`Session created: ${this.sessionId}`, 'success');
            
            // Create peer connection with ICE servers
            this.peerConnection = new RTCPeerConnection(data.ice_servers);
            
            // Handle ICE candidates
            this.peerConnection.onicecandidate = (event) => {
                if (event.candidate) {
                    this.sendICECandidate(event.candidate);
                }
            };
            
            // Handle connection state changes
            this.peerConnection.onconnectionstatechange = () => {
                console.log(`Connection state: ${this.peerConnection.connectionState}`);
                if (this.peerConnection.connectionState === 'connected') {
                    this.updateStatus('Call connected', 'success');
                    this.updateUIState('connected');
                } else if (this.peerConnection.connectionState === 'failed') {
                    this.updateStatus('Connection failed', 'error');
                    this.hangup();
                } else if (this.peerConnection.connectionState === 'disconnected') {
                    this.updateStatus('Call disconnected', 'warning');
                    this.hangup();
                }
            };
            
            // Handle ICE connection state
            this.peerConnection.oniceconnectionstatechange = () => {
                console.log(`ICE connection state: ${this.peerConnection.iceConnectionState}`);
            };
            
            // Handle remote track (incoming audio)
            this.peerConnection.ontrack = (event) => {
                console.log('Received remote track');
                if (this.remoteAudio) {
                    this.remoteAudio.srcObject = event.streams[0];
                    this.updateStatus('Receiving audio...', 'success');
                }
            };
            
            return true;
        } catch (error) {
            console.error('Error creating session:', error);
            this.updateStatus(`Error: ${error.message}`, 'error');
            return false;
        }
    }
    
    async makeCall() {
        try {
            const targetExt = this.targetExtension ? this.targetExtension.value : '1001';
            
            if (!targetExt) {
                this.updateStatus('Please enter target extension', 'error');
                return;
            }
            
            this.updateUIState('connecting');
            this.updateStatus('Requesting microphone access...', 'info');
            
            // Get user media (microphone)
            try {
                this.localStream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true
                    },
                    video: false
                });
                this.updateStatus('Microphone access granted', 'success');
            } catch (err) {
                console.error('Microphone access denied:', err);
                this.updateStatus('Microphone access denied. Please allow microphone access.', 'error');
                this.updateUIState('idle');
                return;
            }
            
            // Create WebRTC session
            const sessionCreated = await this.createSession();
            if (!sessionCreated) {
                this.updateUIState('idle');
                return;
            }
            
            // Add local stream to peer connection
            this.localStream.getTracks().forEach(track => {
                this.peerConnection.addTrack(track, this.localStream);
                console.log('Added local track to peer connection');
            });
            
            // Create and send offer
            this.updateStatus('Creating call offer...', 'info');
            const offer = await this.peerConnection.createOffer();
            await this.peerConnection.setLocalDescription(offer);
            
            console.log('SDP Offer created:', offer.sdp);
            
            // Send offer to PBX
            const offerResponse = await fetch(`${this.apiUrl}/api/webrtc/offer`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    session_id: this.sessionId,
                    sdp: offer.sdp
                })
            });
            
            if (!offerResponse.ok) {
                throw new Error(`Failed to send offer: ${offerResponse.statusText}`);
            }
            
            const offerData = await offerResponse.json();
            if (!offerData.success) {
                throw new Error('Offer was rejected by server');
            }
            
            this.updateStatus(`Calling extension ${targetExt}...`, 'info');
            this.updateUIState('calling');
            
            // Initiate call to target extension
            const callResponse = await fetch(`${this.apiUrl}/api/webrtc/call`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    session_id: this.sessionId,
                    target_extension: targetExt
                })
            });
            
            const callData = await callResponse.json();
            if (callData.success) {
                this.isCallActive = true;
                this.updateStatus(`Calling ${targetExt}... (Call ID: ${callData.call_id})`, 'success');
            } else {
                throw new Error(callData.error || 'Failed to initiate call');
            }
            
        } catch (error) {
            console.error('Error making call:', error);
            this.updateStatus(`Call failed: ${error.message}`, 'error');
            this.hangup();
        }
    }
    
    async sendICECandidate(candidate) {
        try {
            // Validate session exists before sending ICE candidate
            if (!this.sessionId) {
                console.warn('Cannot send ICE candidate: no active session');
                return;
            }
            
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
            console.log('ICE candidate sent');
        } catch (error) {
            console.error('Error sending ICE candidate:', error);
        }
    }
    
    hangup() {
        console.log('Hanging up call');
        
        // Stop local stream
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }
        
        // Close peer connection
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
        
        // Reset state
        this.sessionId = null;
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
            console.log(`Volume set to ${value}%`);
        }
    }
}

// Initialize WebRTC phone when admin panel loads
let webrtcPhone = null;

async function initWebRTCPhone() {
    const apiUrl = window.location.origin;
    
    // Use a WebRTC-only extension identifier for the admin browser phone
    // Note: This is a virtual extension identifier used for session tracking.
    // The WebRTC backend creates a session for this identifier without requiring
    // a pre-registered extension in the PBX. Outbound calls are made as this
    // virtual extension to any target extension.
    // 
    // If your PBX requires authenticated extensions, you can change this to
    // an actual extension number (e.g., '1000') that exists in your system.
    const adminExtension = 'webrtc-admin'; 
    
    webrtcPhone = new WebRTCPhone(apiUrl, adminExtension);
    console.log('WebRTC Phone initialized');
    
    // Automatically request microphone access on load
    // This prompts the user for permission immediately rather than waiting for a call
    await webrtcPhone.requestMicrophoneAccess();
}

// Call this after DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWebRTCPhone);
} else {
    initWebRTCPhone();
}
