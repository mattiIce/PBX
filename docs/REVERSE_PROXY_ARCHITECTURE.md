# Reverse Proxy Architecture Diagram

## Before (Direct Access)
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

## After (Reverse Proxy - Recommended)
```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       │ https://abps.albl.com
       │ (Friendly URL, no port)
       ▼
┌─────────────────────────┐
│   DNS Server            │
│   abps.albl.com         │
│   → 192.168.1.14        │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│   Nginx (Port 443)      │  ◄── SSL/TLS Termination
│   - HTTPS enabled       │  ◄── Let's Encrypt cert
│   - Security headers    │  ◄── Rate limiting
│   - WebSocket support   │  ◄── Request logging
└──────┬──────────────────┘
       │
       │ Proxies to localhost:8080
       ▼
┌─────────────────────────┐
│   PBX Server (8080)     │
│   - Listens on          │
│     127.0.0.1:8080      │
│   - Not exposed to      │
│     internet            │
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

| Feature | Direct Access | Reverse Proxy |
|---------|---------------|---------------|
| SSL/TLS | Manual setup | Automated (Let's Encrypt) |
| Certificate | Self-signed | Trusted CA |
| Port in URL | Yes (:8080) | No |
| Rate limiting | No | Yes |
| Request logging | Basic | Detailed |
| Security headers | Basic | Enhanced |
| Attack surface | Full | Reduced |
| Professional URL | No | Yes |

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
