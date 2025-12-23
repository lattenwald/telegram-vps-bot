# /list Command Design

**Date:** 2025-12-23
**Status:** Approved

## Overview

Add `/list [provider]` command to list VPS servers with optional provider filtering.

## Command Syntax

```
/list              - List all servers (grouped by provider)
/list <provider>   - List servers for specific provider
```

## Authorization

- Uses existing `is_authorized(chat_id, provider)` pattern
- Without provider arg: queries all providers user can access
- With provider arg: validates user has access to that provider
- Server-level ACL filtering applied to results

## Output Format

### Single Provider
```
📋 bitlaunch (2 servers):
• my-server-1 (running) - `1.2.3.4`
• my-server-2 (stopped) - `5.6.7.8`
```

### Multi-Provider (grouped)
```
📋 bitlaunch (2 servers):
• my-server-1 (running) - `1.2.3.4`
• my-server-2 (stopped) - `5.6.7.8`

📋 kamatera (1 server):
• prod-web (running) - `9.10.11.12`
```

### Server Info Normalization

Each provider's `list_servers()` returns normalized format:
```python
{"name": str, "status": str, "ip": str | None}
```

## Edge Cases

### Empty States

| Scenario | Admin | User |
|----------|-------|------|
| Provider has 0 servers | Show: "📋 bitlaunch (0 servers)" | Skip silently |
| No allowed servers after ACL filter | Show all (no filter) | Skip silently |
| All providers empty/skipped | "No servers found" | "No servers found" |

### Error States

**Provider API Failure:**
```
⚠️ kamatera: Unable to fetch servers
```
- Shown for both admins and users (on allowed providers)
- Doesn't block other providers from showing

**Invalid Provider:**
- Admin: `❌ Unknown provider 'foo'. Available: bitlaunch, kamatera`
- User: `❌ Unknown provider 'foo'. Available: bitlaunch` (only allowed providers)

**Unauthorized Provider:**
```
❌ Access denied for provider `kamatera`
```

## Files to Modify

1. `src/providers/base.py` - Add abstract `list_servers()` method
2. `src/providers/bitlaunch.py` - Implement `list_servers()`
3. `src/providers/kamatera.py` - Implement `list_servers()`
4. `src/handler.py` - Add `handle_list_command()`, update `process_command()`, update `/help`
5. `scripts/setup_commands.py` - Add `/list` command
6. `tests/test_handler.py` - Add tests following existing patterns

## Test Cases

1. `/list` - admin sees all providers grouped
2. `/list` - user sees only allowed providers/servers
3. `/list bitlaunch` - filter to single provider
4. `/list unknown` - error with appropriate provider list
5. `/list kamatera` - unauthorized provider for user
6. Provider API failure - partial results with error note
7. Empty results - appropriate message per role
