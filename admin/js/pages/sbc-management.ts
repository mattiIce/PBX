/**
 * Warden SBC Management page module.
 * Handles SBC statistics, configuration, relay management,
 * blacklist/whitelist, and NAT detection.
 */

import { fetchWithTimeout, getAuthHeaders, getApiBaseUrl } from '../api/client.ts';
import { showNotification } from '../ui/notifications.ts';
import { escapeHtml } from '../utils/html.ts';

// ---------------------------------------------------------------------------
// Interfaces
// ---------------------------------------------------------------------------

interface SBCStatistics {
  product_name: string;
  enabled: boolean;
  total_sessions: number;
  active_sessions: number;
  blocked_requests: number;
  relayed_media_mb: number;
  blacklist_size: number;
  whitelist_size: number;
  topology_hiding: boolean;
  media_relay: boolean;
  current_bandwidth_kbps: number;
  max_bandwidth_kbps: number;
  bandwidth_utilization_pct: number;
  rate_limit_violations: number;
  cac_rejections: number;
  codec_call_counts: Record<string, number>;
  topology_hiding_ops: number;
  nat_detection_count: number;
  relay_port_pool_size: number;
  relay_port_pool_total: number;
  max_calls: number;
  rate_limit: number;
}

interface SBCConfig {
  enabled: boolean;
  topology_hiding: boolean;
  media_relay: boolean;
  stun_enabled: boolean;
  turn_enabled: boolean;
  ice_enabled: boolean;
  max_calls: number;
  max_bandwidth: number;
  rate_limit: number;
  public_ip: string;
  product_name: string;
}

interface RelaySession {
  call_id: string;
  codec: string;
  rtp_port: number;
  rtcp_port: number;
  relay_ip: string;
  allocated_at: string;
  success: boolean;
}

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

export async function loadSBCData(): Promise<void> {
  await Promise.all([
    loadSBCStatistics(),
    loadSBCConfig(),
    loadSBCRelays(),
    loadSBCBlacklist(),
    loadSBCWhitelist(),
  ]);
}

async function loadSBCStatistics(): Promise<void> {
  try {
    const API_BASE = getApiBaseUrl();
    const response = await fetchWithTimeout(`${API_BASE}/api/framework/sbc/statistics`, {
      headers: getAuthHeaders(),
    }, 10000);

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const stats: SBCStatistics = await response.json();

    setTextContent('sbc-active-sessions', String(stats.active_sessions));
    setTextContent('sbc-total-sessions', String(stats.total_sessions));
    setTextContent('sbc-blocked-requests', String(stats.blocked_requests));
    setTextContent('sbc-relayed-media', String(stats.relayed_media_mb));
    setTextContent('sbc-bandwidth-util', `${stats.bandwidth_utilization_pct}%`);
    setTextContent('sbc-rate-violations', String(stats.rate_limit_violations));
    setTextContent('sbc-cac-rejections', String(stats.cac_rejections));
    setTextContent('sbc-port-pool', `${stats.relay_port_pool_size}/${stats.relay_port_pool_total}`);

  } catch (error: unknown) {
    console.error('Error loading SBC statistics:', error);
    const msg = error instanceof Error ? error.message : String(error);
    showNotification(`Failed to load SBC statistics: ${msg}`, 'error');
  }
}

async function loadSBCConfig(): Promise<void> {
  try {
    const API_BASE = getApiBaseUrl();
    const response = await fetchWithTimeout(`${API_BASE}/api/framework/sbc/config`, {
      headers: getAuthHeaders(),
    }, 10000);

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const config: SBCConfig = await response.json();

    setSelectValue('sbc-cfg-enabled', String(config.enabled));
    setSelectValue('sbc-cfg-topology-hiding', String(config.topology_hiding));
    setSelectValue('sbc-cfg-media-relay', String(config.media_relay));
    setSelectValue('sbc-cfg-stun', String(config.stun_enabled));
    setInputValue('sbc-cfg-public-ip', config.public_ip);
    setInputValue('sbc-cfg-max-calls', String(config.max_calls));
    setInputValue('sbc-cfg-max-bandwidth', String(config.max_bandwidth));
    setInputValue('sbc-cfg-rate-limit', String(config.rate_limit));

  } catch (error: unknown) {
    console.error('Error loading SBC config:', error);
  }
}

async function loadSBCRelays(): Promise<void> {
  try {
    const API_BASE = getApiBaseUrl();
    const response = await fetchWithTimeout(`${API_BASE}/api/framework/sbc/relays`, {
      headers: getAuthHeaders(),
    }, 10000);

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data: { relays: Record<string, RelaySession> } = await response.json();

    const tbody = document.getElementById('sbc-relays-list');
    if (!tbody) return;

    const relays = Object.values(data.relays ?? {});

    if (relays.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No active relays</td></tr>';
      return;
    }

    tbody.innerHTML = relays.map(r => `
      <tr>
        <td><code>${escapeHtml(r.call_id)}</code></td>
        <td>${escapeHtml(r.codec)}</td>
        <td>${r.rtp_port}</td>
        <td>${r.rtcp_port}</td>
        <td>${escapeHtml(r.relay_ip)}</td>
        <td>${escapeHtml(r.allocated_at ?? '-')}</td>
        <td>
          <button class="btn btn-danger btn-small" onclick="terminateSBCRelay('${escapeHtml(r.call_id)}')">Terminate</button>
        </td>
      </tr>
    `).join('');

  } catch (error: unknown) {
    console.error('Error loading SBC relays:', error);
    const tbody = document.getElementById('sbc-relays-list');
    if (tbody) tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">Error loading relays</td></tr>';
  }
}

async function loadSBCBlacklist(): Promise<void> {
  try {
    const API_BASE = getApiBaseUrl();
    const response = await fetchWithTimeout(`${API_BASE}/api/framework/sbc/blacklist`, {
      headers: getAuthHeaders(),
    }, 10000);

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data: { blacklist: string[] } = await response.json();

    renderIPList('sbc-blacklist-table', data.blacklist, 'removeSBCBlacklist');

  } catch (error: unknown) {
    console.error('Error loading SBC blacklist:', error);
  }
}

async function loadSBCWhitelist(): Promise<void> {
  try {
    const API_BASE = getApiBaseUrl();
    const response = await fetchWithTimeout(`${API_BASE}/api/framework/sbc/whitelist`, {
      headers: getAuthHeaders(),
    }, 10000);

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data: { whitelist: string[] } = await response.json();

    renderIPList('sbc-whitelist-table', data.whitelist, 'removeSBCWhitelist');

  } catch (error: unknown) {
    console.error('Error loading SBC whitelist:', error);
  }
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

export async function saveSBCConfig(): Promise<void> {
  try {
    const API_BASE = getApiBaseUrl();
    const updates = {
      enabled: getSelectValue('sbc-cfg-enabled') === 'true',
      topology_hiding: getSelectValue('sbc-cfg-topology-hiding') === 'true',
      media_relay: getSelectValue('sbc-cfg-media-relay') === 'true',
      stun_enabled: getSelectValue('sbc-cfg-stun') === 'true',
      public_ip: getInputValue('sbc-cfg-public-ip'),
      max_calls: parseInt(getInputValue('sbc-cfg-max-calls') || '1000', 10),
      max_bandwidth: parseInt(getInputValue('sbc-cfg-max-bandwidth') || '100000', 10),
      rate_limit: parseInt(getInputValue('sbc-cfg-rate-limit') || '100', 10),
    };

    const response = await fetchWithTimeout(`${API_BASE}/api/framework/sbc/config`, {
      method: 'PUT',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    }, 10000);

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    showNotification('Warden SBC configuration saved', 'success');
    await loadSBCStatistics();
  } catch (error: unknown) {
    console.error('Error saving SBC config:', error);
    showNotification('Failed to save SBC configuration', 'error');
  }
}

export async function terminateSBCRelay(callId: string): Promise<void> {
  if (!confirm(`Terminate relay for call ${callId}?`)) return;

  try {
    const API_BASE = getApiBaseUrl();
    const response = await fetchWithTimeout(
      `${API_BASE}/api/framework/sbc/relay/${encodeURIComponent(callId)}`,
      { method: 'DELETE', headers: getAuthHeaders() },
      10000,
    );

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    showNotification('Relay terminated', 'success');
    await loadSBCRelays();
    await loadSBCStatistics();
  } catch (error: unknown) {
    console.error('Error terminating relay:', error);
    showNotification('Failed to terminate relay', 'error');
  }
}

export async function addSBCBlacklist(): Promise<void> {
  const input = document.getElementById('sbc-blacklist-ip') as HTMLInputElement | null;
  const ip = input?.value?.trim();
  if (!ip) {
    showNotification('Enter an IP address', 'warning');
    return;
  }

  try {
    const API_BASE = getApiBaseUrl();
    const response = await fetchWithTimeout(`${API_BASE}/api/framework/sbc/blacklist`, {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip }),
    }, 10000);

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    if (input) input.value = '';
    showNotification(`${ip} added to blacklist`, 'success');
    await loadSBCBlacklist();
    await loadSBCStatistics();
  } catch (error: unknown) {
    console.error('Error adding to blacklist:', error);
    showNotification('Failed to add to blacklist', 'error');
  }
}

export async function removeSBCBlacklist(ip: string): Promise<void> {
  try {
    const API_BASE = getApiBaseUrl();
    const response = await fetchWithTimeout(
      `${API_BASE}/api/framework/sbc/blacklist/${encodeURIComponent(ip)}`,
      { method: 'DELETE', headers: getAuthHeaders() },
      10000,
    );

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    showNotification(`${ip} removed from blacklist`, 'success');
    await loadSBCBlacklist();
    await loadSBCStatistics();
  } catch (error: unknown) {
    console.error('Error removing from blacklist:', error);
    showNotification('Failed to remove from blacklist', 'error');
  }
}

export async function addSBCWhitelist(): Promise<void> {
  const input = document.getElementById('sbc-whitelist-ip') as HTMLInputElement | null;
  const ip = input?.value?.trim();
  if (!ip) {
    showNotification('Enter an IP address', 'warning');
    return;
  }

  try {
    const API_BASE = getApiBaseUrl();
    const response = await fetchWithTimeout(`${API_BASE}/api/framework/sbc/whitelist`, {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip }),
    }, 10000);

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    if (input) input.value = '';
    showNotification(`${ip} added to whitelist`, 'success');
    await loadSBCWhitelist();
    await loadSBCStatistics();
  } catch (error: unknown) {
    console.error('Error adding to whitelist:', error);
    showNotification('Failed to add to whitelist', 'error');
  }
}

export async function removeSBCWhitelist(ip: string): Promise<void> {
  try {
    const API_BASE = getApiBaseUrl();
    const response = await fetchWithTimeout(
      `${API_BASE}/api/framework/sbc/whitelist/${encodeURIComponent(ip)}`,
      { method: 'DELETE', headers: getAuthHeaders() },
      10000,
    );

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    showNotification(`${ip} removed from whitelist`, 'success');
    await loadSBCWhitelist();
    await loadSBCStatistics();
  } catch (error: unknown) {
    console.error('Error removing from whitelist:', error);
    showNotification('Failed to remove from whitelist', 'error');
  }
}

export async function detectSBCNat(): Promise<void> {
  const localIp = getInputValue('sbc-nat-local-ip');
  const publicIp = getInputValue('sbc-nat-public-ip');

  if (!localIp || !publicIp) {
    showNotification('Enter both local and public IP addresses', 'warning');
    return;
  }

  try {
    const API_BASE = getApiBaseUrl();
    const response = await fetchWithTimeout(`${API_BASE}/api/framework/sbc/nat-detect`, {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ local_ip: localIp, public_ip: publicIp }),
    }, 15000);

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data: { nat_type: string } = await response.json();

    const resultDiv = document.getElementById('sbc-nat-result');
    const typeSpan = document.getElementById('sbc-nat-type');
    if (resultDiv) resultDiv.style.display = 'block';
    if (typeSpan) typeSpan.textContent = data.nat_type;

    showNotification(`NAT type detected: ${data.nat_type}`, 'success');
  } catch (error: unknown) {
    console.error('Error detecting NAT:', error);
    showNotification('NAT detection failed', 'error');
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setTextContent(id: string, text: string): void {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function setSelectValue(id: string, value: string): void {
  const el = document.getElementById(id) as HTMLSelectElement | null;
  if (el) el.value = value;
}

function setInputValue(id: string, value: string): void {
  const el = document.getElementById(id) as HTMLInputElement | null;
  if (el) el.value = value;
}

function getSelectValue(id: string): string {
  return (document.getElementById(id) as HTMLSelectElement | null)?.value ?? '';
}

function getInputValue(id: string): string {
  return (document.getElementById(id) as HTMLInputElement | null)?.value?.trim() ?? '';
}

function renderIPList(tbodyId: string, ips: string[], removeFn: string): void {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;

  if (ips.length === 0) {
    tbody.innerHTML = '<tr><td colspan="2" style="text-align: center;">No entries</td></tr>';
    return;
  }

  tbody.innerHTML = ips.map(ip => `
    <tr>
      <td><code>${escapeHtml(ip)}</code></td>
      <td>
        <button class="btn btn-danger btn-small" onclick="${removeFn}('${escapeHtml(ip)}')">Remove</button>
      </td>
    </tr>
  `).join('');
}

// ---------------------------------------------------------------------------
// Window exports for backward compatibility with inline onclick handlers
// ---------------------------------------------------------------------------

window.loadSBCData = loadSBCData;
window.saveSBCConfig = saveSBCConfig;
window.terminateSBCRelay = terminateSBCRelay;
window.addSBCBlacklist = addSBCBlacklist;
window.removeSBCBlacklist = removeSBCBlacklist;
window.addSBCWhitelist = addSBCWhitelist;
window.removeSBCWhitelist = removeSBCWhitelist;
window.detectSBCNat = detectSBCNat;
