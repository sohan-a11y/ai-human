# Security Policy

## Overview

AI Human is an autonomous AI agent that operates your computer. It has broad system
access by design. This document explains the security model, known risks, and how
to report vulnerabilities.

## Security Model

### What AI Human can access
- Full file system (read/write/delete)
- Run any terminal command
- Control keyboard and mouse
- Take screenshots
- Access the internet
- Read/send emails (if configured)
- Control your browser

**This is intentional** — it needs these permissions to be useful. However, all
actions pass through the Safety Broker which blocks dangerous operations.

### Safety Broker
Actions are scored 0–10 for risk. You configure thresholds in `.env`:
- `SAFETY_CONFIRM_THRESHOLD=7` — asks for approval before acting
- `SAFETY_BLOCK_THRESHOLD=9` — always blocked, no override

### Remote Control Authentication
The web dashboard (port 8080) and mobile bridge (port 8081) support API token auth.
**Always set a token if your machine is on a shared or untrusted network:**

```bash
# Generate a strong token
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
REMOTE_API_TOKEN=<your_token>
MOBILE_API_TOKEN=<your_token>
```

### Credential Vault
Sensitive credentials (API keys, passwords) are stored encrypted using Fernet
symmetric encryption (AES-128-CBC + HMAC-SHA256). The vault is unlocked via:

```bash
export AI_HUMAN_VAULT_PASS="your_passphrase"
python launcher.py
```

**Never pass the passphrase as a CLI argument** — it will appear in process lists
and shell history.

## Known Security Limitations

| Limitation | Risk | Mitigation |
|---|---|---|
| Agent has full user permissions | High | Safety Broker + confirmation dialogs |
| No sandboxing of agent actions | Medium | Safety Broker thresholds |
| Peer network has no authentication by default | Medium | Set peer tokens, use on trusted LAN only |
| Browser extension uses plain `ws://` | Low | Only connects to localhost |
| Plugin code is sandboxed but not containerized | Medium | AST scanner blocks dangerous imports |
| Screen recorder stores video locally | Low | Stored in `data/recordings/`, add to .gitignore |

## Supported Versions

| Version | Supported |
|---|---|
| Latest (main branch) | ✅ Yes |
| Older releases | ❌ Use latest |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues by:
1. Opening a [GitHub Security Advisory](https://github.com/YOUR_ORG/ai-human/security/advisories/new)
2. Or emailing the maintainers directly (see GitHub profile)

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We aim to respond within 48 hours and release a patch within 7 days for critical issues.

## Security Checklist for Deployment

Before running on a shared or production system:

- [ ] Set `REMOTE_API_TOKEN` and `REMOTE_MOBILE_TOKEN` in `.env`
- [ ] Set `AI_HUMAN_VAULT_PASS` via environment, not CLI
- [ ] Review `SAFETY_CONFIRM_THRESHOLD` and `SAFETY_BLOCK_THRESHOLD`
- [ ] Ensure `data/vault.enc` and `data/vault.salt` are in `.gitignore`
- [ ] Do not expose ports 8080, 8081, 8090 to the public internet
- [ ] Run as a non-administrator user where possible
- [ ] Review installed plugins before enabling them
