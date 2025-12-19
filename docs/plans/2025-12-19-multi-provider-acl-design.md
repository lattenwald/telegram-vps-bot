# Multi-Provider ACL Design

**Date**: 2025-12-19
**Status**: Approved
**Task**: TASK-001

---

## Overview

Unified access control system supporting multiple VPS providers (BitLaunch, Kamatera) with granular per-user, per-provider, per-server permissions.

---

## ACL Structure

```yaml
admins:
  - 123456789
  - 987654321

users:
  "111222333":
    bitlaunch:
      servers: ["prod-web", "prod-db"]  # only these servers
    kamatera: {}                         # all servers
  "444555666":
    kamatera:
      servers: []                        # explicit deny
```

### Field Semantics

| Field | Type | Meaning |
|-------|------|---------|
| `admins` | `list[int]` | Chat IDs with full access |
| `users` | `dict[str, UserPerms]` | Per-user permissions |
| `users.<id>.<provider>` | `dict` | Access to this provider |
| `users.<id>.<provider>.servers` | `list[str] \| null` | Allowed servers |

### Server Access Rules

| Value | Meaning |
|-------|---------|
| `servers` omitted/null | All servers allowed |
| `servers: []` | Access denied (explicit block) |
| `servers: ["a", "b"]` | Only listed servers |

---

## Storage

### ACL Configuration
- **Location**: SSM Parameter `/telegram-vps-bot/acl-config`
- **Format**: JSON (edited locally as YAML)
- **Why SSM**: Consistent with secrets pattern, no redeploy needed

### Provider Credentials
- `/telegram-vps-bot/credentials/bitlaunch` → `{"api_key": "..."}`
- `/telegram-vps-bot/credentials/kamatera` → `{"client_id": "...", "secret": "..."}`
- **Why JSON per provider**: Self-documenting, extensible

---

## Management Script

```bash
python scripts/manage_acl.py get           # Fetch as YAML
python scripts/manage_acl.py set acl.yaml  # Upload from YAML
python scripts/manage_acl.py validate acl.yaml
```

### Validation Rules
- `admins` is list of integers
- User keys are string integers (chat IDs)
- Provider names are known (`bitlaunch`, `kamatera`)
- `servers` is null, list of strings, or omitted

---

## Authorization Logic

```python
def is_authorized(chat_id: int, provider: str, server: str) -> bool:
    acl = config.acl_config

    # Admins have full access
    if chat_id in acl.get("admins", []):
        return True

    # Check user permissions
    user = acl.get("users", {}).get(str(chat_id))
    if not user:
        return False

    # Check provider access
    provider_perms = user.get(provider)
    if provider_perms is None:
        return False

    # Check server access
    servers = provider_perms.get("servers")
    if servers is None:
        return True   # all servers
    if servers == []:
        return False  # explicit deny
    return server in servers
```

---

## Command Syntax

| Input | Provider | Server |
|-------|----------|--------|
| `/reboot prod-web` | Auto-detect | prod-web |
| `/reboot bitlaunch:prod-web` | bitlaunch | prod-web |
| `/reboot kamatera:my-vps` | kamatera | my-vps |

### Provider Resolution
1. If explicit (`provider:server`), use specified provider
2. If user has single provider access, use that
3. If user has multiple providers, try in order until found

---

## Provider Abstraction

```python
class ProviderClient(ABC):
    @abstractmethod
    def find_server_by_name(self, server_name: str) -> dict | None:
        pass

    @abstractmethod
    def reboot_server(self, server_name: str) -> bool:
        pass
```

### File Structure
```
src/providers/
├── __init__.py      # Registry: {"bitlaunch": BitLaunchClient, ...}
├── base.py          # ProviderClient ABC
├── bitlaunch.py     # Existing, refactored
└── kamatera.py      # New
```

---

## Caching

**Strategy**: In-memory server→provider cache
- Persists across warm Lambda invocations (~15-45 min)
- Lost on cold start (acceptable for personal bot)
- Free, no infrastructure

**Postponed**: DynamoDB for persistent cache (TASK-002)

---

## Technical Decisions

| Decision | Chosen | Alternatives | Reasoning |
|----------|--------|--------------|-----------|
| ACL storage | SSM | Terraform, DynamoDB | No redeploy, consistent pattern |
| ACL format | YAML→JSON | JSON only, YAML only | Human editing + lean Lambda |
| Admin structure | Separate list | Wildcard provider | Clear mental model |
| Server matching | Exact name | Pattern, ID | Simple, matches UX |
| Credentials | JSON per provider | Separate params | Self-documenting, extensible |
| Caching | In-memory | DynamoDB | Free, sufficient |

---

## Migration Steps

1. Create new SSM parameters:
   - `/telegram-vps-bot/acl-config`
   - `/telegram-vps-bot/credentials/bitlaunch`
   - `/telegram-vps-bot/credentials/kamatera`

2. Migrate BitLaunch API key to JSON format

3. Deprecate:
   - `AUTHORIZED_CHAT_IDS` env var
   - `/telegram-vps-bot/bitlaunch-api-key` SSM param

---

## Postponed Features

- **TASK-002**: DynamoDB caching for cold start persistence
- **TASK-003**: Bot admin commands (`/grant`, `/revoke`, `/acl`)
