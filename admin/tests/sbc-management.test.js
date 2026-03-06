/**
 * @jest-environment jsdom
 */

// Mock dependency modules before importing the module under test.
jest.mock('../js/api/client.ts', () => ({
  fetchWithTimeout: jest.fn(),
  getAuthHeaders: jest.fn(() => ({
    'Content-Type': 'application/json',
    'Authorization': 'Bearer test-token'
  })),
  getApiBaseUrl: jest.fn(() => 'http://localhost:9000')
}));

jest.mock('../js/ui/notifications.ts', () => ({
  showNotification: jest.fn()
}));

jest.mock('../js/utils/html.ts', () => ({
  escapeHtml: jest.fn((text) => text)
}));

import { describe, it, expect, beforeEach } from '@jest/globals';
import { loadSBCData, saveSBCConfig, addSBCBlacklist, removeSBCBlacklist, addSBCWhitelist, removeSBCWhitelist, detectSBCNat, terminateSBCRelay } from '../js/pages/sbc-management.ts';
import { fetchWithTimeout, getAuthHeaders } from '../js/api/client.ts';
import { showNotification } from '../js/ui/notifications.ts';

// Set up DOM fixtures
document.body.innerHTML = `
  <div id="sbc-active-sessions">-</div>
  <div id="sbc-total-sessions">-</div>
  <div id="sbc-blocked-requests">-</div>
  <div id="sbc-relayed-media">-</div>
  <div id="sbc-bandwidth-util">-</div>
  <div id="sbc-rate-violations">-</div>
  <div id="sbc-cac-rejections">-</div>
  <div id="sbc-port-pool">-</div>
  <select id="sbc-cfg-enabled"><option value="true">Enabled</option><option value="false">Disabled</option></select>
  <select id="sbc-cfg-topology-hiding"><option value="true">Enabled</option><option value="false">Disabled</option></select>
  <select id="sbc-cfg-media-relay"><option value="true">Enabled</option><option value="false">Disabled</option></select>
  <select id="sbc-cfg-stun"><option value="true">Enabled</option><option value="false">Disabled</option></select>
  <input id="sbc-cfg-public-ip" value="" />
  <input id="sbc-cfg-max-calls" value="" />
  <input id="sbc-cfg-max-bandwidth" value="" />
  <input id="sbc-cfg-rate-limit" value="" />
  <table><tbody id="sbc-relays-list"></tbody></table>
  <table><tbody id="sbc-blacklist-table"></tbody></table>
  <table><tbody id="sbc-whitelist-table"></tbody></table>
  <input id="sbc-blacklist-ip" value="" />
  <input id="sbc-whitelist-ip" value="" />
  <input id="sbc-nat-local-ip" value="" />
  <input id="sbc-nat-public-ip" value="" />
  <div id="sbc-nat-result" style="display: none;"><span id="sbc-nat-type">-</span></div>
`;

const mockStatsResponse = {
  product_name: 'Warden SBC',
  enabled: true,
  total_sessions: 42,
  active_sessions: 5,
  blocked_requests: 12,
  relayed_media_mb: 128.5,
  bandwidth_utilization_pct: 35.2,
  rate_limit_violations: 3,
  cac_rejections: 1,
  relay_port_pool_size: 4990,
  relay_port_pool_total: 5000,
};

const mockConfigResponse = {
  enabled: true,
  topology_hiding: true,
  media_relay: true,
  stun_enabled: true,
  turn_enabled: false,
  ice_enabled: false,
  max_calls: 1000,
  max_bandwidth: 100000,
  rate_limit: 100,
  public_ip: '203.0.113.1',
  product_name: 'Warden SBC',
};

function mockFetchByUrl(urlMap) {
  fetchWithTimeout.mockImplementation((url) => {
    // Find matching response by partial URL match
    for (const [pattern, resp] of Object.entries(urlMap)) {
      if (url.includes(pattern)) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve(resp),
        });
      }
    }
    // Default fallback
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });
  });
}

function mockFetch(responses) {
  let callIndex = 0;
  fetchWithTimeout.mockImplementation(() => {
    const resp = responses[callIndex] || responses[responses.length - 1];
    callIndex++;
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(resp),
    });
  });
}

describe('Warden SBC Management', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    getAuthHeaders.mockReturnValue({
      'Content-Type': 'application/json',
      'Authorization': 'Bearer test-token'
    });
  });

  describe('loadSBCData', () => {
    it('should load statistics and update DOM', async () => {
      mockFetchByUrl({
        '/sbc/statistics': mockStatsResponse,
        '/sbc/config': mockConfigResponse,
        '/sbc/relays': { relays: {} },
        '/sbc/blacklist': { blacklist: [] },
        '/sbc/whitelist': { whitelist: [] },
      });

      await loadSBCData();

      expect(fetchWithTimeout).toHaveBeenCalledTimes(5);
      expect(document.getElementById('sbc-active-sessions').textContent).toBe('5');
      expect(document.getElementById('sbc-total-sessions').textContent).toBe('42');
      expect(document.getElementById('sbc-blocked-requests').textContent).toBe('12');
    });

    it('should populate config form', async () => {
      mockFetchByUrl({
        '/sbc/statistics': mockStatsResponse,
        '/sbc/config': mockConfigResponse,
        '/sbc/relays': { relays: {} },
        '/sbc/blacklist': { blacklist: [] },
        '/sbc/whitelist': { whitelist: [] },
      });

      await loadSBCData();

      expect(document.getElementById('sbc-cfg-public-ip').value).toBe('203.0.113.1');
      expect(document.getElementById('sbc-cfg-max-calls').value).toBe('1000');
    });

    it('should render relays table when relays exist', async () => {
      mockFetchByUrl({
        '/sbc/statistics': mockStatsResponse,
        '/sbc/config': mockConfigResponse,
        '/sbc/relays': {
          relays: {
            'call-1': {
              call_id: 'call-1',
              codec: 'PCMU',
              rtp_port: 10000,
              rtcp_port: 10001,
              relay_ip: '203.0.113.1',
              allocated_at: '2026-03-06T12:00:00Z',
              success: true,
            }
          }
        },
        '/sbc/blacklist': { blacklist: [] },
        '/sbc/whitelist': { whitelist: [] },
      });

      await loadSBCData();

      const relaysTbody = document.getElementById('sbc-relays-list');
      expect(relaysTbody.innerHTML).toContain('call-1');
      expect(relaysTbody.innerHTML).toContain('PCMU');
      expect(relaysTbody.innerHTML).toContain('10000');
    });

    it('should handle API errors gracefully', async () => {
      fetchWithTimeout.mockRejectedValue(new Error('Network error'));

      await loadSBCData();

      expect(showNotification).toHaveBeenCalledWith(
        expect.stringContaining('Failed to load SBC statistics'),
        'error'
      );
    });
  });

  describe('saveSBCConfig', () => {
    it('should send PUT request with config values', async () => {
      // Setup form values
      document.getElementById('sbc-cfg-enabled').value = 'true';
      document.getElementById('sbc-cfg-public-ip').value = '1.2.3.4';
      document.getElementById('sbc-cfg-max-calls').value = '500';
      document.getElementById('sbc-cfg-max-bandwidth').value = '50000';
      document.getElementById('sbc-cfg-rate-limit').value = '200';

      // First call for PUT, second for stats reload
      mockFetch([mockConfigResponse, mockStatsResponse]);

      await saveSBCConfig();

      expect(fetchWithTimeout).toHaveBeenCalledWith(
        'http://localhost:9000/api/framework/sbc/config',
        expect.objectContaining({ method: 'PUT' }),
        10000,
      );
      expect(showNotification).toHaveBeenCalledWith(
        'Warden SBC configuration saved',
        'success'
      );
    });
  });

  describe('Blacklist management', () => {
    it('should add IP to blacklist', async () => {
      document.getElementById('sbc-blacklist-ip').value = '10.0.0.99';

      mockFetch([
        { success: true, blacklist: ['10.0.0.99'] },
        { blacklist: ['10.0.0.99'] },
        mockStatsResponse,
      ]);

      await addSBCBlacklist();

      expect(fetchWithTimeout).toHaveBeenCalledWith(
        'http://localhost:9000/api/framework/sbc/blacklist',
        expect.objectContaining({ method: 'POST' }),
        10000,
      );
      expect(showNotification).toHaveBeenCalledWith(
        '10.0.0.99 added to blacklist',
        'success'
      );
      // Input should be cleared
      expect(document.getElementById('sbc-blacklist-ip').value).toBe('');
    });

    it('should show warning when no IP entered', async () => {
      document.getElementById('sbc-blacklist-ip').value = '';

      await addSBCBlacklist();

      expect(showNotification).toHaveBeenCalledWith(
        'Enter an IP address',
        'warning'
      );
      expect(fetchWithTimeout).not.toHaveBeenCalled();
    });

    it('should remove IP from blacklist', async () => {
      mockFetch([
        { success: true, blacklist: [] },
        { blacklist: [] },
        mockStatsResponse,
      ]);

      await removeSBCBlacklist('10.0.0.99');

      expect(fetchWithTimeout).toHaveBeenCalledWith(
        'http://localhost:9000/api/framework/sbc/blacklist/10.0.0.99',
        expect.objectContaining({ method: 'DELETE' }),
        10000,
      );
    });
  });

  describe('Whitelist management', () => {
    it('should add IP to whitelist', async () => {
      document.getElementById('sbc-whitelist-ip').value = '192.168.1.1';

      mockFetch([
        { success: true, whitelist: ['192.168.1.1'] },
        { whitelist: ['192.168.1.1'] },
        mockStatsResponse,
      ]);

      await addSBCWhitelist();

      expect(showNotification).toHaveBeenCalledWith(
        '192.168.1.1 added to whitelist',
        'success'
      );
    });

    it('should remove IP from whitelist', async () => {
      mockFetch([
        { success: true, whitelist: [] },
        { whitelist: [] },
        mockStatsResponse,
      ]);

      await removeSBCWhitelist('192.168.1.1');

      expect(fetchWithTimeout).toHaveBeenCalledWith(
        'http://localhost:9000/api/framework/sbc/whitelist/192.168.1.1',
        expect.objectContaining({ method: 'DELETE' }),
        10000,
      );
    });
  });

  describe('NAT Detection', () => {
    it('should trigger NAT detection and display result', async () => {
      document.getElementById('sbc-nat-local-ip').value = '192.168.1.100';
      document.getElementById('sbc-nat-public-ip').value = '203.0.113.5';

      mockFetch([{ nat_type: 'full_cone', local_ip: '192.168.1.100', public_ip: '203.0.113.5' }]);

      await detectSBCNat();

      expect(fetchWithTimeout).toHaveBeenCalledWith(
        'http://localhost:9000/api/framework/sbc/nat-detect',
        expect.objectContaining({ method: 'POST' }),
        15000,
      );

      const resultDiv = document.getElementById('sbc-nat-result');
      expect(resultDiv.style.display).toBe('block');
      expect(document.getElementById('sbc-nat-type').textContent).toBe('full_cone');
    });

    it('should warn when IPs are missing', async () => {
      document.getElementById('sbc-nat-local-ip').value = '';
      document.getElementById('sbc-nat-public-ip').value = '';

      await detectSBCNat();

      expect(showNotification).toHaveBeenCalledWith(
        'Enter both local and public IP addresses',
        'warning'
      );
    });
  });

  describe('Relay termination', () => {
    it('should send DELETE request for relay', async () => {
      // Mock window.confirm
      global.confirm = jest.fn(() => true);

      mockFetch([
        { success: true },
        { relays: {} },
        mockStatsResponse,
      ]);

      await terminateSBCRelay('call-123');

      expect(fetchWithTimeout).toHaveBeenCalledWith(
        'http://localhost:9000/api/framework/sbc/relay/call-123',
        expect.objectContaining({ method: 'DELETE' }),
        10000,
      );
      expect(showNotification).toHaveBeenCalledWith('Relay terminated', 'success');
    });
  });
});
