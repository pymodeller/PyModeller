"""Pydantic generator.

========================================================================================================================
Name:         pymodeller/generators/pydantic_generator.py
Description:  Pydantic generator v2.
Project:      PyModeller

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from pathlib import Path

import typer
from jinja2 import Environment, PackageLoader, select_autoescape

from pymodeller.config import DestinationConfig, SourceType, get_code_gen_config
from pymodeller.loader import YAML_TYPE_MAP, EnvSection, EnvSpec, EnvVarSpec, SectionType
from pymodeller.utils import to_pascal_case, to_snake_case

_YAML_HASH_MARKER = "# YAML-SHA256: "
GENERAL = "General"
code_gen_conf = get_code_gen_config()


class PydanticGenerator:
    """Handles Pydantic model generation using Jinja2 templates."""

    def __init__(self, destination_conf: DestinationConfig) -> None:
        """Configura Jinja para leer desde el paquete pymodeller/templates."""
        self.destination_config = destination_conf
        self.env = Environment(loader=PackageLoader("pymodeller", "templates"), autoescape=select_autoescape())
        self.template = self.env.get_template("pydantic_template.jinja")
        self.init_base_path = destination_conf.import_init_base_class
        self.test_dir = destination_conf.test_folder
        self.base_dir = destination_conf.base_dir

    @staticmethod
    def get_python_type(var: EnvVarSpec) -> str:
        """Resolve Pydantic/Python type string."""
        if var.secret:
            return "SecretStr"

        base = YAML_TYPE_MAP.get(var.type, str(var.type))

        if raw_name := (var.from_model or var.from_enum):
            suffix = "Model" if var.from_model else "Enum"
            name = to_pascal_case(to_snake_case(raw_name))
            type_name = f"{name}{suffix}"
            base = f"list[{type_name}]" if var.type == "list" else type_name

        return f"Optional[{base}]" if not var.required and var.default is None else base

    @staticmethod
    def get_default_expr(var: EnvVarSpec) -> str:
        """Generate the default value expression for the Field."""
        if var.required and var.default is None:
            return "..."

        if var.secret:
            return f'default=SecretStr("{var.default or ""}")'

        if var.type == "datetime":
            return "default=datetime.now()"

        if var.type == "Path":
            return f'default=Path("{var.default}")'

        if var.type == "bool":
            return f"default={str(var.default).lower() == 'true'}"

        if isinstance(var.default, (int, float, list, dict)) or var.default in ("[]", "set", "{}"):
            return f"default={var.default}"

        if var.from_model is not None:
            return f"default={var.default}" if var.default else "default=None"

        if var.from_enum is not None and var.default is not None:
            enum_class = f"{to_pascal_case(to_snake_case(var.from_enum))}Enum"
            return f"default={enum_class}.{var.default.upper()}"

        return f'default="{var.default}"' if var.default else "default=None"

    @staticmethod
    def generate_module_class_name(section: EnvSection) -> tuple:
        """Generate module and class names."""
        module_name = to_snake_case(section.name)
        if section.type == SectionType.SETTINGS:
            module_name = "_".join([module_name, SectionType.SETTINGS.value])

        class_name = to_pascal_case(to_snake_case(section.name)) + section.type.capitalize()

        return module_name, class_name

    @staticmethod
    def generate_import(master: Path) -> str:
        """Generate import."""
        parts = master.with_suffix("").parts

        if parts and parts[0] == "src":
            parts = parts[1:]

        return ".".join(parts)

    def render_section(self, section: EnvSection) -> str:
        """Prepares context and renders the Jinja template."""
        variables_context = []

        for var in section.variables:
            variables_context.append({
                "name": var.name,
                "py_type": self.get_python_type(var),
                "default_expr": self.get_default_expr(var),
                "alias": var.alias,
                "validation_alias": var.validation_alias,
                "description": var.description,
                "exclude": var.exclude,
            })
        path_model = self.destination_config.pydantic_model_folder
        path_enum = self.destination_config.enumerations_folder
        extra_imports = []
        for var in section.variables:
            if target := (var.from_model or var.from_enum):
                is_model = bool(var.from_model)
                suffix = "Model" if is_model else "Enum"
                path = path_model if is_model else path_enum

                snake_case = to_snake_case(target)
                class_name = f"{to_pascal_case(snake_case)}{suffix}"
                import_module = ".".join(path.relative_to("src").parts).lstrip(".")

                extra_imports.append(f"from {import_module} import {class_name}")

        _, class_name = self.generate_module_class_name(section)
        literal_name = to_pascal_case(to_snake_case(section.name))
        val_ = tuple(section.pyproject_toml_table_header or ())
        context = {
            "class_name": class_name,
            "import_pydantic_base": self.init_base_path,
            "is_settings": section.type == SectionType.SETTINGS,
            "description": f"Settings for the {section.name} section.",
            "env_prefix": section.env_prefix,
            "from_attributes": section.from_attributes,
            "variables": variables_context,
            "extra_imports": list(set(extra_imports)),
            "pyproject_toml_table_header": val_ if section.pyproject_toml_table_header else None,
            "literal_name": literal_name if (section.include_literal and section.type == SectionType.MODEL) else None,
        }

        return self.template.render(context)

    def _get_import_path(self, base_dir: Path, file_path: Path) -> str:
        """Convierte una ruta de archivo (ej. src/event_driven/infrastructure/config/settings/base_settings.py)
        en una ruta de importación de Python (ej. event_driven.infrastructure.config.settings.base_settings).
        """
        # Elimina la extensión .py
        relative_path = file_path.with_suffix("")

        # Filtra 'src' o '.' si existen en los componentes de la ruta
        parts = [p for p in relative_path.parts if p not in (".", "src")]
        return ".".join(parts)

    def save_template(self, out_path: Path, template_name: str = "", context: dict | None = None) -> None:
        """Save the Jinja template."""
        if not context:
            context = {}

        template = self.env.get_template(f"{template_name}.jinja")

        rendered_code = template.render(context)

        target_dir = out_path / "source" if "source" in template_name.lower() else out_path
        target_dir.mkdir(parents=True, exist_ok=True)

        init_file = target_dir / "__init__.py"
        if not init_file.exists():
            init_file.touch()

        file_path = target_dir / f"{template_name}.py"
        file_path.write_text(rendered_code, encoding="utf-8")

    def generate_base_class(self, out_path: Path) -> None:
        """Generates the static base class needed for tracking."""
        templates = ["base_settings", "source_yaml_env", "source_s3_secrets"]
        str_sources = [source.value for source in code_gen_conf.enabled_sources]
        context_ = {
            "enabled_sources": str_sources,
            "is_yaml": str(SourceType.YAML) in str_sources,
            "env_prefix": code_gen_conf.env_prefix,
        }

        for t in templates:
            context = context_ if t == "base_settings" else {}
            self.save_template(out_path, t, context)

        self.generate_base_settings_test(out_path)

    def generate_base_settings_test(self, out_path: Path) -> None:
        """Generates the test file for BaseTraceableSettings."""
        base_settings_file = out_path / "base_settings.py"

        # Obtener la ruta de importación de Python automáticamente
        import_path = self._get_import_path(self.base_dir, base_settings_file)

        relative_subpath = out_path.relative_to(self.base_dir) if out_path.is_relative_to(self.base_dir) else out_path
        test_target_dir = self.test_dir / relative_subpath
        test_target_dir.mkdir(parents=True, exist_ok=True)

        init_file = test_target_dir / "__init__.py"
        if not init_file.exists():
            init_file.touch()

        template = self.env.get_template("test_base_settings.jinja")
        rendered_code = template.render(import_path=import_path, class_name="BaseTraceableSettings")

        test_file_path = test_target_dir / "test_base_settings.py"
        test_file_path.write_text(rendered_code, encoding="utf-8")

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

        if code_gen_conf.generate_init_models:
            file_path = out_path / "__init__.py"
            file_path.write_text(rendered_code, encoding="utf-8")

    def generate_master(self, sections: list, folder: Path, out_path: Path, yaml_hash: str) -> None:
        """Generate master file."""
        template = self.env.get_template("pydantic_master.jinja")

        sections_context = []
        for s in sections:
            if s.type != SectionType.SETTINGS:
                continue
            master_, class_name = self.generate_module_class_name(s)

            sections_context.append({
                "class_name": class_name,
                "func_name": master_,
                "yaml_file": str(s.yaml_file),
                "include_init_settings": s.include_init_settings,
            })

        context = {
            "models_import_path": self.generate_import(folder),
            "sections": sorted(sections_context, key=lambda x: x["class_name"]),
            "yaml_hash": yaml_hash,
        }
        rendered_code = template.render(context)

        out_path.write_text(rendered_code, encoding="utf-8")

    def generate_general_settings(self, general_section: EnvSection, nested_sections_list: list, out: Path) -> None:
        """Render general settings."""
        template = self.env.get_template("general_settings.jinja")

        imports = []
        path_model = self.destination_config.pydantic_model_folder
        path_enum = self.destination_config.enumerations_folder
        flat_vars = []
        for var in general_section.variables:
            flat_vars.append({
                "name": var.name,
                "py_type": self.get_python_type(var),
                "default_expr": self.get_default_expr(var),
                "alias": var.alias,
                "validation_alias": var.validation_alias,
                "description": var.description,
            })
            if target := var.from_enum:
                is_model = bool(var.from_model)
                suffix = "Model" if is_model else "Enum"
                path = path_model if is_model else path_enum

                snake_case = to_snake_case(target)
                class_name = f"{to_pascal_case(snake_case)}{suffix}"
                import_module = ".".join(path.relative_to("src").parts).lstrip(".")

                imports.append(f"from {import_module} import {class_name}")

        nested_context = []

        for sect in nested_sections_list:
            if not sect.include_general:
                continue
            module_name, class_name = self.generate_module_class_name(sect)

            attr_name = sect.attr if sect.attr else to_snake_case(sect.name)

            nested_context.append({"attr": attr_name, "class_name": class_name})

            imports.append(f"from .{module_name} import {class_name}")

        context = {
            "class_name": "GeneralSettings",
            "import_pydantic_base": self.init_base_path,
            "env_prefix": general_section.env_prefix,
            "from_attributes": general_section.from_attributes,
            "flat_variables": flat_vars,
            "nested_sections": nested_context,
            "imports": imports,
        }
        if code_gen_conf.pyproject_toml_table_header:
            context["pyproject_toml_table_header"] = code_gen_conf.pyproject_toml_table_header

        rendered_code = template.render(context)
        file_path = out / "general_settings.py"

        file_path.write_text(rendered_code, encoding="utf-8")

    @staticmethod
    def check_dir(dir_path: Path) -> Path:
        """Check if dir_path exists."""
        models_dir = Path(dir_path)
        models_dir.mkdir(parents=True, exist_ok=True)
        return models_dir

    def generate_files(self, yaml_hash: str, s: EnvSpec) -> tuple:
        """Generate pydantic files."""
        out_model = self.destination_config.pydantic_model_folder
        out_settings = self.destination_config.pydantic_settings_folder
        master = self.destination_config.pydantic_settings_init

        pydantic_sections_ = [s for s in s.sections if s.type != SectionType.PEEWEE]
        sections = [s for s in pydantic_sections_ if s.destination == self.destination_config.destination_type]

        if len(sections) == 0:
            return None, None

        general_section: EnvSection | None = None
        sections_settings: list[EnvSection | None] = []
        sections_models: list[EnvSection | None] = []

        for sect in sections:
            if sect.name != GENERAL:
                section_str = self.render_section(sect)
                module_name, _ = self.generate_module_class_name(sect)

                dir_ = out_model if sect.type == SectionType.MODEL else out_settings
                adder_section = sections_models if sect.type == SectionType.MODEL else sections_settings
                adder_section.append(sect)
                models_dir = self.check_dir(dir_)

                file_name = module_name + ".py"
                file_path = models_dir / file_name
                file_path.write_text(section_str, encoding="utf-8")
                typer.echo(f"   Model: {file_path}")
            else:
                general_section = sect if sect.destination == self.destination_config.destination_type else None

        if general_section:
            self.generate_general_settings(general_section, sections_settings, out_settings)

        if len(sections_settings) > 0:
            sections_settings.append(general_section)
            if master:
                self.generate_master(sections_settings, out_settings, master, yaml_hash)
                typer.echo(f"   Out: {master}")
            self.generate_init(sections_settings, out_settings)
            if not self.init_base_path and len(sections_settings) > 0:
                self.generate_base_class(out_settings)

        if len(sections_models) > 0:
            self.generate_init(sections_models, out_model)

        typer.echo(f"   Out: {out_model}")

        return out_model, out_settings, master
