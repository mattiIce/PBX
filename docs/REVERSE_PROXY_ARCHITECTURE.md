# Reverse Proxy Architecture Diagram

**Last Updated:** 2025-12-23  
**Priority:** HIGH - Production Best Practice  
**Purpose:** Visual guide to understand the security and architecture benefits of reverse proxy setup

## Before (Direct Access) ❌ NOT RECOMMENDED
```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       │ http://192.168.1.14:8080/admin/
       │ (Must specify IP and port)
       ▼
┌─────────────────────────┐
│   PBX Server (8080)     │
│   - No SSL              │
│   - IP:Port required    │
└─────────────────────────┘
```

## After (Reverse Proxy - Recommended) ✅ PRODUCTION READY
```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       │ https://abps.albl.com
       │ (Friendly URL, no port, encrypted)
       ▼
┌─────────────────────────┐
│   DNS Server            │
│   abps.albl.com         │
│   → 192.168.1.14        │  ◄── Public IP address
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│   Firewall (ufw)        │
│   - Allow 80, 443       │  ◄── HTTP/HTTPS only
│   - Allow 5060 (SIP)    │  ◄── Phone signaling
│   - Allow 10000-20000   │  ◄── RTP media
│   - DENY 8080           │  ◄── Block direct PBX access
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│   Nginx (Port 443)      │  ◄── SSL/TLS Termination
│   - HTTPS enabled       │  ◄── Let's Encrypt cert (auto-renew)
│   - TLS 1.3 support     │  ◄── Modern encryption
│   - Security headers    │  ◄── HSTS, X-Frame-Options
│   - Rate limiting       │  ◄── 10 req/sec API limit
│   - WebSocket support   │  ◄── For WebRTC phones
│   - Request logging     │  ◄── Detailed access logs
│   - DDoS protection     │  ◄── Burst handling
└──────┬──────────────────┘
       │
       │ Proxies to localhost:8080
       │ (Internal, not internet-facing)
       ▼
┌─────────────────────────┐
│   PBX Server (8080)     │
│   - Listens on          │
│     127.0.0.1:8080      │  ◄── Localhost only
│   - Not exposed to      │
│     internet            │  ◄── Enhanced security
│   - No SSL overhead     │  ◄── Nginx handles it
└─────────────────────────┘
```

## Traffic Flow

### User Request Flow
1. User enters: `https://abps.albl.com`
2. DNS resolves to: `192.168.1.14`
3. Browser connects to nginx on port 443 (HTTPS)
4. Nginx validates SSL certificate
5. Nginx proxies request to PBX on `localhost:8080`
6. PBX processes request and returns response
7. Nginx forwards response to browser with security headers
8. Browser displays PBX admin panel

### Security Layers
```
Internet
   ↓
Firewall (ports 80, 443)
   ↓
Nginx Reverse Proxy
   ├─ SSL/TLS encryption
   ├─ Rate limiting
   ├─ Security headers
   ├─ Access logging
   └─ Request filtering
      ↓
   Localhost Only
      ↓
   PBX Application (8080)
      ├─ Authentication
      ├─ Authorization
      └─ Business logic
```

## Port Configuration

### External Ports (Internet-facing)
- **80/tcp** - HTTP (redirects to HTTPS)
- **443/tcp** - HTTPS (nginx reverse proxy)
- **5060/udp** - SIP signaling (for phones)
- **10000-20000/udp** - RTP media (for calls)

### Internal Ports (localhost only)
- **8080/tcp** - PBX HTTP API (not exposed)

## Security Comparison

| Feature | Direct Access ❌ | Reverse Proxy ✅ | Priority |
|---------|-----------------|------------------|----------|
| SSL/TLS | Manual setup, complex | Automated (Let's Encrypt) | CRITICAL |
| Certificate | Self-signed (warnings) | Trusted CA (green lock) | CRITICAL |
| Port in URL | Yes (:8080) ugly | No (standard 443) | HIGH |
| Rate limiting | No protection | Yes (10 req/sec API) | HIGH |
| Request logging | Basic | Detailed nginx logs | MEDIUM |
| Security headers | Basic | Enhanced (HSTS, CSP) | HIGH |
| Attack surface | Full PBX exposed | Only nginx exposed | CRITICAL |
| Professional URL | No | Yes (https://abps.albl.com) | MEDIUM |
| DDoS protection | None | Burst handling | HIGH |
| Auto-renewal | Manual | Automatic (90 days) | HIGH |
| WebSocket support | Manual config | Built-in | MEDIUM |
| Monitoring | Limited | Extensive logs | MEDIUM |

**Bottom Line:** Reverse proxy is NOT optional for production - it's essential for security.

## Setup Summary

1. **Configure DNS**
   - Add A record: `abps.albl.com` → `your-server-ip`

2. **Run setup script**
   ```bash
   sudo scripts/setup_reverse_proxy.sh
   ```

3. **Configure firewall**
   ```bash
   sudo ufw allow 'Nginx Full'
   ```

4. **Access admin panel**
   - Open: `https://abps.albl.com`
   - Enjoy HTTPS with valid certificate!
