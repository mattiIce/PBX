/**
 * SIP Trunks and LCR page module.
 * Handles SIP trunk management, health monitoring, and least-cost routing.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';
import { escapeHtml } from '../utils/html.ts';

// ---------------------------------------------------------------------------
// Interfaces
// ---------------------------------------------------------------------------

interface SIPTrunk {
    trunk_id: string;
    name: string;
    host: string;
    port: number;
    status: string;
    health_status: string;
    priority: number;
    channels_available: number;
    channels_in_use: number;
    max_channels: number;
    success_rate: number;
    successful_calls: number;
    total_calls: number;
}

interface SIPTrunksResponse {
    trunks?: SIPTrunk[];
    count?: number;
}

interface TrunkHealthEntry {
    trunk_id: string;
    name: string;
    health_status: string;
    success_rate: number;
    consecutive_failures: number;
    average_setup_time: number;
    failover_count: number;
    total_calls: number;
    successful_calls: number;
    failed_calls: number;
    last_successful_call?: string;
    last_failed_call?: string;
    last_health_check?: string;
}

interface TrunkHealthResponse {
    health?: TrunkHealthEntry[];
}

interface TrunkTestResponse {
    success: boolean;
    health_status?: string;
    error?: string;
}

interface ApiSuccessResponse {
    success: boolean;
    error?: string;
}

interface LCRRate {
    trunk_id: string;
    pattern: string;
    description: string;
    rate_per_minute: number;
    connection_fee: number;
    minimum_seconds: number;
    billing_increment: number;
}

interface LCRTimeRate {
    name: string;
    start_time: string;
    end_time: string;
    days_of_week: number[];
    rate_multiplier: number;
}

interface LCRRatesResponse {
    rates?: LCRRate[];
    count?: number;
    time_rates?: LCRTimeRate[];
}

interface LCRDecision {
    timestamp: string;
    number: string;
    selected_trunk: string;
    estimated_cost: number;
    alternatives: number;
}

interface LCRStatisticsResponse {
    total_routes?: number;
    enabled?: boolean;
    recent_decisions?: LCRDecision[];
}

// ---------------------------------------------------------------------------
// Helper: badge renderers
// ---------------------------------------------------------------------------

function getStatusBadge(status: string): string {
    const badges: Record<string, string> = {
        'registered': '<span class="badge" style="background: #10b981;">Registered</span>',
        'unregistered': '<span class="badge" style="background: #6b7280;">Unregistered</span>',
        'failed': '<span class="badge" style="background: #ef4444;">Failed</span>',
        'disabled': '<span class="badge" style="background: #9ca3af;">Disabled</span>',
        'degraded': '<span class="badge" style="background: #f59e0b;">Degraded</span>'
    };
    return badges[status] || status;
}

function getHealthBadge(health: string): string {
    const badges: Record<string, string> = {
        'healthy': '<span class="badge" style="background: #10b981;">Healthy</span>',
        'warning': '<span class="badge" style="background: #f59e0b;">Warning</span>',
        'critical': '<span class="badge" style="background: #f59e0b;">Critical</span>',
        'down': '<span class="badge" style="background: #ef4444;">Down</span>'
    };
    return badges[health] || health;
}

// ---------------------------------------------------------------------------
// SIP Trunk Management
// ---------------------------------------------------------------------------

export async function loadSIPTrunks(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/sip-trunks`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: SIPTrunksResponse = await response.json();
        if (data.trunks) {
            // Update stats
            const trunkTotal = document.getElementById('trunk-total') as HTMLElement | null;
            if (trunkTotal) trunkTotal.textContent = String(data.count || 0);

            const healthyCount = data.trunks.filter(t => t.health_status === 'healthy').length;
            const registeredCount = data.trunks.filter(t => t.status === 'registered').length;
            const totalChannels = data.trunks.reduce((sum, t) => sum + t.channels_available, 0);

            const trunkHealthy = document.getElementById('trunk-healthy') as HTMLElement | null;
            if (trunkHealthy) trunkHealthy.textContent = String(healthyCount);

            const trunkRegistered = document.getElementById('trunk-registered') as HTMLElement | null;
            if (trunkRegistered) trunkRegistered.textContent = String(registeredCount);

            const trunkChannels = document.getElementById('trunk-total-channels') as HTMLElement | null;
            if (trunkChannels) trunkChannels.textContent = String(totalChannels);

            // Update table
            const tbody = document.getElementById('trunks-list') as HTMLElement | null;
            if (!tbody) return;

            if (data.trunks.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No SIP trunks configured</td></tr>';
            } else {
                tbody.innerHTML = data.trunks.map(trunk => {
                    const statusBadge = getStatusBadge(trunk.status);
                    const healthBadge = getHealthBadge(trunk.health_status);
                    const successRate = (trunk.success_rate * 100).toFixed(1);

                    return `
                        <tr>
                            <td><strong>${escapeHtml(trunk.name)}</strong><br/><small>${escapeHtml(trunk.trunk_id)}</small></td>
                            <td>${escapeHtml(trunk.host)}:${trunk.port}</td>
                            <td>${statusBadge}</td>
                            <td>${healthBadge}</td>
                            <td>${trunk.priority}</td>
                            <td>${trunk.channels_in_use}/${trunk.max_channels}</td>
                            <td>
                                <div style="display: flex; align-items: center; gap: 5px;">
                                    <div style="flex: 1; background: #e5e7eb; border-radius: 4px; height: 20px; overflow: hidden;">
                                        <div style="background: ${Number(successRate) >= 95 ? '#10b981' : Number(successRate) >= 80 ? '#f59e0b' : '#ef4444'}; height: 100%; width: ${successRate}%;"></div>
                                    </div>
                                    <span>${successRate}%</span>
                                </div>
                                <small>${trunk.successful_calls}/${trunk.total_calls} calls</small>
                            </td>
                            <td>
                                <button class="btn-small btn-primary" onclick="testTrunk('${escapeHtml(trunk.trunk_id)}')">Test</button>
                                <button class="btn-small btn-danger" onclick="deleteTrunk('${escapeHtml(trunk.trunk_id)}', '${escapeHtml(trunk.name)}')">Delete</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
    } catch (error: unknown) {
        console.error('Error loading SIP trunks:', error);
        const message = error instanceof Error ? error.message : String(error);
        showNotification(`Error loading SIP trunks: ${message}`, 'error');
    }
}

export async function loadTrunkHealth(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/sip-trunks/health`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: TrunkHealthResponse = await response.json();
        if (data.health) {
            const section = document.getElementById('trunk-health-section') as HTMLElement | null;
            const container = document.getElementById('trunk-health-container') as HTMLElement | null;
            if (!section || !container) return;

            section.style.display = 'block';

            container.innerHTML = data.health.map(h => `
                <div class="config-section" style="margin-bottom: 15px;">
                    <h4>${escapeHtml(h.name)} (${escapeHtml(h.trunk_id)})</h4>
                    <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));">
                        <div class="stat-card">
                            <div class="stat-value">${getHealthBadge(h.health_status)}</div>
                            <div class="stat-label">Health Status</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${(h.success_rate * 100).toFixed(1)}%</div>
                            <div class="stat-label">Success Rate</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${h.consecutive_failures}</div>
                            <div class="stat-label">Consecutive Failures</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${h.average_setup_time.toFixed(2)}s</div>
                            <div class="stat-label">Avg Setup Time</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${h.failover_count}</div>
                            <div class="stat-label">Failover Count</div>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <p><strong>Total Calls:</strong> ${h.total_calls} (${h.successful_calls} successful, ${h.failed_calls} failed)</p>
                        ${h.last_successful_call ? `<p><strong>Last Success:</strong> ${new Date(h.last_successful_call).toLocaleString()}</p>` : ''}
                        ${h.last_failed_call ? `<p><strong>Last Failure:</strong> ${new Date(h.last_failed_call).toLocaleString()}</p>` : ''}
                        ${h.last_health_check ? `<p><strong>Last Check:</strong> ${new Date(h.last_health_check).toLocaleString()}</p>` : ''}
                    </div>
                </div>
            `).join('');

            showNotification('Health metrics loaded', 'success');
        }
    } catch (error: unknown) {
        console.error('Error loading trunk health:', error);
        const message = error instanceof Error ? error.message : String(error);
        showNotification(`Error loading trunk health: ${message}`, 'error');
    }
}

export function showAddTrunkModal(): void {
    const modal = document.getElementById('add-trunk-modal') as HTMLElement | null;
    if (modal) modal.style.display = 'block';
}

export function closeAddTrunkModal(): void {
    const modal = document.getElementById('add-trunk-modal') as HTMLElement | null;
    if (modal) modal.style.display = 'none';
    const form = document.getElementById('add-trunk-form') as HTMLFormElement | null;
    if (form) form.reset();
}

export async function addSIPTrunk(event: Event): Promise<void> {
    event.preventDefault();

    const selectedCodecs = Array.from(
        document.querySelectorAll<HTMLInputElement>('input[name="trunk-codecs"]:checked')
    ).map(cb => cb.value);

    const trunkData = {
        trunk_id: (document.getElementById('trunk-id') as HTMLInputElement).value,
        name: (document.getElementById('trunk-name') as HTMLInputElement).value,
        host: (document.getElementById('trunk-host') as HTMLInputElement).value,
        port: parseInt((document.getElementById('trunk-port') as HTMLInputElement).value),
        username: (document.getElementById('trunk-username') as HTMLInputElement).value,
        password: (document.getElementById('trunk-password') as HTMLInputElement).value,
        priority: parseInt((document.getElementById('trunk-priority') as HTMLInputElement).value),
        max_channels: parseInt((document.getElementById('trunk-channels') as HTMLInputElement).value),
        codec_preferences: selectedCodecs.length > 0 ? selectedCodecs : ['G.711', 'G.729']
    };

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/sip-trunks`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(trunkData)
        });

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification(`Trunk ${trunkData.name} added successfully`, 'success');
            closeAddTrunkModal();
            loadSIPTrunks();
        } else {
            showNotification(data.error || 'Error adding trunk', 'error');
        }
    } catch (error: unknown) {
        console.error('Error adding trunk:', error);
        showNotification('Error adding trunk', 'error');
    }
}

export async function deleteTrunk(trunkId: string, trunkName: string): Promise<void> {
    if (!confirm(`Are you sure you want to delete trunk "${trunkName}"?`)) {
        return;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/sip-trunks/${trunkId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification(`Trunk ${trunkName} deleted`, 'success');
            loadSIPTrunks();
        } else {
            showNotification(data.error || 'Error deleting trunk', 'error');
        }
    } catch (error: unknown) {
        console.error('Error deleting trunk:', error);
        showNotification('Error deleting trunk', 'error');
    }
}

export async function testTrunk(trunkId: string): Promise<void> {
    showNotification('Testing trunk...', 'info');

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/sip-trunks/test`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ trunk_id: trunkId })
        });

        const data: TrunkTestResponse = await response.json();
        if (data.success) {
            const health = data.health_status ?? 'unknown';
            showNotification(
                `Trunk test complete: ${health}`,
                health === 'healthy' ? 'success' : 'warning'
            );
            loadSIPTrunks();
            loadTrunkHealth();
        } else {
            showNotification(data.error || 'Error testing trunk', 'error');
        }
    } catch (error: unknown) {
        console.error('Error testing trunk:', error);
        showNotification('Error testing trunk', 'error');
    }
}

// ---------------------------------------------------------------------------
// Least-Cost Routing (LCR)
// ---------------------------------------------------------------------------

export async function loadLCRRates(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/lcr/rates`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            if ((window as Record<string, unknown>).suppressErrorNotifications) {
                console.info('LCR rates endpoint returned error:', response.status, '(feature may not be enabled)');
            } else {
                console.error('Error loading LCR rates:', response.status);
                showNotification('Error loading LCR rates', 'error');
            }
            return;
        }

        const data: LCRRatesResponse = await response.json();

        if (data.rates !== undefined) {
            // Update stats
            const lcrTotal = document.getElementById('lcr-total-rates') as HTMLElement | null;
            if (lcrTotal) lcrTotal.textContent = String(data.count || 0);

            const lcrTimeCount = document.getElementById('lcr-time-rates') as HTMLElement | null;
            if (lcrTimeCount) lcrTimeCount.textContent = String(data.time_rates ? data.time_rates.length : 0);

            // Update rate entries table
            const ratesBody = document.getElementById('lcr-rates-list') as HTMLElement | null;
            if (ratesBody) {
                if (data.rates.length === 0) {
                    ratesBody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No rates configured</td></tr>';
                } else {
                    ratesBody.innerHTML = data.rates.map(rate => `
                        <tr>
                            <td><strong>${escapeHtml(rate.trunk_id)}</strong></td>
                            <td><code>${escapeHtml(rate.pattern)}</code></td>
                            <td>${escapeHtml(rate.description)}</td>
                            <td>$${rate.rate_per_minute.toFixed(4)}</td>
                            <td>$${rate.connection_fee.toFixed(4)}</td>
                            <td>${rate.minimum_seconds}s</td>
                            <td>${rate.billing_increment}s</td>
                        </tr>
                    `).join('');
                }
            }

            // Update time-based rates table
            const timeRatesBody = document.getElementById('lcr-time-rates-list') as HTMLElement | null;
            if (timeRatesBody) {
                if (!data.time_rates || data.time_rates.length === 0) {
                    timeRatesBody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No time-based rates configured</td></tr>';
                } else {
                    timeRatesBody.innerHTML = data.time_rates.map(tr => {
                        const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
                        const days = tr.days_of_week.map(d => dayNames[d]).join(', ');

                        return `
                            <tr>
                                <td><strong>${escapeHtml(tr.name)}</strong></td>
                                <td>${tr.start_time}</td>
                                <td>${tr.end_time}</td>
                                <td>${days}</td>
                                <td>${tr.rate_multiplier}x</td>
                            </tr>
                        `;
                    }).join('');
                }
            }
        }

        // Load statistics
        loadLCRStatistics();
    } catch (error: unknown) {
        if ((window as Record<string, unknown>).suppressErrorNotifications) {
            const msg = error instanceof Error ? error.message : String(error);
            console.info('Error loading LCR rates (expected if LCR not enabled):', msg);
        } else {
            console.error('Error loading LCR rates:', error);
            showNotification('Error loading LCR rates', 'error');
        }
    }
}

export async function loadLCRStatistics(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/lcr/statistics`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            if ((window as Record<string, unknown>).suppressErrorNotifications) {
                console.info('LCR statistics endpoint returned error:', response.status, '(feature may not be enabled)');
            } else {
                console.error('Error loading LCR statistics:', response.status);
            }
            return;
        }

        const data: LCRStatisticsResponse = await response.json();

        // Update stats
        const lcrRoutes = document.getElementById('lcr-total-routes') as HTMLElement | null;
        if (lcrRoutes) lcrRoutes.textContent = String(data.total_routes || 0);

        const lcrStatus = document.getElementById('lcr-status') as HTMLElement | null;
        if (lcrStatus) {
            lcrStatus.innerHTML = data.enabled
                ? '<span class="badge" style="background: #10b981;">Enabled</span>'
                : '<span class="badge" style="background: #6b7280;">Disabled</span>';
        }

        // Update recent decisions table
        const decisionsBody = document.getElementById('lcr-decisions-list') as HTMLElement | null;
        if (decisionsBody) {
            if (!data.recent_decisions || data.recent_decisions.length === 0) {
                decisionsBody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No recent decisions</td></tr>';
            } else {
                decisionsBody.innerHTML = data.recent_decisions.map(d => {
                    const timestamp = new Date(d.timestamp).toLocaleString();
                    return `
                        <tr>
                            <td>${timestamp}</td>
                            <td>${escapeHtml(d.number)}</td>
                            <td><strong>${escapeHtml(d.selected_trunk)}</strong></td>
                            <td>$${d.estimated_cost.toFixed(4)}</td>
                            <td>${d.alternatives}</td>
                        </tr>
                    `;
                }).join('');
            }
        }
    } catch (error: unknown) {
        if ((window as Record<string, unknown>).suppressErrorNotifications) {
            const msg = error instanceof Error ? error.message : String(error);
            console.info('Error loading LCR statistics (expected if LCR not enabled):', msg);
        } else {
            console.error('Error loading LCR statistics:', error);
        }
    }
}

export function showAddLCRRateModal(): void {
    const modal = `
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
    `;

    document.body.insertAdjacentHTML('beforeend', modal);
}

export function closeLCRRateModal(): void {
    const modal = document.getElementById('lcr-rate-modal');
    if (modal) modal.remove();
}

export async function addLCRRate(event: Event): Promise<void> {
    event.preventDefault();

    const rateData = {
        trunk_id: (document.getElementById('lcr-trunk-id') as HTMLInputElement).value,
        pattern: (document.getElementById('lcr-pattern') as HTMLInputElement).value,
        description: (document.getElementById('lcr-description') as HTMLInputElement).value,
        rate_per_minute: parseFloat((document.getElementById('lcr-rate-per-minute') as HTMLInputElement).value),
        connection_fee: parseFloat((document.getElementById('lcr-connection-fee') as HTMLInputElement).value),
        minimum_seconds: parseInt((document.getElementById('lcr-minimum-seconds') as HTMLInputElement).value),
        billing_increment: parseInt((document.getElementById('lcr-billing-increment') as HTMLInputElement).value)
    };

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/lcr/rate`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(rateData)
        });

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification('LCR rate added successfully', 'success');
            closeLCRRateModal();
            loadLCRRates();
        } else {
            showNotification(data.error || 'Error adding LCR rate', 'error');
        }
    } catch (error: unknown) {
        console.error('Error adding LCR rate:', error);
        showNotification('Error adding LCR rate', 'error');
    }
}

export function showAddTimeRateModal(): void {
    const modal = `
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
    `;

    document.body.insertAdjacentHTML('beforeend', modal);
}

export function closeTimeRateModal(): void {
    const modal = document.getElementById('lcr-time-rate-modal');
    if (modal) modal.remove();
}

export async function addTimeRate(event: Event): Promise<void> {
    event.preventDefault();

    const selectedDays = Array.from(
        document.querySelectorAll<HTMLInputElement>('input[name="time-days"]:checked')
    ).map(cb => parseInt(cb.value));

    const timeRateData = {
        name: (document.getElementById('time-rate-name') as HTMLInputElement).value,
        start_hour: parseInt((document.getElementById('time-rate-start-hour') as HTMLInputElement).value),
        start_minute: parseInt((document.getElementById('time-rate-start-minute') as HTMLInputElement).value),
        end_hour: parseInt((document.getElementById('time-rate-end-hour') as HTMLInputElement).value),
        end_minute: parseInt((document.getElementById('time-rate-end-minute') as HTMLInputElement).value),
        days: selectedDays,
        multiplier: parseFloat((document.getElementById('time-rate-multiplier') as HTMLInputElement).value)
    };

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/lcr/time-rate`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(timeRateData)
        });

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification('Time-based rate added successfully', 'success');
            closeTimeRateModal();
            loadLCRRates();
        } else {
            showNotification(data.error || 'Error adding time-based rate', 'error');
        }
    } catch (error: unknown) {
        console.error('Error adding time-based rate:', error);
        showNotification('Error adding time-based rate', 'error');
    }
}

export async function clearLCRRates(): Promise<void> {
    if (!confirm('Are you sure you want to clear all LCR rates? This cannot be undone.')) {
        return;
    }

    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetchWithTimeout(`${API_BASE}/api/lcr/clear-rates`, {
            method: 'POST',
            headers: getAuthHeaders()
        });

        const data: ApiSuccessResponse = await response.json();
        if (data.success) {
            showNotification('All LCR rates cleared', 'success');
            loadLCRRates();
        } else {
            showNotification(data.error || 'Error clearing LCR rates', 'error');
        }
    } catch (error: unknown) {
        console.error('Error clearing LCR rates:', error);
        showNotification('Error clearing LCR rates', 'error');
    }
}

// ---------------------------------------------------------------------------
// Backward compatibility - register with window
// ---------------------------------------------------------------------------

window.loadSIPTrunks = loadSIPTrunks;
window.loadTrunkHealth = loadTrunkHealth;
window.showAddTrunkModal = showAddTrunkModal;
window.closeAddTrunkModal = closeAddTrunkModal;
window.addSIPTrunk = addSIPTrunk;
window.deleteTrunk = deleteTrunk;
window.testTrunk = testTrunk;
window.loadLCRRates = loadLCRRates;
window.loadLCRStatistics = loadLCRStatistics;
window.showAddLCRRateModal = showAddLCRRateModal;
window.closeLCRRateModal = closeLCRRateModal;
window.addLCRRate = addLCRRate;
window.showAddTimeRateModal = showAddTimeRateModal;
window.closeTimeRateModal = closeTimeRateModal;
window.addTimeRate = addTimeRate;
window.clearLCRRates = clearLCRRates;
