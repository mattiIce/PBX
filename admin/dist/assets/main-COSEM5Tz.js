(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const r of document.querySelectorAll('link[rel="modulepreload"]'))o(r);new MutationObserver(r=>{for(const s of r)if(s.type==="childList")for(const a of s.addedNodes)a.tagName==="LINK"&&a.rel==="modulepreload"&&o(a)}).observe(document,{childList:!0,subtree:!0});function n(r){const s={};return r.integrity&&(s.integrity=r.integrity),r.referrerPolicy&&(s.referrerPolicy=r.referrerPolicy),r.crossOrigin==="use-credentials"?s.credentials="include":r.crossOrigin==="anonymous"?s.credentials="omit":s.credentials="same-origin",s}function o(r){if(r.ep)return;r.ep=!0;const s=n(r);fetch(r.href,s)}})();const Qe="80",Ze="443",G="9000",K=3e4;function u(){const e=document.querySelector('meta[name="api-base-url"]');if(e&&e.content)return e.content;if(window.location.port===G||window.location.port===""||window.location.port===Qe||window.location.port===Ze)return window.location.origin;const t=window.location.protocol,n=window.location.hostname||"localhost";return`${t}//${n}:${G}`}function d(){const e=localStorage.getItem("pbx_token"),t={"Content-Type":"application/json"};return e&&(t.Authorization=`Bearer ${e}`),t}async function g(e,t={},n=K){if(t.signal)throw new Error("fetchWithTimeout does not support custom abort signals. Use the timeout parameter instead.");const o=new AbortController,r=setTimeout(()=>o.abort(),n);try{return await fetch(e,{...t,signal:o.signal})}catch(s){throw s instanceof Error&&s.name==="AbortError"?new Error("Request timed out"):s}finally{clearTimeout(r)}}class Ge{_state;_listeners;constructor(t){this._state={...t},this._listeners=new Map}get(t){return this._state[t]}set(t,n){this._state[t]=n;const o=this._listeners.get(t)??[];for(const r of o)r(n)}subscribe(t,n){return this._listeners.has(t)||this._listeners.set(t,[]),this._listeners.get(t).push(n),()=>{const r=this._listeners.get(t);if(!r)return;const s=r.indexOf(n);s>-1&&r.splice(s,1)}}getState(){return{...this._state}}}const _=new Ge({currentUser:null,currentExtensions:[],currentTab:"dashboard",isAuthenticated:!1,autoRefreshInterval:null});function c(e){const t=document.createElement("div");return t.textContent=e,t.innerHTML}async function Ye(e){try{await navigator.clipboard.writeText(e),i("License data copied to clipboard!","success")}catch(t){console.error("Error copying to clipboard:",t),i("Failed to copy to clipboard","error")}}function X(e){if(!e)return"";try{return new Date(e).toLocaleString()}catch{return e}}function ee(e,t){return e.length<=t?e:e.substring(0,t)+"..."}function te(e){const n=new Date().getTime()-new Date(e).getTime(),o=Math.floor(n/(1e3*60*60)),r=Math.floor(n%(1e3*60*60)/(1e3*60));return o>0?`${o}h ${r}m`:`${r}m`}function ne(e){return{registered:'<span class="badge" style="background: #10b981;">&#x2705; Registered</span>',unregistered:'<span class="badge" style="background: #6b7280;">&#x26AA; Unregistered</span>',failed:'<span class="badge" style="background: #ef4444;">&#x274C; Failed</span>',disabled:'<span class="badge" style="background: #9ca3af;">&#x23F8;&#xFE0F; Disabled</span>',degraded:'<span class="badge" style="background: #f59e0b;">&#x26A0;&#xFE0F; Degraded</span>'}[e]||e}function oe(e){return{healthy:'<span class="badge" style="background: #10b981;">&#x1F49A; Healthy</span>',warning:'<span class="badge" style="background: #f59e0b;">&#x26A0;&#xFE0F; Warning</span>',critical:'<span class="badge" style="background: #f59e0b;">&#x1F534; Critical</span>',down:'<span class="badge" style="background: #ef4444;">&#x1F480; Down</span>'}[e]||e}function se(e){return{1:'<span class="badge" style="background: #ef4444;">1 - Highest</span>',2:'<span class="badge" style="background: #f97316;">2 - High</span>',3:'<span class="badge" style="background: #eab308;">3 - Medium</span>',4:'<span class="badge" style="background: #3b82f6;">4 - Low</span>',5:'<span class="badge" style="background: #6b7280;">5 - Lowest</span>'}[e]||`<span class="badge">${e}</span>`}function re(e){return e>=4.3?"quality-excellent":e>=4?"quality-good":e>=3.6?"quality-fair":e>=3.1?"quality-poor":"quality-bad"}function ae(e){const t=[];if(e.days_of_week){const n=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],o=e.days_of_week.map(r=>n[r]).join(", ");t.push(o)}return e.start_time&&e.end_time&&t.push(`${e.start_time}-${e.end_time}`),e.holidays===!0?t.push("Holidays"):e.holidays===!1&&t.push("Non-holidays"),t.length>0?t.join(" | "):"Always"}function ie(e){const t=JSON.stringify(e,null,2),n=new Blob([t],{type:"application/json"}),o=URL.createObjectURL(n),r=document.createElement("a");r.href=o,r.download=`license_${e.issued_to.replace(/[^a-zA-Z0-9]/g,"_").toLowerCase()}_${new Date().toISOString().split("T")[0]}.json`,document.body.appendChild(r),r.click(),document.body.removeChild(r),URL.revokeObjectURL(o)}window.formatDate=X;window.truncate=ee;window.getDuration=te;window.getStatusBadge=ne;window.getHealthBadge=oe;window.getPriorityBadge=se;window.getQualityClass=re;window.getScheduleDescription=ae;window.downloadLicense=ie;const Ke={displayTime:8e3};let ce=!1;function Xe(e){ce=e}function i(e,t="info"){if(ce&&t==="error"){debugLog(`[${t.toUpperCase()}] ${e}`);return}const n=document.createElement("div");n.className=`notification notification-${t}`,n.style.cssText=`
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
    `;const o=t==="success"?"✓":t==="error"?"✗":t==="warning"?"⚠":"ℹ";n.innerHTML=`<strong>${o}</strong> ${c(e)}`,document.body.appendChild(n),setTimeout(()=>{n.style.animation="slideOutRight 0.3s ease-in",setTimeout(()=>n.remove(),300)},5e3)}function E(e,t=""){const n=`error-${Date.now()}`,o=e.message||e.toString(),r=e.stack||"",s=document.createElement("div");s.id=n,s.className="error-notification",s.style.cssText=`
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
    `;let a=`
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
            <strong style="font-size: 16px;">JavaScript Error</strong>
            <button id="close-${n}"
                    style="background: none; border: none; color: white; font-size: 20px; cursor: pointer; padding: 0; margin-left: 10px;">
                ×
            </button>
        </div>
    `;t&&(a+=`<div style="margin-bottom: 5px;"><strong>Context:</strong> ${c(t)}</div>`),a+=`<div style="margin-bottom: 5px;"><strong>Message:</strong> ${c(o)}</div>`,r&&(a+=`
            <details style="margin-top: 10px; cursor: pointer;">
                <summary style="font-weight: bold; margin-bottom: 5px;">Stack Trace (click to expand)</summary>
                <pre style="background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 11px; margin: 5px 0 0 0;">${c(r)}</pre>
            </details>
        `),a+=`
        <div style="margin-top: 10px; font-size: 11px; opacity: 0.9;">
            Tip: Press F12 to open browser console for more details
        </div>
    `,s.innerHTML=a;const l=s.querySelector(`#close-${n}`);l&&l.addEventListener("click",()=>s.remove()),document.body.appendChild(s),setTimeout(()=>{document.getElementById(n)&&(s.style.animation="slideOut 0.3s ease-in",setTimeout(()=>s.remove(),300))},Ke.displayTime),console.error(`[${t||"Error"}]`,o),r&&console.error("Stack trace:",r)}const et=1e4;let k=null;function tt(){typeof window.loadEmergencyContacts=="function"&&window.loadEmergencyContacts(),typeof window.loadEmergencyHistory=="function"&&window.loadEmergencyHistory()}function nt(){typeof window.loadFraudAlerts=="function"&&window.loadFraudAlerts()}function ot(){typeof window.loadCallbackQueue=="function"&&window.loadCallbackQueue()}function st(e){k&&(clearInterval(k),k=null);const t={dashboard:()=>window.loadDashboard?.(),analytics:()=>window.loadAnalytics?.(),calls:()=>window.loadCalls?.(),qos:()=>window.loadQoSMetrics?.(),emergency:tt,"callback-queue":ot,extensions:()=>window.loadExtensions?.(),phones:()=>window.loadRegisteredPhones?.(),atas:()=>window.loadRegisteredATAs?.(),"hot-desking":()=>window.loadHotDeskSessions?.(),voicemail:()=>window.loadVoicemailTab?.(),"fraud-detection":nt};t[e]&&(k=setInterval(()=>{try{const n=t[e];typeof n=="function"?n():console.error(`Auto-refresh function for ${e} is not a function:`,n)}catch(n){console.error(`Error during auto-refresh of ${e}:`,n),n instanceof Error&&n.message?.includes("401")&&debugWarn("Authentication error during auto-refresh - user may need to re-login")}},et)),_.set("autoRefreshInterval",k)}function $(e){for(const s of document.querySelectorAll(".tab-content"))s.classList.remove("active");for(const s of document.querySelectorAll(".tab-button"))s.classList.remove("active");const t=document.getElementById(e);if(!t)console.error(`CRITICAL: Tab element with id '${e}' not found in DOM`),console.error("This may indicate a UI template issue or incorrect tab name"),console.error(`Current tab name: "${e}"`);else{t.classList.add("active");const s=document.querySelector(`[data-tab="${e}"]`);s?s.classList.add("active"):debugWarn(`Tab button for '${e}' not found`)}_.set("currentTab",e),st(e);const n={dashboard:window.loadDashboard,analytics:window.loadAnalytics,extensions:window.loadExtensions,phones:window.loadRegisteredPhones,atas:window.loadRegisteredATAs,provisioning:window.loadProvisioning,"auto-attendant":window.loadAutoAttendantConfig,voicemail:window.loadVoicemailTab,paging:window.loadPagingData,calls:window.loadCalls,config:window.loadConfig,"features-status":window.loadFeaturesStatus,"webrtc-phone":window.loadWebRTCPhoneConfig,"license-management":window.initLicenseManagement,qos:window.loadQoSMetrics,"find-me-follow-me":window.loadFMFMExtensions,"time-routing":window.loadTimeRoutingRules,webhooks:window.loadWebhooks,"hot-desking":window.loadHotDeskSessions,"recording-retention":window.loadRetentionPolicies,"jitsi-integration":window.loadJitsiConfig,"matrix-integration":window.loadMatrixConfig,"espocrm-integration":window.loadEspoCRMConfig,"click-to-dial":window.loadClickToDialTab,"fraud-detection":window.loadFraudDetectionData,"nomadic-e911":window.loadNomadicE911Data,"callback-queue":window.loadCallbackQueue,"mobile-push":window.loadMobilePushConfig,"recording-announcements":window.loadRecordingAnnouncements,"speech-analytics":window.loadSpeechAnalyticsConfigs,compliance:window.loadComplianceData,"crm-integrations":window.loadCRMActivityLog,"opensource-integrations":window.loadOpenSourceIntegrations},o={emergency:[window.loadEmergencyContacts,window.loadEmergencyHistory],codecs:[window.loadCodecStatus,window.loadDTMFConfig],"sip-trunks":[window.loadSIPTrunks,window.loadTrunkHealth],"least-cost-routing":[window.loadLCRRates,window.loadLCRStatistics]},r=n[e];if(r)r();else{const s=o[e];if(s)for(const a of s)a?.()}}function le(){const e=document.querySelectorAll(".tab-button");for(const n of e)n.addEventListener("click",()=>{const o=n.getAttribute("data-tab");o&&$(o)});const t=document.querySelector(".sidebar");t&&t.addEventListener("keydown",n=>{const o=n,r=o.target;if(!r.classList.contains("tab-button"))return;const s=r.closest(".sidebar-section");if(!s)return;const a=Array.from(s.querySelectorAll(".tab-button")),l=a.indexOf(r);let m=-1;o.key==="ArrowDown"?m=l<a.length-1?l+1:0:o.key==="ArrowUp"?m=l>0?l-1:a.length-1:o.key==="Home"?m=0:o.key==="End"&&(m=a.length-1),m>=0&&(o.preventDefault(),a[m]?.focus())}),document.addEventListener("keydown",n=>{if(n.key==="Escape"){const o=document.querySelector(".modal.active");o&&o.classList.remove("active")}})}async function H(e,t=5,n=1e3){if(!Array.isArray(e))throw new TypeError("promiseFunctions must be an array");const o=[];for(let r=0;r<e.length;r+=t){const a=e.slice(r,r+t).map(m=>typeof m=="function"?m():m),l=await Promise.allSettled(a);o.push(...l),r+t<e.length&&await new Promise(m=>setTimeout(m,n))}return o}async function j(){const e=document.getElementById("refresh-all-button");if(!e||e.disabled)return;const t=e.textContent,n=e.disabled;try{e.textContent="⏳ Refreshing All Tabs...",e.disabled=!0,window.suppressErrorNotifications=!0,debugLog("Refreshing all data for ALL tabs...");const o=[];window.loadDashboard&&o.push(()=>window.loadDashboard()),window.loadADStatus&&o.push(()=>window.loadADStatus()),window.loadAnalytics&&o.push(()=>window.loadAnalytics()),window.loadExtensions&&o.push(()=>window.loadExtensions());const s=(await H(o,5,1e3)).filter(a=>a.status==="rejected");s.length>0&&debugLog(`${s.length} refresh operation(s) failed (expected for unavailable features):`,s.map(a=>a.reason?.message??a.reason)),i("✅ All tabs refreshed successfully","success")}catch(o){const r=o instanceof Error?o.message:String(o);console.error("Error refreshing data:",o),i(`Failed to refresh: ${r}`,"error")}finally{window.suppressErrorNotifications=!1,e.textContent=t,e.disabled=n}}function rt(){const e=document.getElementById("refresh-all-button");e&&e.addEventListener("click",j)}window.executeBatched=H;window.refreshAllData=j;const at=6e4;async function de(){try{const e=u(),t=await g(`${e}/api/status`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}: ${t.statusText}`);const n=await t.json();document.getElementById("stat-extensions").textContent=String(n.registered_extensions??0),document.getElementById("stat-calls").textContent=String(n.active_calls??0),document.getElementById("stat-total-calls").textContent=String(n.total_calls??0),document.getElementById("stat-recordings").textContent=String(n.active_recordings??0);const o=document.getElementById("system-status");o&&(o.textContent=`System: ${n.running?"Running":"Stopped"}`,o.classList.remove("connected","disconnected"),o.classList.add("status-badge",n.running?"connected":"disconnected")),C()}catch(e){console.error("Error loading dashboard:",e);for(const n of["stat-extensions","stat-calls","stat-total-calls","stat-recordings"]){const o=document.getElementById(n);o&&(o.textContent="Error")}const t=e instanceof Error?e.message:String(e);i(`Failed to load dashboard: ${t}`,"error")}}function it(){de(),i("Dashboard refreshed","success")}async function C(){try{const e=u(),t=await g(`${e}/api/integrations/ad/status`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("ad-status-badge");o&&(o.textContent=n.enabled?"Enabled":"Disabled",o.className=`status-badge ${n.enabled?"enabled":"disabled"}`);const r=document.getElementById("ad-connection-status");r&&(r.textContent=n.connected?"✓ Connected":"✗ Not Connected",r.style.color=n.connected?"#10b981":"#ef4444");const s=m=>document.getElementById(m);s("ad-server")&&(s("ad-server").textContent=n.server??"Not configured"),s("ad-auto-provision")&&(s("ad-auto-provision").textContent=n.auto_provision?"Yes":"No"),s("ad-synced-users")&&(s("ad-synced-users").textContent=String(n.synced_users??0));const a=s("ad-error");a&&(a.textContent=n.error??"None",a.style.color=n.error?"#d32f2f":"#10b981");const l=s("ad-sync-btn");l&&(l.disabled=!(n.enabled&&n.connected))}catch(e){console.error("Error loading AD status:",e)}}function ct(){C(),i("AD status refreshed","success")}async function lt(){const e=document.getElementById("ad-sync-btn");if(!e)return;const t=e.textContent;e.disabled=!0,e.textContent="Syncing...";try{const n=u(),o=await g(`${n}/api/integrations/ad/sync`,{method:"POST",headers:d()},at);if(!o.ok){const s=await o.json().catch(()=>({error:`HTTP ${o.status}`}));throw new Error(s.error||`HTTP ${o.status}`)}const r=await o.json();r.success?(i(r.message||`Successfully synced ${r.synced_count} users`,"success"),C()):i(r.error||"Failed to sync users","error")}catch(n){console.error("Error syncing AD users:",n);const r=(n instanceof Error?n.message:String(n))==="Request timed out"?"AD sync timed out. Check server logs.":"Error syncing AD users";i(r,"error")}finally{e.textContent=t,e.disabled=!1}}window.loadDashboard=de;window.refreshDashboard=it;window.loadADStatus=C;window.refreshADStatus=ct;window.syncADUsers=lt;const dt=1e4;async function ue(){const e=document.getElementById("extensions-table-body");if(e){e.innerHTML='<tr><td colspan="7" class="loading">Loading extensions...</td></tr>';try{const t=u(),n=await g(`${t}/api/extensions`,{headers:d()},dt);if(!n.ok)throw new Error(`HTTP error! status: ${n.status}`);const o=await n.json();if(window.currentExtensions=o,o.length===0){e.innerHTML='<tr><td colspan="7" class="loading">No extensions found.</td></tr>';return}const r=s=>{let a="";return s.ad_synced&&(a+=' <span class="ad-badge" title="Synced from Active Directory">AD</span>'),s.is_admin&&(a+=' <span class="admin-badge" title="Admin Privileges">Admin</span>'),a};e.innerHTML=o.map(s=>`
            <tr>
                <td><strong>${c(s.number)}</strong>${r(s)}</td>
                <td>${c(s.name)}</td>
                <td>${s.email?c(s.email):"Not set"}</td>
                <td class="${s.registered?"status-online":"status-offline"}">
                    ${s.registered?"Online":"Offline"}
                </td>
                <td>${s.allow_external?"Yes":"No"}</td>
                <td>${s.voicemail_pin_hash?"Set":"Not Set"}</td>
                <td>
                    <button class="btn btn-primary" onclick="editExtension('${c(s.number)}')">Edit</button>
                    ${s.registered?`<button class="btn btn-secondary" onclick="rebootPhone('${c(s.number)}')">Reboot</button>`:""}
                    <button class="btn btn-danger" onclick="deleteExtension('${c(s.number)}')">Delete</button>
                </td>
            </tr>
        `).join("")}catch(t){console.error("Error loading extensions:",t);const o=(t instanceof Error?t.message:String(t))==="Request timed out"?"Request timed out. System may still be starting.":"Error loading extensions";e.innerHTML=`<tr><td colspan="7" class="loading">${o}</td></tr>`}}}function ut(){const e=document.getElementById("add-extension-modal");e&&e.classList.add("active");const t=document.getElementById("add-extension-form");t&&t.reset()}function mt(){const e=document.getElementById("add-extension-modal");e&&e.classList.remove("active")}function gt(e){const t=(window.currentExtensions??[]).find(r=>r.number===e);if(!t)return;const n=r=>document.getElementById(r);n("edit-ext-number")&&(n("edit-ext-number").value=t.number),n("edit-ext-name")&&(n("edit-ext-name").value=t.name),n("edit-ext-email")&&(n("edit-ext-email").value=t.email??""),n("edit-ext-allow-external")&&(n("edit-ext-allow-external").checked=!!t.allow_external),n("edit-ext-is-admin")&&(n("edit-ext-is-admin").checked=!!t.is_admin),n("edit-ext-password")&&(n("edit-ext-password").value="");const o=document.getElementById("edit-extension-modal");o&&o.classList.add("active")}function ft(){const e=document.getElementById("edit-extension-modal");e&&e.classList.remove("active")}async function pt(e){if(confirm(`Are you sure you want to delete extension ${e}?`))try{const t=u(),n=await fetch(`${t}/api/extensions/${e}`,{method:"DELETE",headers:d()});if(n.ok)i("Extension deleted successfully","success"),ue();else{const o=await n.json();i(o.error||"Failed to delete extension","error")}}catch(t){console.error("Error deleting extension:",t),i("Failed to delete extension","error")}}async function bt(e){if(confirm(`Reboot phone for extension ${e}?`))try{const t=u();(await fetch(`${t}/api/phones/reboot/${e}`,{method:"POST",headers:d()})).ok?i(`Reboot command sent to ${e}`,"success"):i("Failed to reboot phone","error")}catch(t){console.error("Error rebooting phone:",t),i("Failed to reboot phone","error")}}async function yt(){if(confirm("Reboot ALL registered phones?"))try{const e=u();(await fetch(`${e}/api/phones/reboot-all`,{method:"POST",headers:d()})).ok?i("Reboot command sent to all phones","success"):i("Failed to reboot phones","error")}catch(e){console.error("Error rebooting all phones:",e),i("Failed to reboot phones","error")}}window.loadExtensions=ue;window.showAddExtensionModal=ut;window.closeAddExtensionModal=mt;window.editExtension=gt;window.closeEditExtensionModal=ft;window.deleteExtension=pt;window.rebootPhone=bt;window.rebootAllPhones=yt;async function wt(){try{const e=u(),t=await fetch(`${e}/api/extensions`,{headers:d()});if(!t.ok)throw new Error(`HTTP error! status: ${t.status}`);const n=await t.json(),o=document.getElementById("vm-extension-select");if(!o)return;o.innerHTML='<option value="">Select Extension</option>';for(const r of n){const s=document.createElement("option");s.value=r.number,s.textContent=`${r.number} - ${r.name}`,o.appendChild(s)}}catch(e){console.error("Error loading voicemail tab:",e),i("Failed to load extensions","error")}}async function me(){const e=document.getElementById("vm-extension-select")?.value;if(!e){for(const n of["voicemail-pin-section","voicemail-messages-section","voicemail-box-overview"]){const o=document.getElementById(n);o&&(o.style.display="none")}return}for(const n of["voicemail-pin-section","voicemail-messages-section","voicemail-box-overview"]){const o=document.getElementById(n);o&&(o.style.display="block")}const t=document.getElementById("vm-current-extension");t&&(t.textContent=e);try{const n=u(),o=await fetch(`${n}/api/voicemail/${e}`,{headers:d()});if(!o.ok)throw new Error(`HTTP error! status: ${o.status}`);const r=await o.json();ht(r.messages,e)}catch(n){console.error("Error loading voicemail:",n),i("Failed to load voicemail messages","error")}}function ht(e,t){const n=document.getElementById("voicemail-cards-view");if(n){if(!e||e.length===0){n.innerHTML='<div class="info-box">No voicemail messages</div>';return}n.innerHTML=e.map(o=>{const r=new Date(o.timestamp).toLocaleString(),s=o.duration?`${o.duration}s`:"Unknown",a=!o.listened;return`
            <div class="voicemail-card ${a?"unread":""}">
                <div class="voicemail-card-header">
                    <div class="voicemail-from">${o.caller_id}</div>
                    <span class="voicemail-status-badge ${a?"unread":"read"}">
                        ${a?"NEW":"READ"}
                    </span>
                </div>
                <div class="voicemail-card-body">
                    <div>Time: ${r}</div>
                    <div>Duration: ${s}</div>
                </div>
                <div class="voicemail-card-actions">
                    <button class="btn btn-primary btn-sm" onclick="playVoicemail('${t}', '${o.id}')">Play</button>
                    <button class="btn btn-secondary btn-sm" onclick="downloadVoicemail('${t}', '${o.id}')">Download</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteVoicemail('${t}', '${o.id}')">Delete</button>
                </div>
            </div>
        `}).join("")}}async function Et(e,t){try{const o=`${u()}/api/voicemail/${e}/${t}/audio`,r=document.getElementById("voicemail-audio-player");r&&(r.src=o,r.play()),await ge(e,t)}catch(n){console.error("Error playing voicemail:",n),i("Failed to play voicemail","error")}}async function vt(e,t){const n=u();window.open(`${n}/api/voicemail/${e}/${t}/audio?download=1`,"_blank")}async function ge(e,t){try{const n=u();await fetch(`${n}/api/voicemail/${e}/${t}/read`,{method:"POST",headers:d()})}catch(n){console.error("Error marking voicemail read:",n)}}async function kt(e,t){if(confirm("Delete this voicemail message?"))try{const n=u();(await fetch(`${n}/api/voicemail/${e}/${t}`,{method:"DELETE",headers:d()})).ok?(i("Voicemail deleted","success"),me()):i("Failed to delete voicemail","error")}catch(n){console.error("Error deleting voicemail:",n),i("Failed to delete voicemail","error")}}window.loadVoicemailTab=wt;window.loadVoicemailForExtension=me;window.playVoicemail=Et;window.downloadVoicemail=vt;window.deleteVoicemail=kt;window.markVoicemailRead=ge;async function $t(){const e=document.getElementById("calls-list");if(e){e.innerHTML='<div class="loading">Loading calls...</div>';try{const t=u(),o=await(await g(`${t}/api/calls`,{headers:d()})).json();if(o.length===0){e.innerHTML='<div class="loading">No active calls</div>';return}e.innerHTML=o.map(r=>`
            <div class="call-item"><strong>Call:</strong> ${c(String(r))}</div>
        `).join("")}catch(t){console.error("Error loading calls:",t),e.innerHTML='<div class="loading">Error loading calls</div>'}}}async function St(){try{const e=u(),t=await g(`${e}/api/config/codecs`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("codec-status");o&&n.codecs&&(o.innerHTML=n.codecs.map(r=>`<div class="codec-item">${c(r.name)} - ${r.enabled?"Enabled":"Disabled"}</div>`).join(""))}catch(e){console.error("Error loading codec status:",e)}}async function xt(){try{const e=u(),t=await g(`${e}/api/config/dtmf`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("dtmf-mode");o&&(o.value=n.mode??"rfc2833");const r=document.getElementById("dtmf-threshold");r&&(r.value=String(n.threshold??-30))}catch(e){console.error("Error loading DTMF config:",e)}}async function At(){try{const e=u(),t={mode:document.getElementById("dtmf-mode")?.value??"rfc2833",threshold:parseInt(document.getElementById("dtmf-threshold")?.value??"-30")};(await fetch(`${e}/api/config/dtmf`,{method:"POST",headers:{...d(),"Content-Type":"application/json"},body:JSON.stringify(t)})).ok?i("DTMF configuration saved","success"):i("Failed to save DTMF configuration","error")}catch(e){console.error("Error saving DTMF config:",e),i("Failed to save DTMF configuration","error")}}window.loadCalls=$t;window.loadCodecStatus=St;window.loadDTMFConfig=xt;window.saveDTMFConfig=At;const Tt="Configuration saved successfully. Restart may be required for some changes.";async function It(){try{const e=u(),t=await g(`${e}/api/config/full`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json();if(n.features){const o=["call-recording","call-transfer","call-hold","conference","voicemail","call-parking","call-queues","presence","music-on-hold","auto-attendant"];for(const r of o){const s=document.getElementById(`feature-${r}`),a=r.replace(/-/g,"_");s&&(s.checked=n.features[a]??!1)}}if(n.voicemail){const o=r=>document.getElementById(r);o("vm-max-duration")&&(o("vm-max-duration").value=String(n.voicemail.max_duration??120)),o("vm-max-messages")&&(o("vm-max-messages").value=String(n.voicemail.max_messages??100))}}catch(e){console.error("Error loading config:",e),i("Failed to load configuration","error")}}async function _t(){try{const e=u(),t=await g(`${e}/api/config/features`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json();if(n.features)for(const[o,r]of Object.entries(n.features)){const s=document.getElementById(`feature-${o.replace(/_/g,"-")}`);s&&(s.checked=r)}}catch(e){console.error("Error loading features status:",e)}}async function Ct(e){try{const t=u(),n=document.getElementById(`${e}-form`);if(!n)return;const o=new FormData(n),r=Object.fromEntries(o.entries()),s=await fetch(`${t}/api/config/${e}`,{method:"POST",headers:{...d(),"Content-Type":"application/json"},body:JSON.stringify(r)});if(s.ok)i(Tt,"success");else{const a=await s.json();i(a.error||"Failed to save configuration","error")}}catch(t){console.error(`Error saving ${e} config:`,t),i("Failed to save configuration","error")}}async function fe(){try{const e=u(),t=await g(`${e}/api/ssl/status`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("ssl-status");if(o&&(o.textContent=n.enabled?"Enabled":"Disabled",o.className=`status-badge ${n.enabled?"enabled":"disabled"}`),n.certificate){const r=document.getElementById("ssl-cert-details");r&&(r.innerHTML=`
                    <div>Subject: ${n.certificate.subject||"N/A"}</div>
                    <div>Issuer: ${n.certificate.issuer||"N/A"}</div>
                    <div>Expires: ${n.certificate.expires||"N/A"}</div>
                `)}}catch(e){console.error("Error loading SSL status:",e)}}async function Bt(){try{const e=u();(await fetch(`${e}/api/ssl/generate`,{method:"POST",headers:d()})).ok?(i("SSL certificate generated successfully","success"),fe()):i("Failed to generate SSL certificate","error")}catch(e){console.error("Error generating SSL certificate:",e),i("Failed to generate SSL certificate","error")}}window.loadConfig=It;window.loadFeaturesStatus=_t;window.saveConfigSection=Ct;window.loadSSLStatus=fe;window.generateSSLCertificate=Bt;let pe=[];async function Pt(){await Promise.all([be(),N(),ye(),we(),he()])}async function be(){try{const e=u(),t=await fetch(`${e}/api/provisioning/vendors`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);pe=(await t.json()).vendors||[],Mt()}catch(e){console.error("Error loading vendors:",e)}}async function N(){try{const e=u(),t=await fetch(`${e}/api/provisioning/devices`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("provisioning-devices-body");if(!o)return;const r=n.devices||[];if(r.length===0){o.innerHTML='<tr><td colspan="6">No provisioned devices</td></tr>';return}o.innerHTML=r.map(s=>`
            <tr>
                <td>${c(s.mac_address||"")}</td>
                <td>${c(s.model||"")}</td>
                <td>${c(s.extension||"")}</td>
                <td>${c(s.label||"")}</td>
                <td><span class="status-badge ${s.status==="active"?"enabled":"disabled"}">${s.status||"unknown"}</span></td>
                <td><button class="btn btn-danger btn-sm" onclick="deleteDevice('${c(s.mac_address||"")}')">Delete</button></td>
            </tr>
        `).join("")}catch(e){console.error("Error loading devices:",e)}}async function ye(){try{const e=u(),t=await fetch(`${e}/api/provisioning/templates`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("provisioning-templates-list");if(!o)return;const r=n.templates||[];if(r.length===0){o.innerHTML='<div class="info-box">No templates configured</div>';return}o.innerHTML=r.map(s=>`
            <div class="template-item">
                <strong>${c(s.name)}</strong> - ${c(s.manufacturer||"Generic")}
                <button class="btn btn-sm btn-secondary" onclick="viewTemplate('${c(s.name)}')">View</button>
            </div>
        `).join("")}catch(e){console.error("Error loading templates:",e)}}async function we(){try{const e=u(),t=await fetch(`${e}/api/provisioning/settings`,{headers:d()});if(!t.ok)return;const n=await t.json(),o=r=>document.getElementById(r);o("provisioning-enabled")&&(o("provisioning-enabled").checked=n.enabled??!1),o("provisioning-url-format")&&(o("provisioning-url-format").value=n.url_format??"")}catch(e){console.error("Error loading provisioning settings:",e)}}async function he(){try{const e=u(),t=await fetch(`${e}/api/provisioning/phonebook-settings`,{headers:d()});if(!t.ok)return;const n=await t.json(),o=r=>document.getElementById(r);o("ldap-phonebook-enabled")&&(o("ldap-phonebook-enabled").checked=n.ldap_enabled??!1),o("remote-phonebook-enabled")&&(o("remote-phonebook-enabled").checked=n.remote_enabled??!1)}catch(e){console.error("Error loading phonebook settings:",e)}}async function Lt(e){if(confirm(`Delete device ${e}?`))try{const t=u();(await fetch(`${t}/api/provisioning/devices/${e}`,{method:"DELETE",headers:d()})).ok?(i("Device deleted","success"),N()):i("Failed to delete device","error")}catch(t){console.error("Error deleting device:",t),i("Failed to delete device","error")}}function Mt(){const e=document.getElementById("device-vendor");if(e){e.innerHTML='<option value="">Select Vendor</option>';for(const t of pe){const n=document.createElement("option");n.value=t,n.textContent=t,e.appendChild(n)}}}function Dt(e){i(`Viewing template: ${e}`,"info")}window.loadProvisioning=Pt;window.loadSupportedVendors=be;window.loadProvisioningDevices=N;window.loadProvisioningTemplates=ye;window.loadProvisioningSettings=we;window.loadPhonebookSettings=he;window.deleteDevice=Lt;window.viewTemplate=Dt;async function Rt(){const e=document.getElementById("registered-phones-body");if(e)try{const t=u(),n=await g(`${t}/api/registered-phones`,{headers:d()});if(!n.ok)throw new Error(`HTTP ${n.status}`);const r=(await n.json()).phones??[];if(r.length===0){e.innerHTML='<tr><td colspan="6">No registered phones</td></tr>';return}e.innerHTML=r.map(s=>`
            <tr>
                <td>${c(s.extension||"")}</td>
                <td>${c(s.name||"")}</td>
                <td>${c(s.ip_address||"")}</td>
                <td>${c(s.user_agent||"")}</td>
                <td>${c(s.registered_at||"")}</td>
                <td><span class="status-badge ${s.status==="online"?"connected":"disconnected"}">${s.status||"unknown"}</span></td>
            </tr>
        `).join("")}catch(t){console.error("Error loading registered phones:",t),e.innerHTML='<tr><td colspan="6">Error loading phones</td></tr>'}}async function Ht(){const e=document.getElementById("registered-atas-body");if(e)try{const t=u(),n=await g(`${t}/api/registered-phones/atas`,{headers:d()});if(!n.ok)throw new Error(`HTTP ${n.status}`);const r=(await n.json()).atas??[];if(r.length===0){e.innerHTML='<tr><td colspan="5">No registered ATAs</td></tr>';return}e.innerHTML=r.map(s=>`
            <tr>
                <td>${c(s.mac_address||"")}</td>
                <td>${c(s.model||"")}</td>
                <td>${c(s.ip_address||"")}</td>
                <td>${c(s.ports?.toString()||"")}</td>
                <td><span class="status-badge ${s.status==="online"?"connected":"disconnected"}">${s.status||"unknown"}</span></td>
            </tr>
        `).join("")}catch(t){console.error("Error loading ATAs:",t)}}window.loadRegisteredPhones=Rt;window.loadRegisteredATAs=Ht;async function jt(){try{const e=u(),t=await fetch(`${e}/api/security/fraud-alerts`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("fraud-alerts-list");if(!o)return;const r=n.alerts??[];if(r.length===0){o.innerHTML='<div class="info-box">No fraud alerts</div>';return}o.innerHTML=r.map(s=>`
            <div class="alert-item ${s.severity||"info"}">
                <strong>${c(s.type||"Alert")}</strong> - ${c(s.description||"")}
                <span class="alert-time">${new Date(s.timestamp).toLocaleString()}</span>
            </div>
        `).join("")}catch(e){console.error("Error loading fraud alerts:",e)}}async function F(){try{const e=u(),t=await fetch(`${e}/api/calls/callback-queue`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("callback-queue-body");if(!o)return;const r=n.queue??[];if(r.length===0){o.innerHTML='<tr><td colspan="5">No callbacks in queue</td></tr>';return}o.innerHTML=r.map(s=>`
            <tr>
                <td>${c(s.caller||"")}</td>
                <td>${c(s.number||"")}</td>
                <td>${c(s.status||"")}</td>
                <td>${new Date(s.requested_at).toLocaleString()}</td>
                <td>
                    <button class="btn btn-primary btn-sm" onclick="startCallback('${s.id}')">Start</button>
                    <button class="btn btn-danger btn-sm" onclick="cancelCallback('${s.id}')">Cancel</button>
                </td>
            </tr>
        `).join("")}catch(e){console.error("Error loading callback queue:",e)}}async function Nt(e){try{const t=u();(await fetch(`${t}/api/calls/callback/${e}/start`,{method:"POST",headers:d()})).ok&&(i("Callback initiated","success"),F())}catch(t){console.error("Error starting callback:",t),i("Failed to start callback","error")}}async function Ft(e){try{const t=u();(await fetch(`${t}/api/calls/callback/${e}/cancel`,{method:"POST",headers:d()})).ok&&(i("Callback cancelled","success"),F())}catch(t){console.error("Error cancelling callback:",t),i("Failed to cancel callback","error")}}async function qt(){try{const e=u(),t=await fetch(`${e}/api/integrations/mobile-push/devices`,{headers:d()});if(!t.ok)return;const n=await t.json(),o=document.getElementById("mobile-push-devices");if(!o)return;const r=n.devices??[];if(r.length===0){o.innerHTML='<div class="info-box">No registered devices</div>';return}o.innerHTML=r.map(s=>`
            <div class="device-item">
                <strong>${c(s.name||s.device_id)}</strong> - ${c(s.platform||"Unknown")}
                <span class="status-badge ${s.active?"enabled":"disabled"}">${s.active?"Active":"Inactive"}</span>
            </div>
        `).join("")}catch(e){console.error("Error loading mobile push devices:",e)}}async function Ot(){try{const e=u(),t=await fetch(`${e}/api/framework/speech-analytics/configs`,{headers:d()});if(!t.ok)return;const n=await t.json(),o=document.getElementById("speech-analytics-configs");o&&(o.innerHTML=JSON.stringify(n.configs??[],null,2))}catch(e){console.error("Error loading speech analytics:",e)}}window.loadFraudAlerts=jt;window.loadCallbackQueue=F;window.startCallback=Nt;window.cancelCallback=Ft;window.loadMobilePushDevices=qt;window.loadSpeechAnalyticsConfigs=Ot;async function Ee(){try{const e=u(),t=await fetch(`${e}/api/emergency/contacts`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("emergency-contacts-body");if(!o)return;const r=n.contacts??[];if(r.length===0){o.innerHTML='<tr><td colspan="5">No emergency contacts</td></tr>';return}o.innerHTML=r.map(s=>`
            <tr>
                <td>${c(s.name||"")}</td>
                <td>${c(s.phone||"")}</td>
                <td>${c(s.role||"")}</td>
                <td>${Ut(s.priority)}</td>
                <td><button class="btn btn-danger btn-sm" onclick="deleteEmergencyContact('${s.id}')">Delete</button></td>
            </tr>
        `).join("")}catch(e){console.error("Error loading emergency contacts:",e)}}function Ut(e){return`<span class="status-badge ${{high:"danger",medium:"warning",low:"info"}[e??""]??"info"}">${e??"normal"}</span>`}async function Wt(){try{const e=u(),t=await fetch(`${e}/api/emergency/history`,{headers:d()});if(!t.ok)return;const n=await t.json(),o=document.getElementById("emergency-history");if(!o)return;const r=n.history??[];o.innerHTML=r.length===0?'<div class="info-box">No emergency history</div>':r.map(s=>`
                <div class="history-item">
                    <strong>${new Date(s.timestamp).toLocaleString()}</strong> - ${c(s.description||"")}
                </div>
            `).join("")}catch(e){console.error("Error loading emergency history:",e)}}async function zt(e){if(confirm("Delete this emergency contact?"))try{const t=u();(await fetch(`${t}/api/emergency/contacts/${e}`,{method:"DELETE",headers:d()})).ok&&(i("Emergency contact deleted","success"),Ee())}catch(t){console.error("Error deleting contact:",t),i("Failed to delete contact","error")}}async function Jt(){try{const e=u(),t=await fetch(`${e}/api/emergency/e911/sites`,{headers:d()});if(!t.ok)return;const n=await t.json(),o=document.getElementById("e911-sites-list");if(!o)return;const r=n.sites??[];o.innerHTML=r.length===0?'<div class="info-box">No E911 sites configured</div>':r.map(s=>`
                <div class="site-item">
                    <strong>${c(s.name||"")}</strong> - ${c(s.address||"")}
                    <button class="btn btn-sm btn-secondary" onclick="editE911Site('${s.id}')">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteE911Site('${s.id}')">Delete</button>
                </div>
            `).join("")}catch(e){console.error("Error loading E911 sites:",e)}}async function Vt(){try{const e=u(),t=await fetch(`${e}/api/emergency/e911/locations`,{headers:d()});if(!t.ok)return;const n=await t.json(),o=document.getElementById("extension-locations-list");if(o){const r=n.locations??[];o.innerHTML=r.length===0?'<div class="info-box">No locations assigned</div>':r.map(s=>`
                    <div class="location-item">
                        Extension ${c(s.extension)} - ${c(s.site_name||"Unassigned")}
                    </div>
                `).join("")}}catch(e){console.error("Error loading extension locations:",e)}}window.loadEmergencyContacts=Ee;window.loadEmergencyHistory=Wt;window.deleteEmergencyContact=zt;window.loadE911Sites=Jt;window.loadExtensionLocations=Vt;async function ve(){try{const e=u(),t=await fetch(`${e}/api/phone-book`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("phone-book-body");if(!o)return;const r=n.entries??[];if(r.length===0){o.innerHTML='<tr><td colspan="5">No phone book entries</td></tr>';return}o.innerHTML=r.map(s=>`
            <tr>
                <td>${c(s.name||"")}</td>
                <td>${c(s.number||"")}</td>
                <td>${c(s.email||"")}</td>
                <td>${c(s.group||"General")}</td>
                <td>
                    <button class="btn btn-primary btn-sm" onclick="editPhoneBookEntry('${s.id}')">Edit</button>
                    <button class="btn btn-danger btn-sm" onclick="deletePhoneBookEntry('${s.id}')">Delete</button>
                </td>
            </tr>
        `).join("")}catch(e){console.error("Error loading phone book:",e)}}async function Qt(e){if(confirm("Delete this phone book entry?"))try{const t=u();(await fetch(`${t}/api/phone-book/${e}`,{method:"DELETE",headers:d()})).ok&&(i("Phone book entry deleted","success"),ve())}catch(t){console.error("Error deleting entry:",t),i("Failed to delete entry","error")}}window.loadPhoneBook=ve;window.deletePhoneBookEntry=Qt;async function Zt(){await Promise.all([B(),P(),ke()])}async function B(){try{const e=u(),t=await fetch(`${e}/api/paging/zones`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("paging-zones-body");if(!o)return;const r=n.zones??[];if(r.length===0){o.innerHTML='<tr><td colspan="4">No paging zones</td></tr>';return}o.innerHTML=r.map(s=>`
            <tr>
                <td>${c(s.name||"")}</td>
                <td>${c(s.number||"")}</td>
                <td>${s.devices?.length||0} devices</td>
                <td><button class="btn btn-danger btn-sm" onclick="deletePagingZone('${s.id}')">Delete</button></td>
            </tr>
        `).join("")}catch(e){console.error("Error loading paging zones:",e)}}async function P(){try{const e=u(),t=await fetch(`${e}/api/paging/devices`,{headers:d()});if(!t.ok)return;const n=await t.json(),o=document.getElementById("paging-devices-list");if(o){const r=n.devices??[];o.innerHTML=r.length===0?'<div class="info-box">No paging devices</div>':r.map(s=>`<div class="device-item">${c(s.name||s.id)}</div>`).join("")}}catch(e){console.error("Error loading paging devices:",e)}}async function ke(){try{const e=u(),t=await fetch(`${e}/api/paging/active`,{headers:d()});if(!t.ok)return;const n=await t.json(),o=document.getElementById("active-pages");if(o){const r=n.pages??[];o.innerHTML=r.length===0?'<div class="info-box">No active pages</div>':r.map(s=>`<div class="page-item">${c(s.zone)} - ${c(s.initiator)}</div>`).join("")}}catch(e){console.error("Error loading active pages:",e)}}async function Gt(e){if(confirm("Delete this paging zone?"))try{const t=u();(await fetch(`${t}/api/paging/zones/${e}`,{method:"DELETE",headers:d()})).ok&&(i("Paging zone deleted","success"),B())}catch(t){console.error("Error deleting paging zone:",t),i("Failed to delete zone","error")}}async function Yt(){const e=prompt("Zone Extension (e.g., 701):");if(!e)return;const t=prompt('Zone Name (e.g., "Warehouse"):');if(!t)return;const n=prompt("Description (optional):")??"",o=prompt("Device ID (optional):")??"",r={extension:e,name:t,description:n,device_id:o};try{const s=u(),l=await(await fetch(`${s}/api/paging/zones`,{method:"POST",headers:d(),body:JSON.stringify(r)})).json();l.success?(i(`Zone ${t} added successfully`,"success"),B()):i(l.message??"Failed to add zone","error")}catch(s){console.error("Error adding zone:",s),i("Error adding zone","error")}}async function Kt(){const e=prompt('Device ID (e.g., "dac-1"):');if(!e)return;const t=prompt('Device Name (e.g., "Main PA System"):');if(!t)return;const n=prompt('Device Type (e.g., "sip_gateway"):')??"sip_gateway",o=prompt('SIP Address (e.g., "paging@192.168.1.10:5060"):')??"",r={device_id:e,name:t,type:n,sip_address:o};try{const s=u(),l=await(await fetch(`${s}/api/paging/devices`,{method:"POST",headers:d(),body:JSON.stringify(r)})).json();l.success?(i(`Device ${t} added successfully`,"success"),P()):i(l.message??"Failed to add device","error")}catch(s){console.error("Error adding device:",s),i("Error adding device","error")}}async function Xt(e){if(confirm(`Delete paging device ${e}?`))try{const t=u(),o=await(await fetch(`${t}/api/paging/devices/${e}`,{method:"DELETE",headers:d()})).json();o.success?(i(`Device ${e} deleted`,"success"),P()):i(o.message??"Failed to delete device","error")}catch(t){console.error("Error deleting device:",t),i("Error deleting device","error")}}window.loadPagingData=Zt;window.loadPagingZones=B;window.loadPagingDevices=P;window.loadActivePages=ke;window.deletePagingZone=Gt;window.showAddZoneModal=Yt;window.showAddDeviceModal=Kt;window.deletePagingDevice=Xt;async function q(){try{const e=u(),t=await g(`${e}/api/license/status`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json();if(n.success&&n.license){const o=n.license,r=s=>document.getElementById(s);r("license-type")&&(r("license-type").textContent=o.type??"Unknown"),r("license-status")&&(r("license-status").textContent=o.valid?"Valid":"Invalid",r("license-status").className=`status-badge ${o.valid?"enabled":"disabled"}`),r("license-expires")&&(r("license-expires").textContent=o.expires_at??"Never"),r("license-extensions")&&(r("license-extensions").textContent=`${o.used_extensions??0} / ${o.max_extensions??"Unlimited"}`)}}catch(e){console.error("Error loading license status:",e)}}async function O(){try{const e=u(),t=await g(`${e}/api/license/features`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("license-features-list");if(!o)return;if(!n.licensing_enabled){o.innerHTML='<div class="info-box">Licensing disabled - all features available</div>';return}const r=n.features??{};o.innerHTML=Object.entries(r).map(([s,a])=>`<div class="feature-item">
                <span>${s.replace(/_/g," ")}</span>
                <span class="status-badge ${a?"enabled":"disabled"}">${a?"Available":"Locked"}</span>
            </div>`).join("")}catch(e){console.error("Error loading license features:",e)}}async function en(){const e=document.getElementById("license-key-input");if(!e||!e.value.trim()){i("Please enter a license key","error");return}try{const t=u(),o=await(await fetch(`${t}/api/license/install`,{method:"POST",headers:{...d(),"Content-Type":"application/json"},body:JSON.stringify({license_key:e.value.trim()})})).json();o.success?(i("License installed successfully","success"),e.value="",q(),O()):i(o.error??"Failed to install license","error")}catch(t){console.error("Error installing license:",t),i("Failed to install license","error")}}function tn(){q(),O()}window.loadLicenseStatus=q;window.loadLicenseFeatures=O;window.installLicense=en;window.initLicenseManagement=tn;let w={};function nn(){return typeof Chart<"u"}async function on(){try{const e=u(),t=await fetch(`${e}/api/analytics/overview`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json();sn(n),nn()&&(n.daily_trends&&rn(n.daily_trends),n.hourly_distribution&&an(n.hourly_distribution),n.disposition&&cn(n.disposition))}catch(e){console.error("Error loading analytics:",e)}}function sn(e){const t=a=>document.getElementById(a),n=t("analytics-total-calls"),o=t("analytics-avg-duration"),r=t("analytics-answer-rate"),s=t("analytics-active-now");n&&(n.textContent=String(e.total_calls??0)),o&&(o.textContent=`${e.avg_duration??0}s`),r&&(r.textContent=`${e.answer_rate??0}%`),s&&(s.textContent=String(e.active_calls??0))}function rn(e){const t=document.getElementById("daily-trends-chart")?.getContext("2d");t&&(w.dailyTrends&&w.dailyTrends.destroy(),w.dailyTrends=new Chart(t,{type:"line",data:{labels:e.labels||[],datasets:[{label:"Calls",data:e.data||[],borderColor:"#3b82f6",tension:.3,fill:!1}]},options:{responsive:!0,maintainAspectRatio:!1}}))}function an(e){const t=document.getElementById("hourly-distribution-chart")?.getContext("2d");t&&(w.hourlyDist&&w.hourlyDist.destroy(),w.hourlyDist=new Chart(t,{type:"bar",data:{labels:e.labels||[],datasets:[{label:"Calls by Hour",data:e.data||[],backgroundColor:"#60a5fa"}]},options:{responsive:!0,maintainAspectRatio:!1}}))}function cn(e){const t=document.getElementById("disposition-chart")?.getContext("2d");t&&(w.disposition&&w.disposition.destroy(),w.disposition=new Chart(t,{type:"doughnut",data:{labels:e.labels||[],datasets:[{data:e.data||[],backgroundColor:["#10b981","#ef4444","#f59e0b","#6b7280"]}]},options:{responsive:!0,maintainAspectRatio:!1}}))}async function ln(){try{const e=u(),t=await fetch(`${e}/api/qos/metrics`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}`);const n=await t.json(),o=document.getElementById("qos-mos"),r=document.getElementById("qos-jitter"),s=document.getElementById("qos-packet-loss"),a=document.getElementById("qos-latency");o&&(o.textContent=n.avg_mos?.toFixed(2)??"N/A"),r&&(r.textContent=`${n.avg_jitter??0}ms`),s&&(s.textContent=`${n.avg_packet_loss??0}%`),a&&(a.textContent=`${n.avg_latency??0}ms`)}catch(e){console.error("Error loading QoS metrics:",e)}}window.loadAnalytics=on;window.loadQoSMetrics=ln;function dn(e){return{registered:'<span class="badge" style="background: #10b981;">Registered</span>',unregistered:'<span class="badge" style="background: #6b7280;">Unregistered</span>',failed:'<span class="badge" style="background: #ef4444;">Failed</span>',disabled:'<span class="badge" style="background: #9ca3af;">Disabled</span>',degraded:'<span class="badge" style="background: #f59e0b;">Degraded</span>'}[e]||e}function $e(e){return{healthy:'<span class="badge" style="background: #10b981;">Healthy</span>',warning:'<span class="badge" style="background: #f59e0b;">Warning</span>',critical:'<span class="badge" style="background: #f59e0b;">Critical</span>',down:'<span class="badge" style="background: #ef4444;">Down</span>'}[e]||e}async function L(){try{const e=u(),t=await g(`${e}/api/sip-trunks`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}: ${t.statusText}`);const n=await t.json();if(n.trunks){const o=document.getElementById("trunk-total");o&&(o.textContent=String(n.count||0));const r=n.trunks.filter(f=>f.health_status==="healthy").length,s=n.trunks.filter(f=>f.status==="registered").length,a=n.trunks.reduce((f,y)=>f+y.channels_available,0),l=document.getElementById("trunk-healthy");l&&(l.textContent=String(r));const m=document.getElementById("trunk-registered");m&&(m.textContent=String(s));const p=document.getElementById("trunk-total-channels");p&&(p.textContent=String(a));const b=document.getElementById("trunks-list");if(!b)return;n.trunks.length===0?b.innerHTML='<tr><td colspan="8" style="text-align: center;">No SIP trunks configured</td></tr>':b.innerHTML=n.trunks.map(f=>{const y=dn(f.status),v=$e(f.health_status),h=(f.success_rate*100).toFixed(1);return`
                        <tr>
                            <td><strong>${c(f.name)}</strong><br/><small>${c(f.trunk_id)}</small></td>
                            <td>${c(f.host)}:${f.port}</td>
                            <td>${y}</td>
                            <td>${v}</td>
                            <td>${f.priority}</td>
                            <td>${f.channels_in_use}/${f.max_channels}</td>
                            <td>
                                <div style="display: flex; align-items: center; gap: 5px;">
                                    <div style="flex: 1; background: #e5e7eb; border-radius: 4px; height: 20px; overflow: hidden;">
                                        <div style="background: ${Number(h)>=95?"#10b981":Number(h)>=80?"#f59e0b":"#ef4444"}; height: 100%; width: ${h}%;"></div>
                                    </div>
                                    <span>${h}%</span>
                                </div>
                                <small>${f.successful_calls}/${f.total_calls} calls</small>
                            </td>
                            <td>
                                <button class="btn-small btn-primary" onclick="testTrunk('${c(f.trunk_id)}')">Test</button>
                                <button class="btn-small btn-danger" onclick="deleteTrunk('${c(f.trunk_id)}', '${c(f.name)}')">Delete</button>
                            </td>
                        </tr>
                    `}).join("")}}catch(e){console.error("Error loading SIP trunks:",e);const t=e instanceof Error?e.message:String(e);i(`Error loading SIP trunks: ${t}`,"error")}}async function Se(){try{const e=u(),t=await g(`${e}/api/sip-trunks/health`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}: ${t.statusText}`);const n=await t.json();if(n.health){const o=document.getElementById("trunk-health-section"),r=document.getElementById("trunk-health-container");if(!o||!r)return;o.style.display="block",r.innerHTML=n.health.map(s=>`
                <div class="config-section" style="margin-bottom: 15px;">
                    <h4>${c(s.name)} (${c(s.trunk_id)})</h4>
                    <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));">
                        <div class="stat-card">
                            <div class="stat-value">${$e(s.health_status)}</div>
                            <div class="stat-label">Health Status</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${(s.success_rate*100).toFixed(1)}%</div>
                            <div class="stat-label">Success Rate</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${s.consecutive_failures}</div>
                            <div class="stat-label">Consecutive Failures</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${s.average_setup_time.toFixed(2)}s</div>
                            <div class="stat-label">Avg Setup Time</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${s.failover_count}</div>
                            <div class="stat-label">Failover Count</div>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <p><strong>Total Calls:</strong> ${s.total_calls} (${s.successful_calls} successful, ${s.failed_calls} failed)</p>
                        ${s.last_successful_call?`<p><strong>Last Success:</strong> ${new Date(s.last_successful_call).toLocaleString()}</p>`:""}
                        ${s.last_failed_call?`<p><strong>Last Failure:</strong> ${new Date(s.last_failed_call).toLocaleString()}</p>`:""}
                        ${s.last_health_check?`<p><strong>Last Check:</strong> ${new Date(s.last_health_check).toLocaleString()}</p>`:""}
                    </div>
                </div>
            `).join(""),i("Health metrics loaded","success")}}catch(e){console.error("Error loading trunk health:",e);const t=e instanceof Error?e.message:String(e);i(`Error loading trunk health: ${t}`,"error")}}function un(){const e=document.getElementById("add-trunk-modal");e&&(e.style.display="block")}function xe(){const e=document.getElementById("add-trunk-modal");e&&(e.style.display="none");const t=document.getElementById("add-trunk-form");t&&t.reset()}async function mn(e){e.preventDefault();const t=Array.from(document.querySelectorAll('input[name="trunk-codecs"]:checked')).map(o=>o.value),n={trunk_id:document.getElementById("trunk-id").value,name:document.getElementById("trunk-name").value,host:document.getElementById("trunk-host").value,port:parseInt(document.getElementById("trunk-port").value),username:document.getElementById("trunk-username").value,password:document.getElementById("trunk-password").value,priority:parseInt(document.getElementById("trunk-priority").value),max_channels:parseInt(document.getElementById("trunk-channels").value),codec_preferences:t.length>0?t:["G.711","G.729"]};try{const o=u(),s=await(await g(`${o}/api/sip-trunks`,{method:"POST",headers:d(),body:JSON.stringify(n)})).json();s.success?(i(`Trunk ${n.name} added successfully`,"success"),xe(),L()):i(s.error||"Error adding trunk","error")}catch(o){console.error("Error adding trunk:",o),i("Error adding trunk","error")}}async function gn(e,t){if(confirm(`Are you sure you want to delete trunk "${t}"?`))try{const n=u(),r=await(await g(`${n}/api/sip-trunks/${e}`,{method:"DELETE",headers:d()})).json();r.success?(i(`Trunk ${t} deleted`,"success"),L()):i(r.error||"Error deleting trunk","error")}catch(n){console.error("Error deleting trunk:",n),i("Error deleting trunk","error")}}async function fn(e){i("Testing trunk...","info");try{const t=u(),o=await(await g(`${t}/api/sip-trunks/test`,{method:"POST",headers:d(),body:JSON.stringify({trunk_id:e})})).json();if(o.success){const r=o.health_status??"unknown";i(`Trunk test complete: ${r}`,r==="healthy"?"success":"warning"),L(),Se()}else i(o.error||"Error testing trunk","error")}catch(t){console.error("Error testing trunk:",t),i("Error testing trunk","error")}}async function M(){try{const e=u(),t=await g(`${e}/api/lcr/rates`,{headers:d()});if(!t.ok){window.suppressErrorNotifications?debugLog("LCR rates endpoint returned error:",t.status,"(feature may not be enabled)"):(console.error("Error loading LCR rates:",t.status),i("Error loading LCR rates","error"));return}const n=await t.json();if(n.rates!==void 0){const o=document.getElementById("lcr-total-rates");o&&(o.textContent=String(n.count||0));const r=document.getElementById("lcr-time-rates");r&&(r.textContent=String(n.time_rates?n.time_rates.length:0));const s=document.getElementById("lcr-rates-list");s&&(n.rates.length===0?s.innerHTML='<tr><td colspan="7" style="text-align: center;">No rates configured</td></tr>':s.innerHTML=n.rates.map(l=>`
                        <tr>
                            <td><strong>${c(l.trunk_id)}</strong></td>
                            <td><code>${c(l.pattern)}</code></td>
                            <td>${c(l.description)}</td>
                            <td>$${l.rate_per_minute.toFixed(4)}</td>
                            <td>$${l.connection_fee.toFixed(4)}</td>
                            <td>${l.minimum_seconds}s</td>
                            <td>${l.billing_increment}s</td>
                        </tr>
                    `).join(""));const a=document.getElementById("lcr-time-rates-list");a&&(!n.time_rates||n.time_rates.length===0?a.innerHTML='<tr><td colspan="5" style="text-align: center;">No time-based rates configured</td></tr>':a.innerHTML=n.time_rates.map(l=>{const m=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],p=l.days_of_week.map(b=>m[b]).join(", ");return`
                            <tr>
                                <td><strong>${c(l.name)}</strong></td>
                                <td>${l.start_time}</td>
                                <td>${l.end_time}</td>
                                <td>${p}</td>
                                <td>${l.rate_multiplier}x</td>
                            </tr>
                        `}).join(""))}Ae()}catch(e){if(window.suppressErrorNotifications){const t=e instanceof Error?e.message:String(e);debugLog("Error loading LCR rates (expected if LCR not enabled):",t)}else console.error("Error loading LCR rates:",e),i("Error loading LCR rates","error")}}async function Ae(){try{const e=u(),t=await g(`${e}/api/lcr/statistics`,{headers:d()});if(!t.ok){window.suppressErrorNotifications?debugLog("LCR statistics endpoint returned error:",t.status,"(feature may not be enabled)"):console.error("Error loading LCR statistics:",t.status);return}const n=await t.json(),o=document.getElementById("lcr-total-routes");o&&(o.textContent=String(n.total_routes||0));const r=document.getElementById("lcr-status");r&&(r.innerHTML=n.enabled?'<span class="badge" style="background: #10b981;">Enabled</span>':'<span class="badge" style="background: #6b7280;">Disabled</span>');const s=document.getElementById("lcr-decisions-list");s&&(!n.recent_decisions||n.recent_decisions.length===0?s.innerHTML='<tr><td colspan="5" style="text-align: center;">No recent decisions</td></tr>':s.innerHTML=n.recent_decisions.map(a=>`
                        <tr>
                            <td>${new Date(a.timestamp).toLocaleString()}</td>
                            <td>${c(a.number)}</td>
                            <td><strong>${c(a.selected_trunk)}</strong></td>
                            <td>$${a.estimated_cost.toFixed(4)}</td>
                            <td>${a.alternatives}</td>
                        </tr>
                    `).join(""))}catch(e){if(window.suppressErrorNotifications){const t=e instanceof Error?e.message:String(e);debugLog("Error loading LCR statistics (expected if LCR not enabled):",t)}else console.error("Error loading LCR statistics:",e)}}function pn(){document.body.insertAdjacentHTML("beforeend",`
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
    `)}function Te(){const e=document.getElementById("lcr-rate-modal");e&&e.remove()}async function bn(e){e.preventDefault();const t={trunk_id:document.getElementById("lcr-trunk-id").value,pattern:document.getElementById("lcr-pattern").value,description:document.getElementById("lcr-description").value,rate_per_minute:parseFloat(document.getElementById("lcr-rate-per-minute").value),connection_fee:parseFloat(document.getElementById("lcr-connection-fee").value),minimum_seconds:parseInt(document.getElementById("lcr-minimum-seconds").value),billing_increment:parseInt(document.getElementById("lcr-billing-increment").value)};try{const n=u(),r=await(await g(`${n}/api/lcr/rate`,{method:"POST",headers:d(),body:JSON.stringify(t)})).json();r.success?(i("LCR rate added successfully","success"),Te(),M()):i(r.error||"Error adding LCR rate","error")}catch(n){console.error("Error adding LCR rate:",n),i("Error adding LCR rate","error")}}function yn(){document.body.insertAdjacentHTML("beforeend",`
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
    `)}function Ie(){const e=document.getElementById("lcr-time-rate-modal");e&&e.remove()}async function wn(e){e.preventDefault();const t=Array.from(document.querySelectorAll('input[name="time-days"]:checked')).map(o=>parseInt(o.value)),n={name:document.getElementById("time-rate-name").value,start_hour:parseInt(document.getElementById("time-rate-start-hour").value),start_minute:parseInt(document.getElementById("time-rate-start-minute").value),end_hour:parseInt(document.getElementById("time-rate-end-hour").value),end_minute:parseInt(document.getElementById("time-rate-end-minute").value),days:t,multiplier:parseFloat(document.getElementById("time-rate-multiplier").value)};try{const o=u(),s=await(await g(`${o}/api/lcr/time-rate`,{method:"POST",headers:d(),body:JSON.stringify(n)})).json();s.success?(i("Time-based rate added successfully","success"),Ie(),M()):i(s.error||"Error adding time-based rate","error")}catch(o){console.error("Error adding time-based rate:",o),i("Error adding time-based rate","error")}}async function hn(){if(confirm("Are you sure you want to clear all LCR rates? This cannot be undone."))try{const e=u(),n=await(await g(`${e}/api/lcr/clear-rates`,{method:"POST",headers:d()})).json();n.success?(i("All LCR rates cleared","success"),M()):i(n.error||"Error clearing LCR rates","error")}catch(e){console.error("Error clearing LCR rates:",e),i("Error clearing LCR rates","error")}}window.loadSIPTrunks=L;window.loadTrunkHealth=Se;window.showAddTrunkModal=un;window.closeAddTrunkModal=xe;window.addSIPTrunk=mn;window.deleteTrunk=gn;window.testTrunk=fn;window.loadLCRRates=M;window.loadLCRStatistics=Ae;window.showAddLCRRateModal=pn;window.closeLCRRateModal=Te;window.addLCRRate=bn;window.showAddTimeRateModal=yn;window.closeTimeRateModal=Ie;window.addTimeRate=wn;window.clearLCRRates=hn;let En=0;async function U(){try{const e=u(),t=await g(`${e}/api/fmfm/extensions`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}: ${t.statusText}`);const n=await t.json();if(n.extensions){const o=document.getElementById("fmfm-total-extensions");o&&(o.textContent=String(n.count||0));const r=n.extensions.filter(f=>f.mode==="sequential").length,s=n.extensions.filter(f=>f.mode==="simultaneous").length,a=n.extensions.filter(f=>f.enabled!==!1).length,l=document.getElementById("fmfm-sequential");l&&(l.textContent=String(r));const m=document.getElementById("fmfm-simultaneous");m&&(m.textContent=String(s));const p=document.getElementById("fmfm-active-count");p&&(p.textContent=String(a));const b=document.getElementById("fmfm-list");if(!b)return;n.extensions.length===0?b.innerHTML='<tr><td colspan="6" style="text-align: center;">No Find Me/Follow Me configurations</td></tr>':b.innerHTML=n.extensions.map(f=>{const y=f.enabled!==!1,v=f.mode==="sequential"?'<span class="badge" style="background: #3b82f6;">Sequential</span>':'<span class="badge" style="background: #10b981;">Simultaneous</span>',h=y?'<span class="badge" style="background: #10b981;">Active</span>':'<span class="badge" style="background: #6b7280;">Disabled</span>',A=f.destinations||[],Z=A.map(D=>`${c(D.number)}${D.ring_time?` (${D.ring_time}s)`:""}`).join(", "),Ve=f.updated_at?new Date(f.updated_at).toLocaleString():"N/A";return`
                        <tr>
                            <td><strong>${c(f.extension)}</strong></td>
                            <td>${v}</td>
                            <td>
                                <div style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${c(Z)}">
                                    ${A.length} destination(s): ${c(Z)||"None"}
                                </div>
                            </td>
                            <td>${h}</td>
                            <td><small>${Ve}</small></td>
                            <td>
                                <button class="btn-small btn-primary" data-config='${c(JSON.stringify(f))}' onclick="editFMFMConfig(JSON.parse(this.getAttribute('data-config')))">Edit</button>
                                <button class="btn-small btn-danger" onclick="deleteFMFMConfig('${c(f.extension)}')">Delete</button>
                            </td>
                        </tr>
                    `}).join("")}}catch(e){console.error("Error loading FMFM extensions:",e),i("Error loading FMFM configurations","error")}}function _e(){const e=document.getElementById("add-fmfm-modal");e&&(e.style.display="block");const t=document.getElementById("fmfm-extension");t&&(t.value="",t.readOnly=!1);const n=document.getElementById("fmfm-mode");n&&(n.value="sequential");const o=document.getElementById("fmfm-enabled");o&&(o.checked=!0);const r=document.getElementById("fmfm-no-answer");r&&(r.value="");const s=document.getElementById("fmfm-destinations-list");s&&(s.innerHTML=""),I()}function Ce(){const e=document.getElementById("add-fmfm-modal");e&&(e.style.display="none");const t=document.getElementById("add-fmfm-form");t&&t.reset()}function I(){const e=document.getElementById("fmfm-destinations-list");if(!e)return;const t=`fmfm-dest-${En++}`,n=document.createElement("div");n.id=t,n.style.cssText="display: flex; gap: 10px; margin-bottom: 10px; align-items: center;",n.innerHTML=`
        <input type="text" class="fmfm-dest-number" placeholder="Phone number or extension" required style="flex: 2;">
        <input type="number" class="fmfm-dest-ringtime" placeholder="Ring time (s)" value="20" min="5" max="120" style="flex: 1;">
        <button type="button" class="btn-small btn-danger" onclick="document.getElementById('${t}').remove()">Remove</button>
    `,e.appendChild(n)}async function vn(e){e.preventDefault();const t=document.getElementById("fmfm-extension").value,n=document.getElementById("fmfm-mode").value,o=document.getElementById("fmfm-enabled").checked,r=document.getElementById("fmfm-no-answer").value,s=Array.from(document.querySelectorAll(".fmfm-dest-number")),a=Array.from(document.querySelectorAll(".fmfm-dest-ringtime")),l=s.map((p,b)=>({number:p.value,ring_time:parseInt(a[b]?.value??"20")||20})).filter(p=>p.number);if(l.length===0){i("At least one destination is required","error");return}const m={extension:t,mode:n,enabled:o,destinations:l};r&&(m.no_answer_destination=r);try{const p=u(),f=await(await g(`${p}/api/fmfm/config`,{method:"POST",headers:d(),body:JSON.stringify(m)})).json();f.success?(i(`FMFM configured for extension ${t}`,"success"),Ce(),U()):i(f.error||"Error configuring FMFM","error")}catch(p){console.error("Error saving FMFM config:",p),i("Error saving FMFM configuration","error")}}function kn(e){_e();const t=document.getElementById("fmfm-extension");t&&(t.value=e.extension,t.readOnly=!0);const n=document.getElementById("fmfm-mode");n&&(n.value=e.mode);const o=document.getElementById("fmfm-enabled");o&&(o.checked=e.enabled!==!1);const r=document.getElementById("fmfm-no-answer");r&&(r.value=e.no_answer_destination||"");const s=document.getElementById("fmfm-destinations-list");if(s)if(s.innerHTML="",e.destinations&&e.destinations.length>0)for(const a of e.destinations){I();const l=s.children,m=l[l.length-1],p=m.querySelector(".fmfm-dest-number");p&&(p.value=a.number);const b=m.querySelector(".fmfm-dest-ringtime");b&&(b.value=String(a.ring_time??20))}else I()}async function $n(e){if(confirm(`Are you sure you want to delete FMFM configuration for extension ${e}?`))try{const t=u(),o=await(await g(`${t}/api/fmfm/config/${e}`,{method:"DELETE",headers:d()})).json();o.success?(i(`FMFM configuration deleted for ${e}`,"success"),U()):i(o.error||"Error deleting FMFM configuration","error")}catch(t){console.error("Error deleting FMFM config:",t),i("Error deleting FMFM configuration","error")}}function Be(e){const t=[];if(e.days_of_week){const n=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],o=e.days_of_week.map(r=>n[r]).join(", ");t.push(o)}return e.start_time&&e.end_time&&t.push(`${e.start_time}-${e.end_time}`),e.holidays===!0?t.push("Holidays"):e.holidays===!1&&t.push("Non-holidays"),t.length>0?t.join(" | "):"Always"}async function W(){try{const e=u(),t=await g(`${e}/api/time-routing/rules`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}: ${t.statusText}`);const n=await t.json();if(n.rules){const o=document.getElementById("time-routing-total");o&&(o.textContent=String(n.count||0));const r=n.rules.filter(f=>f.enabled!==!1).length,s=n.rules.filter(f=>f.name&&(f.name.toLowerCase().includes("business")||f.name.toLowerCase().includes("hours"))).length,a=n.rules.filter(f=>f.name&&(f.name.toLowerCase().includes("after")||f.name.toLowerCase().includes("closed"))).length,l=document.getElementById("time-routing-active");l&&(l.textContent=String(r));const m=document.getElementById("time-routing-business");m&&(m.textContent=String(s));const p=document.getElementById("time-routing-after");p&&(p.textContent=String(a));const b=document.getElementById("time-routing-list");if(!b)return;n.rules.length===0?b.innerHTML='<tr><td colspan="7" style="text-align: center;">No time-based routing rules</td></tr>':b.innerHTML=n.rules.map(f=>{const v=f.enabled!==!1?'<span class="badge" style="background: #10b981;">Active</span>':'<span class="badge" style="background: #6b7280;">Disabled</span>',h=f.time_conditions||{},A=Be(h);return`
                        <tr>
                            <td><strong>${c(f.name)}</strong></td>
                            <td>${c(f.destination)}</td>
                            <td>${c(f.route_to)}</td>
                            <td><small>${c(A)}</small></td>
                            <td>${f.priority||100}</td>
                            <td>${v}</td>
                            <td>
                                <button class="btn-small btn-danger" onclick="deleteTimeRoutingRule('${c(f.rule_id)}', '${c(f.name)}')">Delete</button>
                            </td>
                        </tr>
                    `}).join("")}}catch(e){console.error("Error loading time routing rules:",e),i("Error loading time routing rules","error")}}function Sn(){const e=document.getElementById("add-time-rule-modal");e&&(e.style.display="block")}function Pe(){const e=document.getElementById("add-time-rule-modal");e&&(e.style.display="none");const t=document.getElementById("add-time-rule-form");t&&t.reset()}async function xn(e){e.preventDefault();const t=document.getElementById("time-rule-name").value,n=document.getElementById("time-rule-destination").value,o=document.getElementById("time-rule-route-to").value,r=document.getElementById("time-rule-start").value,s=document.getElementById("time-rule-end").value,a=parseInt(document.getElementById("time-rule-priority").value),l=document.getElementById("time-rule-enabled").checked,m=Array.from(document.querySelectorAll('input[name="time-rule-days"]:checked')).map(b=>parseInt(b.value));if(m.length===0){i("Please select at least one day of the week","error");return}const p={name:t,destination:n,route_to:o,priority:a,enabled:l,time_conditions:{days_of_week:m,start_time:r,end_time:s}};try{const b=u(),y=await(await g(`${b}/api/time-routing/rule`,{method:"POST",headers:d(),body:JSON.stringify(p)})).json();y.success?(i(`Time routing rule "${t}" added successfully`,"success"),Pe(),W()):i(y.error||"Error adding time routing rule","error")}catch(b){console.error("Error saving time routing rule:",b),i("Error saving time routing rule","error")}}async function An(e,t){if(confirm(`Are you sure you want to delete time routing rule "${t}"?`))try{const n=u(),r=await(await g(`${n}/api/time-routing/rule/${e}`,{method:"DELETE",headers:d()})).json();r.success?(i(`Time routing rule "${t}" deleted`,"success"),W()):i(r.error||"Error deleting time routing rule","error")}catch(n){console.error("Error deleting time routing rule:",n),i("Error deleting time routing rule","error")}}async function z(){try{const e=u(),t=await g(`${e}/api/webhooks`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}: ${t.statusText}`);const n=await t.json();if(n.subscriptions){const o=document.getElementById("webhooks-list");if(!o)return;n.subscriptions.length===0?o.innerHTML='<tr><td colspan="5" style="text-align: center;">No webhooks configured</td></tr>':o.innerHTML=n.subscriptions.map(r=>{const a=r.enabled!==!1?'<span class="badge" style="background: #10b981;">Active</span>':'<span class="badge" style="background: #6b7280;">Disabled</span>',m=(r.event_types||[]).join(", "),p=r.secret?"Yes":"No";return`
                        <tr>
                            <td>
                                <div style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${c(r.url)}">
                                    ${c(r.url)}
                                </div>
                            </td>
                            <td>
                                <div style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${c(m)}">
                                    <small>${c(m)}</small>
                                </div>
                            </td>
                            <td>${p}</td>
                            <td>${a}</td>
                            <td>
                                <button class="btn-small btn-danger" onclick="deleteWebhook('${c(r.url)}')">Delete</button>
                            </td>
                        </tr>
                    `}).join("")}}catch(e){console.error("Error loading webhooks:",e),i("Error loading webhooks","error")}}function Tn(){const e=document.getElementById("add-webhook-modal");e&&(e.style.display="block")}function Le(){const e=document.getElementById("add-webhook-modal");e&&(e.style.display="none");const t=document.getElementById("add-webhook-form");t&&t.reset()}async function In(e){e.preventDefault();const t=document.getElementById("webhook-url").value,n=document.getElementById("webhook-secret").value,o=document.getElementById("webhook-enabled").checked,r=Array.from(document.querySelectorAll('input[name="webhook-events"]:checked')).map(a=>a.value);if(r.length===0){i("Please select at least one event type","error");return}const s={url:t,event_types:r,enabled:o};n&&(s.secret=n);try{const a=u(),m=await(await g(`${a}/api/webhooks`,{method:"POST",headers:d(),body:JSON.stringify(s)})).json();m.success?(i("Webhook added successfully","success"),Le(),z()):i(m.error||"Error adding webhook","error")}catch(a){console.error("Error adding webhook:",a),i("Error adding webhook","error")}}async function _n(e){if(!confirm(`Are you sure you want to delete webhook for ${e}?`))return;const t=encodeURIComponent(e);try{const n=u(),r=await(await g(`${n}/api/webhooks/${t}`,{method:"DELETE",headers:d()})).json();r.success?(i("Webhook deleted","success"),z()):i(r.error||"Error deleting webhook","error")}catch(n){console.error("Error deleting webhook:",n),i("Error deleting webhook","error")}}function Me(e){const n=new Date().getTime()-e.getTime(),o=Math.floor(n/(1e3*60*60)),r=Math.floor(n%(1e3*60*60)/(1e3*60));return o>0?`${o}h ${r}m`:`${r}m`}async function De(){try{const e=u(),t=await g(`${e}/api/hot-desk/sessions`,{headers:d()});if(!t.ok)throw new Error(`HTTP ${t.status}: ${t.statusText}`);const n=await t.json();if(n.sessions){const o=n.sessions.filter(l=>l.active!==!1),r=document.getElementById("hotdesk-active");r&&(r.textContent=String(o.length));const s=document.getElementById("hotdesk-total");s&&(s.textContent=String(n.sessions.length));const a=document.getElementById("hotdesk-sessions-list");if(!a)return;o.length===0?a.innerHTML='<tr><td colspan="6" style="text-align: center;">No active hot desk sessions</td></tr>':a.innerHTML=o.map(l=>{const m=l.login_time?new Date(l.login_time).toLocaleString():"N/A",p=l.login_time?Me(new Date(l.login_time)):"N/A";return`
                        <tr>
                            <td><strong>${c(l.extension)}</strong></td>
                            <td>${c(l.device_mac||"N/A")}</td>
                            <td>${c(l.device_ip||"N/A")}</td>
                            <td><small>${m}</small></td>
                            <td>${p}</td>
                            <td>
                                <button class="btn-small btn-warning" onclick="logoutHotDesk('${c(l.extension)}')">Logout</button>
                            </td>
                        </tr>
                    `}).join("")}}catch(e){console.error("Error loading hot desk sessions:",e),i("Error loading hot desk sessions","error")}}async function Cn(e){if(confirm(`Are you sure you want to log out extension ${e} from hot desk?`))try{const t=u(),o=await(await g(`${t}/api/hot-desk/logout`,{method:"POST",headers:d(),body:JSON.stringify({extension:e})})).json();o.success?(i(`Extension ${e} logged out`,"success"),De()):i(o.error||"Error logging out","error")}catch(t){console.error("Error logging out hot desk:",t),i("Error logging out hot desk","error")}}async function J(){try{const e=u(),[t,n]=await Promise.all([g(`${e}/api/recording-retention/policies`,{headers:d()}),g(`${e}/api/recording-retention/statistics`,{headers:d()})]),[o,r]=await Promise.all([t.json(),n.json()]);if(r){const s=document.getElementById("retention-policies-count");s&&(s.textContent=String(r.total_policies||0));const a=document.getElementById("retention-recordings");a&&(a.textContent=String(r.total_recordings||0));const l=document.getElementById("retention-deleted");l&&(l.textContent=String(r.deleted_count||0));const m=r.last_cleanup?new Date(r.last_cleanup).toLocaleDateString():"Never",p=document.getElementById("retention-last-cleanup");p&&(p.textContent=m)}if(o&&o.policies){const s=document.getElementById("retention-policies-list");if(!s)return;o.policies.length===0?s.innerHTML='<tr><td colspan="5" style="text-align: center;">No retention policies configured</td></tr>':s.innerHTML=o.policies.map(a=>{const l=a.created_at?new Date(a.created_at).toLocaleDateString():"N/A",m=a.tags?a.tags.join(", "):"None";return`
                        <tr>
                            <td><strong>${c(a.name)}</strong></td>
                            <td>${a.retention_days} days</td>
                            <td><small>${c(m)}</small></td>
                            <td><small>${l}</small></td>
                            <td>
                                <button class="btn-small btn-danger" onclick="deleteRetentionPolicy('${c(a.policy_id)}', '${c(a.name)}')">Delete</button>
                            </td>
                        </tr>
                    `}).join("")}}catch(e){console.error("Error loading retention policies:",e),i("Error loading retention policies","error")}}function Bn(){const e=document.getElementById("add-retention-policy-modal");e&&(e.style.display="block")}function Re(){const e=document.getElementById("add-retention-policy-modal");e&&(e.style.display="none");const t=document.getElementById("add-retention-policy-form");t&&t.reset()}async function Pn(e){e.preventDefault();const t=document.getElementById("retention-policy-name").value,n=parseInt(document.getElementById("retention-days").value),o=document.getElementById("retention-tags").value;if(!t.match(/^[a-zA-Z0-9_\s-]+$/)){i("Policy name contains invalid characters","error");return}if(n<1||n>3650){i("Retention days must be between 1 and 3650","error");return}const r={name:t,retention_days:n};o.trim()&&(r.tags=o.split(",").map(s=>s.trim()).filter(s=>s));try{const s=u(),l=await(await g(`${s}/api/recording-retention/policy`,{method:"POST",headers:d(),body:JSON.stringify(r)})).json();l.success?(i(`Retention policy "${t}" added successfully`,"success"),Re(),J()):i(l.error||"Error adding retention policy","error")}catch(s){console.error("Error adding retention policy:",s),i("Error adding retention policy","error")}}async function Ln(e,t){if(confirm(`Are you sure you want to delete retention policy "${t}"?`))try{const n=u(),r=await(await g(`${n}/api/recording-retention/policy/${encodeURIComponent(e)}`,{method:"DELETE",headers:d()})).json();r.success?(i(`Retention policy "${t}" deleted`,"success"),J()):i(r.error||"Error deleting retention policy","error")}catch(n){console.error("Error deleting retention policy:",n),i("Error deleting retention policy","error")}}async function S(){try{const e=u(),[t,n]=await Promise.all([g(`${e}/api/callback-queue/list`,{headers:d()}),g(`${e}/api/callback-queue/statistics`,{headers:d()})]),[o,r]=await Promise.all([t.json(),n.json()]);if(r){const s=document.getElementById("callback-total");s&&(s.textContent=String(r.total_callbacks||0));const a=r.status_breakdown||{},l=document.getElementById("callback-scheduled");l&&(l.textContent=String(a.scheduled||0));const m=document.getElementById("callback-in-progress");m&&(m.textContent=String(a.in_progress||0));const p=document.getElementById("callback-completed");p&&(p.textContent=String(a.completed||0));const b=document.getElementById("callback-failed");b&&(b.textContent=String(a.failed||0))}if(o&&o.callbacks){const s=document.getElementById("callback-list");if(!s)return;o.callbacks.length===0?s.innerHTML='<tr><td colspan="8" style="text-align: center;">No callbacks in queue</td></tr>':s.innerHTML=o.callbacks.map(a=>{const l=new Date(a.requested_at).toLocaleString(),m=new Date(a.callback_time).toLocaleString();let p="";switch(a.status){case"scheduled":p="badge-info";break;case"in_progress":p="badge-warning";break;case"completed":p="badge-success";break;case"failed":p="badge-danger";break;case"cancelled":p="badge-secondary";break;default:p="badge-info"}return`
                        <tr>
                            <td><code>${c(a.callback_id)}</code></td>
                            <td>${c(a.queue_id)}</td>
                            <td>
                                <strong>${c(a.caller_number)}</strong><br>
                                <small>${c(a.caller_name||"N/A")}</small>
                            </td>
                            <td><small>${l}</small></td>
                            <td><small>${m}</small></td>
                            <td><span class="badge ${p}">${c(a.status)}</span></td>
                            <td>${a.attempts}</td>
                            <td>
                                ${a.status==="scheduled"?`
                                    <button class="btn-small btn-primary" onclick="startCallback('${c(a.callback_id)}')">Start</button>
                                    <button class="btn-small btn-danger" onclick="cancelCallback('${c(a.callback_id)}')">Cancel</button>
                                `:a.status==="in_progress"?`
                                    <button class="btn-small btn-success" onclick="completeCallback('${c(a.callback_id)}', true)">Done</button>
                                    <button class="btn-small btn-warning" onclick="completeCallback('${c(a.callback_id)}', false)">Retry</button>
                                `:"-"}
                            </td>
                        </tr>
                    `}).join("")}}catch(e){console.error("Error loading callback queue:",e),i("Error loading callback queue","error")}}function Mn(){const e=document.createElement("div");e.className="modal",e.id="request-callback-modal",e.innerHTML=`
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
    `,document.body.appendChild(e),e.style.display="block"}function He(){const e=document.getElementById("request-callback-modal");e&&e.remove()}async function Dn(e){e.preventDefault();const t=document.getElementById("callback-queue-id").value,n=document.getElementById("callback-caller-number").value,o=document.getElementById("callback-caller-name").value,r=document.getElementById("callback-preferred-time").value,s={queue_id:t,caller_number:n};o&&(s.caller_name=o),r&&(s.preferred_time=new Date(r).toISOString());try{const a=u(),m=await(await g(`${a}/api/callback-queue/request`,{method:"POST",headers:d(),body:JSON.stringify(s)})).json();m.success?(i("Callback requested successfully","success"),He(),S()):i(m.error||"Error requesting callback","error")}catch(a){console.error("Error requesting callback:",a),i("Error requesting callback","error")}}async function Rn(e){const t=prompt("Enter your agent ID/extension:");if(t)try{const n=u(),r=await(await g(`${n}/api/callback-queue/start`,{method:"POST",headers:d(),body:JSON.stringify({callback_id:e,agent_id:t})})).json();r.success?(i(`Started callback to ${r.caller_number??"caller"}`,"success"),S()):i(r.error||"Error starting callback","error")}catch(n){console.error("Error starting callback:",n),i("Error starting callback","error")}}async function Hn(e,t){let n="";t||(n=prompt("Enter reason for failure (optional):")||"");try{const o=u(),s=await(await g(`${o}/api/callback-queue/complete`,{method:"POST",headers:d(),body:JSON.stringify({callback_id:e,success:t,notes:n})})).json();s.success?(i(t?"Callback completed":"Callback will be retried","success"),S()):i(s.error||"Error completing callback","error")}catch(o){console.error("Error completing callback:",o),i("Error completing callback","error")}}async function jn(e){if(confirm("Are you sure you want to cancel this callback request?"))try{const t=u(),o=await(await g(`${t}/api/callback-queue/cancel`,{method:"POST",headers:d(),body:JSON.stringify({callback_id:e})})).json();o.success?(i("Callback cancelled","success"),S()):i(o.error||"Error cancelling callback","error")}catch(t){console.error("Error cancelling callback:",t),i("Error cancelling callback","error")}}window.loadFMFMExtensions=U;window.showAddFMFMModal=_e;window.closeAddFMFMModal=Ce;window.addFMFMDestinationRow=I;window.saveFMFMConfig=vn;window.editFMFMConfig=kn;window.deleteFMFMConfig=$n;window.getScheduleDescription=Be;window.showAddTimeRuleModal=Sn;window.closeAddTimeRuleModal=Pe;window.loadTimeRoutingRules=W;window.saveTimeRoutingRule=xn;window.deleteTimeRoutingRule=An;window.showAddWebhookModal=Tn;window.closeAddWebhookModal=Le;window.loadWebhooks=z;window.addWebhook=In;window.deleteWebhook=_n;window.loadHotDeskSessions=De;window.logoutHotDesk=Cn;window.getDuration=Me;window.loadRetentionPolicies=J;window.showAddRetentionPolicyModal=Bn;window.closeAddRetentionPolicyModal=Re;window.addRetentionPolicy=Pn;window.deleteRetentionPolicy=Ln;window.loadCallbackQueue=S;window.showRequestCallbackModal=Mn;window.closeRequestCallbackModal=He;window.requestCallback=Dn;window.startCallback=Rn;window.completeCallback=Hn;window.cancelCallback=jn;async function V(){try{const e=u(),[t,n]=await Promise.all([g(`${e}/api/fraud-detection/alerts?hours=24`,{headers:d()}),g(`${e}/api/fraud-detection/statistics`,{headers:d()})]),[o,r]=await Promise.all([t.json(),n.json()]);if(r){const s=a=>document.getElementById(a);s("fraud-total-alerts")&&(s("fraud-total-alerts").textContent=String(r.total_alerts??0)),s("fraud-high-risk")&&(s("fraud-high-risk").textContent=String(r.high_risk_alerts??0)),s("fraud-blocked-patterns")&&(s("fraud-blocked-patterns").textContent=String(r.blocked_patterns_count??0)),s("fraud-extensions-flagged")&&(s("fraud-extensions-flagged").textContent=String(r.extensions_flagged??0))}if(o?.alerts){const s=document.getElementById("fraud-alerts-list");s&&(o.alerts.length===0?s.innerHTML='<tr><td colspan="5" style="text-align: center;">No fraud alerts detected</td></tr>':s.innerHTML=o.alerts.map(a=>{const l=new Date(a.timestamp).toLocaleString(),m=a.fraud_score>.8?"#ef4444":a.fraud_score>.5?"#f59e0b":"#10b981",p=(a.fraud_score*100).toFixed(0),b=(a.alert_types??[]).join(", ");return`
                            <tr>
                                <td><small>${c(l)}</small></td>
                                <td><strong>${c(a.extension)}</strong></td>
                                <td><small>${c(b)}</small></td>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 5px;">
                                        <div style="flex: 1; background: #e5e7eb; border-radius: 4px; height: 20px; overflow: hidden;">
                                            <div style="background: ${m}; height: 100%; width: ${p}%;"></div>
                                        </div>
                                        <span>${p}%</span>
                                    </div>
                                </td>
                                <td><small>${c(a.details??"No details")}</small></td>
                            </tr>
                        `}).join(""))}if(r?.blocked_patterns){const s=document.getElementById("blocked-patterns-list");s&&(r.blocked_patterns.length===0?s.innerHTML='<tr><td colspan="3" style="text-align: center;">No blocked patterns</td></tr>':s.innerHTML=r.blocked_patterns.map((a,l)=>`
                        <tr>
                            <td><code>${c(a.pattern)}</code></td>
                            <td>${c(a.reason)}</td>
                            <td>
                                <button class="btn-small btn-danger" onclick="deleteBlockedPattern(${l}, '${c(a.pattern)}')">Delete</button>
                            </td>
                        </tr>
                    `).join(""))}}catch(e){console.error("Error loading fraud detection data:",e),i("Error loading fraud detection data","error")}}function Nn(){const e=document.getElementById("add-blocked-pattern-modal");e&&(e.style.display="block")}function je(){const e=document.getElementById("add-blocked-pattern-modal");e&&(e.style.display="none");const t=document.getElementById("add-blocked-pattern-form");t&&t.reset()}async function Fn(e){e.preventDefault();const t=document.getElementById("blocked-pattern"),n=document.getElementById("blocked-reason"),o=t?.value??"",r=n?.value??"";try{new RegExp(o)}catch(a){const l=a instanceof Error?a.message:String(a);i(`Invalid regex pattern: ${l}`,"error");return}const s={pattern:o,reason:r};try{const a=u(),m=await(await g(`${a}/api/fraud-detection/blocked-pattern`,{method:"POST",headers:d(),body:JSON.stringify(s)})).json();m.success?(i("Blocked pattern added successfully","success"),je(),V()):i(m.error??"Error adding blocked pattern","error")}catch(a){console.error("Error adding blocked pattern:",a),i("Error adding blocked pattern","error")}}async function qn(e,t){if(confirm(`Are you sure you want to unblock pattern "${t}"?`))try{const n=u(),r=await(await g(`${n}/api/fraud-detection/blocked-pattern/${e}`,{method:"DELETE",headers:d()})).json();r.success?(i("Blocked pattern removed","success"),V()):i(r.error??"Error removing blocked pattern","error")}catch(n){console.error("Error removing blocked pattern:",n),i("Error removing blocked pattern","error")}}async function x(){try{const e=u(),[t,n]=await Promise.all([g(`${e}/api/callback-queue/list`,{headers:d()}),g(`${e}/api/callback-queue/statistics`,{headers:d()})]),[o,r]=await Promise.all([t.json(),n.json()]);if(r){const s=l=>document.getElementById(l);s("callback-total")&&(s("callback-total").textContent=String(r.total_callbacks??0));const a=r.status_breakdown??{};s("callback-scheduled")&&(s("callback-scheduled").textContent=String(a.scheduled??0)),s("callback-in-progress")&&(s("callback-in-progress").textContent=String(a.in_progress??0)),s("callback-completed")&&(s("callback-completed").textContent=String(a.completed??0)),s("callback-failed")&&(s("callback-failed").textContent=String(a.failed??0))}if(o?.callbacks){const s=document.getElementById("callback-list");s&&(o.callbacks.length===0?s.innerHTML='<tr><td colspan="8" style="text-align: center;">No callbacks in queue</td></tr>':s.innerHTML=o.callbacks.map(a=>{const l=new Date(a.requested_at).toLocaleString(),m=new Date(a.callback_time).toLocaleString();let p="";switch(a.status){case"scheduled":p="badge-info";break;case"in_progress":p="badge-warning";break;case"completed":p="badge-success";break;case"failed":p="badge-danger";break;case"cancelled":p="badge-secondary";break;default:p="badge-info"}return`
                            <tr>
                                <td><code>${c(a.callback_id)}</code></td>
                                <td>${c(a.queue_id)}</td>
                                <td>
                                    <strong>${c(a.caller_number)}</strong><br>
                                    <small>${c(a.caller_name??"N/A")}</small>
                                </td>
                                <td><small>${c(l)}</small></td>
                                <td><small>${c(m)}</small></td>
                                <td><span class="badge ${p}">${c(a.status)}</span></td>
                                <td>${a.attempts}</td>
                                <td>
                                    ${a.status==="scheduled"?`
                                        <button class="btn-small btn-primary" onclick="startCallback('${c(a.callback_id)}')">Start</button>
                                        <button class="btn-small btn-danger" onclick="cancelCallback('${c(a.callback_id)}')">Cancel</button>
                                    `:a.status==="in_progress"?`
                                        <button class="btn-small btn-success" onclick="completeCallback('${c(a.callback_id)}', true)">Done</button>
                                        <button class="btn-small btn-warning" onclick="completeCallback('${c(a.callback_id)}', false)">Retry</button>
                                    `:"-"}
                                </td>
                            </tr>
                        `}).join(""))}}catch(e){console.error("Error loading callback queue:",e),i("Error loading callback queue","error")}}function On(){const e=document.createElement("div");e.className="modal",e.id="request-callback-modal",e.innerHTML=`
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
    `,document.body.appendChild(e),e.style.display="block"}function Ne(){const e=document.getElementById("request-callback-modal");e&&e.remove()}async function Un(e){e.preventDefault();const t=document.getElementById("callback-queue-id")?.value??"",n=document.getElementById("callback-caller-number")?.value??"",o=document.getElementById("callback-caller-name")?.value??"",r=document.getElementById("callback-preferred-time")?.value??"",s={queue_id:t,caller_number:n};o&&(s.caller_name=o),r&&(s.preferred_time=new Date(r).toISOString());try{const a=u(),m=await(await g(`${a}/api/callback-queue/request`,{method:"POST",headers:d(),body:JSON.stringify(s)})).json();m.success?(i("Callback requested successfully","success"),Ne(),x()):i(m.error??"Error requesting callback","error")}catch(a){console.error("Error requesting callback:",a),i("Error requesting callback","error")}}async function Wn(e){const t=prompt("Enter your agent ID/extension:");if(t)try{const n=u(),r=await(await g(`${n}/api/callback-queue/start`,{method:"POST",headers:d(),body:JSON.stringify({callback_id:e,agent_id:t})})).json();r.success?(i(`Started callback to ${r.caller_number??e}`,"success"),x()):i(r.error??"Error starting callback","error")}catch(n){console.error("Error starting callback:",n),i("Error starting callback","error")}}async function zn(e,t){let n="";t||(n=prompt("Enter reason for failure (optional):")??"");try{const o=u(),s=await(await g(`${o}/api/callback-queue/complete`,{method:"POST",headers:d(),body:JSON.stringify({callback_id:e,success:t,notes:n})})).json();s.success?(i(t?"Callback completed":"Callback will be retried","success"),x()):i(s.error??"Error completing callback","error")}catch(o){console.error("Error completing callback:",o),i("Error completing callback","error")}}async function Jn(e){if(confirm("Are you sure you want to cancel this callback request?"))try{const t=u(),o=await(await g(`${t}/api/callback-queue/cancel`,{method:"POST",headers:d(),body:JSON.stringify({callback_id:e})})).json();o.success?(i("Callback cancelled","success"),x()):i(o.error??"Error cancelling callback","error")}catch(t){console.error("Error cancelling callback:",t),i("Error cancelling callback","error")}}async function Q(){try{const e=u(),[t,n,o]=await Promise.all([g(`${e}/api/mobile-push/devices`,{headers:d()}),g(`${e}/api/mobile-push/statistics`,{headers:d()}),g(`${e}/api/mobile-push/history`,{headers:d()})]),[r,s,a]=await Promise.all([t.json(),n.json(),o.json()]);if(s){const l=p=>document.getElementById(p);l("push-total-devices")&&(l("push-total-devices").textContent=String(s.total_devices??0)),l("push-total-users")&&(l("push-total-users").textContent=String(s.total_users??0));const m=s.platforms??{};l("push-ios-devices")&&(l("push-ios-devices").textContent=String(m.ios??0)),l("push-android-devices")&&(l("push-android-devices").textContent=String(m.android??0)),l("push-recent-notifications")&&(l("push-recent-notifications").textContent=String(s.recent_notifications??0))}if(r?.devices){const l=document.getElementById("mobile-devices-list");l&&(r.devices.length===0?l.innerHTML='<tr><td colspan="5" style="text-align: center;">No devices registered</td></tr>':l.innerHTML=r.devices.map(m=>{const p=new Date(m.registered_at).toLocaleString(),b=new Date(m.last_seen).toLocaleString();let f="";return m.platform==="ios"?f='<span class="badge badge-info">iOS</span>':m.platform==="android"?f='<span class="badge badge-success">Android</span>':f=`<span class="badge badge-secondary">${c(m.platform)}</span>`,`
                            <tr>
                                <td><strong>${c(m.user_id)}</strong></td>
                                <td>${f}</td>
                                <td><small>${c(p)}</small></td>
                                <td><small>${c(b)}</small></td>
                                <td>
                                    <button class="btn-small btn-primary" onclick="sendTestNotification('${c(m.user_id)}')">Test</button>
                                </td>
                            </tr>
                        `}).join(""))}if(a?.history){const l=document.getElementById("push-history-list");l&&(a.history.length===0?l.innerHTML='<tr><td colspan="5" style="text-align: center;">No notifications sent</td></tr>':l.innerHTML=a.history.slice(0,50).map(m=>{const p=new Date(m.sent_at).toLocaleString(),b=m.success_count??0,f=m.failure_count??0;return`
                                <tr>
                                    <td>${c(m.user_id)}</td>
                                    <td><strong>${c(m.title)}</strong></td>
                                    <td><small>${c(m.body)}</small></td>
                                    <td><small>${c(p)}</small></td>
                                    <td>
                                        <span class="badge badge-success">${b} sent</span>
                                        ${f>0?`<span class="badge badge-danger">${f} failed</span>`:""}
                                    </td>
                                </tr>
                            `}).join(""))}}catch(e){console.error("Error loading mobile push data:",e),i("Error loading mobile push data","error")}}function Vn(){const e=document.createElement("div");e.className="modal",e.id="register-device-modal",e.innerHTML=`
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
    `,document.body.appendChild(e),e.style.display="block"}function Fe(){const e=document.getElementById("register-device-modal");e&&e.remove()}async function Qn(e){e.preventDefault();const t=document.getElementById("device-user-id")?.value??"",n=document.getElementById("device-token")?.value.trim()??"",o=document.getElementById("device-platform")?.value??"",r={user_id:t,device_token:n,platform:o};try{const s=u(),l=await(await g(`${s}/api/mobile-push/register`,{method:"POST",headers:d(),body:JSON.stringify(r)})).json();l.success?(i("Device registered successfully","success"),Fe(),Q()):i(l.error??"Error registering device","error")}catch(s){console.error("Error registering device:",s),i("Error registering device","error")}}function Zn(){const e=document.createElement("div");e.className="modal",e.id="test-notification-modal",e.innerHTML=`
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
    `,document.body.appendChild(e),e.style.display="block"}function qe(){const e=document.getElementById("test-notification-modal");e&&e.remove()}function Gn(e){e.preventDefault();const t=document.getElementById("test-user-id")?.value??"";Oe(t),qe()}async function Oe(e){try{const t=u(),o=await(await g(`${t}/api/mobile-push/test`,{method:"POST",headers:d(),body:JSON.stringify({user_id:e})})).json();o.success||o.stub_mode?(o.stub_mode?i("Test notification logged (Firebase not configured)","warning"):i(`Test notification sent: ${o.success_count??0} succeeded, ${o.failure_count??0} failed`,"success"),Q()):i(o.error??"Error sending test notification","error")}catch(t){console.error("Error sending test notification:",t),i("Error sending test notification","error")}}async function Yn(){try{const e=u(),[t,n]=await Promise.all([g(`${e}/api/recording-announcements/statistics`,{headers:d()}),g(`${e}/api/recording-announcements/config`,{headers:d()})]),[o,r]=await Promise.all([t.json(),n.json()]);if(o){const s=a=>document.getElementById(a);s("announcements-enabled")&&(s("announcements-enabled").textContent=o.enabled?"Enabled":"Disabled"),s("announcements-played")&&(s("announcements-played").textContent=String(o.announcements_played??0)),s("consent-accepted")&&(s("consent-accepted").textContent=String(o.consent_accepted??0)),s("consent-declined")&&(s("consent-declined").textContent=String(o.consent_declined??0)),s("announcement-type")&&(s("announcement-type").textContent=o.announcement_type??"N/A"),s("require-consent")&&(s("require-consent").textContent=o.require_consent?"Yes":"No")}if(r){const s=a=>document.getElementById(a);s("audio-file-path")&&(s("audio-file-path").textContent=r.audio_path??"N/A"),s("announcement-text")&&(s("announcement-text").textContent=r.announcement_text??"N/A")}}catch(e){console.error("Error loading recording announcements data:",e),i("Error loading recording announcements data","error")}}async function Kn(){try{const e=u(),n=await(await g(`${e}/api/framework/speech-analytics/configs`,{headers:d()})).json(),o=document.getElementById("speech-analytics-configs-table");if(!o)return;if(!n.configs||n.configs.length===0){o.innerHTML='<tr><td colspan="5" class="loading">No extension-specific configurations. Using system defaults.</td></tr>';return}o.innerHTML=n.configs.map(r=>`
            <tr>
                <td>${c(r.extension)}</td>
                <td>${r.transcription_enabled?"Enabled":"Disabled"}</td>
                <td>${r.sentiment_enabled?"Enabled":"Disabled"}</td>
                <td>${r.summarization_enabled?"Enabled":"Disabled"}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editSpeechAnalyticsConfig('${c(r.extension)}')">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteSpeechAnalyticsConfig('${c(r.extension)}')">Delete</button>
                </td>
            </tr>
        `).join("")}catch(e){console.error("Error loading speech analytics configs:",e),i("Error loading speech analytics configurations","error")}}async function Ue(){try{const e=u(),t=await g(`${e}/api/framework/integrations/activity-log`,{headers:d()});if(!t.ok){console.error("Error loading CRM activity log:",t.status),i("Error loading CRM activity log","error");return}const n=await t.json(),o=document.getElementById("crm-activity-log-table");if(!o)return;if(!n.activities||n.activities.length===0){o.innerHTML='<tr><td colspan="5" class="loading">No integration activity yet</td></tr>';return}o.innerHTML=n.activities.map(r=>{const s=r.status==="success"?"success":"error",a=r.status==="success"?"OK":"FAIL";return`
                <tr>
                    <td>${c(new Date(r.timestamp).toLocaleString())}</td>
                    <td>${c(r.integration)}</td>
                    <td>${c(r.action)}</td>
                    <td class="${s}">${a} ${c(r.status)}</td>
                    <td>${c(r.details??"-")}</td>
                </tr>
            `}).join("")}catch(e){console.error("Error loading CRM activity log:",e),i("Error loading CRM activity log","error")}}async function Xn(){if(confirm("Clear old activity log entries? This will remove entries older than 30 days."))try{const e=u(),n=await(await g(`${e}/api/framework/integrations/activity-log/clear`,{method:"POST",headers:d()})).json();n.success?(i(`Cleared ${n.deleted_count??0} old entries`,"success"),Ue()):i(n.error??"Error clearing activity log","error")}catch(e){console.error("Error clearing CRM activity log:",e),i("Error clearing activity log","error")}}window.loadFraudAlerts=V;window.showAddBlockedPatternModal=Nn;window.closeAddBlockedPatternModal=je;window.addBlockedPattern=Fn;window.deleteBlockedPattern=qn;window.loadCallbackQueue=x;window.showRequestCallbackModal=On;window.closeRequestCallbackModal=Ne;window.requestCallback=Un;window.startCallback=Wn;window.completeCallback=zn;window.cancelCallback=Jn;window.loadMobilePushDevices=Q;window.showRegisterDeviceModal=Vn;window.closeRegisterDeviceModal=Fe;window.registerDevice=Qn;window.showTestNotificationModal=Zn;window.closeTestNotificationModal=qe;window.sendTestNotificationForm=Gn;window.sendTestNotification=Oe;window.loadRecordingAnnouncementsStats=Yn;window.loadSpeechAnalyticsConfigs=Kn;window.loadCRMActivityLog=Ue;window.clearCRMActivityLog=Xn;const eo={completed:"success",failed:"error",cancelled:"warning",busy:"warning","no-answer":"warning"};async function We(){try{const e=u(),n=await(await g(`${e}/api/framework/click-to-dial/configs`,{headers:d()})).json();if(n.error){console.error("Error loading click-to-dial configs:",n.error);return}const o=document.getElementById("ctd-extension-select"),r=document.getElementById("ctd-history-extension"),s=window.currentExtensions;if(o&&s){o.innerHTML='<option value="">Select Extension</option>';for(const l of s){const m=document.createElement("option");m.value=l.number,m.textContent=`${l.number} - ${l.name}`,o.appendChild(m)}}if(r&&s){r.innerHTML='<option value="">All Extensions</option>';for(const l of s){const m=document.createElement("option");m.value=l.number,m.textContent=`${l.number} - ${l.name}`,r.appendChild(m)}}const a=document.getElementById("ctd-configs-table");if(!a)return;if(!n.configs||n.configs.length===0){a.innerHTML='<tr><td colspan="6" style="text-align: center;">No configurations found. Configure extensions above.</td></tr>';return}a.innerHTML=n.configs.map(l=>`
            <tr>
                <td>${c(l.extension)}</td>
                <td><span class="status-badge ${l.enabled?"success":"error"}">${l.enabled?"Enabled":"Disabled"}</span></td>
                <td>${l.default_caller_id?c(l.default_caller_id):"-"}</td>
                <td>${l.auto_answer?"Yes":"No"}</td>
                <td>${l.browser_notification?"Yes":"No"}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editClickToDialConfig('${c(l.extension)}')">Edit</button>
                </td>
            </tr>
        `).join("")}catch(e){console.error("Error loading click-to-dial configs:",e),e instanceof Error&&E(e,"Loading click-to-dial configurations")}}function R(e){const t=document.getElementById("ctd-config-section"),n=document.getElementById("ctd-no-extension");t&&n&&(t.style.display=e?"block":"none",n.style.display=e?"none":"block")}async function ze(){const t=document.getElementById("ctd-extension-select")?.value;if(!t){R(!1);return}try{const n=u(),r=await(await g(`${n}/api/framework/click-to-dial/config/${t}`,{headers:d()})).json();if(r.error){console.error("Error loading config:",r.error);const s=document.getElementById("ctd-current-extension");s&&(s.textContent=t);const a=document.getElementById("ctd-enabled");a&&(a.checked=!0);const l=document.getElementById("ctd-caller-id");l&&(l.value="");const m=document.getElementById("ctd-auto-answer");m&&(m.checked=!1);const p=document.getElementById("ctd-browser-notification");p&&(p.checked=!0)}else{const s=document.getElementById("ctd-current-extension");s&&(s.textContent=t);const a=document.getElementById("ctd-enabled");a&&(a.checked=r.config.enabled);const l=document.getElementById("ctd-caller-id");l&&(l.value=r.config.default_caller_id??"");const m=document.getElementById("ctd-auto-answer");m&&(m.checked=r.config.auto_answer);const p=document.getElementById("ctd-browser-notification");p&&(p.checked=r.config.browser_notification)}R(!0)}catch(n){console.error("Error loading click-to-dial config:",n),n instanceof Error&&E(n,"Loading click-to-dial configuration")}}async function to(e){e.preventDefault();const n=document.getElementById("ctd-current-extension")?.textContent;if(!n){i("No extension selected","error");return}const o={enabled:document.getElementById("ctd-enabled")?.checked??!1,default_caller_id:document.getElementById("ctd-caller-id")?.value.trim()||null,auto_answer:document.getElementById("ctd-auto-answer")?.checked??!1,browser_notification:document.getElementById("ctd-browser-notification")?.checked??!1};try{const r=u(),a=await(await g(`${r}/api/framework/click-to-dial/config/${n}`,{method:"POST",headers:d(),body:JSON.stringify(o)})).json();a.error?i(`Error: ${a.error}`,"error"):(i("Configuration saved successfully","success"),We())}catch(r){console.error("Error saving config:",r),r instanceof Error&&E(r,"Saving click-to-dial configuration"),i("Error saving configuration","error")}}async function no(e){const t=document.getElementById("ctd-extension-select");if(t){t.value=e,await ze();const n=document.getElementById("ctd-config-section");n&&n.scrollIntoView({behavior:"smooth"})}}async function oo(){const t=document.getElementById("ctd-extension-select")?.value,n=document.getElementById("ctd-phone-number"),o=n?.value.trim();if(!t){i("Please select an extension","error");return}if(!o){i("Please enter a phone number","error");return}try{const r=u(),a=await(await g(`${r}/api/framework/click-to-dial/call/${t}`,{method:"POST",headers:d(),body:JSON.stringify({destination:o})})).json();a.error?i(`Error: ${a.error}`,"error"):(i(`Call initiated from extension ${t} to ${o}`,"success"),n&&(n.value=""),setTimeout(()=>Je(),1e3))}catch(r){console.error("Error initiating call:",r),r instanceof Error&&E(r,"Initiating click-to-dial call"),i("Error initiating call","error")}}async function Je(){const t=document.getElementById("ctd-history-extension")?.value,n=document.getElementById("ctd-history-table");if(n){if(!t){n.innerHTML='<tr><td colspan="5" style="text-align: center;">Select an extension to view history</td></tr>';return}try{const o=u(),s=await(await g(`${o}/api/framework/click-to-dial/history/${t}`,{headers:d()})).json();if(s.error){n.innerHTML=`<tr><td colspan="5" style="text-align: center;">Error: ${c(s.error)}</td></tr>`;return}if(!s.history||s.history.length===0){n.innerHTML='<tr><td colspan="5" style="text-align: center;">No call history found</td></tr>';return}n.innerHTML=s.history.map(a=>{const l=new Date(a.timestamp).toLocaleString(),m=a.duration?`${a.duration}s`:"-",p=eo[a.status]??"warning";return`
                <tr>
                    <td>${c(l)}</td>
                    <td>${c(a.extension)}</td>
                    <td>${c(a.destination)}</td>
                    <td>${m}</td>
                    <td><span class="status-badge ${p}">${c(a.status)}</span></td>
                </tr>
            `}).join("")}catch(o){console.error("Error loading history:",o),o instanceof Error&&E(o,"Loading click-to-dial history"),n&&(n.innerHTML='<tr><td colspan="5" style="text-align: center;">Error loading history</td></tr>')}}}async function so(){try{const e=u(),n=await(await g(`${e}/api/webrtc/phone-config`,{headers:d()})).json();if(n.success){const o=document.getElementById("webrtc-phone-extension");o&&(o.value=n.extension??(typeof DEFAULT_WEBRTC_EXTENSION<"u"?DEFAULT_WEBRTC_EXTENSION:"")),typeof initWebRTCPhone=="function"&&initWebRTCPhone()}else console.error("Failed to load WebRTC phone config:",n.error)}catch(e){console.error("Error loading WebRTC phone config:",e)}}async function ro(e){e.preventDefault();const n=document.getElementById("webrtc-phone-extension")?.value.trim()??"";if(!n){i("Please enter an extension","error");return}try{const o=u(),s=await(await g(`${o}/api/webrtc/phone-config`,{method:"POST",headers:d(),body:JSON.stringify({extension:n})})).json();s.success?(i("Phone extension saved successfully! Reloading phone...","success"),typeof initWebRTCPhone=="function"&&initWebRTCPhone()):i(`Error: ${s.error??"Failed to save phone extension"}`,"error")}catch(o){console.error("Error saving WebRTC phone config:",o);const r=o instanceof Error?o.message:String(o);i(`Error: ${r}`,"error")}}window.loadClickToDialConfigs=We;window.toggleClickToDialConfigSections=R;window.loadClickToDialConfig=ze;window.saveClickToDialConfig=to;window.editClickToDialConfig=no;window.initiateClickToDial=oo;window.loadClickToDialHistory=Je;window.loadWebRTCPhoneConfig=so;window.saveWebRTCPhoneConfig=ro;async function ao(){try{const e=u(),n=await(await g(`${e}/api/framework/nomadic-e911/sites`,{headers:d()})).json(),o=document.getElementById("e911-sites-table");if(!o)return;if(!n.sites||n.sites.length===0){o.innerHTML='<tr><td colspan="5" class="loading">No E911 sites configured</td></tr>';return}o.innerHTML=n.sites.map(r=>`
            <tr>
                <td>${c(r.site_name)}</td>
                <td>${c(r.address)}, ${c(r.city)}, ${c(r.state)} ${c(r.postal_code)}</td>
                <td>${c(r.ip_ranges??"N/A")}</td>
                <td>${c(r.psap??"Default")}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editE911Site(${r.id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteE911Site(${r.id})">Delete</button>
                </td>
            </tr>
        `).join("")}catch(e){console.error("Error loading E911 sites:",e),i("Error loading E911 sites","error")}}async function io(){try{const e=u(),n=await(await g(`${e}/api/framework/nomadic-e911/locations`,{headers:d()})).json(),o=document.getElementById("extension-locations-table");if(!o)return;if(!n.locations||n.locations.length===0){o.innerHTML='<tr><td colspan="5" class="loading">No location data available</td></tr>';return}o.innerHTML=n.locations.map(r=>`
            <tr>
                <td>${c(r.extension)}</td>
                <td>${c(r.site_name??"Unknown")} - ${c(r.address??"N/A")}</td>
                <td>${c(r.detection_method??"N/A")}</td>
                <td>${r.last_updated?new Date(r.last_updated).toLocaleString():"N/A"}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="updateExtensionLocation('${c(r.extension)}')">Update</button>
                </td>
            </tr>
        `).join("")}catch(e){console.error("Error loading extension locations:",e),i("Error loading extension locations","error")}}async function co(){const t=document.getElementById("location-history-extension")?.value??"",n=t?`/api/framework/nomadic-e911/history/${t}`:"/api/framework/nomadic-e911/history";try{const o=u(),s=await(await g(`${o}${n}`,{headers:d()})).json(),a=document.getElementById("location-history-table");if(!a)return;if(!s.history||s.history.length===0){a.innerHTML='<tr><td colspan="5" class="loading">No location history available</td></tr>';return}a.innerHTML=s.history.map(l=>`
            <tr>
                <td>${c(new Date(l.timestamp).toLocaleString())}</td>
                <td>${c(l.extension)}</td>
                <td>${c(l.site_name??"N/A")}</td>
                <td>${c(l.detection_method??"N/A")}</td>
                <td>${c(l.ip_address??"N/A")}</td>
            </tr>
        `).join("")}catch(o){console.error("Error loading location history:",o),i("Error loading location history","error")}}function lo(){i("Add E911 site modal coming soon","info")}function uo(e){i(`Edit E911 site ${e} coming soon`,"info")}function mo(e){confirm(`Delete E911 site ${e}?`)&&i(`Delete E911 site ${e} coming soon`,"info")}function go(){i("Update location modal coming soon","info")}function fo(e){i(`Update location for extension ${e} coming soon`,"info")}function po(){i("Add speech analytics config modal coming soon","info")}function bo(e){i(`Edit speech analytics config for ${e} coming soon`,"info")}function yo(e){confirm(`Delete speech analytics config for extension ${e}?`)&&i(`Delete speech analytics config for ${e} coming soon`,"info")}window.loadE911Sites=ao;window.loadExtensionLocations=io;window.loadLocationHistory=co;window.showAddE911SiteModal=lo;window.editE911Site=uo;window.deleteE911Site=mo;window.showUpdateLocationModal=go;window.updateExtensionLocation=fo;window.showAddSpeechAnalyticsConfigModal=po;window.editSpeechAnalyticsConfig=bo;window.deleteSpeechAnalyticsConfig=yo;window.fetchWithTimeout=g;window.getAuthHeaders=d;window.getApiBaseUrl=u;window.DEFAULT_FETCH_TIMEOUT=K;window.store=_;window.showNotification=i;window.displayError=E;window.setSuppressErrorNotifications=Xe;window.showTab=$;window.switchTab=$;window.initializeTabs=le;window.escapeHtml=c;window.copyToClipboard=Ye;window.formatDate=X;window.truncate=ee;window.getDuration=te;window.getStatusBadge=ne;window.getHealthBadge=oe;window.getPriorityBadge=se;window.getQualityClass=re;window.getScheduleDescription=ae;window.downloadLicense=ie;window.executeBatched=H;window.refreshAllData=j;const T="/admin/login.html";async function wo(){if(debugLog("Initializing user context..."),!localStorage.getItem("pbx_token")){debugLog("No authentication token found, redirecting to login..."),window.location.replace(T);return}try{const r=await g(`${u()}/api/extensions`,{headers:d()},5e3);if(r.status===401||r.status===403){debugLog("Authentication token is invalid, redirecting to login..."),localStorage.removeItem("pbx_token"),localStorage.removeItem("pbx_extension"),localStorage.removeItem("pbx_is_admin"),localStorage.removeItem("pbx_name"),window.location.replace(T);return}if(!r.ok)throw new Error(`HTTP ${r.status}`)}catch(r){console.error("Error verifying authentication:",r),i("Unable to verify authentication - server may be starting up","error")}const t=localStorage.getItem("pbx_extension"),n=localStorage.getItem("pbx_is_admin")==="true",o=localStorage.getItem("pbx_name")||"User";if(!t){debugLog("No extension number found, redirecting to login..."),window.location.replace(T);return}_.set("currentUser",{number:t,is_admin:n,name:o}),debugLog("User context initialized:",{number:t,is_admin:n,name:o}),n?(debugLog("Admin user - showing dashboard tab"),$("dashboard")):(debugLog("Regular user - showing webrtc-phone tab"),$("webrtc-phone")),debugLog("User context initialization complete")}function ho(){const e=document.querySelectorAll("form[data-ajax]");for(const t of e)t.addEventListener("submit",n=>{n.preventDefault(),debugLog("Ajax form submitted:",t.id)})}function Eo(){const e=document.getElementById("logout-button");e&&e.addEventListener("click",async()=>{const t=localStorage.getItem("pbx_token");localStorage.removeItem("pbx_token"),localStorage.removeItem("pbx_extension"),localStorage.removeItem("pbx_is_admin"),localStorage.removeItem("pbx_name"),localStorage.removeItem("pbx_current_extension");try{t&&await fetch(`${u()}/api/auth/logout`,{method:"POST",headers:d()})}catch(n){console.error("Logout API error:",n)}window.location.href=T})}async function Y(){const e=document.getElementById("connection-status");if(!e){console.error("Connection status badge element not found");return}try{if((await g(`${u()}/api/status`,{headers:d()},5e3)).ok)e.textContent="Connected",e.classList.remove("disconnected"),e.classList.add("connected");else throw new Error("Connection failed")}catch(t){console.error("Connection check failed:",t),e.textContent="Disconnected",e.classList.remove("connected"),e.classList.add("disconnected")}}document.addEventListener("DOMContentLoaded",async()=>{debugLog("DOMContentLoaded event fired - starting initialization"),await wo(),debugLog("User context initialization awaited"),debugLog("Initializing tabs, forms, and logout"),le(),ho(),Eo(),rt(),Y(),setInterval(Y,1e4),debugLog("Page initialization complete")});
