from unittest.mock import MagicMock, patch

from pymodeller.cli.dev_tools import main_check, main_ci, main_test


@patch("pymodeller.cli.dev_tools.ToolRunner.run_with_uv")
class TestDevTools:
    """Unit tests for the dev_tools orchestrator."""

    def test_main_check_calls_tools(self, mock_run: MagicMock) -> None:
        """Verify that main_check triggers Ruff (format/check) and Pyrefly."""
        main_check()

        # Should result in 3 calls: 2 for ruff and 1 for pyrefly
        assert mock_run.call_count == 3

        # Extract arguments from call history
        calls = [call.args for call in mock_run.call_args_list]

        # Validate specific tool arguments
        assert ("ruff", ["format", "--config=pyproject.toml", "--exclude", r"\.venv"]) in calls
        assert ("ruff", ["check", "--fix", "--config=pyproject.toml", "--exclude", r"\.venv"]) in calls
        assert ("pyrefly", ["check", "src"]) in calls

    def test_main_test_calls_pytest(self, mock_run: MagicMock) -> None:
        """Verify that main_test executes pytest with the --check flag."""
        main_test()

        mock_run.assert_called_once_with("pytest", ["--check"])

    def test_main_ci_orchestration(self, mock_run: MagicMock) -> None:
        """Verify that the CI pipeline orchestrates both checks and tests."""
        with (
            patch("pymodeller.cli.dev_tools.main_check") as mock_check,
            patch("pymodeller.cli.dev_tools.main_test") as mock_test,
        ):
            main_ci()

            mock_check.assert_called_once()
            mock_test.assert_called_once()

    def test_main_check_logging(self, mock_run: MagicMock) -> None:
        """Verify that logging signals the completion of static checks."""
        with patch("pymodeller.cli.dev_tools.logger") as mock_logger:
            # We type mock_logger implicitly here or could cast it: mock_logger: MagicMock
            main_check()
            assert mock_logger.info.called
            # Verify the final success message is logged
            mock_logger.info.assert_any_call("Static checks completed successfully ✅")
