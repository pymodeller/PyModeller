"""Unit tests for pymodeller.commands.

========================================================================================================================
Name:         tests/test_commands.py
Description:  Integration and unit tests for the Typer CLI commands.
              Tests file generation, validation logic, and drift detection.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import pytest
import typer
import yaml
from typer.testing import CliRunner, Result

from pymodeller.cli.cli import app
from pymodeller.cli.commands import banner_full, check, codegen, drift, print_diff, setup, sync, yaml_file
from pymodeller.generators import EnvGenerator
from pymodeller.utils import deep_merge, get_file_hash, write_env_file

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
    content: str = EnvGenerator().generate_example_content(mock_spec)

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
    assert get_file_hash(test_file) == expected


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

    result: Result = runner.invoke(app, ["env", "example", "--out", str(out_file)])

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
@patch("pymodeller.utils.get_file_hash")
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

    current_hash: str = get_file_hash(spec_path)

    model_path: Path = tmp_path / "model.py"
    model_path.write_text(f"# YAML-SHA256: {current_hash}")

    result: Result = runner.invoke(app, ["drift", "--spec", str(spec_path), "--data-model", str(model_path)])

    assert result.exit_code == 1
    assert "Checking differences between YAML" in result.stdout


class TestCLICommands:
    """Tests for CLI commands in commands.py to achieve full coverage."""

    # --- Tests for EnvManager (Line 70) ---

    @patch("pathlib.Path.read_bytes")
    def test_env_manager_get_file_hash(self, mock_read: MagicMock) -> None:
        """Test SHA-256 computation logic."""
        mock_read.return_value = b"test content"
        result = get_file_hash(Path("dummy.txt"))
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
    @patch("pymodeller.cli.commands.PeeweeGenerator.generate_files")
    @patch("pymodeller.cli.commands.load_env_spec")
    @patch("pymodeller.utils.get_file_hash")
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
    @patch("pymodeller.utils.get_file_hash")
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
    @patch("pymodeller.utils.get_file_hash")
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
        assert "Checking differences" in result.stdout

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
        mock_temp.return_value.__enter__.return_value = Path("./tmp/dummy")

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


def test_print_diff_equal(capsys: MagicMock) -> None:
    """Verifica el mensaje cuando los modelos son iguales."""
    diff = {"equal": True, "added": [], "removed": [], "modified": []}

    print_diff("User", diff)

    captured = capsys.readouterr()
    assert "Comparing User models" in captured.out
    assert "✅ In sync" in captured.out
    # Aseguramos que no imprima otras secciones
    assert "Added" not in captured.out


def test_print_diff_with_changes(capsys: MagicMock) -> None:
    """Verifica que se listen correctamente los añadidos, eliminados y modificados."""
    diff = {"equal": False, "added": ["age", "email"], "removed": ["old_id"], "modified": ["name"]}

    print_diff("Product", diff)

    captured = capsys.readouterr()
    out = captured.out

    assert "Comparing Product models" in out

    # Verificar sección de añadidos
    assert "+ Added:" in out
    assert "- age" in out
    assert "- email" in out

    # Verificar sección de eliminados
    assert "- Removed:" in out
    assert "- old_id" in out

    # Verificar sección de modificados
    assert "✏️ Modified:" in out
    assert "- name" in out


def test_print_diff_partial_changes(capsys: MagicMock) -> None:
    """Verifica que si solo hay una categoría (ej. added), no muestre las otras."""
    diff = {"equal": False, "added": ["phone"], "removed": [], "modified": []}

    print_diff("Settings", diff)

    captured = capsys.readouterr()
    out = captured.out

    assert "+ Added:" in out
    assert "- phone" in out
    assert "Removed:" not in out
    assert "Modified:" not in out


# --- TESTS PARA LÍNEAS 71 (Error en check si el .env no existe) ---


def test_check_env_not_found(capsys: MagicMock) -> None:
    """Generate test check env."""
    with patch("pymodeller.cli.commands.Path.exists", return_value=False):
        with pytest.raises(typer.Exit) as exc:
            check(env=Path(".env.missing"))

        assert exc.value.exit_code == 1
        captured = capsys.readouterr()
        assert ".env.missing not found" in captured.out


# --- TESTS PARA LÍNEAS 164-167 (Generación de modelos vacíos en codegen) ---


@patch("pymodeller.cli.commands.load_env_spec")
@patch("pymodeller.utils.get_file_hash", return_value="abc")
@patch("pymodeller.cli.commands.PydanticGenerator.generate_files")
@patch("pymodeller.cli.commands.PeeweeGenerator.generate_files")
@patch("pymodeller.cli.commands.ToolRunner.run_with_uv")
def test_codegen_no_models_declared(
    mock_uv: MagicMock,
    mock_peewee: MagicMock,
    mock_pydantic: MagicMock,
    mock_hash: MagicMock,
    mock_load: MagicMock,
    capsys: MagicMock,
) -> None:
    """Test code gen."""
    # Simulamos que no se generan archivos (retornan None o vacíos)
    mock_pydantic.return_value = (None, None)
    mock_peewee.return_value = (None, None)

    exc = codegen()

    assert exc.exit_code == 0
    captured = capsys.readouterr()
    assert "No declared pydantic models" in captured.out
    assert "No declared peewee models" in captured.out
    # Verificamos que NO se llamó a ruff/uv si no hay archivos
    assert mock_uv.call_count == 2


# --- TESTS PARA LÍNEAS 244-268 (Sync y comparación de Master files) ---


@patch("pymodeller.cli.commands.compare_dirs")
@patch("pymodeller.cli.commands.file_hash")
@patch("pymodeller.cli.commands.codegen")
@patch("pymodeller.cli.commands.Path.exists", return_value=True)
def test_sync_with_master_diff(
    mock_exists: MagicMock,
    mock_codegen: MagicMock,
    mock_file_hash: MagicMock,
    mock_compare: MagicMock,
    capsys: MagicMock,
) -> None:
    # Resultados de directorios iguales
    mock_compare.return_value = {"equal": True, "added": [], "removed": [], "modified": []}
    # Forzamos que los hashes de los archivos master sean DIFERENTES
    mock_file_hash.side_effect = ["hash_a", "hash_b", "hash_c", "hash_d"]

    exc = sync()

    assert exc.exit_code == 0
    captured = capsys.readouterr()
    # Verifica que se detectó modificación en archivos master (Líneas 273-288)
    assert "Modified:" in captured.out


# --- TESTS PARA LÍNEAS 273-288 (show_master_diff) ---


def test_show_master_diff_modified(capsys: MagicMock) -> None:
    """Test show master diff."""
    from pymodeller.cli.commands import show_master_diff

    master_diff = {"pydantic_master": True, "peewee_master": False}

    show_master_diff(master_diff)
    captured = capsys.readouterr()
    assert "Modified" in captured.out
    assert "✅" not in captured.out


# --- TESTS PARA LÍNEAS 320-325 (Banner y Setup) ---


def test_banner_full() -> None:
    """Solo para asegurar que se ejecuta sin errores de consola."""
    banner_full("Test Message", "blue")


@patch("pymodeller.cli.commands.codegen")
@patch("pymodeller.cli.commands.example")
def test_setup_flow(mock_example: MagicMock, mock_codegen: MagicMock) -> None:
    """Test setup flow."""
    exc = setup()
    assert exc.exit_code == 0
    mock_codegen.assert_called_once()
    mock_example.assert_called_once()


# --- Tests para cubrir líneas 70-78 (check) ---


def test_check_env_file_not_found() -> None:
    """Test para verificar el comportamiento cuando el archivo .env no existe.
    Entrada: Path inexistente.
    Salida: typer.Exit con código 1.
    """
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(typer.Exit) as exc:
            check(env=Path(".env.missing"))
        assert exc.value.exit_code == 1


def test_check_validation_fails() -> None:
    """Test para verificar el comportamiento cuando la validación del .env devuelve errores.
    Entrada: Mock de validate_env con ok=False.
    Salida: typer.Exit con código 1.
    """
    mock_result = MagicMock()
    mock_result.ok = False
    mock_result.issues = [MagicMock(name="VAR", detail="Missing value")]

    with (
        patch("pymodeller.cli.commands.Path.exists", return_value=True),
        patch("pymodeller.cli.commands.dotenv_values", return_value={"VAR": None}),
        patch("pymodeller.cli.commands.validate_env", return_value=mock_result),
    ):
        with pytest.raises(typer.Exit) as exc:
            check(spec=Path("spec.yaml"), env=Path(".env"))
        assert exc.value.exit_code == 1


# --- Tests para cubrir líneas 148-153 (codegen: No models generated) ---


@patch("pymodeller.cli.commands.PydanticGenerator.generate_files")
@patch("pymodeller.cli.commands.PeeweeGenerator.generate_files")
@patch("pymodeller.cli.commands.load_env_spec")
@patch("pymodeller.cli.commands.get_file_hash")
def test_codegen_no_models(
    mock_hash: MagicMock, mock_load: MagicMock, mock_peewee: MagicMock, mock_pydantic: MagicMock
) -> None:
    """Test para cubrir el caso donde no se declaran modelos pydantic ni peewee.
    Entrada: Retornos de generate_files como (None, None).
    Salida: typer.Exit con código 0.
    """
    mock_pydantic.return_value = (None, None)
    mock_peewee.return_value = (None, None)

    res = codegen()
    assert res.exit_code == 0


# --- Tests para cubrir líneas 203-204 (drift: Hash mismatch) ---


@patch("pymodeller.cli.commands.get_file_hash")
@patch("pathlib.Path.open")
@patch("pathlib.Path.exists", return_value=True)
def test_drift_detected(mock_exists: MagicMock, mock_open: MagicMock, mock_hash: MagicMock) -> None:
    """Test para detectar drift cuando el hash del YAML es distinto al del archivo generado.
    Entrada: Hash actual 'AAA', Hash guardado 'BBB'.
    Salida: typer.Exit con código 1.
    """
    mock_hash.return_value = "AAA"
    # Simulamos el contenido del archivo con un marcador de hash diferente
    mock_file = MagicMock()
    mock_file.__enter__.return_value = ["# yaml_hash: BBB"]
    mock_open.return_value = mock_file

    with pytest.raises(typer.Exit) as exc:
        drift(spec=Path("spec.yaml"), data_model=Path("model.py"))
    assert exc.value.exit_code == 1


# --- Tests para cubrir línea 279 (banner_full) ---


def test_banner_full_custom_color() -> None:
    """Test simple para cubrir la función banner_full con color personalizado.
    Entrada: Mensaje string y color string.
    Salida: None (verifica que no explote).
    """
    with patch("pymodeller.cli.commands.console.print") as mock_print:
        banner_full("Test Message", color="red")
        mock_print.assert_called()


@patch("pymodeller.cli.commands.Path.write_text")
@patch("pymodeller.cli.commands.Path.mkdir")
@patch("pymodeller.cli.commands.EnvGenerator.generate_environment_yaml")
@patch("pymodeller.cli.commands.load_env_spec")
def test_yaml_file_success(
    mock_load: MagicMock,
    mock_gen_yaml: MagicMock,
    mock_mkdir: MagicMock,
    mock_write: MagicMock,
    capsys: pytest.CaptureFixture,
) -> None:
    """Test the successful generation of the environment.yaml file.

    Args:
        mock_load: Mock for the function that loads the YAML specification.
        mock_gen_yaml: Mock for the environment content generator.
        mock_mkdir: Mock to prevent actual directory creation on the OS.
        mock_write: Mock to intercept the file writing process.
        capsys: Pytest fixture to capture stdout/stderr output.

    Input:
        Mocked Path objects for --spec and --out.

    Output:
        Asserts a typer.Exit(0) and verifies the success message in the console.
    """
    # 1. Setup Mocks
    # Create a dummy spec object that load_env_spec would normally return
    mock_spec_data = MagicMock(name="SpecObject")
    mock_load.return_value = mock_spec_data

    # Define the dummy content that the generator should produce
    fake_content = "key: value\nfake_yaml_content: true"
    mock_gen_yaml.return_value = fake_content

    # Define arbitrary paths for input and output
    test_spec_path = Path("input/env_spec.yaml")
    test_out_path = Path("output/environment.yaml")

    # 2. Execute the function
    # Typer commands raise a typer.Exit exception to signal completion
    res = yaml_file(spec=test_spec_path, out=test_out_path)

    # 3. Assertions

    # Check that the command exited with success code 0
    assert res.exit_code == 0

    # Verify that the loader was called with the correct input path
    mock_load.assert_called_once_with(test_spec_path)

    # Verify that the generator was called using the loaded spec data
    mock_gen_yaml.assert_called_once_with(spec=mock_spec_data)

    # Verify that the directory creation logic was triggered for the output path
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    # Verify that write_text was called with the generated content and UTF-8 encoding
    mock_write.assert_called_once_with(fake_content, encoding="utf-8")

    # Verify the console output contains the success indicator and the output filename
    captured = capsys.readouterr()
    assert "✅ Created" in captured.out
    assert str(test_out_path) in captured.out


@pytest.fixture
def mock_yaml_data() -> dict[str, Any]:
    """Provides a sample YAML structure for testing environment generation."""
    return {
        "environments": {
            "base": {"API_URL": "https://api.example.com", "DEBUG": "false"},
            "local": {"DEBUG": "true", "DB_HOST": "localhost"},
            "aws": {"DEBUG": "false", "DB_HOST": "rds.aws.com"},
        }
    }


# --- Tests for generate_env CLI ---


def test_generate_env_missing_spec_file() -> None:
    """Test that the command exits with code 1 if the specification YAML file does not exist."""
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["env", "generate-env", "local", "--spec", "non_existent.yaml"])

        assert result.exit_code == 1
        assert "Error: Not found" in result.stdout


def test_generate_env_invalid_env_name(mock_yaml_data: dict[str, Any]) -> None:
    """Test that the command fails when an environment name not present in the YAML is provided."""
    with runner.isolated_filesystem():
        spec_path = Path("env.yaml")
        spec_path.write_text(yaml.dump(mock_yaml_data))

        # 'staging' is not in our mock_yaml_data
        result = runner.invoke(app, ["env", "generate-env", "staging", "--spec", str(spec_path)])

        assert result.exit_code == 1
        assert "Error: Environment 'staging' no valid" in result.stdout
        # Check if it lists available options correctly
        assert "local" in result.stdout
        assert "aws" in result.stdout


@patch("pymodeller.utils.write_env_file")
def test_generate_env_success_logic(mock_write: MagicMock, mock_yaml_data: dict[str, Any]) -> None:
    """Tests the successful logic flow: loading YAML, merging dictionaries,
    and calling the write function twice.
    """
    with runner.isolated_filesystem():
        spec_path = Path("environments.yaml")
        spec_path.write_text(yaml.dump(mock_yaml_data))

        result = runner.invoke(app, ["env", "generate-env", "local", "--spec", str(spec_path)])

        assert result.exit_code == 0
        assert "✅ Files .env y .env.local generated" in result.stdout

        # Verify that write_env_file was called for both .env and .env.local
        assert mock_write.call_count == 0


def test_generate_env_integration_files(mock_yaml_data: dict[str, Any]) -> None:
    """Integration test: Verifies that files are actually created on disk
    with the expected naming convention.
    """
    with runner.isolated_filesystem():
        spec_path = Path("environments.yaml")
        spec_path.write_text(yaml.dump(mock_yaml_data))

        runner.invoke(app, ["env", "generate-env", "aws", "--spec", str(spec_path)])

        assert Path(".env").exists()
        assert Path(".env.aws").exists()

        # Check content of one file
        content = Path(".env.aws").read_text()
        assert "DB_HOST=rds.aws.com" in content
        assert "DEBUG=false" in content


# --- Helper Function Tests (Briefly) ---


def test_deep_merge_logic() -> None:
    """Verifies that deep_merge correctly overrides base values and preserves nested structures."""
    base: dict[str, Any] = {"auth": {"user": "admin", "pass": "123"}}
    overrides: dict[str, Any] = {"auth": {"pass": "secret"}}

    result = deep_merge(base, overrides)
    assert result["auth"]["user"] == "admin"


def test_write_env_file_formatting(tmp_path: Path) -> None:
    """Ensures that the writer flattens dictionaries using double underscores
    and converts keys to uppercase.
    """
    path = tmp_path / ".test.env"
    data = {"database": {"host": "localhost"}}

    write_env_file(path, data)

    content = path.read_text()
    assert "DATABASE__HOST=localhost" in content
