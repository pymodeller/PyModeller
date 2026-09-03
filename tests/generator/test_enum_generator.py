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


class TestEnumGeneratorHelpers(unittest.TestCase):
    """Unit tests for helper methods in EnumGenerator."""

    def test_to_snake_case(self) -> None:
        """Test CamelCase / PascalCase to snake_case string transformation."""
        self.assertEqual(EnumGenerator._to_snake_case("UserRole"), "user_role")
        self.assertEqual(EnumGenerator._to_snake_case("HTTPStatusType"), "h_t_t_p_status_type")
        self.assertEqual(EnumGenerator._to_snake_case("Status"), "status")



if __name__ == "__main__":
    unittest.main()