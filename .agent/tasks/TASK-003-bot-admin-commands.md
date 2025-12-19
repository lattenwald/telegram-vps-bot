# TASK-003: Bot Admin Commands for ACL Management

**Status**: ⏸️ Postponed
**Created**: 2025-12-19
**Depends On**: TASK-001

---

## Context

**Problem**:
ACL management requires SSH/AWS CLI access to run the management script. Admins should be able to manage permissions directly from Telegram.

**Goal**:
Implement Telegram bot commands for admins to view and modify ACL configuration.

**Success Criteria**:
- [ ] `/acl` command to view current permissions
- [ ] `/grant` command to add user permissions
- [ ] `/revoke` command to remove user permissions
- [ ] Admin-only access to these commands
- [ ] Confirmation prompts for destructive actions

---

## Implementation Plan

### Phase 1: Read Commands
**Goal**: View ACL configuration

**Tasks**:
- [ ] Implement `/acl` - Show current ACL summary
- [ ] Implement `/acl @user` - Show specific user's permissions
- [ ] Format output for Telegram readability

**Files**:
- `src/handler.py` - Add ACL command handlers

### Phase 2: Write Commands
**Goal**: Modify ACL configuration

**Tasks**:
- [ ] Implement `/grant @user provider:server` - Add permission
- [ ] Implement `/grant @user provider:*` - Add full provider access
- [ ] Implement `/revoke @user provider` - Remove provider access
- [ ] Implement `/revoke @user` - Remove all access
- [ ] Add confirmation prompts

**Files**:
- `src/handler.py` - Add grant/revoke handlers
- `src/acl_manager.py` - ACL modification logic

### Phase 3: SSM Write-Back
**Goal**: Persist changes to SSM

**Tasks**:
- [ ] Implement SSM put_parameter for ACL updates
- [ ] Add optimistic locking (version check)
- [ ] Handle concurrent modification conflicts

**Files**:
- `src/config.py` - Add SSM write capability
- `src/acl_manager.py` - Atomic update logic

### Phase 4: Testing
**Goal**: Ensure commands work correctly

**Tasks**:
- [ ] Unit tests for ACL parsing/formatting
- [ ] Integration tests for grant/revoke flows
- [ ] Test admin-only access enforcement

**Files**:
- `tests/test_handler.py` - Command tests
- `tests/test_acl_manager.py` - ACL logic tests

---

## Command Syntax

```
/acl                          - Show all permissions
/acl @user                    - Show user's permissions

/grant @user provider:*       - Grant full provider access
/grant @user provider:server  - Grant specific server access

/revoke @user provider        - Revoke provider access
/revoke @user                 - Revoke all access (remove from ACL)
```

---

## Technical Decisions

| Decision | Options | Chosen | Reasoning |
|----------|---------|--------|-----------|
| User identification | chat_id, @username | chat_id | Stable, no API lookup needed |
| Confirmation | Inline keyboard, Reply, None | Inline keyboard | Better UX |
| Conflict handling | Last write wins, Reject, Merge | Reject with retry | Prevent data loss |

---

## Security Considerations

- Only admins can use these commands
- Log all ACL modifications
- Require confirmation for revoke operations
- Cannot remove self from admins (prevent lockout)

---

## Notes

- Requires Lambda to have SSM write permissions (currently read-only)
- Consider rate limiting to prevent abuse
- May need inline keyboard for confirmation UI

---

**Last Updated**: 2025-12-19
