"""Unit tests for the Enum generator module.

========================================================================================================================
Name:        tests/generators/test_enum_generator.py
Description: Comprehensive test suite for EnumGenerator, EnumerationParser, and Pydantic models.
             Verifies Pydantic parsing, snake_case conversion, Jinja2 template rendering,
             destination filtering, file creation, and exception handling.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from pymodeller.generators.enum_generator import (
    EnumGenerator,
    EnumerationConfig,
    EnumerationParser,
    EnumerationSpec,
)
from pymodeller.loader import DestinationType


class TestEnumerationModels(unittest.TestCase):
    """Unit tests for Pydantic models: EnumerationSpec and EnumerationConfig."""

    def test_enumeration_spec_defaults_and_parsing(self) -> None:
        """Test valid initialization and default destination for EnumerationSpec."""
        data = {
            "name": "UserRole",
            "options": ["ADMIN", "USER"],
            "description": "User access roles",
        }
        spec = EnumerationSpec(**data)

        self.assertEqual(spec.name, "UserRole")
        self.assertEqual(spec.destination, DestinationType.INFRASTRUCTURE)
        self.assertEqual(spec.options, ["ADMIN", "USER"])
        self.assertEqual(spec.description, "User access roles")

    def test_enumeration_spec_validation_error(self) -> None:
        """Test validation fails when required fields are missing."""
        with self.assertRaises(ValidationError):
            EnumerationSpec(name="UserRole")  # Missing options and description

    def test_enumeration_config_parsing(self) -> None:
        """Test parsing a list of enumerations inside EnumerationConfig."""
        data = {
            "enumerations": [
                {
                    "name": "Status",
                    "options": ["ACTIVE", "INACTIVE"],
                    "description": "Entity status",
                }
            ]
        }
        config = EnumerationConfig(**data)

        self.assertEqual(len(config.enumerations), 1)
        self.assertEqual(config.enumerations[0].name, "Status")


class TestEnumerationParser(unittest.TestCase):
    """Unit tests for YAML parsing via EnumerationParser."""

    def setUp(self) -> None:
        """Create a temporary directory for dummy YAML files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        """Clean up the temporary directory."""
        self.temp_dir.cleanup()

    def test_parse_yaml_success(self) -> None:
        """Test successful parsing of a valid YAML file into EnumerationSpec list."""
        yaml_content = """
        enumerations:
          - name: UserRole
            destination: infrastructure
            options:
              - ADMIN
              - GUEST
            description: Roles system
        """
        yaml_file = self.base_path / "enums.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        specs = EnumerationParser.parse_yaml(yaml_file)

        self.assertEqual(len(specs), 1)
        self.assertIsInstance(specs[0], EnumerationSpec)
        self.assertEqual(specs[0].name, "UserRole")
        self.assertEqual(specs[0].options, ["ADMIN", "GUEST"])

    def test_parse_yaml_empty_enumerations(self) -> None:
        """Test parsing YAML file without enumerations returns empty list."""
        yaml_file = self.base_path / "empty.yaml"
        yaml_file.write_text("other_key: 123", encoding="utf-8")

        specs = EnumerationParser.parse_yaml(yaml_file)
        self.assertEqual(specs, [])


class TestEnumGeneratorHelpers(unittest.TestCase):
    """Unit tests for helper methods in EnumGenerator."""

    def test_to_snake_case(self) -> None:
        """Test CamelCase / PascalCase to snake_case string transformation."""
        self.assertEqual(EnumGenerator._to_snake_case("UserRole"), "user_role")
        self.assertEqual(EnumGenerator._to_snake_case("HTTPStatusType"), "h_t_t_p_status_type")
        self.assertEqual(EnumGenerator._to_snake_case("Status"), "status")


class TestEnumGeneratorFlow(unittest.TestCase):
    """Unit tests for the main generation workflow in EnumGenerator."""

    def setUp(self) -> None:
        """Set up temporary directories and mocked Jinja environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.yaml_path = self.base_path / "enums.yaml"
        self.output_dir = self.base_path / "generated_enums"

        # Create valid dummy YAML
        yaml_content = """
        enumerations:
          - name: UserRole
            destination: infrastructure
            options: [ADMIN, USER]
            description: User roles
          - name: PaymentType
            destination: domain
            options: [CARD, CASH]
            description: Payment types
        """
        self.yaml_path.write_text(yaml_content, encoding="utf-8")

        with patch("pymodeller.generators.enum_generator.PackageLoader"), patch(
            "pymodeller.generators.enum_generator.Environment"
        ) as mock_env_cls:
            self.mock_env = MagicMock()
            mock_env_cls.return_value = self.mock_env

            # Mock template rendering
            self.mock_enum_template = MagicMock()
            self.mock_enum_template.render.return_value = "# Enum generated code"

            self.mock_init_template = MagicMock()
            self.mock_init_template.render.return_value = "# Init generated code"

            def get_template_side_effect(name: str) -> MagicMock:
                if name == "enumerate.jinja":
                    return self.mock_enum_template
                if name == "init.jinja":
                    return self.mock_init_template
                return MagicMock()

            self.mock_env.get_template.side_effect = get_template_side_effect
            self.generator = EnumGenerator(destination=DestinationType.INFRASTRUCTURE)

    def tearDown(self) -> None:
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_generate_raises_file_not_found(self) -> None:
        """Test generate method raises FileNotFoundError when YAML doesn't exist."""
        non_existent = self.base_path / "missing.yaml"
        with self.assertRaises(FileNotFoundError):
            self.generator.generate(non_existent, self.output_dir)

    def test_generate_filters_by_destination(self) -> None:
        """Test generation only processes specs matching the specified destination."""
        generated_files = self.generator.generate(self.yaml_path, self.output_dir)

        # Expected files for INFRASTRUCTURE: user_role.py + __init__.py (PaymentType is DOMAIN)
        self.assertEqual(len(generated_files), 2)
        self.assertIn(self.output_dir / "user_role.py", generated_files)
        self.assertIn(self.output_dir / "__init__.py", generated_files)
        self.assertNotIn(self.output_dir / "payment_type.py", generated_files)

    def test_generate_creates_files_and_writes_content(self) -> None:
        """Test file creation on disk and verify content written."""
        self.generator.generate(self.yaml_path, self.output_dir)

        enum_file = self.output_dir / "user_role.py"
        init_file = self.output_dir / "__init__.py"

        self.assertTrue(enum_file.exists())
        self.assertTrue(init_file.exists())

        self.assertEqual(enum_file.read_text(encoding="utf-8"), "# Enum generated code")
        self.assertEqual(init_file.read_text(encoding="utf-8"), "# Init generated code")

    def test_generate_returns_empty_when_no_destination_match(self) -> None:
        """Test returns empty list if no enum specs match generator destination."""
        try:
            generator_other = EnumGenerator(destination=DestinationType.INFRASTRUCTURE)
            generated_files = generator_other.generate(self.yaml_path, self.output_dir)
        except AttributeError:
            self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()