/**
 * Analytics page module.
 * Handles call analytics, charts, and QoS metrics.
 */

import { getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';

declare const Chart: any;

interface ChartData {
    labels?: string[];
    data?: number[];
}

interface AnalyticsOverview {
    total_calls?: number;
    avg_duration?: number;
    answer_rate?: number;
    active_calls?: number;
    daily_trends?: ChartData;
    hourly_distribution?: ChartData;
    disposition?: ChartData;
}

interface QoSData {
    avg_mos?: number;
    avg_jitter?: number;
    avg_packet_loss?: number;
    avg_latency?: number;
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
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/analytics/overview`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: AnalyticsOverview = await response.json();

        updateAnalyticsOverview(data);

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
    if (answeredCalls) answeredCalls.textContent = String(data.active_calls ?? 0);
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

        const mosEl = document.getElementById('qos-mos');
        const jitterEl = document.getElementById('qos-jitter');
        const packetLossEl = document.getElementById('qos-packet-loss');
        const latencyEl = document.getElementById('qos-latency');
        if (mosEl) mosEl.textContent = data.avg_mos?.toFixed(2) ?? 'N/A';
        if (jitterEl) jitterEl.textContent = `${data.avg_jitter ?? 0}ms`;
        if (packetLossEl) packetLossEl.textContent = `${data.avg_packet_loss ?? 0}%`;
        if (latencyEl) latencyEl.textContent = `${data.avg_latency ?? 0}ms`;
    } catch (error: unknown) {
        console.error('Error loading QoS metrics:', error);
    }
}

export async function clearQoSAlerts(): Promise<void> {
    try {
        const API_BASE = getApiBaseUrl();
        const response = await fetch(`${API_BASE}/api/qos/alerts`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (response.ok) {
            const container = document.getElementById('qos-alerts-list') as HTMLElement | null;
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
            mos_threshold: parseFloat(val('qos-mos-threshold')) || 3.5,
            jitter_threshold: parseInt(val('qos-jitter-threshold'), 10) || 30,
            packet_loss_threshold: parseFloat(val('qos-packet-loss-threshold')) || 1.0,
            latency_threshold: parseInt(val('qos-latency-threshold'), 10) || 150,
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
