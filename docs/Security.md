# Security

The security module provides network security utilities for nanobot.

## Files

| File | Description |
|------|-------------|
| `security/__init__.py` | Module initialization |
| `security/network.py` | Network security utilities |

---

## Network Security

**File:** `security/network.py`

### SSRF Protection

Prevents the bot from accessing internal/private URLs (Server-Side Request Forgery protection).

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `validate_url_target` | url | tuple[bool, str] | Validate a URL is safe to fetch |
| `validate_resolved_url` | url | tuple[bool, str] | Validate an already-fetched URL |
| `contains_internal_url` | command | bool | Scan command for internal URLs |

### validate_url_target

Validates a URL is safe to fetch.

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | str | URL to validate |

| Returns | Type | Description |
|---------|------|-------------|
| tuple[bool, str] | (ok, error_message) | Whether URL is safe |

Checks:
- Scheme must be http or https
- Hostname must be present
- Resolves to public IP (not private/internal)

### validate_resolved_url

Validates an already-fetched URL (after redirect).

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | str | URL to validate |

Only checks IP - skips DNS resolution for performance.

### contains_internal_url

Scans a command string for URLs targeting internal/private addresses.

| Parameter | Type | Description |
|-----------|------|-------------|
| `command` | str | Command to scan |

| Returns | Type | Description |
|---------|------|-------------|
| bool | True if internal URL found | |

---

## Blocked Networks

The following private/internal networks are blocked:

| Network | CIDR | Description |
|---------|------|-------------|
| Current network | 0.0.0.0/8 | |
| Private Class A | 10.0.0.0/8 | |
| Carrier-grade NAT | 100.64.0.0/10 | |
| Loopback | 127.0.0.0/8 | |
| Link-local | 169.254.0.0/16 | Cloud metadata |
| Private Class B | 172.16.0.0/12 | |
| Private Class C | 192.168.0.0/16 | |
| IPv6 loopback | ::1/128 | |
| IPv6 unique local | fc00::/7 | |
| IPv6 link-local | fe80::/10 | |

---

## Usage

Used by:
- `agent/tools/web.py` - WebFetchTool validates URLs before fetching
- `agent/tools/shell.py` - ExecTool blocks commands with internal URLs
