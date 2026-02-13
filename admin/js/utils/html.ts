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
