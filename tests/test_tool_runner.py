from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest

from pymodeller.tool_runner import ToolRunner


class TestToolRunner:
    """Unit tests for the ToolRunner class, ensuring command execution and fallbacks."""

    # --- Tests for execute method ---

    @patch("subprocess.run")
    def test_execute_success(self, mock_run: MagicMock) -> None:
        """Verify that execute runs correctly when the command succeeds (return code 0)."""
        mock_run.return_value = MagicMock(returncode=0)

        # It should not raise exceptions or trigger sys.exit
        ToolRunner.execute(["ls", "-la"])
        mock_run.assert_called_once_with(["ls", "-la"], check=False)

    @patch("subprocess.run")
    def test_execute_failure(self, mock_run: MagicMock) -> None:
        """Verify that execute calls sys.exit when the command fails (non-zero return code)."""
        mock_run.return_value = MagicMock(returncode=42)

        with pytest.raises(SystemExit) as excinfo:
            ToolRunner.execute(["false"])

        assert excinfo.value.code == 42

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_execute_not_found(self, mock_run: MagicMock) -> None:
        """Verify that execute handles missing executables gracefully."""
        with pytest.raises(SystemExit) as excinfo:
            ToolRunner.execute(["non_existent_command"])

        assert excinfo.value.code == 1

    # --- Tests for run_with_uv method ---

    @patch("shutil.which")
    @patch.object(ToolRunner, "execute")
    def test_run_with_uv_preferred(self, mock_execute: MagicMock, mock_which: MagicMock) -> None:
        """Verify that 'uv run' is prioritized if the uv binary is found."""
        # Mocking shutil.which: return path if 'uv', else None
        mock_which.side_effect: Callable[[str], str | None] = lambda x: "/usr/bin/uv" if x == "uv" else None

        ToolRunner.run_with_uv("ruff", ["check"])

        mock_execute.assert_called_once_with(["uv", "run", "ruff", "check"])

    @patch("shutil.which")
    @patch.object(ToolRunner, "execute")
    def test_run_with_uv_fallback_to_direct(self, mock_execute: MagicMock, mock_which: MagicMock) -> None:
        """Verify fallback to direct execution if 'uv' is missing but the tool exists."""
        # 'uv' is not found, but 'ruff' is
        mock_which.side_effect: Callable[[str], str | None] = lambda x: "/usr/bin/ruff" if x == "ruff" else None

        ToolRunner.run_with_uv("ruff", ["format"])

        mock_execute.assert_called_once_with(["ruff", "format"])

    @patch("shutil.which")
    def test_run_with_uv_total_failure(self, mock_which: MagicMock) -> None:
        """Verify failure when neither 'uv' nor the tool are found in PATH."""
        mock_which.return_value = None  # Nothing exists in PATH

        with pytest.raises(SystemExit) as excinfo:
            ToolRunner.run_with_uv("unknown_tool", [])

        assert excinfo.value.code == 1
