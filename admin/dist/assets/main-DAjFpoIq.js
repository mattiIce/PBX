import"./modulepreload-polyfill-B5Qt9EMX.js";window.__DEV__=["localhost","127.0.0.1"].includes(location.hostname)||!["","80","443"].includes(location.port);window.debugLog=window.__DEV__?console.log.bind(console):function(){};window.debugWarn=window.__DEV__?console.warn.bind(console):function(){};window.addEventListener("error",function(e){console.error("JavaScript Error:",e.error||e.message,`
File:`,e.filename,`
Line:`,e.lineno)});window.addEventListener("unhandledrejection",function(e){console.error("Unhandled Promise Rejection:",e.reason)});debugLog("Admin panel loading...",new Date().toISOString());(function(){var e=["https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js","https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js","https://unpkg.com/chart.js@4.4.0/dist/chart.umd.min.js"],t=0;function n(){if(t>=e.length){console.error("All Chart.js CDN sources failed"),window.chartJsLoadFailed=!0;return}var o=document.createElement("script");o.src=e[t],o.onerror=function(){debugWarn("Chart.js CDN "+(t+1)+" failed, trying next..."),t++,n()},o.onload=function(){debugLog("Chart.js loaded successfully from CDN "+(t+1)),window.chartJsLoadFailed=!1},document.head.appendChild(o)}n()})();window.API_BASE=(function(){var e=window.location.port;return e==="9000"||e===""||e==="80"||e==="443"?window.location.origin:window.location.protocol+"//"+(window.location.hostname||"localhost")+":9000"})();window.pbxAuthHeaders=function(){var e={"Content-Type":"application/json"},t=localStorage.getItem("pbx_token");return t&&(e.Authorization="Bearer "+t),e};function b(...e){window.WEBRTC_VERBOSE_LOGGING&&debugLog("[VERBOSE]",...e)}class wn{constructor(t,n){this.apiUrl=t,this.extension=n,this.sessionId=null,this.callId=null,this.peerConnection=null,this.localStream=null,this.isCallActive=!1,this.remoteAudio=null,this._audioCtx=null,this._ringbackNodes=null,this._ringbackTimer=null,this._ringbackSafetyTimer=null,this._callStatusPollTimer=null,this._currentCallState=null,b("WebRTC Phone constructor called:",{apiUrl:this.apiUrl,extension:this.extension}),this.initializeUI()}_ensureAudioCtx(){return this._audioCtx||(this._audioCtx=new(window.AudioContext||window.webkitAudioContext)),this._audioCtx.state==="suspended"&&this._audioCtx.resume(),this._audioCtx}startRingbackTone(){if(!this._ringbackNodes){this._ringbackSafetyTimer&&clearTimeout(this._ringbackSafetyTimer),this._ringbackSafetyTimer=setTimeout(()=>{debugLog("[WebRTC Phone] Ringback safety timeout reached (60s), stopping"),this.stopRingbackTone()},6e4);try{const t=this._ensureAudioCtx(),n=t.createGain();n.gain.value=0,n.connect(t.destination);const o=t.createOscillator();o.frequency.value=440,o.connect(n),o.start();const s=t.createOscillator();s.frequency.value=480,s.connect(n),s.start(),this._ringbackNodes={osc1:o,osc2:s,gain:n};const a=2e3,i=4e3;let c=!0;n.gain.value=.15,this._ringbackTimer=setInterval(()=>{c=!c,n.gain.value=c?.15:0},c?a:i),clearInterval(this._ringbackTimer);const d=()=>{this._ringbackNodes&&(this._ringbackNodes.gain.gain.value=.15,this._ringbackTimer=setTimeout(()=>{this._ringbackNodes&&(this._ringbackNodes.gain.gain.value=0,this._ringbackTimer=setTimeout(d,i))},a))};d(),b("Ringback tone started")}catch(t){console.error("[WebRTC Phone] Error starting ringback tone:",t)}}}stopRingbackTone(){if(this._ringbackSafetyTimer&&(clearTimeout(this._ringbackSafetyTimer),this._ringbackSafetyTimer=null),this._ringbackTimer&&(clearTimeout(this._ringbackTimer),this._ringbackTimer=null),this._ringbackNodes){try{this._ringbackNodes.osc1.stop(),this._ringbackNodes.osc2.stop(),this._ringbackNodes.gain.disconnect()}catch{}this._ringbackNodes=null,b("Ringback tone stopped")}}playDTMFTone(t){const o={1:[697,1209],2:[697,1336],3:[697,1477],4:[770,1209],5:[770,1336],6:[770,1477],7:[852,1209],8:[852,1336],9:[852,1477],"*":[941,1209],0:[941,1336],"#":[941,1477]}[t];if(o)try{const s=this._ensureAudioCtx(),a=s.createGain();a.gain.value=.15,a.connect(s.destination);const i=s.createOscillator();i.frequency.value=o[0],i.connect(a);const c=s.createOscillator();c.frequency.value=o[1],c.connect(a);const d=s.currentTime;i.start(d),c.start(d),i.stop(d+.15),c.stop(d+.15),a.gain.setValueAtTime(.15,d+.12),a.gain.linearRampToValueAtTime(0,d+.15),b("DTMF tone played for digit:",t)}catch(s){console.error("[WebRTC Phone] Error playing DTMF tone:",s)}}_startCallStatusPolling(){if(this._callStatusPollTimer)return;this._currentCallState="calling";const t=async()=>{if(!this.callId){this._stopCallStatusPolling();return}try{const n=await fetch(`${this.apiUrl}/api/webrtc/call-status?call_id=${encodeURIComponent(this.callId)}`,{headers:this.getAuthHeaders()});if(!n.ok)return;const o=await n.json();if(o.error)return;const s=o.status;if(s===this._currentCallState)return;b("Call state changed:",this._currentCallState,"->",s);const a=this._currentCallState;this._currentCallState=s,s==="ringing"&&a==="calling"?(this.startRingbackTone(),this.updateStatus("Ringing...","info")):s==="connected"?(this.stopRingbackTone(),this.updateStatus("Call connected","success"),this.updateUIState("connected")):s==="ended"&&(this.stopRingbackTone(),this._stopCallStatusPolling(),this.updateStatus("Call ended by remote party","info"),this.hangup())}catch(n){b("Call status poll error:",n)}};this._callStatusPollTimer=setInterval(t,500),t()}_stopCallStatusPolling(){this._callStatusPollTimer&&(clearInterval(this._callStatusPollTimer),this._callStatusPollTimer=null)}getAuthHeaders(){const t={"Content-Type":"application/json"},n=localStorage.getItem("pbx_token");return n&&(t.Authorization=`Bearer ${n}`),t}initializeUI(){this.callButton=document.getElementById("webrtc-call-btn"),this.hangupButton=document.getElementById("webrtc-hangup-btn"),this.muteButton=document.getElementById("webrtc-mute-btn"),this.volumeSlider=document.getElementById("webrtc-volume"),this.statusDiv=document.getElementById("webrtc-status"),this.targetExtension=document.getElementById("webrtc-target-ext"),this.keypadSection=document.getElementById("webrtc-keypad-section"),this.remoteAudio=document.getElementById("webrtc-remote-audio"),this.remoteAudio||(this.remoteAudio=document.createElement("audio"),this.remoteAudio.id="webrtc-remote-audio",this.remoteAudio.autoplay=!0,this.remoteAudio.playsInline=!0,document.body.appendChild(this.remoteAudio)),this.remoteAudio.autoplay=!0,this.remoteAudio.playsInline=!0,this.remoteAudio.volume=.8,this.callButton&&this.callButton.addEventListener("click",()=>this.makeCall()),this.hangupButton&&this.hangupButton.addEventListener("click",()=>this.hangup()),this.muteButton&&this.muteButton.addEventListener("click",()=>this.toggleMute()),this.volumeSlider&&this.volumeSlider.addEventListener("input",t=>this.setVolume(t.target.value)),this.setupKeypad(),this.updateUIState("idle")}setupKeypad(){const t=document.querySelectorAll(".keypad-btn");t.forEach(n=>{n.addEventListener("click",o=>{const s=o.currentTarget.getAttribute("data-digit");s&&this.isCallActive&&(this.playDTMFTone(s),this.sendDTMF(s),o.currentTarget.classList.add("pressed"),setTimeout(()=>{o.currentTarget.classList.remove("pressed")},300))})}),b("Keypad initialized with",t.length,"buttons")}updateStatus(t,n="info"){this.statusDiv&&(this.statusDiv.textContent=t,this.statusDiv.className=`webrtc-status ${n}`,debugLog(`[WebRTC Phone] ${t}`),b("Status update:",{message:t,type:n}))}updateUIState(t){this.callButton&&(this.callButton.disabled=t!=="idle"),this.hangupButton&&(this.hangupButton.disabled=t==="idle"),this.muteButton&&(this.muteButton.disabled=t==="idle");const n=t==="connected"||t==="calling";this.keypadSection&&(this.keypadSection.style.display=n?"block":"none"),document.querySelectorAll(".keypad-btn").forEach(s=>{s.disabled=!n})}_checkWebRTCSupport(){if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){const t="WebRTC not supported in this browser or context. Try using HTTPS or a modern browser.";return this.updateStatus(t,"error"),console.error("[WebRTC Phone]",t),!1}return!0}async requestMicrophoneAccess(){try{return this.updateStatus("Requesting microphone access...","info"),this._checkWebRTCSupport()?((await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:!0,noiseSuppression:!0,autoGainControl:!0},video:!1})).getTracks().forEach(n=>n.stop()),this.updateStatus("Ready to call (microphone access granted)","success"),debugLog("[WebRTC Phone] Microphone access granted"),!0):!1}catch(t){return console.error("[WebRTC Phone] Microphone access denied:",t),this.updateStatus("Microphone access denied. Please allow microphone access in browser settings.","error"),!1}}async createSession(){try{this.updateStatus("Creating WebRTC session...","info"),b("Creating WebRTC session:",{url:`${this.apiUrl}/api/webrtc/session`,extension:this.extension});const t=await fetch(`${this.apiUrl}/api/webrtc/session`,{method:"POST",headers:this.getAuthHeaders(),body:JSON.stringify({extension:this.extension})});if(b("Session creation response:",{status:t.status,statusText:t.statusText,ok:t.ok}),!t.ok){const o=await t.text();throw b("Session creation failed - response text:",o),new Error(`Failed to create session: ${t.statusText} - ${o}`)}const n=await t.json();if(b("Session creation response data:",n),!n.success)throw new Error("Session creation failed");return this.sessionId=n.session.session_id,this.updateStatus(`Session created: ${this.sessionId}`,"success"),b("Session created successfully:",{sessionId:this.sessionId,iceServers:n.ice_servers}),this.peerConnection=new RTCPeerConnection(n.ice_servers),b("RTCPeerConnection created with configuration:",n.ice_servers),this.peerConnection.onicecandidate=o=>{b("ICE candidate event:",{candidate:o.candidate,url:o.url}),o.candidate&&this.sendICECandidate(o.candidate)},this.peerConnection.onconnectionstatechange=()=>{debugLog(`Connection state: ${this.peerConnection.connectionState}`),b("Connection state changed:",{connectionState:this.peerConnection.connectionState,iceConnectionState:this.peerConnection.iceConnectionState,iceGatheringState:this.peerConnection.iceGatheringState,signalingState:this.peerConnection.signalingState}),this.peerConnection.connectionState==="connected"?b("WebRTC media path ready (waiting for SIP call progress)"):this.peerConnection.connectionState==="failed"?(b("Connection FAILED - checking stats..."),this.stopRingbackTone(),this.updateStatus("Connection failed","error"),this.hangup()):this.peerConnection.connectionState==="disconnected"&&(b("Connection DISCONNECTED"),this.stopRingbackTone(),this.updateStatus("Call disconnected","warning"),this.hangup())},this.peerConnection.oniceconnectionstatechange=()=>{debugLog(`ICE connection state: ${this.peerConnection.iceConnectionState}`),b("ICE connection state changed:",{iceConnectionState:this.peerConnection.iceConnectionState,iceGatheringState:this.peerConnection.iceGatheringState}),this.peerConnection.iceConnectionState==="failed"&&b("ICE connection FAILED - this usually means network connectivity issues")},this.peerConnection.ontrack=o=>{if(debugLog("Received remote track"),b("Remote track received:",{track:o.track,streams:o.streams,trackKind:o.track.kind,trackId:o.track.id}),this.remoteAudio&&o.streams?.length>0){this.remoteAudio.srcObject=o.streams[0];const s=this.remoteAudio.play();s!==void 0&&s.then(()=>{debugLog("Remote audio playback started successfully"),this.updateStatus("Audio connected","success")}).catch(a=>{debugWarn("Audio autoplay prevented:",a),this.updateStatus("Audio ready (click to unmute if needed)","warning")})}else debugWarn("No remote audio element or streams available")},!0}catch(t){return console.error("Error creating session:",t),b("Error in createSession:",{error:t,message:t.message,stack:t.stack}),this.updateStatus(`Error: ${t.message}`,"error"),!1}}async makeCall(){try{const t=this.targetExtension?.value??"1001";if(b("makeCall() called:",{targetExtension:t}),!t){this.updateStatus("Please enter target extension","error");return}if(this.updateUIState("connecting"),this.updateStatus("Requesting microphone access...","info"),!this._checkWebRTCSupport()){this.updateUIState("idle");return}try{b("Requesting user media..."),this.localStream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:!0,noiseSuppression:!0,autoGainControl:!0},video:!1}),b("User media granted:",{streamId:this.localStream.id,audioTracks:this.localStream.getAudioTracks().map(g=>({id:g.id,kind:g.kind,label:g.label,enabled:g.enabled,muted:g.muted,readyState:g.readyState}))}),this.updateStatus("Microphone access granted","success")}catch(g){console.error("Microphone access denied:",g),b("Microphone access error:",{error:g,name:g.name,message:g.message}),this.updateStatus("Microphone access denied. Please allow microphone access.","error"),this.updateUIState("idle");return}if(b("Creating WebRTC session..."),!await this.createSession()){b("Session creation failed"),this.updateUIState("idle");return}b("Adding local tracks to peer connection...");for(const g of this.localStream.getTracks())this.peerConnection.addTrack(g,this.localStream),debugLog("Added local track to peer connection"),b("Track added:",{trackId:g.id,kind:g.kind,label:g.label});this.updateStatus("Creating call offer...","info"),b("Creating RTC offer...");const o=await this.peerConnection.createOffer();b("Offer created:",{type:o.type,sdpLength:o.sdp.length}),await this.peerConnection.setLocalDescription(o),b("Local description set"),debugLog("Waiting for ICE gathering to complete..."),await new Promise(g=>{if(this.peerConnection.iceGatheringState==="complete"){g();return}const y=()=>{this.peerConnection.iceGatheringState==="complete"&&(this.peerConnection.removeEventListener("icegatheringstatechange",y),g())};this.peerConnection.addEventListener("icegatheringstatechange",y),setTimeout(()=>{this.peerConnection.removeEventListener("icegatheringstatechange",y),debugLog("ICE gathering timed out after 5 s, proceeding with available candidates"),g()},5e3)});const s=this.peerConnection.localDescription;debugLog("SDP Offer created (ICE gathering done):",s.sdp),b("Full SDP Offer:",s.sdp),b("Sending offer to PBX:",{url:`${this.apiUrl}/api/webrtc/offer`,sessionId:this.sessionId});const a=await fetch(`${this.apiUrl}/api/webrtc/offer`,{method:"POST",headers:this.getAuthHeaders(),body:JSON.stringify({session_id:this.sessionId,sdp:s.sdp})});if(b("Offer response:",{status:a.status,statusText:a.statusText,ok:a.ok}),!a.ok){const g=await a.text();throw b("Offer failed - response text:",g),new Error(`Failed to send offer: ${a.statusText} - ${g}`)}const i=await a.json();if(b("Offer response data:",i),!i.success)throw new Error("Offer was rejected by server");if(i.answer_sdp){b("Setting remote description from server SDP answer");const g=new RTCSessionDescription({type:"answer",sdp:i.answer_sdp});await this.peerConnection.setRemoteDescription(g),b("Remote description set successfully")}else b("No SDP answer from server (legacy mode)");this.updateStatus(`Calling extension ${t}...`,"info"),this.updateUIState("calling"),b("Initiating call to target extension:",{url:`${this.apiUrl}/api/webrtc/call`,sessionId:this.sessionId,targetExtension:t});const c=await fetch(`${this.apiUrl}/api/webrtc/call`,{method:"POST",headers:this.getAuthHeaders(),body:JSON.stringify({session_id:this.sessionId,target_extension:t})});b("Call response:",{status:c.status,statusText:c.statusText,ok:c.ok});const d=await c.json();if(b("Call response data:",d),d.success)this.isCallActive=!0,this.callId=d.call_id,this.updateStatus(`Calling ${t}...`,"info"),b("Call initiated successfully:",{callId:d.call_id}),this.startRingbackTone(),this._startCallStatusPolling();else throw b("Call initiation failed:",d),new Error(d.error??"Failed to initiate call")}catch(t){console.error("Error making call:",t),b("Error in makeCall:",{error:t,message:t.message,stack:t.stack}),this.updateStatus(`Call failed: ${t.message}`,"error"),this.hangup()}}async sendICECandidate(t){try{if(!this.sessionId){debugWarn("Cannot send ICE candidate: no active session"),b("ICE candidate send skipped - no session");return}b("Sending ICE candidate:",{sessionId:this.sessionId,candidate:t.candidate,sdpMid:t.sdpMid,sdpMLineIndex:t.sdpMLineIndex}),await fetch(`${this.apiUrl}/api/webrtc/ice-candidate`,{method:"POST",headers:this.getAuthHeaders(),body:JSON.stringify({session_id:this.sessionId,candidate:{candidate:t.candidate,sdpMid:t.sdpMid,sdpMLineIndex:t.sdpMLineIndex}})}),debugLog("ICE candidate sent"),b("ICE candidate sent successfully")}catch(n){console.error("Error sending ICE candidate:",n),b("Error sending ICE candidate:",{error:n,message:n.message})}}async sendDTMF(t){if(!this.isCallActive||!this.sessionId){debugWarn("Cannot send DTMF: No active call");return}try{b("Sending DTMF digit:",t);const n=await fetch(`${this.apiUrl}/api/webrtc/dtmf`,{method:"POST",headers:this.getAuthHeaders(),body:JSON.stringify({session_id:this.sessionId,digit:t,duration:160})});if(b("DTMF response:",{status:n.status,statusText:n.statusText}),n.ok){const o=await n.json();debugLog(`DTMF '${t}' sent successfully`),b("DTMF send result:",o);const s=this.statusDiv?.textContent??"";this.updateStatus(`Sent: ${t}`,"info"),setTimeout(()=>{this.isCallActive&&this.updateStatus(s,"success")},500)}else console.error(`Failed to send DTMF '${t}':`,n.statusText),this.updateStatus(`Failed to send: ${t}`,"error")}catch(n){console.error("Error sending DTMF:",n),b("DTMF send error:",{error:n,message:n.message})}}async hangup(){if(debugLog("Hanging up call"),this.stopRingbackTone(),this._stopCallStatusPolling(),this.sessionId||this.callId)try{b("Notifying server of hangup:",{sessionId:this.sessionId,callId:this.callId});const t=await fetch(`${this.apiUrl}/api/webrtc/hangup`,{method:"POST",headers:this.getAuthHeaders(),body:JSON.stringify({session_id:this.sessionId,call_id:this.callId})});if(t.ok){const n=await t.json();b("Server hangup response:",n),debugLog("Server notified of call termination")}else debugWarn("Failed to notify server of hangup:",t.statusText),b("Hangup notification failed:",{status:t.status,statusText:t.statusText})}catch(t){console.error("Error notifying server of hangup:",t),b("Error in hangup notification:",{error:t,message:t.message})}if(this.localStream){for(const t of this.localStream.getTracks())t.stop();this.localStream=null}this.peerConnection&&(this.peerConnection.close(),this.peerConnection=null),this.sessionId=null,this.callId=null,this.isCallActive=!1,this.updateStatus("Call ended","info"),this.updateUIState("idle")}toggleMute(){if(!this.localStream)return;const t=this.localStream.getAudioTracks()[0];t&&(t.enabled=!t.enabled,this.muteButton&&(this.muteButton.textContent=t.enabled?"🔇 Mute":"🔊 Unmute",this.muteButton.classList.toggle("muted",!t.enabled)),this.updateStatus(t.enabled?"Unmuted":"Muted","info"))}setVolume(t){this.remoteAudio&&(this.remoteAudio.volume=t/100,debugLog(`Volume set to ${t}%`))}_startRingback(){if(!this._ringbackOsc)try{const t=new(window.AudioContext||window.webkitAudioContext),n=t.createGain();n.gain.value=.15;const o=t.createOscillator();o.frequency.value=440;const s=t.createOscillator();s.frequency.value=480,o.connect(n),s.connect(n),n.connect(t.destination),o.start(),s.start(),this._ringbackCtx=t,this._ringbackOsc=[o,s],this._ringbackGain=n;let a=!0;this._ringbackTimer=setInterval(()=>{a=!a,n.gain.setValueAtTime(a?.15:0,t.currentTime)},a?2e3:4e3),clearInterval(this._ringbackTimer);const i=()=>{this._ringbackCtx&&(n.gain.setValueAtTime(.15,t.currentTime),n.gain.setValueAtTime(0,t.currentTime+2),this._ringbackTimer=setTimeout(i,6e3))};i(),debugLog("Ringback tone started")}catch(t){debugWarn("Could not start ringback tone:",t)}}_stopRingback(){if(this._ringbackTimer&&(clearTimeout(this._ringbackTimer),this._ringbackTimer=null),this._ringbackOsc&&(this._ringbackOsc.forEach(t=>{try{t.stop()}catch{}}),this._ringbackOsc=null),this._ringbackCtx){try{this._ringbackCtx.close()}catch{}this._ringbackCtx=null}this._ringbackGain=null}_startStatusPolling(){this._statusPollTimer||(this._statusPollTimer=setInterval(()=>this._pollCallStatus(),1e3),b("Call status polling started"))}_stopStatusPolling(){this._statusPollTimer&&(clearInterval(this._statusPollTimer),this._statusPollTimer=null,b("Call status polling stopped"))}async _pollCallStatus(){if(this.sessionId)try{const t=await fetch(`${this.apiUrl}/api/webrtc/call-status`,{method:"POST",headers:this.getAuthHeaders(),body:JSON.stringify({session_id:this.sessionId,call_id:this.callId})});if(!t.ok)return;const n=await t.json();b("Call status poll:",n),n.status==="ringing"?(this._startRingback(),this.updateStatus("Ringing...","info")):n.status==="connected"?(this._stopRingback(),this.updateStatus("Call connected","success"),this.updateUIState("connected")):n.status==="ended"&&(this._stopRingback(),this._stopStatusPolling(),this.updateStatus("Call ended by remote","info"),this.hangup())}catch{}}}let P=null;const qe="webrtc-admin";async function Ue(){const e=window.location.origin;let t=qe;try{const o=localStorage.getItem("pbx_token"),s=o?{Authorization:`Bearer ${o}`}:{},i=await(await fetch("/api/webrtc/phone-config",{headers:s})).json();i.success&&i.extension?(t=i.extension,debugLog("WebRTC Phone using configured extension:",t)):debugLog("WebRTC Phone using default extension:",t)}catch(o){debugWarn("Failed to load WebRTC phone config, using default:",o)}P&&P.isCallActive&&await P.hangup(),P=new wn(e,t),debugLog("WebRTC Phone initialized with extension:",t),await P.requestMicrophoneAccess();const n=document.getElementById("webrtc-status");n&&(t!==qe?n.textContent=`Ready to call (Extension: ${t})`:n.textContent="Ready to call (Default extension)")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",Ue):Ue();function En(){return`
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

    `}function kn(){const e=`
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
    `;return setTimeout(async()=>{try{const n=await(await fetch("/api/framework/click-to-dial/configs",{headers:pbxAuthHeaders()})).json();xn(n.configs??[])}catch(t){const n=document.getElementById("click-to-dial-configs-list");n&&(n.innerHTML=`<div class="error-box">Error loading configurations: ${escapeHtml(t.message)}</div>`)}},100),e}function xn(e){const t=document.getElementById("click-to-dial-configs-list");if(!t){debugWarn("Click-to-dial configs container not found");return}if(e.length===0){t.innerHTML="<p>No configurations found. Configurations are created automatically when extensions use click-to-dial.</p>";return}const n=`
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
                ${e.map(o=>`
                    <tr>
                        <td>${escapeHtml(String(o.extension))}</td>
                        <td>${o.enabled?"✅ Yes":"❌ No"}</td>
                        <td>${o.auto_answer?"✅ Yes":"❌ No"}</td>
                        <td>${o.browser_notification?"✅ Yes":"❌ No"}</td>
                        <td>
                            <button onclick="viewClickToDialHistory('${escapeHtml(String(o.extension))}')" class="btn-secondary btn-sm">View History</button>
                        </td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;t.innerHTML=n}const In=async e=>{try{const o=(await(await fetch(`/api/framework/click-to-dial/history/${e}`,{headers:pbxAuthHeaders()})).json()).history??[],s=document.getElementById("click-to-dial-history");if(o.length===0){s.innerHTML=`<p>No call history for extension ${escapeHtml(String(e))}</p>`;return}const a=`
            <h4>Call History for Extension ${escapeHtml(String(e))}</h4>
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
                    ${o.map(i=>`
                        <tr>
                            <td>${escapeHtml(String(i.destination))}</td>
                            <td>${escapeHtml(String(i.source))}</td>
                            <td><span class="status-badge status-${escapeHtml(String(i.status))}">${escapeHtml(String(i.status))}</span></td>
                            <td>${new Date(i.initiated_at).toLocaleString()}</td>
                            <td>${i.connected_at?new Date(i.connected_at).toLocaleString():"-"}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;s.innerHTML=a}catch(t){document.getElementById("click-to-dial-history").innerHTML=`<div class="error-box">Error loading history: ${escapeHtml(t.message)}</div>`}};function Sn(){const e=`
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
    `;return setTimeout(()=>{Cn()},100),e}const Cn=async()=>{try{const t=await(await fetch("/api/framework/video-conference/rooms",{headers:pbxAuthHeaders()})).json();Tn(t.rooms??[])}catch(e){document.getElementById("video-rooms-list").innerHTML=`<div class="error-box">Error loading rooms: ${escapeHtml(e.message)}</div>`}};function Tn(e){const t=document.getElementById("video-rooms-list");if(e.length===0){t.innerHTML="<p>No conference rooms created yet.</p>";return}const n=`
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
                ${e.map(o=>`
                    <tr>
                        <td>${escapeHtml(o.room_name)}</td>
                        <td>${escapeHtml(o.owner_extension||"-")}</td>
                        <td>${o.max_participants}</td>
                        <td>${o.enable_4k?"✅":"❌"}</td>
                        <td>${o.enable_screen_share?"✅":"❌"}</td>
                        <td>${o.recording_enabled?"✅":"❌"}</td>
                        <td>${new Date(o.created_at).toLocaleDateString()}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;t.innerHTML=n}function $n(){return`
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
    `}const _n=async()=>{const e=document.getElementById("ai-statistics");e.innerHTML="<p>Loading statistics...</p>";try{const o=(await(await fetch("/api/framework/conversational-ai/statistics",{headers:pbxAuthHeaders()})).json()).statistics??{};e.innerHTML=`
            <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));">
                <div class="stat-card">
                    <div class="stat-value">${o.total_conversations||0}</div>
                    <div class="stat-label">Total Conversations</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${o.active_conversations||0}</div>
                    <div class="stat-label">Active</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${o.total_messages||0}</div>
                    <div class="stat-label">Messages Processed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${o.intents_detected||0}</div>
                    <div class="stat-label">Intents Detected</div>
                </div>
            </div>
            ${o.total_conversations===0?'<p style="margin-top: 15px; color: #666;"><em>Note: No conversations yet. Statistics will appear when the feature is enabled and in use.</em></p>':""}
        `}catch{e.innerHTML='<p style="color: #666;"><em>Statistics unavailable. The API endpoint (/api/framework/conversational-ai/stats) will be available when the feature is enabled with an AI provider configured.</em></p>'}},An=async e=>{e.preventDefault();const t=e.target,n=new FormData(t),o=n.get("provider"),s=n.get("api_key");if(!s){alert("API key is required");return}const a={provider:o,api_key:s,options:{model:n.get("model")||"gpt-4",max_tokens:parseInt(n.get("max_tokens"))||150,temperature:parseFloat(n.get("temperature"))||.7}};try{const c=await(await fetch("/api/framework/conversational-ai/config",{method:"POST",headers:pbxAuthHeaders(),body:JSON.stringify(a)})).json();c.success?alert(`Conversational AI configured with ${c.provider} provider.`):alert(`Error saving config: ${c.error??"Unknown error"}`)}catch(i){alert("Error saving configuration: "+i.message)}};function Bn(){const e=`
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
    `;return setTimeout(()=>{G(),Ye()},100),e}const G=async()=>{try{const n=(await(await fetch("/api/framework/predictive-dialing/campaigns",{headers:pbxAuthHeaders()})).json()).campaigns??[],o=document.getElementById("campaigns-list");if(n.length===0){o.innerHTML='<p style="color: #666;">No campaigns created yet. Framework ready for campaign management.</p>';return}const s=`
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
                    ${n.map(a=>`
                        <tr>
                            <td><strong>${escapeHtml(a.name)}</strong></td>
                            <td>${escapeHtml(a.mode)}</td>
                            <td><span class="status-badge status-${escapeHtml(a.status)}">${escapeHtml(a.status)}</span></td>
                            <td>${a.total_contacts||0}</td>
                            <td>${a.dialed||0}</td>
                            <td>${a.connected||0}</td>
                            <td>
                                <button onclick="toggleCampaign('${escapeHtml(String(a.id))}')" class="btn-secondary btn-sm">
                                    ${a.status==="active"?"Pause":"Start"}
                                </button>
                            </td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;o.innerHTML=s}catch{document.getElementById("campaigns-list").innerHTML='<p style="color: #666;">Framework ready. Campaigns will appear when feature is enabled.</p>'}},Ye=async()=>{try{const n=(await(await fetch("/api/framework/predictive-dialing/statistics",{headers:pbxAuthHeaders()})).json()).statistics??{};document.getElementById("total-campaigns").textContent=n.total_campaigns||0,document.getElementById("active-campaigns").textContent=n.active_campaigns||0,document.getElementById("calls-today").textContent=n.calls_today||0,document.getElementById("contact-rate").textContent=`${n.contact_rate??0}%`}catch{}};function ye(){const e=document.getElementById("create-campaign-dialog");e&&e.remove()}function Pn(){ye(),document.body.insertAdjacentHTML("beforeend",`
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
    `),document.getElementById("create-campaign-form").onsubmit=async function(t){t.preventDefault();const n=new FormData(t.target),o={campaign_id:n.get("campaign_id"),name:n.get("name"),dialing_mode:n.get("dialing_mode")};try{const a=await(await fetch("/api/framework/predictive-dialing/campaign",{method:"POST",headers:pbxAuthHeaders(),body:JSON.stringify(o)})).json();a.success?(alert("Campaign created successfully!"),ye(),G()):alert(`Error creating campaign: ${a.error??"Unknown error"}`)}catch(s){alert("Error creating campaign: "+s.message)}}}const Mn=async e=>{try{await fetch(`/api/framework/predictive-dialing/campaigns/${e}/toggle`,{method:"POST",headers:pbxAuthHeaders()}),await G()}catch(t){alert(`Error: ${t.message}`)}};function Ln(){const e=`
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
    `;return setTimeout(()=>{Q(),Ze()},100),e}const Q=async()=>{try{const n=(await(await fetch("/api/framework/voice-biometrics/profiles",{headers:pbxAuthHeaders()})).json()).profiles??[],o=document.getElementById("biometric-profiles-list");if(n.length===0){o.innerHTML='<p style="color: #666;">No users enrolled yet. Framework ready for voice enrollment.</p>';return}const s=`
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
                    ${n.map(a=>`
                        <tr>
                            <td>${a.extension}</td>
                            <td>${a.name}</td>
                            <td>${new Date(a.enrolled_at).toLocaleDateString()}</td>
                            <td>${a.verification_count||0}</td>
                            <td>${a.last_verified?new Date(a.last_verified).toLocaleString():"Never"}</td>
                            <td><span class="status-badge status-${a.status}">${a.status}</span></td>
                            <td>
                                <button onclick="deleteVoiceProfile('${a.id}')" class="btn-danger btn-sm">Delete</button>
                            </td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;o.innerHTML=s}catch{document.getElementById("biometric-profiles-list").innerHTML='<p style="color: #666;">Framework ready. Voice profiles will appear when feature is enabled.</p>'}},Ze=async()=>{try{const n=(await(await fetch("/api/framework/voice-biometrics/statistics",{headers:pbxAuthHeaders()})).json()).statistics??{};document.getElementById("enrolled-users").textContent=n.enrolled_users||0,document.getElementById("verifications-today").textContent=n.verifications_today||0,document.getElementById("success-rate").textContent=`${n.success_rate??0}%`,document.getElementById("fraud-attempts").textContent=n.fraud_attempts||0}catch{}};function be(){const e=document.getElementById("enroll-user-dialog");e&&e.remove()}function Dn(){be(),document.body.insertAdjacentHTML("beforeend",`
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
    `),document.getElementById("enroll-user-form").onsubmit=async function(t){t.preventDefault();const o={user_id:new FormData(t.target).get("user_id")};try{const a=await(await fetch("/api/framework/voice-biometrics/enroll",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(o)})).json();a.success?(alert(`Enrollment started for ${a.user_id}.

Session ID: ${a.session_id}
Required samples: ${a.required_samples}

Please complete voice sample recording via the phone system.`),be(),Q()):alert(`Error starting enrollment: ${a.error??"Unknown error"}`)}catch(s){alert("Error starting enrollment: "+s.message)}}}const Rn=async e=>{if(confirm("Are you sure you want to delete this voice profile?"))try{await fetch(`/api/framework/voice-biometrics/profile/${e}`,{method:"DELETE",headers:pbxAuthHeaders()}),await Q()}catch(t){alert(`Error: ${t.message}`)}};function Fn(){return`
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
    `}function Nn(){return`
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
    `}function Hn(){return(async()=>{try{const n=await(await fetch("/api/framework/bi-integration/statistics",{headers:pbxAuthHeaders()})).json();document.getElementById("bi-stats-display").innerHTML=`
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">📦</div>
                        <div class="stat-value">${n.total_datasets||0}</div>
                        <div class="stat-label">Datasets</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">📤</div>
                        <div class="stat-value">${n.total_exports||0}</div>
                        <div class="stat-label">Total Exports</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">⏰</div>
                        <div class="stat-value">${n.last_export_time?new Date(n.last_export_time).toLocaleDateString():"Never"}</div>
                        <div class="stat-label">Last Export</div>
                    </div>
                </div>
            `}catch(t){console.error("Error loading BI statistics:",t)}})(),`
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
    `}const jn=async e=>{const t=document.getElementById("bi-export-format")?.value||"csv",n=document.getElementById("bi-date-range")?.value||"last7days",o=event.target,s=o.textContent;o.textContent="Exporting...",o.disabled=!0;try{const i=await(await fetch("/api/framework/bi-integration/export",{method:"POST",headers:pbxAuthHeaders(),body:JSON.stringify({dataset:e,format:t,date_range:n})})).json();i.success?alert(`✅ Export successful!

Dataset: ${i.dataset}
Format: ${i.format}
File: ${i.file_path}

The export has been created on the server.`):alert(`❌ Export failed: ${i.error}`)}catch(a){alert(`❌ Export error: ${a.message}`)}finally{o.textContent=s,o.disabled=!1}};function On(){(async()=>{try{const n=await(await fetch("/api/framework/call-tagging/statistics",{headers:pbxAuthHeaders()})).json();document.getElementById("tagging-stats-display").innerHTML=`
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">🏷️</div>
                        <div class="stat-value">${n.total_calls_tagged||0}</div>
                        <div class="stat-label">Calls Tagged</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">📝</div>
                        <div class="stat-value">${n.custom_tags_count||0}</div>
                        <div class="stat-label">Custom Tags</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">⚙️</div>
                        <div class="stat-value">${n.tagging_rules_count||0}</div>
                        <div class="stat-label">Active Rules</div>
                    </div>
                </div>
            `}catch(t){console.error("Error loading tagging statistics:",t)}})();const e=`
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
    `;return setTimeout(()=>{K(),R()},100),e}const K=async()=>{try{const n=(await(await fetch("/api/framework/call-tagging/tags",{headers:pbxAuthHeaders()})).json()).tags??[],o=document.getElementById("tags-list");if(n.length===0){o.innerHTML='<p style="color: #666;">No tags created yet. Click "+ Create Tag" to add your first tag.</p>';return}const s=`
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                ${n.map(a=>`
                    <div class="tag-badge" style="background: ${a.color||"#4caf50"}; color: white; padding: 8px 15px; border-radius: 20px; display: flex; align-items: center; gap: 8px;">
                        <span>${a.name}</span>
                        <span style="font-size: 11px; opacity: 0.8;">(${a.count||0} calls)</span>
                        <button onclick="deleteTag('${a.id}')" style="background: none; border: none; color: white; cursor: pointer; padding: 0 5px;">×</button>
                    </div>
                `).join("")}
            </div>
        `;o.innerHTML=s}catch{document.getElementById("tags-list").innerHTML='<p class="text-muted">Framework ready. Tags will appear when feature is enabled.</p>'}},R=async()=>{try{const n=(await(await fetch("/api/framework/call-tagging/rules",{headers:pbxAuthHeaders()})).json()).rules??[],o=document.getElementById("tagging-rules-list");if(n.length===0){o.innerHTML='<p style="color: #666;">No auto-tagging rules created yet.</p>';return}const s=`
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
                    ${n.map(a=>`
                        <tr>
                            <td>${a.name}</td>
                            <td>${a.condition}</td>
                            <td><span class="tag-badge" style="background: ${a.tag_color}; color: white; padding: 4px 10px; border-radius: 12px;">${a.tag_name}</span></td>
                            <td>${a.enabled?"✅ Active":"❌ Disabled"}</td>
                            <td>
                                <button onclick="toggleRule('${a.id}')" class="btn-secondary btn-sm">${a.enabled?"Disable":"Enable"}</button>
                                <button onclick="deleteRule('${a.id}')" class="btn-danger btn-sm">Delete</button>
                            </td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;o.innerHTML=s}catch{document.getElementById("tagging-rules-list").innerHTML='<p class="text-muted">Framework ready. Rules will appear when feature is enabled.</p>'}},Ee=async()=>{try{const n=(await(await fetch("/api/framework/call-tagging/statistics",{headers:pbxAuthHeaders()})).json()).statistics??{};document.getElementById("total-tags").textContent=n.total_tags||0,document.getElementById("tagged-calls").textContent=n.tagged_calls||0,document.getElementById("active-rules").textContent=n.active_rules||0,document.getElementById("auto-tagged").textContent=n.auto_tagged_today||0}catch{}};function he(){const e=document.getElementById("create-tag-dialog");e&&e.remove()}function qn(){he(),document.body.insertAdjacentHTML("beforeend",`
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
    `),document.getElementById("create-tag-form").onsubmit=async function(t){t.preventDefault();const n=new FormData(t.target),o={name:n.get("name"),description:n.get("description")||"",color:n.get("color")||"#007bff"};try{const a=await(await fetch("/api/framework/call-tagging/tag",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(o)})).json();a.success?(alert("Tag created successfully!"),he(),K(),Ee()):alert(`Error creating tag: ${a.error??"Unknown error"}`)}catch(s){alert("Error creating tag: "+s.message)}}}function ve(){const e=document.getElementById("create-rule-dialog");e&&e.remove()}function Un(){ve(),document.body.insertAdjacentHTML("beforeend",`
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
    `),document.getElementById("create-rule-form").onsubmit=async function(t){t.preventDefault();const n=new FormData(t.target),o={name:n.get("name"),tag_id:n.get("tag_id"),priority:parseInt(n.get("priority"))||100,conditions:[{type:n.get("condition_type"),value:n.get("condition_value")}]};try{const a=await(await fetch("/api/framework/call-tagging/rule",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(o)})).json();a.success?(alert("Rule created successfully!"),ve(),R(),Ee()):alert(`Error creating rule: ${a.error??"Unknown error"}`)}catch(s){alert("Error creating rule: "+s.message)}}}const Vn=async e=>{if(confirm("Are you sure you want to delete this tag?"))try{await fetch(`/api/framework/call-tagging/tags/${e}`,{method:"DELETE",headers:pbxAuthHeaders()}),await K()}catch(t){alert(`Error: ${t.message}`)}},Jn=async e=>{if(confirm("Are you sure you want to delete this rule?"))try{await fetch(`/api/framework/call-tagging/rules/${e}`,{method:"DELETE",headers:pbxAuthHeaders()}),await R()}catch(t){alert(`Error: ${t.message}`)}},Wn=async e=>{try{await fetch(`/api/framework/call-tagging/rules/${e}/toggle`,{method:"POST",headers:pbxAuthHeaders()}),await R()}catch(t){alert(`Error: ${t.message}`)}};function zn(){return`
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
    `}const Xe=async()=>{const e=document.getElementById("mobile-devices-list");e.innerHTML="<p>Loading device statistics...</p>";try{const n=await(await fetch("/api/mobile-push/devices",{headers:pbxAuthHeaders()})).json(),o=n.devices??[],s=n.statistics??{};let a=`
            <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); margin-bottom: 20px;">
                <div class="stat-card">
                    <div class="stat-value">${s.total_devices||o.length||0}</div>
                    <div class="stat-label">Total Devices</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${s.ios_devices||0}</div>
                    <div class="stat-label">iOS Devices</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${s.android_devices||0}</div>
                    <div class="stat-label">Android Devices</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${s.active_devices||0}</div>
                    <div class="stat-label">Active</div>
                </div>
            </div>
        `;o.length>0?a+=`
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
                        ${o.map(i=>`
                            <tr>
                                <td>${i.extension}</td>
                                <td>${i.platform==="ios"?"📱 iOS":"🤖 Android"}</td>
                                <td>${i.device_model||"Unknown"}</td>
                                <td><code style="font-size: 11px;">${(i.push_token||"").substring(0,20)}...</code></td>
                                <td>${new Date(i.registered_at).toLocaleString()}</td>
                                <td>${i.last_seen?new Date(i.last_seen).toLocaleString():"Never"}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `:a+="<p><em>No devices registered yet. Devices will appear here once the mobile apps are deployed and users register.</em></p>",e.innerHTML=a}catch{e.innerHTML=`
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
        `}},Gn=async e=>{e.preventDefault();const t=e.target,n=new FormData(t),o=n.get("user_id"),s=n.get("device_token");if(!o||!s){alert("User ID and Device Token are required to register a device.");return}const a={user_id:o,device_token:s,platform:n.get("platform")||"unknown"};try{const c=await(await fetch("/api/mobile-push/register",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(a)})).json();c.success?(alert("Device registered successfully!"),Xe()):alert(`Error registering device: ${c.error??"Unknown error"}`)}catch(i){alert("Error registering device: "+i.message)}};function Qn(){return`
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
    `}function Kn(){return`
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
    `}function Yn(){return(async()=>{try{const t=await(await fetch("/api/framework/call-blending/statistics",{headers:pbxAuthHeaders()})).json();document.getElementById("blending-stats-display").innerHTML=`
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">👥</div>
                        <div class="stat-value">${t.total_agents||0}</div>
                        <div class="stat-label">Total Agents</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">✅</div>
                        <div class="stat-value">${t.available_agents||0}</div>
                        <div class="stat-label">Available</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">📞</div>
                        <div class="stat-value">${t.total_blended_calls||0}</div>
                        <div class="stat-label">Blended Calls</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">📊</div>
                        <div class="stat-value">${Math.round((t.actual_blend_ratio||0)*100)}%</div>
                        <div class="stat-label">Inbound Ratio</div>
                    </div>
                </div>
            `}catch(e){console.error("Error loading blending statistics:",e)}})(),(async()=>{try{const n=(await(await fetch("/api/framework/call-blending/agents",{headers:pbxAuthHeaders()})).json()).agents??[],o=document.getElementById("blending-agents-list");if(n.length===0){o.innerHTML='<p style="color: #666;">No agents registered for call blending yet.</p>';return}const s=`
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
                        ${n.map(a=>`
                            <tr>
                                <td>${a.agent_id}</td>
                                <td>${a.extension}</td>
                                <td>
                                    <select onchange="changeAgentMode('${a.agent_id}', this.value)">
                                        <option value="blended" ${a.mode==="blended"?"selected":""}>Blended</option>
                                        <option value="inbound_only" ${a.mode==="inbound_only"?"selected":""}>Inbound Only</option>
                                        <option value="outbound_only" ${a.mode==="outbound_only"?"selected":""}>Outbound Only</option>
                                        <option value="auto" ${a.mode==="auto"?"selected":""}>Auto</option>
                                    </select>
                                </td>
                                <td>
                                    <span class="status-badge ${a.available?"status-online":"status-offline"}">
                                        ${a.available?"✅ Available":"🔴 Unavailable"}
                                    </span>
                                </td>
                                <td>${a.inbound_calls_handled||0}</td>
                                <td>${a.outbound_calls_handled||0}</td>
                                <td>
                                    <button onclick="viewAgentDetails('${a.agent_id}')" class="btn-sm btn-primary">View</button>
                                </td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `;o.innerHTML=s}catch(e){console.error("Error loading agents:",e),document.getElementById("blending-agents-list").innerHTML='<p style="color: #666;">No agents available.</p>'}})(),`
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
    `}function Zn(){return`
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
    `}function Xn(){return(async()=>{try{const t=await(await fetch("/api/framework/geo-redundancy/statistics",{headers:pbxAuthHeaders()})).json();document.getElementById("geo-stats-display").innerHTML=`
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">🌍</div>
                        <div class="stat-value">${t.total_regions||0}</div>
                        <div class="stat-label">Regions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">✅</div>
                        <div class="stat-value">${t.active_region||"None"}</div>
                        <div class="stat-label">Active Region</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">🔄</div>
                        <div class="stat-value">${t.total_failovers||0}</div>
                        <div class="stat-label">Total Failovers</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">🤖</div>
                        <div class="stat-value">${t.auto_failover?"Enabled":"Disabled"}</div>
                        <div class="stat-label">Auto Failover</div>
                    </div>
                </div>
            `}catch(e){console.error("Error loading geo statistics:",e)}})(),(async()=>{try{const n=(await(await fetch("/api/framework/geo-redundancy/regions",{headers:pbxAuthHeaders()})).json()).regions??[],o=document.getElementById("geo-regions-list");if(n.length===0){o.innerHTML='<p style="color: #666;">No regions configured yet. Click "+ Add Region" to create your first region.</p>';return}const s=`
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
                        ${n.map(a=>{let i="#4caf50";return a.status==="failed"?i="#f44336":a.status==="standby"&&(i="#ff9800"),`
                                <tr ${a.is_active?'style="background: #e8f5e9;"':""}>
                                    <td>
                                        ${a.region_id}
                                        ${a.is_active?'<span class="status-badge status-online">ACTIVE</span>':""}
                                    </td>
                                    <td>${a.name}</td>
                                    <td>${a.location}</td>
                                    <td>
                                        <span class="status-badge" style="background: ${i};">
                                            ${a.status.toUpperCase()}
                                        </span>
                                    </td>
                                    <td>${Math.round((a.health_score||0)*100)}%</td>
                                    <td>${a.trunk_count||0}</td>
                                    <td>${a.priority}</td>
                                    <td>
                                        ${a.is_active?"":`<button onclick="triggerFailover('${a.region_id}')" class="btn-sm btn-primary">Activate</button>`}
                                        <button onclick="viewRegionDetails('${a.region_id}')" class="btn-sm">Details</button>
                                    </td>
                                </tr>
                            `}).join("")}
                    </tbody>
                </table>
            `;o.innerHTML=s}catch(e){console.error("Error loading regions:",e),document.getElementById("geo-regions-list").innerHTML='<p style="color: #666;">No regions available.</p>'}})(),`
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
    `}function eo(){return`
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
    `}function to(){return`
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
    `}function no(){return`
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
    `}function oo(){return`
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
    `}window.frameworkFeatures={loadFrameworkOverview:En,loadClickToDialTab:kn,loadVideoConferencingTab:Sn,loadConversationalAITab:$n,loadPredictiveDialingTab:Bn,loadVoiceBiometricsTab:Ln,loadCallQualityPredictionTab:Fn,loadVideoCodecTab:Nn,loadBIIntegrationTab:Hn,loadCallTaggingTab:On,loadMobileAppsTab:zn,loadMobileNumberPortabilityTab:Qn,loadRecordingAnalyticsTab:Kn,loadCallBlendingTab:Yn,loadVoicemailDropTab:Zn,loadGeographicRedundancyTab:Xn,loadDNSSRVFailoverTab:eo,loadSessionBorderControllerTab:to,loadDataResidencyTab:no,loadTeamMessagingTab:oo,viewClickToDialHistory:In,loadConversationalAIStats:_n,loadMobileAppsStats:Xe,exportBIDataset:jn,loadCallTags:K,loadTaggingRules:R,loadTagStatistics:Ee,showCreateTagDialog:qn,showCreateRuleDialog:Un,deleteTag:Vn,deleteRule:Jn,toggleRule:Wn,loadPredictiveDialingCampaigns:G,loadPredictiveDialingStats:Ye,showCreateCampaignDialog:Pn,toggleCampaign:Mn,loadVoiceBiometricProfiles:Q,loadVoiceBiometricStats:Ze,showEnrollUserDialog:Dn,hideEnrollUserDialog:be,deleteVoiceProfile:Rn,hideCreateCampaignDialog:ye,hideCreateTagDialog:he,hideCreateRuleDialog:ve,submitConversationalAIConfig:An,submitMobileAppsConfig:Gn};for(const e of Object.keys(window.frameworkFeatures))typeof window.frameworkFeatures[e]=="function"&&(window[e]=window.frameworkFeatures[e]);const so="80",ao="443",Ve="9000",et=3e4;function m(){const e=document.querySelector('meta[name="api-base-url"]');if(e&&e.content)return e.content;if(window.location.port===Ve||window.location.port===""||window.location.port===so||window.location.port===ao)return window.location.origin;const t=window.location.protocol,n=window.location.hostname||"localhost";return`${t}//${n}:${Ve}`}function u(){const e=localStorage.getItem("pbx_token"),t={"Content-Type":"application/json"};return e&&(t.Authorization=`Bearer ${e}`),t}async function f(e,t={},n=et){if(t.signal)throw new Error("fetchWithTimeout does not support custom abort signals. Use the timeout parameter instead.");const o=new AbortController,s=setTimeout(()=>o.abort(),n);try{return await fetch(e,{...t,signal:o.signal})}catch(a){throw a instanceof Error&&a.name==="AbortError"?new Error("Request timed out"):a}finally{clearTimeout(s)}}class io{_state;_listeners;constructor(t){this._state={...t},this._listeners=new Map}get(t){return this._state[t]}set(t,n){this._state[t]=n;const o=this._listeners.get(t)??[];for(const s of o)s(n)}subscribe(t,n){return this._listeners.has(t)||this._listeners.set(t,[]),this._listeners.get(t).push(n),()=>{const s=this._listeners.get(t);if(!s)return;const a=s.indexOf(n);a>-1&&s.splice(a,1)}}getState(){return{...this._state}}}const Y=new io({currentUser:null,currentExtensions:[],currentTab:"dashboard",isAuthenticated:!1,autoRefreshInterval:null});function l(e){return String(e).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;")}async function ro(e){try{await navigator.clipboard.writeText(e),r("License data copied to clipboard!","success")}catch(t){console.error("Error copying to clipboard:",t),r("Failed to copy to clipboard","error")}}function tt(e){if(!e)return"";try{return new Date(e).toLocaleString()}catch{return e}}function nt(e,t){return e.length<=t?e:e.substring(0,t)+"..."}function ot(e){const n=new Date().getTime()-new Date(e).getTime(),o=Math.floor(n/(1e3*60*60)),s=Math.floor(n%(1e3*60*60)/(1e3*60));return o>0?`${o}h ${s}m`:`${s}m`}function st(e){return{registered:'<span class="badge" style="background: #10b981;">&#x2705; Registered</span>',unregistered:'<span class="badge" style="background: #6b7280;">&#x26AA; Unregistered</span>',failed:'<span class="badge" style="background: #ef4444;">&#x274C; Failed</span>',disabled:'<span class="badge" style="background: #9ca3af;">&#x23F8;&#xFE0F; Disabled</span>',degraded:'<span class="badge" style="background: #f59e0b;">&#x26A0;&#xFE0F; Degraded</span>'}[e]||e}function at(e){return{healthy:'<span class="badge" style="background: #10b981;">&#x1F49A; Healthy</span>',warning:'<span class="badge" style="background: #f59e0b;">&#x26A0;&#xFE0F; Warning</span>',critical:'<span class="badge" style="background: #f59e0b;">&#x1F534; Critical</span>',down:'<span class="badge" style="background: #ef4444;">&#x1F480; Down</span>'}[e]||e}function it(e){return{1:'<span class="badge" style="background: #ef4444;">1 - Highest</span>',2:'<span class="badge" style="background: #f97316;">2 - High</span>',3:'<span class="badge" style="background: #eab308;">3 - Medium</span>',4:'<span class="badge" style="background: #3b82f6;">4 - Low</span>',5:'<span class="badge" style="background: #6b7280;">5 - Lowest</span>'}[e]||`<span class="badge">${e}</span>`}function rt(e){return e>=4.3?"quality-excellent":e>=4?"quality-good":e>=3.6?"quality-fair":e>=3.1?"quality-poor":"quality-bad"}function ct(e){const t=[];if(e.days_of_week){const n=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],o=e.days_of_week.map(s=>n[s]).join(", ");t.push(o)}return e.start_time&&e.end_time&&t.push(`${e.start_time}-${e.end_time}`),e.holidays===!0?t.push("Holidays"):e.holidays===!1&&t.push("Non-holidays"),t.length>0?t.join(" | "):"Always"}function lt(e){const t=JSON.stringify(e,null,2),n=new Blob([t],{type:"application/json"}),o=URL.createObjectURL(n),s=document.createElement("a");s.href=o,s.download=`license_${e.issued_to.replace(/[^a-zA-Z0-9]/g,"_").toLowerCase()}_${new Date().toISOString().split("T")[0]}.json`,document.body.appendChild(s),s.click(),document.body.removeChild(s),URL.revokeObjectURL(o)}window.formatDate=tt;window.truncate=nt;window.getDuration=ot;window.getStatusBadge=st;window.getHealthBadge=at;window.getPriorityBadge=it;window.getQualityClass=rt;window.getScheduleDescription=ct;window.downloadLicense=lt;const co={displayTime:8e3};let dt=!1;function lo(e){dt=e}function r(e,t="info"){if(dt&&t==="error"){debugLog(`[${t.toUpperCase()}] ${e}`);return}const n=document.createElement("div");n.className=`notification notification-${t}`,n.style.cssText=`
        position: fixed;
        top: 80px;
        right: 20px;
        max-width: 400px;
        padding: 15px 20px;
        background: ${t==="success"?"#10b981":t==="error"?"#ef4444":t==="warning"?"#f59e0b":"#3b82f6"};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999;
        animation: slideInRight 0.3s ease-out;
        font-size: 14px;
        line-height: 1.4;
    `;const o=t==="success"?"✓":t==="error"?"✗":t==="warning"?"⚠":"ℹ";n.innerHTML=`<strong>${o}</strong> ${l(e)}`,document.body.appendChild(n),setTimeout(()=>{n.style.animation="slideOutRight 0.3s ease-in",setTimeout(()=>n.remove(),300)},5e3)}function A(e,t=""){const n=`error-${Date.now()}`,o=e.message||e.toString(),s=e.stack||"",a=document.createElement("div");a.id=n,a.className="error-notification",a.style.cssText=`
        position: fixed;
        top: 70px;
        right: 20px;
        max-width: 450px;
        background: #f44336;
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
        font-family: monospace;
        font-size: 13px;
        line-height: 1.4;
    `;let i=`
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
            <strong style="font-size: 16px;">JavaScript Error</strong>
            <button id="close-${n}"
                    style="background: none; border: none; color: white; font-size: 20px; cursor: pointer; padding: 0; margin-left: 10px;">
                ×
            </button>
        </div>
    `;t&&(i+=`<div style="margin-bottom: 5px;"><strong>Context:</strong> ${l(t)}</div>`),i+=`<div style="margin-bottom: 5px;"><strong>Message:</strong> ${l(o)}</div>`,s&&(i+=`
            <details style="margin-top: 10px; cursor: pointer;">
                <summary style="font-weight: bold; margin-bottom: 5px;">Stack Trace (click to expand)</summary>
                <pre style="background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 11px; margin: 5px 0 0 0;">${l(s)}</pre>
            </details>
        `),i+=`
        <div style="margin-top: 10px; font-size: 11px; opacity: 0.9;">
            Tip: Press F12 to open browser console for more details
        </div>
    `,a.innerHTML=i;const c=a.querySelector(`#close-${n}`);c&&c.addEventListener("click",()=>a.remove()),document.body.appendChild(a),setTimeout(()=>{document.getElementById(n)&&(a.style.animation="slideOut 0.3s ease-in",setTimeout(()=>a.remove(),300))},co.displayTime),console.error(`[${t||"Error"}]`,o),s&&console.error("Stack trace:",s)}const uo=1e4;let M=null;function mo(){typeof window.loadEmergencyContacts=="function"&&window.loadEmergencyContacts(),typeof window.loadEmergencyHistory=="function"&&window.loadEmergencyHistory()}function go(){typeof window.loadFraudAlerts=="function"&&window.loadFraudAlerts()}function po(){typeof window.loadCallbackQueue=="function"&&window.loadCallbackQueue()}function fo(e){M&&(clearInterval(M),M=null);const t={dashboard:()=>window.loadDashboard?.(),analytics:()=>window.loadAnalytics?.(),calls:()=>window.loadCalls?.(),qos:()=>window.loadQoSMetrics?.(),emergency:mo,"callback-queue":po,extensions:()=>window.loadExtensions?.(),phones:()=>window.loadRegisteredPhones?.(),atas:()=>window.loadRegisteredATAs?.(),"hot-desking":()=>window.loadHotDeskSessions?.(),voicemail:()=>window.loadVoicemailTab?.(),"fraud-detection":go};t[e]&&(M=setInterval(()=>{try{const n=t[e];typeof n=="function"?n():console.error(`Auto-refresh function for ${e} is not a function:`,n)}catch(n){console.error(`Error during auto-refresh of ${e}:`,n),n instanceof Error&&n.message?.includes("401")&&debugWarn("Authentication error during auto-refresh - user may need to re-login")}},uo)),Y.set("autoRefreshInterval",M)}function L(e){for(const a of document.querySelectorAll(".tab-content"))a.classList.remove("active");for(const a of document.querySelectorAll(".tab-button"))a.classList.remove("active");const t=document.getElementById(e);if(!t)console.error(`CRITICAL: Tab element with id '${e}' not found in DOM`),console.error("This may indicate a UI template issue or incorrect tab name"),console.error(`Current tab name: "${e}"`);else{t.classList.add("active");const a=document.querySelector(`[data-tab="${e}"]`);a?a.classList.add("active"):debugWarn(`Tab button for '${e}' not found`)}Y.set("currentTab",e),fo(e);const n={dashboard:window.loadDashboard,analytics:window.loadAnalytics,extensions:window.loadExtensions,phones:window.loadRegisteredPhones,atas:window.loadRegisteredATAs,provisioning:window.loadProvisioning,"auto-attendant":window.loadAutoAttendantConfig,voicemail:window.loadVoicemailTab,paging:window.loadPagingData,calls:window.loadCalls,config:window.loadConfig,"features-status":window.loadFeaturesStatus,"webrtc-phone":window.loadWebRTCPhoneConfig,"license-management":window.initLicenseManagement,qos:window.loadQoSMetrics,"find-me-follow-me":window.loadFMFMExtensions,"time-routing":window.loadTimeRoutingRules,webhooks:window.loadWebhooks,"hot-desking":window.loadHotDeskSessions,"recording-retention":window.loadRetentionPolicies,"jitsi-integration":window.loadJitsiConfig,"matrix-integration":window.loadMatrixConfig,"espocrm-integration":window.loadEspoCRMConfig,"click-to-dial":window.loadClickToDialTab,"fraud-detection":window.loadFraudDetectionData,"nomadic-e911":window.loadNomadicE911Data,"callback-queue":window.loadCallbackQueue,"mobile-push":window.loadMobilePushConfig,"recording-announcements":window.loadRecordingAnnouncements,"speech-analytics":window.loadSpeechAnalyticsConfigs,compliance:window.loadComplianceData,"crm-integrations":window.loadCRMActivityLog,"opensource-integrations":window.loadOpenSourceIntegrations},o={emergency:[window.loadEmergencyContacts,window.loadEmergencyHistory],codecs:[window.loadCodecStatus,window.loadDTMFConfig],"sip-trunks":[window.loadSIPTrunks,window.loadTrunkHealth],"least-cost-routing":[window.loadLCRRates,window.loadLCRStatistics]},s=n[e];if(s)s();else{const a=o[e];if(a)for(const i of a)i?.()}}function ut(){const e=document.querySelectorAll(".tab-button");for(const n of e)n.addEventListener("click",()=>{const o=n.getAttribute("data-tab");o&&L(o)});const t=document.querySelector(".sidebar");t&&t.addEventListener("keydown",n=>{const o=n,s=o.target;if(!s.classList.contains("tab-button"))return;const a=s.closest(".sidebar-section");if(!a)return;const i=Array.from(a.querySelectorAll(".tab-button")),c=i.indexOf(s);let d=-1;o.key==="ArrowDown"?d=c<i.length-1?c+1:0:o.key==="ArrowUp"?d=c>0?c-1:i.length-1:o.key==="Home"?d=0:o.key==="End"&&(d=i.length-1),d>=0&&(o.preventDefault(),i[d]?.focus())}),document.addEventListener("keydown",n=>{if(n.key==="Escape"){const o=document.querySelector(".modal.active");o&&o.classList.remove("active")}})}async function ke(e,t=5,n=1e3){if(!Array.isArray(e))throw new TypeError("promiseFunctions must be an array");const o=[];for(let s=0;s<e.length;s+=t){const i=e.slice(s,s+t).map(d=>typeof d=="function"?d():d),c=await Promise.allSettled(i);o.push(...c),s+t<e.length&&await new Promise(d=>setTimeout(d,n))}return o}async function xe(){const e=document.getElementById("refresh-all-button");if(!e||e.disabled)return;const t=e.textContent,n=e.disabled;try{e.textContent="⏳ Refreshing All Tabs...",e.disabled=!0,window.suppressErrorNotifications=!0,debugLog("Refreshing all data for ALL tabs...");const o=[];window.loadDashboard&&o.push(()=>window.loadDashboard()),window.loadADStatus&&o.push(()=>window.loadADStatus()),window.loadAnalytics&&o.push(()=>window.loadAnalytics()),window.loadExtensions&&o.push(()=>window.loadExtensions());const a=(await ke(o,5,1e3)).filter(i=>i.status==="rejected");a.length>0&&debugLog(`${a.length} refresh operation(s) failed (expected for unavailable features):`,a.map(i=>i.reason?.message??i.reason)),r("✅ All tabs refreshed successfully","success")}catch(o){const s=o instanceof Error?o.message:String(o);console.error("Error refreshing data:",o),r(`Failed to refresh: ${s}`,"error")}finally{window.suppressErrorNotifications=!1,e.textContent=t,e.disabled=n}}function yo(){const e=document.getElementById("refresh-all-button");e&&e.addEventListener("click",xe)}window.executeBatched=ke;window.refreshAllData=xe;const bo=6e4;async function mt(){try{const e=m(),t=await f(`${e}/api/status`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}: ${t.statusText}`);const n=await t.json();document.getElementById("stat-extensions").textContent=String(n.registered_extensions??0),document.getElementById("stat-calls").textContent=String(n.active_calls??0),document.getElementById("stat-total-calls").textContent=String(n.total_calls??0),document.getElementById("stat-recordings").textContent=String(n.active_recordings??0);const o=document.getElementById("system-status");o&&(o.textContent=`System: ${n.running?"Running":"Stopped"}`,o.classList.remove("connected","disconnected"),o.classList.add("status-badge",n.running?"connected":"disconnected")),Z()}catch(e){console.error("Error loading dashboard:",e);for(const n of["stat-extensions","stat-calls","stat-total-calls","stat-recordings"]){const o=document.getElementById(n);o&&(o.textContent="Error")}const t=e instanceof Error?e.message:String(e);r(`Failed to load dashboard: ${t}`,"error")}}function ho(){mt(),r("Dashboard refreshed","success")}async function Z(){try{const e=m(),t=await f(`${e}/api/integrations/ad/status`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("ad-status-badge");o&&(o.textContent=n.enabled?"Enabled":"Disabled",o.className=`status-badge ${n.enabled?"enabled":"disabled"}`);const s=document.getElementById("ad-connection-status");s&&(s.textContent=n.connected?"✓ Connected":"✗ Not Connected",s.style.color=n.connected?"#10b981":"#ef4444");const a=d=>document.getElementById(d);a("ad-server")&&(a("ad-server").textContent=n.server??"Not configured"),a("ad-auto-provision")&&(a("ad-auto-provision").textContent=n.auto_provision?"Yes":"No"),a("ad-synced-users")&&(a("ad-synced-users").textContent=String(n.synced_users??0));const i=a("ad-error");i&&(i.textContent=n.error??"None",i.style.color=n.error?"#d32f2f":"#10b981");const c=a("ad-sync-btn");c&&(c.disabled=!(n.enabled&&n.connected))}catch(e){console.error("Error loading AD status:",e)}}function vo(){Z(),r("AD status refreshed","success")}async function wo(){const e=document.getElementById("ad-sync-btn");if(!e)return;const t=e.textContent;e.disabled=!0,e.textContent="Syncing...";try{const n=m(),o=await f(`${n}/api/integrations/ad/sync`,{method:"POST",headers:u()},bo);if(!o.ok){const a=await o.json().catch(()=>({error:`HTTP ${o.status}`}));throw new Error(a.error||`HTTP ${o.status}`)}const s=await o.json();s.success?(r(s.message||`Successfully synced ${s.synced_count} users`,"success"),Z()):r(s.error||"Failed to sync users","error")}catch(n){console.error("Error syncing AD users:",n);const s=(n instanceof Error?n.message:String(n))==="Request timed out"?"AD sync timed out. Check server logs.":"Error syncing AD users";r(s,"error")}finally{e.textContent=t,e.disabled=!1}}window.loadDashboard=mt;window.refreshDashboard=ho;window.loadADStatus=Z;window.refreshADStatus=vo;window.syncADUsers=wo;const Eo=1e4;async function U(){const e=document.getElementById("extensions-table-body");if(e){e.innerHTML='<tr><td colspan="7" class="loading">Loading extensions...</td></tr>';try{const t=m(),n=await f(`${t}/api/extensions`,{headers:u()},Eo);if(!n.ok)throw new Error(`HTTP error! status: ${n.status}`);const o=await n.json();if(window.currentExtensions=o,o.length===0){e.innerHTML='<tr><td colspan="7" class="loading">No extensions found.</td></tr>';return}const s=a=>{let i="";return a.ad_synced&&(i+=' <span class="ad-badge" title="Synced from Active Directory">AD</span>'),a.is_admin&&(i+=' <span class="admin-badge" title="Admin Privileges">Admin</span>'),i};e.innerHTML=o.map(a=>`
            <tr>
                <td><strong>${l(a.number)}</strong>${s(a)}</td>
                <td>${l(a.name)}</td>
                <td>${a.email?l(a.email):"Not set"}</td>
                <td class="${a.registered?"status-online":"status-offline"}">
                    ${a.registered?"Online":"Offline"}
                </td>
                <td>${a.allow_external?"Yes":"No"}</td>
                <td>${a.voicemail_enabled?"Set":"Not Set"}</td>
                <td>
                    <button class="btn btn-primary" onclick="editExtension('${l(a.number)}')">Edit</button>
                    ${a.registered?`<button class="btn btn-secondary" onclick="rebootPhone('${l(a.number)}')">Reboot</button>`:""}
                    <button class="btn btn-danger" onclick="deleteExtension('${l(a.number)}')">Delete</button>
                </td>
            </tr>
        `).join("")}catch(t){console.error("Error loading extensions:",t);const o=(t instanceof Error?t.message:String(t))==="Request timed out"?"Request timed out. System may still be starting.":"Error loading extensions";e.innerHTML=`<tr><td colspan="7" class="loading">${o}</td></tr>`}}}function ko(){const e=document.getElementById("add-extension-modal");e&&e.classList.add("active");const t=document.getElementById("add-extension-form");t&&t.reset()}function gt(){const e=document.getElementById("add-extension-modal");e&&e.classList.remove("active")}function xo(e){const t=(window.currentExtensions??[]).find(s=>s.number===e);if(!t)return;const n=s=>document.getElementById(s);n("edit-ext-number")&&(n("edit-ext-number").value=t.number),n("edit-ext-name")&&(n("edit-ext-name").value=t.name),n("edit-ext-email")&&(n("edit-ext-email").value=t.email??""),n("edit-ext-allow-external")&&(n("edit-ext-allow-external").checked=!!t.allow_external),n("edit-ext-is-admin")&&(n("edit-ext-is-admin").checked=!!t.is_admin),n("edit-ext-password")&&(n("edit-ext-password").value="");const o=document.getElementById("edit-extension-modal");o&&o.classList.add("active")}function pt(){const e=document.getElementById("edit-extension-modal");e&&e.classList.remove("active")}async function Io(e){if(confirm(`Are you sure you want to delete extension ${e}?`))try{const t=m(),n=await fetch(`${t}/api/extensions/${e}`,{method:"DELETE",headers:u()});if(n.ok)r("Extension deleted successfully","success"),U();else{const o=await n.json();r(o.error||"Failed to delete extension","error")}}catch(t){console.error("Error deleting extension:",t),r("Failed to delete extension","error")}}async function So(e){if(confirm(`Reboot phone for extension ${e}?`))try{const t=m();(await fetch(`${t}/api/phones/${e}/reboot`,{method:"POST",headers:u()})).ok?r(`Reboot command sent to ${e}`,"success"):r("Failed to reboot phone","error")}catch(t){console.error("Error rebooting phone:",t),r("Failed to reboot phone","error")}}async function Co(){if(confirm("Reboot ALL registered phones?"))try{const e=m();(await fetch(`${e}/api/phones/reboot`,{method:"POST",headers:u()})).ok?r("Reboot command sent to all phones","success"):r("Failed to reboot phones","error")}catch(e){console.error("Error rebooting all phones:",e),r("Failed to reboot phones","error")}}function Je(){const e=document.getElementById("add-extension-form");e&&e.addEventListener("submit",async n=>{n.preventDefault();const o=i=>document.getElementById(i)?.value??"",s=i=>document.getElementById(i)?.checked??!1,a={number:o("new-ext-number"),name:o("new-ext-name"),email:o("new-ext-email"),password:o("new-ext-password"),voicemail_pin:o("new-ext-voicemail-pin"),allow_external:s("new-ext-allow-external"),is_admin:s("new-ext-is-admin")};try{const i=m(),c=await fetch(`${i}/api/extensions`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify(a)}),d=await c.json();c.ok&&d.success?(r("Extension added successfully","success"),gt(),U()):r(d.error||"Failed to add extension","error")}catch(i){console.error("Error adding extension:",i),r("Failed to add extension","error")}});const t=document.getElementById("edit-extension-form");t&&t.addEventListener("submit",async n=>{n.preventDefault();const o=g=>document.getElementById(g)?.value??"",s=g=>document.getElementById(g)?.checked??!1,a=o("edit-ext-number"),i=o("edit-ext-password"),c=o("edit-ext-voicemail-pin"),d={name:o("edit-ext-name"),email:o("edit-ext-email"),allow_external:s("edit-ext-allow-external"),is_admin:s("edit-ext-is-admin")};i&&(d.password=i),c&&(d.voicemail_pin=c);try{const g=m(),y=await fetch(`${g}/api/extensions/${a}`,{method:"PUT",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify(d)}),p=await y.json();y.ok&&p.success?(r("Extension updated successfully","success"),pt(),U()):r(p.error||"Failed to update extension","error")}catch(g){console.error("Error updating extension:",g),r("Failed to update extension","error")}})}window.loadExtensions=U;window.showAddExtensionModal=ko;window.closeAddExtensionModal=gt;window.editExtension=xo;window.closeEditExtensionModal=pt;window.deleteExtension=Io;window.rebootPhone=So;window.rebootAllPhones=Co;document.readyState==="loading"?document.addEventListener("DOMContentLoaded",Je):Je();async function To(){try{const e=m(),t=await fetch(`${e}/api/extensions`,{headers:u()});if(!t.ok)throw new Error(`HTTP error! status: ${t.status}`);const n=await t.json(),o=document.getElementById("vm-extension-select");if(!o)return;o.innerHTML='<option value="">Select Extension</option>';for(const s of n){const a=document.createElement("option");a.value=s.number,a.textContent=`${s.number} - ${s.name}`,o.appendChild(a)}}catch(e){console.error("Error loading voicemail tab:",e),r("Failed to load extensions","error")}}async function ft(){const e=document.getElementById("vm-extension-select")?.value;if(!e){for(const n of["voicemail-pin-section","voicemail-messages-section","voicemail-box-overview"]){const o=document.getElementById(n);o&&(o.style.display="none")}return}for(const n of["voicemail-pin-section","voicemail-messages-section","voicemail-box-overview"]){const o=document.getElementById(n);o&&(o.style.display="block")}const t=document.getElementById("vm-current-extension");t&&(t.textContent=e);try{const n=m(),o=await fetch(`${n}/api/voicemail/${e}`,{headers:u()});if(!o.ok)throw new Error(`HTTP error! status: ${o.status}`);const s=await o.json();$o(s.messages,e)}catch(n){console.error("Error loading voicemail:",n),r("Failed to load voicemail messages","error")}}function $o(e,t){const n=document.getElementById("voicemail-cards-view");if(n){if(!e||e.length===0){n.innerHTML='<div class="info-box">No voicemail messages</div>';return}n.innerHTML=e.map(o=>{const s=new Date(o.timestamp).toLocaleString(),a=o.duration?`${o.duration}s`:"Unknown",i=!o.listened;return`
            <div class="voicemail-card ${i?"unread":""}">
                <div class="voicemail-card-header">
                    <div class="voicemail-from">${l(o.caller_id)}</div>
                    <span class="voicemail-status-badge ${i?"unread":"read"}">
                        ${i?"NEW":"READ"}
                    </span>
                </div>
                <div class="voicemail-card-body">
                    <div>Time: ${s}</div>
                    <div>Duration: ${a}</div>
                </div>
                <div class="voicemail-card-actions">
                    <button class="btn btn-primary btn-sm" onclick="playVoicemail('${t}', '${o.id}')">Play</button>
                    <button class="btn btn-secondary btn-sm" onclick="downloadVoicemail('${t}', '${o.id}')">Download</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteVoicemail('${t}', '${o.id}')">Delete</button>
                </div>
            </div>
        `}).join("")}}async function _o(e,t){try{const o=`${m()}/api/voicemail/${e}/${t}/audio`,s=document.getElementById("vm-audio-player");s&&(s.src=o,s.play()),await yt(e,t)}catch(n){console.error("Error playing voicemail:",n),r("Failed to play voicemail","error")}}async function Ao(e,t){const n=m();window.open(`${n}/api/voicemail/${e}/${t}/audio?download=1`,"_blank")}async function yt(e,t){try{const n=m();await fetch(`${n}/api/voicemail/${e}/${t}/read`,{method:"POST",headers:u()})}catch(n){console.error("Error marking voicemail read:",n)}}async function Bo(e,t){if(confirm("Delete this voicemail message?"))try{const n=m();(await fetch(`${n}/api/voicemail/${e}/${t}`,{method:"DELETE",headers:u()})).ok?(r("Voicemail deleted","success"),ft()):r("Failed to delete voicemail","error")}catch(n){console.error("Error deleting voicemail:",n),r("Failed to delete voicemail","error")}}function Po(){const e=document.getElementById("vm-audio-player");e&&(e.pause(),e.src="");const t=document.getElementById("voicemail-player-section");t&&(t.style.display="none")}function Mo(){const e=document.getElementById("voicemail-cards-view"),t=document.getElementById("voicemail-table-view"),n=document.getElementById("toggle-voicemail-view-btn");if(e&&t){const o=e.style.display!=="none";e.style.display=o?"none":"block",t.style.display=o?"block":"none",n&&(n.textContent=o?"Switch to Card View":"Switch to Table View")}}window.loadVoicemailTab=To;window.loadVoicemailForExtension=ft;window.playVoicemail=_o;window.downloadVoicemail=Ao;window.deleteVoicemail=Bo;window.markVoicemailRead=yt;window.closeVoicemailPlayer=Po;window.toggleVoicemailView=Mo;async function Lo(){const e=document.getElementById("calls-list");if(e){e.innerHTML='<div class="loading">Loading calls...</div>';try{const t=m(),o=await(await f(`${t}/api/calls`,{headers:u()})).json();if(o.length===0){e.innerHTML='<div class="loading">No active calls</div>';return}e.innerHTML=o.map(s=>`
            <div class="call-item"><strong>Call:</strong> ${l(String(s))}</div>
        `).join("")}catch(t){console.error("Error loading calls:",t),e.innerHTML='<div class="loading">Error loading calls</div>'}}}async function Do(){try{const e=m(),t=await f(`${e}/api/config/codecs`,{headers:u()});if(!t.ok)throw new Error(`Failed to load codecs (HTTP ${t.status})`);const n=await t.json(),o=document.getElementById("codec-status");o&&(n.codecs&&n.codecs.length>0?o.innerHTML=n.codecs.map(s=>`<div class="codec-item">${l(s.name)} - <span class="status-${s.enabled?"enabled":"disabled"}">${s.enabled?"Enabled":"Disabled"}</span></div>`).join(""):o.innerHTML='<div class="info-box">No codecs configured</div>')}catch(e){console.error("Error loading codec status:",e);const t=document.getElementById("codec-status");t&&(t.innerHTML='<div class="error-box">Failed to load codec configuration</div>')}}async function Ro(){try{const e=m(),t=await f(`${e}/api/config/dtmf`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("dtmf-mode");o&&(o.value=n.mode??"rfc2833");const s=document.getElementById("dtmf-detection-threshold");s&&(s.value=String(n.threshold??-30))}catch(e){console.error("Error loading DTMF config:",e)}}async function Fo(){try{const e=m(),t={mode:document.getElementById("dtmf-mode")?.value??"rfc2833",threshold:parseInt(document.getElementById("dtmf-detection-threshold")?.value??"-30")};(await fetch(`${e}/api/config/dtmf`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify(t)})).ok?r("DTMF configuration saved","success"):r("Failed to save DTMF configuration","error")}catch(e){console.error("Error saving DTMF config:",e),r("Failed to save DTMF configuration","error")}}async function No(e){e&&e.preventDefault();try{const t=m(),n=document.getElementById("codec-config-form");if(!n)return;const o=new FormData(n),s=Object.fromEntries(o.entries());(await fetch(`${t}/api/config/codecs`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify(s)})).ok?r("Codec configuration saved","success"):r("Failed to save codec configuration","error")}catch(t){console.error("Error saving codec config:",t),r("Failed to save codec configuration","error")}}window.loadCalls=Lo;window.loadCodecStatus=Do;window.loadDTMFConfig=Ro;window.saveDTMFConfig=Fo;window.saveCodecConfig=No;const Ho="Configuration saved successfully. Restart may be required for some changes.";async function jo(){try{const e=m(),t=await f(`${e}/api/config/full`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json();if(n.features){const o=["call-recording","call-transfer","call-hold","conference","voicemail","call-parking","call-queues","presence","music-on-hold","auto-attendant"];for(const s of o){const a=document.getElementById(`feature-${s}`),i=s.replace(/-/g,"_");a&&(a.checked=n.features[i]??!1)}}if(n.voicemail){const o=s=>document.getElementById(s);o("voicemail-max-duration")&&(o("voicemail-max-duration").value=String(n.voicemail.max_duration??120))}}catch(e){console.error("Error loading config:",e),r("Failed to load configuration","error")}}async function Oo(){try{const e=m(),t=await f(`${e}/api/config/features`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json();pe("core-features-table",n.core),pe("advanced-features-table",n.advanced),pe("integration-features-table",n.integrations)}catch(e){console.error("Error loading features status:",e),r("Failed to load feature status","error")}}function pe(e,t){const n=document.getElementById(e);if(n){if(!t||Object.keys(t).length===0){n.innerHTML='<tr><td colspan="3" style="text-align:center;">No features found</td></tr>';return}n.innerHTML=Object.entries(t).map(([o,s])=>{const a=o.replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase()),i=s.enabled?'<span class="badge" style="background:#10b981;">Enabled</span>':'<span class="badge" style="background:#6b7280;">Disabled</span>';return`<tr>
            <td><strong>${l(a)}</strong></td>
            <td>${i}</td>
            <td>${l(s.description)}</td>
        </tr>`}).join("")}}async function bt(e){try{const t=m(),n=document.getElementById(`${e}-form`);if(!n)return;const o=new FormData(n),s=Object.fromEntries(o.entries()),a=await fetch(`${t}/api/config/section`,{method:"PUT",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify({section:e,data:s})});if(a.ok)r(Ho,"success");else{const i=await a.json();r(i.error||"Failed to save configuration","error")}}catch(t){console.error(`Error saving ${e} config:`,t),r(`Failed to save ${e} configuration`,"error")}}async function Ie(){try{const e=m(),t=await f(`${e}/api/ssl/status`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("ssl-status-info");if(o&&(o.textContent=n.enabled?"Enabled":"Disabled",o.className=`status-badge ${n.enabled?"enabled":"disabled"}`),n.certificate){const s=document.getElementById("cert-details-section");s&&(s.style.display="block");const a=document.getElementById("cert-subject"),i=document.getElementById("cert-issuer"),c=document.getElementById("cert-valid-from"),d=document.getElementById("cert-valid-until");a&&(a.value=n.certificate.subject||"N/A"),i&&(i.value=n.certificate.issuer||"N/A"),c&&(c.value=n.certificate.expires||"N/A"),d&&(d.value=n.certificate.expires||"N/A")}}catch(e){console.error("Error loading SSL status:",e)}}async function qo(){try{const e=m(),t=await fetch(`${e}/api/ssl/generate-certificate`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify({})});if(t.ok)r("SSL certificate generated successfully. Server restart required.","success"),Ie();else{const n=await t.json();r(n.error||"Failed to generate SSL certificate","error")}}catch(e){console.error("Error generating SSL certificate:",e),r("Failed to generate SSL certificate","error")}}async function Uo(){await Ie(),r("SSL status refreshed","success")}const Vo=["features-config","voicemail-config","email-config","recording-config","security-config","advanced-features","conference-config","ssl-config"];function We(){for(const e of Vo){const t=document.getElementById(`${e}-form`);t&&t.addEventListener("submit",async n=>{n.preventDefault(),await bt(e)})}}window.loadConfig=jo;window.loadFeaturesStatus=Oo;window.saveConfigSection=bt;window.loadSSLStatus=Ie;window.generateSSLCertificate=qo;window.refreshSSLStatus=Uo;document.readyState==="loading"?document.addEventListener("DOMContentLoaded",We):We();let V=[],D={};async function Jo(){await Promise.all([ht(),Wo(),X(),Se(),vt(),wt()])}async function ht(){try{const e=m(),t=await fetch(`${e}/api/provisioning/vendors`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json();V=n.vendors||[],D=n.models||{},Go(),Qo()}catch(e){console.error("Error loading vendors:",e);const t=document.getElementById("supported-vendors-list");t&&(t.innerHTML="<p>Failed to load supported vendors.</p>")}}async function Wo(){try{const e=m(),t=await fetch(`${e}/api/extensions`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("device-extension");if(!o)return;o.innerHTML='<option value="">Select Extension</option>';for(const s of n){const a=document.createElement("option");a.value=s.number,a.textContent=`${s.number} - ${s.name}`,o.appendChild(a)}}catch(e){console.error("Error loading extensions for provisioning:",e)}}async function X(){try{const e=m(),t=await fetch(`${e}/api/provisioning/devices`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("provisioning-devices-table-body");if(!o)return;const s=Array.isArray(n)?n:n.devices||[];if(s.length===0){o.innerHTML='<tr><td colspan="8">No provisioned devices</td></tr>';return}o.innerHTML=s.map(a=>`
            <tr>
                <td>${l(a.mac_address||"")}</td>
                <td>${l(a.extension_number||a.extension||"")}</td>
                <td>${l(a.device_type||"phone")}</td>
                <td>${l(a.vendor||"")}</td>
                <td>${l(a.model||"")}</td>
                <td>${l(a.created_at||"")}</td>
                <td>${l(a.last_provisioned||"Never")}</td>
                <td><button class="btn btn-danger btn-sm" onclick="deleteDevice('${l(a.mac_address||"")}')">Delete</button></td>
            </tr>
        `).join("")}catch(e){console.error("Error loading devices:",e)}}async function Se(){try{const e=m(),t=await fetch(`${e}/api/provisioning/templates`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("templates-table-body");if(!o)return;const s=n.templates||[];if(s.length===0){o.innerHTML='<tr><td colspan="5">No templates configured</td></tr>';return}o.innerHTML=s.map(a=>{const i=a.name||`${a.vendor||"unknown"}_${a.model||"unknown"}`;return`
            <tr>
                <td>${l(a.vendor||a.manufacturer||"Generic")}</td>
                <td>${l(a.model||"")}</td>
                <td>${l(a.is_custom?"custom":"built-in")}</td>
                <td>${a.size?`${a.size} bytes`:"-"}</td>
                <td><button class="btn btn-sm btn-secondary" onclick="viewTemplate('${l(i)}')">View</button></td>
            </tr>`}).join("")}catch(e){console.error("Error loading templates:",e)}}async function vt(){try{const e=m(),t=await fetch(`${e}/api/provisioning/settings`,{headers:u()});if(!t.ok)return;const n=await t.json(),o=s=>document.getElementById(s);o("provisioning-enabled")&&(o("provisioning-enabled").checked=n.enabled??!1),o("provisioning-url-format")&&(o("provisioning-url-format").value=n.url_format??""),Et()}catch(e){console.error("Error loading provisioning settings:",e)}}async function wt(){try{const e=m(),t=await fetch(`${e}/api/provisioning/phonebook-settings`,{headers:u()});if(!t.ok)return;const n=await t.json(),o=s=>document.getElementById(s);o("ldap-phonebook-enabled")&&(o("ldap-phonebook-enabled").checked=n.ldap_enabled??!1),o("remote-phonebook-enabled")&&(o("remote-phonebook-enabled").checked=n.remote_enabled??!1),kt(),xt()}catch(e){console.error("Error loading phonebook settings:",e)}}async function zo(e){if(confirm(`Delete device ${e}?`))try{const t=m();(await fetch(`${t}/api/provisioning/devices/${e}`,{method:"DELETE",headers:u()})).ok?(r("Device deleted","success"),X()):r("Failed to delete device","error")}catch(t){console.error("Error deleting device:",t),r("Failed to delete device","error")}}function Go(){const e=document.getElementById("device-vendor");if(e){e.innerHTML='<option value="">Select Vendor</option>';for(const t of V){const n=document.createElement("option");n.value=t,n.textContent=t,e.appendChild(n)}}}function Qo(){const e=document.getElementById("supported-vendors-list");if(!e)return;if(V.length===0){e.innerHTML="<p>No supported vendors found.</p>";return}const t=V.map(n=>{const o=D[n]||D[n.toLowerCase()]||[],s=o.length>0?o.map(a=>`<span class="badge">${l(a.toUpperCase())}</span>`).join(" "):"<em>No models</em>";return`<div style="margin-bottom: 8px;">
            <strong>${l(n.charAt(0).toUpperCase()+n.slice(1))}</strong>: ${s}
        </div>`}).join("");e.innerHTML=t}function Ko(){const e=document.getElementById("device-vendor"),t=document.getElementById("device-model");if(!e||!t)return;const n=e.value;if(t.innerHTML="",!n){t.innerHTML='<option value="">Select Vendor First</option>';return}const o=D[n]||D[n.toLowerCase()]||[];if(o.length===0){t.innerHTML='<option value="">No models available</option>';return}t.innerHTML='<option value="">Select Model</option>';for(const s of o){const a=document.createElement("option");a.value=s,a.textContent=s,t.appendChild(a)}}function Et(){const e=document.getElementById("provisioning-enabled"),t=document.getElementById("provisioning-settings");e&&t&&(t.style.display=e.checked?"block":"none")}async function Yo(){try{const e=a=>document.getElementById(a)?.value??"",n={enabled:(a=>document.getElementById(a)?.checked??!1)("provisioning-enabled"),server_ip:e("provisioning-server-ip"),port:parseInt(e("provisioning-port"),10)||9e3,custom_templates_dir:e("provisioning-custom-dir")},o=m();(await fetch(`${o}/api/provisioning/settings`,{method:"PUT",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify(n)})).ok?r("Provisioning settings saved","success"):r("Failed to save provisioning settings","error")}catch(e){console.error("Error saving provisioning settings:",e),r("Failed to save provisioning settings","error")}}function kt(){const e=document.getElementById("ldap-phonebook-enabled"),t=document.getElementById("ldap-phonebook-settings");e&&t&&(t.style.display=e.checked?"block":"none")}function xt(){const e=document.getElementById("remote-phonebook-enabled"),t=document.getElementById("remote-phonebook-settings");e&&t&&(t.style.display=e.checked?"block":"none")}async function Zo(){try{const e=a=>document.getElementById(a)?.value??"",t=a=>document.getElementById(a)?.checked??!1,n={ldap_enabled:t("ldap-phonebook-enabled"),ldap_server:e("ldap-phonebook-server"),ldap_port:parseInt(e("ldap-phonebook-port"),10)||636,ldap_base_dn:e("ldap-phonebook-base"),ldap_bind_user:e("ldap-phonebook-user"),ldap_bind_password:e("ldap-phonebook-password"),ldap_use_tls:t("ldap-phonebook-tls"),ldap_display_name:e("ldap-phonebook-display-name"),remote_enabled:t("remote-phonebook-enabled"),remote_refresh_interval:parseInt(e("remote-phonebook-refresh"),10)||60},o=m();(await fetch(`${o}/api/provisioning/phonebook-settings`,{method:"PUT",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify(n)})).ok?r("Phone book settings saved","success"):r("Failed to save phone book settings","error")}catch(e){console.error("Error saving phonebook settings:",e),r("Failed to save phone book settings","error")}}async function Xo(){try{const e=m();(await fetch(`${e}/api/provisioning/reload-templates`,{method:"POST",headers:u()})).ok?(r("Templates reloaded from disk","success"),Se()):r("Failed to reload templates","error")}catch(e){console.error("Error reloading templates:",e),r("Failed to reload templates","error")}}function It(){const e=document.getElementById("add-device-form");e&&e.reset();const t=document.getElementById("device-model");t&&(t.innerHTML='<option value="">Select Vendor First</option>')}function es(e){r(`Viewing template: ${e}`,"info")}function ze(){const e=document.getElementById("add-device-form");e&&e.addEventListener("submit",async t=>{t.preventDefault();const n=s=>document.getElementById(s)?.value??"",o={mac_address:n("device-mac"),extension_number:n("device-extension"),vendor:n("device-vendor"),model:n("device-model")};if(!o.mac_address||!o.extension_number||!o.vendor||!o.model){r("Please fill in all required fields","error");return}try{const s=m(),a=await fetch(`${s}/api/provisioning/devices`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify(o)}),i=await a.json();a.ok&&i.success?(r(i.message||"Device added successfully","success"),It(),X()):r(i.error||"Failed to add device","error")}catch(s){console.error("Error adding device:",s),r("Failed to add device","error")}})}window.loadProvisioning=Jo;window.loadSupportedVendors=ht;window.loadProvisioningDevices=X;window.loadProvisioningTemplates=Se;window.loadProvisioningSettings=vt;window.loadPhonebookSettings=wt;window.deleteDevice=zo;window.viewTemplate=es;window.updateModelOptions=Ko;window.toggleProvisioningEnabled=Et;window.saveProvisioningSettings=Yo;window.toggleLdapPhonebookSettings=kt;window.toggleRemotePhonebookSettings=xt;window.savePhonebookSettings=Zo;window.reloadTemplates=Xo;window.resetAddDeviceForm=It;document.readyState==="loading"?document.addEventListener("DOMContentLoaded",ze):ze();async function ts(){const e=document.getElementById("registered-phones-table-body");if(e)try{const t=m(),n=await f(`${t}/api/registered-phones`,{headers:u()});if(!n.ok)throw new Error(`HTTP ${n.status}`);const o=await n.json();if(o.length===0){e.innerHTML='<tr><td colspan="5">No registered phones</td></tr>';return}e.innerHTML=o.map(s=>`
            <tr>
                <td>${l(s.extension_number||"")}</td>
                <td>${l(s.ip_address||"")}</td>
                <td>${l(s.mac_address||"")}</td>
                <td>${l(s.user_agent||"")}</td>
                <td>${l(s.last_registered||"")}</td>
            </tr>
        `).join("")}catch(t){console.error("Error loading registered phones:",t),e.innerHTML='<tr><td colspan="5">Error loading phones</td></tr>'}}async function ns(){const e=document.getElementById("registered-atas-table-body");if(e)try{const t=m(),n=await f(`${t}/api/registered-phones/atas`,{headers:u()});if(!n.ok)throw new Error(`HTTP ${n.status}`);const o=await n.json();if(o.length===0){e.innerHTML='<tr><td colspan="6">No registered ATAs</td></tr>';return}e.innerHTML=o.map(s=>{const a=[s.vendor,s.model].filter(Boolean).join(" ");return`
            <tr>
                <td>${l(s.extension_number||"")}</td>
                <td>${l(s.ip_address||"")}</td>
                <td>${l(s.mac_address||"")}</td>
                <td>${l(a)}</td>
                <td>${l(s.user_agent||"")}</td>
                <td>${l(s.last_registered||"")}</td>
            </tr>
        `}).join("")}catch(t){console.error("Error loading ATAs:",t),e.innerHTML='<tr><td colspan="6">Error loading ATAs</td></tr>'}}window.loadRegisteredPhones=ts;window.loadRegisteredATAs=ns;async function os(){try{const e=m(),t=await fetch(`${e}/api/fraud-detection/alerts`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("fraud-alerts-list");if(!o)return;const s=n.alerts??[];if(s.length===0){o.innerHTML='<div class="info-box">No fraud alerts</div>';return}o.innerHTML=s.map(a=>`
            <div class="alert-item ${a.severity||"info"}">
                <strong>${l(a.type||"Alert")}</strong> - ${l(a.description||"")}
                <span class="alert-time">${new Date(a.timestamp).toLocaleString()}</span>
            </div>
        `).join("")}catch(e){console.error("Error loading fraud alerts:",e)}}async function Ce(){try{const e=m(),t=await fetch(`${e}/api/callback-queue/list`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("callback-list");if(!o)return;const s=n.queue??[];if(s.length===0){o.innerHTML='<tr><td colspan="5">No callbacks in queue</td></tr>';return}o.innerHTML=s.map(a=>`
            <tr>
                <td>${l(a.caller||"")}</td>
                <td>${l(a.number||"")}</td>
                <td>${l(a.status||"")}</td>
                <td>${new Date(a.requested_at).toLocaleString()}</td>
                <td>
                    <button class="btn btn-primary btn-sm" onclick="startCallback('${a.id}')">Start</button>
                    <button class="btn btn-danger btn-sm" onclick="cancelCallback('${a.id}')">Cancel</button>
                </td>
            </tr>
        `).join("")}catch(e){console.error("Error loading callback queue:",e)}}async function ss(e){try{const t=m();(await fetch(`${t}/api/callback-queue/start`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify({callback_id:e,agent_id:"admin"})})).ok?(r("Callback initiated","success"),Ce()):r("Failed to start callback","error")}catch(t){console.error("Error starting callback:",t),r("Failed to start callback","error")}}async function as(e){try{const t=m();(await fetch(`${t}/api/callback-queue/cancel`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify({callback_id:e})})).ok?(r("Callback cancelled","success"),Ce()):r("Failed to cancel callback","error")}catch(t){console.error("Error cancelling callback:",t),r("Failed to cancel callback","error")}}async function is(){try{const e=m(),t=await fetch(`${e}/api/mobile-push/devices`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("mobile-devices-list");if(!o)return;const s=n.devices??[];if(s.length===0){o.innerHTML='<div class="info-box">No registered devices</div>';return}o.innerHTML=s.map(a=>`
            <div class="device-item">
                <strong>${l(a.name||a.device_id)}</strong> - ${l(a.platform||"Unknown")}
                <span class="status-badge ${a.active?"enabled":"disabled"}">${a.active?"Active":"Inactive"}</span>
            </div>
        `).join("")}catch(e){console.error("Error loading mobile push devices:",e)}}async function rs(){try{const e=m(),t=await fetch(`${e}/api/framework/speech-analytics/configs`,{headers:u()});if(!t.ok)return;const n=await t.json(),o=document.getElementById("speech-analytics-configs-table");if(o){const s=n.configs??[];s.length===0?o.innerHTML='<div class="info-box">No speech analytics configurations</div>':o.innerHTML=`
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Configuration</th>
                                <th>Status</th>
                                <th>Details</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${s.map(a=>`
                                <tr>
                                    <td>${l(a.name||"N/A")}</td>
                                    <td>${l(a.status||"inactive")}</td>
                                    <td><small>${l(JSON.stringify(a))}</small></td>
                                </tr>
                            `).join("")}
                        </tbody>
                    </table>
                `}}catch(e){console.error("Error loading speech analytics:",e)}}window.loadFraudAlerts=os;window.loadCallbackQueue=Ce;window.startCallback=ss;window.cancelCallback=as;window.loadMobilePushDevices=is;window.loadSpeechAnalyticsConfigs=rs;async function Te(){try{const e=m(),t=await fetch(`${e}/api/emergency/contacts`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("emergency-contacts-table");if(!o)return;const s=n.contacts??[];if(s.length===0){o.innerHTML='<tr><td colspan="5">No emergency contacts</td></tr>';return}o.innerHTML=s.map(a=>`
            <tr>
                <td>${l(a.name||"")}</td>
                <td>${l(a.phone||"")}</td>
                <td>${l(a.role||"")}</td>
                <td>${cs(a.priority)}</td>
                <td><button class="btn btn-danger btn-sm" onclick="deleteEmergencyContact('${a.id}')">Delete</button></td>
            </tr>
        `).join("")}catch(e){console.error("Error loading emergency contacts:",e)}}function cs(e){return`<span class="status-badge ${{high:"danger",medium:"warning",low:"info"}[e??""]??"info"}">${e??"normal"}</span>`}async function St(){try{const e=m(),t=await fetch(`${e}/api/emergency/history`,{headers:u()});if(!t.ok)return;const n=await t.json(),o=document.getElementById("emergency-history-table");if(!o)return;const s=n.history??[];o.innerHTML=s.length===0?'<div class="info-box">No emergency history</div>':s.map(a=>`
                <div class="history-item">
                    <strong>${new Date(a.timestamp).toLocaleString()}</strong> - ${l(a.description||"")}
                </div>
            `).join("")}catch(e){console.error("Error loading emergency history:",e)}}async function ls(e){if(confirm("Delete this emergency contact?"))try{const t=m();(await fetch(`${t}/api/emergency/contacts/${e}`,{method:"DELETE",headers:u()})).ok&&(r("Emergency contact deleted","success"),Te())}catch(t){console.error("Error deleting contact:",t),r("Failed to delete contact","error")}}async function ds(){try{const e=m(),t=await fetch(`${e}/api/framework/nomadic-e911/sites`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("e911-sites-table");if(!o)return;const s=n.sites??[];o.innerHTML=s.length===0?'<div class="info-box">No E911 sites configured</div>':s.map(a=>`
                <div class="site-item">
                    <strong>${l(a.name||"")}</strong> - ${l(a.address||"")}
                    <button class="btn btn-sm btn-secondary" onclick="editE911Site('${a.id}')">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteE911Site('${a.id}')">Delete</button>
                </div>
            `).join("")}catch(e){console.error("Error loading E911 sites:",e);const t=document.getElementById("e911-sites-table");t&&(t.innerHTML='<div class="error-box">Failed to load E911 sites</div>')}}async function us(){try{const e=m(),t=await fetch(`${e}/api/framework/nomadic-e911/locations`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("extension-locations-table");if(o){const s=n.locations??[];o.innerHTML=s.length===0?'<div class="info-box">No locations assigned</div>':s.map(a=>`
                    <div class="location-item">
                        Extension ${l(a.extension)} - ${l(a.site_name||"Unassigned")}
                    </div>
                `).join("")}}catch(e){console.error("Error loading extension locations:",e)}}function ms(){const e=document.getElementById("add-emergency-contact-modal");e&&e.classList.add("active")}function Ct(){const e=document.getElementById("add-emergency-contact-modal");e&&e.classList.remove("active")}function gs(){const e=document.getElementById("trigger-emergency-modal");e&&e.classList.add("active")}function Tt(){const e=document.getElementById("trigger-emergency-modal");e&&e.classList.remove("active")}async function ps(e){e.preventDefault();const t=a=>document.getElementById(a)?.value??"",n=a=>document.getElementById(a)?.checked??!1,o=[];n("method-call")&&o.push("call"),n("method-page")&&o.push("page"),n("method-email")&&o.push("email"),n("method-sms")&&o.push("sms");const s={name:t("emergency-contact-name"),extension:t("emergency-contact-extension"),phone:t("emergency-contact-phone"),email:t("emergency-contact-email"),priority:t("emergency-contact-priority"),notification_methods:o};try{const a=m();(await fetch(`${a}/api/emergency/contacts`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify(s)})).ok?(r("Emergency contact added","success"),Ct(),Te()):r("Failed to add emergency contact","error")}catch(a){console.error("Error adding emergency contact:",a),r("Failed to add emergency contact","error")}}async function fs(e){e.preventDefault();const t=o=>document.getElementById(o)?.value??"",n={type:t("trigger-type"),details:t("trigger-details"),info:t("trigger-info")};try{const o=m();(await fetch(`${o}/api/emergency/trigger`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify(n)})).ok?(r("Emergency notification sent","success"),Tt(),St()):r("Failed to trigger emergency","error")}catch(o){console.error("Error triggering emergency:",o),r("Failed to trigger emergency","error")}}async function ys(){try{const e=m();(await fetch(`${e}/api/emergency/test`,{method:"GET",headers:u()})).ok?r("Test notification sent successfully","success"):r("Failed to send test notification","error")}catch(e){console.error("Error testing emergency notification:",e),r("Failed to send test notification","error")}}window.loadEmergencyContacts=Te;window.loadEmergencyHistory=St;window.deleteEmergencyContact=ls;window.loadE911Sites=ds;window.loadExtensionLocations=us;window.showAddEmergencyContactModal=ms;window.closeAddEmergencyContactModal=Ct;window.showTriggerEmergencyModal=gs;window.closeTriggerEmergencyModal=Tt;window.addEmergencyContact=ps;window.triggerEmergency=fs;window.testEmergencyNotification=ys;async function $t(){try{const e=m(),t=await fetch(`${e}/api/phone-book`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("phone-book-body");if(!o)return;const s=n.entries??[];if(s.length===0){o.innerHTML='<tr><td colspan="5">No phone book entries</td></tr>';return}o.innerHTML=s.map(a=>`
            <tr>
                <td>${l(a.name||"")}</td>
                <td>${l(a.number||"")}</td>
                <td>${l(a.email||"")}</td>
                <td>${l(a.group||"General")}</td>
                <td>
                    <button class="btn btn-primary btn-sm" onclick="editPhoneBookEntry('${a.id}')">Edit</button>
                    <button class="btn btn-danger btn-sm" onclick="deletePhoneBookEntry('${a.id}')">Delete</button>
                </td>
            </tr>
        `).join("")}catch(e){console.error("Error loading phone book:",e)}}async function bs(e){if(confirm("Delete this phone book entry?"))try{const t=m();(await fetch(`${t}/api/phone-book/${e}`,{method:"DELETE",headers:u()})).ok&&(r("Phone book entry deleted","success"),$t())}catch(t){console.error("Error deleting entry:",t),r("Failed to delete entry","error")}}window.loadPhoneBook=$t;window.deletePhoneBookEntry=bs;async function hs(){await Promise.all([ee(),te(),_t()])}async function ee(){try{const e=m(),t=await fetch(`${e}/api/paging/zones`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("paging-zones-table-body");if(!o)return;const s=n.zones??[];if(s.length===0){o.innerHTML='<tr><td colspan="4">No paging zones</td></tr>';return}o.innerHTML=s.map(a=>`
            <tr>
                <td>${l(a.name||"")}</td>
                <td>${l(a.number||"")}</td>
                <td>${a.devices?.length||0} devices</td>
                <td><button class="btn btn-danger btn-sm" onclick="deletePagingZone('${a.id}')">Delete</button></td>
            </tr>
        `).join("")}catch(e){console.error("Error loading paging zones:",e)}}async function te(){try{const e=m(),t=await fetch(`${e}/api/paging/devices`,{headers:u()});if(!t.ok)return;const n=await t.json(),o=document.getElementById("paging-devices-table-body");if(o){const s=n.devices??[];o.innerHTML=s.length===0?'<div class="info-box">No paging devices</div>':s.map(a=>`<div class="device-item">${l(a.name||a.id)}</div>`).join("")}}catch(e){console.error("Error loading paging devices:",e)}}async function _t(){try{const e=m(),t=await fetch(`${e}/api/paging/active`,{headers:u()});if(!t.ok)return;const n=await t.json(),o=document.getElementById("active-pages-table-body");if(o){const s=n.pages??[];o.innerHTML=s.length===0?'<div class="info-box">No active pages</div>':s.map(a=>`<div class="page-item">${l(a.zone)} - ${l(a.initiator)}</div>`).join("")}}catch(e){console.error("Error loading active pages:",e)}}async function vs(e){if(confirm("Delete this paging zone?"))try{const t=m();(await fetch(`${t}/api/paging/zones/${e}`,{method:"DELETE",headers:u()})).ok&&(r("Paging zone deleted","success"),ee())}catch(t){console.error("Error deleting paging zone:",t),r("Failed to delete zone","error")}}async function ws(){const e=prompt("Zone Extension (e.g., 701):");if(!e)return;const t=prompt('Zone Name (e.g., "Warehouse"):');if(!t)return;const n=prompt("Description (optional):")??"",o=prompt("Device ID (optional):")??"",s={extension:e,name:t,description:n,device_id:o};try{const a=m(),c=await(await fetch(`${a}/api/paging/zones`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify(s)})).json();c.success?(r(`Zone ${t} added successfully`,"success"),ee()):r(c.message??"Failed to add zone","error")}catch(a){console.error(`Error adding zone ${t}:`,a),r(`Error adding zone ${t}`,"error")}}async function Es(){const e=prompt('Device ID (e.g., "dac-1"):');if(!e)return;const t=prompt('Device Name (e.g., "Main PA System"):');if(!t)return;const n=prompt('Device Type (e.g., "sip_gateway"):')??"sip_gateway",o=prompt('SIP Address (e.g., "paging@192.168.1.10:5060"):')??"",s={device_id:e,name:t,type:n,sip_address:o};try{const a=m(),c=await(await fetch(`${a}/api/paging/devices`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify(s)})).json();c.success?(r(`Device ${t} added successfully`,"success"),te()):r(c.message??"Failed to add device","error")}catch(a){console.error(`Error adding device ${t}:`,a),r(`Error adding device ${t}`,"error")}}async function ks(e){if(confirm(`Delete paging device ${e}?`))try{const t=m(),o=await(await fetch(`${t}/api/paging/devices/${e}`,{method:"DELETE",headers:u()})).json();o.success?(r(`Device ${e} deleted`,"success"),te()):r(o.message??"Failed to delete device","error")}catch(t){console.error("Error deleting device:",t),r("Error deleting device","error")}}window.loadPagingData=hs;window.loadPagingZones=ee;window.loadPagingDevices=te;window.loadActivePages=_t;window.deletePagingZone=vs;window.showAddZoneModal=ws;window.showAddDeviceModal=Es;window.deletePagingDevice=ks;async function F(){const e=document.getElementById("license-status-container");if(e){e.innerHTML='<div class="loading">Loading license information...</div>';try{const t=m(),n=await f(`${t}/api/license/status`,{headers:u()});if(!n.ok)throw new Error(`HTTP ${n.status}`);const o=await n.json();if(o.success&&o.license){const s=o.license,a=s.status==="active"||s.valid?"badge-success":"badge-danger",i=s.status||(s.valid?"Active":"Invalid");e.innerHTML=`
                <div class="ad-status-grid">
                    <div class="ad-status-item">
                        <strong>License Type</strong>
                        <span>${(s.type||"Unknown").toUpperCase()}</span>
                    </div>
                    <div class="ad-status-item">
                        <strong>Status</strong>
                        <span class="badge ${a}">${i}</span>
                    </div>
                    <div class="ad-status-item">
                        <strong>Issued To</strong>
                        <span>${s.issued_to||"N/A"}</span>
                    </div>
                    <div class="ad-status-item">
                        <strong>Expires</strong>
                        <span>${s.expires_at||s.expiration||"Never"}</span>
                    </div>
                    <div class="ad-status-item">
                        <strong>Extensions</strong>
                        <span>${s.used_extensions??0} / ${s.max_extensions??"Unlimited"}</span>
                    </div>
                    <div class="ad-status-item">
                        <strong>Concurrent Calls</strong>
                        <span>${s.max_concurrent_calls??"Unlimited"}</span>
                    </div>
                    <div class="ad-status-item">
                        <strong>Licensing Enabled</strong>
                        <span class="badge ${s.licensing_enabled!==!1?"badge-success":"badge-warning"}">${s.licensing_enabled!==!1?"Yes":"No (Open Source Mode)"}</span>
                    </div>
                    ${s.key?`<div class="ad-status-item" style="grid-column: 1 / -1;">
                        <strong>License Key</strong>
                        <span style="font-family: monospace; font-size: 12px; word-break: break-all;">${s.key}</span>
                    </div>`:""}
                </div>
            `}else e.innerHTML='<div class="info-box">No license installed. System is running in open-source mode with all features available.</div>'}catch(t){console.error("Error loading license status:",t),e.innerHTML='<div class="error-message">Failed to load license status</div>'}}}async function N(){const e=document.getElementById("license-features-container");if(e){e.innerHTML='<div class="loading">Loading features...</div>';try{const t=m(),n=await f(`${t}/api/license/features`,{headers:u()});if(!n.ok)throw new Error(`HTTP ${n.status}`);const o=await n.json();if(!o.licensing_enabled){e.innerHTML='<div class="info-box">Licensing disabled &mdash; all features are available (open-source mode).</div>';return}const s=o.features??[],a=o.limits??{};let i=`<p style="margin-bottom: 10px;"><strong>License Type:</strong> ${(o.license_type||"unknown").toUpperCase()}</p>`;if(Object.keys(a).length>0){i+='<h4 style="margin: 15px 0 8px;">Limits</h4><div class="ad-status-grid">';for(const[c,d]of Object.entries(a))i+=`<div class="ad-status-item"><strong>${c.replace(/_/g," ")}</strong><span>${d??"Unlimited"}</span></div>`;i+="</div>"}if(s.length>0){i+='<h4 style="margin: 15px 0 8px;">Included Features</h4><div style="display: flex; flex-wrap: wrap; gap: 8px;">';for(const c of s)i+=`<span class="badge badge-success" style="padding: 4px 10px;">${c.replace(/_/g," ")}</span>`;i+="</div>"}e.innerHTML=i}catch(t){console.error("Error loading license features:",t),e.innerHTML='<div class="error-message">Failed to load license features</div>'}}}async function xs(e){e&&e.preventDefault();const t=document.getElementById("generate-license-result"),n=document.getElementById("license-type")?.value,o=document.getElementById("issued-to")?.value?.trim(),s=document.getElementById("expiration-days")?.value,a=document.getElementById("max-extensions")?.value,i=document.getElementById("max-concurrent-calls")?.value;if(!n||!o){r("License type and organization/person are required","error");return}const c={type:n,issued_to:o};s&&(c.expiration_days=parseInt(s,10)),a&&(c.max_extensions=parseInt(a,10)),i&&(c.max_concurrent_calls=parseInt(i,10));try{const d=m(),y=await(await f(`${d}/api/license/generate`,{method:"POST",headers:u(),body:JSON.stringify(c)})).json();if(y.success&&y.license){r("License generated successfully","success");const p=JSON.stringify(y.license,null,2);t&&(t.innerHTML=`
                    <div class="config-section" style="margin-top: 10px; background: #e8f5e9; border: 1px solid #4caf50;">
                        <h4 style="margin-top: 0; color: #2e7d32;">Generated License</h4>
                        <pre style="background: #263238; color: #eeffff; padding: 15px; border-radius: 4px; overflow-x: auto; font-size: 12px; max-height: 300px;">${p}</pre>
                        <div class="action-buttons" style="margin-top: 10px;">
                            <button class="btn btn-primary" onclick="navigator.clipboard.writeText(document.getElementById('generated-license-json').textContent).then(()=>alert('Copied!'))">📋 Copy to Clipboard</button>
                            <button class="btn btn-success" onclick="autoInstallGeneratedLicense()">📥 Install This License</button>
                        </div>
                        <pre id="generated-license-json" style="display:none;">${p}</pre>
                    </div>
                `)}else r(y.error||"Failed to generate license","error"),t&&(t.innerHTML=`<div class="error-message">${y.error||"Failed to generate license"}</div>`)}catch(d){console.error("Error generating license:",d),r("Failed to generate license","error"),t&&(t.innerHTML='<div class="error-message">Failed to generate license</div>')}}async function Is(){const e=document.getElementById("generated-license-json");if(e)try{const t=JSON.parse(e.textContent||"{}");await At(t,!1)}catch(t){console.error("Error auto-installing license:",t),r("Failed to install generated license","error")}}async function Ss(e){e&&e.preventDefault();const t=document.getElementById("license-data"),n=document.getElementById("enforce-licensing"),o=document.getElementById("install-license-result");if(!t||!t.value.trim()){r("Please enter license data (JSON)","error");return}let s;try{s=JSON.parse(t.value.trim())}catch{r("Invalid JSON format. Please check the license data.","error");return}const a=n?.checked??!1;try{await At(s,a),t.value="",n&&(n.checked=!1)}catch(i){console.error("Error installing license:",i),r("Failed to install license","error"),o&&(o.innerHTML='<div class="error-message">Failed to install license</div>')}}async function At(e,t){const n=document.getElementById("install-license-result"),o=m(),a=await(await f(`${o}/api/license/install`,{method:"POST",headers:u(),body:JSON.stringify({license_data:e,enforce_licensing:t})})).json();a.success?(r(a.message||"License installed successfully","success"),n&&(n.innerHTML=`<div class="info-box" style="border-left-color: #4caf50;">${a.message||"License installed successfully"}</div>`),F(),N()):(r(a.error||"Failed to install license","error"),n&&(n.innerHTML=`<div class="error-message">${a.error||"Failed to install license"}</div>`))}async function Cs(e){const t=document.getElementById("licensing-toggle-result"),n=e?"enable":"disable";if(confirm(`Are you sure you want to ${n} licensing?`))try{const o=m(),a=await(await f(`${o}/api/license/toggle`,{method:"POST",headers:u(),body:JSON.stringify({enabled:e})})).json();a.success?(r(a.message||`Licensing ${n}d successfully`,"success"),t&&(t.innerHTML=`<div class="info-box" style="border-left-color: #4caf50;">${a.message||`Licensing ${n}d successfully`}</div>`),F(),N()):(r(a.error||`Failed to ${n} licensing`,"error"),t&&(t.innerHTML=`<div class="error-message">${a.error||`Failed to ${n} licensing`}</div>`))}catch(o){console.error("Error toggling licensing:",o),r(`Failed to ${n} licensing`,"error"),t&&(t.innerHTML=`<div class="error-message">Failed to ${n} licensing</div>`)}}async function Ts(){if(!confirm("Are you sure you want to revoke the current license? This action cannot be undone."))return;const e=document.getElementById("revoke-license-result");try{const t=m(),o=await(await f(`${t}/api/license/revoke`,{method:"POST",headers:u()})).json();o.success?(r("License revoked successfully","success"),e&&(e.innerHTML='<div class="info-box" style="border-left-color: #4caf50;">License revoked successfully</div>'),F(),N()):(r(o.error||"Failed to revoke license","error"),e&&(e.innerHTML=`<div class="error-message">${o.error||"Failed to revoke license"}</div>`))}catch(t){console.error("Error revoking license:",t),r("Failed to revoke license","error"),e&&(e.innerHTML='<div class="error-message">Failed to revoke license</div>')}}async function $s(){if(!confirm("Are you sure you want to remove the license lock? This will allow licensing to be disabled."))return;const e=document.getElementById("remove-lock-result");try{const t=m(),o=await(await f(`${t}/api/license/remove_lock`,{method:"POST",headers:u()})).json();o.success?(r(o.message||"License lock removed","success"),e&&(e.innerHTML=`<div class="info-box" style="border-left-color: #4caf50;">${o.message||"License lock removed"}</div>`)):(r(o.error||"Failed to remove license lock","error"),e&&(e.innerHTML=`<div class="error-message">${o.error||"Failed to remove license lock"}</div>`))}catch(t){console.error("Error removing license lock:",t),r("Failed to remove license lock","error"),e&&(e.innerHTML='<div class="error-message">Failed to remove license lock</div>')}}function _s(){F(),N()}window.loadLicenseStatus=F;window.loadLicenseFeatures=N;window.generateLicense=xs;window.autoInstallGeneratedLicense=Is;window.installLicense=Ss;window.toggleLicensing=Cs;window.revokeLicense=Ts;window.removeLicenseLock=$s;window.initLicenseManagement=_s;let S={};function As(){return typeof Chart<"u"}async function Bs(){try{const t=document.getElementById("analytics-period")?.value??"7",n=m(),o=await fetch(`${n}/api/analytics/overview?days=${t}`,{headers:u()});if(!o.ok)throw new Error(`HTTP ${o.status}`);const s=await o.json();Ps(s),Ms(s.top_callers??[]),As()&&(s.daily_trends&&Ls(s.daily_trends),s.hourly_distribution&&Ds(s.hourly_distribution),s.disposition&&Rs(s.disposition))}catch(e){console.error("Error loading analytics:",e)}}function Ps(e){const t=i=>document.getElementById(i),n=t("analytics-total-calls"),o=t("analytics-avg-duration"),s=t("analytics-answer-rate"),a=t("analytics-answered-calls");n&&(n.textContent=String(e.total_calls??0)),o&&(o.textContent=`${e.avg_duration??0}s`),s&&(s.textContent=`${e.answer_rate??0}%`),a&&(a.textContent=String(e.answered_calls??0))}function Ms(e){const t=document.getElementById("top-callers-table");if(t){if(e.length===0){t.innerHTML='<tr><td colspan="4" class="loading">No call data available</td></tr>';return}t.innerHTML=e.map(n=>`<tr>
            <td>${l(String(n.extension??"Unknown"))}</td>
            <td>${n.calls??0}</td>
            <td>${((n.total_duration??0)/60).toFixed(1)}</td>
            <td>${(n.avg_duration??0).toFixed(1)}</td>
        </tr>`).join("")}}function Ls(e){const t=document.getElementById("daily-trends-chart")?.getContext("2d");t&&(S.dailyTrends&&S.dailyTrends.destroy(),S.dailyTrends=new Chart(t,{type:"line",data:{labels:e.labels||[],datasets:[{label:"Calls",data:e.data||[],borderColor:"#3b82f6",tension:.3,fill:!1}]},options:{responsive:!0,maintainAspectRatio:!1}}))}function Ds(e){const t=document.getElementById("hourly-distribution-chart")?.getContext("2d");t&&(S.hourlyDist&&S.hourlyDist.destroy(),S.hourlyDist=new Chart(t,{type:"bar",data:{labels:e.labels||[],datasets:[{label:"Calls by Hour",data:e.data||[],backgroundColor:"#60a5fa"}]},options:{responsive:!0,maintainAspectRatio:!1}}))}function Rs(e){const t=document.getElementById("disposition-chart")?.getContext("2d");t&&(S.disposition&&S.disposition.destroy(),S.disposition=new Chart(t,{type:"doughnut",data:{labels:e.labels||[],datasets:[{data:e.data||[],backgroundColor:["#10b981","#ef4444","#f59e0b","#6b7280"]}]},options:{responsive:!0,maintainAspectRatio:!1}}))}async function Fs(){try{const e=m(),t=await fetch(`${e}/api/qos/metrics`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=n.active_calls??0,s=n.metrics??[];let a=0,i=0;if(s.length>0){const p=s.map(h=>h.mos_score??0).filter(h=>h>0);a=p.length>0?p.reduce((h,k)=>h+k,0)/p.length:0,i=p.filter(h=>h<3.5).length}const c=document.getElementById("qos-avg-mos"),d=document.getElementById("qos-active-calls"),g=document.getElementById("qos-total-calls"),y=document.getElementById("qos-calls-with-issues");c&&(c.textContent=a>0?a.toFixed(2):"N/A"),d&&(d.textContent=String(o)),g&&(g.textContent=String(s.length)),y&&(y.textContent=String(i))}catch(e){console.error("Error loading QoS metrics:",e)}}async function Ns(){try{const e=m();if((await fetch(`${e}/api/qos/clear-alerts`,{method:"POST",headers:u()})).ok){const n=document.getElementById("qos-alerts-container");n&&(n.innerHTML='<div class="info-box">No quality alerts</div>'),r("QoS alerts cleared","success")}else r("Failed to clear QoS alerts","error")}catch(e){console.error("Error clearing QoS alerts:",e),r("Failed to clear QoS alerts","error")}}async function Hs(e){e&&e.preventDefault();try{const t=a=>document.getElementById(a)?.value??"",n={mos_min:parseFloat(t("qos-threshold-mos"))||3.5,jitter_max:parseInt(t("qos-threshold-jitter"),10)||50,packet_loss_max:parseFloat(t("qos-threshold-loss"))||2,latency_max:parseInt(t("qos-threshold-latency"),10)||300},o=m();(await fetch(`${o}/api/qos/thresholds`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify(n)})).ok?r("QoS thresholds saved","success"):r("Failed to save QoS thresholds","error")}catch(t){console.error("Error saving QoS thresholds:",t),r("Failed to save QoS thresholds","error")}}window.loadAnalytics=Bs;window.loadQoSMetrics=Fs;window.clearQoSAlerts=Ns;window.saveQoSThresholds=Hs;function js(e){return{registered:'<span class="badge" style="background: #10b981;">Registered</span>',unregistered:'<span class="badge" style="background: #6b7280;">Unregistered</span>',failed:'<span class="badge" style="background: #ef4444;">Failed</span>',disabled:'<span class="badge" style="background: #9ca3af;">Disabled</span>',degraded:'<span class="badge" style="background: #f59e0b;">Degraded</span>'}[e]||e}function Bt(e){return{healthy:'<span class="badge" style="background: #10b981;">Healthy</span>',warning:'<span class="badge" style="background: #f59e0b;">Warning</span>',critical:'<span class="badge" style="background: #f59e0b;">Critical</span>',down:'<span class="badge" style="background: #ef4444;">Down</span>'}[e]||e}async function ne(){try{const e=m(),t=await f(`${e}/api/sip-trunks`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}: ${t.statusText}`);const n=await t.json();if(n.trunks){const o=document.getElementById("trunk-total");o&&(o.textContent=String(n.count||0));const s=n.trunks.filter(p=>p.health_status==="healthy").length,a=n.trunks.filter(p=>p.status==="registered").length,i=n.trunks.reduce((p,h)=>p+h.channels_available,0),c=document.getElementById("trunk-healthy");c&&(c.textContent=String(s));const d=document.getElementById("trunk-registered");d&&(d.textContent=String(a));const g=document.getElementById("trunk-total-channels");g&&(g.textContent=String(i));const y=document.getElementById("trunks-list");if(!y)return;n.trunks.length===0?y.innerHTML='<tr><td colspan="8" style="text-align: center;">No SIP trunks configured</td></tr>':y.innerHTML=n.trunks.map(p=>{const h=js(p.status),k=Bt(p.health_status),E=(p.success_rate*100).toFixed(1);return`
                        <tr>
                            <td><strong>${l(p.name)}</strong><br/><small>${l(p.trunk_id)}</small></td>
                            <td>${l(p.host)}:${p.port}</td>
                            <td>${h}</td>
                            <td>${k}</td>
                            <td>${p.priority}</td>
                            <td>${p.channels_in_use}/${p.max_channels}</td>
                            <td>
                                <div style="display: flex; align-items: center; gap: 5px;">
                                    <div style="flex: 1; background: #e5e7eb; border-radius: 4px; height: 20px; overflow: hidden;">
                                        <div style="background: ${Number(E)>=95?"#10b981":Number(E)>=80?"#f59e0b":"#ef4444"}; height: 100%; width: ${E}%;"></div>
                                    </div>
                                    <span>${E}%</span>
                                </div>
                                <small>${p.successful_calls}/${p.total_calls} calls</small>
                            </td>
                            <td>
                                <button class="btn-small btn-primary" onclick="testTrunk('${l(p.trunk_id)}')">Test</button>
                                <button class="btn-small btn-danger" onclick="deleteTrunk('${l(p.trunk_id)}', '${l(p.name)}')">Delete</button>
                            </td>
                        </tr>
                    `}).join("")}}catch(e){console.error("Error loading SIP trunks:",e);const t=e instanceof Error?e.message:String(e);r(`Error loading SIP trunks: ${t}`,"error")}}async function Pt(){try{const e=m(),t=await f(`${e}/api/sip-trunks/health`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}: ${t.statusText}`);const n=await t.json();if(n.health){const o=document.getElementById("trunk-health-section"),s=document.getElementById("trunk-health-container");if(!o||!s)return;o.style.display="block",s.innerHTML=n.health.map(a=>`
                <div class="config-section" style="margin-bottom: 15px;">
                    <h4>${l(a.name)} (${l(a.trunk_id)})</h4>
                    <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));">
                        <div class="stat-card">
                            <div class="stat-value">${Bt(a.health_status)}</div>
                            <div class="stat-label">Health Status</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${(a.success_rate*100).toFixed(1)}%</div>
                            <div class="stat-label">Success Rate</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${a.consecutive_failures}</div>
                            <div class="stat-label">Consecutive Failures</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${a.average_setup_time.toFixed(2)}s</div>
                            <div class="stat-label">Avg Setup Time</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${a.failover_count}</div>
                            <div class="stat-label">Failover Count</div>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <p><strong>Total Calls:</strong> ${a.total_calls} (${a.successful_calls} successful, ${a.failed_calls} failed)</p>
                        ${a.last_successful_call?`<p><strong>Last Success:</strong> ${new Date(a.last_successful_call).toLocaleString()}</p>`:""}
                        ${a.last_failed_call?`<p><strong>Last Failure:</strong> ${new Date(a.last_failed_call).toLocaleString()}</p>`:""}
                        ${a.last_health_check?`<p><strong>Last Check:</strong> ${new Date(a.last_health_check).toLocaleString()}</p>`:""}
                    </div>
                </div>
            `).join(""),r("Health metrics loaded","success")}}catch(e){console.error("Error loading trunk health:",e);const t=e instanceof Error?e.message:String(e);r(`Error loading trunk health: ${t}`,"error")}}function Os(){const e=document.getElementById("add-trunk-modal");e&&(e.style.display="block")}function Mt(){const e=document.getElementById("add-trunk-modal");e&&(e.style.display="none");const t=document.getElementById("add-trunk-form");t&&t.reset()}async function qs(e){e.preventDefault();const t=Array.from(document.querySelectorAll('input[name="trunk-codecs"]:checked')).map(o=>o.value),n={trunk_id:document.getElementById("trunk-id").value,name:document.getElementById("trunk-name").value,host:document.getElementById("trunk-host").value,port:parseInt(document.getElementById("trunk-port").value),username:document.getElementById("trunk-username").value,password:document.getElementById("trunk-password").value,priority:parseInt(document.getElementById("trunk-priority").value),max_channels:parseInt(document.getElementById("trunk-channels").value),codec_preferences:t.length>0?t:["G.711","G.729"]};try{const o=m(),a=await(await f(`${o}/api/sip-trunks`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify(n)})).json();a.success?(r(`Trunk ${n.name} added successfully`,"success"),Mt(),ne()):r(a.error||"Error adding trunk","error")}catch(o){console.error("Error adding trunk:",o),r("Error adding trunk","error")}}async function Us(e,t){if(confirm(`Are you sure you want to delete trunk "${t}"?`))try{const n=m(),s=await(await f(`${n}/api/sip-trunks/${e}`,{method:"DELETE",headers:u()})).json();s.success?(r(`Trunk ${t} deleted`,"success"),ne()):r(s.error||"Error deleting trunk","error")}catch(n){console.error("Error deleting trunk:",n),r("Error deleting trunk","error")}}async function Vs(e){r("Testing trunk...","info");try{const t=m(),o=await(await f(`${t}/api/sip-trunks/test`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify({trunk_id:e})})).json();if(o.success){const s=o.health_status??"unknown";r(`Trunk test complete: ${s}`,s==="healthy"?"success":"warning"),ne(),Pt()}else r(o.error||"Error testing trunk","error")}catch(t){console.error("Error testing trunk:",t),r("Error testing trunk","error")}}async function oe(){try{const e=m(),t=await f(`${e}/api/lcr/rates`,{headers:u()});if(!t.ok){window.suppressErrorNotifications?debugLog("LCR rates endpoint returned error:",t.status,"(feature may not be enabled)"):(console.error("Error loading LCR rates:",t.status),r("Error loading LCR rates","error"));return}const n=await t.json();if(n.rates!==void 0){const o=document.getElementById("lcr-total-rates");o&&(o.textContent=String(n.count||0));const s=document.getElementById("lcr-time-rates");s&&(s.textContent=String(n.time_rates?n.time_rates.length:0));const a=document.getElementById("lcr-rates-list");a&&(n.rates.length===0?a.innerHTML='<tr><td colspan="7" style="text-align: center;">No rates configured</td></tr>':a.innerHTML=n.rates.map(c=>`
                        <tr>
                            <td><strong>${l(c.trunk_id)}</strong></td>
                            <td><code>${l(c.pattern)}</code></td>
                            <td>${l(c.description)}</td>
                            <td>$${c.rate_per_minute.toFixed(4)}</td>
                            <td>$${c.connection_fee.toFixed(4)}</td>
                            <td>${c.minimum_seconds}s</td>
                            <td>${c.billing_increment}s</td>
                        </tr>
                    `).join(""));const i=document.getElementById("lcr-time-rates-list");i&&(!n.time_rates||n.time_rates.length===0?i.innerHTML='<tr><td colspan="5" style="text-align: center;">No time-based rates configured</td></tr>':i.innerHTML=n.time_rates.map(c=>{const d=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],g=c.days_of_week.map(y=>d[y]).join(", ");return`
                            <tr>
                                <td><strong>${l(c.name)}</strong></td>
                                <td>${c.start_time}</td>
                                <td>${c.end_time}</td>
                                <td>${g}</td>
                                <td>${c.rate_multiplier}x</td>
                            </tr>
                        `}).join(""))}Lt()}catch(e){if(window.suppressErrorNotifications){const t=e instanceof Error?e.message:String(e);debugLog("Error loading LCR rates (expected if LCR not enabled):",t)}else console.error("Error loading LCR rates:",e),r("Error loading LCR rates","error")}}async function Lt(){try{const e=m(),t=await f(`${e}/api/lcr/statistics`,{headers:u()});if(!t.ok){window.suppressErrorNotifications?debugLog("LCR statistics endpoint returned error:",t.status,"(feature may not be enabled)"):console.error("Error loading LCR statistics:",t.status);return}const n=await t.json(),o=document.getElementById("lcr-total-routes");o&&(o.textContent=String(n.total_routes||0));const s=document.getElementById("lcr-status");s&&(s.innerHTML=n.enabled?'<span class="badge" style="background: #10b981;">Enabled</span>':'<span class="badge" style="background: #6b7280;">Disabled</span>');const a=document.getElementById("lcr-decisions-list");a&&(!n.recent_decisions||n.recent_decisions.length===0?a.innerHTML='<tr><td colspan="5" style="text-align: center;">No recent decisions</td></tr>':a.innerHTML=n.recent_decisions.map(i=>`
                        <tr>
                            <td>${new Date(i.timestamp).toLocaleString()}</td>
                            <td>${l(i.number)}</td>
                            <td><strong>${l(i.selected_trunk)}</strong></td>
                            <td>$${i.estimated_cost.toFixed(4)}</td>
                            <td>${i.alternatives}</td>
                        </tr>
                    `).join(""))}catch(e){if(window.suppressErrorNotifications){const t=e instanceof Error?e.message:String(e);debugLog("Error loading LCR statistics (expected if LCR not enabled):",t)}else console.error("Error loading LCR statistics:",e)}}function Js(){document.body.insertAdjacentHTML("beforeend",`
        <div id="lcr-rate-modal" class="modal" style="display: block;">
            <div class="modal-content" style="max-width: 600px;">
                <h2>Add LCR Rate</h2>
                <form id="add-lcr-rate-form" onsubmit="addLCRRate(event)">
                    <div class="form-group">
                        <label for="lcr-trunk-id">Trunk ID:</label>
                        <input type="text" id="lcr-trunk-id" required>
                        <small>The SIP trunk ID this rate applies to</small>
                    </div>

                    <div class="form-group">
                        <label for="lcr-pattern">Dial Pattern (Regex):</label>
                        <input type="text" id="lcr-pattern" required placeholder="^\\d{10}$">
                        <small>Regex pattern to match dialed numbers (e.g., ^\\d{10}$ for US local)</small>
                    </div>

                    <div class="form-group">
                        <label for="lcr-description">Description:</label>
                        <input type="text" id="lcr-description" placeholder="US Local Calls">
                    </div>

                    <div class="form-group">
                        <label for="lcr-rate-per-minute">Rate per Minute ($):</label>
                        <input type="number" id="lcr-rate-per-minute" step="0.0001" min="0" required placeholder="0.0100">
                    </div>

                    <div class="form-group">
                        <label for="lcr-connection-fee">Connection Fee ($):</label>
                        <input type="number" id="lcr-connection-fee" step="0.0001" min="0" value="0.0000">
                    </div>

                    <div class="form-group">
                        <label for="lcr-minimum-seconds">Minimum Billable Seconds:</label>
                        <input type="number" id="lcr-minimum-seconds" min="0" value="0">
                    </div>

                    <div class="form-group">
                        <label for="lcr-billing-increment">Billing Increment (seconds):</label>
                        <input type="number" id="lcr-billing-increment" min="1" value="1">
                        <small>Round up billing to this increment (e.g., 6 for 6-second increments)</small>
                    </div>

                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">Add Rate</button>
                        <button type="button" class="btn btn-secondary" onclick="closeLCRRateModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `)}function Dt(){const e=document.getElementById("lcr-rate-modal");e&&e.remove()}function Ws(e){if(!e||e.trim().length===0)return{valid:!1,error:"Pattern cannot be empty"};try{return new RegExp(e),{valid:!0}}catch(t){return{valid:!1,error:`Invalid regex: ${t instanceof Error?t.message:"Invalid regex pattern"}`}}}async function zs(e){e.preventDefault();const t=document.getElementById("lcr-pattern").value,n=Ws(t);if(!n.valid){r(n.error||"Invalid LCR pattern","error");return}const o={trunk_id:document.getElementById("lcr-trunk-id").value,pattern:t,description:document.getElementById("lcr-description").value,rate_per_minute:parseFloat(document.getElementById("lcr-rate-per-minute").value),connection_fee:parseFloat(document.getElementById("lcr-connection-fee").value),minimum_seconds:parseInt(document.getElementById("lcr-minimum-seconds").value),billing_increment:parseInt(document.getElementById("lcr-billing-increment").value)};try{const s=m(),i=await(await f(`${s}/api/lcr/rate`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify(o)})).json();i.success?(r("LCR rate added successfully","success"),Dt(),oe()):r(i.error||"Error adding LCR rate","error")}catch(s){console.error("Error adding LCR rate:",s),r(`Error adding LCR rate: ${s instanceof Error?s.message:"Unknown error"}`,"error")}}function Gs(){document.body.insertAdjacentHTML("beforeend",`
        <div id="lcr-time-rate-modal" class="modal" style="display: block;">
            <div class="modal-content" style="max-width: 600px;">
                <h2>Add Time-Based Rate Modifier</h2>
                <form id="add-time-rate-form" onsubmit="addTimeRate(event)">
                    <div class="form-group">
                        <label for="time-rate-name">Period Name:</label>
                        <input type="text" id="time-rate-name" required placeholder="Peak Hours">
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="time-rate-start-hour">Start Hour (0-23):</label>
                            <input type="number" id="time-rate-start-hour" min="0" max="23" required value="9">
                        </div>
                        <div class="form-group">
                            <label for="time-rate-start-minute">Start Minute:</label>
                            <input type="number" id="time-rate-start-minute" min="0" max="59" required value="0">
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="time-rate-end-hour">End Hour (0-23):</label>
                            <input type="number" id="time-rate-end-hour" min="0" max="23" required value="17">
                        </div>
                        <div class="form-group">
                            <label for="time-rate-end-minute">End Minute:</label>
                            <input type="number" id="time-rate-end-minute" min="0" max="59" required value="0">
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Days of Week:</label>
                        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                            <label><input type="checkbox" name="time-days" value="0" checked> Mon</label>
                            <label><input type="checkbox" name="time-days" value="1" checked> Tue</label>
                            <label><input type="checkbox" name="time-days" value="2" checked> Wed</label>
                            <label><input type="checkbox" name="time-days" value="3" checked> Thu</label>
                            <label><input type="checkbox" name="time-days" value="4" checked> Fri</label>
                            <label><input type="checkbox" name="time-days" value="5"> Sat</label>
                            <label><input type="checkbox" name="time-days" value="6"> Sun</label>
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="time-rate-multiplier">Rate Multiplier:</label>
                        <input type="number" id="time-rate-multiplier" step="0.1" min="0.1" required value="1.0">
                        <small>Multiply rates by this factor during this period (e.g., 1.2 for 20% increase)</small>
                    </div>

                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">Add Time Rate</button>
                        <button type="button" class="btn btn-secondary" onclick="closeTimeRateModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `)}function Rt(){const e=document.getElementById("lcr-time-rate-modal");e&&e.remove()}async function Qs(e){e.preventDefault();const t=Array.from(document.querySelectorAll('input[name="time-days"]:checked')).map(o=>parseInt(o.value)),n={name:document.getElementById("time-rate-name").value,start_hour:parseInt(document.getElementById("time-rate-start-hour").value),start_minute:parseInt(document.getElementById("time-rate-start-minute").value),end_hour:parseInt(document.getElementById("time-rate-end-hour").value),end_minute:parseInt(document.getElementById("time-rate-end-minute").value),days:t,multiplier:parseFloat(document.getElementById("time-rate-multiplier").value)};try{const o=m(),a=await(await f(`${o}/api/lcr/time-rate`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify(n)})).json();a.success?(r("Time-based rate added successfully","success"),Rt(),oe()):r(a.error||"Error adding time-based rate","error")}catch(o){console.error("Error adding time-based rate:",o),r("Error adding time-based rate","error")}}async function Ks(){if(confirm("Are you sure you want to clear all LCR rates? This cannot be undone."))try{const e=m(),n=await(await f(`${e}/api/lcr/clear-rates`,{method:"POST",headers:{...u(),"Content-Type":"application/json"},body:JSON.stringify({})})).json();n.success?(r("All LCR rates cleared","success"),oe()):r(n.error||"Error clearing LCR rates","error")}catch(e){console.error("Error clearing LCR rates:",e),r("Error clearing LCR rates","error")}}window.loadSIPTrunks=ne;window.loadTrunkHealth=Pt;window.showAddTrunkModal=Os;window.closeAddTrunkModal=Mt;window.addSIPTrunk=qs;window.deleteTrunk=Us;window.testTrunk=Vs;window.loadLCRRates=oe;window.loadLCRStatistics=Lt;window.showAddLCRRateModal=Js;window.closeLCRRateModal=Dt;window.addLCRRate=zs;window.showAddTimeRateModal=Gs;window.closeTimeRateModal=Rt;window.addTimeRate=Qs;window.clearLCRRates=Ks;let Ys=0;async function $e(){try{const e=m(),t=await f(`${e}/api/fmfm/extensions`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}: ${t.statusText}`);const n=await t.json();if(n.extensions){const o=document.getElementById("fmfm-total-extensions");o&&(o.textContent=String(n.count||0));const s=n.extensions.filter(p=>p.mode==="sequential").length,a=n.extensions.filter(p=>p.mode==="simultaneous").length,i=n.extensions.filter(p=>p.enabled!==!1).length,c=document.getElementById("fmfm-sequential");c&&(c.textContent=String(s));const d=document.getElementById("fmfm-simultaneous");d&&(d.textContent=String(a));const g=document.getElementById("fmfm-active-count");g&&(g.textContent=String(i));const y=document.getElementById("fmfm-list");if(!y)return;n.extensions.length===0?y.innerHTML='<tr><td colspan="6" style="text-align: center;">No Find Me/Follow Me configurations</td></tr>':y.innerHTML=n.extensions.map(p=>{const h=p.enabled!==!1,k=p.mode==="sequential"?'<span class="badge" style="background: #3b82f6;">Sequential</span>':'<span class="badge" style="background: #10b981;">Simultaneous</span>',E=h?'<span class="badge" style="background: #10b981;">Active</span>':'<span class="badge" style="background: #6b7280;">Disabled</span>',O=p.destinations||[],Oe=O.map(ge=>`${l(ge.number)}${ge.ring_time?` (${ge.ring_time}s)`:""}`).join(", "),vn=p.updated_at?new Date(p.updated_at).toLocaleString():"N/A";return`
                        <tr>
                            <td><strong>${l(p.extension)}</strong></td>
                            <td>${k}</td>
                            <td>
                                <div style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${l(Oe)}">
                                    ${O.length} destination(s): ${l(Oe)||"None"}
                                </div>
                            </td>
                            <td>${E}</td>
                            <td><small>${vn}</small></td>
                            <td>
                                <button class="btn-small btn-primary" data-config='${l(JSON.stringify(p))}' onclick="editFMFMConfig(JSON.parse(this.getAttribute('data-config')))">Edit</button>
                                <button class="btn-small btn-danger" onclick="deleteFMFMConfig('${l(p.extension)}')">Delete</button>
                            </td>
                        </tr>
                    `}).join("")}}catch(e){console.error("Error loading FMFM extensions:",e),r("Error loading FMFM configurations","error")}}function Ft(){const e=document.getElementById("add-fmfm-modal");e&&(e.style.display="block");const t=document.getElementById("fmfm-extension");t&&(t.value="",t.readOnly=!1);const n=document.getElementById("fmfm-mode");n&&(n.value="sequential");const o=document.getElementById("fmfm-enabled");o&&(o.checked=!0);const s=document.getElementById("fmfm-no-answer");s&&(s.value="");const a=document.getElementById("fmfm-destinations-list");a&&(a.innerHTML=""),J()}function Nt(){const e=document.getElementById("add-fmfm-modal");e&&(e.style.display="none");const t=document.getElementById("add-fmfm-form");t&&t.reset()}function J(){const e=document.getElementById("fmfm-destinations-list");if(!e)return;const t=`fmfm-dest-${Ys++}`,n=document.createElement("div");n.id=t,n.style.cssText="display: flex; gap: 10px; margin-bottom: 10px; align-items: center;",n.innerHTML=`
        <input type="text" class="fmfm-dest-number" placeholder="Phone number or extension" required style="flex: 2;">
        <input type="number" class="fmfm-dest-ringtime" placeholder="Ring time (s)" value="20" min="5" max="120" style="flex: 1;">
        <button type="button" class="btn-small btn-danger" onclick="document.getElementById('${t}').remove()">Remove</button>
    `,e.appendChild(n)}async function Zs(e){e.preventDefault();const t=document.getElementById("fmfm-extension").value,n=document.getElementById("fmfm-mode").value,o=document.getElementById("fmfm-enabled").checked,s=document.getElementById("fmfm-no-answer").value,a=Array.from(document.querySelectorAll(".fmfm-dest-number")),i=Array.from(document.querySelectorAll(".fmfm-dest-ringtime")),c=a.map((g,y)=>({number:g.value,ring_time:parseInt(i[y]?.value??"20")||20})).filter(g=>g.number);if(c.length===0){r("At least one destination is required","error");return}const d={extension:t,mode:n,enabled:o,destinations:c};s&&(d.no_answer_destination=s);try{const g=m(),p=await(await f(`${g}/api/fmfm/config`,{method:"POST",headers:u(),body:JSON.stringify(d)})).json();p.success?(r(`FMFM configured for extension ${t}`,"success"),Nt(),$e()):r(p.error||"Error configuring FMFM","error")}catch(g){console.error("Error saving FMFM config:",g),r("Error saving FMFM configuration","error")}}function Xs(e){Ft();const t=document.getElementById("fmfm-extension");t&&(t.value=e.extension,t.readOnly=!0);const n=document.getElementById("fmfm-mode");n&&(n.value=e.mode);const o=document.getElementById("fmfm-enabled");o&&(o.checked=e.enabled!==!1);const s=document.getElementById("fmfm-no-answer");s&&(s.value=e.no_answer_destination||"");const a=document.getElementById("fmfm-destinations-list");if(a)if(a.innerHTML="",e.destinations&&e.destinations.length>0)for(const i of e.destinations){J();const c=a.children,d=c[c.length-1],g=d.querySelector(".fmfm-dest-number");g&&(g.value=i.number);const y=d.querySelector(".fmfm-dest-ringtime");y&&(y.value=String(i.ring_time??20))}else J()}async function ea(e){if(confirm(`Are you sure you want to delete FMFM configuration for extension ${e}?`))try{const t=m(),o=await(await f(`${t}/api/fmfm/config/${e}`,{method:"DELETE",headers:u()})).json();o.success?(r(`FMFM configuration deleted for ${e}`,"success"),$e()):r(o.error||"Error deleting FMFM configuration","error")}catch(t){console.error("Error deleting FMFM config:",t),r("Error deleting FMFM configuration","error")}}function Ht(e){const t=[];if(e.days_of_week){const n=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],o=e.days_of_week.map(s=>n[s]).join(", ");t.push(o)}return e.start_time&&e.end_time&&t.push(`${e.start_time}-${e.end_time}`),e.holidays===!0?t.push("Holidays"):e.holidays===!1&&t.push("Non-holidays"),t.length>0?t.join(" | "):"Always"}async function _e(){try{const e=m(),t=await f(`${e}/api/time-routing/rules`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}: ${t.statusText}`);const n=await t.json();if(n.rules){const o=document.getElementById("time-routing-total");o&&(o.textContent=String(n.count||0));const s=n.rules.filter(p=>p.enabled!==!1).length,a=n.rules.filter(p=>p.name&&(p.name.toLowerCase().includes("business")||p.name.toLowerCase().includes("hours"))).length,i=n.rules.filter(p=>p.name&&(p.name.toLowerCase().includes("after")||p.name.toLowerCase().includes("closed"))).length,c=document.getElementById("time-routing-active");c&&(c.textContent=String(s));const d=document.getElementById("time-routing-business");d&&(d.textContent=String(a));const g=document.getElementById("time-routing-after");g&&(g.textContent=String(i));const y=document.getElementById("time-routing-list");if(!y)return;n.rules.length===0?y.innerHTML='<tr><td colspan="7" style="text-align: center;">No time-based routing rules</td></tr>':y.innerHTML=n.rules.map(p=>{const k=p.enabled!==!1?'<span class="badge" style="background: #10b981;">Active</span>':'<span class="badge" style="background: #6b7280;">Disabled</span>',E=p.time_conditions||{},O=Ht(E);return`
                        <tr>
                            <td><strong>${l(p.name)}</strong></td>
                            <td>${l(p.destination)}</td>
                            <td>${l(p.route_to)}</td>
                            <td><small>${l(O)}</small></td>
                            <td>${p.priority||100}</td>
                            <td>${k}</td>
                            <td>
                                <button class="btn-small btn-danger" onclick="deleteTimeRoutingRule('${l(p.rule_id)}', '${l(p.name)}')">Delete</button>
                            </td>
                        </tr>
                    `}).join("")}}catch(e){console.error("Error loading time routing rules:",e),r("Error loading time routing rules","error")}}function ta(){const e=document.getElementById("add-time-rule-modal");e&&(e.style.display="block")}function jt(){const e=document.getElementById("add-time-rule-modal");e&&(e.style.display="none");const t=document.getElementById("add-time-rule-form");t&&t.reset()}async function na(e){e.preventDefault();const t=document.getElementById("time-rule-name").value,n=document.getElementById("time-rule-destination").value,o=document.getElementById("time-rule-route-to").value,s=document.getElementById("time-rule-start").value,a=document.getElementById("time-rule-end").value,i=parseInt(document.getElementById("time-rule-priority").value),c=document.getElementById("time-rule-enabled").checked,d=Array.from(document.querySelectorAll('input[name="time-rule-days"]:checked')).map(y=>parseInt(y.value));if(d.length===0){r("Please select at least one day of the week","error");return}const g={name:t,destination:n,route_to:o,priority:i,enabled:c,time_conditions:{days_of_week:d,start_time:s,end_time:a}};try{const y=m(),h=await(await f(`${y}/api/time-routing/rule`,{method:"POST",headers:u(),body:JSON.stringify(g)})).json();h.success?(r(`Time routing rule "${t}" added successfully`,"success"),jt(),_e()):r(h.error||"Error adding time routing rule","error")}catch(y){console.error("Error saving time routing rule:",y),r("Error saving time routing rule","error")}}async function oa(e,t){if(confirm(`Are you sure you want to delete time routing rule "${t}"?`))try{const n=m(),s=await(await f(`${n}/api/time-routing/rule/${e}`,{method:"DELETE",headers:u()})).json();s.success?(r(`Time routing rule "${t}" deleted`,"success"),_e()):r(s.error||"Error deleting time routing rule","error")}catch(n){console.error("Error deleting time routing rule:",n),r("Error deleting time routing rule","error")}}async function Ae(){try{const e=m(),t=await f(`${e}/api/webhooks`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}: ${t.statusText}`);const n=await t.json();if(n.subscriptions){const o=document.getElementById("webhooks-list");if(!o)return;n.subscriptions.length===0?o.innerHTML='<tr><td colspan="5" style="text-align: center;">No webhooks configured</td></tr>':o.innerHTML=n.subscriptions.map(s=>{const i=s.enabled!==!1?'<span class="badge" style="background: #10b981;">Active</span>':'<span class="badge" style="background: #6b7280;">Disabled</span>',d=(s.event_types||[]).join(", "),g=s.secret?"Yes":"No";return`
                        <tr>
                            <td>
                                <div style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${l(s.url)}">
                                    ${l(s.url)}
                                </div>
                            </td>
                            <td>
                                <div style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${l(d)}">
                                    <small>${l(d)}</small>
                                </div>
                            </td>
                            <td>${g}</td>
                            <td>${i}</td>
                            <td>
                                <button class="btn-small btn-danger" onclick="deleteWebhook('${l(s.url)}')">Delete</button>
                            </td>
                        </tr>
                    `}).join("")}}catch(e){console.error("Error loading webhooks:",e),r("Error loading webhooks","error")}}function sa(){const e=document.getElementById("add-webhook-modal");e&&(e.style.display="block")}function Ot(){const e=document.getElementById("add-webhook-modal");e&&(e.style.display="none");const t=document.getElementById("add-webhook-form");t&&t.reset()}async function aa(e){e.preventDefault();const t=document.getElementById("webhook-url").value,n=document.getElementById("webhook-secret").value,o=document.getElementById("webhook-enabled").checked,s=Array.from(document.querySelectorAll('input[name="webhook-events"]:checked')).map(i=>i.value);if(s.length===0){r("Please select at least one event type","error");return}const a={url:t,event_types:s,enabled:o};n&&(a.secret=n);try{const i=m(),d=await(await f(`${i}/api/webhooks`,{method:"POST",headers:u(),body:JSON.stringify(a)})).json();d.success?(r("Webhook added successfully","success"),Ot(),Ae()):r(d.error||"Error adding webhook","error")}catch(i){console.error("Error adding webhook:",i),r("Error adding webhook","error")}}async function ia(e){if(!confirm(`Are you sure you want to delete webhook for ${e}?`))return;const t=encodeURIComponent(e);try{const n=m(),s=await(await f(`${n}/api/webhooks/${t}`,{method:"DELETE",headers:u()})).json();s.success?(r("Webhook deleted","success"),Ae()):r(s.error||"Error deleting webhook","error")}catch(n){console.error("Error deleting webhook:",n),r("Error deleting webhook","error")}}function qt(e){const n=new Date().getTime()-e.getTime(),o=Math.floor(n/(1e3*60*60)),s=Math.floor(n%(1e3*60*60)/(1e3*60));return o>0?`${o}h ${s}m`:`${s}m`}async function Ut(){try{const e=m(),t=await f(`${e}/api/hot-desk/sessions`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}: ${t.statusText}`);const n=await t.json();if(n.sessions){const o=n.sessions.filter(c=>c.active!==!1),s=document.getElementById("hotdesk-active");s&&(s.textContent=String(o.length));const a=document.getElementById("hotdesk-total");a&&(a.textContent=String(n.sessions.length));const i=document.getElementById("hotdesk-sessions-list");if(!i)return;o.length===0?i.innerHTML='<tr><td colspan="6" style="text-align: center;">No active hot desk sessions</td></tr>':i.innerHTML=o.map(c=>{const d=c.login_time?new Date(c.login_time).toLocaleString():"N/A",g=c.login_time?qt(new Date(c.login_time)):"N/A";return`
                        <tr>
                            <td><strong>${l(c.extension)}</strong></td>
                            <td>${l(c.device_mac||"N/A")}</td>
                            <td>${l(c.device_ip||"N/A")}</td>
                            <td><small>${d}</small></td>
                            <td>${g}</td>
                            <td>
                                <button class="btn-small btn-warning" onclick="logoutHotDesk('${l(c.extension)}')">Logout</button>
                            </td>
                        </tr>
                    `}).join("")}}catch(e){console.error("Error loading hot desk sessions:",e),r("Error loading hot desk sessions","error")}}async function ra(e){if(confirm(`Are you sure you want to log out extension ${e} from hot desk?`))try{const t=m(),o=await(await f(`${t}/api/hot-desk/logout`,{method:"POST",headers:u(),body:JSON.stringify({extension:e})})).json();o.success?(r(`Extension ${e} logged out`,"success"),Ut()):r(o.error||"Error logging out","error")}catch(t){console.error("Error logging out hot desk:",t),r("Error logging out hot desk","error")}}async function Be(){try{const e=m(),[t,n]=await Promise.all([f(`${e}/api/recording-retention/policies`,{headers:u()}),f(`${e}/api/recording-retention/statistics`,{headers:u()})]),[o,s]=await Promise.all([t.json(),n.json()]);if(s){const a=document.getElementById("retention-policies-count");a&&(a.textContent=String(s.total_policies||0));const i=document.getElementById("retention-recordings");i&&(i.textContent=String(s.total_recordings||0));const c=document.getElementById("retention-deleted");c&&(c.textContent=String(s.deleted_count||0));const d=s.last_cleanup?new Date(s.last_cleanup).toLocaleDateString():"Never",g=document.getElementById("retention-last-cleanup");g&&(g.textContent=d)}if(o&&o.policies){const a=document.getElementById("retention-policies-list");if(!a)return;o.policies.length===0?a.innerHTML='<tr><td colspan="5" style="text-align: center;">No retention policies configured</td></tr>':a.innerHTML=o.policies.map(i=>{const c=i.created_at?new Date(i.created_at).toLocaleDateString():"N/A",d=i.tags?i.tags.join(", "):"None";return`
                        <tr>
                            <td><strong>${l(i.name)}</strong></td>
                            <td>${i.retention_days} days</td>
                            <td><small>${l(d)}</small></td>
                            <td><small>${c}</small></td>
                            <td>
                                <button class="btn-small btn-danger" onclick="deleteRetentionPolicy('${l(i.policy_id)}', '${l(i.name)}')">Delete</button>
                            </td>
                        </tr>
                    `}).join("")}}catch(e){console.error("Error loading retention policies:",e),r("Error loading retention policies","error")}}function ca(){const e=document.getElementById("add-retention-policy-modal");e&&(e.style.display="block")}function Vt(){const e=document.getElementById("add-retention-policy-modal");e&&(e.style.display="none");const t=document.getElementById("add-retention-policy-form");t&&t.reset()}async function la(e){e.preventDefault();const t=document.getElementById("retention-policy-name").value,n=parseInt(document.getElementById("retention-days").value),o=document.getElementById("retention-tags").value;if(!t.match(/^[a-zA-Z0-9_\s-]+$/)){r("Policy name contains invalid characters","error");return}if(n<1||n>3650){r("Retention days must be between 1 and 3650","error");return}const s={name:t,retention_days:n};o.trim()&&(s.tags=o.split(",").map(a=>a.trim()).filter(a=>a));try{const a=m(),c=await(await f(`${a}/api/recording-retention/policy`,{method:"POST",headers:u(),body:JSON.stringify(s)})).json();c.success?(r(`Retention policy "${t}" added successfully`,"success"),Vt(),Be()):r(c.error||"Error adding retention policy","error")}catch(a){console.error("Error adding retention policy:",a),r("Error adding retention policy","error")}}async function da(e,t){if(confirm(`Are you sure you want to delete retention policy "${t}"?`))try{const n=m(),s=await(await f(`${n}/api/recording-retention/policy/${encodeURIComponent(e)}`,{method:"DELETE",headers:u()})).json();s.success?(r(`Retention policy "${t}" deleted`,"success"),Be()):r(s.error||"Error deleting retention policy","error")}catch(n){console.error("Error deleting retention policy:",n),r("Error deleting retention policy","error")}}async function H(){try{const e=m(),[t,n]=await Promise.all([f(`${e}/api/callback-queue/list`,{headers:u()}),f(`${e}/api/callback-queue/statistics`,{headers:u()})]),[o,s]=await Promise.all([t.json(),n.json()]);if(s){const a=document.getElementById("callback-total");a&&(a.textContent=String(s.total_callbacks||0));const i=s.status_breakdown||{},c=document.getElementById("callback-scheduled");c&&(c.textContent=String(i.scheduled||0));const d=document.getElementById("callback-in-progress");d&&(d.textContent=String(i.in_progress||0));const g=document.getElementById("callback-completed");g&&(g.textContent=String(i.completed||0));const y=document.getElementById("callback-failed");y&&(y.textContent=String(i.failed||0))}if(o&&o.callbacks){const a=document.getElementById("callback-list");if(!a)return;o.callbacks.length===0?a.innerHTML='<tr><td colspan="8" style="text-align: center;">No callbacks in queue</td></tr>':a.innerHTML=o.callbacks.map(i=>{const c=new Date(i.requested_at).toLocaleString(),d=new Date(i.callback_time).toLocaleString();let g="";switch(i.status){case"scheduled":g="badge-info";break;case"in_progress":g="badge-warning";break;case"completed":g="badge-success";break;case"failed":g="badge-danger";break;case"cancelled":g="badge-secondary";break;default:g="badge-info"}return`
                        <tr>
                            <td><code>${l(i.callback_id)}</code></td>
                            <td>${l(i.queue_id)}</td>
                            <td>
                                <strong>${l(i.caller_number)}</strong><br>
                                <small>${l(i.caller_name||"N/A")}</small>
                            </td>
                            <td><small>${c}</small></td>
                            <td><small>${d}</small></td>
                            <td><span class="badge ${g}">${l(i.status)}</span></td>
                            <td>${i.attempts}</td>
                            <td>
                                ${i.status==="scheduled"?`
                                    <button class="btn-small btn-primary" onclick="startCallback('${l(i.callback_id)}')">Start</button>
                                    <button class="btn-small btn-danger" onclick="cancelCallback('${l(i.callback_id)}')">Cancel</button>
                                `:i.status==="in_progress"?`
                                    <button class="btn-small btn-success" onclick="completeCallback('${l(i.callback_id)}', true)">Done</button>
                                    <button class="btn-small btn-warning" onclick="completeCallback('${l(i.callback_id)}', false)">Retry</button>
                                `:"-"}
                            </td>
                        </tr>
                    `}).join("")}}catch(e){console.error("Error loading callback queue:",e),r("Error loading callback queue","error")}}function ua(){const e=document.createElement("div");e.className="modal",e.id="request-callback-modal",e.innerHTML=`
        <div class="modal-content">
            <span class="close" onclick="closeRequestCallbackModal()">&times;</span>
            <h2>Request Callback</h2>
            <form id="request-callback-form" onsubmit="requestCallback(event)">
                <div class="form-group">
                    <label for="callback-queue-id">Queue ID: *</label>
                    <input type="text" id="callback-queue-id" required
                           placeholder="e.g., sales, support, general">
                </div>
                <div class="form-group">
                    <label for="callback-caller-number">Caller Number: *</label>
                    <input type="tel" id="callback-caller-number" required
                           placeholder="e.g., +1234567890">
                </div>
                <div class="form-group">
                    <label for="callback-caller-name">Caller Name:</label>
                    <input type="text" id="callback-caller-name"
                           placeholder="Optional">
                </div>
                <div class="form-group">
                    <label for="callback-preferred-time">Preferred Time:</label>
                    <input type="datetime-local" id="callback-preferred-time">
                    <small>Leave empty for ASAP callback</small>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeRequestCallbackModal()">Cancel</button>
                    <button type="submit" class="btn btn-success">Request Callback</button>
                </div>
            </form>
        </div>
    `,document.body.appendChild(e),e.style.display="block"}function Jt(){const e=document.getElementById("request-callback-modal");e&&e.remove()}async function ma(e){e.preventDefault();const t=document.getElementById("callback-queue-id").value,n=document.getElementById("callback-caller-number").value,o=document.getElementById("callback-caller-name").value,s=document.getElementById("callback-preferred-time").value,a={queue_id:t,caller_number:n};o&&(a.caller_name=o),s&&(a.preferred_time=new Date(s).toISOString());try{const i=m(),d=await(await f(`${i}/api/callback-queue/request`,{method:"POST",headers:u(),body:JSON.stringify(a)})).json();d.success?(r("Callback requested successfully","success"),Jt(),H()):r(d.error||"Error requesting callback","error")}catch(i){console.error("Error requesting callback:",i),r("Error requesting callback","error")}}async function ga(e){const t=prompt("Enter your agent ID/extension:");if(t)try{const n=m(),s=await(await f(`${n}/api/callback-queue/start`,{method:"POST",headers:u(),body:JSON.stringify({callback_id:e,agent_id:t})})).json();s.success?(r(`Started callback to ${s.caller_number??"caller"}`,"success"),H()):r(s.error||"Error starting callback","error")}catch(n){console.error("Error starting callback:",n),r("Error starting callback","error")}}async function pa(e,t){let n="";t||(n=prompt("Enter reason for failure (optional):")||"");try{const o=m(),a=await(await f(`${o}/api/callback-queue/complete`,{method:"POST",headers:u(),body:JSON.stringify({callback_id:e,success:t,notes:n})})).json();a.success?(r(t?"Callback completed":"Callback will be retried","success"),H()):r(a.error||"Error completing callback","error")}catch(o){console.error("Error completing callback:",o),r("Error completing callback","error")}}async function fa(e){if(confirm("Are you sure you want to cancel this callback request?"))try{const t=m(),o=await(await f(`${t}/api/callback-queue/cancel`,{method:"POST",headers:u(),body:JSON.stringify({callback_id:e})})).json();o.success?(r("Callback cancelled","success"),H()):r(o.error||"Error cancelling callback","error")}catch(t){console.error("Error cancelling callback:",t),r("Error cancelling callback","error")}}window.loadFMFMExtensions=$e;window.showAddFMFMModal=Ft;window.closeAddFMFMModal=Nt;window.addFMFMDestinationRow=J;window.saveFMFMConfig=Zs;window.editFMFMConfig=Xs;window.deleteFMFMConfig=ea;window.getScheduleDescription=Ht;window.showAddTimeRuleModal=ta;window.closeAddTimeRuleModal=jt;window.loadTimeRoutingRules=_e;window.saveTimeRoutingRule=na;window.deleteTimeRoutingRule=oa;window.showAddWebhookModal=sa;window.closeAddWebhookModal=Ot;window.loadWebhooks=Ae;window.addWebhook=aa;window.deleteWebhook=ia;window.loadHotDeskSessions=Ut;window.logoutHotDesk=ra;window.getDuration=qt;window.loadRetentionPolicies=Be;window.showAddRetentionPolicyModal=ca;window.closeAddRetentionPolicyModal=Vt;window.addRetentionPolicy=la;window.deleteRetentionPolicy=da;window.loadCallbackQueue=H;window.showRequestCallbackModal=ua;window.closeRequestCallbackModal=Jt;window.requestCallback=ma;window.startCallback=ga;window.completeCallback=pa;window.cancelCallback=fa;async function se(){try{const e=m(),[t,n]=await Promise.all([f(`${e}/api/fraud-detection/alerts?hours=24`,{headers:u()}),f(`${e}/api/fraud-detection/statistics`,{headers:u()})]),[o,s]=await Promise.all([t.json(),n.json()]);if(s){const a=i=>document.getElementById(i);a("fraud-total-alerts")&&(a("fraud-total-alerts").textContent=String(s.total_alerts??0)),a("fraud-high-risk")&&(a("fraud-high-risk").textContent=String(s.high_risk_alerts??0)),a("fraud-blocked-patterns")&&(a("fraud-blocked-patterns").textContent=String(s.blocked_patterns_count??0)),a("fraud-extensions-flagged")&&(a("fraud-extensions-flagged").textContent=String(s.extensions_flagged??0))}if(o?.alerts){const a=document.getElementById("fraud-alerts-list");a&&(o.alerts.length===0?a.innerHTML='<tr><td colspan="5" style="text-align: center;">No fraud alerts detected</td></tr>':a.innerHTML=o.alerts.map(i=>{const c=new Date(i.timestamp).toLocaleString(),d=i.fraud_score>.8?"#ef4444":i.fraud_score>.5?"#f59e0b":"#10b981",g=(i.fraud_score*100).toFixed(0),y=(i.alert_types??[]).join(", ");return`
                            <tr>
                                <td><small>${l(c)}</small></td>
                                <td><strong>${l(i.extension)}</strong></td>
                                <td><small>${l(y)}</small></td>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 5px;">
                                        <div style="flex: 1; background: #e5e7eb; border-radius: 4px; height: 20px; overflow: hidden;">
                                            <div style="background: ${d}; height: 100%; width: ${g}%;"></div>
                                        </div>
                                        <span>${g}%</span>
                                    </div>
                                </td>
                                <td><small>${l(i.details??"No details")}</small></td>
                            </tr>
                        `}).join(""))}if(s?.blocked_patterns){const a=document.getElementById("blocked-patterns-list");a&&(s.blocked_patterns.length===0?a.innerHTML='<tr><td colspan="3" style="text-align: center;">No blocked patterns</td></tr>':a.innerHTML=s.blocked_patterns.map((i,c)=>`
                        <tr>
                            <td><code>${l(i.pattern)}</code></td>
                            <td>${l(i.reason)}</td>
                            <td>
                                <button class="btn-small btn-danger" onclick="deleteBlockedPattern(${c}, '${l(i.pattern)}')">Delete</button>
                            </td>
                        </tr>
                    `).join(""))}}catch(e){console.error("Error loading fraud detection data:",e),r("Error loading fraud detection data","error")}}function ya(){const e=document.getElementById("add-blocked-pattern-modal");e&&(e.style.display="block")}function Wt(){const e=document.getElementById("add-blocked-pattern-modal");e&&(e.style.display="none");const t=document.getElementById("add-blocked-pattern-form");t&&t.reset()}async function ba(e){e.preventDefault();const t=document.getElementById("blocked-pattern"),n=document.getElementById("blocked-reason"),o=t?.value??"",s=n?.value??"";try{new RegExp(o)}catch(i){const c=i instanceof Error?i.message:String(i);r(`Invalid regex pattern: ${c}`,"error");return}const a={pattern:o,reason:s};try{const i=m(),d=await(await f(`${i}/api/fraud-detection/blocked-pattern`,{method:"POST",headers:u(),body:JSON.stringify(a)})).json();d.success?(r("Blocked pattern added successfully","success"),Wt(),se()):r(d.error??"Error adding blocked pattern","error")}catch(i){console.error("Error adding blocked pattern:",i),r("Error adding blocked pattern","error")}}async function ha(e,t){if(confirm(`Are you sure you want to unblock pattern "${t}"?`))try{const n=m(),s=await(await f(`${n}/api/fraud-detection/blocked-pattern/${e}`,{method:"DELETE",headers:u()})).json();s.success?(r("Blocked pattern removed","success"),se()):r(s.error??"Error removing blocked pattern","error")}catch(n){console.error("Error removing blocked pattern:",n),r("Error removing blocked pattern","error")}}async function j(){try{const e=m(),[t,n]=await Promise.all([f(`${e}/api/callback-queue/list`,{headers:u()}),f(`${e}/api/callback-queue/statistics`,{headers:u()})]),[o,s]=await Promise.all([t.json(),n.json()]);if(s){const a=c=>document.getElementById(c);a("callback-total")&&(a("callback-total").textContent=String(s.total_callbacks??0));const i=s.status_breakdown??{};a("callback-scheduled")&&(a("callback-scheduled").textContent=String(i.scheduled??0)),a("callback-in-progress")&&(a("callback-in-progress").textContent=String(i.in_progress??0)),a("callback-completed")&&(a("callback-completed").textContent=String(i.completed??0)),a("callback-failed")&&(a("callback-failed").textContent=String(i.failed??0))}if(o?.callbacks){const a=document.getElementById("callback-list");a&&(o.callbacks.length===0?a.innerHTML='<tr><td colspan="8" style="text-align: center;">No callbacks in queue</td></tr>':a.innerHTML=o.callbacks.map(i=>{const c=new Date(i.requested_at).toLocaleString(),d=new Date(i.callback_time).toLocaleString();let g="";switch(i.status){case"scheduled":g="badge-info";break;case"in_progress":g="badge-warning";break;case"completed":g="badge-success";break;case"failed":g="badge-danger";break;case"cancelled":g="badge-secondary";break;default:g="badge-info"}return`
                            <tr>
                                <td><code>${l(i.callback_id)}</code></td>
                                <td>${l(i.queue_id)}</td>
                                <td>
                                    <strong>${l(i.caller_number)}</strong><br>
                                    <small>${l(i.caller_name??"N/A")}</small>
                                </td>
                                <td><small>${l(c)}</small></td>
                                <td><small>${l(d)}</small></td>
                                <td><span class="badge ${g}">${l(i.status)}</span></td>
                                <td>${i.attempts}</td>
                                <td>
                                    ${i.status==="scheduled"?`
                                        <button class="btn-small btn-primary" onclick="startCallback('${l(i.callback_id)}')">Start</button>
                                        <button class="btn-small btn-danger" onclick="cancelCallback('${l(i.callback_id)}')">Cancel</button>
                                    `:i.status==="in_progress"?`
                                        <button class="btn-small btn-success" onclick="completeCallback('${l(i.callback_id)}', true)">Done</button>
                                        <button class="btn-small btn-warning" onclick="completeCallback('${l(i.callback_id)}', false)">Retry</button>
                                    `:"-"}
                                </td>
                            </tr>
                        `}).join(""))}}catch(e){console.error("Error loading callback queue:",e),r("Error loading callback queue","error")}}function va(){const e=document.createElement("div");e.className="modal",e.id="request-callback-modal",e.innerHTML=`
        <div class="modal-content">
            <span class="close" onclick="closeRequestCallbackModal()">&times;</span>
            <h2>Request Callback</h2>
            <form id="request-callback-form" onsubmit="requestCallback(event)">
                <div class="form-group">
                    <label for="callback-queue-id">Queue ID: *</label>
                    <input type="text" id="callback-queue-id" required
                           placeholder="e.g., sales, support, general">
                </div>
                <div class="form-group">
                    <label for="callback-caller-number">Caller Number: *</label>
                    <input type="tel" id="callback-caller-number" required
                           placeholder="e.g., +1234567890">
                </div>
                <div class="form-group">
                    <label for="callback-caller-name">Caller Name:</label>
                    <input type="text" id="callback-caller-name"
                           placeholder="Optional">
                </div>
                <div class="form-group">
                    <label for="callback-preferred-time">Preferred Time:</label>
                    <input type="datetime-local" id="callback-preferred-time">
                    <small>Leave empty for ASAP callback</small>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeRequestCallbackModal()">Cancel</button>
                    <button type="submit" class="btn btn-success">Request Callback</button>
                </div>
            </form>
        </div>
    `,document.body.appendChild(e),e.style.display="block"}function zt(){const e=document.getElementById("request-callback-modal");e&&e.remove()}async function wa(e){e.preventDefault();const t=document.getElementById("callback-queue-id")?.value??"",n=document.getElementById("callback-caller-number")?.value??"",o=document.getElementById("callback-caller-name")?.value??"",s=document.getElementById("callback-preferred-time")?.value??"",a={queue_id:t,caller_number:n};o&&(a.caller_name=o),s&&(a.preferred_time=new Date(s).toISOString());try{const i=m(),d=await(await f(`${i}/api/callback-queue/request`,{method:"POST",headers:u(),body:JSON.stringify(a)})).json();d.success?(r("Callback requested successfully","success"),zt(),j()):r(d.error??"Error requesting callback","error")}catch(i){console.error("Error requesting callback:",i),r("Error requesting callback","error")}}async function Ea(e){const t=prompt("Enter your agent ID/extension:");if(t)try{const n=m(),s=await(await f(`${n}/api/callback-queue/start`,{method:"POST",headers:u(),body:JSON.stringify({callback_id:e,agent_id:t})})).json();s.success?(r(`Started callback to ${s.caller_number??e}`,"success"),j()):r(s.error??"Error starting callback","error")}catch(n){console.error("Error starting callback:",n),r("Error starting callback","error")}}async function ka(e,t){let n="";t||(n=prompt("Enter reason for failure (optional):")??"");try{const o=m(),a=await(await f(`${o}/api/callback-queue/complete`,{method:"POST",headers:u(),body:JSON.stringify({callback_id:e,success:t,notes:n})})).json();a.success?(r(t?"Callback completed":"Callback will be retried","success"),j()):r(a.error??"Error completing callback","error")}catch(o){console.error("Error completing callback:",o),r("Error completing callback","error")}}async function xa(e){if(confirm("Are you sure you want to cancel this callback request?"))try{const t=m(),o=await(await f(`${t}/api/callback-queue/cancel`,{method:"POST",headers:u(),body:JSON.stringify({callback_id:e})})).json();o.success?(r("Callback cancelled","success"),j()):r(o.error??"Error cancelling callback","error")}catch(t){console.error("Error cancelling callback:",t),r("Error cancelling callback","error")}}async function ae(){try{const e=m(),[t,n,o]=await Promise.all([f(`${e}/api/mobile-push/devices`,{headers:u()}),f(`${e}/api/mobile-push/statistics`,{headers:u()}),f(`${e}/api/mobile-push/history`,{headers:u()})]),[s,a,i]=await Promise.all([t.json(),n.json(),o.json()]);if(a){const c=g=>document.getElementById(g);c("push-total-devices")&&(c("push-total-devices").textContent=String(a.total_devices??0)),c("push-total-users")&&(c("push-total-users").textContent=String(a.total_users??0));const d=a.platforms??{};c("push-ios-devices")&&(c("push-ios-devices").textContent=String(d.ios??0)),c("push-android-devices")&&(c("push-android-devices").textContent=String(d.android??0)),c("push-recent-notifications")&&(c("push-recent-notifications").textContent=String(a.recent_notifications??0))}if(s?.devices){const c=document.getElementById("mobile-devices-list");c&&(s.devices.length===0?c.innerHTML='<tr><td colspan="5" style="text-align: center;">No devices registered</td></tr>':c.innerHTML=s.devices.map(d=>{const g=new Date(d.registered_at).toLocaleString(),y=new Date(d.last_seen).toLocaleString();let p="";return d.platform==="ios"?p='<span class="badge badge-info">iOS</span>':d.platform==="android"?p='<span class="badge badge-success">Android</span>':p=`<span class="badge badge-secondary">${l(d.platform)}</span>`,`
                            <tr>
                                <td><strong>${l(d.user_id)}</strong></td>
                                <td>${p}</td>
                                <td><small>${l(g)}</small></td>
                                <td><small>${l(y)}</small></td>
                                <td>
                                    <button class="btn-small btn-primary" onclick="sendTestNotification('${l(d.user_id)}')">Test</button>
                                </td>
                            </tr>
                        `}).join(""))}if(i?.history){const c=document.getElementById("push-history-list");c&&(i.history.length===0?c.innerHTML='<tr><td colspan="5" style="text-align: center;">No notifications sent</td></tr>':c.innerHTML=i.history.slice(0,50).map(d=>{const g=new Date(d.sent_at).toLocaleString(),y=d.success_count??0,p=d.failure_count??0;return`
                                <tr>
                                    <td>${l(d.user_id)}</td>
                                    <td><strong>${l(d.title)}</strong></td>
                                    <td><small>${l(d.body)}</small></td>
                                    <td><small>${l(g)}</small></td>
                                    <td>
                                        <span class="badge badge-success">${y} sent</span>
                                        ${p>0?`<span class="badge badge-danger">${p} failed</span>`:""}
                                    </td>
                                </tr>
                            `}).join(""))}}catch(e){console.error("Error loading mobile push data:",e),r("Error loading mobile push data","error")}}function Ia(){const e=document.createElement("div");e.className="modal",e.id="register-device-modal",e.innerHTML=`
        <div class="modal-content">
            <span class="close" onclick="closeRegisterDeviceModal()">&times;</span>
            <h2>Register Mobile Device</h2>
            <form id="register-device-form" onsubmit="registerDevice(event)">
                <div class="form-group">
                    <label for="device-user-id">User ID / Extension: *</label>
                    <input type="text" id="device-user-id" required
                           placeholder="e.g., 1001 or user@example.com">
                </div>
                <div class="form-group">
                    <label for="device-token">Device Token: *</label>
                    <textarea id="device-token" required rows="4"
                              placeholder="FCM device registration token"></textarea>
                    <small>Obtain from mobile app after FCM SDK initialization</small>
                </div>
                <div class="form-group">
                    <label for="device-platform">Platform: *</label>
                    <select id="device-platform" required>
                        <option value="">Select Platform</option>
                        <option value="ios">iOS</option>
                        <option value="android">Android</option>
                        <option value="other">Other</option>
                    </select>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeRegisterDeviceModal()">Cancel</button>
                    <button type="submit" class="btn btn-success">Register Device</button>
                </div>
            </form>
        </div>
    `,document.body.appendChild(e),e.style.display="block"}function Gt(){const e=document.getElementById("register-device-modal");e&&e.remove()}async function Sa(e){e.preventDefault();const t=document.getElementById("device-user-id")?.value??"",n=document.getElementById("device-token")?.value.trim()??"",o=document.getElementById("device-platform")?.value??"",s={user_id:t,device_token:n,platform:o};try{const a=m(),c=await(await f(`${a}/api/mobile-push/register`,{method:"POST",headers:u(),body:JSON.stringify(s)})).json();c.success?(r("Device registered successfully","success"),Gt(),ae()):r(c.error??"Error registering device","error")}catch(a){console.error("Error registering device:",a),r("Error registering device","error")}}function Ca(){const e=document.createElement("div");e.className="modal",e.id="test-notification-modal",e.innerHTML=`
        <div class="modal-content">
            <span class="close" onclick="closeTestNotificationModal()">&times;</span>
            <h2>Send Test Notification</h2>
            <form id="test-notification-form" onsubmit="sendTestNotificationForm(event)">
                <div class="form-group">
                    <label for="test-user-id">User ID / Extension: *</label>
                    <input type="text" id="test-user-id" required
                           placeholder="e.g., 1001 or user@example.com">
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeTestNotificationModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Send Test</button>
                </div>
            </form>
        </div>
    `,document.body.appendChild(e),e.style.display="block"}function Qt(){const e=document.getElementById("test-notification-modal");e&&e.remove()}function Ta(e){e.preventDefault();const t=document.getElementById("test-user-id")?.value??"";Kt(t),Qt()}async function Kt(e){try{const t=m(),o=await(await f(`${t}/api/mobile-push/test`,{method:"POST",headers:u(),body:JSON.stringify({user_id:e})})).json();o.success||o.stub_mode?(o.stub_mode?r("Test notification logged (Firebase not configured)","warning"):r(`Test notification sent: ${o.success_count??0} succeeded, ${o.failure_count??0} failed`,"success"),ae()):r(o.error??"Error sending test notification","error")}catch(t){console.error("Error sending test notification:",t),r("Error sending test notification","error")}}async function Yt(){try{const e=m(),[t,n]=await Promise.all([f(`${e}/api/recording-announcements/statistics`,{headers:u()}),f(`${e}/api/recording-announcements/config`,{headers:u()})]),[o,s]=await Promise.all([t.json(),n.json()]);if(o){const a=i=>document.getElementById(i);a("announcements-enabled")&&(a("announcements-enabled").textContent=o.enabled?"Enabled":"Disabled"),a("announcements-played")&&(a("announcements-played").textContent=String(o.announcements_played??0)),a("consent-accepted")&&(a("consent-accepted").textContent=String(o.consent_accepted??0)),a("consent-declined")&&(a("consent-declined").textContent=String(o.consent_declined??0)),a("announcement-type")&&(a("announcement-type").textContent=o.announcement_type??"N/A"),a("require-consent")&&(a("require-consent").textContent=o.require_consent?"Yes":"No")}if(s){const a=i=>document.getElementById(i);a("audio-file-path")&&(a("audio-file-path").textContent=s.audio_path??"N/A"),a("announcement-text")&&(a("announcement-text").textContent=s.announcement_text??"N/A")}}catch(e){console.error("Error loading recording announcements data:",e),r("Error loading recording announcements data","error")}}async function $a(){try{const e=m(),n=await(await f(`${e}/api/framework/speech-analytics/configs`,{headers:u()})).json(),o=document.getElementById("speech-analytics-configs-table");if(!o)return;if(!n.configs||n.configs.length===0){o.innerHTML='<tr><td colspan="5" class="loading">No extension-specific configurations. Using system defaults.</td></tr>';return}o.innerHTML=n.configs.map(s=>`
            <tr>
                <td>${l(s.extension)}</td>
                <td>${s.transcription_enabled?"Enabled":"Disabled"}</td>
                <td>${s.sentiment_enabled?"Enabled":"Disabled"}</td>
                <td>${s.summarization_enabled?"Enabled":"Disabled"}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editSpeechAnalyticsConfig('${l(s.extension)}')">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteSpeechAnalyticsConfig('${l(s.extension)}')">Delete</button>
                </td>
            </tr>
        `).join("")}catch(e){console.error("Error loading speech analytics configs:",e),r("Error loading speech analytics configurations","error")}}async function Zt(){try{const e=m(),t=await f(`${e}/api/framework/integrations/activity-log`,{headers:u()});if(!t.ok){console.error("Error loading CRM activity log:",t.status),r("Error loading CRM activity log","error");return}const n=await t.json(),o=document.getElementById("crm-activity-log-table");if(!o)return;if(!n.activities||n.activities.length===0){o.innerHTML='<tr><td colspan="5" class="loading">No integration activity yet</td></tr>';return}o.innerHTML=n.activities.map(s=>{const a=s.status==="success"?"success":"error",i=s.status==="success"?"OK":"FAIL";return`
                <tr>
                    <td>${l(new Date(s.timestamp).toLocaleString())}</td>
                    <td>${l(s.integration)}</td>
                    <td>${l(s.action)}</td>
                    <td class="${a}">${i} ${l(s.status)}</td>
                    <td>${l(s.details??"-")}</td>
                </tr>
            `}).join("")}catch(e){console.error("Error loading CRM activity log:",e),r("Error loading CRM activity log","error")}}async function _a(){if(confirm("Clear old activity log entries? This will remove entries older than 30 days."))try{const e=m(),n=await(await f(`${e}/api/framework/integrations/activity-log/clear`,{method:"POST",headers:u()})).json();n.success?(r(`Cleared ${n.deleted_count??0} old entries`,"success"),Zt()):r(n.error??"Error clearing activity log","error")}catch(e){console.error("Error clearing CRM activity log:",e),r("Error clearing activity log","error")}}async function Aa(){try{const e=m(),[t,n,o]=await Promise.all([f(`${e}/api/framework/compliance/soc2/controls`,{headers:u()}),f(`${e}/api/framework/compliance/gdpr/consents`,{headers:u()}),f(`${e}/api/framework/compliance/pci/audit-log`,{headers:u()})]),[s,a,i]=await Promise.all([t.ok?t.json():null,n.ok?n.json():null,o.ok?o.json():null]),c=document.getElementById("compliance-soc2-count");if(c&&s){const y=s.controls??[];c.textContent=String(y.length)}const d=document.getElementById("compliance-gdpr-count");if(d&&a){const y=a.consents??[];d.textContent=String(y.length)}const g=document.getElementById("compliance-pci-count");if(g&&i){const y=i.entries??i.audit_log??[];g.textContent=String(y.length)}}catch(e){console.error("Error loading compliance data:",e)}}window.loadFraudAlerts=se;window.showAddBlockedPatternModal=ya;window.closeAddBlockedPatternModal=Wt;window.addBlockedPattern=ba;window.deleteBlockedPattern=ha;window.loadCallbackQueue=j;window.showRequestCallbackModal=va;window.closeRequestCallbackModal=zt;window.requestCallback=wa;window.startCallback=Ea;window.completeCallback=ka;window.cancelCallback=xa;window.loadMobilePushDevices=ae;window.showRegisterDeviceModal=Ia;window.closeRegisterDeviceModal=Gt;window.registerDevice=Sa;window.showTestNotificationModal=Ca;window.closeTestNotificationModal=Qt;window.sendTestNotificationForm=Ta;window.sendTestNotification=Kt;window.loadRecordingAnnouncementsStats=Yt;window.loadSpeechAnalyticsConfigs=$a;window.loadCRMActivityLog=Zt;window.clearCRMActivityLog=_a;window.loadFraudDetectionData=se;window.loadMobilePushConfig=ae;window.loadRecordingAnnouncements=Yt;window.loadComplianceData=Aa;const Ba={completed:"success",failed:"error",cancelled:"warning",busy:"warning","no-answer":"warning"};async function Pa(){try{const e=m(),t=await f(`${e}/api/extensions`,{headers:u()});if(!t.ok)throw new Error(`HTTP ${t.status}`);return(await t.json()).extensions??[]}catch(e){return console.error("Error loading extensions for click-to-dial:",e),window.currentExtensions??[]}}async function Pe(){try{const e=m(),n=await(await f(`${e}/api/framework/click-to-dial/configs`,{headers:u()})).json();if(n.error){console.error("Error loading click-to-dial configs:",n.error);return}const o=await Pa(),s=document.getElementById("ctd-extension-select"),a=document.getElementById("ctd-history-extension");if(s&&o.length>0){s.innerHTML='<option value="">Select Extension</option>';for(const c of o){const d=document.createElement("option");d.value=c.number,d.textContent=`${c.number} - ${c.name}`,s.appendChild(d)}}else s&&(s.innerHTML='<option value="">No extensions available</option>');if(a&&o.length>0){a.innerHTML='<option value="">All Extensions</option>';for(const c of o){const d=document.createElement("option");d.value=c.number,d.textContent=`${c.number} - ${c.name}`,a.appendChild(d)}}else a&&(a.innerHTML='<option value="">No extensions available</option>');const i=document.getElementById("ctd-configs-table");if(!i)return;if(!n.configs||n.configs.length===0){i.innerHTML='<tr><td colspan="6" style="text-align: center;">No configurations found. Configure extensions above.</td></tr>';return}i.innerHTML=n.configs.map(c=>`
            <tr>
                <td>${l(c.extension)}</td>
                <td><span class="status-badge ${c.enabled?"success":"error"}">${c.enabled?"Enabled":"Disabled"}</span></td>
                <td>${c.default_caller_id?l(c.default_caller_id):"-"}</td>
                <td>${c.auto_answer?"Yes":"No"}</td>
                <td>${c.browser_notification?"Yes":"No"}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editClickToDialConfig('${l(c.extension)}')">Edit</button>
                </td>
            </tr>
        `).join("")}catch(e){console.error("Error loading click-to-dial configs:",e),e instanceof Error&&A(e,"Loading click-to-dial configurations")}}function we(e){const t=document.getElementById("ctd-config-section"),n=document.getElementById("ctd-no-extension");t&&n&&(t.style.display=e?"block":"none",n.style.display=e?"none":"block")}async function Xt(){const t=document.getElementById("ctd-extension-select")?.value;if(!t){we(!1);return}try{const n=m(),s=await(await f(`${n}/api/framework/click-to-dial/config/${t}`,{headers:u()})).json();if(s.error){console.error("Error loading config:",s.error);const a=document.getElementById("ctd-current-extension");a&&(a.textContent=t);const i=document.getElementById("ctd-enabled");i&&(i.checked=!0);const c=document.getElementById("ctd-caller-id");c&&(c.value="");const d=document.getElementById("ctd-auto-answer");d&&(d.checked=!1);const g=document.getElementById("ctd-browser-notification");g&&(g.checked=!0)}else{const a=document.getElementById("ctd-current-extension");a&&(a.textContent=t);const i=document.getElementById("ctd-enabled");i&&(i.checked=s.config.enabled);const c=document.getElementById("ctd-caller-id");c&&(c.value=s.config.default_caller_id??"");const d=document.getElementById("ctd-auto-answer");d&&(d.checked=s.config.auto_answer);const g=document.getElementById("ctd-browser-notification");g&&(g.checked=s.config.browser_notification)}we(!0)}catch(n){console.error("Error loading click-to-dial config:",n),n instanceof Error&&A(n,"Loading click-to-dial configuration")}}async function Ma(e){e.preventDefault();const n=document.getElementById("ctd-current-extension")?.textContent;if(!n){r("No extension selected","error");return}const o={enabled:document.getElementById("ctd-enabled")?.checked??!1,default_caller_id:document.getElementById("ctd-caller-id")?.value.trim()||null,auto_answer:document.getElementById("ctd-auto-answer")?.checked??!1,browser_notification:document.getElementById("ctd-browser-notification")?.checked??!1};try{const s=m(),i=await(await f(`${s}/api/framework/click-to-dial/config/${n}`,{method:"POST",headers:u(),body:JSON.stringify(o)})).json();i.error?r(`Error: ${i.error}`,"error"):(r("Configuration saved successfully","success"),Pe())}catch(s){console.error("Error saving config:",s),s instanceof Error&&A(s,"Saving click-to-dial configuration"),r("Error saving configuration","error")}}async function La(e){const t=document.getElementById("ctd-extension-select");if(t){t.value=e,await Xt();const n=document.getElementById("ctd-config-section");n&&n.scrollIntoView({behavior:"smooth"})}}async function Da(){const t=document.getElementById("ctd-extension-select")?.value,n=document.getElementById("ctd-phone-number"),o=n?.value.trim();if(!t){r("Please select an extension","error");return}if(!o){r("Please enter a phone number","error");return}try{const s=m(),i=await(await f(`${s}/api/framework/click-to-dial/call/${t}`,{method:"POST",headers:u(),body:JSON.stringify({destination:o})})).json();i.error?r(`Error: ${i.error}`,"error"):(r(`Call initiated from extension ${t} to ${o}`,"success"),n&&(n.value=""),setTimeout(()=>en(),1e3))}catch(s){console.error("Error initiating call:",s),s instanceof Error&&A(s,"Initiating click-to-dial call"),r("Error initiating call","error")}}async function en(){const t=document.getElementById("ctd-history-extension")?.value,n=document.getElementById("ctd-history-table");if(n){if(!t){n.innerHTML='<tr><td colspan="5" style="text-align: center;">Select an extension to view history</td></tr>';return}try{const o=m(),a=await(await f(`${o}/api/framework/click-to-dial/history/${t}`,{headers:u()})).json();if(a.error){n.innerHTML=`<tr><td colspan="5" style="text-align: center;">Error: ${l(a.error)}</td></tr>`;return}if(!a.history||a.history.length===0){n.innerHTML='<tr><td colspan="5" style="text-align: center;">No call history found</td></tr>';return}n.innerHTML=a.history.map(i=>{const c=new Date(i.timestamp).toLocaleString(),d=i.duration?`${i.duration}s`:"-",g=Ba[i.status]??"warning";return`
                <tr>
                    <td>${l(c)}</td>
                    <td>${l(i.extension)}</td>
                    <td>${l(i.destination)}</td>
                    <td>${d}</td>
                    <td><span class="status-badge ${g}">${l(i.status)}</span></td>
                </tr>
            `}).join("")}catch(o){console.error("Error loading history:",o),o instanceof Error&&A(o,"Loading click-to-dial history"),n&&(n.innerHTML='<tr><td colspan="5" style="text-align: center;">Error loading history</td></tr>')}}}async function Ra(){try{const e=m(),n=await(await f(`${e}/api/webrtc/phone-config`,{headers:u()})).json();if(n.success){const o=document.getElementById("webrtc-phone-extension");o&&(o.value=n.extension??(typeof DEFAULT_WEBRTC_EXTENSION<"u"?DEFAULT_WEBRTC_EXTENSION:"")),typeof initWebRTCPhone=="function"&&initWebRTCPhone()}else console.error("Failed to load WebRTC phone config:",n.error)}catch(e){console.error("Error loading WebRTC phone config:",e)}}async function Fa(e){e.preventDefault();const n=document.getElementById("webrtc-phone-extension")?.value.trim()??"";if(!n){r("Please enter an extension","error");return}try{const o=m(),a=await(await f(`${o}/api/webrtc/phone-config`,{method:"POST",headers:u(),body:JSON.stringify({extension:n})})).json();a.success?(r("Phone extension saved successfully! Reloading phone...","success"),typeof initWebRTCPhone=="function"&&initWebRTCPhone()):r(`Error: ${a.error??"Failed to save phone extension"}`,"error")}catch(o){console.error("Error saving WebRTC phone config:",o);const s=o instanceof Error?o.message:String(o);r(`Error: ${s}`,"error")}}window.loadClickToDialConfigs=Pe;window.toggleClickToDialConfigSections=we;window.loadClickToDialConfig=Xt;window.saveClickToDialConfig=Ma;window.editClickToDialConfig=La;window.initiateClickToDial=Da;window.loadClickToDialHistory=en;window.loadWebRTCPhoneConfig=Ra;window.saveWebRTCPhoneConfig=Fa;window.loadClickToDialTab=Pe;async function ie(){try{const e=m(),n=await(await f(`${e}/api/framework/nomadic-e911/sites`,{headers:u()})).json(),o=document.getElementById("e911-sites-table");if(!o)return;if(!n.sites||n.sites.length===0){o.innerHTML='<tr><td colspan="5" class="loading">No E911 sites configured</td></tr>';return}o.innerHTML=n.sites.map(s=>`
            <tr>
                <td>${l(s.site_name)}</td>
                <td>${l(s.street_address)}, ${l(s.city)}, ${l(s.state)} ${l(s.postal_code)}</td>
                <td>${l(s.ip_range_start??"")} - ${l(s.ip_range_end??"")}</td>
                <td>${l(s.psap_number??"Default")}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editE911Site(${s.id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteE911Site(${s.id})">Delete</button>
                </td>
            </tr>
        `).join("")}catch(e){console.error("Error loading E911 sites:",e),r("Error loading E911 sites","error")}}async function Me(){try{const e=m(),n=await(await f(`${e}/api/framework/nomadic-e911/locations`,{headers:u()})).json(),o=document.getElementById("extension-locations-table");if(!o)return;if(!n.locations||n.locations.length===0){o.innerHTML='<tr><td colspan="5" class="loading">No location data available</td></tr>';return}o.innerHTML=n.locations.map(s=>`
            <tr>
                <td>${l(s.extension)}</td>
                <td>${l(s.site_name??"Unknown")} - ${l(s.address??"N/A")}</td>
                <td>${l(s.detection_method??"N/A")}</td>
                <td>${s.last_updated?new Date(s.last_updated).toLocaleString():"N/A"}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="updateExtensionLocation('${l(s.extension)}')">Update</button>
                </td>
            </tr>
        `).join("")}catch(e){console.error("Error loading extension locations:",e),r("Error loading extension locations","error")}}async function Na(){const t=document.getElementById("location-history-extension")?.value??"",n=t?`/api/framework/nomadic-e911/history/${t}`:"/api/framework/nomadic-e911/history";try{const o=m(),a=await(await f(`${o}${n}`,{headers:u()})).json(),i=document.getElementById("location-history-table");if(!i)return;if(!a.history||a.history.length===0){i.innerHTML='<tr><td colspan="5" class="loading">No location history available</td></tr>';return}i.innerHTML=a.history.map(c=>`
            <tr>
                <td>${l(new Date(c.timestamp).toLocaleString())}</td>
                <td>${l(c.extension)}</td>
                <td>${l(c.site_name??"N/A")}</td>
                <td>${l(c.detection_method??"N/A")}</td>
                <td>${l(c.ip_address??"N/A")}</td>
            </tr>
        `).join("")}catch(o){console.error("Error loading location history:",o),r("Error loading location history","error")}}function re(){const e=document.getElementById("e911-site-modal");e&&e.remove()}function tn(e){return`
        <div id="e911-site-modal" class="modal" style="display: flex; align-items: center;
             justify-content: center;">
            <div class="modal-content" style="max-width: 600px;">
                <div class="modal-header">
                    <h3>${e?"Edit":"Add"} E911 Site</h3>
                    <span class="close" onclick="removeE911SiteModal()">&times;</span>
                </div>
                <form id="e911-site-form">
                    ${e?`<input type="hidden" name="site_id" value="${e.id}">`:""}
                    <div class="form-group">
                        <label>Site Name:</label>
                        <input type="text" name="site_name" required class="form-control"
                            value="${l(e?.site_name??"")}">
                    </div>
                    <div class="form-group">
                        <label>Street Address:</label>
                        <input type="text" name="street_address" class="form-control"
                            value="${l(e?.street_address??"")}">
                    </div>
                    <div class="form-group">
                        <label>City:</label>
                        <input type="text" name="city" class="form-control"
                            value="${l(e?.city??"")}">
                    </div>
                    <div class="form-group">
                        <label>State:</label>
                        <input type="text" name="state" class="form-control"
                            value="${l(e?.state??"")}">
                    </div>
                    <div class="form-group">
                        <label>Postal Code:</label>
                        <input type="text" name="postal_code" class="form-control"
                            value="${l(e?.postal_code??"")}">
                    </div>
                    <div class="form-group">
                        <label>Country:</label>
                        <input type="text" name="country" class="form-control"
                            value="${l(e?.country??"USA")}" placeholder="USA">
                    </div>
                    <div class="form-group">
                        <label>IP Range Start:</label>
                        <input type="text" name="ip_range_start" required class="form-control"
                            value="${l(e?.ip_range_start??"")}"
                            placeholder="192.168.1.0">
                    </div>
                    <div class="form-group">
                        <label>IP Range End:</label>
                        <input type="text" name="ip_range_end" required class="form-control"
                            value="${l(e?.ip_range_end??"")}"
                            placeholder="192.168.1.255">
                    </div>
                    <div class="form-group">
                        <label>Emergency Trunk:</label>
                        <input type="text" name="emergency_trunk" class="form-control"
                            value="${l(e?.emergency_trunk??"")}">
                    </div>
                    <div class="form-group">
                        <label>PSAP Number:</label>
                        <input type="text" name="psap_number" class="form-control"
                            value="${l(e?.psap_number??"")}"
                            placeholder="Default PSAP">
                    </div>
                    <div class="form-group">
                        <label>ELIN:</label>
                        <input type="text" name="elin" class="form-control"
                            value="${l(e?.elin??"")}">
                        <small>Emergency Location Information Number</small>
                    </div>
                    <div class="form-group">
                        <label>Building:</label>
                        <input type="text" name="building" class="form-control"
                            value="${l(e?.building??"")}">
                    </div>
                    <div class="form-group">
                        <label>Floor:</label>
                        <input type="text" name="floor" class="form-control"
                            value="${l(e?.floor??"")}">
                    </div>
                    <div class="modal-actions">
                        <button type="submit" class="btn btn-primary">
                            ${e?"Update":"Create"} Site
                        </button>
                        <button type="button" class="btn btn-secondary"
                            onclick="removeE911SiteModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `}async function nn(e){const t=new FormData(e),n=t.get("site_id"),o={};for(const[s,a]of t.entries())s!=="site_id"&&String(a).trim()&&(o[s]=String(a).trim());try{const s=m(),a=n?`${s}/api/framework/nomadic-e911/sites/${n}`:`${s}/api/framework/nomadic-e911/create-site`,d=await(await f(a,{method:n?"PUT":"POST",headers:u(),body:JSON.stringify(o)})).json();d.success?(r("E911 site saved successfully","success"),re(),await ie()):r(d.error??"Error saving E911 site","error")}catch(s){console.error("Error saving E911 site:",s),r("Error saving E911 site","error")}}function Ha(){re(),document.body.insertAdjacentHTML("beforeend",tn());const e=document.getElementById("e911-site-form");e.onsubmit=t=>{t.preventDefault(),nn(e)}}function ja(e){const t=m();f(`${t}/api/framework/nomadic-e911/sites`,{headers:u()}).then(async n=>{const s=(await n.json()).sites?.find(i=>i.id===e);if(!s){r("Site not found","error");return}re(),document.body.insertAdjacentHTML("beforeend",tn(s));const a=document.getElementById("e911-site-form");a.onsubmit=i=>{i.preventDefault(),nn(a)}}).catch(()=>{r("Error loading site details","error")})}async function Oa(e){if(confirm(`Delete E911 site ${e}?`))try{const t=m(),o=await(await f(`${t}/api/framework/nomadic-e911/sites/${e}`,{method:"DELETE",headers:u()})).json();o.success?(r("E911 site deleted","success"),await ie()):r(o.error??"Error deleting site","error")}catch(t){console.error("Error deleting E911 site:",t),r("Error deleting E911 site","error")}}function ce(){const e=document.getElementById("location-update-modal");e&&e.remove()}function on(e){return`
        <div id="location-update-modal" class="modal" style="display: flex;
             align-items: center; justify-content: center;">
            <div class="modal-content" style="max-width: 600px;">
                <div class="modal-header">
                    <h3>Update Extension Location</h3>
                    <span class="close" onclick="removeLocationModal()">&times;</span>
                </div>
                <form id="location-update-form">
                    <div class="form-group">
                        <label>Extension:</label>
                        <input type="text" name="extension" required class="form-control"
                            value="${l(e??"")}"
                            ${e?"readonly":""}>
                    </div>
                    <div class="form-group">
                        <label>Location Name:</label>
                        <input type="text" name="location_name" class="form-control"
                            placeholder="Main Office">
                    </div>
                    <div class="form-group">
                        <label>IP Address:</label>
                        <input type="text" name="ip_address" class="form-control"
                            placeholder="192.168.1.100">
                    </div>
                    <div class="form-group">
                        <label>Street Address:</label>
                        <input type="text" name="street_address" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>City:</label>
                        <input type="text" name="city" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>State:</label>
                        <input type="text" name="state" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>Postal Code:</label>
                        <input type="text" name="postal_code" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>Country:</label>
                        <input type="text" name="country" class="form-control"
                            placeholder="USA">
                    </div>
                    <div class="form-group">
                        <label>Building:</label>
                        <input type="text" name="building" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>Floor:</label>
                        <input type="text" name="floor" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>Room:</label>
                        <input type="text" name="room" class="form-control">
                    </div>
                    <div class="modal-actions">
                        <button type="submit" class="btn btn-primary">Update Location</button>
                        <button type="button" class="btn btn-secondary"
                            onclick="removeLocationModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `}async function sn(e){const t=new FormData(e),n=String(t.get("extension")??"").trim();if(!n){r("Extension is required","error");return}const o={};for(const[s,a]of t.entries())s!=="extension"&&String(a).trim()&&(o[s]=String(a).trim());try{const s=m(),i=await(await f(`${s}/api/framework/nomadic-e911/update-location/${encodeURIComponent(n)}`,{method:"POST",headers:u(),body:JSON.stringify(o)})).json();i.success?(r(`Location updated for extension ${n}`,"success"),ce(),await Me()):r(i.error??"Error updating location","error")}catch(s){console.error("Error updating location:",s),r("Error updating location","error")}}function qa(){ce(),document.body.insertAdjacentHTML("beforeend",on());const e=document.getElementById("location-update-form");e.onsubmit=t=>{t.preventDefault(),sn(e)}}function Ua(e){ce(),document.body.insertAdjacentHTML("beforeend",on(e));const t=document.getElementById("location-update-form");t.onsubmit=n=>{n.preventDefault(),sn(t)}}function le(){const e=document.getElementById("speech-config-modal");e&&e.remove()}function an(e,t){return`
        <div id="speech-config-modal" class="modal" style="display: flex;
             align-items: center; justify-content: center;">
            <div class="modal-content" style="max-width: 600px;">
                <div class="modal-header">
                    <h3>Add Speech Analytics Config</h3>
                    <span class="close" onclick="removeSpeechConfigModal()">&times;</span>
                </div>
                <form id="speech-config-form">
                    <div class="form-group">
                        <label>Extension:</label>
                        <input type="text" name="extension" required class="form-control"
                            value="${l(e??"")}"
                            ${e?"readonly":""}>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="enabled"
                                checked>
                            Enabled
                        </label>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="transcription_enabled"
                                checked>
                            Transcription
                        </label>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="sentiment_enabled"
                                checked>
                            Sentiment Analysis
                        </label>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="summarization_enabled"
                                checked>
                            Call Summarization
                        </label>
                    </div>
                    <div class="form-group">
                        <label>Keywords (comma-separated):</label>
                        <input type="text" name="keywords" class="form-control"
                            value="${l("")}"
                            placeholder="urgent, escalation, complaint">
                    </div>
                    <div class="form-group">
                        <label>Alert Threshold (0.0 - 1.0):</label>
                        <input type="number" name="alert_threshold" class="form-control"
                            value="${.7}"
                            min="0" max="1" step="0.1">
                    </div>
                    <div class="modal-actions">
                        <button type="submit" class="btn btn-primary">
                            Create Config
                        </button>
                        <button type="button" class="btn btn-secondary"
                            onclick="removeSpeechConfigModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `}async function rn(e){const t=new FormData(e),n=String(t.get("extension")??"").trim();if(!n){r("Extension is required","error");return}const o={enabled:t.get("enabled")==="on",transcription_enabled:t.get("transcription_enabled")==="on",sentiment_enabled:t.get("sentiment_enabled")==="on",summarization_enabled:t.get("summarization_enabled")==="on",keywords:String(t.get("keywords")??"").trim(),alert_threshold:parseFloat(String(t.get("alert_threshold")??"0.7"))};try{const s=m(),i=await(await f(`${s}/api/framework/speech-analytics/config/${encodeURIComponent(n)}`,{method:"POST",headers:u(),body:JSON.stringify(o)})).json();i.success?(r("Speech analytics config saved","success"),le()):r(i.error??"Error saving config","error")}catch(s){console.error("Error saving speech analytics config:",s),r("Error saving speech analytics config","error")}}function Va(){le(),document.body.insertAdjacentHTML("beforeend",an());const e=document.getElementById("speech-config-form");e.onsubmit=t=>{t.preventDefault(),rn(e)}}function Ja(e){le(),document.body.insertAdjacentHTML("beforeend",an(e));const t=document.getElementById("speech-config-form");t.onsubmit=n=>{n.preventDefault(),rn(t)}}async function Wa(e){if(confirm(`Delete speech analytics config for extension ${e}?`))try{const n=`${m()}/api/framework/speech-analytics/config/${encodeURIComponent(e)}`,s=await(await f(n,{method:"DELETE",headers:u()})).json();s.success?r("Speech analytics config deleted","success"):r(s.error??"Error deleting config","error")}catch(t){console.error("Error deleting speech analytics config:",t),r("Error deleting speech analytics config","error")}}window.loadE911Sites=ie;window.loadExtensionLocations=Me;window.loadLocationHistory=Na;window.showAddE911SiteModal=Ha;window.editE911Site=ja;window.deleteE911Site=Oa;window.removeE911SiteModal=re;window.showUpdateLocationModal=qa;window.updateExtensionLocation=Ua;window.removeLocationModal=ce;window.showAddSpeechAnalyticsConfigModal=Va;window.editSpeechAnalyticsConfig=Ja;window.deleteSpeechAnalyticsConfig=Wa;window.removeSpeechConfigModal=le;window.loadNomadicE911Data=function(){ie(),Me()};window.fetchWithTimeout=f;window.getAuthHeaders=u;window.getApiBaseUrl=m;window.DEFAULT_FETCH_TIMEOUT=et;window.store=Y;window.showNotification=r;window.displayError=A;window.setSuppressErrorNotifications=lo;window.showTab=L;window.switchTab=L;window.initializeTabs=ut;window.escapeHtml=l;window.copyToClipboard=ro;window.formatDate=tt;window.truncate=nt;window.getDuration=ot;window.getStatusBadge=st;window.getHealthBadge=at;window.getPriorityBadge=it;window.getQualityClass=rt;window.getScheduleDescription=ct;window.downloadLicense=lt;window.executeBatched=ke;window.refreshAllData=xe;const q="/admin/login.html";async function za(){if(debugLog("Initializing user context..."),!localStorage.getItem("pbx_token")){debugLog("No authentication token found, redirecting to login..."),window.location.replace(q);return}try{const s=await f(`${m()}/api/extensions`,{headers:u()},5e3);if(s.status===401||s.status===403){debugLog("Authentication token is invalid, redirecting to login..."),localStorage.removeItem("pbx_token"),localStorage.removeItem("pbx_extension"),localStorage.removeItem("pbx_is_admin"),localStorage.removeItem("pbx_name"),window.location.replace(q);return}if(!s.ok)throw new Error(`HTTP ${s.status}`)}catch(s){console.error("Error verifying authentication:",s),r("Unable to verify authentication - server may be starting up","error")}const t=localStorage.getItem("pbx_extension"),n=localStorage.getItem("pbx_is_admin")==="true",o=localStorage.getItem("pbx_name")||"User";if(!t){debugLog("No extension number found, redirecting to login..."),window.location.replace(q);return}Y.set("currentUser",{number:t,is_admin:n,name:o}),debugLog("User context initialized:",{number:t,is_admin:n,name:o}),n?(debugLog("Admin user - showing dashboard tab"),L("dashboard")):(debugLog("Regular user - showing webrtc-phone tab"),L("webrtc-phone")),debugLog("User context initialization complete")}function Ga(){const e=document.querySelectorAll("form[data-ajax]");for(const t of e)t.addEventListener("submit",n=>{n.preventDefault(),debugLog("Ajax form submitted:",t.id)})}function Qa(){const e=document.getElementById("logout-button");e&&e.addEventListener("click",async()=>{const t=localStorage.getItem("pbx_token"),n=u();localStorage.removeItem("pbx_token"),localStorage.removeItem("pbx_extension"),localStorage.removeItem("pbx_is_admin"),localStorage.removeItem("pbx_name"),localStorage.removeItem("pbx_current_extension");try{t&&await fetch(`${m()}/api/auth/logout`,{method:"POST",headers:n})}catch(o){console.error("Logout API error:",o)}window.location.href=q})}async function Ge(){const e=document.getElementById("connection-status");if(!e){console.error("Connection status badge element not found");return}try{if((await f(`${m()}/api/status`,{headers:u()},5e3)).ok)e.textContent="Connected",e.classList.remove("connecting","disconnected"),e.classList.add("connected");else throw new Error("Connection failed")}catch(t){console.error("Connection check failed:",t),e.textContent="Disconnected",e.classList.remove("connecting","connected"),e.classList.add("disconnected")}}document.addEventListener("DOMContentLoaded",async()=>{debugLog("DOMContentLoaded event fired - starting initialization"),Ge(),setInterval(Ge,1e4),debugLog("Initializing tabs, forms, and logout"),ut(),Ga(),Qa(),yo();try{await za(),debugLog("User context initialization complete")}catch(e){console.error("User context initialization failed:",e)}debugLog("Page initialization complete")});async function Ka(){try{const e=await fetch(`${API_BASE}/api/auto-attendant/config`,{headers:pbxAuthHeaders()});if(e.ok){const t=await e.json();document.getElementById("aa-enabled").checked=t.enabled??!1,document.getElementById("aa-extension").value=t.extension??"0",document.getElementById("aa-timeout").value=t.timeout??10,document.getElementById("aa-max-retries").value=t.max_retries??3}await Fe(),await $(),await cn()}catch(e){console.error("Error loading auto attendant config:",e),showNotification("Failed to load auto attendant configuration","error")}}async function cn(){try{const e=await fetch(`${API_BASE}/api/auto-attendant/prompts`,{headers:pbxAuthHeaders()});if(!e.ok){debugWarn("Failed to load prompts, using defaults");return}const t=await e.json(),n=t.prompts??{},o=t.company_name??"",s=document.getElementById("aa-company-name");s&&(s.value=o),n.welcome&&(document.getElementById("aa-prompt-welcome").value=n.welcome),n.main_menu&&(document.getElementById("aa-prompt-main-menu").value=n.main_menu),n.invalid&&(document.getElementById("aa-prompt-invalid").value=n.invalid),n.timeout&&(document.getElementById("aa-prompt-timeout").value=n.timeout),n.transferring&&(document.getElementById("aa-prompt-transferring").value=n.transferring)}catch(e){console.error("Error loading prompts:",e)}}async function $(){try{const e=await fetch(`${API_BASE}/api/auto-attendant/menus/${I}/items`,{headers:pbxAuthHeaders()});if(e.status===404)return debugWarn(`Menu items endpoint returned 404 for menu '${I}', trying legacy API...`),await Ya();if(!e.ok){const s=await Re(e);throw new Error(`Failed to load menu options: ${e.status} - ${s.error||e.statusText}`)}const t=await e.json(),n=document.getElementById("aa-menu-options-table-body");if(Xa(),!t.items||t.items.length===0){n.innerHTML='<tr><td colspan="5" class="no-data">No menu options configured. Click "Add Menu Option" to get started.</td></tr>';return}const o=t.items.sort((s,a)=>s.digit===a.digit?0:s.digit==="*"?1:a.digit==="*"?-1:s.digit==="#"?1:a.digit==="#"?-1:s.digit.localeCompare(a.digit));n.innerHTML="";for(const s of o){const a=document.createElement("tr"),i=document.createElement("td");i.innerHTML=`<strong>${x(s.digit)}</strong>`,a.appendChild(i);const c=document.createElement("td"),d=Za(s.destination_type);c.innerHTML=`${d} ${s.destination_type}`,a.appendChild(c);const g=document.createElement("td");s.destination_type==="submenu"?g.innerHTML=`<span style="color: #4CAF50; font-weight: bold;">${x(s.destination_value)}</span>`:g.textContent=s.destination_value,a.appendChild(g);const y=document.createElement("td");y.textContent=s.description,a.appendChild(y);const p=document.createElement("td");if(s.destination_type==="submenu"){const E=document.createElement("button");E.className="btn btn-secondary",E.textContent="➡️ Open",E.onclick=()=>ln(s.destination_value),p.appendChild(E)}const h=document.createElement("button");h.className="btn btn-primary",h.textContent="✏️ Edit",h.onclick=()=>Le(s.digit,s.destination_type,s.destination_value,s.description),p.appendChild(h);const k=document.createElement("button");k.className="btn btn-danger",k.textContent="🗑️ Delete",k.onclick=()=>De(s.digit),p.appendChild(k),a.appendChild(p),n.appendChild(a)}}catch(e){console.error("Error loading menu options:",e),showNotification("Failed to load menu options","error")}}async function Ya(){try{const e=await fetch(`${API_BASE}/api/auto-attendant/menu-options`,{headers:pbxAuthHeaders()});if(!e.ok)throw new Error("Failed to load menu options");const t=await e.json(),n=document.getElementById("aa-menu-options-table-body");if(!t.menu_options||t.menu_options.length===0){n.innerHTML='<tr><td colspan="5" class="no-data">No menu options configured.</td></tr>';return}const o=t.menu_options.sort((s,a)=>s.digit===a.digit?0:s.digit==="*"?1:a.digit==="*"?-1:s.digit==="#"?1:a.digit==="#"?-1:s.digit.localeCompare(a.digit));n.innerHTML="";for(const s of o){const a=document.createElement("tr"),i=document.createElement("td");i.innerHTML=`<strong>${x(s.digit)}</strong>`,a.appendChild(i);const c=document.createElement("td");c.innerHTML="📞 extension",a.appendChild(c);const d=document.createElement("td");d.textContent=s.destination,a.appendChild(d);const g=document.createElement("td");g.textContent=s.description,a.appendChild(g);const y=document.createElement("td"),p=document.createElement("button");p.className="btn btn-primary",p.textContent="✏️ Edit",p.onclick=()=>Le(s.digit,"extension",s.destination,s.description),y.appendChild(p);const h=document.createElement("button");h.className="btn btn-danger",h.textContent="🗑️ Delete",h.onclick=()=>De(s.digit),y.appendChild(h),a.appendChild(y),n.appendChild(a)}}catch(e){throw console.error("Error loading legacy menu options:",e),e}}function Za(e){return{extension:"📞",submenu:"📁",queue:"👥",voicemail:"📧",operator:"🎧"}[e]??"❓"}async function ln(e){I=e,await $()}async function Xa(){try{const e=await fetch(`${API_BASE}/api/auto-attendant/menus/${I}`,{headers:pbxAuthHeaders()});if(e.ok){const t=await e.json(),n=document.getElementById("breadcrumb-path");if(n){let o=x(t.menu.menu_name);I!=="main"&&(o=`<button class="btn btn-secondary" onclick="navigateToMenu('main')" style="margin-right: 10px;">⬅️ Back to Main</button> ${o}`),n.innerHTML=o}}}catch(e){console.error("Error updating breadcrumb:",e)}}document.addEventListener("DOMContentLoaded",function(){const e=document.getElementById("auto-attendant-config-form");e&&e.addEventListener("submit",async function(t){t.preventDefault();const n={enabled:document.getElementById("aa-enabled").checked,extension:document.getElementById("aa-extension").value,timeout:parseInt(document.getElementById("aa-timeout").value,10),max_retries:parseInt(document.getElementById("aa-max-retries").value,10)};try{const o=await fetch(`${API_BASE}/api/auto-attendant/config`,{method:"PUT",headers:pbxAuthHeaders(),body:JSON.stringify(n)});if(o.ok)showNotification("Auto attendant configuration saved successfully","success");else{const s=await o.json();showNotification(s.error||"Failed to save configuration","error")}}catch(o){console.error("Error saving auto attendant config:",o),showNotification("Failed to save configuration","error")}})});function ei(){document.getElementById("add-menu-option-modal").classList.add("active"),document.getElementById("add-menu-option-form").reset()}function dn(){document.getElementById("add-menu-option-modal").classList.remove("active")}function Le(e,t,n,o){document.getElementById("edit-menu-digit").value=e,document.getElementById("edit-menu-digit-display").textContent=e,document.getElementById("edit-menu-dest-type").value=t??"extension",document.getElementById("edit-menu-description").value=o,gn("edit"),t==="submenu"?document.getElementById("edit-menu-submenu").value=n:document.getElementById("edit-menu-destination").value=n,document.getElementById("edit-menu-option-modal").classList.add("active")}function un(){document.getElementById("edit-menu-option-modal").classList.remove("active")}async function De(e){if(confirm(`Are you sure you want to delete menu option for digit "${e}"?`))try{const t=await fetch(`${API_BASE}/api/auto-attendant/menus/${I}/items/${e}`,{method:"DELETE",headers:pbxAuthHeaders()});if(t.ok)showNotification("Menu option deleted successfully","success"),$();else{const n=await t.json();showNotification(n.error||"Failed to delete menu option","error")}}catch(t){console.error("Error deleting menu option:",t),showNotification("Failed to delete menu option","error")}}document.addEventListener("DOMContentLoaded",function(){const e=document.getElementById("add-menu-option-form");e&&e.addEventListener("submit",async function(t){t.preventDefault();const n=document.getElementById("new-menu-dest-type").value;let o;n==="submenu"?o=document.getElementById("new-menu-submenu").value:o=document.getElementById("new-menu-destination").value;const s={digit:document.getElementById("new-menu-digit").value,destination_type:n,destination_value:o,description:document.getElementById("new-menu-description").value};try{const a=await fetch(`${API_BASE}/api/auto-attendant/menus/${I}/items`,{method:"POST",headers:pbxAuthHeaders(),body:JSON.stringify(s)});if(a.ok)showNotification("Menu option added successfully","success"),dn(),$();else{const i=await a.json();showNotification(i.error||"Failed to add menu option","error")}}catch(a){console.error("Error adding menu option:",a),showNotification("Failed to add menu option","error")}})});document.addEventListener("DOMContentLoaded",function(){const e=document.getElementById("edit-menu-option-form");e&&e.addEventListener("submit",async function(t){t.preventDefault();const n=document.getElementById("edit-menu-digit").value,o=document.getElementById("edit-menu-dest-type").value;let s;o==="submenu"?s=document.getElementById("edit-menu-submenu").value:s=document.getElementById("edit-menu-destination").value;const a={destination_type:o,destination_value:s,description:document.getElementById("edit-menu-description").value};try{const i=await fetch(`${API_BASE}/api/auto-attendant/menus/${I}/items/${n}`,{method:"PUT",headers:pbxAuthHeaders(),body:JSON.stringify(a)});if(i.ok)showNotification("Menu option updated successfully","success"),un(),$();else{const c=await i.json();showNotification(c.error||"Failed to update menu option","error")}}catch(i){console.error("Error updating menu option:",i),showNotification("Failed to update menu option","error")}})});document.addEventListener("DOMContentLoaded",function(){const e=document.getElementById("auto-attendant-prompts-form");e&&e.addEventListener("submit",async function(t){t.preventDefault();const n=document.getElementById("voice-generation-status"),o=document.getElementById("voice-generation-message");n&&(n.style.display="block",o.textContent="⏳ Saving prompts and regenerating voices using gTTS...");const s={company_name:document.getElementById("aa-company-name").value,prompts:{welcome:document.getElementById("aa-prompt-welcome").value,main_menu:document.getElementById("aa-prompt-main-menu").value,invalid:document.getElementById("aa-prompt-invalid").value,timeout:document.getElementById("aa-prompt-timeout").value,transferring:document.getElementById("aa-prompt-transferring").value}};try{const a=await fetch(`${API_BASE}/api/auto-attendant/prompts`,{method:"PUT",headers:pbxAuthHeaders(),body:JSON.stringify(s)});if(a.ok)showNotification("Prompts saved and voices regenerated successfully!","success"),n&&(o.textContent="✅ Voice prompts regenerated successfully using gTTS!",setTimeout(()=>{n.style.display="none"},3e3));else{const i=await a.json();showNotification(i.error||"Failed to save prompts","error"),n&&(o.textContent="❌ Failed to regenerate voices",setTimeout(()=>{n.style.display="none"},3e3))}}catch(a){console.error("Error saving prompts:",a),showNotification("Failed to save prompts","error"),n&&(o.textContent="❌ Error: "+a.message,setTimeout(()=>{n.style.display="none"},3e3))}})});function x(e){const t=document.createElement("div");return t.textContent=e,t.innerHTML}let I="main",fe=[];async function Re(e){try{return await e.json()}catch(t){const n=t?.message||String(t);return t instanceof SyntaxError||/JSON|Unexpected token/i.test(n)?{error:"Server returned an invalid response format"}:t instanceof TypeError||/network|NetworkError|fetch/i.test(n)?{error:"Network error while reading server response"}:(debugWarn("Unexpected error parsing response:",t),{error:"Unable to read server response"})}}async function Fe(){try{const e=await fetch(`${API_BASE}/api/auto-attendant/menus`,{headers:pbxAuthHeaders()});if(e.ok)return fe=(await e.json()).menus??[],debugLog(`Loaded ${fe.length} menu(s) for submenu selection`),fe;{const t=await Re(e);console.error(`Failed to load menus: ${e.status} ${e.statusText}`,t);let n=t.error||e.statusText;e.status===404?n+=". API endpoint not found - check server version.":e.status>=500&&(n+=". Server error occurred."),showNotification(`Failed to load menus: ${n}`,"error")}}catch(e){console.error("Error loading menus:",e),showNotification(`Unable to connect to API: ${e.message}. Please check your connection.`,"error")}return[]}async function mn(){const e=await Fe(),t=document.getElementById("new-menu-submenu");if(t)if(t.innerHTML='<option value="">Select a submenu</option>',e.length===0){const s=document.createElement("option");s.value="",s.textContent="No menus available - create one first",s.disabled=!0,t.appendChild(s),t.disabled=!0}else{for(const s of e)if(s.menu_id!==I){const a=document.createElement("option");a.value=s.menu_id,a.textContent=`${s.menu_name} (${s.menu_id})`,t.appendChild(a)}t.disabled=!1}const n=document.getElementById("edit-menu-submenu");if(n)if(n.innerHTML='<option value="">Select a submenu</option>',e.length===0){const s=document.createElement("option");s.value="",s.textContent="No menus available - create one first",s.disabled=!0,n.appendChild(s),n.disabled=!0}else{for(const s of e)if(s.menu_id!==I){const a=document.createElement("option");a.value=s.menu_id,a.textContent=`${s.menu_name} (${s.menu_id})`,n.appendChild(a)}n.disabled=!1}const o=document.getElementById("submenu-parent");if(o)if(o.innerHTML="",e.length===0){const s=document.createElement("option");s.value="",s.textContent="No parent menus available - check API connection or server status",s.disabled=!0,s.selected=!0,o.appendChild(s),debugWarn("No menus loaded for parent dropdown")}else{for(const s of e){const a=document.createElement("option");a.value=s.menu_id,a.textContent=`${s.menu_name} (${s.menu_id})`,s.menu_id==="main"&&(a.selected=!0),o.appendChild(a)}debugLog(`Populated parent menu dropdown with ${e.length} menu(s)`)}}function gn(e){const t=document.getElementById(`${e}-menu-dest-type`),n=document.getElementById(`${e}-dest-extension-group`),o=document.getElementById(`${e}-dest-submenu-group`),s=document.getElementById(`${e}-menu-destination`),a=document.getElementById(`${e}-menu-submenu`),i=document.getElementById(`${e}-dest-label`),c=document.getElementById(`${e}-dest-help`);if(!t)return;const d=t.value;if(d==="submenu")n&&(n.style.display="none"),o&&(o.style.display="block"),s&&(s.required=!1),a&&(a.required=!0),mn();else if(n&&(n.style.display="block"),o&&(o.style.display="none"),s&&(s.required=!0),a&&(a.required=!1),i)switch(d){case"extension":i.textContent="Extension",c&&(c.textContent="Extension number to transfer to");break;case"queue":i.textContent="Queue",c&&(c.textContent="Queue extension number");break;case"voicemail":i.textContent="Voicemail Box",c&&(c.textContent="Voicemail box extension");break;case"operator":i.textContent="Operator Extension",c&&(c.textContent="Operator extension number");break}}function ti(){mn(),document.getElementById("create-submenu-modal").classList.add("active"),document.getElementById("create-submenu-form").reset()}function pn(){document.getElementById("create-submenu-modal").classList.remove("active")}async function ni(){const e=document.getElementById("menu-tree-container");e.style.display==="none"?(e.style.display="block",await oi()):e.style.display="none"}async function oi(){try{const e=await fetch(`${API_BASE}/api/auto-attendant/menu-tree`,{headers:pbxAuthHeaders()});if(!e.ok){const o=await Re(e);throw console.error(`Failed to load menu tree: ${e.status} ${e.statusText}`,o),e.status===404?new Error("Menu tree endpoint not found. The server may need to be restarted to load new API routes."):e.status===500?new Error(`Server error: ${o.error||"Internal server error"}`):new Error(`Failed to load menu tree: ${o.error||e.statusText}`)}const t=await e.json(),n=document.getElementById("menu-tree-view");t.menu_tree?(n.innerHTML=fn(t.menu_tree,0),debugLog("Menu tree loaded successfully")):(n.innerHTML='<p style="color: #666;">No menu structure available</p>',debugWarn("Menu tree data is empty"))}catch(e){console.error("Error loading menu tree:",e),showNotification(`Failed to load menu tree: ${e.message}`,"error");const t=document.getElementById("menu-tree-view");t&&(t.innerHTML=`<p class="error-message">
                <strong>Error:</strong> ${x(e.message)}<br>
                <small>Check the browser console for more details.</small>
            </p>`)}}function fn(e,t){let n=`<div style="margin-left: ${t*20}px; margin-top: 5px;">`;if(n+=`<strong>${x(e.menu_name||e.menu_id)}</strong>`,e.items&&e.items.length>0)for(const o of e.items)n+=`<div style="margin-left: ${(t+1)*20}px; margin-top: 3px;">`,n+=`📌 ${x(o.digit)}: ${x(o.description??"No description")} `,o.destination_type==="submenu"&&o.submenu?(n+='<span style="color: #4CAF50;">[Submenu]</span>',n+="</div>",n+=fn(o.submenu,t+2)):(n+=`<span style="color: #666;">(${x(o.destination_type)}: ${x(o.destination_value)})</span>`,n+="</div>");return n+="</div>",n}document.addEventListener("DOMContentLoaded",function(){const e=document.getElementById("create-submenu-form");e&&e.addEventListener("submit",async function(t){t.preventDefault();const n={menu_id:document.getElementById("submenu-id").value,parent_menu_id:document.getElementById("submenu-parent").value,menu_name:document.getElementById("submenu-name").value,prompt_text:document.getElementById("submenu-prompt").value};try{const o=await fetch(`${API_BASE}/api/auto-attendant/menus`,{method:"POST",headers:pbxAuthHeaders(),body:JSON.stringify(n)});if(o.ok)showNotification("Submenu created successfully and voice generated!","success"),pn(),await Fe(),await $();else{const s=await o.json();showNotification(s.error||"Failed to create submenu","error")}}catch(o){console.error("Error creating submenu:",o),showNotification("Failed to create submenu","error")}})});window.loadAutoAttendantConfig=Ka;window.loadAutoAttendantPrompts=cn;window.loadAutoAttendantMenuOptions=$;window.showAddMenuOptionModal=ei;window.closeAddMenuOptionModal=dn;window.editMenuOption=Le;window.closeEditMenuOptionModal=un;window.deleteMenuOption=De;window.navigateToMenu=ln;window.toggleMenuTreeView=ni;window.showCreateSubmenuModal=ti;window.closeCreateSubmenuModal=pn;window.updateDestinationFieldVisibility=gn;const Qe=window.loadVoicemailForExtension;window.loadVoicemailForExtension=async function(){Qe&&await Qe();const e=document.getElementById("vm-extension-select").value;if(!e){document.getElementById("voicemail-box-overview").style.display="none";return}document.getElementById("voicemail-box-overview").style.display="block";try{const t=await fetch(`${API_BASE}/api/voicemail-boxes/${e}`,{headers:pbxAuthHeaders()});if(t.ok){const n=await t.json();document.getElementById("vm-total-messages").textContent=n.total_messages||0,document.getElementById("vm-unread-messages").textContent=n.unread_messages||0,document.getElementById("vm-has-greeting").textContent=n.has_custom_greeting?"Yes":"No"}else console.error("Failed to load mailbox details:",t.status,t.statusText),document.getElementById("vm-total-messages").textContent="0",document.getElementById("vm-unread-messages").textContent="0",document.getElementById("vm-has-greeting").textContent="Unknown"}catch(t){console.error("Error loading mailbox details:",t),document.getElementById("vm-total-messages").textContent="0",document.getElementById("vm-unread-messages").textContent="0",document.getElementById("vm-has-greeting").textContent="Unknown"}};window.exportVoicemailBox=async function(){const e=document.getElementById("vm-extension-select").value;if(!e){showNotification("Please select an extension first","error");return}if(confirm(`Export all voicemails for extension ${e}?

This will download a ZIP file containing all voicemail messages and a manifest file.`))try{const t=await fetch(`${API_BASE}/api/voicemail-boxes/${e}/export`,{method:"POST",headers:pbxAuthHeaders()});if(!t.ok){const c=await t.json();throw new Error(c.error||"Failed to export voicemail box")}const n=await t.blob(),o=t.headers.get("Content-Disposition");let s=`voicemail_${e}_export.zip`;if(o){const c=o.match(/filename="?(.+)"?/i);c&&(s=c[1])}const a=window.URL.createObjectURL(n),i=document.createElement("a");i.href=a,i.download=s,document.body.appendChild(i),i.click(),window.URL.revokeObjectURL(a),document.body.removeChild(i),showNotification("Voicemail box exported successfully","success")}catch(t){console.error("Error exporting voicemail box:",t),showNotification(`Failed to export voicemail box: ${t.message}`,"error")}};window.clearVoicemailBox=async function(){const e=document.getElementById("vm-extension-select").value;if(!e){showNotification("Please select an extension first","error");return}if(confirm(`⚠️ WARNING: Clear ALL voicemail messages for extension ${e}?

This action cannot be undone!

Consider exporting the voicemail box first.`)&&confirm("Are you absolutely sure? All voicemail messages will be permanently deleted."))try{const t=await fetch(`${API_BASE}/api/voicemail-boxes/${e}/clear`,{method:"DELETE",headers:pbxAuthHeaders()});if(t.ok){const n=await t.json();showNotification(n.message||"Voicemail box cleared successfully","success"),loadVoicemailForExtension()}else{const n=await t.json();showNotification(n.error||"Failed to clear voicemail box","error")}}catch(t){console.error("Error clearing voicemail box:",t),showNotification("Failed to clear voicemail box","error")}};window.uploadCustomGreeting=async function(){const e=document.getElementById("vm-extension-select").value;if(!e){showNotification("Please select an extension first","error");return}const t=document.createElement("input");t.type="file",t.accept="audio/wav",t.onchange=async n=>{const o=n.target.files[0];if(o){if(!o.name.endsWith(".wav")){showNotification("Please upload a WAV file","error");return}try{const s=localStorage.getItem("pbx_token"),a=s?{Authorization:"Bearer "+s}:{},i=await fetch(`${API_BASE}/api/voicemail-boxes/${e}/greeting`,{method:"PUT",headers:a,body:await o.arrayBuffer()});if(i.ok)showNotification("Custom greeting uploaded successfully","success"),loadVoicemailForExtension();else{const c=await i.json();showNotification(c.error||"Failed to upload greeting","error")}}catch(s){console.error("Error uploading greeting:",s),showNotification("Failed to upload greeting","error")}}},t.click()};window.downloadCustomGreeting=async function(){const e=document.getElementById("vm-extension-select").value;if(!e){showNotification("Please select an extension first","error");return}try{const t=await fetch(`${API_BASE}/api/voicemail-boxes/${e}/greeting`,{headers:pbxAuthHeaders()});if(!t.ok)throw new Error("No custom greeting found");const n=await t.blob(),o=window.URL.createObjectURL(n),s=document.createElement("a");s.href=o,s.download=`greeting_${e}.wav`,document.body.appendChild(s),s.click(),window.URL.revokeObjectURL(o),document.body.removeChild(s),showNotification("Greeting downloaded","success")}catch(t){console.error("Error downloading greeting:",t),showNotification("No custom greeting found for this extension","error")}};window.deleteCustomGreeting=async function(){const e=document.getElementById("vm-extension-select").value;if(!e){showNotification("Please select an extension first","error");return}if(confirm(`Delete custom greeting for extension ${e}?

The default system greeting will be used.`))try{const t=await fetch(`${API_BASE}/api/voicemail-boxes/${e}/greeting`,{method:"DELETE",headers:pbxAuthHeaders()});if(t.ok)showNotification("Custom greeting deleted successfully","success"),loadVoicemailForExtension();else{const n=await t.json();showNotification(n.error??"Failed to delete greeting","error")}}catch(t){console.error("Error deleting greeting:",t),showNotification("Failed to delete greeting","error")}};window.loadAllVoicemailBoxes=async function(){try{const e=await fetch(`${API_BASE}/api/voicemail-boxes`,{headers:pbxAuthHeaders()});if(!e.ok)throw new Error("Failed to load voicemail boxes");const t=await e.json();return debugLog("All voicemail boxes:",t.voicemail_boxes),t.voicemail_boxes}catch(e){return console.error("Error loading voicemail boxes:",e),[]}};function w(e){return String(e).replace(/[&<>"'\/]/g,function(t){switch(t){case"&":return"&amp;";case"<":return"&lt;";case">":return"&gt;";case'"':return"&quot;";case"'":return"&#39;";case"/":return"&#x2F;";default:return t}})}const W={jitsi:"Jitsi Meet",matrix:"Matrix",espocrm:"EspoCRM"};function v(e,t="info",n=5e3){let o=document.getElementById("quick-setup-notifications");o||(o=document.createElement("div"),o.id="quick-setup-notifications",o.style.cssText=`
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            max-width: 400px;
        `,document.body.appendChild(o));const s=document.createElement("div"),a={success:"#4CAF50",error:"#f44336",warning:"#ff9800",info:"#2196F3"};if(s.style.cssText=`
        background-color: ${a[t]||a.info};
        color: white;
        padding: 16px 20px;
        margin-bottom: 10px;
        border-radius: 4px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        display: flex;
        align-items: center;
        justify-content: space-between;
        animation: slideIn 0.3s ease-out;
    `,s.innerHTML=`
        <div style="flex: 1; padding-right: 10px;">${w(e)}</div>
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
    `,!document.getElementById("notification-animations")){const i=document.createElement("style");i.id="notification-animations",i.textContent=`
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
        `,document.head.appendChild(i)}o.appendChild(s),n>0&&setTimeout(()=>{s.style.animation="slideIn 0.3s ease-out reverse",setTimeout(()=>s.remove(),300)},n)}async function si(){de(),ue(),me(),await B()}async function B(){try{const n=(await(await fetch("/api/config",{headers:pbxAuthHeaders()})).json()).integrations||{},o=n.jitsi?.enabled||!1,s=document.getElementById("quick-jitsi-enabled"),a=document.getElementById("jitsi-status-badge");s&&(s.checked=o),a&&(a.style.display=o?"inline-block":"none",a.style.backgroundColor="#4CAF50",a.style.color="white",a.textContent="● Enabled");const i=n.matrix?.enabled||!1,c=document.getElementById("quick-matrix-enabled"),d=document.getElementById("matrix-status-badge");c&&(c.checked=i),d&&(d.style.display=i?"inline-block":"none",d.style.backgroundColor="#9C27B0",d.style.color="white",d.textContent="● Enabled");const g=n.espocrm?.enabled||!1,y=document.getElementById("quick-espocrm-enabled"),p=document.getElementById("espocrm-status-badge");y&&(y.checked=g),p&&(p.style.display=g?"inline-block":"none",p.style.backgroundColor="#2196F3",p.style.color="white",p.textContent="● Enabled")}catch(e){console.error("Failed to load integration status:",e)}}async function ai(e){document.getElementById(`quick-${e}-enabled`).checked?await yn(e):await bn(e)}async function yn(e){const n={jitsi:{enabled:!0,server_url:"https://localhost",auto_create_rooms:!0,app_id:"",app_secret:""},matrix:{enabled:!0,homeserver_url:"https://localhost:8008",bot_username:"",bot_password:"${MATRIX_BOT_PASSWORD}",notification_room:"",voicemail_room:"",missed_call_notifications:!0},espocrm:{enabled:!0,api_url:"https://localhost/api/v1",api_key:"${ESPOCRM_API_KEY}",auto_create_contacts:!0,auto_log_calls:!0,screen_pop:!0}}[e];if(!n){v(`Unknown integration: ${e}`,"error");return}try{if((await fetch("/api/config/section",{method:"PUT",headers:pbxAuthHeaders(),body:JSON.stringify({section:"integrations",data:{[e]:n}})})).ok){const s=document.getElementById(`quick-${e}-enabled`);s&&(s.checked=!0),B();const a=`✅ ${W[e]} enabled with default settings! The integration is now active.`;e==="matrix"?v(`${a} Note: You need to set MATRIX_BOT_PASSWORD in your .env file for Matrix to work.`,"warning",8e3):e==="espocrm"?v(`${a} Note: You need to set ESPOCRM_API_KEY and api_url in the configuration tab.`,"warning",8e3):v(a,"success"),e==="jitsi"?de():e==="matrix"?ue():e==="espocrm"&&me()}else{v(`Failed to enable ${W[e]}`,"error");const s=document.getElementById(`quick-${e}-enabled`);s&&(s.checked=!1)}}catch(o){v(`Error enabling integration: ${o.message}`,"error");const s=document.getElementById(`quick-${e}-enabled`);s&&(s.checked=!1)}}async function bn(e){try{const o=(await(await fetch("/api/config",{headers:pbxAuthHeaders()})).json()).integrations?.[e]??{};if(o.enabled=!1,(await fetch("/api/config/section",{method:"PUT",headers:pbxAuthHeaders(),body:JSON.stringify({section:"integrations",data:{[e]:o}})})).ok)B(),v(`${W[e]} has been disabled.`,"info"),e==="jitsi"?de():e==="matrix"?ue():e==="espocrm"&&me();else{v(`Failed to disable ${W[e]}`,"error");const a=document.getElementById(`quick-${e}-enabled`);a&&(a.checked=!0)}}catch(t){v(`Error disabling integration: ${t.message}`,"error");const n=document.getElementById(`quick-${e}-enabled`);n&&(n.checked=!0)}}async function de(){try{const e=await fetch("/api/config",{headers:pbxAuthHeaders()});if(!e.ok){window.suppressErrorNotifications?debugLog("Config endpoint returned error:",e.status,"(feature may not be available or authentication required)"):console.error("Failed to load Jitsi config:",e.status);return}const n=(await e.json()).integrations?.jitsi??{};document.getElementById("jitsi-enabled").checked=n.enabled??!1,document.getElementById("jitsi-server-url").value=n.server_url??"https://localhost",document.getElementById("jitsi-auto-create-rooms").checked=n.auto_create_rooms!==!1,document.getElementById("jitsi-app-id").value=n.app_id??"",document.getElementById("jitsi-app-secret").value=n.app_secret??"",Ne()}catch(e){window.suppressErrorNotifications?debugLog("Failed to load Jitsi config (expected if not authenticated):",e.message):console.error("Failed to load Jitsi config:",e)}}function Ne(){const e=document.getElementById("jitsi-enabled").checked;document.getElementById("jitsi-settings").style.display=e?"block":"none"}document.getElementById("jitsi-enabled")?.addEventListener("change",Ne);document.getElementById("jitsi-config-form")?.addEventListener("submit",async function(e){e.preventDefault();const t={enabled:document.getElementById("jitsi-enabled").checked,server_url:document.getElementById("jitsi-server-url").value,auto_create_rooms:document.getElementById("jitsi-auto-create-rooms").checked,app_id:document.getElementById("jitsi-app-id").value,app_secret:document.getElementById("jitsi-app-secret").value};try{(await fetch("/api/config/section",{method:"PUT",headers:pbxAuthHeaders(),body:JSON.stringify({section:"integrations",data:{jitsi:t}})})).ok?(_("Configuration saved successfully!","success"),B()):_("Failed to save configuration","error")}catch(n){_(`Error: ${w(n.message)}`,"error")}});async function ii(){const e=document.getElementById("jitsi-server-url").value;_(`Testing connection to ${w(e)}...`,"info");try{const t=`${e}/external_api.js`,n=await fetch(t,{mode:"no-cors"}),o=`${e}/test-pbx-${Date.now()}`;_(`✅ Connection successful!<br>Test meeting URL: <a href="${w(o)}" target="_blank">${w(o)}</a>`,"success")}catch(t){_(`⚠️ Could not verify connection. Server may still be accessible.<br>Error: ${w(t.message)}`,"warning")}}function _(e,t){const o=["success","error","warning","info"].includes(t)?t:"info",s=document.getElementById("jitsi-status");s.innerHTML=`<div class="alert alert-${o}">${e}</div>`}async function ue(){try{const e=await fetch("/api/config",{headers:pbxAuthHeaders()});if(!e.ok){window.suppressErrorNotifications?debugLog("Config endpoint returned error:",e.status,"(feature may not be available or authentication required)"):console.error("Failed to load Matrix config:",e.status);return}const n=(await e.json()).integrations?.matrix??{};document.getElementById("matrix-enabled").checked=n.enabled??!1,document.getElementById("matrix-homeserver-url").value=n.homeserver_url??"https://localhost:8008",document.getElementById("matrix-bot-username").value=n.bot_username??"",document.getElementById("matrix-bot-password").value=n.bot_password??"",document.getElementById("matrix-notification-room").value=n.notification_room??"",document.getElementById("matrix-voicemail-room").value=n.voicemail_room??"",document.getElementById("matrix-missed-call-notifications").checked=n.missed_call_notifications!==!1,He()}catch(e){window.suppressErrorNotifications?debugLog("Failed to load Matrix config (expected if not authenticated):",e.message):console.error("Failed to load Matrix config:",e)}}function He(){const e=document.getElementById("matrix-enabled").checked;document.getElementById("matrix-settings").style.display=e?"block":"none"}document.getElementById("matrix-enabled")?.addEventListener("change",He);document.getElementById("matrix-config-form")?.addEventListener("submit",async function(e){e.preventDefault();const t={enabled:document.getElementById("matrix-enabled").checked,homeserver_url:document.getElementById("matrix-homeserver-url").value,bot_username:document.getElementById("matrix-bot-username").value,bot_password:document.getElementById("matrix-bot-password").value,notification_room:document.getElementById("matrix-notification-room").value,voicemail_room:document.getElementById("matrix-voicemail-room").value,missed_call_notifications:document.getElementById("matrix-missed-call-notifications").checked};try{(await fetch("/api/config/section",{method:"PUT",headers:pbxAuthHeaders(),body:JSON.stringify({section:"integrations",data:{matrix:t}})})).ok?(C("Configuration saved successfully!","success"),B()):C("Failed to save configuration","error")}catch(n){C(`Error: ${w(n.message)}`,"error")}});async function ri(){const e=document.getElementById("matrix-homeserver-url").value,t=document.getElementById("matrix-bot-username").value,n=document.getElementById("matrix-bot-password").value;if(!t||!n){C("Please enter bot username and password","error");return}C("Testing Matrix connection...","info");try{const o=`${e}/_matrix/client/versions`,s=await fetch(o);if(!s.ok)throw new Error("Homeserver not accessible");const i=(await s.json()).versions?.join(", ")??"Unknown";C(`✅ Homeserver is accessible!<br>Supported versions: ${w(i)}<br><small>Note: Full authentication test requires server-side validation</small>`,"success")}catch(o){C(`❌ Connection failed: ${w(o.message)}`,"error")}}function C(e,t){const o=["success","error","warning","info"].includes(t)?t:"info",s=document.getElementById("matrix-status");s.innerHTML=`<div class="alert alert-${o}">${e}</div>`}async function me(){try{const e=await fetch("/api/config",{headers:pbxAuthHeaders()});if(!e.ok){window.suppressErrorNotifications?debugLog("Config endpoint returned error:",e.status,"(feature may not be available or authentication required)"):console.error("Failed to load EspoCRM config:",e.status);return}const n=(await e.json()).integrations?.espocrm??{};document.getElementById("espocrm-enabled").checked=n.enabled??!1,document.getElementById("espocrm-api-url").value=n.api_url??"https://localhost/api/v1",document.getElementById("espocrm-api-key").value=n.api_key??"",document.getElementById("espocrm-auto-create-contacts").checked=n.auto_create_contacts!==!1,document.getElementById("espocrm-auto-log-calls").checked=n.auto_log_calls!==!1,document.getElementById("espocrm-screen-pop").checked=n.screen_pop!==!1,je()}catch(e){window.suppressErrorNotifications?debugLog("Failed to load EspoCRM config (expected if not authenticated):",e.message):console.error("Failed to load EspoCRM config:",e)}}function je(){const e=document.getElementById("espocrm-enabled").checked;document.getElementById("espocrm-settings").style.display=e?"block":"none"}document.getElementById("espocrm-enabled")?.addEventListener("change",je);document.getElementById("espocrm-config-form")?.addEventListener("submit",async function(e){e.preventDefault();const t={enabled:document.getElementById("espocrm-enabled").checked,api_url:document.getElementById("espocrm-api-url").value,api_key:document.getElementById("espocrm-api-key").value,auto_create_contacts:document.getElementById("espocrm-auto-create-contacts").checked,auto_log_calls:document.getElementById("espocrm-auto-log-calls").checked,screen_pop:document.getElementById("espocrm-screen-pop").checked};try{(await fetch("/api/config/section",{method:"PUT",headers:pbxAuthHeaders(),body:JSON.stringify({section:"integrations",data:{espocrm:t}})})).ok?(T("Configuration saved successfully!","success"),B()):T("Failed to save configuration","error")}catch(n){T(`Error: ${w(n.message)}`,"error")}});async function ci(){const e=document.getElementById("espocrm-api-url").value,t=document.getElementById("espocrm-api-key").value;if(!e||!t){T("Please enter API URL and API Key","error");return}T("Testing EspoCRM connection...","info");try{const n=`${e}/App/user`,o=await fetch(n,{headers:{"X-Api-Key":t,"Content-Type":"application/json"}});if(o.ok){const s=await o.json();T(`✅ Connection successful!<br>Connected as: ${w(s.userName??"Unknown")}<br>EspoCRM is ready for integration.`,"success")}else throw new Error(`API returned status ${o.status}`)}catch(n){T(`❌ Connection failed: ${w(n.message)}<br>Check API URL and API Key.`,"error")}}function T(e,t){const o=["success","error","warning","info"].includes(t)?t:"info",s=document.getElementById("espocrm-status");s.innerHTML=`<div class="alert alert-${o}">${e}</div>`}async function li(){const e=document.getElementById("jitsi-instant-room").value??"";try{const t=await fetch("/api/integrations/jitsi/instant",{method:"POST",headers:pbxAuthHeaders(),body:JSON.stringify({room_name:e,extension:"admin"})});if(!t.ok){const o=await t.json();throw new Error(o.error||"Failed to create meeting")}const n=await t.json();hn(n.meeting_url),v("Meeting created successfully!","success")}catch(t){v(`Failed to create meeting: ${t.message}`,"error")}}async function di(){const e=document.getElementById("jitsi-schedule-subject").value,t=document.getElementById("jitsi-schedule-duration").value;if(!e){v("Please enter a meeting subject","warning");return}try{const n=await fetch("/api/integrations/jitsi/meetings",{method:"POST",headers:pbxAuthHeaders(),body:JSON.stringify({subject:e,duration:parseInt(t),moderator_name:"Admin"})});if(!n.ok){const s=await n.json();throw new Error(s.error||"Failed to schedule meeting")}const o=await n.json();hn(o.meeting_url),v("Meeting scheduled successfully!","success")}catch(n){v(`Failed to schedule meeting: ${n.message}`,"error")}}function hn(e){const t=document.getElementById("jitsi-meeting-result"),n=document.getElementById("jitsi-meeting-url");n.value=e,t.style.display="block"}async function ui(){const e=document.getElementById("jitsi-meeting-url"),t=e.value;try{navigator.clipboard&&navigator.clipboard.writeText?(await navigator.clipboard.writeText(t),v("Meeting URL copied to clipboard!","success",3e3)):(e.select(),document.execCommand("copy"),v("Meeting URL copied to clipboard!","success",3e3))}catch{e.select(),document.execCommand("copy"),v("Meeting URL copied to clipboard!","success",3e3)}}function mi(){const e=document.getElementById("jitsi-meeting-url").value;e&&window.open(e,"_blank")}document.addEventListener("DOMContentLoaded",function(){const e=document.getElementById("matrix-room-select");e&&e.addEventListener("change",function(){const t=document.getElementById("matrix-custom-room");this.value==="custom"?t.style.display="block":t.style.display="none"})});async function gi(){const e=document.getElementById("matrix-room-select").value,t=document.getElementById("matrix-custom-room-id").value,n=document.getElementById("matrix-message-text").value;if(!n){v("Please enter a message","warning");return}let o=null;if(e==="custom"){if(o=t,!o){v("Please enter a custom room ID","warning");return}}else(e==="notification"||e==="voicemail")&&(o=null);try{const s=await fetch("/api/integrations/matrix/messages",{method:"POST",headers:pbxAuthHeaders(),body:JSON.stringify({room_id:o,message:n,msg_type:"m.text"})});if(!s.ok){const i=await s.json();throw new Error(i.error||"Failed to send message")}const a=await s.json();z("✅ Message sent successfully!","success"),document.getElementById("matrix-message-text").value=""}catch(s){z(`❌ Failed to send message: ${s.message}`,"error")}}async function pi(){try{const e=await fetch("/api/integrations/matrix/notifications",{method:"POST",headers:pbxAuthHeaders(),body:JSON.stringify({message:`🧪 Test notification from PBX Admin Panel - ${new Date().toLocaleString()}`})});if(!e.ok){const t=await e.json();throw new Error(t.error||"Failed to send notification")}z("✅ Test notification sent successfully!","success")}catch(e){z(`❌ Failed to send notification: ${e.message}`,"error")}}async function fi(){const e=document.getElementById("matrix-new-room-name").value,t=document.getElementById("matrix-new-room-topic").value;if(!e){v("Please enter a room name","warning");return}try{const n=await fetch("/api/integrations/matrix/rooms",{method:"POST",headers:pbxAuthHeaders(),body:JSON.stringify({name:e,topic:t})});if(!n.ok){const s=await n.json();throw new Error(s.error||"Failed to create room")}const o=await n.json();yi(o.room_id),v("Room created successfully!","success"),document.getElementById("matrix-new-room-name").value="",document.getElementById("matrix-new-room-topic").value=""}catch(n){v(`Failed to create room: ${n.message}`,"error")}}function z(e,t){const n=document.getElementById("matrix-message-result"),o=document.getElementById("matrix-message-result-text");o.textContent=e,n.style.display="block",n.querySelector(".info-box").style.backgroundColor=t==="success"?"#e8f5e9":"#ffebee",setTimeout(()=>{n.style.display="none"},5e3)}function yi(e){const t=document.getElementById("matrix-room-result"),n=document.getElementById("matrix-new-room-id");n.textContent=e,t.style.display="block"}async function bi(){const e=document.getElementById("espocrm-search-type").value,t=document.getElementById("espocrm-search-term").value;if(!t){v("Please enter a search term","warning");return}try{const o=await fetch(`/api/integrations/espocrm/contacts/search?${e==="phone"?"phone":e==="email"?"email":"name"}=${encodeURIComponent(t)}`,{method:"GET",headers:pbxAuthHeaders()});if(!o.ok){const a=await o.json();throw new Error(a.error||"Failed to search contact")}const s=await o.json();hi(s)}catch(n){v(`Failed to search contact: ${n.message}`,"error")}}function hi(e){const t=document.getElementById("espocrm-search-results"),n=document.getElementById("espocrm-contact-details");if(!e.success||!e.contact){n.innerHTML='<div class="info-box" style="background-color: #fff3e0;">No contact found</div>',t.style.display="block";return}const o=e.contact;let s='<div class="info-box" style="background-color: #e8f5e9;">';s+="<h4>✅ Contact Found</h4>",s+='<table style="width: 100%; margin-top: 10px;">',o.name&&(s+=`<tr><td><strong>Name:</strong></td><td>${w(o.name)}</td></tr>`),o.email&&(s+=`<tr><td><strong>Email:</strong></td><td>${w(o.email)}</td></tr>`),o.phone&&(s+=`<tr><td><strong>Phone:</strong></td><td>${w(o.phone)}</td></tr>`),o.company&&(s+=`<tr><td><strong>Company:</strong></td><td>${w(o.company)}</td></tr>`),o.title&&(s+=`<tr><td><strong>Title:</strong></td><td>${w(o.title)}</td></tr>`),o.id&&(s+=`<tr><td><strong>CRM ID:</strong></td><td>${w(o.id)}</td></tr>`),s+="</table></div>",n.innerHTML=s,t.style.display="block"}async function vi(){const e=document.getElementById("espocrm-new-firstname").value,t=document.getElementById("espocrm-new-lastname").value,n=document.getElementById("espocrm-new-phone").value,o=document.getElementById("espocrm-new-email").value,s=document.getElementById("espocrm-new-company").value,a=document.getElementById("espocrm-new-title").value;if(!e||!t){v("Please enter first and last name","warning");return}if(!n&&!o){v("Please enter at least phone or email","warning");return}try{const i=await fetch("/api/integrations/espocrm/contacts",{method:"POST",headers:pbxAuthHeaders(),body:JSON.stringify({name:`${e} ${t}`,phone:n,email:o,company:s,title:a})});if(!i.ok){const d=await i.json();throw new Error(d.error||"Failed to create contact")}const c=await i.json();Ke(`✅ Contact created successfully! CRM ID: ${c.contact?.id??"unknown"}`),document.getElementById("espocrm-new-firstname").value="",document.getElementById("espocrm-new-lastname").value="",document.getElementById("espocrm-new-phone").value="",document.getElementById("espocrm-new-email").value="",document.getElementById("espocrm-new-company").value="",document.getElementById("espocrm-new-title").value=""}catch(i){Ke(`❌ Failed to create contact: ${i.message}`)}}function Ke(e){const t=document.getElementById("espocrm-create-result"),n=document.getElementById("espocrm-create-result-text");n.textContent=e,t.style.display="block",setTimeout(()=>{t.style.display="none"},5e3)}window.loadOpenSourceIntegrations=si;window.loadJitsiConfig=de;window.loadMatrixConfig=ue;window.loadEspoCRMConfig=me;window.toggleJitsiSettings=Ne;window.testJitsiConnection=ii;window.toggleMatrixSettings=He;window.testMatrixConnection=ri;window.toggleEspoCRMSettings=je;window.testEspoCRMConnection=ci;window.quickToggleIntegration=ai;window.quickSetupIntegration=yn;window.disableIntegration=bn;window.createInstantJitsiMeeting=li;window.scheduleJitsiMeeting=di;window.copyJitsiMeetingUrl=ui;window.openJitsiMeeting=mi;window.sendMatrixMessage=gi;window.sendMatrixTestNotification=pi;window.createMatrixRoom=fi;window.searchEspoCRMContact=bi;window.createEspoCRMContact=vi;setTimeout(function(){if(!window.currentUser&&!document.querySelector(".tab-content.active")){console.warn("Page may not have loaded correctly. Checking for common issues...");var e=document.querySelector(".sidebar");if(e){var t=window.getComputedStyle(e);if(t.width==="auto"||t.width==="0px"){console.error("CSS may not be loaded correctly. Try clearing your browser cache:"),console.error("  - Press Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)"),console.error("  - See BROWSER_CACHE_FIX.md for detailed instructions");var n=document.createElement("div");n.className="page-load-alert",n.innerHTML='<strong class="page-load-alert-title">⚠️ Page Loading Issue</strong><p>The admin panel may not be displaying correctly due to cached files.</p><p class="page-load-alert-action">Press <code>Ctrl+Shift+R</code> (or <code>Cmd+Shift+R</code> on Mac) to reload without cache</p>';var o=document.createElement("button");o.className="page-load-alert-dismiss",o.textContent="Dismiss",o.addEventListener("click",function(){n.remove()}),n.appendChild(o),document.body.appendChild(n)}}}else console.log("Page loaded successfully at",new Date().toISOString())},3e3);(function(){var e=document.getElementById("sidebar-toggle"),t=document.querySelector(".sidebar"),n=document.getElementById("sidebar-overlay");if(!e||!t||!n)return;function o(){t.classList.add("open"),n.classList.add("active"),e.classList.add("active"),e.setAttribute("aria-expanded","true")}function s(){t.classList.remove("open"),n.classList.remove("active"),e.classList.remove("active"),e.setAttribute("aria-expanded","false")}e.addEventListener("click",function(){t.classList.contains("open")?s():o()}),n.addEventListener("click",s),t.addEventListener("click",function(a){a.target.closest(".tab-button")&&s()}),document.addEventListener("keydown",function(a){a.key==="Escape"&&t.classList.contains("open")&&s()})})();
