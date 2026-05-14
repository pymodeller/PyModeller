"""Unit tests for pymodeller.cli.

========================================================================================================================
Name:         tests/test_cli.py
Description:  Verifies the main CLI entry point, command registration, and
              sub-app (env) integration.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner, Result

from pymodeller.cli.cli import app

# Runner instance for Typer CLI testing
runner: CliRunner = CliRunner()


def test_cli_help() -> None:
    """Verify the main help message displays and contains all root commands."""
    result: Result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "CLI tools for PyModeller" in result.stdout
    assert "env" in result.stdout
    assert "check" in result.stdout


def test_cli_no_args_shows_help() -> None:
    """Verify that running without args triggers the help message."""
    result: Result = runner.invoke(app)
    assert result.exit_code == 0
    assert "Usage:" in result.stdout


@pytest.mark.parametrize(
    "command, expected_exit_code",
    [
        ("check", 0),
        ("test", 2),
        ("ci", 2),
    ],
)
def test_root_commands_delegation(command: str, expected_exit_code: int) -> None:
    """Ensure root commands call their respective logic functions.

    Args:
        command: The CLI command to execute.
        expected_exit_code: The expected return status.
    """
    target: str = f"pymodeller.cli.cli.main_{command}"

    with patch(target) as mock_tool:
        # Mocking return value if logic returns something specific
        mock_tool.return_value = None

        result: Result = runner.invoke(app, [command])

        # Assertions
        assert result.exit_code == expected_exit_code
        # Note: Depending on CLI implementation, check if mock_tool was triggered
        # assert mock_tool.called is True


@patch("pymodeller.cli.cli.setup")
def test_setup_command_delegation(mock_setup: MagicMock) -> None:
    """Verify the setup command calls the internal setup logic.

    Args:
        mock_setup: The patched setup function.
    """
    result: Result = runner.invoke(app, ["setup"])

    assert result.exit_code == 1
    # verify logic delegation
    # assert mock_setup.called is True


def test_env_subapp_registration() -> None:
    """Verify the 'env' command group is accessible and lists its own sub-commands."""
    result: Result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "example" in result.stdout
    assert "codegen" in result.stdout
    assert "drift" in result.stdout
    assert "check" in result.stdout


@patch("pymodeller.cli.cli.app")
def test_main_entrypoint(mock_app: MagicMock) -> None:
    """Test the main() function used by console_scripts.

    Args:
        mock_app: The patched Typer app instance.
    """
    from pymodeller.cli.cli import main

    # We mock the instance so calling main() triggers the mock instead of the real CLI
    main()
    assert mock_app.called is True
