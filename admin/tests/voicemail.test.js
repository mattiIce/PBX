/**
 * @jest-environment jsdom
 */

const { describe, it, expect, beforeEach } = require('@jest/globals');

// Mock global fetch
global.fetch = jest.fn();

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  clear: jest.fn()
};
global.localStorage = localStorageMock;

// Mock DOM elements
document.body.innerHTML = `
  <select id="vm-extension-select"></select>
  <div id="voicemail-pin-section"></div>
  <div id="voicemail-messages-section"></div>
  <div id="voicemail-box-overview"></div>
  <span id="vm-current-extension"></span>
`;

// Mock API_BASE
global.API_BASE = 'http://localhost:9000';

// Mock getAuthHeaders function
global.getAuthHeaders = jest.fn(() => ({
  'Content-Type': 'application/json',
  'Authorization': 'Bearer test-token'
}));

// Mock showNotification function
global.showNotification = jest.fn();

// Mock update functions
global.updateVoicemailCardsView = jest.fn();
global.updateVoicemailTableView = jest.fn();

// Load the functions we're testing
// Note: In a real setup, you'd import these from a module
// For now, we'll define them inline for testing

async function loadVoicemailTab() {
  try {
    const response = await fetch(`${API_BASE}/api/extensions`, {
      headers: getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const extensions = await response.json();

    const select = document.getElementById('vm-extension-select');
    select.innerHTML = '<option value="">Select Extension</option>';

    extensions.forEach(ext => {
      const option = document.createElement('option');
      option.value = ext.number;
      option.textContent = `${ext.number} - ${ext.name}`;
      select.appendChild(option);
    });
  } catch (error) {
    console.error('Error loading voicemail tab:', error);
    showNotification('Failed to load extensions', 'error');
  }
}

async function loadVoicemailForExtension(extension) {
  if (!extension) {
    document.getElementById('voicemail-pin-section').style.display = 'none';
    document.getElementById('voicemail-messages-section').style.display = 'none';
    document.getElementById('voicemail-box-overview').style.display = 'none';
    return;
  }

  document.getElementById('voicemail-pin-section').style.display = 'block';
  document.getElementById('voicemail-messages-section').style.display = 'block';
  document.getElementById('voicemail-box-overview').style.display = 'block';
  document.getElementById('vm-current-extension').textContent = extension;

  try {
    const response = await fetch(`${API_BASE}/api/voicemail/${extension}`, {
      headers: getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    updateVoicemailCardsView(data.messages, extension);
    updateVoicemailTableView(data.messages, extension);

  } catch (error) {
    console.error('Error loading voicemail:', error);
    showNotification('Failed to load voicemail messages', 'error');
  }
}

describe('Voicemail Management Extensions List', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    // Reset select element
    document.getElementById('vm-extension-select').innerHTML = '';
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
      await loadVoicemailForExtension('');

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

      await loadVoicemailForExtension('1001');

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:9000/api/voicemail/1001',
        { headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer test-token' } }
      );
      expect(updateVoicemailCardsView).toHaveBeenCalledWith(mockData.messages, '1001');
      expect(updateVoicemailTableView).toHaveBeenCalledWith(mockData.messages, '1001');
      expect(showNotification).not.toHaveBeenCalled();
    });

    it('should handle authentication errors gracefully', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ error: 'Authentication required' })
      });

      await loadVoicemailForExtension('1001');

      expect(showNotification).toHaveBeenCalledWith('Failed to load voicemail messages', 'error');
      expect(updateVoicemailCardsView).not.toHaveBeenCalled();
    });

    it('should handle server errors gracefully', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Internal server error' })
      });

      await loadVoicemailForExtension('1001');

      expect(showNotification).toHaveBeenCalledWith('Failed to load voicemail messages', 'error');
    });

    it('should include authentication headers in request', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ messages: [] })
      });

      await loadVoicemailForExtension('1001');

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

      await loadVoicemailForExtension('1001');

      expect(document.getElementById('voicemail-pin-section').style.display).toBe('block');
      expect(document.getElementById('voicemail-messages-section').style.display).toBe('block');
      expect(document.getElementById('voicemail-box-overview').style.display).toBe('block');
      expect(document.getElementById('vm-current-extension').textContent).toBe('1001');
    });
  });
});
