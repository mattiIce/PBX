# Security Policy

## Supported Versions

The following versions of Warden VoIP currently receive security updates:

| Version | Supported |
| ------- | --------- |
| 1.0.x   | Yes       |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please use [GitHub private vulnerability reporting](https://github.com/mattiIce/PBX/security/advisories/new) to disclose security issues confidentially.

When reporting, please include:

- A clear description of the vulnerability
- Step-by-step reproduction instructions
- An impact assessment (what an attacker could achieve)
- The affected versions

## Response Timeline

- **48 hours** — acknowledgment of your report
- **7 days** — triage and initial severity assessment
- **30 days** — patch released for critical and high-severity findings
- **CVE assignment** — requested for all confirmed vulnerabilities

We will keep you informed throughout the process and credit you in the release notes unless you prefer to remain anonymous.

## Disclosure Policy

We follow a **90-day coordinated disclosure** window. After a fix is released (or after 90 days if a fix cannot be produced in time), reporters are free to publish their findings publicly. We will credit reporters in the security advisory and release notes.

## Security Measures

Warden VoIP incorporates multiple layers of security controls:

- **FIPS 140-2 encryption** — implemented in `pbx/utils/encryption.py`
- **TLS 1.3** — enforced for all SIP and admin-interface traffic via `pbx/utils/tls_support.py`
- **STIR/SHAKEN** — caller ID attestation to prevent spoofing
- **CI security scanning** — every pull request is checked by:
  - `bandit` — Python SAST
  - `pip-audit` — dependency vulnerability audit
  - `Trivy` — container and filesystem scanning
  - `gitleaks` — secret detection
- **Pre-commit hooks** — `bandit` runs locally before every commit to catch issues early
