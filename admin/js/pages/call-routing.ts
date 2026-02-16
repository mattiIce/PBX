/**
 * Call Routing page module.
 * Handles Find Me/Follow Me, time-based routing, webhooks, hot desking,
 * recording retention, and callback queue management.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';
import { escapeHtml } from '../utils/html.ts';

// ---------------------------------------------------------------------------
// Interfaces
// ---------------------------------------------------------------------------

interface FMFMDestination {
    number: string;
    ring_time?: number;
}

interface FMFMConfig {
    extension: string;
    mode: string;
    enabled?: boolean;
    destinations?: FMFMDestination[];
    no_answer_destination?: string;
    updated_at?: string;
}

interface FMFMExtensionsResponse {
    extensions?: FMFMConfig[];
    count?: number;
}

interface TimeConditions {
    days_of_week?: number[];
    start_time?: string;
    end_time?: string;
    holidays?: boolean;
}

interface TimeRoutingRule {
    rule_id: string;
    name: string;
    destination: string;
    route_to: string;
    time_conditions?: TimeConditions;
    priority?: number;
    enabled?: boolean;
}

interface TimeRoutingRulesResponse {
    rules?: TimeRoutingRule[];
    count?: number;
}

interface Webhook {
    url: string;
    event_types?: string[];
    secret?: string;
    enabled?: boolean;
}

interface WebhooksResponse {
    subscriptions?: Webhook[];
}

interface HotDeskSession {
    extension: string;
    device_mac?: string;
    device_ip?: string;
    login_time?: string;
    active?: boolean;
}

interface HotDeskSessionsResponse {
    sessions?: HotDeskSession[];
}

interface RetentionPolicy {
    policy_id: string;
    name: string;
    retention_days: number;
    tags?: string[];
    created_at?: string;
}

interface RetentionPoliciesResponse {
    policies?: RetentionPolicy[];
}

interface RetentionStatisticsResponse {
    total_policies?: number;
    total_recordings?: number;
    deleted_count?: number;
    last_cleanup?: string;
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

interface CallbackListResponse {
    callbacks?: CallbackEntry[];
}

interface CallbackStatisticsResponse {
    total_callbacks?: number;
    status_breakdown?: Record<string, number>;
}

interface ApiSuccessResponse {
    success: boolean;
    error?: string;
    caller_number?: string;
}

// ---------------------------------------------------------------------------
// Module state
// ---------------------------------------------------------------------------

let fmfmDestinationCounter = 0;

// ---------------------------------------------------------------------------
// Find Me / Follow Me
// ---------------------------------------------------------------------------

export async function loadFMFMExtensions(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/fmfm/extensions`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: FMFMExtensionsResponse = await response.json();
        if (data.extensions) {
            // Update stats
            const totalEl = document.getElementById('fmfm-total-extensions') as HTMLElement | null;
            if (totalEl) totalEl.textContent = String(data.count || 0);

            const sequentialCount = data.extensions.filter(e => e.mode === 'sequential').length;
            const simultaneousCount = data.extensions.filter(e => e.mode === 'simultaneous').length;
            const enabledCount = data.extensions.filter(e => e.enabled !== false).length;

            const seqEl = document.getElementById('fmfm-sequential') as HTMLElement | null;
            if (seqEl) seqEl.textContent = String(sequentialCount);

            const simEl = document.getElementById('fmfm-simultaneous') as HTMLElement | null;
            if (simEl) simEl.textContent = String(simultaneousCount);

            const activeEl = document.getElementById('fmfm-active-count') as HTMLElement | null;
            if (activeEl) activeEl.textContent = String(enabledCount);

            // Update table
            const tbody = document.getElementById('fmfm-list') as HTMLElement | null;
            if (!tbody) return;

            if (data.extensions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No Find Me/Follow Me configurations</td></tr>';
            } else {
                tbody.innerHTML = data.extensions.map(config => {
                    const enabled = config.enabled !== false;
                    const modeBadge = config.mode === 'sequential'
                        ? '<span class="badge" style="background: #3b82f6;">Sequential</span>'
                        : '<span class="badge" style="background: #10b981;">Simultaneous</span>';
                    const statusBadge = enabled
                        ? '<span class="badge" style="background: #10b981;">Active</span>'
                        : '<span class="badge" style="background: #6b7280;">Disabled</span>';

                    const destinations = config.destinations || [];
                    const destList = destinations.map(d =>
                        `${escapeHtml(d.number)}${d.ring_time ? ` (${d.ring_time}s)` : ''}`
                    ).join(', ');

                    const updated = config.updated_at ? new Date(config.updated_at).toLocaleString() : 'N/A';

                    return `
                        <tr>
                            <td><strong>${escapeHtml(config.extension)}</strong></td>
                            <td>${modeBadge}</td>
                            <td>
                                <div style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(destList)}">
                                    ${destinations.length} destination(s): ${escapeHtml(destList) || 'None'}
                                </div>
                            </td>
                            <td>${statusBadge}</td>
                            <td><small>${updated}</small></td>
                            <td>
                                <button class="btn-small btn-primary" data-config='${escapeHtml(JSON.stringify(config))}' onclick="editFMFMConfig(JSON.parse(this.getAttribute('data-config')))">Edit</button>
                                <button class="btn-small btn-danger" onclick="deleteFMFMConfig('${escapeHtml(config.extension)}')">Delete</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
    } catch (error: unknown) {
        console.error('Error loading FMFM extensions:', error);
        showNotification('Error loading FMFM configurations', 'error');
    }
}

export function showAddFMFMModal(): void {
    const modal = document.getElementById('add-fmfm-modal') as HTMLElement | null;
    if (modal) modal.style.display = 'block';

    const extInput = document.getElementById('fmfm-extension') as HTMLInputElement | null;
    if (extInput) {
        extInput.value = '';
        extInput.readOnly = false;
    }

    const modeSelect = document.getElementById('fmfm-mode') as HTMLSelectElement | null;
    if (modeSelect) modeSelect.value = 'sequential';

    const enabledCheck = document.getElementById('fmfm-enabled') as HTMLInputElement | null;
    if (enabledCheck) enabledCheck.checked = true;

    const noAnswerInput = document.getElementById('fmfm-no-answer') as HTMLInputElement | null;
    if (noAnswerInput) noAnswerInput.value = '';

    const destContainer = document.getElementById('fmfm-destinations-list') as HTMLElement | null;
    if (destContainer) destContainer.innerHTML = '';

    addFMFMDestinationRow();
}

export function closeAddFMFMModal(): void {
    const modal = document.getElementById('add-fmfm-modal') as HTMLElement | null;
    if (modal) modal.style.display = 'none';
    const form = document.getElementById('add-fmfm-form') as HTMLFormElement | null;
    if (form) form.reset();
}

export function addFMFMDestinationRow(): void {
    const container = document.getElementById('fmfm-destinations-list') as HTMLElement | null;
    if (!container) return;

    const rowId = `fmfm-dest-${fmfmDestinationCounter++}`;

    const row = document.createElement('div');
    row.id = rowId;
    row.style.cssText = 'display: flex; gap: 10px; margin-bottom: 10px; align-items: center;';
    row.innerHTML = `
        <input type="text" class="fmfm-dest-number" placeholder="Phone number or extension" required style="flex: 2;">
        <input type="number" class="fmfm-dest-ringtime" placeholder="Ring time (s)" value="20" min="5" max="120" style="flex: 1;">
        <button type="button" class="btn-small btn-danger" onclick="document.getElementById('${rowId}').remove()">Remove</button>
    `;
    container.appendChild(row);
}

export async function saveFMFMConfig(event: Event): Promise<void> {
    event.preventDefault();

    const extension = (document.getElementById('fmfm-extension') as HTMLInputElement).value;
    const mode = (document.getElementById('fmfm-mode') as HTMLSelectElement).value;
    const enabled = (document.getElementById('fmfm-enabled') as HTMLInputElement).checked;
    const noAnswer = (document.getElementById('fmfm-no-answer') as HTMLInputElement).value;

    // Collect destinations
    const destNumbers = Array.from(document.querySelectorAll<HTMLInputElement>('.fmfm-dest-number'));
    const destRingTimes = Array.from(document.querySelectorAll<HTMLInputElement>('.fmfm-dest-ringtime'));

    const destinations: FMFMDestination[] = destNumbers.map((input, idx) => ({
        number: input.value,
        ring_time: parseInt(destRingTimes[idx].value) || 20
    })).filter(d => d.number);

    if (destinations.length === 0) {
        showNotification('At least one destination is required', 'error');
        return;
    }

    const configData: Record<string, unknown> = {
        extension: extension,
        mode: mode,
        enabled: enabled,
        destinations: destinations
    };

    if (noAnswer) {
        configData.no_answer_destination = noAnswer;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/fmfm/config`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(configData)
        });

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification(`FMFM configured for extension ${extension}`, 'success');
            closeAddFMFMModal();
            loadFMFMExtensions();
        } else {
            showNotification(data.error || 'Error configuring FMFM', 'error');
        }
    } catch (error: unknown) {
        console.error('Error saving FMFM config:', error);
        showNotification('Error saving FMFM configuration', 'error');
    }
}

export function editFMFMConfig(config: FMFMConfig): void {
    showAddFMFMModal();

    const extInput = document.getElementById('fmfm-extension') as HTMLInputElement | null;
    if (extInput) {
        extInput.value = config.extension;
        extInput.readOnly = true;  // Don't allow changing extension
    }

    const modeSelect = document.getElementById('fmfm-mode') as HTMLSelectElement | null;
    if (modeSelect) modeSelect.value = config.mode;

    const enabledCheck = document.getElementById('fmfm-enabled') as HTMLInputElement | null;
    if (enabledCheck) enabledCheck.checked = config.enabled !== false;

    const noAnswerInput = document.getElementById('fmfm-no-answer') as HTMLInputElement | null;
    if (noAnswerInput) noAnswerInput.value = config.no_answer_destination || '';

    // Clear and add destination rows
    const container = document.getElementById('fmfm-destinations-list') as HTMLElement | null;
    if (!container) return;
    container.innerHTML = '';

    if (config.destinations && config.destinations.length > 0) {
        for (const dest of config.destinations) {
            addFMFMDestinationRow();
            const rows = container.children;
            const lastRow = rows[rows.length - 1] as HTMLElement;
            const numberInput = lastRow.querySelector('.fmfm-dest-number') as HTMLInputElement | null;
            if (numberInput) numberInput.value = dest.number;
            const ringInput = lastRow.querySelector('.fmfm-dest-ringtime') as HTMLInputElement | null;
            if (ringInput) ringInput.value = String(dest.ring_time ?? 20);
        }
    } else {
        addFMFMDestinationRow();
    }
}

export async function deleteFMFMConfig(extension: string): Promise<void> {
    if (!confirm(`Are you sure you want to delete FMFM configuration for extension ${extension}?`)) {
        return;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/fmfm/config/${extension}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification(`FMFM configuration deleted for ${extension}`, 'success');
            loadFMFMExtensions();
        } else {
            showNotification(data.error || 'Error deleting FMFM configuration', 'error');
        }
    } catch (error: unknown) {
        console.error('Error deleting FMFM config:', error);
        showNotification('Error deleting FMFM configuration', 'error');
    }
}

// ---------------------------------------------------------------------------
// Time-Based Routing
// ---------------------------------------------------------------------------

export function getScheduleDescription(conditions: TimeConditions): string {
    const parts: string[] = [];

    if (conditions.days_of_week) {
        const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        const days = conditions.days_of_week.map(d => dayNames[d]).join(', ');
        parts.push(days);
    }

    if (conditions.start_time && conditions.end_time) {
        parts.push(`${conditions.start_time}-${conditions.end_time}`);
    }

    if (conditions.holidays === true) {
        parts.push('Holidays');
    } else if (conditions.holidays === false) {
        parts.push('Non-holidays');
    }

    return parts.length > 0 ? parts.join(' | ') : 'Always';
}

export async function loadTimeRoutingRules(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/time-routing/rules`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: TimeRoutingRulesResponse = await response.json();
        if (data.rules) {
            // Update stats
            const totalEl = document.getElementById('time-routing-total') as HTMLElement | null;
            if (totalEl) totalEl.textContent = String(data.count || 0);

            const activeCount = data.rules.filter(r => r.enabled !== false).length;
            const businessCount = data.rules.filter(r =>
                r.name && (r.name.toLowerCase().includes('business') || r.name.toLowerCase().includes('hours'))
            ).length;
            const afterCount = data.rules.filter(r =>
                r.name && (r.name.toLowerCase().includes('after') || r.name.toLowerCase().includes('closed'))
            ).length;

            const activeEl = document.getElementById('time-routing-active') as HTMLElement | null;
            if (activeEl) activeEl.textContent = String(activeCount);

            const businessEl = document.getElementById('time-routing-business') as HTMLElement | null;
            if (businessEl) businessEl.textContent = String(businessCount);

            const afterEl = document.getElementById('time-routing-after') as HTMLElement | null;
            if (afterEl) afterEl.textContent = String(afterCount);

            // Update table
            const tbody = document.getElementById('time-routing-list') as HTMLElement | null;
            if (!tbody) return;

            if (data.rules.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No time-based routing rules</td></tr>';
            } else {
                tbody.innerHTML = data.rules.map(rule => {
                    const enabled = rule.enabled !== false;
                    const statusBadge = enabled
                        ? '<span class="badge" style="background: #10b981;">Active</span>'
                        : '<span class="badge" style="background: #6b7280;">Disabled</span>';

                    const conditions = rule.time_conditions || {};
                    const schedule = getScheduleDescription(conditions);

                    return `
                        <tr>
                            <td><strong>${escapeHtml(rule.name)}</strong></td>
                            <td>${escapeHtml(rule.destination)}</td>
                            <td>${escapeHtml(rule.route_to)}</td>
                            <td><small>${escapeHtml(schedule)}</small></td>
                            <td>${rule.priority || 100}</td>
                            <td>${statusBadge}</td>
                            <td>
                                <button class="btn-small btn-danger" onclick="deleteTimeRoutingRule('${escapeHtml(rule.rule_id)}', '${escapeHtml(rule.name)}')">Delete</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
    } catch (error: unknown) {
        console.error('Error loading time routing rules:', error);
        showNotification('Error loading time routing rules', 'error');
    }
}

export function showAddTimeRuleModal(): void {
    const modal = document.getElementById('add-time-rule-modal') as HTMLElement | null;
    if (modal) modal.style.display = 'block';
}

export function closeAddTimeRuleModal(): void {
    const modal = document.getElementById('add-time-rule-modal') as HTMLElement | null;
    if (modal) modal.style.display = 'none';
    const form = document.getElementById('add-time-rule-form') as HTMLFormElement | null;
    if (form) form.reset();
}

export async function saveTimeRoutingRule(event: Event): Promise<void> {
    event.preventDefault();

    const name = (document.getElementById('time-rule-name') as HTMLInputElement).value;
    const destination = (document.getElementById('time-rule-destination') as HTMLInputElement).value;
    const routeTo = (document.getElementById('time-rule-route-to') as HTMLInputElement).value;
    const startTime = (document.getElementById('time-rule-start') as HTMLInputElement).value;
    const endTime = (document.getElementById('time-rule-end') as HTMLInputElement).value;
    const priority = parseInt((document.getElementById('time-rule-priority') as HTMLInputElement).value);
    const enabled = (document.getElementById('time-rule-enabled') as HTMLInputElement).checked;

    // Collect selected days
    const selectedDays = Array.from(
        document.querySelectorAll<HTMLInputElement>('input[name="time-rule-days"]:checked')
    ).map(cb => parseInt(cb.value));

    if (selectedDays.length === 0) {
        showNotification('Please select at least one day of the week', 'error');
        return;
    }

    const ruleData = {
        name: name,
        destination: destination,
        route_to: routeTo,
        priority: priority,
        enabled: enabled,
        time_conditions: {
            days_of_week: selectedDays,
            start_time: startTime,
            end_time: endTime
        }
    };

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/time-routing/rule`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(ruleData)
        });

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification(`Time routing rule "${name}" added successfully`, 'success');
            closeAddTimeRuleModal();
            loadTimeRoutingRules();
        } else {
            showNotification(data.error || 'Error adding time routing rule', 'error');
        }
    } catch (error: unknown) {
        console.error('Error saving time routing rule:', error);
        showNotification('Error saving time routing rule', 'error');
    }
}

export async function deleteTimeRoutingRule(ruleId: string, ruleName: string): Promise<void> {
    if (!confirm(`Are you sure you want to delete time routing rule "${ruleName}"?`)) {
        return;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/time-routing/rule/${ruleId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification(`Time routing rule "${ruleName}" deleted`, 'success');
            loadTimeRoutingRules();
        } else {
            showNotification(data.error || 'Error deleting time routing rule', 'error');
        }
    } catch (error: unknown) {
        console.error('Error deleting time routing rule:', error);
        showNotification('Error deleting time routing rule', 'error');
    }
}

// ---------------------------------------------------------------------------
// Webhooks
// ---------------------------------------------------------------------------

export async function loadWebhooks(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/webhooks`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: WebhooksResponse = await response.json();
        if (data.subscriptions) {
            const tbody = document.getElementById('webhooks-list') as HTMLElement | null;
            if (!tbody) return;

            if (data.subscriptions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No webhooks configured</td></tr>';
            } else {
                tbody.innerHTML = data.subscriptions.map(webhook => {
                    const enabled = webhook.enabled !== false;
                    const statusBadge = enabled
                        ? '<span class="badge" style="background: #10b981;">Active</span>'
                        : '<span class="badge" style="background: #6b7280;">Disabled</span>';

                    const events = webhook.event_types || [];
                    const eventList = events.join(', ');
                    const hasSecret = webhook.secret ? 'Yes' : 'No';

                    return `
                        <tr>
                            <td>
                                <div style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(webhook.url)}">
                                    ${escapeHtml(webhook.url)}
                                </div>
                            </td>
                            <td>
                                <div style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(eventList)}">
                                    <small>${escapeHtml(eventList)}</small>
                                </div>
                            </td>
                            <td>${hasSecret}</td>
                            <td>${statusBadge}</td>
                            <td>
                                <button class="btn-small btn-danger" onclick="deleteWebhook('${escapeHtml(webhook.url)}')">Delete</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
    } catch (error: unknown) {
        console.error('Error loading webhooks:', error);
        showNotification('Error loading webhooks', 'error');
    }
}

export function showAddWebhookModal(): void {
    const modal = document.getElementById('add-webhook-modal') as HTMLElement | null;
    if (modal) modal.style.display = 'block';
}

export function closeAddWebhookModal(): void {
    const modal = document.getElementById('add-webhook-modal') as HTMLElement | null;
    if (modal) modal.style.display = 'none';
    const form = document.getElementById('add-webhook-form') as HTMLFormElement | null;
    if (form) form.reset();
}

export async function addWebhook(event: Event): Promise<void> {
    event.preventDefault();

    const url = (document.getElementById('webhook-url') as HTMLInputElement).value;
    const secret = (document.getElementById('webhook-secret') as HTMLInputElement).value;
    const enabled = (document.getElementById('webhook-enabled') as HTMLInputElement).checked;

    // Collect selected events
    const selectedEvents = Array.from(
        document.querySelectorAll<HTMLInputElement>('input[name="webhook-events"]:checked')
    ).map(cb => cb.value);

    if (selectedEvents.length === 0) {
        showNotification('Please select at least one event type', 'error');
        return;
    }

    const webhookData: Record<string, unknown> = {
        url: url,
        event_types: selectedEvents,
        enabled: enabled
    };

    if (secret) {
        webhookData.secret = secret;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/webhooks`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(webhookData)
        });

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification('Webhook added successfully', 'success');
            closeAddWebhookModal();
            loadWebhooks();
        } else {
            showNotification(data.error || 'Error adding webhook', 'error');
        }
    } catch (error: unknown) {
        console.error('Error adding webhook:', error);
        showNotification('Error adding webhook', 'error');
    }
}

export async function deleteWebhook(url: string): Promise<void> {
    if (!confirm(`Are you sure you want to delete webhook for ${url}?`)) {
        return;
    }

    const encodedUrl = encodeURIComponent(url);

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/webhooks/${encodedUrl}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification('Webhook deleted', 'success');
            loadWebhooks();
        } else {
            showNotification(data.error || 'Error deleting webhook', 'error');
        }
    } catch (error: unknown) {
        console.error('Error deleting webhook:', error);
        showNotification('Error deleting webhook', 'error');
    }
}

// ---------------------------------------------------------------------------
// Hot Desking
// ---------------------------------------------------------------------------

export function getDuration(startTime: Date): string {
    const now = new Date();
    const diff = now.getTime() - startTime.getTime();

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
}

export async function loadHotDeskSessions(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/hot-desk/sessions`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: HotDeskSessionsResponse = await response.json();
        if (data.sessions) {
            // Update stats
            const activeSessions = data.sessions.filter(s => s.active !== false);

            const activeEl = document.getElementById('hotdesk-active') as HTMLElement | null;
            if (activeEl) activeEl.textContent = String(activeSessions.length);

            const totalEl = document.getElementById('hotdesk-total') as HTMLElement | null;
            if (totalEl) totalEl.textContent = String(data.sessions.length);

            // Update table
            const tbody = document.getElementById('hotdesk-sessions-list') as HTMLElement | null;
            if (!tbody) return;

            if (activeSessions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No active hot desk sessions</td></tr>';
            } else {
                tbody.innerHTML = activeSessions.map(session => {
                    const loginTime = session.login_time ? new Date(session.login_time).toLocaleString() : 'N/A';
                    const duration = session.login_time ? getDuration(new Date(session.login_time)) : 'N/A';

                    return `
                        <tr>
                            <td><strong>${escapeHtml(session.extension)}</strong></td>
                            <td>${escapeHtml(session.device_mac || 'N/A')}</td>
                            <td>${escapeHtml(session.device_ip || 'N/A')}</td>
                            <td><small>${loginTime}</small></td>
                            <td>${duration}</td>
                            <td>
                                <button class="btn-small btn-warning" onclick="logoutHotDesk('${escapeHtml(session.extension)}')">Logout</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
    } catch (error: unknown) {
        console.error('Error loading hot desk sessions:', error);
        showNotification('Error loading hot desk sessions', 'error');
    }
}

export async function logoutHotDesk(extension: string): Promise<void> {
    if (!confirm(`Are you sure you want to log out extension ${extension} from hot desk?`)) {
        return;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/hot-desk/logout`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ extension: extension })
        });

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification(`Extension ${extension} logged out`, 'success');
            loadHotDeskSessions();
        } else {
            showNotification(data.error || 'Error logging out', 'error');
        }
    } catch (error: unknown) {
        console.error('Error logging out hot desk:', error);
        showNotification('Error logging out hot desk', 'error');
    }
}

// ---------------------------------------------------------------------------
// Recording Retention
// ---------------------------------------------------------------------------

export async function loadRetentionPolicies(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const [policiesRes, statsRes] = await Promise.all([
            fetchWithTimeout(`${API_BASE}/api/recording-retention/policies`, {
                headers: getAuthHeaders()
            }),
            fetchWithTimeout(`${API_BASE}/api/recording-retention/statistics`, {
                headers: getAuthHeaders()
            })
        ]);

        const [policiesData, statsData]: [RetentionPoliciesResponse, RetentionStatisticsResponse] =
            await Promise.all([policiesRes.json(), statsRes.json()]);

        // Update stats
        if (statsData) {
            const policiesCount = document.getElementById('retention-policies-count') as HTMLElement | null;
            if (policiesCount) policiesCount.textContent = String(statsData.total_policies || 0);

            const recordings = document.getElementById('retention-recordings') as HTMLElement | null;
            if (recordings) recordings.textContent = String(statsData.total_recordings || 0);

            const deleted = document.getElementById('retention-deleted') as HTMLElement | null;
            if (deleted) deleted.textContent = String(statsData.deleted_count || 0);

            const lastCleanup = statsData.last_cleanup
                ? new Date(statsData.last_cleanup).toLocaleDateString()
                : 'Never';
            const cleanupEl = document.getElementById('retention-last-cleanup') as HTMLElement | null;
            if (cleanupEl) cleanupEl.textContent = lastCleanup;
        }

        // Update policies table
        if (policiesData && policiesData.policies) {
            const tbody = document.getElementById('retention-policies-list') as HTMLElement | null;
            if (!tbody) return;

            if (policiesData.policies.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No retention policies configured</td></tr>';
            } else {
                tbody.innerHTML = policiesData.policies.map(policy => {
                    const created = policy.created_at ? new Date(policy.created_at).toLocaleDateString() : 'N/A';
                    const tags = policy.tags ? policy.tags.join(', ') : 'None';

                    return `
                        <tr>
                            <td><strong>${escapeHtml(policy.name)}</strong></td>
                            <td>${policy.retention_days} days</td>
                            <td><small>${escapeHtml(tags)}</small></td>
                            <td><small>${created}</small></td>
                            <td>
                                <button class="btn-small btn-danger" onclick="deleteRetentionPolicy('${escapeHtml(policy.policy_id)}', '${escapeHtml(policy.name)}')">Delete</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
    } catch (error: unknown) {
        console.error('Error loading retention policies:', error);
        showNotification('Error loading retention policies', 'error');
    }
}

export function showAddRetentionPolicyModal(): void {
    const modal = document.getElementById('add-retention-policy-modal') as HTMLElement | null;
    if (modal) modal.style.display = 'block';
}

export function closeAddRetentionPolicyModal(): void {
    const modal = document.getElementById('add-retention-policy-modal') as HTMLElement | null;
    if (modal) modal.style.display = 'none';
    const form = document.getElementById('add-retention-policy-form') as HTMLFormElement | null;
    if (form) form.reset();
}

export async function addRetentionPolicy(event: Event): Promise<void> {
    event.preventDefault();

    const name = (document.getElementById('retention-policy-name') as HTMLInputElement).value;
    const retentionDays = parseInt((document.getElementById('retention-days') as HTMLInputElement).value);
    const tagsInput = (document.getElementById('retention-tags') as HTMLInputElement).value;

    // Validate input
    if (!name.match(/^[a-zA-Z0-9_\s-]+$/)) {
        showNotification('Policy name contains invalid characters', 'error');
        return;
    }

    if (retentionDays < 1 || retentionDays > 3650) {
        showNotification('Retention days must be between 1 and 3650', 'error');
        return;
    }

    const policyData: Record<string, unknown> = {
        name: name,
        retention_days: retentionDays
    };

    // Parse tags if provided
    if (tagsInput.trim()) {
        policyData.tags = tagsInput.split(',').map(t => t.trim()).filter(t => t);
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/recording-retention/policy`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(policyData)
        });

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification(`Retention policy "${name}" added successfully`, 'success');
            closeAddRetentionPolicyModal();
            loadRetentionPolicies();
        } else {
            showNotification(data.error || 'Error adding retention policy', 'error');
        }
    } catch (error: unknown) {
        console.error('Error adding retention policy:', error);
        showNotification('Error adding retention policy', 'error');
    }
}

export async function deleteRetentionPolicy(policyId: string, policyName: string): Promise<void> {
    if (!confirm(`Are you sure you want to delete retention policy "${policyName}"?`)) {
        return;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(
            `${API_BASE}/api/recording-retention/policy/${encodeURIComponent(policyId)}`,
            {
                method: 'DELETE',
                headers: getAuthHeaders()
            }
        );

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification(`Retention policy "${policyName}" deleted`, 'success');
            loadRetentionPolicies();
        } else {
            showNotification(data.error || 'Error deleting retention policy', 'error');
        }
    } catch (error: unknown) {
        console.error('Error deleting retention policy:', error);
        showNotification('Error deleting retention policy', 'error');
    }
}

// ---------------------------------------------------------------------------
// Callback Queue
// ---------------------------------------------------------------------------

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

        const [listData, statsData]: [CallbackListResponse, CallbackStatisticsResponse] =
            await Promise.all([listRes.json(), statsRes.json()]);

        // Update statistics
        if (statsData) {
            const totalEl = document.getElementById('callback-total') as HTMLElement | null;
            if (totalEl) totalEl.textContent = String(statsData.total_callbacks || 0);

            const statusBreakdown = statsData.status_breakdown || {};
            const scheduledEl = document.getElementById('callback-scheduled') as HTMLElement | null;
            if (scheduledEl) scheduledEl.textContent = String(statusBreakdown.scheduled || 0);

            const inProgressEl = document.getElementById('callback-in-progress') as HTMLElement | null;
            if (inProgressEl) inProgressEl.textContent = String(statusBreakdown.in_progress || 0);

            const completedEl = document.getElementById('callback-completed') as HTMLElement | null;
            if (completedEl) completedEl.textContent = String(statusBreakdown.completed || 0);

            const failedEl = document.getElementById('callback-failed') as HTMLElement | null;
            if (failedEl) failedEl.textContent = String(statusBreakdown.failed || 0);
        }

        // Update callback list table
        if (listData && listData.callbacks) {
            const tbody = document.getElementById('callback-list') as HTMLElement | null;
            if (!tbody) return;

            if (listData.callbacks.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No callbacks in queue</td></tr>';
            } else {
                tbody.innerHTML = listData.callbacks.map(callback => {
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
                                <small>${escapeHtml(callback.caller_name || 'N/A')}</small>
                            </td>
                            <td><small>${requestedTime}</small></td>
                            <td><small>${callbackTime}</small></td>
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
    if (modal) modal.remove();
}

export async function requestCallback(event: Event): Promise<void> {
    event.preventDefault();

    const queueId = (document.getElementById('callback-queue-id') as HTMLInputElement).value;
    const callerNumber = (document.getElementById('callback-caller-number') as HTMLInputElement).value;
    const callerName = (document.getElementById('callback-caller-name') as HTMLInputElement).value;
    const preferredTime = (document.getElementById('callback-preferred-time') as HTMLInputElement).value;

    const callbackData: Record<string, unknown> = {
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

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification('Callback requested successfully', 'success');
            closeRequestCallbackModal();
            loadCallbackQueue();
        } else {
            showNotification(data.error || 'Error requesting callback', 'error');
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

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification(`Started callback to ${data.caller_number ?? 'caller'}`, 'success');
            loadCallbackQueue();
        } else {
            showNotification(data.error || 'Error starting callback', 'error');
        }
    } catch (error: unknown) {
        console.error('Error starting callback:', error);
        showNotification('Error starting callback', 'error');
    }
}

export async function completeCallback(callbackId: string, success: boolean): Promise<void> {
    let notes = '';
    if (!success) {
        notes = prompt('Enter reason for failure (optional):') || '';
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

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification(success ? 'Callback completed' : 'Callback will be retried', 'success');
            loadCallbackQueue();
        } else {
            showNotification(data.error || 'Error completing callback', 'error');
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

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification('Callback cancelled', 'success');
            loadCallbackQueue();
        } else {
            showNotification(data.error || 'Error cancelling callback', 'error');
        }
    } catch (error: unknown) {
        console.error('Error cancelling callback:', error);
        showNotification('Error cancelling callback', 'error');
    }
}

// ---------------------------------------------------------------------------
// Backward compatibility - register with window
// ---------------------------------------------------------------------------

window.loadFMFMExtensions = loadFMFMExtensions;
window.showAddFMFMModal = showAddFMFMModal;
window.closeAddFMFMModal = closeAddFMFMModal;
window.addFMFMDestinationRow = addFMFMDestinationRow;
window.saveFMFMConfig = saveFMFMConfig;
window.editFMFMConfig = editFMFMConfig;
window.deleteFMFMConfig = deleteFMFMConfig;
window.getScheduleDescription = getScheduleDescription;
window.showAddTimeRuleModal = showAddTimeRuleModal;
window.closeAddTimeRuleModal = closeAddTimeRuleModal;
window.loadTimeRoutingRules = loadTimeRoutingRules;
window.saveTimeRoutingRule = saveTimeRoutingRule;
window.deleteTimeRoutingRule = deleteTimeRoutingRule;
window.showAddWebhookModal = showAddWebhookModal;
window.closeAddWebhookModal = closeAddWebhookModal;
window.loadWebhooks = loadWebhooks;
window.addWebhook = addWebhook;
window.deleteWebhook = deleteWebhook;
window.loadHotDeskSessions = loadHotDeskSessions;
window.logoutHotDesk = logoutHotDesk;
window.getDuration = getDuration;
window.loadRetentionPolicies = loadRetentionPolicies;
window.showAddRetentionPolicyModal = showAddRetentionPolicyModal;
window.closeAddRetentionPolicyModal = closeAddRetentionPolicyModal;
window.addRetentionPolicy = addRetentionPolicy;
window.deleteRetentionPolicy = deleteRetentionPolicy;
window.loadCallbackQueue = loadCallbackQueue;
window.showRequestCallbackModal = showRequestCallbackModal;
window.closeRequestCallbackModal = closeRequestCallbackModal;
window.requestCallback = requestCallback;
window.startCallback = startCallback;
window.completeCallback = completeCallback;
window.cancelCallback = cancelCallback;
