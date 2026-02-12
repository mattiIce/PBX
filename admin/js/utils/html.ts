/**
 * Escape a string for safe insertion into HTML (prevents XSS).
 */
export function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Copy the given text to the clipboard using the legacy execCommand approach.
 */
export function copyToClipboard(text: string): void {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();

    try {
        document.execCommand('copy');
        alert('License data copied to clipboard!');
    } catch (error: unknown) {
        console.error('Error copying to clipboard:', error);
        alert('Failed to copy to clipboard');
    } finally {
        document.body.removeChild(textarea);
    }
}
