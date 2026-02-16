import { store } from '../state/store.ts';

const AUTO_REFRESH_INTERVAL_MS = 10000; // 10 seconds

// Track the auto-refresh interval handle locally
let autoRefreshInterval: ReturnType<typeof setInterval> | null = null;

// Auto-refresh wrapper functions - defined once to avoid recreation on tab switch

/** Wrapper for emergency tab: refresh both contacts and history */
function refreshEmergencyTab(): void {
    if (typeof window.loadEmergencyContacts === 'function') window.loadEmergencyContacts();
    if (typeof window.loadEmergencyHistory === 'function') window.loadEmergencyHistory();
}

/** Wrapper for fraud detection tab */
function refreshFraudDetectionTab(): void {
    if (typeof window.loadFraudAlerts === 'function') {
        window.loadFraudAlerts();
    }
}

/** Wrapper for callback queue tab */
function refreshCallbackQueueTab(): void {
    if (typeof window.loadCallbackQueue === 'function') {
        window.loadCallbackQueue();
    }
}

/**
 * Setup auto-refresh for tabs that need periodic data updates.
 */
function setupAutoRefresh(tabName: string): void {
    // Clear any existing auto-refresh interval
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }

    // Define which tabs should auto-refresh and their refresh functions
    const autoRefreshTabs: Record<string, () => void> = {
        // System Overview
        'dashboard': () => window.loadDashboard?.(),
        'analytics': () => window.loadAnalytics?.(),

        // Communication & Calls
        'calls': () => window.loadCalls?.(),
        'qos': () => window.loadQoSMetrics?.(),
        'emergency': refreshEmergencyTab,
        'callback-queue': refreshCallbackQueueTab,

        // Extensions & Devices
        'extensions': () => window.loadExtensions?.(),
        'phones': () => window.loadRegisteredPhones?.(),
        'atas': () => window.loadRegisteredATAs?.(),
        'hot-desking': () => window.loadHotDeskSessions?.(),

        // User Features
        'voicemail': () => window.loadVoicemailTab?.(),

        // Security
        'fraud-detection': refreshFraudDetectionTab
    };

    // If the current tab supports auto-refresh, set it up
    if (autoRefreshTabs[tabName]) {
        autoRefreshInterval = setInterval(() => {
            try {
                const refreshFunction = autoRefreshTabs[tabName];
                if (typeof refreshFunction === 'function') {
                    refreshFunction();
                } else {
                    console.error(`Auto-refresh function for ${tabName} is not a function:`, refreshFunction);
                }
            } catch (error: unknown) {
                console.error(`Error during auto-refresh of ${tabName}:`, error);
                if (error instanceof Error && error.message?.includes('401')) {
                    console.warn('Authentication error during auto-refresh - user may need to re-login');
                }
            }
        }, AUTO_REFRESH_INTERVAL_MS);
    }

    store.set('autoRefreshInterval', autoRefreshInterval as unknown as number | null);
}

/**
 * Switch to the given tab: update UI active states, load tab data,
 * and configure auto-refresh.
 */
export function showTab(tabName: string): void {
    // Hide all tabs
    for (const tab of document.querySelectorAll('.tab-content')) {
        (tab as HTMLElement).classList.remove('active');
    }

    // Remove active from all buttons
    for (const button of document.querySelectorAll('.tab-button')) {
        (button as HTMLElement).classList.remove('active');
    }

    // Show selected tab
    const tabElement = document.getElementById(tabName) as HTMLElement | null;
    if (!tabElement) {
        console.error(`CRITICAL: Tab element with id '${tabName}' not found in DOM`);
        console.error('This may indicate a UI template issue or incorrect tab name');
        console.error(`Current tab name: "${tabName}"`);
    } else {
        tabElement.classList.add('active');
        const tabButton = document.querySelector(`[data-tab="${tabName}"]`) as HTMLElement | null;
        if (tabButton) {
            tabButton.classList.add('active');
        } else {
            console.warn(`Tab button for '${tabName}' not found`);
        }
    }

    // Update current tab and setup auto-refresh
    store.set('currentTab', tabName);
    setupAutoRefresh(tabName);

    // Tab-to-loader mapping for single-loader tabs
    const tabLoaders: Record<string, (() => void) | undefined> = {
        'dashboard':           window.loadDashboard,
        'analytics':           window.loadAnalytics,
        'extensions':          window.loadExtensions,
        'phones':              window.loadRegisteredPhones,
        'atas':                window.loadRegisteredATAs,
        'provisioning':        window.loadProvisioning,
        'auto-attendant':      window.loadAutoAttendantConfig,
        'voicemail':           window.loadVoicemailTab,
        'paging':              window.loadPagingData,
        'calls':               window.loadCalls,
        'config':              window.loadConfig,
        'features-status':     window.loadFeaturesStatus,
        'webrtc-phone':        window.loadWebRTCPhoneConfig,
        'license-management':  window.initLicenseManagement,
        'qos':                 window.loadQoSMetrics,
        'find-me-follow-me':   window.loadFMFMExtensions,
        'time-routing':        window.loadTimeRoutingRules,
        'webhooks':            window.loadWebhooks,
        'hot-desking':         window.loadHotDeskSessions,
        'recording-retention': window.loadRetentionPolicies,
        'jitsi-integration':   window.loadJitsiConfig,
        'matrix-integration':  window.loadMatrixConfig,
        'espocrm-integration': window.loadEspoCRMConfig,
        'click-to-dial':       window.loadClickToDialTab,
        'fraud-detection':     window.loadFraudDetectionData,
        'nomadic-e911':        window.loadNomadicE911Data,
        'callback-queue':      window.loadCallbackQueue,
        'mobile-push':         window.loadMobilePushConfig,
        'recording-announcements': window.loadRecordingAnnouncements,
        'speech-analytics':    window.loadSpeechAnalyticsConfigs,
        'compliance':          window.loadComplianceData,
        'crm-integrations':    window.loadCRMActivityLog,
        'opensource-integrations': window.loadOpenSourceIntegrations,
    };

    // Tabs with multiple loaders
    const multiLoaderTabs: Record<string, ((() => void) | undefined)[]> = {
        'emergency':           [window.loadEmergencyContacts, window.loadEmergencyHistory],
        'codecs':              [window.loadCodecStatus, window.loadDTMFConfig],
        'sip-trunks':          [window.loadSIPTrunks, window.loadTrunkHealth],
        'least-cost-routing':  [window.loadLCRRates, window.loadLCRStatistics],
    };

    // Load data for the tab
    const singleLoader = tabLoaders[tabName];
    if (singleLoader) {
        singleLoader();
    } else {
        const loaders = multiLoaderTabs[tabName];
        if (loaders) {
            for (const loader of loaders) {
                loader?.();
            }
        }
    }
}

/**
 * Bind click handlers to all .tab-button elements.
 */
export function initializeTabs(): void {
    const tabButtons = document.querySelectorAll('.tab-button');

    for (const button of tabButtons) {
        button.addEventListener('click', () => {
            const tabName = (button as HTMLElement).getAttribute('data-tab');
            if (tabName) showTab(tabName);
        });
    }
}
