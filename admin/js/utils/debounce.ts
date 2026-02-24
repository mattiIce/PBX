/**
 * Debounce utility for preventing rapid successive function calls.
 * Useful for form submissions, API calls, and other expensive operations.
 */

export interface DebouncedFunction {
    (): Promise<void>;
    cancel(): void;
}

/**
 * Creates a debounced version of a function that will only execute after
 * the specified delay has passed since the last call.
 *
 * @param fn - The function to debounce
 * @param delayMs - Delay in milliseconds (default: 300)
 * @returns Debounced function with cancel method
 */
export function debounce(fn: () => Promise<void>, delayMs = 300): DebouncedFunction {
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    let lastExecutionTime = 0;

    const debounced = async () => {
        const now = Date.now();
        const timeSinceLastExecution = now - lastExecutionTime;

        if (timeoutId) {
            clearTimeout(timeoutId);
        }

        timeoutId = setTimeout(async () => {
            lastExecutionTime = Date.now();
            await fn();
            timeoutId = null;
        }, Math.max(0, delayMs - timeSinceLastExecution));
    };

    debounced.cancel = () => {
        if (timeoutId) {
            clearTimeout(timeoutId);
            timeoutId = null;
        }
    };

    return debounced;
}

/**
 * Creates a simple button disable guard to prevent multiple clicks.
 * Automatically re-enables the button after the operation completes.
 *
 * @param buttonId - ID of the button to guard
 * @param fn - Async function to execute
 */
export async function withButtonGuard(
    buttonId: string,
    fn: () => Promise<void>
): Promise<void> {
    const button = document.getElementById(buttonId) as HTMLButtonElement | null;
    if (!button) {
        console.warn(`Button with ID "${buttonId}" not found`);
        return;
    }

    if (button.disabled) {
        console.warn('Button is already processing');
        return;
    }

    button.disabled = true;
    const originalText = button.textContent;

    try {
        button.textContent = 'Processing...';
        await fn();
    } finally {
        button.disabled = false;
        button.textContent = originalText;
    }
}
