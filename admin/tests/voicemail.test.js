/**
 * @jest-environment jsdom
 */

const { describe, it, expect, beforeEach } = require('@jest/globals');

// Mock fetch and DOM
global.fetch = jest.fn();
global.localStorage = { getItem: jest.fn(), setItem: jest.fn(), clear: jest.fn() };

// Set up DOM
document.body.innerHTML = `
  <select id="vm-extension-select"></select>
  <div id="voicemail-pin-section"></div>
  <div id="voicemail-messages-section"></div>
  <div id="voicemail-box-overview"></div>
  <span id="vm-current-extension"></span>
  <div id="voicemail-cards-view"></div>
`;

// Mock dependencies that voicemail.js imports
// Since the modules use window.* backward compatibility exports,
// we can set up global mocks and then use dynamic import
global.getAuthHeaders = jest.fn(() => ({
  'Content-Type': 'application/json',
  'Authorization': 'Bearer test-token'
}));
global.showNotification = jest.fn();
global.getApiBaseUrl = jest.fn(() => 'http://localhost:9000');

// The page modules self-register on window.*, so we can use the window globals
// after loading the module, or we test the window.* exports directly
//
// NOTE: The voicemail module (admin/js/pages/voicemail.js) exports:
//   - loadVoicemailTab()
//   - loadVoicemailForExtension() - reads extension from DOM #vm-extension-select
//   - playVoicemail(), downloadVoicemail(), deleteVoicemail(), markVoicemailRead()
//
// These are also registered as window.* for backward compatibility.
// Since Jest/jsdom doesn't natively support ES module imports, we test
// the functions via window.* globals set by the module's backward-compat layer.
// The functions are loaded by requiring the module after globals are set up.

// Since the actual ES module uses import { getAuthHeaders, getApiBaseUrl } from '../api/client.js'
// and import { showNotification } from '../ui/notifications.js', but in the test environment
// these resolve to window.* globals, we define stub modules or rely on the global fallbacks.
// For now, we test the core logic by calling the window-registered functions.

// Helper: set vm-extension-select value (the module reads extension from DOM)
function setExtensionSelectValue(value) {
  const select = document.getElementById('vm-extension-select');
  // Clear existing options and add a matching option so .value works in jsdom
  select.innerHTML = '';
  if (value) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
    select.value = value;
  }
}

describe('Voicemail Management', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    // Reset select element
    document.getElementById('vm-extension-select').innerHTML = '';
    // Reset section visibility
    ['voicemail-pin-section', 'voicemail-messages-section', 'voicemail-box-overview'].forEach(id => {
      document.getElementById(id).style.display = '';
    });
    document.getElementById('vm-current-extension').textContent = '';
  });

  describe('loadVoicemailTab', () => {
    it('should load extensions successfully when API returns OK', async () => {
      const mockExtensions = [
        { number: '1001', name: 'John Doe' },
        { number: '1002', name: 'Jane Smith' }
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockExtensions
      });

      await window.loadVoicemailTab();

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:9000/api/extensions',
        { headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer test-token' } }
      );

      const select = document.getElementById('vm-extension-select');
      expect(select.children.length).toBe(3); // "Select Extension" + 2 extensions
      expect(select.children[0].textContent).toBe('Select Extension');
      expect(select.children[1].textContent).toBe('1001 - John Doe');
      expect(select.children[2].textContent).toBe('1002 - Jane Smith');
      expect(showNotification).not.toHaveBeenCalled();
    });

    it('should handle authentication errors gracefully', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ error: 'Authentication required' })
      });

      await window.loadVoicemailTab();

      expect(showNotification).toHaveBeenCalledWith('Failed to load extensions', 'error');

      const select = document.getElementById('vm-extension-select');
      // Should not populate extensions on error
      expect(select.children.length).toBe(0);
    });

    it('should handle server errors gracefully', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Internal server error' })
      });

      await window.loadVoicemailTab();

      expect(showNotification).toHaveBeenCalledWith('Failed to load extensions', 'error');
    });

    it('should handle network errors gracefully', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      await window.loadVoicemailTab();

      expect(showNotification).toHaveBeenCalledWith('Failed to load extensions', 'error');
    });

    it('should include authentication headers in request', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => []
      });

      await window.loadVoicemailTab();

      expect(getAuthHeaders).toHaveBeenCalled();
      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token'
          })
        })
      );
    });
  });

  describe('loadVoicemailForExtension', () => {
    it('should hide sections when no extension is provided', async () => {
      // Set select to empty value (no extension selected)
      setExtensionSelectValue('');

      await window.loadVoicemailForExtension();

      expect(document.getElementById('voicemail-pin-section').style.display).toBe('none');
      expect(document.getElementById('voicemail-messages-section').style.display).toBe('none');
      expect(document.getElementById('voicemail-box-overview').style.display).toBe('none');
    });

    it('should load voicemail messages successfully when API returns OK', async () => {
      const mockData = {
        messages: [
          { id: '1', caller_id: '5551234', timestamp: '2024-01-01T10:00:00Z' }
        ]
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData
      });

      // Set the extension in the DOM select (module reads from DOM)
      setExtensionSelectValue('1001');

      await window.loadVoicemailForExtension();

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:9000/api/voicemail/1001',
        { headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer test-token' } }
      );
      expect(showNotification).not.toHaveBeenCalled();
    });

    it('should handle authentication errors gracefully', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ error: 'Authentication required' })
      });

      setExtensionSelectValue('1001');

      await window.loadVoicemailForExtension();

      expect(showNotification).toHaveBeenCalledWith('Failed to load voicemail messages', 'error');
    });

    it('should handle server errors gracefully', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Internal server error' })
      });

      setExtensionSelectValue('1001');

      await window.loadVoicemailForExtension();

      expect(showNotification).toHaveBeenCalledWith('Failed to load voicemail messages', 'error');
    });

    it('should include authentication headers in request', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ messages: [] })
      });

      setExtensionSelectValue('1001');

      await window.loadVoicemailForExtension();

      expect(getAuthHeaders).toHaveBeenCalled();
      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token'
          })
        })
      );
    });

    it('should show sections when extension is provided', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ messages: [] })
      });

      setExtensionSelectValue('1001');

      await window.loadVoicemailForExtension();

      expect(document.getElementById('voicemail-pin-section').style.display).toBe('block');
      expect(document.getElementById('voicemail-messages-section').style.display).toBe('block');
      expect(document.getElementById('voicemail-box-overview').style.display).toBe('block');
      expect(document.getElementById('vm-current-extension').textContent).toBe('1001');
    });
  });
});
