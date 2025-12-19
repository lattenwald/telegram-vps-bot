# ACL Management Script Design

**Created**: 2025-12-19
**Status**: Approved

---

## Overview

A standalone script for managing ACL (Access Control List) configuration stored in AWS SSM Parameter Store. The script converts between human-readable YAML and JSON stored in SSM.

## Interface

```bash
uv run scripts/manage_acl.py get                  # fetch and print as YAML
uv run scripts/manage_acl.py set acl.yaml         # validate and upload
uv run scripts/manage_acl.py set -                # read from stdin
uv run scripts/manage_acl.py validate acl.yaml   # check without uploading
```

**Exit codes**: 0 = success, 1 = error

## Dependencies

Uses PEP 723 inline script metadata for self-contained execution:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0", "boto3", "pydantic>=2.0"]
# ///
```

No installation required - `uv run` handles dependencies automatically.

## ACL Schema

```yaml
admins:
  - 123456789        # Full access to all providers/servers
  - 987654321

users:
  "111222333":
    bitlaunch:
      servers: ["prod-web", "prod-db"]  # only these servers
    kamatera: {}                         # all servers (empty = all)
  "444555666":
    kamatera:
      servers: []                        # explicit deny (empty list)
```

**Server access rules**:
- `servers` omitted or `null` → all servers allowed
- `servers: []` → access denied
- `servers: ["a", "b"]` → only listed servers

## Validation

Pydantic models enforce:

1. **admins** - list of positive integers
2. **users** - dict with numeric string keys
3. **providers** - must exist in `src/providers/*.py` (auto-detected)
4. **servers** - list of non-empty strings, or null
5. **no empty users** - each user must have at least one provider

```python
class ProviderConfig(BaseModel):
    servers: list[str] | None = None

class ACL(BaseModel):
    admins: list[int] = []
    users: dict[str, dict[str, ProviderConfig | None]] = {}
```

## Configuration

Hardcoded SSM path (matches project convention):

```python
SSM_ACL_PATH = "/telegram-vps-bot/acl-config"
```

## Command Behavior

### `get`
- Fetches JSON from SSM
- Converts to YAML and prints to stdout
- Exits with error if parameter doesn't exist

### `validate`
- Reads YAML from file or stdin (`-`)
- Validates against Pydantic model
- Prints success or detailed errors
- Does not upload

### `set`
- Reads YAML from file or stdin (`-`)
- Always validates before uploading (no `--force` option)
- Uploads JSON to SSM on success
- Exits with error if validation fails

## Provider Auto-Detection

Allowed providers are detected from filesystem:

```python
def get_allowed_providers() -> set[str]:
    providers_dir = Path(__file__).parent.parent / "src" / "providers"
    return {
        f.stem for f in providers_dir.glob("*.py")
        if f.stem not in ("__init__", "base")
    }
```

This ensures validation stays in sync with implemented providers.

## Error Messages

```
❌ Error: ACL not found at /telegram-vps-bot/acl-config
❌ Validation failed:
  1 validation error for ACL
  users.123.bitlaunch
    Unknown provider 'digitalocean' [type=value_error]
✅ ACL is valid
✅ ACL uploaded to /telegram-vps-bot/acl-config
```

## File Location

```
scripts/manage_acl.py
```
