from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pymodeller.generators.pydantic_generator import PydanticGenerator
from pymodeller.loader import EnvSection, EnvSpec, EnvVarSpec, SectionType


class TestPydanticGenerator:
    """Test suite for the PydanticGenerator class."""

    @pytest.fixture
    def generator(self) -> PydanticGenerator:
        """Fixture to initialize the PydanticGenerator with mocked Jinja2 environment.

        Returns:
            PydanticGenerator: An instance of the generator.
        """
        with (
            patch("pymodeller.generators.pydantic_generator.Environment"),
            patch("pymodeller.generators.pydantic_generator.PackageLoader"),
        ):
            gen = PydanticGenerator()
            # Mock the templates to avoid looking for real files
            gen.template = MagicMock()
            gen.env.get_template = MagicMock(return_value=MagicMock())
            return gen

    def test_get_python_type_secret(self, generator: PydanticGenerator) -> None:
        """Test that secret variables return SecretStr."""
        var = EnvVarSpec(name="token", type="str", secret=True)
        assert generator.get_python_type(var) == "SecretStr"

    def test_get_python_type_optional(self, generator: PydanticGenerator) -> None:
        """Test that non-required variables with no default return Optional."""
        var = EnvVarSpec(name="user", type="str", required=False, default=None)
        assert generator.get_python_type(var) == "Optional[str]"

    def test_get_python_type_from_model(self, generator: PydanticGenerator) -> None:
        """Test that variables referencing another model return the Model name."""
        var = EnvVarSpec(name="sub", type="object", from_model="device", required=True)
        assert generator.get_python_type(var) == "DeviceModel"

    def test_get_default_expr_path(self) -> None:
        """Test the generation of default expression for Path types."""
        var = EnvVarSpec(name="root", type="Path", default="/data")
        result = PydanticGenerator.get_default_expr(var)
        assert result == 'default=Path("/data")'

    def test_get_default_expr_bool(self) -> None:
        """Test the generation of default expression for boolean types."""
        var = EnvVarSpec(name="active", type="bool", default="true")
        assert PydanticGenerator.get_default_expr(var) == "default=True"

    def test_get_default_expr_required(self) -> None:
        """Test that required variables return the ellipsis (...) marker."""
        var = EnvVarSpec(name="key", type="str", required=True, default=None)
        assert PydanticGenerator.get_default_expr(var) == "..."

    def test_generate_module_class_name_settings(self) -> None:
        """Test module and class name generation for Settings sections."""
        section = EnvSection(name="Path", type=SectionType.SETTINGS)
        module, class_name = PydanticGenerator.generate_module_class_name(section)
        assert module == "path_settings"
        assert class_name == "PathSettings"

    def test_generate_module_class_name_model(self) -> None:
        """Test module and class name generation for Model sections."""
        section = EnvSection(name="Device Info", type=SectionType.MODEL)
        module, class_name = PydanticGenerator.generate_module_class_name(section)
        assert module == "device_info"
        assert class_name == "DeviceInfoModel"

    def test_render_section(self, generator: PydanticGenerator) -> None:
        """Test that render_section correctly calls the Jinja2 template with context."""
        var = EnvVarSpec(name="input", type="str", alias="in")
        section = EnvSection(name="test", type=SectionType.SETTINGS, variables=[var])

        generator.render_section(section)

        # Verify that the template.render was called
        generator.template.render.assert_called_once()
        args, _ = generator.template.render.call_args
        context = args[0]

        assert context["class_name"] == "TestSettings"
        assert context["variables"][0]["name"] == "input"

    def test_generate_base_class(self, generator: PydanticGenerator, tmp_path: Path) -> None:
        """Test the generation of the base_settings.py file."""
        mock_template = MagicMock()
        mock_template.render.return_value = "class BaseTraceableSettings: pass"
        generator.env.get_template.return_value = mock_template

        generator.generate_base_class(tmp_path)

        expected_file = tmp_path / "base_settings.py"
        assert expected_file.exists()
        assert expected_file.read_text() == "class BaseTraceableSettings: pass"

    def test_generate_files_empty(self, generator: PydanticGenerator) -> None:
        """Test that generate_files returns None if no sections are provided."""
        spec = EnvSpec(sections=[])
        result = generator.generate_files("hash", spec, Path("out"), Path("master"))
        assert result == (None, None)

    @patch("typer.echo")
    def test_generate_files_full_flow(self, mock_echo: MagicMock, generator: PydanticGenerator, tmp_path: Path) -> None:
        """Test the full generation flow including file creation and Typer output."""
        # Set up a mock spec
        var = EnvVarSpec(name="port", type="int", default=80)
        section = EnvSection(name="Server", type=SectionType.SETTINGS, variables=[var])
        spec = EnvSpec(sections=[section])

        out_dir = tmp_path / "models"
        master_file = tmp_path / "master.py"

        # Configure mocks to return dummy strings
        generator.template.render.return_value = "content"
        generator.env.get_template.return_value.render.return_value = "content"

        generator.generate_files("hash123", spec, out_dir, master_file)

        # Check if the specific model file was created
        assert (out_dir / "server_settings.py").exists()
        # Check if master file was created
        assert master_file.exists()
        # Check if typer.echo was called (logging)
        assert mock_echo.called
