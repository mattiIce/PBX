/**
 * Analytics page module.
 * Handles call analytics, charts, and QoS metrics.
 */

import { getAuthHeaders, getApiBaseUrl } from '../api/client.js';
import { showNotification } from '../ui/notifications.js';

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
    if (el('analytics-total-calls')) (el('analytics-total-calls') as HTMLElement).textContent = String(data.total_calls || 0);
    if (el('analytics-avg-duration')) (el('analytics-avg-duration') as HTMLElement).textContent = `${data.avg_duration || 0}s`;
    if (el('analytics-answer-rate')) (el('analytics-answer-rate') as HTMLElement).textContent = `${data.answer_rate || 0}%`;
    if (el('analytics-active-now')) (el('analytics-active-now') as HTMLElement).textContent = String(data.active_calls || 0);
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

        const el = (id: string): HTMLElement | null => document.getElementById(id);
        if (el('qos-mos')) (el('qos-mos') as HTMLElement).textContent = data.avg_mos?.toFixed(2) || 'N/A';
        if (el('qos-jitter')) (el('qos-jitter') as HTMLElement).textContent = `${data.avg_jitter || 0}ms`;
        if (el('qos-packet-loss')) (el('qos-packet-loss') as HTMLElement).textContent = `${data.avg_packet_loss || 0}%`;
        if (el('qos-latency')) (el('qos-latency') as HTMLElement).textContent = `${data.avg_latency || 0}ms`;
    } catch (error: unknown) {
        console.error('Error loading QoS metrics:', error);
    }
}

// Backward compatibility
(window as any).loadAnalytics = loadAnalytics;
(window as any).loadQoSMetrics = loadQoSMetrics;
