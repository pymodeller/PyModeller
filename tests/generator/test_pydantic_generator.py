"""Unit tests for the Pydantic generator module.

========================================================================================================================
Name:        tests/generators/test_pydantic_generator.py
Description: Comprehensive test suite for PydanticGenerator, verifying static helper methods,
             type expression building, Jinja2 template context preparation, file output generation,
             and directory structures.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from pymodeller.config import DestinationConfig
from pymodeller.generators.pydantic_generator import PydanticGenerator
from pymodeller.loader import (
    DestinationType,
    EnvSection,
    EnvSpec,
    EnvVarSpec,
    SectionType,
)


class TestPydanticGeneratorHelpers(unittest.TestCase):
    """Unit tests for static helper methods within PydanticGenerator."""

    def test_get_python_type_secret(self) -> None:
        """Test that secret variables are typed as SecretStr."""
        var: EnvVarSpec = EnvVarSpec(name="api_key", secret=True)
        py_type: str = PydanticGenerator.get_python_type(var)
        self.assertEqual(py_type, "SecretStr")

    def test_get_python_type_yaml_map_and_optional(self) -> None:
        """Test Python type resolution using YAML_TYPE_MAP and optional wrapping."""
        # Non-required without default -> Optional[str]
        var_opt: EnvVarSpec = EnvVarSpec(name="description", type="string", required=False)
        self.assertEqual(PydanticGenerator.get_python_type(var_opt), "str | None")

        # Required field -> str
        var_req: EnvVarSpec = EnvVarSpec(name="description", type="string", required=True)
        self.assertEqual(PydanticGenerator.get_python_type(var_req), "str")

    def test_get_python_type_from_model_and_enum(self) -> None:
        """Test Python type resolution when referencing nested models or enums."""
        var_model: EnvVarSpec = EnvVarSpec(name="user", from_model="user_detail")
        var_enum: EnvVarSpec = EnvVarSpec(name="role", from_enum="user_role")
        var_list_model: EnvVarSpec = EnvVarSpec(
            name="items", type="list", from_model="item_detail", required=True
        )

        self.assertEqual(PydanticGenerator.get_python_type(var_model), "UserDetailModel | None")
        self.assertEqual(PydanticGenerator.get_python_type(var_enum), "UserRoleEnum | None")
        self.assertEqual(PydanticGenerator.get_python_type(var_list_model), "list[ItemDetailModel]")

    def test_get_default_expr_variations(self) -> None:
        """Test Field default expression formatting for various data types."""
        req_var: EnvVarSpec = EnvVarSpec(name="id", required=True)
        secret_var: EnvVarSpec = EnvVarSpec(name="token", secret=True, default="my-secret")
        dt_var: EnvVarSpec = EnvVarSpec(name="created_at", type="datetime")
        path_var: EnvVarSpec = EnvVarSpec(name="config_path", type="Path", default="/etc/app")
        bool_var: EnvVarSpec = EnvVarSpec(name="is_active", type="bool", default="true")
        enum_var: EnvVarSpec = EnvVarSpec(name="status", from_enum="status_type", default="active")

        self.assertEqual(PydanticGenerator.get_default_expr(req_var), "...")
        self.assertEqual(PydanticGenerator.get_default_expr(secret_var), 'default=SecretStr("my-secret")')
        self.assertEqual(PydanticGenerator.get_default_expr(dt_var), "default=datetime.now()")
        self.assertEqual(PydanticGenerator.get_default_expr(path_var), 'default=Path("/etc/app")')
        self.assertEqual(PydanticGenerator.get_default_expr(bool_var), "default=True")
        self.assertEqual(PydanticGenerator.get_default_expr(enum_var), "default=StatusTypeEnum.ACTIVE")

    def test_generate_module_class_name(self) -> None:
        """Test generation of Python module and class names from section specifications."""
        settings_sec: EnvSection = EnvSection(name="database", type=SectionType.SETTINGS)
        model_sec: EnvSection = EnvSection(name="user_account", type=SectionType.MODEL)

        s_mod, s_cls = PydanticGenerator.generate_module_class_name(settings_sec)
        m_mod, m_cls = PydanticGenerator.generate_module_class_name(model_sec)

        self.assertEqual(s_mod, "database_settings")
        self.assertEqual(s_cls, "DatabaseSettings")
        self.assertEqual(m_mod, "user_account")
        self.assertEqual(m_cls, "UserAccountModel")

    def test_generate_import_path_stripping(self) -> None:
        """Test import string resolution stripping 'src' prefixes."""
        path_with_src: Path = Path("src/app/domain/models/user.py")
        path_without_src: Path = Path("app/domain/models/user.py")

        self.assertEqual(PydanticGenerator.generate_import(path_with_src), "app.domain.models.user")
        self.assertEqual(PydanticGenerator.generate_import(path_without_src), "app.domain.models.user")


class TestPydanticGeneratorRendering(unittest.TestCase):
    """Unit tests for template context rendering methods."""

    def setUp(self) -> None:
        """Set up mock DestinationConfig and initialize PydanticGenerator instance."""
        self.mock_dest_config: MagicMock = MagicMock(spec=DestinationConfig)
        self.mock_dest_config.import_init_base_class = "app.base.BaseSettings"
        self.mock_dest_config.test_folder = Path("/tmp/tests")
        self.mock_dest_config.base_dir = Path("/tmp/base")
        self.mock_dest_config.pydantic_model_folder = Path("src/app/models")
        # self.mock_dest_config.enumerations_folder = Path("src/app/enums")
        self.mock_dest_config.pydantic_settings_folder = Path("src/app/settings")

        with patch("pymodeller.generators.pydantic_generator.PackageLoader"), patch(
            "pymodeller.generators.pydantic_generator.Environment"
        ):
            self.generator: PydanticGenerator = PydanticGenerator(self.mock_dest_config)

    def test_get_import_path_internal_helper(self) -> None:
        """Test internal _get_import_path file-to-module conversion."""
        base_path: Path = Path("src/app")
        target_path: Path = Path("src/app/infrastructure/config/settings/base_settings.py")

        import_str: str = self.generator._get_import_path(base_path, target_path)
        self.assertEqual(import_str, "app.infrastructure.config.settings.base_settings")


class TestPydanticGeneratorFileGeneration(unittest.TestCase):
    """Unit tests for disk writing and code generation routines."""

    def setUp(self) -> None:
        """Set up temporary directories and generator instance."""
        self.temp_dir: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory()
        self.base_path: Path = Path(self.temp_dir.name)

        self.mock_dest_config: MagicMock = MagicMock(spec=DestinationConfig)
        self.mock_dest_config.destination_type = DestinationType.INFRASTRUCTURE
        self.mock_dest_config.import_init_base_class = "app.base.BaseSettings"
        self.mock_dest_config.base_dir = self.base_path
        self.mock_dest_config.test_folder = self.base_path / "tests"
        self.mock_dest_config.pydantic_model_folder = self.base_path / "models"
        self.mock_dest_config.pydantic_settings_folder = self.base_path / "settings"
        self.mock_dest_config.pydantic_settings_init = self.base_path / "settings" / "master.py"
        self.mock_dest_config.enumerations_folder = self.base_path / "enumerations"

        with patch("pymodeller.generators.pydantic_generator.PackageLoader"), patch(
            "pymodeller.generators.pydantic_generator.Environment"
        ) as mock_env_cls:
            self.mock_env: MagicMock = MagicMock()
            mock_env_cls.return_value = self.mock_env
            self.mock_template: MagicMock = MagicMock()
            self.mock_template.render.return_value = "# Auto-generated python code"
            self.mock_env.get_template.return_value = self.mock_template

            self.generator: PydanticGenerator = PydanticGenerator(self.mock_dest_config)

    def tearDown(self) -> None:
        """Clean up temporary directory after each test execution."""
        self.temp_dir.cleanup()

    def test_check_dir_creates_directory_structure(self) -> None:
        """Test directory existence checking and recursive creation."""
        target_dir: Path = self.base_path / "nested" / "output"
        resolved_path: Path = PydanticGenerator.check_dir(target_dir)

        self.assertTrue(resolved_path.exists())
        self.assertTrue(resolved_path.is_dir())

    def test_save_template_creates_files_and_init(self) -> None:
        """Test template rendering and saving to target output directories."""
        out_path: Path = self.base_path / "output"
        self.generator.save_template(out_path, template_name="base_settings")

        saved_file: Path = out_path / "base_settings.py"
        init_file: Path = out_path / "__init__.py"

        self.assertTrue(saved_file.exists())
        self.assertTrue(init_file.exists())
        self.assertEqual(saved_file.read_text(encoding="utf-8"), "# Auto-generated python code")


if __name__ == "__main__":
    unittest.main()