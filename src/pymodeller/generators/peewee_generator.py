"""Peewee generator v2 based on Jinja2 templates."""

from pathlib import Path

import typer
from jinja2 import Environment, PackageLoader, select_autoescape

from pymodeller.loader import DBField, EnvSection, EnvSpec, EnvVarSpec, SectionType
from pymodeller.utils import to_snake_case


class PeeweeGenerator:
    """Handles Peewee model generation using Jinja2 templates."""

    def __init__(self) -> None:
        """Instance peewee generator."""
        self.env = Environment(loader=PackageLoader("pymodeller", "templates"), autoescape=select_autoescape())
        self.type_mapping = {
            "str": "CharField",
            "int": "IntegerField",
            "bool": "BooleanField",
            "float": "FloatField",
            "datetime": "DateTimeField",
        }

    @staticmethod
    def generate_module_class_name(name: str) -> tuple:
        """Generate module and class names."""
        module_name = to_snake_case(name)

        class_name = "".join(word.title() for word in name.split())

        return module_name, class_name

    def _prepare_foreign_key(self, db: DBField) -> tuple:
        """Prepare foreign key."""
        field_type = "ForeignKeyField"
        params = [db.foreign_key]  # El primer argumento es la clase relacionada
        if db.backref:
            params.append(f"backref='{db.backref}'")
        if db.on_delete:
            params.append(f"on_delete='{db.on_delete}'")
        return field_type, params

    def _extent_attributes(self, db: DBField, params: list) -> list:
        """Prepare foreign key."""
        if db.max_length:
            params.append(f"max_length={db.max_length}")
        if db.index:
            params.append("index=True")
        if db.unique:
            params.append("unique=True")
        if db.column_name:
            params.append(f"column_name='{db.column_name}'")
        if db.default_callable:
            params.append(f"default={db.default_callable}")
        return params

    def _get_field_data(self, var: EnvVarSpec) -> dict:
        """Process variable specs into Peewee field parameters."""
        db = var.db_spec
        field_type = self.type_mapping.get(var.type, "CharField")
        params = []

        # Nullability & Defaults
        if not var.required or (db and db.allow_null):
            params.append("null=True")

        if var.default is not None:
            params.append(f"default={var.default!r}")

        # DB Specifics
        if db:
            if db.foreign_key:
                field_type, params = self._prepare_foreign_key(db)
            else:
                params = self._extent_attributes(db, params)

            if db.constraints:
                c_list = ", ".join([f"SQL({c!r})" for c in db.constraints])
                params.append(f"constraints=[{c_list}]")

        return {"name": var.name, "field_type": field_type, "params": params}

    @staticmethod
    def generate_import(master: Path) -> str:
        """Generate import."""
        parts = master.with_suffix("").parts

        if parts and parts[0] == "src":
            parts = parts[1:]

        return ".".join(parts)

    def render_section(self, section: EnvSection, master_import_path: Path) -> str:
        """Renders a single Peewee model file."""
        _, class_name = self.generate_module_class_name(section.name)

        # Determine extra imports for ForeignKeys
        extra_imports = []
        if master_import_path:
            import_ = self.generate_import(master_import_path)
            extra_imports.append(f"from {import_} import get_database")

        foreign_keys_ = [v.db_spec.foreign_key for v in section.variables if
                         v.db_spec and v.db_spec.foreign_key]

        for e in foreign_keys_:
            module_, class_= self.generate_module_class_name(e)
            extra_imports.append(f"from .{module_} import {class_}")

        variables_context = [self._get_field_data(v) for v in section.variables]

        table_name = (
            section.database.table_name
            if section.database and section.database.table_name
            else to_snake_case(section.name)
        )

        pk = None
        if section.database and section.database.primary_key:
            cols = ", ".join([f"'{c}'" for c in section.database.primary_key])
            pk = f"CompositeKey({cols})"

        context = {
            "class_name": class_name,
            "description": section.description or f"Model for {section.name}",
            "variables": variables_context,
            "extra_imports": extra_imports,
            "database_func": "get_database",
            "table_name": table_name,
            "primary_key": pk,
            "indexes": section.database.indexes if section.database else [],
        }

        return self.env.get_template("peewee_model.jinja").render(context)

    def generate_init(self, sections: list, out_path: Path) -> None:
        """sections_info debe ser una lista de dicts."""
        template = self.env.get_template("init.jinja")

        sections_info = []
        for s in sections:
            master_, class_name = self.generate_module_class_name(s.name)

            sections_info.append({
                "class_name": class_name,
                "module": master_,
            })

        sorted_models = sorted(sections_info, key=lambda x: x["class_name"])

        context = {"models": sorted_models}
        rendered_code = template.render(context)

        file_path = out_path / "__init__.py"
        file_path.write_text(rendered_code, encoding="utf-8")

    def generate_files(self, s: EnvSpec, out: Path, master: Path) -> tuple:
        """Main entry point to generate all Peewee files."""
        sections = [sect for sect in s.sections if sect.type == SectionType.PEEWEE]
        if not sections:
            return None, None

        out.mkdir(parents=True, exist_ok=True)

        # 1. Generate Master (DB Config)
        db_config_code = self.env.get_template("peewee_db.jinja").render()
        master.parent.mkdir(parents=True, exist_ok=True)
        master.write_text(db_config_code, encoding="utf-8")

        for sect in sections:
            master_mod = master.stem

            module_, _ = self.generate_module_class_name(sect.name)

            model_code = self.render_section(sect, master)
            file_name = f"{module_}.py"
            file_path = out / file_name
            file_path.write_text(model_code, encoding="utf-8")

            typer.echo(f"   Model created: {file_path}")

        self.generate_init(sections, out)

        return master, out
