import { escapeHtml } from '../utils/html.ts';

type NotificationType = 'success' | 'error' | 'warning' | 'info';

interface ErrorDisplayConfig {
    enabled: boolean;
    displayTime: number;
    maxErrors: number;
    showStackTrace: boolean;
}

interface ErrorEntry {
    id: string;
    message: string;
    context: string;
    stack: string;
    timestamp: Date;
}

// Error Display Configuration
const ERROR_DISPLAY_CONFIG: ErrorDisplayConfig = {
    enabled: true,
    displayTime: 8000, // 8 seconds
    maxErrors: 5,
    showStackTrace: true
};

// Error queue
let errorQueue: ErrorEntry[] = [];

// Flag to suppress error notifications during bulk operations
let suppressErrorNotifications = false;

/**
 * Set the suppression flag for error notifications (used during bulk operations).
 */
export function setSuppressErrorNotifications(value: boolean): void {
    suppressErrorNotifications = value;
}

/**
 * Display a brief notification banner (success, error, warning, or info).
 */
export function showNotification(message: string, type: NotificationType = 'info'): void {
    // Log to console for debugging (use info level for suppressed errors)
    if (suppressErrorNotifications && type === 'error') {
        debugLog(`[${type.toUpperCase()}] ${message}`);
        return; // Don't show error notifications during bulk operations
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        max-width: 400px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999;
        animation: slideInRight 0.3s ease-out;
        font-size: 14px;
        line-height: 1.4;
    `;

    const icon = type === 'success' ? '\u2713' : type === 'error' ? '\u2717' : type === 'warning' ? '\u26A0' : '\u2139';
    notification.innerHTML = `<strong>${icon}</strong> ${escapeHtml(message)}`;

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

/**
 * Display a detailed error notification with optional stack trace.
 */
export function displayError(error: Error | { message?: string; stack?: string; toString(): string }, context: string = ''): void {
    if (!ERROR_DISPLAY_CONFIG.enabled) return;

    const errorId = `error-${Date.now()}`;
    const errorMessage = error.message || error.toString();
    const errorStack = error.stack || '';

    // Add to queue
    errorQueue.push({
        id: errorId,
        message: errorMessage,
        context: context,
        stack: errorStack,
        timestamp: new Date()
    });

    // Keep only max errors
    if (errorQueue.length > ERROR_DISPLAY_CONFIG.maxErrors) {
        errorQueue.shift();
    }

    // Create error notification element
    const errorDiv = document.createElement('div');
    errorDiv.id = errorId;
    errorDiv.className = 'error-notification';
    errorDiv.style.cssText = `
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
    `;

    let html = `
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
            <strong style="font-size: 16px;">JavaScript Error</strong>
            <button id="close-${errorId}"
                    style="background: none; border: none; color: white; font-size: 20px; cursor: pointer; padding: 0; margin-left: 10px;">
                \u00D7
            </button>
        </div>
    `;

    if (context) {
        html += `<div style="margin-bottom: 5px;"><strong>Context:</strong> ${escapeHtml(context)}</div>`;
    }

    html += `<div style="margin-bottom: 5px;"><strong>Message:</strong> ${escapeHtml(errorMessage)}</div>`;

    if (ERROR_DISPLAY_CONFIG.showStackTrace && errorStack) {
        html += `
            <details style="margin-top: 10px; cursor: pointer;">
                <summary style="font-weight: bold; margin-bottom: 5px;">Stack Trace (click to expand)</summary>
                <pre style="background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 11px; margin: 5px 0 0 0;">${escapeHtml(errorStack)}</pre>
            </details>
        `;
    }

    html += `
        <div style="margin-top: 10px; font-size: 11px; opacity: 0.9;">
            Tip: Press F12 to open browser console for more details
        </div>
    `;

    errorDiv.innerHTML = html;

    // Add click handler for close button using event listener (not inline onclick)
    const closeBtn = errorDiv.querySelector(`#close-${errorId}`) as HTMLButtonElement | null;
    if (closeBtn) {
        closeBtn.addEventListener('click', () => errorDiv.remove());
    }

    // Add to page
    document.body.appendChild(errorDiv);

    // Auto-remove after configured time
    setTimeout(() => {
        if (document.getElementById(errorId)) {
            errorDiv.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => errorDiv.remove(), 300);
        }
    }, ERROR_DISPLAY_CONFIG.displayTime);

    // Also log to console
    console.error(`[${context || 'Error'}]`, errorMessage);
    if (errorStack) {
        console.error('Stack trace:', errorStack);
    }
}
