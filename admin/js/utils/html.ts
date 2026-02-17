import { showNotification } from '../ui/notifications.ts';

/**
 * Escape a string for safe insertion into HTML (prevents XSS).
 */
export function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Copy the given text to the clipboard using the modern Clipboard API.
 */
export async function copyToClipboard(text: string): Promise<void> {
    try {
        await navigator.clipboard.writeText(text);
        showNotification('License data copied to clipboard!', 'success');
    } catch (error: unknown) {
        console.error('Error copying to clipboard:', error);
        showNotification('Failed to copy to clipboard', 'error');
    }
}

/**
 * Format an ISO date string into a locale-formatted date/time string.
 */
export function formatDate(dateString: string): string {
    if (!dateString) return '';
    try {
        const date = new Date(dateString);
        return date.toLocaleString();
    } catch {
        return dateString;
    }
}

/**
 * Truncate a string to the given length, appending '...' if truncated.
 */
export function truncate(str: string, length: number): string {
    if (str.length <= length) return str;
    return str.substring(0, length) + '...';
}

/**
 * Calculate a human-readable duration from a start time until now.
 */
export function getDuration(startTime: string): string {
    const now = new Date();
    const diff = now.getTime() - new Date(startTime).getTime();

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
}

/**
 * Return an HTML badge element for a SIP trunk registration status.
 */
export function getStatusBadge(status: string): string {
    const badges: Record<string, string> = {
        'registered': '<span class="badge" style="background: #10b981;">&#x2705; Registered</span>',
        'unregistered': '<span class="badge" style="background: #6b7280;">&#x26AA; Unregistered</span>',
        'failed': '<span class="badge" style="background: #ef4444;">&#x274C; Failed</span>',
        'disabled': '<span class="badge" style="background: #9ca3af;">&#x23F8;&#xFE0F; Disabled</span>',
        'degraded': '<span class="badge" style="background: #f59e0b;">&#x26A0;&#xFE0F; Degraded</span>',
    };
    return badges[status] || status;
}

/**
 * Return an HTML badge element for a trunk health status.
 */
export function getHealthBadge(health: string): string {
    const badges: Record<string, string> = {
        'healthy': '<span class="badge" style="background: #10b981;">&#x1F49A; Healthy</span>',
        'warning': '<span class="badge" style="background: #f59e0b;">&#x26A0;&#xFE0F; Warning</span>',
        'critical': '<span class="badge" style="background: #f59e0b;">&#x1F534; Critical</span>',
        'down': '<span class="badge" style="background: #ef4444;">&#x1F480; Down</span>',
    };
    return badges[health] || health;
}

/**
 * Return an HTML badge element for an emergency contact priority level.
 */
export function getPriorityBadge(priority: number): string {
    const badges: Record<number, string> = {
        1: '<span class="badge" style="background: #ef4444;">1 - Highest</span>',
        2: '<span class="badge" style="background: #f97316;">2 - High</span>',
        3: '<span class="badge" style="background: #eab308;">3 - Medium</span>',
        4: '<span class="badge" style="background: #3b82f6;">4 - Low</span>',
        5: '<span class="badge" style="background: #6b7280;">5 - Lowest</span>',
    };
    return badges[priority] || `<span class="badge">${priority}</span>`;
}

/**
 * Return a CSS class name based on the MOS (Mean Opinion Score) quality rating.
 */
export function getQualityClass(mosScore: number): string {
    if (mosScore >= 4.3) return 'quality-excellent';
    if (mosScore >= 4.0) return 'quality-good';
    if (mosScore >= 3.6) return 'quality-fair';
    if (mosScore >= 3.1) return 'quality-poor';
    return 'quality-bad';
}

interface ScheduleConditions {
    days_of_week?: number[];
    start_time?: string;
    end_time?: string;
    holidays?: boolean;
}

/**
 * Format schedule conditions into a human-readable description string.
 */
export function getScheduleDescription(conditions: ScheduleConditions): string {
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

interface LicenseData {
    issued_to: string;
    [key: string]: unknown;
}

/**
 * Trigger a browser download of license data as a JSON file.
 */
export function downloadLicense(licenseData: LicenseData): void {
    const dataStr = JSON.stringify(licenseData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `license_${licenseData.issued_to.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase()}_${new Date().toISOString().split('T')[0]}.json`;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
}

// Backward compatibility: register utilities on the window object
(window as unknown as Record<string, unknown>).formatDate = formatDate;
(window as unknown as Record<string, unknown>).truncate = truncate;
(window as unknown as Record<string, unknown>).getDuration = getDuration;
(window as unknown as Record<string, unknown>).getStatusBadge = getStatusBadge;
(window as unknown as Record<string, unknown>).getHealthBadge = getHealthBadge;
(window as unknown as Record<string, unknown>).getPriorityBadge = getPriorityBadge;
(window as unknown as Record<string, unknown>).getQualityClass = getQualityClass;
(window as unknown as Record<string, unknown>).getScheduleDescription = getScheduleDescription;
(window as unknown as Record<string, unknown>).downloadLicense = downloadLicense;
