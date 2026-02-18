import { showNotification } from '../ui/notifications.ts';

/**
 * Execute promise-returning functions in batches to avoid overwhelming the rate limiter.
 * IMPORTANT: Pass functions that return promises, not promises themselves.
 * This ensures requests don't start until the batch is ready to execute them.
 *
 * @param promiseFunctions - Array of functions that return promises
 * @param batchSize - Number of promises to execute concurrently (default: 5)
 * @param delayMs - Delay in milliseconds between batches (default: 1000)
 * @returns Results from Promise.allSettled for all promises
 */
export async function executeBatched(
    promiseFunctions: Array<(() => Promise<unknown>) | Promise<unknown>>,
    batchSize = 5,
    delayMs = 1000,
): Promise<PromiseSettledResult<unknown>[]> {
    if (!Array.isArray(promiseFunctions)) {
        throw new TypeError('promiseFunctions must be an array');
    }

    const results: PromiseSettledResult<unknown>[] = [];

    for (let i = 0; i < promiseFunctions.length; i += batchSize) {
        const batchFunctions = promiseFunctions.slice(i, i + batchSize);

        // Create promises only when ready to execute (lazy evaluation)
        const batchPromises = batchFunctions.map(fn =>
            typeof fn === 'function' ? fn() : fn,
        );

        const batchResults = await Promise.allSettled(batchPromises);
        results.push(...batchResults);

        // Add delay between batches (except after the last batch)
        if (i + batchSize < promiseFunctions.length) {
            await new Promise(resolve => setTimeout(resolve, delayMs));
        }
    }

    return results;
}

/**
 * Refresh all tab data regardless of which tab is currently active.
 * Uses batched execution to avoid overwhelming the API rate limiter.
 */
export async function refreshAllData(): Promise<void> {
    const refreshBtn = document.getElementById('refresh-all-button');
    if (!refreshBtn) return;

    // Prevent concurrent refresh operations
    if ((refreshBtn as HTMLButtonElement).disabled) return;

    const originalText = refreshBtn.textContent;
    const originalDisabled = (refreshBtn as HTMLButtonElement).disabled;

    try {
        refreshBtn.textContent = '\u23F3 Refreshing All Tabs...';
        (refreshBtn as HTMLButtonElement).disabled = true;

        // Suppress error notifications during bulk refresh to avoid notification spam
        (window as unknown as Record<string, unknown>).suppressErrorNotifications = true;

        console.log('Refreshing all data for ALL tabs...');

        // Collect ALL tab refresh functions for batched execution
        const refreshFunctions: Array<() => Promise<void>> = [];

        if (window.loadDashboard) refreshFunctions.push(() => window.loadDashboard());
        if (window.loadADStatus) refreshFunctions.push(() => window.loadADStatus());
        if (window.loadAnalytics) refreshFunctions.push(() => window.loadAnalytics());
        if (window.loadExtensions) refreshFunctions.push(() => window.loadExtensions());

        const results = await executeBatched(refreshFunctions, 5, 1000);

        const failures = results.filter(r => r.status === 'rejected');
        if (failures.length > 0) {
            console.info(
                `${failures.length} refresh operation(s) failed (expected for unavailable features):`,
                failures.map(f => (f as PromiseRejectedResult).reason?.message ?? (f as PromiseRejectedResult).reason),
            );
        }
        showNotification('\u2705 All tabs refreshed successfully', 'success');
    } catch (error: unknown) {
        const message = error instanceof Error ? error.message : String(error);
        console.error('Error refreshing data:', error);
        showNotification(`Failed to refresh: ${message}`, 'error');
    } finally {
        (window as unknown as Record<string, unknown>).suppressErrorNotifications = false;

        refreshBtn.textContent = originalText;
        (refreshBtn as HTMLButtonElement).disabled = originalDisabled;
    }
}

/**
 * Attach the refreshAllData handler to the refresh-all button.
 * Call this once during application initialization.
 */
export function initializeRefreshButton(): void {
    const refreshBtn = document.getElementById('refresh-all-button');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshAllData);
    }
}

// Backward compatibility: register on the window object
(window as unknown as Record<string, unknown>).executeBatched = executeBatched;
(window as unknown as Record<string, unknown>).refreshAllData = refreshAllData;
