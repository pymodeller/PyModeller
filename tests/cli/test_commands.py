from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from typer.testing import CliRunner

from pymodeller.cli.commands import EnvManager

runner = CliRunner()


class TestCLICommands:
    """Tests for CLI commands in commands.py to achieve full coverage."""

    # --- Tests for EnvManager (Line 70) ---

    @patch("pathlib.Path.read_bytes")
    def test_env_manager_get_file_hash(self, mock_read: MagicMock) -> None:
        """Test SHA-256 computation logic."""
        mock_read.return_value = b"test content"
        result = EnvManager.get_file_hash(Path("dummy.txt"))
        # Verify it returns a valid hex string
        assert len(result) == 64
        assert isinstance(result, str)

    # --- Tests for Check command (Line 151) ---

    @patch("pymodeller.cli.commands.Path.exists")
    def test_check_file_not_found(self, mock_exists: MagicMock) -> None:
        """Verify check command exits when .env file is missing."""
        mock_exists.return_value = False
        # Running via Typer to catch Exit(1)
        import typer

        from pymodeller.cli.commands import check as check_cmd

        app = typer.Typer()
        app.command()(check_cmd)

        result = runner.invoke(app, ["--env", "non_existent.env"])
        assert result.exit_code == 1
        assert "not found" in result.stdout

    # --- Tests for Codegen (Lines 161-164, 188-189, 213) ---

    @patch("pymodeller.cli.commands.PydanticGenerator.generate_files")
    @patch("pymodeller.cli.commands.PeeweeCodeGenerator.generate_files")
    @patch("pymodeller.cli.commands.load_env_spec")
    @patch("pymodeller.cli.commands.EnvManager.get_file_hash")
    def test_codegen_no_models_declared(
        self, mock_hash: MagicMock, mock_load: MagicMock, mock_peewee: MagicMock, mock_pydantic: MagicMock
    ) -> None:
        """Coverage for branches where no models are generated (p_path is None)."""
        mock_pydantic.return_value = (None, None)
        mock_peewee.return_value = (None, None)

        import typer

        from pymodeller.cli.commands import codegen as codegen_cmd

        app = typer.Typer()
        app.command()(codegen_cmd)

        result = runner.invoke(app)
        assert result.exit_code == 0
        assert "No declared pydantic models" in result.stdout
        assert "No declared peewee models" in result.stdout

    # --- Tests for Drift (Lines 239-263) ---

    @patch("pymodeller.cli.commands.Path.exists")
    @patch("pymodeller.cli.commands.EnvManager.get_file_hash")
    def test_drift_file_missing(self, mock_hash: MagicMock, mock_exists: MagicMock) -> None:
        """Verify drift fails if data model doesn't exist."""
        mock_exists.return_value = False
        import typer

        from pymodeller.cli.commands import drift as drift_cmd

        app = typer.Typer()
        app.command()(drift_cmd)

        result = runner.invoke(app)
        assert result.exit_code == 1
        assert "Data model file missing" in result.stdout

    @patch("pymodeller.cli.commands.Path.exists")
    @patch("pymodeller.cli.commands.Path.open", new_callable=mock_open, read_data="# YAML_HASH: old_hash\n")
    @patch("pymodeller.cli.commands.EnvManager.get_file_hash")
    def test_drift_detected(self, mock_hash: MagicMock, mock_file: MagicMock, mock_exists: MagicMock) -> None:
        """Verify drift exit when hashes don't match."""
        mock_exists.return_value = True
        mock_hash.return_value = "new_hash"  # Current is different from 'old_hash' in file

        import typer

        from pymodeller.cli.commands import drift as drift_cmd

        app = typer.Typer()
        app.command()(drift_cmd)

        result = runner.invoke(app)
        assert result.exit_code == 1
        assert "Drift detected" in result.stdout

    # --- Tests for Sync & Diff printing (Lines 268-307) ---

    @patch("pymodeller.cli.commands.compare_dirs")
    @patch("pymodeller.cli.commands.codegen")
    @patch("tempfile.TemporaryDirectory")
    def test_sync_logic_and_diff_printing(
        self, mock_temp: MagicMock, mock_codegen: MagicMock, mock_compare: MagicMock
    ) -> None:
        """Coverage for sync process and the print_diff/show_master_diff functions."""
        # Setup mock for directory comparison with differences
        mock_compare.return_value = {
            "equal": False,
            "added": ["new_file.py"],
            "removed": ["old_file.py"],
            "modified": ["changed.py"],
        }

        # Setup mock for temp directory path
        mock_temp.return_value.__enter__.return_value = Path("/tmp/dummy")  # noqa: S108

        import typer

        from pymodeller.cli.commands import sync as sync_cmd

        app = typer.Typer()
        app.command()(sync_cmd)

        result = runner.invoke(app)
        # It should exit 1 due to the explicit raise at end of sync
        assert result.exit_code == 1

    @patch("pymodeller.cli.commands.compare_dirs")
    def test_print_diff_in_sync(self, mock_compare: MagicMock) -> None:
        """Test the 'equal' branch in print_diff."""
        from pymodeller.cli.commands import print_diff

        diff_data = {"equal": True}

        with patch("typer.echo") as mock_echo:
            print_diff("Test", diff_data)
            mock_echo.assert_any_call("   ✅ In sync")
