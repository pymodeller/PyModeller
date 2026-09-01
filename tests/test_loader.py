"""Unit tests for the env-spec loader module.

========================================================================================================================
Name:        tests/test_loader.py
Description: Exhaustive test suite for verifying validation, parsing, normalization,
             and file loading logic in core/env/loader.py.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from pymodeller.loader import (
    DestinationType,
    EnvSection,
    EnvSpec,
    EnvVarSpec,
    SectionType,
    load_env_spec,
)


class TestEnvVarSpec(unittest.TestCase):
    """Unit tests for the EnvVarSpec Pydantic model and its validators."""

    def test_normalize_name_to_snake_case(self) -> None:
        """Test that variable names are automatically normalized to snake_case."""
        with patch("pymodeller.loader.to_snake_case", return_value="database_url") as mock_snake:
            var_spec: EnvVarSpec = EnvVarSpec(name="DatabaseUrl")
            mock_snake.assert_called_once_with("DatabaseUrl")
            self.assertEqual(var_spec.name, "database_url")

    def test_normalize_type_from_yaml_map(self) -> None:
        """Test that YAML raw type string mappings are converted to standard Python types."""
        var_str: EnvVarSpec = EnvVarSpec(name="var1", type="string")
        var_path: EnvVarSpec = EnvVarSpec(name="var2", type="path")
        var_unknown: EnvVarSpec = EnvVarSpec(name="var3", type="CustomClass")

        self.assertEqual(var_str.type, "str")
        self.assertEqual(var_path.type, "Path")
        self.assertEqual(var_unknown.type, "CustomClass")

    def test_derived_fields_alias_and_variants(self) -> None:
        """Test default fallback for alias generation and validation_alias variants."""
        with (
            patch("pymodeller.loader.to_camel_case", return_value="dbPort") as mock_camel,
            patch("pymodeller.loader.get_variants", return_value=["DB_PORT", "db_port"]) as mock_variants,
        ):
            var_spec: EnvVarSpec = EnvVarSpec(name="db_port")

            mock_camel.assert_called_once_with("db_port")
            mock_variants.assert_called_once_with("db_port")
            self.assertEqual(var_spec.alias, "dbPort")
            self.assertEqual(var_spec.validation_alias, ["DB_PORT", "db_port"])

    def test_automatic_secret_detection_from_prefixes(self) -> None:
        """Test that defaults matching AWS ARN or S3 URI prefixes are marked as secret."""
        aws_var: EnvVarSpec = EnvVarSpec(name="aws_res", default="arn:aws:s3:::mybucket")
        s3_var: EnvVarSpec = EnvVarSpec(name="s3_res", default="s3://mybucket/path")
        plain_var: EnvVarSpec = EnvVarSpec(name="plain_res", default="http://localhost")

        self.assertTrue(aws_var.secret)
        self.assertTrue(s3_var.secret)
        self.assertFalse(plain_var.secret)

    def test_secret_sugar_syntax(self) -> None:
        """Test that type='secret' converts type to 'str' and sets secret=True."""
        secret_var: EnvVarSpec = EnvVarSpec(name="api_token", type="secret", secret=True)

        self.assertTrue(secret_var.secret)

    def test_display_value_masking(self) -> None:
        """Test display value generation for secrets vs plain defaults."""
        plain_var: EnvVarSpec = EnvVarSpec(name="host", default="127.0.0.1", secret=False)
        secret_var: EnvVarSpec = EnvVarSpec(name="key", default="super-secret-key", secret=True)
        no_default_var: EnvVarSpec = EnvVarSpec(name="port", default=None)

        self.assertEqual(plain_var.display_value(), "127.0.0.1")
        self.assertEqual(secret_var.display_value(), "")
        self.assertEqual(no_default_var.display_value(), "")


class TestEnvSection(unittest.TestCase):
    """Unit tests for the EnvSection model, validators, and metadata propagation."""

    def test_uppercase_prefix_validator(self) -> None:
        """Test that env_prefix is sanitized and converted to uppercase."""
        section: EnvSection = EnvSection(env_prefix="app_db")
        self.assertEqual(section.env_prefix, "APP_DB")

    def test_parse_pyproject_header_from_string(self) -> None:
        """Test parsing comma-separated string headers into a cleaned list."""
        section: EnvSection = EnvSection(
            pyproject_toml_table_header="tool.mypy , tool.pytest "  # type: ignore[arg-type]
        )
        self.assertEqual(section.pyproject_toml_table_header, ["tool.mypy", "tool.pytest"])

    def test_propagate_section_to_variables(self) -> None:
        """Test propagation of section name and prefixed env_name to child variables."""
        var1: EnvVarSpec = EnvVarSpec(name="host")
        var2: EnvVarSpec = EnvVarSpec(name="port", env_name="CUSTOM_PORT_NAME")

        section: EnvSection = EnvSection(
            name="DatabaseSettings",
            env_prefix="DB",
            variables=[var1, var2],
        )

        # First variable should inherit section name and generated env_name
        self.assertEqual(var1.section, "DatabaseSettings")
        self.assertEqual(var1.env_name, "DB_host")

        # Second variable should retain its custom env_name
        self.assertEqual(var2.section, "DatabaseSettings")
        self.assertEqual(var2.env_name, "CUSTOM_PORT_NAME")


class TestEnvSpec(unittest.TestCase):
    """Unit tests for the root EnvSpec model and duplicate checking logic."""

    def test_all_vars_property(self) -> None:
        """Test flattening of all variable specifications across multiple sections."""
        sec1: EnvSection = EnvSection(name="Sec1", variables=[EnvVarSpec(name="a")])
        sec2: EnvSection = EnvSection(name="Sec2", variables=[EnvVarSpec(name="b"), EnvVarSpec(name="c")])

        spec: EnvSpec = EnvSpec(sections=[sec1, sec2])
        all_var_names: list[str] = [v.name for v in spec.all_vars]

        self.assertEqual(len(spec.all_vars), 3)
        self.assertEqual(all_var_names, ["a", "b", "c"])

    def test_duplicate_env_name_raises_validation_error(self) -> None:
        """Test that duplicate env_names within SETTINGS sections raise a ValueError."""
        var1: EnvVarSpec = EnvVarSpec(name="port", env_name="APP_PORT", alias="port1")
        var2: EnvVarSpec = EnvVarSpec(name="target_port", env_name="APP_PORT", alias="port2")

        sec: EnvSection = EnvSection(
            name="Core",
            type=SectionType.SETTINGS,
            variables=[var1, var2],
        )

        with self.assertRaises(ValidationError) as ctx:
            EnvSpec(sections=[sec])

        self.assertIn("Duplicate environment variable name: APP_PORT", str(ctx.exception))

    def test_duplicate_alias_raises_validation_error(self) -> None:
        """Test that duplicate Python aliases within SETTINGS sections raise a ValueError."""
        var1: EnvVarSpec = EnvVarSpec(name="host_primary", env_name="HOST_1", alias="dbHost")
        var2: EnvVarSpec = EnvVarSpec(name="host_secondary", env_name="HOST_2", alias="dbHost")

        sec: EnvSection = EnvSection(
            name="Network",
            type=SectionType.SETTINGS,
            variables=[var1, var2],
        )

        with self.assertRaises(ValidationError) as ctx:
            EnvSpec(sections=[sec])

        self.assertIn("Duplicate Python alias: dbHost", str(ctx.exception))


class TestLoadEnvSpec(unittest.TestCase):
    """Unit tests for the load_env_spec function (file and directory handling)."""

    def test_file_not_found_raises_exception(self) -> None:
        """Test that passing a non-existent file path raises FileNotFoundError."""
        non_existent_path: Path = Path("/invalid/path/to/spec.yaml")
        with self.assertRaises(FileNotFoundError):
            load_env_spec(non_existent_path)

    @patch("yaml.safe_load")
    def test_empty_sections_raises_value_error(self, mock_yaml: MagicMock) -> None:
        """Test that a spec file returning no models/sections raises a ValueError."""
        mock_yaml.return_value = {"models": []}

        with tempfile.NamedTemporaryFile(suffix=".yaml") as tmp_file:
            with self.assertRaises(ValueError) as ctx:
                load_env_spec(tmp_file.name)

            self.assertIn("Empty sections", str(ctx.exception))

    @patch("yaml.safe_load")
    def test_load_single_file_success(self, mock_yaml: MagicMock) -> None:
        """Test loading and parsing a single YAML specification file."""
        mock_yaml.return_value = {
            "models": [
                {
                    "name": "AuthSettings",
                    "type": "settings",
                    "destination": "infrastructure",
                    "variables": [{"name": "jwt_secret", "type": "secret"}],
                }
            ]
        }

        with tempfile.NamedTemporaryFile(suffix=".yaml") as tmp_file:
            spec: EnvSpec = load_env_spec(tmp_file.name)

            self.assertEqual(len(spec.sections), 1)
            self.assertEqual(spec.sections[0].name, "AuthSettings")
            self.assertEqual(spec.sections[0].destination, DestinationType.INFRASTRUCTURE)
            self.assertEqual(spec.sections[0].variables[0].name, "jwt_secret")

    @patch("yaml.safe_load")
    def test_load_directory_success(self, mock_yaml: MagicMock) -> None:
        """Test loading and parsing multiple specification files from a directory."""
        mock_yaml.side_effect = [
            {"models": [{"name": "Sec1", "variables": [{"name": "var1"}]}]},
            {"models": [{"name": "Sec2", "variables": [{"name": "var2"}]}]},
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path: Path = Path(tmp_dir)
            (dir_path / "spec1.yaml").touch()
            (dir_path / "spec2.yml").touch()

            spec: EnvSpec = load_env_spec(dir_path)

            self.assertEqual(len(spec.sections), 2)
            section_names: set[str] = {s.name for s in spec.sections}
            self.assertEqual(section_names, {"Sec1", "Sec2"})


if __name__ == "__main__":
    unittest.main()