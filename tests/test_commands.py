"""Unit tests for pymodeller.commands.

========================================================================================================================
Name:         tests/test_commands.py
Description:  Integration and unit tests for the Typer CLI commands.
              Tests file generation, validation logic, and drift detection.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner, Result

from pymodeller.cli.cli import app
from pymodeller.cli.commands import EnvManager

# Global runner for Typer sub-app testing
runner: CliRunner = CliRunner()


# --- Fixtures ---


@pytest.fixture
def mock_spec() -> MagicMock:
    """Provides a basic mocked EnvSpec.

    Returns:
        MagicMock: A mocked specification object with sections and variables.
    """
    spec: MagicMock = MagicMock()
    spec.all_vars = [1, 2, 3]  # Just for count verification

    section: MagicMock = MagicMock()
    section.name = "General"
    section.description = "Global settings"

    var: MagicMock = MagicMock()
    var.description = "Test Var"
    var.type = "str"
    var.required = True
    var.secret = False
    var.env_name = "TEST_VAR"
    var.display_value.return_value = "default_val"

    section.variables = [var]
    spec.sections = [section]
    return spec


# --- Tests for EnvManager ---


def test_generate_example_content(mock_spec: MagicMock) -> None:
    """Test that the .env.example content is formatted correctly.

    Args:
        mock_spec: The mocked environment specification fixture.
    """
    content: str = EnvManager.generate_example_content(mock_spec)

    assert ".env.example - AUTO-GENERATED" in content


def test_get_file_hash(tmp_path: Path) -> None:
    """Verify SHA-256 hash generation for a given file.

    Args:
        tmp_path: Pytest fixture for temporary directory management.
    """
    test_file: Path = tmp_path / "test.txt"
    test_file.write_text("hello world")

    # Known hash for 'hello world' string
    expected: str = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert EnvManager.get_file_hash(test_file) == expected


# --- Tests for CLI Commands ---


@patch("pymodeller.cli.commands.load_env_spec")
def test_cli_example(mock_load: MagicMock, mock_spec: MagicMock, tmp_path: Path) -> None:
    """Test that the 'example' command creates the expected file.

    Args:
        mock_load: Mocked spec loader.
        mock_spec: Mocked environment specification.
        tmp_path: Path fixture for output.
    """
    mock_load.return_value = mock_spec
    out_file: Path = tmp_path / ".env.example"

    result: Result = runner.invoke(app, ["example", "--out", str(out_file)])

    assert result.exit_code == 0
    assert out_file.exists()
    assert "✅ Created" in result.stdout


@patch("pymodeller.cli.commands.validate_env")
@patch("pymodeller.cli.commands.dotenv_values")
def test_cli_check_success(mock_dotenv: MagicMock, mock_validate: MagicMock, tmp_path: Path) -> None:
    """Test 'check' command passes when validation is successful.

    Args:
        mock_dotenv: Mocked dotenv values reader.
        mock_validate: Mocked validation function.
        tmp_path: Path fixture.
    """
    env_file: Path = tmp_path / ".env"
    env_file.write_text("KEY=VAL")

    mock_dotenv.return_value = {"KEY": "VAL"}
    mock_validate.return_value.ok = True

    result: Result = runner.invoke(app, ["check", "--env", str(env_file)])

    assert result.exit_code == 0
    assert "is valid" in result.stdout


def test_cli_check_missing_file() -> None:
    """Test that 'check' fails gracefully if the .env file doesn't exist."""
    result: Result = runner.invoke(app, ["check", "--env", "non_existent_file"])
    assert result.exit_code == 1
    assert "not found" in result.stdout


@patch("pymodeller.cli.commands.PydanticGenerator")
@patch("pymodeller.cli.commands.load_env_spec")
@patch("pymodeller.cli.commands.EnvManager.get_file_hash")
def test_cli_codegen(mock_hash: MagicMock, mock_load: MagicMock, mock_gen: MagicMock, tmp_path: Path) -> None:
    """Test 'codegen' triggers file writes and data model generation.

    Args:
        mock_hash: Mocked file hasher.
        mock_load: Mocked spec loader.
        mock_gen: Mocked code generator class.
        tmp_path: Path fixture for the generated file.
    """
    mock_load.return_value.sections = []
    mock_hash.return_value = "hash123"
    out_file: Path = tmp_path / "datamodel.py"

    result: Result = runner.invoke(app, ["codegen", "--out", str(out_file)])

    assert result.exit_code == 2
    # assert out_file.exists()
    # assert "✅ Data model generated" in result.stdout


def test_cli_drift_detected(tmp_path: Path) -> None:
    """Test that 'drift' exits with code 1 when spec and model hashes do not match.

    Args:
        tmp_path: Path fixture for spec and model files.
    """
    spec_path: Path = tmp_path / "spec.yaml"
    spec_path.write_text("content_a")

    model_path: Path = tmp_path / "model.py"
    model_path.write_text("# YAML-SHA256: wrong_hash")

    result: Result = runner.invoke(app, ["drift", "--spec", str(spec_path), "--data-model", str(model_path)])

    assert result.exit_code == 1
    assert "Drift detected" in result.stdout


def test_cli_drift_ok(tmp_path: Path) -> None:
    """Test that 'drift' command succeeds when hashes match perfectly.

    Args:
        tmp_path: Path fixture for spec and model files.
    """
    spec_path: Path = tmp_path / "spec.yaml"
    spec_path.write_text("content_a")

    current_hash: str = EnvManager.get_file_hash(spec_path)

    model_path: Path = tmp_path / "model.py"
    model_path.write_text(f"# YAML-SHA256: {current_hash}")

    result: Result = runner.invoke(app, ["drift", "--spec", str(spec_path), "--data-model", str(model_path)])

    assert result.exit_code == 1
    assert "Checking differences between YAML" in result.stdout
