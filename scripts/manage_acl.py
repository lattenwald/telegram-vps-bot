#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0", "boto3", "pydantic>=2.0"]
# ///
"""
ACL Management Script for Telegram VPS Bot.

Manages ACL (Access Control List) configuration stored in AWS SSM Parameter Store.
Converts between human-readable YAML and JSON stored in SSM.

Usage:
    uv run scripts/manage_acl.py get                  # fetch and print as YAML
    uv run scripts/manage_acl.py set acl.yaml         # validate and upload
    uv run scripts/manage_acl.py set -                # read from stdin
    uv run scripts/manage_acl.py validate acl.yaml   # check without uploading
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import boto3
import yaml
from botocore.exceptions import ClientError
from pydantic import BaseModel, field_validator, model_validator

SSM_ACL_PATH = "/telegram-vps-bot/acl-config"


def get_allowed_providers() -> set[str]:
    """Auto-detect allowed providers from src/providers/*.py files."""
    providers_dir = Path(__file__).parent.parent / "src" / "providers"
    return {
        f.stem for f in providers_dir.glob("*.py") if f.stem not in ("__init__", "base")
    }


class ProviderConfig(BaseModel):
    """Configuration for a single provider's server access."""

    servers: list[str] | None = None

    @field_validator("servers", mode="before")
    @classmethod
    def empty_dict_to_none(cls, v: object) -> list[str] | None:
        """Convert empty dict {} to None (means all servers allowed)."""
        if isinstance(v, dict) and len(v) == 0:
            return None
        return v  # type: ignore[return-value]

    @field_validator("servers", mode="after")
    @classmethod
    def validate_servers(cls, v: list[str] | None) -> list[str] | None:
        """Validate server names are non-empty strings."""
        if v is not None:
            for server in v:
                if not server or not server.strip():
                    raise ValueError("Server names must be non-empty strings")
        return v


class ACL(BaseModel):
    """Access Control List configuration."""

    admins: list[int] = []
    users: dict[str, dict[str, ProviderConfig | None]] = {}

    @field_validator("admins", mode="after")
    @classmethod
    def validate_admins(cls, v: list[int]) -> list[int]:
        """Validate admin chat IDs are positive integers."""
        for admin_id in v:
            if admin_id <= 0:
                raise ValueError(f"Admin ID must be positive integer, got {admin_id}")
        return v

    @model_validator(mode="after")
    def validate_users(self) -> ACL:
        """Validate user entries have valid structure."""
        allowed_providers = get_allowed_providers()

        for user_id, providers in self.users.items():
            # Validate user ID is numeric string
            if not user_id.isdigit():
                raise ValueError(f"User ID must be numeric string, got '{user_id}'")

            # Validate user has at least one provider
            if not providers:
                raise ValueError(f"User '{user_id}' must have at least one provider")

            # Validate providers exist
            for provider_name, config in providers.items():
                if provider_name not in allowed_providers:
                    raise ValueError(
                        f"Unknown provider '{provider_name}' for user '{user_id}'. "
                        f"Allowed: {sorted(allowed_providers)}"
                    )

                # Convert None config to ProviderConfig with all servers allowed
                if config is None:
                    providers[provider_name] = ProviderConfig()

        return self


def get_ssm_client() -> boto3.client:
    """Create SSM client."""
    return boto3.client("ssm")


def cmd_get() -> int:
    """Fetch ACL from SSM and print as YAML."""
    ssm = get_ssm_client()

    try:
        response = ssm.get_parameter(Name=SSM_ACL_PATH, WithDecryption=True)
        json_value = response["Parameter"]["Value"]
        acl_dict = json.loads(json_value)
        yaml_output = yaml.dump(acl_dict, default_flow_style=False, sort_keys=False)
        print(yaml_output)
        return 0
    except ClientError as e:
        if e.response["Error"]["Code"] == "ParameterNotFound":
            print(f"❌ Error: ACL not found at {SSM_ACL_PATH}", file=sys.stderr)
        else:
            print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in SSM parameter: {e}", file=sys.stderr)
        return 1


def load_yaml(source: str) -> tuple[dict | None, str | None]:
    """Load YAML from file or stdin. Returns (data, error)."""
    try:
        if source == "-":
            content = sys.stdin.read()
        else:
            path = Path(source)
            if not path.exists():
                return None, f"File not found: {source}"
            content = path.read_text()

        data = yaml.safe_load(content)
        if data is None:
            return None, "Empty YAML content"
        return data, None
    except yaml.YAMLError as e:
        return None, f"Invalid YAML: {e}"


def validate_acl(data: dict) -> tuple[ACL | None, str | None]:
    """Validate ACL data against Pydantic model. Returns (acl, error)."""
    try:
        acl = ACL.model_validate(data)
        return acl, None
    except Exception as e:
        return None, str(e)


def cmd_validate(source: str) -> int:
    """Validate ACL YAML without uploading."""
    data, error = load_yaml(source)
    if error:
        print(f"❌ {error}", file=sys.stderr)
        return 1

    acl, error = validate_acl(data)
    if error:
        print(f"❌ Validation failed:\n  {error}", file=sys.stderr)
        return 1

    print("✅ ACL is valid")
    return 0


def cmd_set(source: str) -> int:
    """Validate and upload ACL to SSM."""
    data, error = load_yaml(source)
    if error:
        print(f"❌ {error}", file=sys.stderr)
        return 1

    acl, error = validate_acl(data)
    if error:
        print(f"❌ Validation failed:\n  {error}", file=sys.stderr)
        return 1

    # Convert to JSON for storage
    json_value = json.dumps(acl.model_dump(mode="json"), separators=(",", ":"))

    ssm = get_ssm_client()
    try:
        ssm.put_parameter(
            Name=SSM_ACL_PATH,
            Value=json_value,
            Type="SecureString",
            Overwrite=True,
        )
        print(f"✅ ACL uploaded to {SSM_ACL_PATH}")
        return 0
    except ClientError as e:
        print(f"❌ Error uploading to SSM: {e}", file=sys.stderr)
        return 1


def print_usage() -> None:
    """Print usage information."""
    print(__doc__.strip())


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print_usage()
        return 1

    command = sys.argv[1]

    if command == "get":
        if len(sys.argv) != 2:
            print("Usage: manage_acl.py get", file=sys.stderr)
            return 1
        return cmd_get()

    elif command == "validate":
        if len(sys.argv) != 3:
            print("Usage: manage_acl.py validate <file.yaml>", file=sys.stderr)
            return 1
        return cmd_validate(sys.argv[2])

    elif command == "set":
        if len(sys.argv) != 3:
            print("Usage: manage_acl.py set <file.yaml | ->", file=sys.stderr)
            return 1
        return cmd_set(sys.argv[2])

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print_usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())
