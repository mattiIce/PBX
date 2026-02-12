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
export interface AuthHeaders {
    'Content-Type': string;
    Authorization?: string;
}

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
