"""Generate code for peewee models."""

from pathlib import Path

import typer

from pymodeller.config import get_code_gen_config
from pymodeller.loader import DBField, EnvSection, EnvSpec, EnvVarSpec, SectionType
from pymodeller.utils import to_snake_case

code_gen_conf = get_code_gen_config()
_YAML_HASH_MARKER = "# YAML-SHA256: "


class PeeweeCodeGenerator:
    """Handles Peewee Model generation."""

    @staticmethod
    def create_import_str(out: Path) -> str:
        """Create import."""
        parts = out.with_suffix("").parts

        if parts[0].startswith("tmp"):
            parts = parts[1:]

        if parts and parts[0] in ["src", "/"]:
            parts = parts[1:]

        return ".".join(parts)

    @staticmethod
    def build_header_files(out: Path | None = None) -> list:
        """Build header files."""
        result = ""

        if out:
            result = PeeweeCodeGenerator.create_import_str(out)

        lines = [
            '"""Auto-generated settings from YAML spec."""',
            "from datetime import datetime",
            "from typing import ClassVar",
            "from peewee import SQL",
            f"from {result} import get_database" if out else "",
            "from datetime import datetime",
            "from peewee import (",
            "    CompositeKey,",
            "    CharField,",
            "    CompositeKey,",
            "    DateTimeField,",
            "    FloatField,",
            "    IntegerField,",
            "    ForeignKeyField,",
            "    Model,",
            ")",
            "",
        ]
        return lines

    @staticmethod
    def get_peewee_type(var: EnvVarSpec) -> str:
        """Mapea tipos de YAML a campos de Peewee."""
        mapping = {
            "str": "CharField",
            "int": "IntegerField",
            "bool": "BooleanField",
            "float": "FloatField",
            "datetime": "DateTimeField",
        }
        return mapping.get(var.type, "CharField")

    @staticmethod
    def add_foreign(db: DBField | None, params: list, field_type: str) -> tuple:
        """Add foreign key."""
        # foreign key
        if db and db.foreign_key:
            params = []
            if db.backref:
                params.append(f"backref='{db.backref}'")

            if db.on_delete:
                params.append(f"on_delete='{db.on_delete}'")
            params = [f"{db.foreign_key}", *params]
            field_type = "ForeignKeyField"

        return params, field_type

    @staticmethod
    def format_field(var: EnvVarSpec) -> str:
        """Genera una línea de campo estilo Peewee con lógica simplificada."""
        db = var.db_spec
        field_type = PeeweeCodeGenerator.get_peewee_type(var)

        def add(condition: bool, value: str) -> None:
            """Add param to list."""
            if condition:
                params.append(value)

        params = []

        condition = bool(not var.required or (db and db.allow_null))
        # null
        add(condition, "null=True")

        # default
        if var.default is not None:
            default = repr(var.default)
            params.append(f"default={default}")

        if db:
            add(db.max_length is not None, f"max_length={db.max_length}")
            add(db.index, "index=True")
            add(db.unique, "unique=True")
            add(db.column_name is not None, f"column_name='{db.column_name}'")
            add(db.default_callable is not None, f"default={db.default_callable}")

        # foreign key
        params, field_type = PeeweeCodeGenerator.add_foreign(db, params, field_type)

        # constraints
        if db and db.constraints:
            constraints = ",\n            ".join(f"SQL({c!r})" for c in db.constraints)
            params.append(f"constraints=[\n            {constraints}\n        ]")

        # render
        if len(params) <= 3:
            joined = ", ".join(params)
            return f"    {var.name} = {field_type}({joined})"

        joined = ",\n        ".join(params)
        return f"""    {var.name} = {field_type}(
            {joined}
        )"""

    @staticmethod
    def to_composite_key(s: list[str]) -> str:
        """Generate composite key."""
        if not s:
            return ""
        cols_str = ", ".join(f'"{c}"' for c in s)
        return f"CompositeKey({cols_str})"

    @staticmethod
    def add_meta(lines: list, section: EnvSection) -> list:
        """Add class meta."""
        if section.database:
            table_name_ = section.database.table_name

            table_name = to_snake_case(section.name) if table_name_ != "" else table_name_

            composite_ = section.database.primary_key

            composite = PeeweeCodeGenerator.to_composite_key(composite_) if composite_ else None

            lines += [
                "",
                "    class Meta:",
                '        """Database configuration."""',
                "        database = get_database()",
                f"        table_name = '{table_name}'",
            ]

            if composite:
                lines.append(f"        primary_key = {composite}")

            indexes = section.database.indexes
            if indexes:
                lines.append("        indexes: ClassVar = [")

                for idx in indexes:
                    fields = idx.get("fields", [])
                    unique = idx.get("unique", False)

                    cols = ", ".join(f"'{c}'" for c in fields)
                    lines.append(f"            (({cols}), {unique}),")

                lines.append("        ]")
        return lines

    @staticmethod
    def codegen_section(section: EnvSection, out: Path, master: Path) -> list:
        """Generate code section."""
        class_name = PeeweeCodeGenerator._section_class_name(section)

        foreign_keys_ = [v.db_spec.foreign_key for v in section.variables if v.db_spec and v.db_spec.foreign_key]
        result = PeeweeCodeGenerator.create_import_str(out)

        lines = [
            *PeeweeCodeGenerator.build_header_files(master),
            f"from {result} import {', '.join(foreign_keys_)}" if out and len(foreign_keys_) > 0 else "",
            "",
            f"class {class_name}(Model):",
            f'    """{section.description}."""',
        ]

        for var in section.variables:
            lines.append(PeeweeCodeGenerator.format_field(var))

        lines = PeeweeCodeGenerator.add_meta(lines, section)

        return lines

    @staticmethod
    def _section_class_name(section: EnvSection) -> str:
        """Convert a section name to a PascalCase class name, e.g. 'API Service' → 'ApiServiceSettings'."""
        return "".join(word.title() for word in section.name.split())

    @staticmethod
    def codegen_init(init_imports: list, all_imports: list, folder: Path) -> None:
        """Generate init from package."""
        str_all_imports = ", ".join(all_imports)

        init_lines = [
            '"""Auto-generated models package."""',
            "",
            *init_imports,
            "",
            f"__all__ = [{str_all_imports}]",
        ]

        init_file = folder / "__init__.py"
        init_content = "\n".join(init_lines) + "\n"

        init_file.write_text(init_content, encoding="utf-8")
        typer.echo(f"   Init: {init_file}")

    @staticmethod
    def generate_main() -> list:
        """Generate main content."""
        lines = [
            *PeeweeCodeGenerator.build_header_files(),
            "from functools import lru_cache",
            "from peewee import PostgresqlDatabase",
            "from pydantic import Field, SecretStr",
            "from pydantic_settings import SettingsConfigDict, BaseSettings",
            "",
            "class DatabaseSettings(BaseSettings):",
            '    """Database settings."""',
            "",
            "    name: str | None = Field(default=None)",
            "    user: str | None = Field(default=None)",
            '    psswrd: SecretStr = Field(default=SecretStr(""))',
            "    host: str | None = Field(default=None)",
            "    port: str | None = Field(default=None)",
            "",
            "    model_config = SettingsConfigDict(",
            '        env_prefix="DATABASE_",',
            "        populate_by_name=True,",
            '        env_file=".env",',
            '        env_file_encoding="utf-8",',
            "        env_ignore_empty=True,",
            '        env_nested_delimiter="__",',
            "        case_sensitive=False,",
            '        extra="ignore",',
            "    )",
            "",
            "@lru_cache(maxsize=1)",
            "def get_database() -> PostgresqlDatabase:",
            '    """Get settings."""',
            "    db_settings = DatabaseSettings()",
            "    return PostgresqlDatabase(",
            "        database=db_settings.name,",
            "        user=db_settings.user,",
            "        password=db_settings.psswrd.get_secret_value(),", # NOSONAR
            "        host=db_settings.host,",
            "        port=db_settings.port,",
            "    )",
        ]
        return lines

    @staticmethod
    def generate_files(s: EnvSpec, out: Path, master: Path) -> tuple:
        """Generate files."""
        sections = [s for s in s.sections if s.type == SectionType.PEEWEE]
        if len(sections) == 0:
            return None, None

        models_dir = Path(out)
        models_dir.mkdir(parents=True, exist_ok=True)

        sections_with_classes: list[EnvSection] = []

        init_imports = []
        all_imports = []

        for sect in sections:
            section_lines = PeeweeCodeGenerator.codegen_section(sect, out, master)
            sections_with_classes.append(sect)
            class_name = PeeweeCodeGenerator._section_class_name(sect)

            init_imports.append(f"from .{to_snake_case(sect.name).replace(' ', '_')} import {class_name}")
            all_imports.append(f'"{class_name}"')

            # Nombre del archivo en snake_case
            file_name = to_snake_case(sect.name).replace(" ", "_") + ".py"
            file_path = models_dir / file_name

            file_path.write_text("\n".join(section_lines), encoding="utf-8")
            typer.echo(f"   Model: {file_path}")

        PeeweeCodeGenerator.codegen_init(init_imports, all_imports, out)

        lines = PeeweeCodeGenerator.generate_main()

        out_path = Path(master)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines), encoding="utf-8")
        typer.echo(f"   Out: {out_path}")
        return out_path, models_dir
