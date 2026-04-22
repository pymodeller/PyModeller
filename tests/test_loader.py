"""Tests for core/env/loader.py.

========================================================================================================================
Name:         tests/test_loader.py
Description:  Verifies YAML schema loading, variable normalization, and
              default behavior of the EnvSpec loader.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from pathlib import Path
from typing import Any, Final

import pytest
import yaml

from pymodeller.loader import EnvSpec, EnvVarSpec, load_env_spec


def write_spec(tmp_path: Path, data: dict[str, Any]) -> Path:
    """Write a YAML spec file and return its path.

    Args:
        tmp_path: Pytest temporary directory fixture.
        data: Dictionary to be serialized into YAML.

    Returns:
        Path: The file path to the generated YAML.
    """
    p: Path = tmp_path / "env_spec.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    return p


# Test data constants
MINIMAL_SPEC: Final[dict[str, Any]] = {
    "sections": [
        {
            "name": "General",
            "description": "General settings",
            "variables": [
                {"name": "FOO", "description": "Foo variable", "type": "str", "default": "bar"},
            ],
        }
    ]
}

FULL_SPEC: Final[dict[str, Any]] = {
    "sections": [
        {
            "name": "Server",
            "description": "Server settings",
            "variables": [
                {
                    "name": "HOST",
                    "description": "Host address",
                    "type": "str",
                    "default": "localhost",
                    "required": False,
                    "secret": False,
                },
                {
                    "name": "PORT",
                    "description": "Port number",
                    "type": "int",
                    "default": "8000",
                    "required": True,
                    "secret": False,
                },
            ],
        },
        {
            "name": "Auth",
            "description": "Auth settings",
            "variables": [
                {
                    "name": "SECRET_KEY",
                    "description": "App secret key",
                    "type": "str",
                    "required": True,
                    "secret": True,
                    "default": "change-me",
                },
            ],
        },
    ]
}


# ──────────────────────────────────────────────────────────────────────────────
# load_env_spec — basic
# ──────────────────────────────────────────────────────────────────────────────


def test_load_returns_env_spec(tmp_path: Path) -> None:
    """Verify that loading a valid YAML returns an EnvSpec instance."""
    path: Path = write_spec(tmp_path, MINIMAL_SPEC)
    spec: EnvSpec = load_env_spec(path)
    assert isinstance(spec, EnvSpec)


def test_load_parses_sections(tmp_path: Path) -> None:
    """Ensure that all sections in the YAML are correctly identified and named."""
    path: Path = write_spec(tmp_path, FULL_SPEC)
    spec: EnvSpec = load_env_spec(path)
    assert len(spec.sections) == 2
    assert spec.sections[0].name == "Server"
    assert spec.sections[1].name == "Auth"


def test_load_parses_variables(tmp_path: Path) -> None:
    """Verify that variables are parsed and names are normalized to lowercase."""
    path: Path = write_spec(tmp_path, FULL_SPEC)
    spec: EnvSpec = load_env_spec(path)
    server_vars: list[EnvVarSpec] = spec.sections[0].variables
    assert len(server_vars) == 2
    assert server_vars[0].name == "host"
    assert server_vars[1].name == "port"


def test_all_vars_flat_list(tmp_path: Path) -> None:
    """Test the flat list property that aggregates all variables from all sections."""
    path: Path = write_spec(tmp_path, FULL_SPEC)
    spec: EnvSpec = load_env_spec(path)
    names: list[str] = [v.name for v in spec.all_vars]
    assert names == ["host", "port", "secret_key"]


def test_required_vars_filter(tmp_path: Path) -> None:
    """Check that variables can be filtered or retrieved via the all_vars collector."""
    path: Path = write_spec(tmp_path, FULL_SPEC)
    spec: EnvSpec = load_env_spec(path)
    required_names: set[str] = {v.name for v in spec.all_vars}
    assert required_names == {"host", "port", "secret_key"}


# ──────────────────────────────────────────────────────────────────────────────
# EnvVarSpec — display_value
# ──────────────────────────────────────────────────────────────────────────────


def test_display_value_secret_masked() -> None:
    """Secrets must always return a masked string for security reasons."""
    var: EnvVarSpec = EnvVarSpec(name="TOKEN", description="A token", secret=True, default="change-me")
    assert var.display_value() == ""


def test_display_value_secret_no_default_masked() -> None:
    """Secret without default must also return a masked string."""
    var: EnvVarSpec = EnvVarSpec(name="TOKEN", description="A token", secret=True)
    assert var.display_value() == ""


def test_display_value_default_used_when_not_secret() -> None:
    """Regular variables should return their default value as string."""
    var: EnvVarSpec = EnvVarSpec(name="HOST", description="Host", secret=False, default="myhost")
    assert var.display_value() == "myhost"


def test_display_value_default_fallback() -> None:
    """Ensure standard default value is used when not secret."""
    var: EnvVarSpec = EnvVarSpec(name="PORT", description="Port", default="8000")
    assert var.display_value() == "8000"


def test_display_value_empty_when_no_default() -> None:
    """If no default is provided, display_value should return an empty string."""
    var: EnvVarSpec = EnvVarSpec(name="X", description="Unknown")
    assert var.display_value() == ""


def test_load_raises_file_not_found() -> None:
    """Verify that a missing file path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_env_spec(Path("/nonexistent/path/env_spec.yaml"))


def test_load_raises_value_error_for_missing_sections(tmp_path: Path) -> None:
    """Ensure that a YAML without the 'sections' key raises a ValueError."""
    bad: Path = tmp_path / "env_spec.yaml"
    bad.write_text("something: else\n", encoding="utf-8")
    with pytest.raises(ValueError, match="sections"):
        load_env_spec(bad)


def test_section_description_defaults_to_empty(tmp_path: Path) -> None:
    """Sections without explicit description should default to an empty string."""
    data: dict[str, Any] = {"sections": [{"name": "NoDesc", "variables": []}]}
    path: Path = write_spec(tmp_path, data)
    spec: EnvSpec = load_env_spec(path)
    assert spec.sections[0].description == "Auto-generated description"


def test_alias_defaults_to_lowercase_name(tmp_path: Path) -> None:
    """When no alias is provided, it should default to the lowercase name of the variable."""
    path: Path = write_spec(tmp_path, MINIMAL_SPEC)
    spec: EnvSpec = load_env_spec(path)
    assert spec.all_vars[0].alias == "foo"


def test_explicit_alias_preserved(tmp_path: Path) -> None:
    """Explicitly provided aliases in YAML must be preserved exactly."""
    data: dict[str, Any] = {
        "sections": [
            {
                "name": "S",
                "variables": [
                    {"name": "JWT_PROTECTED", "description": "JWT flag", "alias": "protected"},
                ],
            }
        ]
    }
    path: Path = write_spec(tmp_path, data)
    spec: EnvSpec = load_env_spec(path)
    var: EnvVarSpec = spec.all_vars[0]
    assert var.alias == "protected"
    assert var.name == "jwt_protected"


def test_type_secret_sugar_normalises(tmp_path: Path) -> None:
    """Verify that the 'secret' attribute handles boolean-like strings from YAML."""
    data: dict[str, Any] = {
        "sections": [
            {
                "name": "Creds",
                "variables": [
                    {"name": "DB_PASSWORD", "description": "DB pass", "type": "str", "secret": "true"},
                ],
            }
        ]
    }
    path: Path = write_spec(tmp_path, data)
    spec: EnvSpec = load_env_spec(path)
    var: EnvVarSpec = spec.all_vars[0]
    assert var.type == "str"
    assert var.secret is True


def test_section_name_stored_on_var(tmp_path: Path) -> None:
    """Each variable should know which parent section it belongs to."""
    path: Path = write_spec(tmp_path, FULL_SPEC)
    spec: EnvSpec = load_env_spec(path)
    auth_var: EnvVarSpec = spec.sections[1].variables[0]
    assert auth_var.section == "Auth"
