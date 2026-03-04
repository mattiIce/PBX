/**
 * Analytics page module.
 * Handles call analytics, charts, and QoS metrics.
 */

import { getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';
import { escapeHtml } from '../utils/html.ts';

declare const Chart: any;

interface ChartData {
    labels?: string[];
    data?: number[];
}

interface TopCaller {
    extension?: string;
    calls?: number;
    total_duration?: number;
    avg_duration?: number;
}

interface AnalyticsOverview {
    total_calls?: number;
    answered_calls?: number;
    avg_duration?: number;
    answer_rate?: number;
    daily_trends?: ChartData;
    hourly_distribution?: ChartData;
    disposition?: ChartData;
    top_callers?: TopCaller[];
}

interface QoSData {
    avg_mos?: number;
    active_calls?: number;
    total_calls?: number;
    calls_with_issues?: number;
    metrics?: unknown[];
}

interface ChartInstance {
    destroy(): void;
}

let analyticsCharts: Record<string, ChartInstance> = {};

function isChartJsAvailable(): boolean {
    return typeof Chart !== 'undefined';
}

export async function loadAnalytics(): Promise<void> {
    try {
        const periodSelect = document.getElementById('analytics-period') as HTMLSelectElement | null;
        const days = periodSelect?.value ?? '7';
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/analytics/overview?days=${days}`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: AnalyticsOverview = await response.json();

        updateAnalyticsOverview(data);
        renderTopCallers(data.top_callers ?? []);

        if (isChartJsAvailable()) {
            if (data.daily_trends) renderDailyTrendsChart(data.daily_trends);
            if (data.hourly_distribution) renderHourlyDistributionChart(data.hourly_distribution);
            if (data.disposition) renderDispositionChart(data.disposition);
        }
    } catch (error: unknown) {
        console.error('Error loading analytics:', error);
    }
}

function updateAnalyticsOverview(data: AnalyticsOverview): void {
    const el = (id: string): HTMLElement | null => document.getElementById(id);
    const totalCalls = el('analytics-total-calls');
    const avgDuration = el('analytics-avg-duration');
    const answerRate = el('analytics-answer-rate');
    const answeredCalls = el('analytics-answered-calls');
    if (totalCalls) totalCalls.textContent = String(data.total_calls ?? 0);
    if (avgDuration) avgDuration.textContent = `${data.avg_duration ?? 0}s`;
    if (answerRate) answerRate.textContent = `${data.answer_rate ?? 0}%`;
    if (answeredCalls) answeredCalls.textContent = String(data.answered_calls ?? 0);
}

function renderTopCallers(callers: TopCaller[]): void {
    const tbody = document.getElementById('top-callers-table');
    if (!tbody) return;

    if (callers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="loading">No call data available</td></tr>';
        return;
    }

    tbody.innerHTML = callers.map(c =>
        `<tr>
            <td>${escapeHtml(String(c.extension ?? 'Unknown'))}</td>
            <td>${c.calls ?? 0}</td>
            <td>${((c.total_duration ?? 0) / 60).toFixed(1)}</td>
            <td>${(c.avg_duration ?? 0).toFixed(1)}</td>
        </tr>`
    ).join('');
}

function renderDailyTrendsChart(trends: ChartData): void {
    const ctx = (document.getElementById('daily-trends-chart') as HTMLCanvasElement | null)?.getContext('2d');
    if (!ctx) return;
    if (analyticsCharts.dailyTrends) analyticsCharts.dailyTrends.destroy();

    analyticsCharts.dailyTrends = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trends.labels || [],
            datasets: [{
                label: 'Calls',
                data: trends.data || [],
                borderColor: '#3b82f6',
                tension: 0.3,
                fill: false
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

function renderHourlyDistributionChart(hourly: ChartData): void {
    const ctx = (document.getElementById('hourly-distribution-chart') as HTMLCanvasElement | null)?.getContext('2d');
    if (!ctx) return;
    if (analyticsCharts.hourlyDist) analyticsCharts.hourlyDist.destroy();

    analyticsCharts.hourlyDist = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hourly.labels || [],
            datasets: [{
                label: 'Calls by Hour',
                data: hourly.data || [],
                backgroundColor: '#60a5fa'
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

function renderDispositionChart(disposition: ChartData): void {
    const ctx = (document.getElementById('disposition-chart') as HTMLCanvasElement | null)?.getContext('2d');
    if (!ctx) return;
    if (analyticsCharts.disposition) analyticsCharts.disposition.destroy();

    analyticsCharts.disposition = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: disposition.labels || [],
            datasets: [{
                data: disposition.data || [],
                backgroundColor: ['#10b981', '#ef4444', '#f59e0b', '#6b7280']
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

export async function loadQoSMetrics(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/qos/metrics`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: QoSData = await response.json();

        const activeCalls = data.active_calls ?? 0;
        const metrics = data.metrics as Record<string, number>[] ?? [];

        // Compute average MOS from per-call metrics
        let avgMos = 0;
        let callsWithIssues = 0;
        if (metrics.length > 0) {
            const mosValues = metrics.map(m => m.mos_score ?? 0).filter(v => v > 0);
            avgMos = mosValues.length > 0
                ? mosValues.reduce((a, b) => a + b, 0) / mosValues.length
                : 0;
            callsWithIssues = mosValues.filter(v => v < 3.5).length;
        }

        const mosEl = document.getElementById('qos-avg-mos');
        const activeCallsEl = document.getElementById('qos-active-calls');
        const totalCallsEl = document.getElementById('qos-total-calls');
        const issuesEl = document.getElementById('qos-calls-with-issues');
        if (mosEl) mosEl.textContent = avgMos > 0 ? avgMos.toFixed(2) : 'N/A';
        if (activeCallsEl) activeCallsEl.textContent = String(activeCalls);
        if (totalCallsEl) totalCallsEl.textContent = String(metrics.length);
        if (issuesEl) issuesEl.textContent = String(callsWithIssues);
    } catch (error: unknown) {
        console.error('Error loading QoS metrics:', error);
    }
}

export async function clearQoSAlerts(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/qos/clear-alerts`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if (response.ok) {
            const container = document.getElementById('qos-alerts-container') as HTMLElement | null;
            if (container) container.innerHTML = '<div class="info-box">No quality alerts</div>';
            showNotification('QoS alerts cleared', 'success');
        } else {
            showNotification('Failed to clear QoS alerts', 'error');
        }
    } catch (error: unknown) {
        console.error('Error clearing QoS alerts:', error);
        showNotification('Failed to clear QoS alerts', 'error');
    }
}

export async function saveQoSThresholds(event?: Event): Promise<void> {
    if (event) event.preventDefault();
    try {
        const val = (id: string): string => (document.getElementById(id) as HTMLInputElement)?.value ?? '';

        const data = {
            mos_min: parseFloat(val('qos-threshold-mos')) || 3.5,
            jitter_max: parseInt(val('qos-threshold-jitter'), 10) || 50,
            packet_loss_max: parseFloat(val('qos-threshold-loss')) || 2.0,
            latency_max: parseInt(val('qos-threshold-latency'), 10) || 300,
        };

        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/qos/thresholds`, {
            method: 'POST',
            headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (response.ok) {
            showNotification('QoS thresholds saved', 'success');
        } else {
            showNotification('Failed to save QoS thresholds', 'error');
        }
    } catch (error: unknown) {
        console.error('Error saving QoS thresholds:', error);
        showNotification('Failed to save QoS thresholds', 'error');
    }
}

// Backward compatibility
window.loadAnalytics = loadAnalytics;
window.loadQoSMetrics = loadQoSMetrics;
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- legacy backward compat
(window as any).clearQoSAlerts = clearQoSAlerts;
(window as any).saveQoSThresholds = saveQoSThresholds;
