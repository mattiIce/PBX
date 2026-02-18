// Constants for API endpoint detection
const STANDARD_HTTP_PORT = '80';
const STANDARD_HTTPS_PORT = '443';
const API_PORT = '9000';

export const DEFAULT_FETCH_TIMEOUT = 30000; // 30 seconds for general requests

/**
 * Options passed to fetchWithTimeout, extending the standard RequestInit
 * but disallowing a custom abort signal (timeout is managed internally).
 */
export interface FetchOptions extends Omit<RequestInit, 'signal'> {
    signal?: never;
}

/**
 * Headers returned by getAuthHeaders, always including Content-Type
 * and optionally including an Authorization bearer token.
 */
/**
 * Type alias for auth headers - compatible with HeadersInit / Record<string, string>.
 * Always includes Content-Type; Authorization is added when a token is available.
 */
export type AuthHeaders = Record<string, string>;

/**
 * Generic shape for JSON responses returned by the PBX API.
 */
export interface ApiResponse<T = unknown> {
    success: boolean;
    data?: T;
    error?: string;
    message?: string;
}

/**
 * Detect the API base URL based on the current page location.
 * Checks for a meta tag override, then falls back to port-based detection.
 */
export function getApiBaseUrl(): string {
    // Check for meta tag override first
    const apiMeta = document.querySelector('meta[name="api-base-url"]') as HTMLMetaElement | null;
    if (apiMeta && apiMeta.content) {
        return apiMeta.content;
    }

    // If we're on the API port, use current origin
    if (window.location.port === API_PORT) {
        return window.location.origin;
    }

    // If accessed through reverse proxy or standard HTTP/HTTPS ports,
    // try same origin first (API should be proxied)
    if (window.location.port === '' ||
        window.location.port === STANDARD_HTTP_PORT ||
        window.location.port === STANDARD_HTTPS_PORT) {
        return window.location.origin;
    }

    // Fallback: use current hostname with API port (direct API access)
    const protocol = window.location.protocol;
    const hostname = window.location.hostname || 'localhost';
    return `${protocol}//${hostname}:${API_PORT}`;
}

/**
 * Build authorization headers from the stored JWT token.
 */
export function getAuthHeaders(): AuthHeaders {
    const token = localStorage.getItem('pbx_token');
    const headers: AuthHeaders = {
        'Content-Type': 'application/json'
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
}

/**
 * Fetch wrapper that enforces a timeout via AbortController.
 * Throws 'Request timed out' on timeout. Does not accept custom abort signals.
 */
export async function fetchWithTimeout(
    url: string,
    options: FetchOptions = {},
    timeout: number = DEFAULT_FETCH_TIMEOUT
): Promise<Response> {
    // Prevent caller from passing their own signal which would conflict with timeout
    if ((options as RequestInit).signal) {
        throw new Error('fetchWithTimeout does not support custom abort signals. Use the timeout parameter instead.');
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        return response;
    } catch (error: unknown) {
        if (error instanceof Error && error.name === 'AbortError') {
            throw new Error('Request timed out');
        }
        throw error;
    } finally {
        // Always clear timeout to prevent memory leaks
        clearTimeout(timeoutId);
    }
}

/**
 * Fetch with automatic retry on network errors using exponential backoff.
 * Only retries on network failures and 5xx server errors, not on 4xx client errors.
 */
export async function fetchWithRetry(
    url: string,
    options: FetchOptions = {},
    {
        maxRetries = 3,
        baseDelay = 1000,
        timeout = DEFAULT_FETCH_TIMEOUT,
    }: { maxRetries?: number; baseDelay?: number; timeout?: number } = {}
): Promise<Response> {
    let lastError: Error | undefined;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            const response = await fetchWithTimeout(url, options, timeout);

            // Don't retry on client errors (4xx) - only on server errors (5xx)
            if (response.status < 500) {
                return response;
            }

            // Server error - retry if attempts remain
            if (attempt < maxRetries) {
                const delay = baseDelay * Math.pow(2, attempt);
                await new Promise(resolve => setTimeout(resolve, delay));
                continue;
            }

            return response;
        } catch (error: unknown) {
            lastError = error instanceof Error ? error : new Error(String(error));

            // Don't retry on timeout or if no retries left
            if (lastError.message === 'Request timed out' || attempt >= maxRetries) {
                throw lastError;
            }

            // Exponential backoff before retry
            const delay = baseDelay * Math.pow(2, attempt);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }

    throw lastError ?? new Error('Request failed after retries');
}

/**
 * Handle 401 responses by clearing auth state and redirecting to login.
 * Returns true if the response was a 401 (caller should stop processing).
 */
export function handleUnauthorized(response: Response): boolean {
    if (response.status === 401) {
        localStorage.removeItem('pbx_token');
        localStorage.removeItem('pbx_extension');
        localStorage.removeItem('pbx_is_admin');
        localStorage.removeItem('pbx_name');
        window.location.href = '/admin/login.html';
        return true;
    }
    return false;
}

/**
 * Convenience wrapper: fetch with auth headers, retry, and automatic 401 handling.
 */
export async function apiFetch<T = unknown>(
    path: string,
    options: FetchOptions = {}
): Promise<ApiResponse<T>> {
    const url = `${getApiBaseUrl()}${path}`;
    const headers = { ...getAuthHeaders(), ...options.headers as Record<string, string> };

    const response = await fetchWithRetry(url, { ...options, headers });

    if (handleUnauthorized(response)) {
        return { success: false, error: 'Session expired' };
    }

    return response.json() as Promise<ApiResponse<T>>;
}
