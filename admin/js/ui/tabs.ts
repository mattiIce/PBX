import { store } from '../state/store.ts';

const AUTO_REFRESH_INTERVAL_MS = 10000; // 10 seconds

// Track the auto-refresh interval handle locally
let autoRefreshInterval: ReturnType<typeof setInterval> | null = null;

// Auto-refresh wrapper functions - defined once to avoid recreation on tab switch

/** Wrapper for emergency tab: refresh both contacts and history */
function refreshEmergencyTab(): void {
    if (typeof (window as any).loadEmergencyContacts === 'function') (window as any).loadEmergencyContacts();
    if (typeof (window as any).loadEmergencyHistory === 'function') (window as any).loadEmergencyHistory();
}

/** Wrapper for fraud detection tab */
function refreshFraudDetectionTab(): void {
    if (typeof (window as any).loadFraudAlerts === 'function') {
        (window as any).loadFraudAlerts();
    }
}

/** Wrapper for callback queue tab */
function refreshCallbackQueueTab(): void {
    if (typeof (window as any).loadCallbackQueue === 'function') {
        (window as any).loadCallbackQueue();
    }
}

/**
 * Setup auto-refresh for tabs that need periodic data updates.
 */
function setupAutoRefresh(tabName: string): void {
    // Clear any existing auto-refresh interval
    if (autoRefreshInterval) {
        console.log(`Clearing existing auto-refresh interval for tab: ${store.get('currentTab')}`);
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }

    // Define which tabs should auto-refresh and their refresh functions
    const autoRefreshTabs: Record<string, () => void> = {
        // System Overview
        'dashboard': () => (window as any).loadDashboard && (window as any).loadDashboard(),
        'analytics': () => (window as any).loadAnalytics && (window as any).loadAnalytics(),

        // Communication & Calls
        'calls': () => (window as any).loadCalls && (window as any).loadCalls(),
        'qos': () => (window as any).loadQoSMetrics && (window as any).loadQoSMetrics(),
        'emergency': refreshEmergencyTab,
        'callback-queue': refreshCallbackQueueTab,

        // Extensions & Devices
        'extensions': () => (window as any).loadExtensions && (window as any).loadExtensions(),
        'phones': () => (window as any).loadRegisteredPhones && (window as any).loadRegisteredPhones(),
        'atas': () => (window as any).loadRegisteredATAs && (window as any).loadRegisteredATAs(),
        'hot-desking': () => (window as any).loadHotDeskSessions && (window as any).loadHotDeskSessions(),

        // User Features
        'voicemail': () => (window as any).loadVoicemailTab && (window as any).loadVoicemailTab(),

        // Security
        'fraud-detection': refreshFraudDetectionTab
    };

    // If the current tab supports auto-refresh, set it up
    if (autoRefreshTabs[tabName]) {
        console.log(`Setting up auto-refresh for tab: ${tabName} (interval: ${AUTO_REFRESH_INTERVAL_MS}ms)`);
        autoRefreshInterval = setInterval(() => {
            console.log(`Auto-refreshing tab: ${tabName}`);
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
        console.log(`Auto-refresh interval ID: ${autoRefreshInterval}`);
    } else {
        console.log(`Tab ${tabName} does not support auto-refresh`);
    }

    store.set('autoRefreshInterval', autoRefreshInterval as unknown as number | null);
}

/**
 * Switch to the given tab: update UI active states, load tab data,
 * and configure auto-refresh.
 */
export function showTab(tabName: string): void {
    console.log(`showTab called with: ${tabName}`);

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
        case 'dashboard':           (window as any).loadDashboard && (window as any).loadDashboard(); break;
        case 'analytics':           (window as any).loadAnalytics && (window as any).loadAnalytics(); break;
        case 'extensions':          (window as any).loadExtensions && (window as any).loadExtensions(); break;
        case 'phones':              (window as any).loadRegisteredPhones && (window as any).loadRegisteredPhones(); break;
        case 'atas':                (window as any).loadRegisteredATAs && (window as any).loadRegisteredATAs(); break;
        case 'provisioning':        (window as any).loadProvisioning && (window as any).loadProvisioning(); break;
        case 'auto-attendant':      (window as any).loadAutoAttendantConfig && (window as any).loadAutoAttendantConfig(); break;
        case 'voicemail':           (window as any).loadVoicemailTab && (window as any).loadVoicemailTab(); break;
        case 'paging':              (window as any).loadPagingData && (window as any).loadPagingData(); break;
        case 'calls':               (window as any).loadCalls && (window as any).loadCalls(); break;
        case 'config':              (window as any).loadConfig && (window as any).loadConfig(); break;
        case 'features-status':     (window as any).loadFeaturesStatus && (window as any).loadFeaturesStatus(); break;
        case 'webrtc-phone':        (window as any).loadWebRTCPhoneConfig && (window as any).loadWebRTCPhoneConfig(); break;
        case 'license-management':  (window as any).initLicenseManagement && (window as any).initLicenseManagement(); break;
        case 'qos':                 (window as any).loadQoSMetrics && (window as any).loadQoSMetrics(); break;
        case 'emergency':
            if ((window as any).loadEmergencyContacts) (window as any).loadEmergencyContacts();
            if ((window as any).loadEmergencyHistory) (window as any).loadEmergencyHistory();
            break;
        case 'codecs':
            if ((window as any).loadCodecStatus) (window as any).loadCodecStatus();
            if ((window as any).loadDTMFConfig) (window as any).loadDTMFConfig();
            break;
        case 'sip-trunks':
            if ((window as any).loadSIPTrunks) (window as any).loadSIPTrunks();
            if ((window as any).loadTrunkHealth) (window as any).loadTrunkHealth();
            break;
        case 'least-cost-routing':
            if ((window as any).loadLCRRates) (window as any).loadLCRRates();
            if ((window as any).loadLCRStatistics) (window as any).loadLCRStatistics();
            break;
        case 'find-me-follow-me':   (window as any).loadFMFMExtensions && (window as any).loadFMFMExtensions(); break;
        case 'time-routing':        (window as any).loadTimeRoutingRules && (window as any).loadTimeRoutingRules(); break;
        case 'webhooks':            (window as any).loadWebhooks && (window as any).loadWebhooks(); break;
        case 'hot-desking':         (window as any).loadHotDeskSessions && (window as any).loadHotDeskSessions(); break;
        case 'recording-retention': (window as any).loadRetentionPolicies && (window as any).loadRetentionPolicies(); break;
        case 'jitsi-integration':   typeof (window as any).loadJitsiConfig === 'function' && (window as any).loadJitsiConfig(); break;
        case 'matrix-integration':  typeof (window as any).loadMatrixConfig === 'function' && (window as any).loadMatrixConfig(); break;
        case 'espocrm-integration': typeof (window as any).loadEspoCRMConfig === 'function' && (window as any).loadEspoCRMConfig(); break;
        case 'click-to-dial':       typeof (window as any).loadClickToDialTab === 'function' && (window as any).loadClickToDialTab(); break;
        case 'fraud-detection':     typeof (window as any).loadFraudDetectionData === 'function' && (window as any).loadFraudDetectionData(); break;
        case 'nomadic-e911':        typeof (window as any).loadNomadicE911Data === 'function' && (window as any).loadNomadicE911Data(); break;
        case 'callback-queue':      typeof (window as any).loadCallbackQueue === 'function' && (window as any).loadCallbackQueue(); break;
        case 'mobile-push':         typeof (window as any).loadMobilePushConfig === 'function' && (window as any).loadMobilePushConfig(); break;
        case 'recording-announcements': typeof (window as any).loadRecordingAnnouncements === 'function' && (window as any).loadRecordingAnnouncements(); break;
        case 'speech-analytics':    typeof (window as any).loadSpeechAnalyticsConfigs === 'function' && (window as any).loadSpeechAnalyticsConfigs(); break;
        case 'compliance':          typeof (window as any).loadComplianceData === 'function' && (window as any).loadComplianceData(); break;
        case 'crm-integrations':    typeof (window as any).loadCRMActivityLog === 'function' && (window as any).loadCRMActivityLog(); break;
        case 'opensource-integrations': typeof (window as any).loadOpenSourceIntegrations === 'function' && (window as any).loadOpenSourceIntegrations(); break;
    }
}

/**
 * Bind click handlers to all .tab-button elements.
 */
export function initializeTabs(): void {
    console.log('Initializing tab click handlers');
    const tabButtons = document.querySelectorAll('.tab-button');
    console.log(`Found ${tabButtons.length} tab buttons`);

    tabButtons.forEach(button => {
        button.addEventListener('click', function (this: HTMLElement) {
            const tabName = this.getAttribute('data-tab');
            console.log(`Tab button clicked: ${tabName}`);
            showTab(tabName!);
        });
    });
}
