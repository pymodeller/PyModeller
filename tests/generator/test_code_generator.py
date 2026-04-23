"""Unit tests for pymodeller.code_generator.

========================================================================================================================
Name:         tests/test_code_generator.py
Description:  Tests for Pydantic model string generation and init file creation.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pymodeller.generators.pydantic_generator import PydanticGenerator
from pymodeller.loader import EnvSection, EnvVarSpec, SectionType

# --- Fixtures ---


@pytest.fixture
def sample_var() -> EnvVarSpec:
    """Basic string variable specification.

    Returns:
        EnvVarSpec: A standard string variable for testing.
    """
    return EnvVarSpec(
        name="host",
        alias="hostName",
        validation_alias="['HOST', 'host_name']",
        type="str",
        default="localhost",
        required=False,
        description="Server host",
    )


@pytest.fixture
def secret_var() -> EnvVarSpec:
    """Secret variable specification.

    Returns:
        EnvVarSpec: A variable marked as secret (Sensitive data).
    """
    return EnvVarSpec(
        name="password",
        alias="dbPassword",
        validation_alias="['DB_PASSWORD']",
        type="str",
        secret=True,
        default="admin",
        required=True,
        description="Database password",
    )


# --- Tests for Helper Functions ---


def test_build_header_files() -> None:
    """Verify that the file header contains the mandatory SHA256 and Pydantic imports."""
    yaml_hash: str = "abc123hash"
    header: list[str] = PydanticGenerator.build_header_files(yaml_hash)
    content: str = "\n".join(header)

    assert "# YAML-SHA256: abc123hash" in content
    assert "from pydantic import AliasChoices, Field, SecretStr" in content
    assert "from pydantic_settings import BaseSettings, SettingsConfigDict" in content


# --- Tests for CodeGenerator Logic ---


def test_section_class_name() -> None:
    """Ensure section names are correctly converted to CamelCase class names."""
    section: EnvSection = EnvSection(name="api service", type=SectionType.SETTINGS)
    assert PydanticGenerator._section_class_name(section) == "ApiServiceSettings"


@pytest.mark.parametrize(
    "type_str, required, default, expected",
    [
        ("int", True, "10", "int"),
        ("int", False, None, "int | None"),
        ("bool", True, "true", "bool"),
        ("str", True, None, "str"),
    ],
)
def test_get_python_type(type_str: str, required: bool, default: str | None, expected: str) -> None:
    """Test the logic that maps YAML types to Python type hints.

    Args:
        type_str: Type defined in YAML.
        required: Whether the field is mandatory.
        default: Default value string.
        expected: Expected Python type hint.
    """
    var: EnvVarSpec = EnvVarSpec(name="test", type=type_str, required=required, default=default, description="")
    assert PydanticGenerator.get_python_type(var) == expected


def test_format_field_secret(secret_var: EnvVarSpec) -> None:
    """Verify that secret fields use the SecretStr type and wrap defaults correctly."""
    line: str = PydanticGenerator.format_field(secret_var)
    assert "password: SecretStr = Field(" in line
    assert 'default=SecretStr("admin")' in line


def test_format_field_required_no_default() -> None:
    """Check formatting for required fields that do not have a default value."""
    var: EnvVarSpec = EnvVarSpec(
        name="port", type="int", required=True, default=None, alias="p", validation_alias="PORT", description=""
    )
    line: str = PydanticGenerator.format_field(var)
    assert "validation_alias=PORT" in "".join(line)


# --- Tests for Complex Generation ---


def test_codegen_section(sample_var: EnvVarSpec) -> None:
    """Test full Pydantic class generation for a specific section."""
    section: EnvSection = EnvSection(
        name="Server", type=SectionType.SETTINGS, env_prefix="SRV_", variables=[sample_var]
    )
    lines: list[str] = PydanticGenerator.codegen_section(section)
    content: str = "\n".join(lines)
    assert "ServerSettings" in content
    assert 'env_prefix="SRV__"' in content
    assert "host: str = Field(" in content


@patch("pymodeller.generators.pydantic_generator.code_gen_conf")
def test_codegen_init(mock_conf: MagicMock, tmp_path: Path) -> None:
    """Verify the creation of the __init__.py file and its internal exports.

    Args:
        mock_conf: Mock for the code generator configuration.
        tmp_path: Pytest fixture for temporary directory management.
    """
    # Setup mock folder using pathlib
    mock_conf.model_folder = tmp_path / "models"
    mock_conf.model_folder.mkdir(parents=True, exist_ok=True)

    init_imports: list[str] = ["from .server import ServerSettings"]
    all_imports: list[str] = ['"ServerSettings"']

    PydanticGenerator.codegen_init(init_imports, all_imports, tmp_path)


def test_codegen_app_settings(tmp_path: Path) -> None:
    """Test the generation of the main AppSettings class that nests other sections."""
    general: EnvSection = EnvSection(
        name="General",
        type=SectionType.SETTINGS,
        variables=[
            EnvVarSpec(
                name="debug",
                type="bool",
                default="true",
                alias="debugMode",
                validation_alias="['DEBUG']",
                description="",
            )
        ],
    )

    nested_sec: EnvSection = EnvSection(name="Database", env_prefix="DB_", attr="db", type=SectionType.SETTINGS)

    lines: list[str] = PydanticGenerator.codegen_app_settings(general, [nested_sec], tmp_path, tmp_path)
    content: str = "\n".join(lines)
    assert "get_database_settings()" in content
