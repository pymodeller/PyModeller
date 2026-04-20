from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pymodeller.generators.peewee_generator import PeeweeCodeGenerator
from pymodeller.loader import DBField, EnvSection, EnvSpec, EnvVarSpec, SectionType


class TestPeeweeGenerator:
    """Tests for Peewee model generation covering all mapping and file logic."""

    # --- Tests for Path & Import Logic (Lines 21-29, 34-58) ---

    @pytest.mark.parametrize(
        "path_str, expected",
        [
            ("tmp_dir/models/db.py", "models.db"),
            ("src/pymodeller/models.py", "pymodeller.models"),
            ("simple/path.py", "simple.path"),
        ],
    )
    def test_create_import_str(self, path_str: str, expected: str) -> None:
        """Verify that system paths are correctly converted into Python import dots."""
        assert PeeweeCodeGenerator.create_import_str(Path(path_str)) == expected

    def test_build_header_files_with_and_without_out(self) -> None:
        """Cover lines 34-58: Header generation with optional database imports."""
        header_no_out = PeeweeCodeGenerator.build_header_files(None)
        assert "Auto-generated" in "".join(header_no_out)

        header_with_out = PeeweeCodeGenerator.build_header_files(Path("src/db.py"))
        assert "from db import get_database" in "".join(header_with_out)

    # --- Tests for Field Mapping (Lines 63-70, 76-86, 91-139) ---

    @pytest.mark.parametrize(
        "var_type, expected_peewee",
        [
            ("str", "CharField"),
            ("int", "IntegerField"),
            ("bool", "BooleanField"),
            ("datetime", "DateTimeField"),
            ("unknown", "CharField"),  # Default case
        ],
    )
    def test_get_peewee_type(self, var_type: str, expected_peewee: str) -> None:
        """Verify mapping between YAML types and Peewee field classes."""
        var = MagicMock(spec=EnvVarSpec)
        var.type = var_type
        assert PeeweeCodeGenerator.get_peewee_type(var) == expected_peewee

    def test_format_field_complex_scenarios(self) -> None:
        """Cover lines 91-139: Tests parameters like null, default, max_length,
        indices, and multi-line formatting.
        """
        # Scenario: String with constraints and indices
        db_spec = DBField(
            allow_null=True,
            max_length=100,
            index=True,
            unique=True,
            column_name="legacy_col",
            constraints=["CHECK (length(name) > 0)"],
        )
        var = EnvVarSpec(name="username", type="str", required=False, default="guest", db_spec=db_spec, env_name="USER")

        result = PeeweeCodeGenerator.format_field(var)
        assert "CharField" in result
        assert "null=True" in result
        assert "default='guest'" in result
        assert "max_length=100" in result
        assert "column_name='legacy_col'" in result
        assert "SQL(" in result  # Constraints check

    def test_add_foreign_logic(self) -> None:
        """Cover lines 76-86: Foreign key mapping and parameters."""
        db = DBField(foreign_key="User", backref="profiles", on_delete="CASCADE")
        params, field_type = PeeweeCodeGenerator.add_foreign(db, [], "CharField")

        assert field_type == "ForeignKeyField"
        assert "User" in params
        assert "backref='profiles'" in params
        assert "on_delete='CASCADE'" in params

    # --- Tests for Meta & Composite Keys (Lines 144-147, 152-184) ---

    def test_to_composite_key(self) -> None:
        """Verify composite key string generation."""
        assert PeeweeCodeGenerator.to_composite_key(["id", "version"]) == 'CompositeKey("id", "version")'
        assert PeeweeCodeGenerator.to_composite_key([]) == ""

    def test_add_meta_with_indexes(self) -> None:
        """Cover lines 152-184: Table name, primary keys, and indexes list."""
        section = MagicMock(spec=EnvSection)
        section.name = "User Profile"
        section.database.table_name = ""  # Triggers to_snake_case
        section.database.primary_key = ["id", "tenant"]
        section.database.indexes = [{"fields": ["email"], "unique": True}]

        lines = PeeweeCodeGenerator.add_meta([], section)

        content = "\n".join(lines)
        assert "class Meta:" in content

    # --- Tests for File Generation & Orchestration (Lines 189-315) ---

    def test_generate_files_no_peewee_sections(self) -> None:
        """Verify early exit if no Peewee sections exist (Line 285)."""
        spec = EnvSpec(sections=[EnvSection(name="S1", type=SectionType.SETTINGS, variables=[])])
        out_path, _ = PeeweeCodeGenerator.generate_files("hash", spec, Path("out"), Path("master.py"))
        assert out_path is None

    @patch("pathlib.Path.write_text")
    @patch("pathlib.Path.mkdir")
    def test_generate_files_success(self, mock_mkdir: MagicMock, mock_write: MagicMock) -> None:
        """Cover full file orchestration: models, __init__.py, and master settings.
        Covers lines 284-315 and helper codegen_init/generate_main.
        """
        # Setup complex spec
        var = EnvVarSpec(name="id", type="int", required=True, env_name="ID")
        sect = EnvSection(name="User", type=SectionType.PEEWEE, variables=[var])
        spec = EnvSpec(sections=[sect])

        out = Path("models_pkg")
        master = Path("settings/db_master.py")

        res_master, res_dir = PeeweeCodeGenerator.generate_files("abc", spec, out, master)

        assert res_master == master
        assert res_dir == out
        # Check that it tried to write at least 3 files: model, __init__, and master
        assert mock_write.call_count >= 3

    def test_generate_main_content(self) -> None:
        """Cover lines 236-275: Main database settings template generation."""
        lines = PeeweeCodeGenerator.generate_main()
        content = "\n".join(lines)
        assert "class DatabaseSettings(BaseSettings):" in content
        assert "def get_database() -> PostgresqlDatabase:" in content
        assert 'env_prefix="DATABASE_"' in content
