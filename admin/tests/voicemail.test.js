/**
 * @jest-environment jsdom
 */

// Mock dependency modules before importing the module under test.
// jest.mock() calls are hoisted above require() by the CJS transform,
// ensuring mocks are registered before voicemail.ts loads its imports.
jest.mock('../js/api/client.ts', () => ({
  getAuthHeaders: jest.fn(() => ({
    'Content-Type': 'application/json',
    'Authorization': 'Bearer test-token'
  })),
  getApiBaseUrl: jest.fn(() => 'http://localhost:9000')
}));

jest.mock('../js/ui/notifications.ts', () => ({
  showNotification: jest.fn()
}));

import { describe, it, expect, beforeEach } from '@jest/globals';
import { loadVoicemailTab, loadVoicemailForExtension } from '../js/pages/voicemail.ts';
import { getAuthHeaders } from '../js/api/client.ts';
import { showNotification } from '../js/ui/notifications.ts';

// Mock fetch globally
global.fetch = jest.fn();

// Set up DOM
document.body.innerHTML = `
  <select id="vm-extension-select"></select>
  <div id="voicemail-pin-section"></div>
  <div id="voicemail-messages-section"></div>
  <div id="voicemail-box-overview"></div>
  <span id="vm-current-extension"></span>
  <div id="voicemail-cards-view"></div>
`;

// Helper: set vm-extension-select value (the module reads extension from DOM)
function setExtensionSelectValue(value) {
  const select = document.getElementById('vm-extension-select');
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
    jest.clearAllMocks();
    // Re-setup default mock returns after clearAllMocks
    getAuthHeaders.mockReturnValue({
      'Content-Type': 'application/json',
      'Authorization': 'Bearer test-token'
    });
    // Reset DOM select element
    document.getElementById('vm-extension-select').innerHTML = '';
    // Reset section visibility
    for (const id of ['voicemail-pin-section', 'voicemail-messages-section', 'voicemail-box-overview']) {
      document.getElementById(id).style.display = '';
    }
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

      await loadVoicemailTab();

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

      await loadVoicemailTab();

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

      await loadVoicemailTab();

      expect(showNotification).toHaveBeenCalledWith('Failed to load extensions', 'error');
    });

    it('should handle network errors gracefully', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      await loadVoicemailTab();

      expect(showNotification).toHaveBeenCalledWith('Failed to load extensions', 'error');
    });

    it('should include authentication headers in request', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => []
      });

      await loadVoicemailTab();

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

      await loadVoicemailForExtension();

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

      setExtensionSelectValue('1001');

      await loadVoicemailForExtension();

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

      await loadVoicemailForExtension();

      expect(showNotification).toHaveBeenCalledWith('Failed to load voicemail messages', 'error');
    });

    it('should handle server errors gracefully', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Internal server error' })
      });

      setExtensionSelectValue('1001');

      await loadVoicemailForExtension();

      expect(showNotification).toHaveBeenCalledWith('Failed to load voicemail messages', 'error');
    });

    it('should include authentication headers in request', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ messages: [] })
      });

      setExtensionSelectValue('1001');

      await loadVoicemailForExtension();

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

      await loadVoicemailForExtension();

      expect(document.getElementById('voicemail-pin-section').style.display).toBe('block');
      expect(document.getElementById('voicemail-messages-section').style.display).toBe('block');
      expect(document.getElementById('voicemail-box-overview').style.display).toBe('block');
      expect(document.getElementById('vm-current-extension').textContent).toBe('1001');
    });
  });
});
