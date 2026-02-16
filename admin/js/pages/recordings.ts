/**
 * Recordings page module.
 * Handles fraud alerts, blocked patterns, callback queue, mobile push devices,
 * test notifications, recording announcements, speech analytics configs,
 * and CRM activity log.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';
import { escapeHtml } from '../utils/html.ts';

// --- Interfaces ---

interface FraudAlert {
    timestamp: string;
    extension: string;
    alert_types?: string[];
    fraud_score: number;
    details?: string;
}

interface BlockedPattern {
    pattern: string;
    reason: string;
}

interface FraudStatistics {
    total_alerts?: number;
    high_risk_alerts?: number;
    blocked_patterns_count?: number;
    extensions_flagged?: number;
    blocked_patterns?: BlockedPattern[];
}

interface FraudAlertsResponse {
    alerts?: FraudAlert[];
}

interface CallbackEntry {
    callback_id: string;
    queue_id: string;
    caller_number: string;
    caller_name?: string;
    requested_at: string;
    callback_time: string;
    status: string;
    attempts: number;
}

interface CallbackStatistics {
    total_callbacks?: number;
    status_breakdown?: {
        scheduled?: number;
        in_progress?: number;
        completed?: number;
        failed?: number;
    };
}

interface CallbackListResponse {
    callbacks?: CallbackEntry[];
}

interface CallbackRequestData {
    queue_id: string;
    caller_number: string;
    caller_name?: string;
    preferred_time?: string;
}

interface MobilePushDevice {
    user_id: string;
    platform: string;
    registered_at: string;
    last_seen: string;
}

interface MobilePushStatistics {
    total_devices?: number;
    total_users?: number;
    platforms?: {
        ios?: number;
        android?: number;
    };
    recent_notifications?: number;
}

interface PushNotificationHistory {
    user_id: string;
    title: string;
    body: string;
    sent_at: string;
    success_count?: number;
    failure_count?: number;
}

interface MobilePushDevicesResponse {
    devices?: MobilePushDevice[];
}

interface MobilePushHistoryResponse {
    history?: PushNotificationHistory[];
}

interface RecordingAnnouncementsStats {
    enabled?: boolean;
    announcements_played?: number;
    consent_accepted?: number;
    consent_declined?: number;
    announcement_type?: string;
    require_consent?: boolean;
}

interface RecordingAnnouncementsConfig {
    audio_path?: string;
    announcement_text?: string;
}

interface SpeechAnalyticsConfig {
    extension: string;
    transcription_enabled?: boolean;
    sentiment_enabled?: boolean;
    summarization_enabled?: boolean;
}

interface SpeechAnalyticsConfigsResponse {
    configs?: SpeechAnalyticsConfig[];
}

interface CRMActivity {
    timestamp: string;
    integration: string;
    action: string;
    status: string;
    details?: string;
}

interface CRMActivityLogResponse {
    activities?: CRMActivity[];
}

interface ApiResponse {
    success?: boolean;
    error?: string;
    deleted_count?: number;
    caller_number?: string;
    stub_mode?: boolean;
    success_count?: number;
    failure_count?: number;
}

// --- Fraud Alerts ---

export async function loadFraudAlerts(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const [alertsRes, statsRes] = await Promise.all([
            fetchWithTimeout(`${API_BASE}/api/fraud-detection/alerts?hours=24`, {
                headers: getAuthHeaders()
            }),
            fetchWithTimeout(`${API_BASE}/api/fraud-detection/statistics`, {
                headers: getAuthHeaders()
            })
        ]);
        const [alertsData, statsData]: [FraudAlertsResponse, FraudStatistics] =
            await Promise.all([alertsRes.json(), statsRes.json()]);

        // Update stats
        if (statsData) {
            const el = (id: string): HTMLElement | null => document.getElementById(id);
            if (el('fraud-total-alerts')) {
                (el('fraud-total-alerts') as HTMLElement).textContent =
                    String(statsData.total_alerts ?? 0);
            }
            if (el('fraud-high-risk')) {
                (el('fraud-high-risk') as HTMLElement).textContent =
                    String(statsData.high_risk_alerts ?? 0);
            }
            if (el('fraud-blocked-patterns')) {
                (el('fraud-blocked-patterns') as HTMLElement).textContent =
                    String(statsData.blocked_patterns_count ?? 0);
            }
            if (el('fraud-extensions-flagged')) {
                (el('fraud-extensions-flagged') as HTMLElement).textContent =
                    String(statsData.extensions_flagged ?? 0);
            }
        }

        // Update alerts table
        if (alertsData?.alerts) {
            const tbody = document.getElementById('fraud-alerts-list') as HTMLElement | null;
            if (tbody) {
                if (alertsData.alerts.length === 0) {
                    tbody.innerHTML =
                        '<tr><td colspan="5" style="text-align: center;">No fraud alerts detected</td></tr>';
                } else {
                    tbody.innerHTML = alertsData.alerts.map((alert: FraudAlert) => {
                        const timestamp = new Date(alert.timestamp).toLocaleString();
                        const scoreColor = alert.fraud_score > 0.8
                            ? '#ef4444'
                            : alert.fraud_score > 0.5
                                ? '#f59e0b'
                                : '#10b981';
                        const scorePercent = (alert.fraud_score * 100).toFixed(0);
                        const alertTypes = (alert.alert_types ?? []).join(', ');

                        return `
                            <tr>
                                <td><small>${escapeHtml(timestamp)}</small></td>
                                <td><strong>${escapeHtml(alert.extension)}</strong></td>
                                <td><small>${escapeHtml(alertTypes)}</small></td>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 5px;">
                                        <div style="flex: 1; background: #e5e7eb; border-radius: 4px; height: 20px; overflow: hidden;">
                                            <div style="background: ${scoreColor}; height: 100%; width: ${scorePercent}%;"></div>
                                        </div>
                                        <span>${scorePercent}%</span>
                                    </div>
                                </td>
                                <td><small>${escapeHtml(alert.details ?? 'No details')}</small></td>
                            </tr>
                        `;
                    }).join('');
                }
            }
        }

        // Load blocked patterns from statistics response
        if (statsData?.blocked_patterns) {
            const tbody = document.getElementById('blocked-patterns-list') as HTMLElement | null;
            if (tbody) {
                if (statsData.blocked_patterns.length === 0) {
                    tbody.innerHTML =
                        '<tr><td colspan="3" style="text-align: center;">No blocked patterns</td></tr>';
                } else {
                    tbody.innerHTML = statsData.blocked_patterns.map(
                        (pattern: BlockedPattern, index: number) => `
                        <tr>
                            <td><code>${escapeHtml(pattern.pattern)}</code></td>
                            <td>${escapeHtml(pattern.reason)}</td>
                            <td>
                                <button class="btn-small btn-danger" onclick="deleteBlockedPattern(${index}, '${escapeHtml(pattern.pattern)}')">Delete</button>
                            </td>
                        </tr>
                    `).join('');
                }
            }
        }
    } catch (error: unknown) {
        console.error('Error loading fraud detection data:', error);
        showNotification('Error loading fraud detection data', 'error');
    }
}

export function showAddBlockedPatternModal(): void {
    const modal = document.getElementById('add-blocked-pattern-modal') as HTMLElement | null;
    if (modal) {
        modal.style.display = 'block';
    }
}

export function closeAddBlockedPatternModal(): void {
    const modal = document.getElementById('add-blocked-pattern-modal') as HTMLElement | null;
    if (modal) {
        modal.style.display = 'none';
    }
    const form = document.getElementById('add-blocked-pattern-form') as HTMLFormElement | null;
    if (form) {
        form.reset();
    }
}

export async function addBlockedPattern(event: Event): Promise<void> {
    event.preventDefault();

    const patternInput = document.getElementById('blocked-pattern') as HTMLInputElement | null;
    const reasonInput = document.getElementById('blocked-reason') as HTMLInputElement | null;
    const pattern = patternInput?.value ?? '';
    const reason = reasonInput?.value ?? '';

    // Client-side validation: test if pattern is a valid regex
    try {
        new RegExp(pattern);
    } catch (e: unknown) {
        const message = e instanceof Error ? e.message : String(e);
        showNotification(`Invalid regex pattern: ${message}`, 'error');
        return;
    }

    const patternData = {
        pattern: pattern,
        reason: reason
    };

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/fraud-detection/blocked-pattern`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(patternData)
        });
        const data: ApiResponse = await response.json();
        if (data.success) {
            showNotification('Blocked pattern added successfully', 'success');
            closeAddBlockedPatternModal();
            loadFraudAlerts();
        } else {
            showNotification(data.error ?? 'Error adding blocked pattern', 'error');
        }
    } catch (error: unknown) {
        console.error('Error adding blocked pattern:', error);
        showNotification('Error adding blocked pattern', 'error');
    }
}

export async function deleteBlockedPattern(
    patternIndex: number,
    pattern: string
): Promise<void> {
    if (!confirm(`Are you sure you want to unblock pattern "${pattern}"?`)) {
        return;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/fraud-detection/blocked-pattern/${patternIndex}`,
            { method: 'DELETE', headers: getAuthHeaders() }
        );
        const data: ApiResponse = await response.json();
        if (data.success) {
            showNotification('Blocked pattern removed', 'success');
            loadFraudAlerts();
        } else {
            showNotification(data.error ?? 'Error removing blocked pattern', 'error');
        }
    } catch (error: unknown) {
        console.error('Error removing blocked pattern:', error);
        showNotification('Error removing blocked pattern', 'error');
    }
}

// --- Callback Queue ---

export async function loadCallbackQueue(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const [listRes, statsRes] = await Promise.all([
            fetchWithTimeout(`${API_BASE}/api/callback-queue/list`, {
                headers: getAuthHeaders()
            }),
            fetchWithTimeout(`${API_BASE}/api/callback-queue/statistics`, {
                headers: getAuthHeaders()
            })
        ]);
        const [listData, statsData]: [CallbackListResponse, CallbackStatistics] =
            await Promise.all([listRes.json(), statsRes.json()]);

        // Update statistics
        if (statsData) {
            const el = (id: string): HTMLElement | null => document.getElementById(id);
            if (el('callback-total')) {
                (el('callback-total') as HTMLElement).textContent =
                    String(statsData.total_callbacks ?? 0);
            }

            const statusBreakdown = statsData.status_breakdown ?? {};
            if (el('callback-scheduled')) {
                (el('callback-scheduled') as HTMLElement).textContent =
                    String(statusBreakdown.scheduled ?? 0);
            }
            if (el('callback-in-progress')) {
                (el('callback-in-progress') as HTMLElement).textContent =
                    String(statusBreakdown.in_progress ?? 0);
            }
            if (el('callback-completed')) {
                (el('callback-completed') as HTMLElement).textContent =
                    String(statusBreakdown.completed ?? 0);
            }
            if (el('callback-failed')) {
                (el('callback-failed') as HTMLElement).textContent =
                    String(statusBreakdown.failed ?? 0);
            }
        }

        // Update callback list table
        if (listData?.callbacks) {
            const tbody = document.getElementById('callback-list') as HTMLElement | null;
            if (tbody) {
                if (listData.callbacks.length === 0) {
                    tbody.innerHTML =
                        '<tr><td colspan="8" style="text-align: center;">No callbacks in queue</td></tr>';
                } else {
                    tbody.innerHTML = listData.callbacks.map((callback: CallbackEntry) => {
                        const requestedTime = new Date(callback.requested_at).toLocaleString();
                        const callbackTime = new Date(callback.callback_time).toLocaleString();

                        let statusClass = '';
                        switch (callback.status) {
                            case 'scheduled': statusClass = 'badge-info'; break;
                            case 'in_progress': statusClass = 'badge-warning'; break;
                            case 'completed': statusClass = 'badge-success'; break;
                            case 'failed': statusClass = 'badge-danger'; break;
                            case 'cancelled': statusClass = 'badge-secondary'; break;
                            default: statusClass = 'badge-info';
                        }

                        return `
                            <tr>
                                <td><code>${escapeHtml(callback.callback_id)}</code></td>
                                <td>${escapeHtml(callback.queue_id)}</td>
                                <td>
                                    <strong>${escapeHtml(callback.caller_number)}</strong><br>
                                    <small>${escapeHtml(callback.caller_name ?? 'N/A')}</small>
                                </td>
                                <td><small>${escapeHtml(requestedTime)}</small></td>
                                <td><small>${escapeHtml(callbackTime)}</small></td>
                                <td><span class="badge ${statusClass}">${escapeHtml(callback.status)}</span></td>
                                <td>${callback.attempts}</td>
                                <td>
                                    ${callback.status === 'scheduled' ? `
                                        <button class="btn-small btn-primary" onclick="startCallback('${escapeHtml(callback.callback_id)}')">Start</button>
                                        <button class="btn-small btn-danger" onclick="cancelCallback('${escapeHtml(callback.callback_id)}')">Cancel</button>
                                    ` : callback.status === 'in_progress' ? `
                                        <button class="btn-small btn-success" onclick="completeCallback('${escapeHtml(callback.callback_id)}', true)">Done</button>
                                        <button class="btn-small btn-warning" onclick="completeCallback('${escapeHtml(callback.callback_id)}', false)">Retry</button>
                                    ` : '-'}
                                </td>
                            </tr>
                        `;
                    }).join('');
                }
            }
        }
    } catch (error: unknown) {
        console.error('Error loading callback queue:', error);
        showNotification('Error loading callback queue', 'error');
    }
}

export function showRequestCallbackModal(): void {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'request-callback-modal';
    modal.innerHTML = `
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
    `;
    document.body.appendChild(modal);
    modal.style.display = 'block';
}

export function closeRequestCallbackModal(): void {
    const modal = document.getElementById('request-callback-modal');
    if (modal) {
        modal.remove();
    }
}

export async function requestCallback(event: Event): Promise<void> {
    event.preventDefault();

    const queueId = (document.getElementById('callback-queue-id') as HTMLInputElement | null)?.value ?? '';
    const callerNumber = (document.getElementById('callback-caller-number') as HTMLInputElement | null)?.value ?? '';
    const callerName = (document.getElementById('callback-caller-name') as HTMLInputElement | null)?.value ?? '';
    const preferredTime = (document.getElementById('callback-preferred-time') as HTMLInputElement | null)?.value ?? '';

    const callbackData: CallbackRequestData = {
        queue_id: queueId,
        caller_number: callerNumber
    };

    if (callerName) {
        callbackData.caller_name = callerName;
    }

    if (preferredTime) {
        callbackData.preferred_time = new Date(preferredTime).toISOString();
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/callback-queue/request`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(callbackData)
        });
        const data: ApiResponse = await response.json();
        if (data.success) {
            showNotification('Callback requested successfully', 'success');
            closeRequestCallbackModal();
            loadCallbackQueue();
        } else {
            showNotification(data.error ?? 'Error requesting callback', 'error');
        }
    } catch (error: unknown) {
        console.error('Error requesting callback:', error);
        showNotification('Error requesting callback', 'error');
    }
}

export async function startCallback(callbackId: string): Promise<void> {
    const agentId = prompt('Enter your agent ID/extension:');
    if (!agentId) {
        return;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/callback-queue/start`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                callback_id: callbackId,
                agent_id: agentId
            })
        });
        const data: ApiResponse = await response.json();
        if (data.success) {
            showNotification(`Started callback to ${data.caller_number ?? callbackId}`, 'success');
            loadCallbackQueue();
        } else {
            showNotification(data.error ?? 'Error starting callback', 'error');
        }
    } catch (error: unknown) {
        console.error('Error starting callback:', error);
        showNotification('Error starting callback', 'error');
    }
}

export async function completeCallback(
    callbackId: string,
    success: boolean
): Promise<void> {
    let notes = '';
    if (!success) {
        notes = prompt('Enter reason for failure (optional):') ?? '';
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/callback-queue/complete`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                callback_id: callbackId,
                success: success,
                notes: notes
            })
        });
        const data: ApiResponse = await response.json();
        if (data.success) {
            showNotification(
                success ? 'Callback completed' : 'Callback will be retried',
                'success'
            );
            loadCallbackQueue();
        } else {
            showNotification(data.error ?? 'Error completing callback', 'error');
        }
    } catch (error: unknown) {
        console.error('Error completing callback:', error);
        showNotification('Error completing callback', 'error');
    }
}

export async function cancelCallback(callbackId: string): Promise<void> {
    if (!confirm('Are you sure you want to cancel this callback request?')) {
        return;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/callback-queue/cancel`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                callback_id: callbackId
            })
        });
        const data: ApiResponse = await response.json();
        if (data.success) {
            showNotification('Callback cancelled', 'success');
            loadCallbackQueue();
        } else {
            showNotification(data.error ?? 'Error cancelling callback', 'error');
        }
    } catch (error: unknown) {
        console.error('Error cancelling callback:', error);
        showNotification('Error cancelling callback', 'error');
    }
}

// --- Mobile Push Notifications ---

export async function loadMobilePushDevices(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const [devicesRes, statsRes, historyRes] = await Promise.all([
            fetchWithTimeout(`${API_BASE}/api/mobile-push/devices`, {
                headers: getAuthHeaders()
            }),
            fetchWithTimeout(`${API_BASE}/api/mobile-push/statistics`, {
                headers: getAuthHeaders()
            }),
            fetchWithTimeout(`${API_BASE}/api/mobile-push/history`, {
                headers: getAuthHeaders()
            })
        ]);
        const [devicesData, statsData, historyData]: [
            MobilePushDevicesResponse,
            MobilePushStatistics,
            MobilePushHistoryResponse
        ] = await Promise.all([devicesRes.json(), statsRes.json(), historyRes.json()]);

        // Update statistics
        if (statsData) {
            const el = (id: string): HTMLElement | null => document.getElementById(id);
            if (el('push-total-devices')) {
                (el('push-total-devices') as HTMLElement).textContent =
                    String(statsData.total_devices ?? 0);
            }
            if (el('push-total-users')) {
                (el('push-total-users') as HTMLElement).textContent =
                    String(statsData.total_users ?? 0);
            }

            const platforms = statsData.platforms ?? {};
            if (el('push-ios-devices')) {
                (el('push-ios-devices') as HTMLElement).textContent =
                    String(platforms.ios ?? 0);
            }
            if (el('push-android-devices')) {
                (el('push-android-devices') as HTMLElement).textContent =
                    String(platforms.android ?? 0);
            }
            if (el('push-recent-notifications')) {
                (el('push-recent-notifications') as HTMLElement).textContent =
                    String(statsData.recent_notifications ?? 0);
            }
        }

        // Update devices table
        if (devicesData?.devices) {
            const tbody = document.getElementById('mobile-devices-list') as HTMLElement | null;
            if (tbody) {
                if (devicesData.devices.length === 0) {
                    tbody.innerHTML =
                        '<tr><td colspan="5" style="text-align: center;">No devices registered</td></tr>';
                } else {
                    tbody.innerHTML = devicesData.devices.map((device: MobilePushDevice) => {
                        const registeredTime = new Date(device.registered_at).toLocaleString();
                        const lastSeenTime = new Date(device.last_seen).toLocaleString();

                        let platformBadge = '';
                        if (device.platform === 'ios') {
                            platformBadge = '<span class="badge badge-info">iOS</span>';
                        } else if (device.platform === 'android') {
                            platformBadge = '<span class="badge badge-success">Android</span>';
                        } else {
                            platformBadge = `<span class="badge badge-secondary">${escapeHtml(device.platform)}</span>`;
                        }

                        return `
                            <tr>
                                <td><strong>${escapeHtml(device.user_id)}</strong></td>
                                <td>${platformBadge}</td>
                                <td><small>${escapeHtml(registeredTime)}</small></td>
                                <td><small>${escapeHtml(lastSeenTime)}</small></td>
                                <td>
                                    <button class="btn-small btn-primary" onclick="sendTestNotification('${escapeHtml(device.user_id)}')">Test</button>
                                </td>
                            </tr>
                        `;
                    }).join('');
                }
            }
        }

        // Update history table
        if (historyData?.history) {
            const tbody = document.getElementById('push-history-list') as HTMLElement | null;
            if (tbody) {
                if (historyData.history.length === 0) {
                    tbody.innerHTML =
                        '<tr><td colspan="5" style="text-align: center;">No notifications sent</td></tr>';
                } else {
                    tbody.innerHTML = historyData.history.slice(0, 50).map(
                        (notif: PushNotificationHistory) => {
                            const sentTime = new Date(notif.sent_at).toLocaleString();
                            const successCount = notif.success_count ?? 0;
                            const failureCount = notif.failure_count ?? 0;

                            return `
                                <tr>
                                    <td>${escapeHtml(notif.user_id)}</td>
                                    <td><strong>${escapeHtml(notif.title)}</strong></td>
                                    <td><small>${escapeHtml(notif.body)}</small></td>
                                    <td><small>${escapeHtml(sentTime)}</small></td>
                                    <td>
                                        <span class="badge badge-success">${successCount} sent</span>
                                        ${failureCount > 0 ? `<span class="badge badge-danger">${failureCount} failed</span>` : ''}
                                    </td>
                                </tr>
                            `;
                        }).join('');
                }
            }
        }
    } catch (error: unknown) {
        console.error('Error loading mobile push data:', error);
        showNotification('Error loading mobile push data', 'error');
    }
}

export function showRegisterDeviceModal(): void {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'register-device-modal';
    modal.innerHTML = `
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
    `;
    document.body.appendChild(modal);
    modal.style.display = 'block';
}

export function closeRegisterDeviceModal(): void {
    const modal = document.getElementById('register-device-modal');
    if (modal) {
        modal.remove();
    }
}

export async function registerDevice(event: Event): Promise<void> {
    event.preventDefault();

    const userId = (document.getElementById('device-user-id') as HTMLInputElement | null)?.value ?? '';
    const deviceToken = (document.getElementById('device-token') as HTMLTextAreaElement | null)?.value.trim() ?? '';
    const platform = (document.getElementById('device-platform') as HTMLSelectElement | null)?.value ?? '';

    const deviceData = {
        user_id: userId,
        device_token: deviceToken,
        platform: platform
    };

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/mobile-push/register`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(deviceData)
        });
        const data: ApiResponse = await response.json();
        if (data.success) {
            showNotification('Device registered successfully', 'success');
            closeRegisterDeviceModal();
            loadMobilePushDevices();
        } else {
            showNotification(data.error ?? 'Error registering device', 'error');
        }
    } catch (error: unknown) {
        console.error('Error registering device:', error);
        showNotification('Error registering device', 'error');
    }
}

// --- Test Notification ---

export function showTestNotificationModal(): void {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'test-notification-modal';
    modal.innerHTML = `
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
    `;
    document.body.appendChild(modal);
    modal.style.display = 'block';
}

export function closeTestNotificationModal(): void {
    const modal = document.getElementById('test-notification-modal');
    if (modal) {
        modal.remove();
    }
}

export function sendTestNotificationForm(event: Event): void {
    event.preventDefault();
    const userId = (document.getElementById('test-user-id') as HTMLInputElement | null)?.value ?? '';
    sendTestNotification(userId);
    closeTestNotificationModal();
}

export async function sendTestNotification(userId: string): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/mobile-push/test`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ user_id: userId })
        });
        const data: ApiResponse = await response.json();
        if (data.success || data.stub_mode) {
            if (data.stub_mode) {
                showNotification(
                    'Test notification logged (Firebase not configured)',
                    'warning'
                );
            } else {
                showNotification(
                    `Test notification sent: ${data.success_count ?? 0} succeeded, ${data.failure_count ?? 0} failed`,
                    'success'
                );
            }
            loadMobilePushDevices();
        } else {
            showNotification(data.error ?? 'Error sending test notification', 'error');
        }
    } catch (error: unknown) {
        console.error('Error sending test notification:', error);
        showNotification('Error sending test notification', 'error');
    }
}

// --- Recording Announcements ---

export async function loadRecordingAnnouncementsStats(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const [statsRes, configRes] = await Promise.all([
            fetchWithTimeout(`${API_BASE}/api/recording-announcements/statistics`, {
                headers: getAuthHeaders()
            }),
            fetchWithTimeout(`${API_BASE}/api/recording-announcements/config`, {
                headers: getAuthHeaders()
            })
        ]);
        const [statsData, configData]: [RecordingAnnouncementsStats, RecordingAnnouncementsConfig] =
            await Promise.all([statsRes.json(), configRes.json()]);

        // Update statistics
        if (statsData) {
            const el = (id: string): HTMLElement | null => document.getElementById(id);
            if (el('announcements-enabled')) {
                (el('announcements-enabled') as HTMLElement).textContent =
                    statsData.enabled ? 'Enabled' : 'Disabled';
            }
            if (el('announcements-played')) {
                (el('announcements-played') as HTMLElement).textContent =
                    String(statsData.announcements_played ?? 0);
            }
            if (el('consent-accepted')) {
                (el('consent-accepted') as HTMLElement).textContent =
                    String(statsData.consent_accepted ?? 0);
            }
            if (el('consent-declined')) {
                (el('consent-declined') as HTMLElement).textContent =
                    String(statsData.consent_declined ?? 0);
            }
            if (el('announcement-type')) {
                (el('announcement-type') as HTMLElement).textContent =
                    statsData.announcement_type ?? 'N/A';
            }
            if (el('require-consent')) {
                (el('require-consent') as HTMLElement).textContent =
                    statsData.require_consent ? 'Yes' : 'No';
            }
        }

        // Update configuration
        if (configData) {
            const el = (id: string): HTMLElement | null => document.getElementById(id);
            if (el('audio-file-path')) {
                (el('audio-file-path') as HTMLElement).textContent =
                    configData.audio_path ?? 'N/A';
            }
            if (el('announcement-text')) {
                (el('announcement-text') as HTMLElement).textContent =
                    configData.announcement_text ?? 'N/A';
            }
        }
    } catch (error: unknown) {
        console.error('Error loading recording announcements data:', error);
        showNotification('Error loading recording announcements data', 'error');
    }
}

// --- Speech Analytics Configs ---

export async function loadSpeechAnalyticsConfigs(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/framework/speech-analytics/configs`,
            { headers: getAuthHeaders() }
        );
        const data: SpeechAnalyticsConfigsResponse = await response.json();
        const tableBody = document.getElementById('speech-analytics-configs-table') as HTMLElement | null;
        if (!tableBody) return;

        if (!data.configs || data.configs.length === 0) {
            tableBody.innerHTML =
                '<tr><td colspan="5" class="loading">No extension-specific configurations. Using system defaults.</td></tr>';
            return;
        }

        tableBody.innerHTML = data.configs.map((config: SpeechAnalyticsConfig) => `
            <tr>
                <td>${escapeHtml(config.extension)}</td>
                <td>${config.transcription_enabled ? 'Enabled' : 'Disabled'}</td>
                <td>${config.sentiment_enabled ? 'Enabled' : 'Disabled'}</td>
                <td>${config.summarization_enabled ? 'Enabled' : 'Disabled'}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editSpeechAnalyticsConfig('${escapeHtml(config.extension)}')">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteSpeechAnalyticsConfig('${escapeHtml(config.extension)}')">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error: unknown) {
        console.error('Error loading speech analytics configs:', error);
        showNotification('Error loading speech analytics configurations', 'error');
    }
}

// --- CRM Activity Log ---

export async function loadCRMActivityLog(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/framework/integrations/activity-log`,
            { headers: getAuthHeaders() }
        );
        if (!response.ok) {
            console.error('Error loading CRM activity log:', response.status);
            showNotification('Error loading CRM activity log', 'error');
            return;
        }
        const data: CRMActivityLogResponse = await response.json();

        const tableBody = document.getElementById('crm-activity-log-table') as HTMLElement | null;
        if (!tableBody) return;

        if (!data.activities || data.activities.length === 0) {
            tableBody.innerHTML =
                '<tr><td colspan="5" class="loading">No integration activity yet</td></tr>';
            return;
        }

        tableBody.innerHTML = data.activities.map((activity: CRMActivity) => {
            const statusClass = activity.status === 'success' ? 'success' : 'error';
            const statusLabel = activity.status === 'success' ? 'OK' : 'FAIL';
            return `
                <tr>
                    <td>${escapeHtml(new Date(activity.timestamp).toLocaleString())}</td>
                    <td>${escapeHtml(activity.integration)}</td>
                    <td>${escapeHtml(activity.action)}</td>
                    <td class="${statusClass}">${statusLabel} ${escapeHtml(activity.status)}</td>
                    <td>${escapeHtml(activity.details ?? '-')}</td>
                </tr>
            `;
        }).join('');
    } catch (error: unknown) {
        console.error('Error loading CRM activity log:', error);
        showNotification('Error loading CRM activity log', 'error');
    }
}

export async function clearCRMActivityLog(): Promise<void> {
    if (!confirm('Clear old activity log entries? This will remove entries older than 30 days.')) {
        return;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/framework/integrations/activity-log/clear`,
            { method: 'POST', headers: getAuthHeaders() }
        );
        const data: ApiResponse = await response.json();
        if (data.success) {
            showNotification(`Cleared ${data.deleted_count ?? 0} old entries`, 'success');
            loadCRMActivityLog();
        } else {
            showNotification(data.error ?? 'Error clearing activity log', 'error');
        }
    } catch (error: unknown) {
        console.error('Error clearing CRM activity log:', error);
        showNotification('Error clearing activity log', 'error');
    }
}

// Backward compatibility
window.loadFraudAlerts = loadFraudAlerts;
window.showAddBlockedPatternModal = showAddBlockedPatternModal;
window.closeAddBlockedPatternModal = closeAddBlockedPatternModal;
window.addBlockedPattern = addBlockedPattern;
window.deleteBlockedPattern = deleteBlockedPattern;
window.loadCallbackQueue = loadCallbackQueue;
window.showRequestCallbackModal = showRequestCallbackModal;
window.closeRequestCallbackModal = closeRequestCallbackModal;
window.requestCallback = requestCallback;
window.startCallback = startCallback;
window.completeCallback = completeCallback;
window.cancelCallback = cancelCallback;
window.loadMobilePushDevices = loadMobilePushDevices;
window.showRegisterDeviceModal = showRegisterDeviceModal;
window.closeRegisterDeviceModal = closeRegisterDeviceModal;
window.registerDevice = registerDevice;
window.showTestNotificationModal = showTestNotificationModal;
window.closeTestNotificationModal = closeTestNotificationModal;
window.sendTestNotificationForm = sendTestNotificationForm;
window.sendTestNotification = sendTestNotification;
window.loadRecordingAnnouncementsStats = loadRecordingAnnouncementsStats;
window.loadSpeechAnalyticsConfigs = loadSpeechAnalyticsConfigs;
window.loadCRMActivityLog = loadCRMActivityLog;
window.clearCRMActivityLog = clearCRMActivityLog;
