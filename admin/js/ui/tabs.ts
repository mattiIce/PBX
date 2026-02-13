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
        'dashboard': () => window.loadDashboard && window.loadDashboard(),
        'analytics': () => window.loadAnalytics && window.loadAnalytics(),

        // Communication & Calls
        'calls': () => window.loadCalls && window.loadCalls(),
        'qos': () => window.loadQoSMetrics && window.loadQoSMetrics(),
        'emergency': refreshEmergencyTab,
        'callback-queue': refreshCallbackQueueTab,

        // Extensions & Devices
        'extensions': () => window.loadExtensions && window.loadExtensions(),
        'phones': () => window.loadRegisteredPhones && window.loadRegisteredPhones(),
        'atas': () => window.loadRegisteredATAs && window.loadRegisteredATAs(),
        'hot-desking': () => window.loadHotDeskSessions && window.loadHotDeskSessions(),

        // User Features
        'voicemail': () => window.loadVoicemailTab && window.loadVoicemailTab(),

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
                if (error instanceof Error && error.message && error.message.includes('401')) {
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
    document.querySelectorAll('.tab-content').forEach(tab => {
        (tab as HTMLElement).classList.remove('active');
    });

    // Remove active from all buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        (button as HTMLElement).classList.remove('active');
    });

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

    // Load data for the tab
    switch (tabName) {
        case 'dashboard':           window.loadDashboard && window.loadDashboard(); break;
        case 'analytics':           window.loadAnalytics && window.loadAnalytics(); break;
        case 'extensions':          window.loadExtensions && window.loadExtensions(); break;
        case 'phones':              window.loadRegisteredPhones && window.loadRegisteredPhones(); break;
        case 'atas':                window.loadRegisteredATAs && window.loadRegisteredATAs(); break;
        case 'provisioning':        window.loadProvisioning && window.loadProvisioning(); break;
        case 'auto-attendant':      window.loadAutoAttendantConfig && window.loadAutoAttendantConfig(); break;
        case 'voicemail':           window.loadVoicemailTab && window.loadVoicemailTab(); break;
        case 'paging':              window.loadPagingData && window.loadPagingData(); break;
        case 'calls':               window.loadCalls && window.loadCalls(); break;
        case 'config':              window.loadConfig && window.loadConfig(); break;
        case 'features-status':     window.loadFeaturesStatus && window.loadFeaturesStatus(); break;
        case 'webrtc-phone':        window.loadWebRTCPhoneConfig && window.loadWebRTCPhoneConfig(); break;
        case 'license-management':  window.initLicenseManagement && window.initLicenseManagement(); break;
        case 'qos':                 window.loadQoSMetrics && window.loadQoSMetrics(); break;
        case 'emergency':
            if (window.loadEmergencyContacts) window.loadEmergencyContacts();
            if (window.loadEmergencyHistory) window.loadEmergencyHistory();
            break;
        case 'codecs':
            if (window.loadCodecStatus) window.loadCodecStatus();
            if (window.loadDTMFConfig) window.loadDTMFConfig();
            break;
        case 'sip-trunks':
            if (window.loadSIPTrunks) window.loadSIPTrunks();
            if (window.loadTrunkHealth) window.loadTrunkHealth();
            break;
        case 'least-cost-routing':
            if (window.loadLCRRates) window.loadLCRRates();
            if (window.loadLCRStatistics) window.loadLCRStatistics();
            break;
        case 'find-me-follow-me':   window.loadFMFMExtensions && window.loadFMFMExtensions(); break;
        case 'time-routing':        window.loadTimeRoutingRules && window.loadTimeRoutingRules(); break;
        case 'webhooks':            window.loadWebhooks && window.loadWebhooks(); break;
        case 'hot-desking':         window.loadHotDeskSessions && window.loadHotDeskSessions(); break;
        case 'recording-retention': window.loadRetentionPolicies && window.loadRetentionPolicies(); break;
        case 'jitsi-integration':   typeof window.loadJitsiConfig === 'function' && window.loadJitsiConfig(); break;
        case 'matrix-integration':  typeof window.loadMatrixConfig === 'function' && window.loadMatrixConfig(); break;
        case 'espocrm-integration': typeof window.loadEspoCRMConfig === 'function' && window.loadEspoCRMConfig(); break;
        case 'click-to-dial':       typeof window.loadClickToDialTab === 'function' && window.loadClickToDialTab(); break;
        case 'fraud-detection':     typeof window.loadFraudDetectionData === 'function' && window.loadFraudDetectionData(); break;
        case 'nomadic-e911':        typeof window.loadNomadicE911Data === 'function' && window.loadNomadicE911Data(); break;
        case 'callback-queue':      typeof window.loadCallbackQueue === 'function' && window.loadCallbackQueue(); break;
        case 'mobile-push':         typeof window.loadMobilePushConfig === 'function' && window.loadMobilePushConfig(); break;
        case 'recording-announcements': typeof window.loadRecordingAnnouncements === 'function' && window.loadRecordingAnnouncements(); break;
        case 'speech-analytics':    typeof window.loadSpeechAnalyticsConfigs === 'function' && window.loadSpeechAnalyticsConfigs(); break;
        case 'compliance':          typeof window.loadComplianceData === 'function' && window.loadComplianceData(); break;
        case 'crm-integrations':    typeof window.loadCRMActivityLog === 'function' && window.loadCRMActivityLog(); break;
        case 'opensource-integrations': typeof window.loadOpenSourceIntegrations === 'function' && window.loadOpenSourceIntegrations(); break;
    }
}

/**
 * Bind click handlers to all .tab-button elements.
 */
export function initializeTabs(): void {
    const tabButtons = document.querySelectorAll('.tab-button');

    tabButtons.forEach(button => {
        button.addEventListener('click', function (this: HTMLElement) {
            const tabName = this.getAttribute('data-tab');
            showTab(tabName!);
        });
    });
}
