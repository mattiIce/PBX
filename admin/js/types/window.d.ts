export {};

declare global {
    interface Window {
        // api/client.ts
        fetchWithTimeout: (url: string, options?: RequestInit, timeout?: number) => Promise<Response>;
        getAuthHeaders: () => { 'Content-Type': string; Authorization?: string };
        getApiBaseUrl: () => string;
        DEFAULT_FETCH_TIMEOUT: number;

        // state/store.ts
        store: {
            get<K extends string>(key: K): unknown;
            set<K extends string>(key: K, value: unknown): void;
            subscribe<K extends string>(key: K, callback: (value: unknown) => void): () => void;
            getState(): Record<string, unknown>;
        };

        // ui/notifications.ts
        showNotification: (message: string, type?: 'success' | 'error' | 'warning' | 'info') => void;
        displayError: (error: Error | { message?: string; stack?: string; toString(): string }, context?: string) => void;
        setSuppressErrorNotifications: (value: boolean) => void;

        // ui/tabs.ts
        showTab: (tabName: string) => void;
        switchTab: (tabName: string) => void;
        initializeTabs: () => void;

        // utils/html.ts
        escapeHtml: (text: string) => string;
        copyToClipboard: (text: string) => Promise<void>;

        // pages/dashboard.ts
        loadDashboard: () => Promise<void>;
        refreshDashboard: () => void;
        loadADStatus: () => Promise<void>;
        refreshADStatus: () => void;
        syncADUsers: () => Promise<void>;

        // pages/extensions.ts
        currentExtensions: unknown[];
        loadExtensions: () => Promise<void>;
        showAddExtensionModal: () => void;
        closeAddExtensionModal: () => void;
        editExtension: (number: string) => void;
        closeEditExtensionModal: () => void;
        deleteExtension: (number: string) => Promise<void>;
        rebootPhone: (extension: string) => Promise<void>;
        rebootAllPhones: () => Promise<void>;

        // pages/voicemail.ts
        loadVoicemailTab: () => Promise<void>;
        loadVoicemailForExtension: () => Promise<void>;
        playVoicemail: (extension: string, messageId: string) => Promise<void>;
        downloadVoicemail: (extension: string, messageId: string) => Promise<void>;
        deleteVoicemail: (extension: string, messageId: string) => Promise<void>;
        markVoicemailRead: (extension: string, messageId: string) => Promise<void>;

        // pages/calls.ts
        loadCalls: () => Promise<void>;
        loadCodecStatus: () => Promise<void>;
        loadDTMFConfig: () => Promise<void>;
        saveDTMFConfig: () => Promise<void>;

        // pages/config.ts
        loadConfig: () => Promise<void>;
        loadFeaturesStatus: () => Promise<void>;
        saveConfigSection: (section: string) => Promise<void>;
        loadSSLStatus: () => Promise<void>;
        generateSSLCertificate: () => Promise<void>;

        // pages/provisioning.ts
        loadProvisioning: () => Promise<void>;
        loadSupportedVendors: () => Promise<void>;
        loadProvisioningDevices: () => Promise<void>;
        loadProvisioningTemplates: () => Promise<void>;
        loadProvisioningSettings: () => Promise<void>;
        loadPhonebookSettings: () => Promise<void>;
        deleteDevice: (macAddress: string) => Promise<void>;
        viewTemplate: (name: string) => void;

        // pages/phones.ts
        loadRegisteredPhones: () => Promise<void>;
        loadRegisteredATAs: () => Promise<void>;

        // pages/security.ts
        loadFraudAlerts: () => Promise<void>;
        loadCallbackQueue: () => Promise<void>;
        startCallback: (callbackId: string) => Promise<void>;
        cancelCallback: (callbackId: string) => Promise<void>;
        loadMobilePushDevices: () => Promise<void>;
        loadSpeechAnalyticsConfigs: () => Promise<void>;

        // pages/emergency.ts
        loadEmergencyContacts: () => Promise<void>;
        loadEmergencyHistory: () => Promise<void>;
        deleteEmergencyContact: (contactId: string) => Promise<void>;
        loadE911Sites: () => Promise<void>;
        loadExtensionLocations: () => Promise<void>;

        // pages/phone_book.ts
        loadPhoneBook: () => Promise<void>;
        deletePhoneBookEntry: (entryId: string) => Promise<void>;

        // pages/paging.ts
        loadPagingData: () => Promise<void>;
        loadPagingZones: () => Promise<void>;
        loadPagingDevices: () => Promise<void>;
        loadActivePages: () => Promise<void>;
        deletePagingZone: (zoneId: string) => Promise<void>;

        // pages/license.ts
        loadLicenseStatus: () => Promise<void>;
        loadLicenseFeatures: () => Promise<void>;
        installLicense: () => Promise<void>;
        initLicenseManagement: () => void;

        // pages/analytics.ts
        loadAnalytics: () => Promise<void>;
        loadQoSMetrics: () => Promise<void>;

        // Functions referenced in tabs.ts from .js modules (not yet ported to .ts)
        loadAutoAttendantConfig?: () => void;
        loadWebRTCPhoneConfig?: () => void;
        loadSIPTrunks?: () => void;
        loadTrunkHealth?: () => void;
        loadLCRRates?: () => void;
        loadLCRStatistics?: () => void;
        loadFMFMExtensions?: () => void;
        loadTimeRoutingRules?: () => void;
        loadWebhooks?: () => void;
        loadHotDeskSessions?: () => void;
        loadRetentionPolicies?: () => void;
        loadJitsiConfig?: () => void;
        loadMatrixConfig?: () => void;
        loadEspoCRMConfig?: () => void;
        loadClickToDialTab?: () => void;
        loadFraudDetectionData?: () => void;
        loadNomadicE911Data?: () => void;
        loadMobilePushConfig?: () => void;
        loadRecordingAnnouncements?: () => void;
        loadComplianceData?: () => void;
        loadCRMActivityLog?: () => void;
        loadOpenSourceIntegrations?: () => void;

        // pages/phone_book.ts — referenced in onclick handlers
        editPhoneBookEntry?: (entryId: string) => void;

        // pages/emergency.ts — referenced in onclick handlers
        editE911Site?: (siteId: string) => void;
        deleteE911Site?: (siteId: string) => void;
    }
}
