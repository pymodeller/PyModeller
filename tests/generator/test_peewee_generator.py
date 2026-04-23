"""Test for peewee generator."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pymodeller.generators.peewee_generator import PeeweeGenerator
from pymodeller.loader import DBField, DBSpec, EnvSection, EnvSpec, EnvVarSpec, SectionType


class TestPeeweeGenerator:
    """Test suite for the PeeweeGenerator class."""

    @pytest.fixture
    def generator(self) -> PeeweeGenerator:
        """Fixture to provide a PeeweeGenerator instance with mocked Jinja2 env."""
        with patch("jinja2.Environment"):
            gen = PeeweeGenerator()
            # Mock the templates to return a simple string or the context
            gen.env.get_template = MagicMock()
            return gen

    def test_generate_module_class_name(self, generator: PeeweeGenerator) -> None:
        """Test conversion of strings to snake_case modules and PascalCase classes."""
        module, clazz = generator.generate_module_class_name("User Profile")
        assert module == "user_profile"
        assert clazz == "UserProfile"

    def test_generate_import_removes_src(self, generator: PeeweeGenerator) -> None:
        """Test that 'src' prefix is correctly removed from python import paths."""
        path = Path("src/app/database/models.py")
        import_path = generator.generate_import(path)
        assert import_path == "app.database.models"

    def test_get_field_data_basic_types(self, generator: PeeweeGenerator) -> None:
        """Test mapping of basic YAML types to Peewee field types."""
        var = EnvVarSpec(name="age", type="int", required=True)
        data = generator._get_field_data(var)

        assert data["name"] == "age"
        assert data["field_type"] == "IntegerField"
        assert "null=True" not in data["params"]

    def test_get_field_data_with_db_spec(self, generator: PeeweeGenerator) -> None:
        """Test field generation with specific DB constraints like unique and index."""
        db_field = DBField(unique=True, index=True, max_length=50, column_name="username_db")
        var = EnvVarSpec(name="username", type="str", db_spec=db_field)

        data = generator._get_field_data(var)
        assert "unique=True" in data["params"]
        assert "index=True" in data["params"]
        assert "max_length=50" in data["params"]
        assert "column_name='username_db'" in data["params"]

    def test_prepare_foreign_key(self, generator: PeeweeGenerator) -> None:
        """Test preparation of ForeignKeyField parameters."""
        db_field = DBField(foreign_key="User", backref="posts", on_delete="CASCADE")
        field_type, params = generator._prepare_foreign_key(db_field)

        assert field_type == "ForeignKeyField"
        assert "User" in params
        assert "backref='posts'" in params
        assert "on_delete='CASCADE'" in params

    def test_render_section_context(self, generator: PeeweeGenerator) -> None:
        """Test that the context sent to the Jinja2 template is correct."""
        # Setup complex section
        db_spec = DBSpec(table_name="custom_table", primary_key=["id", "code"])
        var = EnvVarSpec(name="id", type="int", required=True)
        section = EnvSection(name="Product", type=SectionType.PEEWEE, variables=[var], database=db_spec)
        master_path = Path("src/db/config.py")

        # Mock template render return value
        generator.env.get_template().render.return_value = "rendered_code"

        result = generator.render_section(section, master_path)

        # Verify template was called with expected context keys
        args, _ = generator.env.get_template().render.call_args
        context = args[0]

        assert context["class_name"] == "Product"
        assert context["table_name"] == "custom_table"
        assert "CompositeKey('id', 'code')" in context["primary_key"]
        assert "from db.config import get_database" in context["extra_imports"]
        assert result == "rendered_code"

    def test_generate_files_creation(self, generator: PeeweeGenerator, tmp_path: Path) -> None:
        """Test full file generation cycle using a temporary directory."""
        # Setup paths
        out_dir = tmp_path / "models"
        master_file = tmp_path / "db.py"

        # Setup minimal spec
        var = EnvVarSpec(name="name", type="str")
        section = EnvSection(name="Client", type=SectionType.PEEWEE, variables=[var])
        spec = EnvSpec(sections=[section])

        # Mock templates
        generator.env.get_template().render.return_value = "mocked code"

        res_master, res_out = generator.generate_files(spec, out_dir, master_file)

        # Assertions
        assert master_file.exists()
        assert (out_dir / "client.py").exists()
        assert (out_dir / "__init__.py").exists()
        assert res_master == master_file
        assert res_out == out_dir

    def test_generate_files_no_peewee_sections(self, generator: PeeweeGenerator, tmp_path: Path) -> None:
        """Verify that the generator returns None if no PEEWEE sections are found."""
        section = EnvSection(name="Settings", type=SectionType.SETTINGS, variables=[])
        spec = EnvSpec(sections=[section])

        res_master, res_out = generator.generate_files(spec, tmp_path / "out", tmp_path / "db.py")

        assert res_master is None
        assert res_out is None
