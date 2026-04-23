"""Pydantic generator v2."""

from pathlib import Path

import typer
from jinja2 import Environment, PackageLoader, select_autoescape

from pymodeller.loader import YAML_TYPE_MAP, EnvSection, EnvSpec, EnvVarSpec, SectionType
from pymodeller.utils import to_snake_case

_YAML_HASH_MARKER = "# YAML-SHA256: "


class PydanticGenerator:
    """Handles Pydantic model generation using Jinja2 templates."""

    def __init__(self) -> None:
        """Configura Jinja para leer desde el paquete pymodeller/templates."""
        self.env = Environment(loader=PackageLoader("pymodeller", "templates"), autoescape=select_autoescape())
        self.template = self.env.get_template("pydantic_template.jinja")

    @staticmethod
    def get_python_type(var: EnvVarSpec) -> str:
        """Resolve Pydantic/Python type string."""
        if var.secret:
            return "SecretStr"

        # Mapping simple
        base = YAML_TYPE_MAP.get(var.type, "str")

        if var.from_model:
            model_name = f"{var.from_model.capitalize()}Model"
            base = f"list[{model_name}]" if var.type == "list" else model_name

        return f"Optional[{base}]" if not var.required and var.default is None else base

    @staticmethod
    def get_default_expr(var: EnvVarSpec) -> str:
        """Generate the default value expression for the Field."""
        if var.secret:
            return f'default=SecretStr("{var.default or ""}")'
        if var.type == "Path":
            return f'default=Path("{var.default}")'
        if var.required and var.default is None:
            return "..."
        if var.type == "bool":
            return f"default={str(var.default).lower() == 'true'}"
        if isinstance(var.default, (int, float)):
            return f"default={var.default}"

        return f'default="{var.default}"' if var.default is not None else "default=None"

    @staticmethod
    def generate_module_class_name(section: EnvSection) -> tuple:
        """Generate module and class names."""
        module_name = to_snake_case(section.name)
        if section.type == SectionType.SETTINGS:
            module_name = "_".join([module_name, SectionType.SETTINGS.value])

        class_name = "".join(word.title() for word in section.name.split()) + section.type.capitalize()

        return module_name, class_name

    @staticmethod
    def generate_import(master: Path) -> str:
        """Generate import."""
        parts = master.with_suffix("").parts

        if parts and parts[0] == "src":
            parts = parts[1:]

        return ".".join(parts)

    def render_section(self, section: EnvSection, yaml_hash: str = "") -> str:
        """Prepares context and renders the Jinja template."""
        # Preparar variables para el template
        variables_context = []

        for var in section.variables:
            variables_context.append({
                "name": var.name,
                "py_type": self.get_python_type(var),
                "default_expr": self.get_default_expr(var),
                "alias": var.alias,
                "validation_alias": var.validation_alias,
                "description": var.description,
            })

        # Preparar imports extra (modelos anidados)
        extra_imports = []
        for var in section.variables:
            if var.from_model:
                from pymodeller.utils import to_snake_case

                extra_imports.append(f"from .{to_snake_case(var.from_model)} import {var.from_model.capitalize()}Model")

        _, class_name = self.generate_module_class_name(section)

        # Contexto final
        context = {
            "yaml_hash": yaml_hash,
            "class_name": class_name,
            "is_settings": section.type == SectionType.SETTINGS,
            "description": f"Settings for the {section.name} section.",
            "env_prefix": section.env_prefix,
            "from_attributes": section.from_attributes,
            "variables": variables_context,
            "extra_imports": list(set(extra_imports)),
            "literal_name": section.name if (section.include_literal and section.type == SectionType.MODEL) else None,
        }

        return self.template.render(context)

    def generate_base_class(self, out_path: Path) -> None:
        """Generates the static base class needed for tracking."""
        # Cargamos el template estático
        template = self.env.get_template("base_settings.jinja")

        # Renderizamos sin variables (o con valores por defecto)
        rendered_code = template.render()

        # Lo guardamos como base_settings.py en el destino
        file_path = out_path / "base_settings.py"
        file_path.write_text(rendered_code, encoding="utf-8")

    def generate_init(self, sections: list, out_path: Path) -> None:
        """sections_info debe ser una lista de dicts."""
        template = self.env.get_template("init.jinja")

        sections_info = []
        for s in sections:
            master_, class_name = self.generate_module_class_name(s)

            sections_info.append({
                "class_name": class_name,
                "module": master_,
            })

        sorted_models = sorted(sections_info, key=lambda x: x["class_name"])

        context = {"models": sorted_models}
        rendered_code = template.render(context)

        file_path = out_path / "__init__.py"
        file_path.write_text(rendered_code, encoding="utf-8")

    def generate_master(self, sections: list, folder: Path, out_path: Path, yaml_hash: str) -> None:
        """Generate master file."""
        template = self.env.get_template("master_pydantic.jinja")

        sections_context = []
        for s in sections:
            if s.type != SectionType.SETTINGS:
                continue
            master_, class_name = self.generate_module_class_name(s)

            sections_context.append({
                "class_name": class_name,
                "func_name": master_,
                "yaml_file": s.yaml_file,
            })

        context = {
            "models_import_path": self.generate_import(folder),  # O el path que corresponda
            "sections": sorted(sections_context, key=lambda x: x["class_name"]),
            "yaml_hash": yaml_hash,
        }
        rendered_code = template.render(context)

        out_path.write_text(rendered_code, encoding="utf-8")

    def generate_general_settings(self, general_section: EnvSection, nested_sections_list: list, out: Path) -> None:
        """Render general settings."""
        template = self.env.get_template("general_settings.jinja")

        flat_vars = []
        for var in general_section.variables:
            flat_vars.append({
                "name": var.name,
                "py_type": self.get_python_type(var),  # Usamos el método que ya definimos
                "default_expr": self.get_default_expr(var),
                "alias": var.alias,
                "validation_alias": var.validation_alias,
                "description": var.description,
            })

        nested_context = []
        imports = []

        for sect in nested_sections_list:
            if not sect.include_general:
                continue
            module_name, class_name = self.generate_module_class_name(sect)

            attr_name = sect.attr if sect.attr else to_snake_case(sect.name)

            nested_context.append({"attr": attr_name, "class_name": class_name})

            imports.append(f"from .{module_name} import {class_name}")

        # 3. Renderizar
        context = {
            "class_name": "GeneralSettings",
            "env_prefix": general_section.env_prefix,
            "from_attributes": general_section.from_attributes,
            "flat_variables": flat_vars,
            "nested_sections": nested_context,
            "imports": imports,
        }

        rendered_code = template.render(context)
        file_path = out / "general_settings.py"

        file_path.write_text(rendered_code, encoding="utf-8")

    def generate_files(self, yaml_hash: str, s: EnvSpec, out: Path, master: Path) -> tuple:
        """Generate pydantic files."""
        sections = [s for s in s.sections if s.type != SectionType.PEEWEE]

        if len(sections) == 0:
            return None, None

        models_dir = Path(out)
        models_dir.mkdir(parents=True, exist_ok=True)

        general_section: EnvSection = EnvSection("General")
        sections_with_classes: list[EnvSection] = []

        for sect in sections:
            if sect.name != "General":
                section_str = self.render_section(sect, yaml_hash)
                sections_with_classes.append(sect)
                module_name, _ = self.generate_module_class_name(sect)

                file_name = module_name + ".py"
                file_path = models_dir / file_name
                file_path.write_text(section_str, encoding="utf-8")
                typer.echo(f"   Model: {file_path}")
            else:
                general_section = sect

        self.generate_general_settings(general_section, sections_with_classes, out)
        self.generate_init(sections, out)
        self.generate_base_class(out)
        self.generate_master(sections, out, master, yaml_hash)

        typer.echo(f"   Out: {out}")
        typer.echo(f"   Out: {master}")
        return out, master
