# TASK-001: Multi-Provider ACL Implementation

**Status**: 🚧 In Progress
**Created**: 2025-12-19
**Assignee**: Manual

---

## Context

**Problem**:
Current authorization is a flat list of chat IDs with access to a single provider (BitLaunch). Need to support multiple VPS providers (BitLaunch, Kamatera) with granular per-user, per-provider, per-server access control.

**Goal**:
Implement a unified ACL system that supports:
- Admin users with full access to all providers/servers
- Per-user access control with provider-specific permissions
- Optional server filtering (allow specific servers or all)

**Success Criteria**:
- [x] ACL configuration stored in SSM as JSON ✅
- [x] Management script for YAML editing and upload ✅
- [ ] Provider abstraction supporting BitLaunch and Kamatera (BitLaunch done)
- [x] Updated auth logic with provider/server checks ✅
- [x] Backward-compatible command syntax ✅

---

## Implementation Plan

### Phase 1: ACL Structure & Storage ✅
**Goal**: Define and implement ACL configuration storage

**Tasks**:
- [x] Create ACL JSON schema ✅
- [x] Add SSM parameter `/telegram-vps-bot/acl-config` ✅
- [x] Update `config.py` with `acl_config` property ✅
- [x] Migrate from `AUTHORIZED_CHAT_IDS` env var ✅

**Files**:
- `src/config.py` - Added `ProviderAccess`, `ACLConfig` dataclasses, `acl_config` property ✅

### Phase 2: Management Script ✅
**Goal**: Create script for ACL management

**Tasks**:
- [x] Implement `get` command (fetch JSON → display YAML) ✅
- [x] Implement `set` command (read YAML → upload JSON) ✅
- [x] Implement `validate` command (check structure) ✅
- [x] Add validation for admins, users, providers, servers ✅

**Files**:
- `scripts/manage_acl.py` - PEP 723 script with pydantic validation ✅

### Phase 3: Credentials Migration ✅
**Goal**: Unified credential storage per provider

**Tasks**:
- [x] Create `/telegram-vps-bot/credentials/bitlaunch` with JSON format ✅
- [ ] Create `/telegram-vps-bot/credentials/kamatera` with JSON format
- [x] Update `config.py` with `get_provider_credentials()` method ✅
- [x] Migrate existing BitLaunch API key ✅
- [x] Update IAM policy for wildcard SSM access (`/telegram-vps-bot/*`) ✅

**Files**:
- `src/config.py` - Add credential loading ✅
- `infrastructure/iam.tf` - Wildcard SSM access ✅

### Phase 4: Provider Abstraction ✅ (BitLaunch)
**Goal**: Create unified provider interface

**Tasks**:
- [x] Create `ProviderClient` ABC with `find_server_by_name`, `reboot_server` ✅
- [x] Refactor `BitLaunchClient` to implement interface ✅
- [ ] Create `KamateraClient` implementing interface
- [x] Create provider registry and factory ✅

**Files**:
- `src/providers/__init__.py` - Provider registry ✅
- `src/providers/base.py` - Abstract base class ✅
- `src/providers/bitlaunch.py` - Refactored from `bitlaunch_client.py` ✅
- `src/providers/kamatera.py` - New Kamatera client (pending)

### Phase 5: Authorization Logic ✅
**Goal**: Update auth to support multi-provider ACL

**Tasks**:
- [x] Implement `is_authorized(chat_id, provider, server)` ✅
- [x] Implement `is_admin(chat_id)` ✅
- [x] Implement `get_user_providers(chat_id)` for auto-detection ✅
- [x] ACL caching in config (in-memory) ✅

**Files**:
- `src/auth.py` - Updated authorization logic ✅
- `src/config.py` - ACL dataclasses and loading ✅

### Phase 6: Handler Updates ✅
**Goal**: Support new command syntax

**Tasks**:
- [ ] Implement `parse_server_arg()` for `provider:server` syntax (future)
- [x] Add `/find <server>` command (read-only, tests provider) ✅
- [x] Add Markdown formatting with `escape_markdown()` helper ✅
- [x] Add `parse_mode` support to `send_success/error_message` ✅
- [x] Update `/reboot` handler with provider-aware auth ✅
- [x] Update `/find` handler with provider-aware auth ✅
- [ ] Auto-detect provider when user has single provider access (future)
- [ ] Try providers in order when multiple allowed (future)

**Files**:
- `src/handler.py` - Updated command handling ✅
- `src/telegram_client.py` - Markdown support ✅

### Phase 7: Testing & Documentation ✅
**Goal**: Ensure coverage and document changes

**Tasks**:
- [x] Unit tests for new auth logic (14 tests) ✅
- [x] Unit tests for ACL dataclasses ✅
- [x] Integration tests for handler ✅
- [ ] Update README with new command syntax
- [ ] Update API docs

**Files**:
- `tests/test_auth.py` - New auth tests ✅
- `tests/conftest.py` - ACL mock in SSM ✅

---

## Technical Decisions

| Decision | Options Considered | Chosen | Reasoning |
|----------|-------------------|--------|-----------|
| ACL storage | SSM, Terraform vars, DynamoDB | SSM | Consistent with secrets pattern, no redeploy needed |
| ACL format | JSON only, YAML only, Hybrid | YAML→JSON | Human-readable editing, lean Lambda (no pyyaml) |
| Admin structure | Separate list, Wildcard provider, Role field | Separate list | Clearest mental model, fast lookup |
| Server matching | Exact, Pattern, ID-based | Exact name | Simple, matches command UX |
| All servers | Omit field, Wildcard, Boolean | Omit/null | Natural to read/write |
| Credentials | Separate params, JSON per provider, Single JSON | JSON per provider | Clean separation, self-documenting |
| Caching | In-memory, DynamoDB, Redis | In-memory | Free, sufficient for warm invocations |

---

## ACL Structure

```yaml
admins:
  - 122247178        # Full access to all providers/servers

users:
  "370823094":
    bitlaunch: {}    # All BitLaunch servers
```

**Server access rules**:
- `servers` omitted or `null` → all servers allowed
- `servers: []` → access denied (explicit block)
- `servers: ["a", "b"]` → only those servers

**Current ACL in SSM**: `/telegram-vps-bot/acl-config`

---

## Dependencies

**Requires**:
- [ ] Kamatera API credentials (client_id + secret)
- [x] SSM parameters created in AWS ✅

**Blocks**:
- [ ] TASK-002: DynamoDB caching
- [ ] TASK-003: Bot admin commands

---

## Implementation Order

Practical order (not phase order):

1. **Provider abstraction** (Phase 4) ✅ DONE
   - Created `ProviderClient` ABC
   - Refactored `BitLaunchClient` to implement interface
   - Created `create_provider_client()` factory
   - Removed old `bitlaunch_client.py`

2. **Credentials migration** (Phase 3, BitLaunch only) ✅ DONE
   - [x] Updated `config.py` with `get_provider_credentials()`
   - [x] Updated `handler.py` to use factory
   - [x] Created SSM parameter `/telegram-vps-bot/credentials/bitlaunch`
   - [x] Updated IAM policy for wildcard SSM access
   - [x] Deployed and tested

3. **Deploy & test BitLaunch** ✅ DONE
   - [x] Verified `/reboot` functionality works
   - [x] Added `/find` command for safe testing
   - [x] Added Markdown formatting
   - [x] Increased Lambda timeout to 60s

4. **ACL implementation** (Phases 1, 2, 5) ✅ DONE
   - [x] Created `scripts/manage_acl.py` with get/set/validate commands
   - [x] Added `ProviderAccess` and `ACLConfig` dataclasses to config.py
   - [x] Added `acl_config` property to load ACL from SSM
   - [x] Updated `auth.py` with `is_authorized(chat_id, provider, server)`
   - [x] Added `is_admin()` and `get_user_providers()` functions
   - [x] Updated handler to use provider-aware auth
   - [x] Created initial ACL in SSM
   - [x] Added 14 new auth tests (61 total, 84% coverage)

5. **Kamatera** (Phase 4 continued) ⏳ NEXT
   - Add `KamateraClient`
   - Add Kamatera credentials to SSM

---

## Next Steps

1. **Deploy and test ACL** ⏳
   - Run `terraform apply` to deploy new code
   - Test with admin (122247178) and user (370823094)

2. **Add Kamatera support** (when ready)
   - Get Kamatera API credentials
   - Create `/telegram-vps-bot/credentials/kamatera` in SSM
   - Implement `KamateraClient` in `src/providers/kamatera.py`
   - Update ACL with Kamatera permissions

3. **Optional enhancements**
   - `provider:server` syntax for explicit provider selection
   - Auto-detect provider for single-provider users
   - Update documentation

---

## Notes

- Kamatera API uses Client ID + Secret (vs BitLaunch single API key)
- Kamatera API base: `console.kamatera.com`
- Command syntax: `/reboot server` or `/reboot provider:server` (future)
- Default provider: BitLaunch (for backward compatibility)

**API Differences:**
| Provider | Find Server | Method |
|----------|-------------|--------|
| BitLaunch | Fetch all → filter client-side | No server-side filter |
| Kamatera | POST `/service/server/info` with `{"name": "..."}` | Server-side filter (supports regex) |

---

## Completion Checklist

Before marking complete:
- [x] ACL phases implemented ✅
- [x] Tests written and passing (>80% coverage) ✅
- [ ] Documentation updated
- [x] Management script tested ✅
- [x] Credentials migrated to new format ✅
- [ ] Kamatera support added

---

**Last Updated**: 2025-12-19 (ACL implementation complete, ready for deploy)
