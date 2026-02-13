# Production Readiness Checklist

**Last Updated**: January 2, 2026  
**Version**: 1.0.0  
**Purpose**: Comprehensive checklist for deploying Warden VoIP PBX to production

---

## Overview

This checklist ensures that all critical systems, security measures, monitoring, and documentation are in place before deploying the PBX system to production. Each section must be completed and verified.

**Status Legend:**
- ✅ **Complete** - Verified and tested
- ⚠️ **Partial** - Implemented but needs verification
- ❌ **Missing** - Not yet implemented
- 🔄 **In Progress** - Currently being worked on

---

## 1. Infrastructure & Environment

### 1.1 Server Requirements
- [ ] **Hardware Specifications**
  - [ ] CPU: Minimum 4 cores (8 recommended for >100 extensions)
  - [ ] RAM: Minimum 8GB (16GB recommended for >100 extensions)
  - [ ] Disk: Minimum 100GB SSD (with growth plan)
  - [ ] Network: Dedicated network interface for SIP/RTP traffic
  - [ ] Redundant power supply (if available)

- [ ] **Operating System**
  - [ ] Ubuntu 24.04 LTS installed
  - [ ] All security updates applied
  - [ ] System hardened (disable unnecessary services)
  - [ ] Timezone configured correctly
  - [ ] NTP configured for time synchronization

- [ ] **Network Configuration**
  - [ ] Static IP address assigned
  - [ ] DNS records configured (A, PTR, SRV)
  - [ ] Firewall rules configured (UFW or iptables)
  - [ ] Required ports opened:
    - [ ] 5060 UDP (SIP)
    - [ ] 10000-20000 UDP (RTP)
    - [ ] 8080 TCP (HTTPS API - or via reverse proxy)
    - [ ] 443 TCP (HTTPS - if using reverse proxy)
  - [ ] QoS/DSCP configured for VoIP traffic

### 1.2 Database
- [ ] **PostgreSQL Setup**
  - [ ] PostgreSQL 14+ installed
  - [ ] Database created (`pbx_system`)
  - [ ] Database user created with strong password
  - [ ] Database permissions configured correctly
  - [ ] Connection pooling configured (pgBouncer recommended)
  - [ ] Database tuning for production workload
  - [ ] Regular vacuum and analyze scheduled

- [ ] **Database Backup**
  - [ ] Automated daily backups configured
  - [ ] Backup retention policy defined (30 days recommended)
  - [ ] Backup verification process in place
  - [ ] Off-site backup storage configured
  - [ ] Backup restoration tested successfully
  - [ ] Point-in-time recovery configured (if needed)

### 1.3 Storage
- [ ] **Disk Space Planning**
  - [ ] Voicemail storage: Estimated and allocated
  - [ ] Call recording storage: Estimated and allocated
  - [ ] Log file storage: Rotation configured
  - [ ] Database storage: Growth projected
  - [ ] Disk monitoring and alerting configured

- [ ] **File System**
  - [ ] Dedicated partition for voicemail (recommended)
  - [ ] Dedicated partition for call recordings (recommended)
  - [ ] File permissions secured (owner: pbx user)
  - [ ] Symbolic links configured (if needed)

---

## 2. Application Deployment

### 2.1 PBX Installation
- [ ] **Code Deployment**
  - [ ] Repository cloned from stable branch/tag
  - [ ] Python 3.12 installed
  - [ ] Production dependencies installed (`make install-prod`)
  - [ ] System dependencies installed (espeak, ffmpeg, etc.)
  - [ ] Application user created (`pbx` user)
  - [ ] Directory permissions configured

- [ ] **Configuration**
  - [ ] `config.yml` created from template
  - [ ] `.env` file created with production secrets
  - [ ] Database connection configured
  - [ ] SIP/RTP ports configured
  - [ ] Codec preferences set
  - [ ] Extensions configured
  - [ ] Dialplan rules configured
  - [ ] SIP trunks configured (if applicable)

- [ ] **Voice Prompts**
  - [ ] All voice prompts generated
  - [ ] Correct sample rate (8kHz for PCMU)
  - [ ] Tested on actual phones
  - [ ] Custom greetings recorded (if needed)

### 2.2 Systemd Service
- [ ] **Service Configuration**
  - [ ] `pbx.service` file installed in `/etc/systemd/system/`
  - [ ] Service user configured
  - [ ] Working directory set
  - [ ] Environment variables configured
  - [ ] Restart policy configured
  - [ ] Service enabled (`systemctl enable pbx`)
  - [ ] Service starts on boot

- [ ] **Service Testing**
  - [ ] Service starts successfully
  - [ ] Service stops gracefully
  - [ ] Service restarts without issues
  - [ ] Logs are written correctly
  - [ ] Automatic restart on failure works

### 2.3 Reverse Proxy (Nginx/Apache)
- [ ] **Web Server Setup**
  - [ ] Nginx or Apache installed
  - [ ] Virtual host configured
  - [ ] Reverse proxy to port 8080 configured
  - [ ] SSL/TLS certificate installed
  - [ ] HTTPS enabled and HTTP redirected
  - [ ] WebSocket support enabled (for WebRTC)
  - [ ] Security headers configured (CSP, HSTS, etc.)
  - [ ] Rate limiting configured
  - [ ] Access logs configured

---

## 3. Security & Compliance

### 3.1 SSL/TLS Certificates
- [ ] **Certificate Management**
  - [ ] Valid SSL certificate installed (Let's Encrypt or CA)
  - [ ] Private key secured (chmod 600)
  - [ ] Certificate chain complete
  - [ ] Auto-renewal configured (certbot for Let's Encrypt)
  - [ ] Certificate expiration monitoring configured
  - [ ] TLS 1.2+ enforced, TLS 1.0/1.1 disabled
  - [ ] Strong cipher suites configured

### 3.2 Authentication & Authorization
- [ ] **User Security**
  - [ ] Strong password policy enforced (12+ characters)
  - [ ] Default passwords changed
  - [ ] Admin accounts secured
  - [ ] Password hashing verified (PBKDF2-HMAC-SHA256)
  - [ ] Session timeouts configured (24 hours)
  - [ ] Multi-factor authentication enabled (optional)
  - [ ] Failed login lockout configured

### 3.3 FIPS 140-2 Compliance
- [ ] **Cryptographic Standards**
  - [ ] FIPS mode enabled in configuration
  - [ ] FIPS-approved algorithms verified
  - [ ] No deprecated algorithms (MD5, SHA-1, DES, RC4)
  - [ ] FIPS verification script run successfully
  - [ ] Ubuntu FIPS kernel enabled (if required)
  - [ ] FIPS health check automated

### 3.4 Network Security
- [ ] **Firewall & Access Control**
  - [ ] Firewall (UFW/iptables) configured and enabled
  - [ ] Only required ports open
  - [ ] IP whitelisting configured (if applicable)
  - [ ] Fail2ban installed and configured
  - [ ] Rate limiting enabled
  - [ ] DDoS protection configured (reverse proxy)
  - [ ] SIP authentication required
  - [ ] RTP encryption (SRTP) enabled (if required)

### 3.5 Compliance
- [ ] **Regulatory Requirements**
  - [ ] E911 location tracking configured
  - [ ] Kari's Law compliance verified (direct 911 dialing)
  - [ ] Ray Baum's Act compliance verified (dispatchable location)
  - [ ] STIR/SHAKEN configured (if applicable)
  - [ ] Call recording compliance verified (legal requirements)
  - [ ] Recording announcements configured (if required)
  - [ ] Data retention policies configured
  - [ ] Privacy policy documented
  - [ ] GDPR compliance verified (if applicable)

---

## 4. Monitoring & Alerting

### 4.1 System Monitoring
- [ ] **Infrastructure Monitoring**
  - [ ] CPU usage monitoring
  - [ ] Memory usage monitoring
  - [ ] Disk space monitoring
  - [ ] Network bandwidth monitoring
  - [ ] System load monitoring
  - [ ] Alerts configured for thresholds

- [ ] **Application Monitoring**
  - [ ] PBX service status monitoring
  - [ ] SIP registration monitoring
  - [ ] Active calls monitoring
  - [ ] Call quality (MOS) monitoring
  - [ ] Extension status monitoring
  - [ ] API endpoint monitoring
  - [ ] Database connection pool monitoring

### 4.2 Logging
- [ ] **Log Management**
  - [ ] Application logs configured (`/var/log/pbx/`)
  - [ ] Log rotation configured (logrotate)
  - [ ] Log retention policy defined (30-90 days)
  - [ ] Centralized logging configured (optional: Elasticsearch/Splunk)
  - [ ] Log levels appropriate for production (INFO/WARNING)
  - [ ] Sensitive data not logged (passwords, tokens)
  - [ ] Audit logs enabled for admin actions

### 4.3 Alerting
- [ ] **Alert Configuration**
  - [ ] Email alerts configured (SMTP)
  - [ ] Critical alerts defined:
    - [ ] Service down
    - [ ] Database connection failure
    - [ ] Disk space >80%
    - [ ] High CPU/memory usage
    - [ ] Call quality degradation
    - [ ] Security events (failed logins, etc.)
    - [ ] Certificate expiration (30 days)
  - [ ] Alert recipients configured
  - [ ] Alert escalation policy defined
  - [ ] Alert testing completed

### 4.4 Metrics & Dashboards
- [ ] **Performance Metrics**
  - [ ] Prometheus metrics endpoint configured (optional)
  - [ ] Grafana dashboard configured (optional)
  - [ ] Key metrics tracked:
    - [ ] Concurrent calls
    - [ ] Call success rate
    - [ ] Average call duration
    - [ ] Registration count
    - [ ] API response times
    - [ ] Database query performance
    - [ ] System resource utilization

---

## 5. Backup & Disaster Recovery

### 5.1 Backup Strategy
- [ ] **What to Backup**
  - [ ] Database (automated pg_dump)
  - [ ] Configuration files (`config.yml`, `.env`)
  - [ ] Voicemail recordings
  - [ ] Call recordings (if retention required)
  - [ ] Custom voice prompts
  - [ ] SSL certificates and keys
  - [ ] Phone provisioning templates

- [ ] **Backup Schedule**
  - [ ] Daily database backups (2 AM recommended)
  - [ ] Weekly full system backups
  - [ ] Configuration file backups on change
  - [ ] Backup retention: 30 days local, 90 days off-site
  - [ ] Backup integrity verification automated

- [ ] **Backup Storage**
  - [ ] Local backup location configured
  - [ ] Off-site backup configured (S3, NAS, etc.)
  - [ ] Backup encryption enabled
  - [ ] Backup access restricted
  - [ ] Backup monitoring and alerts configured

### 5.2 Disaster Recovery
- [ ] **DR Planning**
  - [ ] Recovery Time Objective (RTO) defined
  - [ ] Recovery Point Objective (RPO) defined
  - [ ] DR procedures documented
  - [ ] Failover procedures documented
  - [ ] DR site configured (if applicable)
  - [ ] DR testing scheduled (quarterly recommended)

- [ ] **Recovery Procedures**
  - [ ] Database restoration tested
  - [ ] Full system restoration tested
  - [ ] Configuration restoration tested
  - [ ] Recovery runbook created
  - [ ] Recovery time measured and acceptable

---

## 6. Performance & Capacity

### 6.1 Performance Testing
- [ ] **Load Testing**
  - [ ] Maximum concurrent calls tested
  - [ ] Maximum registrations tested
  - [ ] API load testing completed
  - [ ] Database performance tested
  - [ ] Network bandwidth requirements validated
  - [ ] Resource usage at peak load documented

### 6.2 Capacity Planning
- [ ] **Current Capacity**
  - [ ] Maximum extensions: _______
  - [ ] Maximum concurrent calls: _______
  - [ ] Maximum call queue size: _______
  - [ ] Maximum voicemail storage: _______
  - [ ] Maximum call recording storage: _______

- [ ] **Growth Planning**
  - [ ] 6-month capacity projection documented
  - [ ] 12-month capacity projection documented
  - [ ] Scaling plan documented
  - [ ] Hardware upgrade path defined

### 6.3 Optimization
- [ ] **Performance Tuning**
  - [ ] Database query optimization completed
  - [ ] Connection pooling configured
  - [ ] Codec selection optimized (bandwidth vs quality)
  - [ ] RTP buffer sizes tuned
  - [ ] System kernel parameters tuned (if needed)
  - [ ] Application caching enabled (where appropriate)

---

## 7. Testing & Validation

### 7.1 Functional Testing
- [ ] **Core Features**
  - [ ] SIP registration tested
  - [ ] Inbound calls tested
  - [ ] Outbound calls tested
  - [ ] Internal extension-to-extension calls tested
  - [ ] Call transfer tested (blind and attended)
  - [ ] Call forwarding tested
  - [ ] Call parking tested
  - [ ] Conference calling tested
  - [ ] Voicemail deposit and retrieval tested
  - [ ] Voicemail email notifications tested
  - [ ] Call recording tested
  - [ ] Call queues tested
  - [ ] Auto attendant (IVR) tested
  - [ ] Music on hold tested

- [ ] **Advanced Features**
  - [ ] E911 location tested
  - [ ] SIP trunks tested (if configured)
  - [ ] Phone provisioning tested
  - [ ] Hot desking tested
  - [ ] Click-to-dial tested
  - [ ] Presence status tested
  - [ ] Find me/follow me tested
  - [ ] Time-based routing tested

### 7.2 Integration Testing
- [ ] **External Systems**
  - [ ] SIP phones tested (all models in deployment)
  - [ ] Softphones tested (if supported)
  - [ ] SIP trunk provider tested
  - [ ] Active Directory integration tested (if configured)
  - [ ] Email integration tested (SMTP)
  - [ ] CRM integration tested (if configured)
  - [ ] API integration tested
  - [ ] Webhook integrations tested

### 7.3 Security Testing
- [ ] **Vulnerability Assessment**
  - [ ] SSL/TLS configuration tested (SSLLabs)
  - [ ] Password strength enforced and tested
  - [ ] Authentication bypass attempts tested
  - [ ] SQL injection attempts tested
  - [ ] XSS attempts tested
  - [ ] CSRF protection tested
  - [ ] Rate limiting tested
  - [ ] SIP flooding tested
  - [ ] Unauthorized access attempts tested
  - [ ] CodeQL security scan passed

### 7.4 Failover Testing
- [ ] **Resilience Testing**
  - [ ] Service restart tested
  - [ ] Database connection loss tested
  - [ ] Network interruption tested
  - [ ] SIP trunk failover tested (if multiple trunks)
  - [ ] Power failure recovery tested
  - [ ] Automatic service recovery tested

---

## 8. Documentation

### 8.1 System Documentation
- [ ] **Technical Documentation**
  - [ ] Architecture diagram created
  - [ ] Network diagram created
  - [ ] Data flow diagrams created
  - [ ] Database schema documented
  - [ ] API documentation complete
  - [ ] Configuration guide complete
  - [ ] Integration guide complete

### 8.2 Operations Documentation
- [ ] **Operational Procedures**
  - [ ] Installation guide verified
  - [ ] Deployment guide verified
  - [ ] Upgrade procedures documented
  - [ ] Backup and restore procedures documented
  - [ ] Disaster recovery procedures documented
  - [ ] Troubleshooting guide complete
  - [ ] Common issues and solutions documented
  - [ ] Emergency contacts documented

### 8.3 User Documentation
- [ ] **End User Guides**
  - [ ] Admin panel user guide
  - [ ] Phone user guide
  - [ ] Voicemail user guide
  - [ ] Call features guide (transfer, park, etc.)
  - [ ] FAQ document created
  - [ ] Training materials prepared

### 8.4 Compliance Documentation
- [ ] **Regulatory Documentation**
  - [ ] E911 compliance documentation
  - [ ] Call recording compliance documentation
  - [ ] Data retention policies documented
  - [ ] Privacy policy documented
  - [ ] Security policies documented
  - [ ] Incident response plan documented

---

## 9. Support & Maintenance

### 9.1 Support Structure
- [ ] **Support Team**
  - [ ] On-call rotation defined
  - [ ] Escalation procedures defined
  - [ ] Support ticket system configured
  - [ ] Support SLA defined
  - [ ] Knowledge base created
  - [ ] Training completed for support staff

### 9.2 Maintenance Windows
- [ ] **Scheduled Maintenance**
  - [ ] Maintenance windows scheduled
  - [ ] Maintenance procedures documented
  - [ ] Change management process defined
  - [ ] Rollback procedures documented
  - [ ] Maintenance notifications configured

### 9.3 Updates & Patches
- [ ] **Update Strategy**
  - [ ] Update testing environment configured
  - [ ] Update procedures documented
  - [ ] Security patch policy defined
  - [ ] Update notification process defined
  - [ ] Automated update checking configured (optional)

---

## 10. Go-Live Preparation

### 10.1 Pre-Launch Checklist
- [ ] **Final Verification**
  - [ ] All sections of this checklist completed
  - [ ] All critical tests passed
  - [ ] All documentation complete and verified
  - [ ] All stakeholders notified
  - [ ] Rollback plan prepared
  - [ ] Support team ready
  - [ ] Monitoring confirmed operational
  - [ ] Backups verified and tested

### 10.2 Launch Plan
- [ ] **Deployment Strategy**
  - [ ] Phased rollout plan defined (if applicable)
  - [ ] Pilot group identified (if applicable)
  - [ ] Cutover time scheduled
  - [ ] Migration plan documented (if replacing existing system)
  - [ ] Cutover checklist created
  - [ ] Communication plan defined
  - [ ] User training scheduled

### 10.3 Post-Launch
- [ ] **Immediate Post-Launch**
  - [ ] Day 1 monitoring plan defined
  - [ ] Week 1 review scheduled
  - [ ] Month 1 review scheduled
  - [ ] Lessons learned session scheduled
  - [ ] Performance baseline established
  - [ ] User feedback collection method defined

---

## 11. Sign-Off

### Approval Required From:

**Technical Team:**
- [ ] System Administrator: _________________ Date: _______
- [ ] Network Administrator: ________________ Date: _______
- [ ] Security Officer: _____________________ Date: _______
- [ ] Database Administrator: _______________ Date: _______

**Business Team:**
- [ ] Project Manager: _____________________ Date: _______
- [ ] Business Owner: ______________________ Date: _______
- [ ] Compliance Officer: ___________________ Date: _______

**Final Approval:**
- [ ] IT Director/CTO: ______________________ Date: _______

---

## Notes

Use this section to document any exceptions, deviations, or additional notes:

```
[Add notes here]
```

---

## Appendix

### A. Related Documentation
- [README.md](../README.md) - Project overview
- [COMPLETE_GUIDE.md](../COMPLETE_GUIDE.md) - Comprehensive documentation
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Troubleshooting guide
- [COMPLETE_GUIDE.md - Section 6: Security & Compliance](../COMPLETE_GUIDE.md#6-security--compliance) - FIPS compliance and security

### B. Deployment Scripts
- `scripts/deploy_production_pilot.sh` - Automated deployment script
- `scripts/setup_production_env.py` - Environment setup
- `scripts/verify_fips.py` - FIPS compliance verification
- `scripts/check_fips_health.py` - FIPS health check

### C. Monitoring Tools
- `healthcheck.py` - Health check endpoint
- `pbx/utils/production_health.py` - Production health checker
- `pbx/features/qos_monitoring.py` - Call quality monitoring

---

**Document Version**: 1.0.0  
**Last Updated**: January 2, 2026  
**Next Review**: [Schedule quarterly reviews]
