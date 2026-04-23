"""Code generator."""

from pathlib import Path

import typer

from pymodeller.config import get_code_gen_config
from pymodeller.loader import YAML_TYPE_MAP, EnvSection, EnvSpec, EnvVarSpec, SectionType
from pymodeller.utils import to_snake_case

code_gen_conf = get_code_gen_config()
_YAML_HASH_MARKER = "# YAML-SHA256: "


class PydanticGenerator:
    """Handles Pydantic model generation (Code-gen)."""

    @staticmethod
    def build_header_files(yaml_hash: str | None = None, extra_lines: list | None = None) -> list[str]:
        """Generate the header for auto-generated files."""
        headers = [
            "from pathlib import Path",
            "from pydantic import AliasChoices, Field, SecretStr, BaseModel, ConfigDict, PrivateAttr, model_validator",
            "from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource",
            "from functools import lru_cache",
            "from datetime import datetime",
            "import pydantic_numpy.typing as pnd",
            "from typing import Any, Literal, Callable",
            "import glob",
        ]

        if extra_lines:
            headers = headers + extra_lines

        if yaml_hash:
            headers.insert(0, f"{_YAML_HASH_MARKER}{yaml_hash}")

        return [
            '"""Auto-generated settings from YAML spec."""',
            "",
            *headers,
            "",
        ]

    @staticmethod
    def capitalize(name: str) -> str:
        """Just capitalize."""
        return "".join(word.title() for word in name.split())

    @staticmethod
    def generate_name(name: str, type_: str) -> str:
        """Generate name."""
        return PydanticGenerator.capitalize(name) + type_.capitalize()

    @staticmethod
    def _section_class_name(section: EnvSection) -> str:
        """Convert a section name to a PascalCase class name, e.g. 'API Service' → 'ApiServiceSettings'."""
        return PydanticGenerator.generate_name(section.name, section.type)

    @staticmethod
    def get_python_type(var: EnvVarSpec) -> str:
        """Resolve Pydantic/Python type string."""
        if var.secret:
            return "SecretStr"
        base = YAML_TYPE_MAP.get(var.type, "str")
        if base in ["object", "model"] and var.from_model:
            base = "".join([var.from_model.capitalize(), "Model"])
        return f"{base} | None" if not var.required and var.default is None else base

    @staticmethod
    def format_field(var: EnvVarSpec) -> str:
        """Generate a single Pydantic Field line."""
        py_type = PydanticGenerator.get_python_type(var)

        # Handle default values based on type
        if var.secret:
            val = f'SecretStr("{var.default}")' if var.default else "SecretStr('')"
            default_expr = f"default={val}"
        elif var.type == "Path":
            default_expr = f'default=Path("{var.default}")'
        elif var.required and var.default is None:
            default_expr = "..."
        elif var.type == "bool":
            default_expr = f"default={str(var.default).lower() in {'true', '1'}}"
        elif var.type in ("int", "float") and var.default is not None:
            default_expr = f"default={var.default}"
        else:
            default_expr = f'default="{var.default}"' if var.default is not None else "default=None"

        if var.from_model and var.type not in ["object", "model"]:
            py_type = "".join([py_type, "[", var.from_model.capitalize(), "Model]"])

        return (
            f"    {var.name}: {py_type} = Field(\n"
            f"        {default_expr}, \n"
            f'        alias="{var.alias}", \n'
            f"        validation_alias={var.validation_alias}, \n"
            f'        description="{var.description}",\n'
            f"    )"
        )

    @staticmethod
    def codegen_section(section: EnvSection) -> list:
        """Return lines for a single BaseSettings subclass."""
        class_name = PydanticGenerator._section_class_name(section)
        class_base = "BaseSettings" if section.type == SectionType.SETTINGS else "BaseModel"

        options = [
            f"        from_attributes={section.from_attributes},",
            '        extra="ignore",',
            "        populate_by_name=True,",
            "    )",
        ]

        model_config_settings = [
            "    _metadata_origins: dict[str, str] = PrivateAttr(default_factory=dict)",
            "",
            "    model_config = SettingsConfigDict(",
            '        env_file=".env",',
            '        env_file_encoding="utf-8",',
            "        env_ignore_empty=True,",
            f'        env_prefix="{section.env_prefix}_",',
            '        env_nested_delimiter="__",',
            "        case_sensitive=False,",
            '        env_prefix_target="all",',
            *options,
        ]

        model_config_base = [
            "    model_config = ConfigDict(",
            *options,
        ]

        model_config = model_config_settings if section.type == SectionType.SETTINGS else model_config_base

        extra_lines = PydanticGenerator.generate_extra_imports(section)

        generate_content = [PydanticGenerator.format_field(var) for var in section.variables]

        headers = PydanticGenerator.build_header_files(extra_lines=extra_lines)

        literal_: str | None = (
            PydanticGenerator.generate_literal(section.name)
            if section.include_literal and section.type == SectionType.MODEL
            else None
        )

        lines = [
            *headers,
            "",
            f"class {class_name}({class_base}):",
            f'    """Settings for the {section.name} section."""',
            "",
        ]

        if literal_:
            lines.append(f"    {literal_}")
            lines.append("")

        # 4. Continue with the rest of the class body
        lines.extend([
            *model_config,
            "",
            *generate_content,
        ])

        if section.type == SectionType.SETTINGS:
            lines.extend(PydanticGenerator.generate_sources_funcs())

        return lines

    @staticmethod
    def generate_sources_funcs() -> list:
        """Generate sources functions."""
        return [
            "",
            '    @model_validator(mode="before")',
            "    @classmethod",
            "    def _prepare_metadata(cls, data: Any) -> Any:",
            '        """ Intercept data origin and save. """',
            '        if isinstance(data, dict) and "_metadata_origins" in data:',
            '            cls._metadata_origins = data.pop("_metadata_origins")',
            "            return data",
            "        return data",
            "",
            "    @classmethod",
            "    def settings_customise_sources(",
            "        cls,",
            "        settings_cls: PydanticBaseSettingsSource,",
            "        init_settings: PydanticBaseSettingsSource,",
            "        env_settings: PydanticBaseSettingsSource,",
            "        dotenv_settings: PydanticBaseSettingsSource,",
            "        file_secret_settings: PydanticBaseSettingsSource,",
            "    ) -> tuple:",
            '        """Settings customise sources. """',
            "        return (",
            '            track_source(init_settings, "init / yaml"),',
            '            track_source(env_settings, "env"),',
            '            track_source(dotenv_settings, "dotenv"),',
            '            track_source(file_secret_settings, "file_secret"),',
            "        )",
            "",
            "    def get_origin(self, field_path: str) -> str:",
            '        """Get origin variable."""',
            '        return self._metadata_origins.get(field_path, "Unknown")',
            "",
            "",
            'def track_origin(data: dict, origin: str, prefix: str = "",',
            "                 registry: dict | None = None) -> dict[str, str]:",
            '    """ Get data a register the origin. """',
            "    if registry is None:",
            "        registry = {}",
            "",
            "    for key, value in data.items():",
            '        path = f"{prefix}.{key}" if prefix else key',
            "        ",
            "        if isinstance(value, dict):",
            "            track_origin(value, origin, path, registry)",
            "        else:",
            "            if path not in registry:",
            "                registry[path] = origin",
            "                ",
            "    return registry",
            "",
            "",
            "def track_source(source: PydanticBaseSettingsSource, origin: str) -> Any:",
            '    """ Wrapper to save data origins. """',
            "    def wrapper() -> dict[str, Any]:",
            '        """Wrapper. """',
            "        data = source()",
            "        result = dict(data)",
            "        if result:",
            '            result["_metadata_origins"] = track_origin(data, origin)',
            "        return result",
            "    return wrapper",
            "",
        ]

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
    def generate_init_import(section: EnvSection) -> str:
        """Generate init imports."""
        class_name = PydanticGenerator._section_class_name(section)
        name = to_snake_case(section.name)
        if section.type == SectionType.SETTINGS:
            name = "_".join([name, SectionType.SETTINGS.value])
        return f"from .{name} import {class_name}"

    @staticmethod
    def generate_extra_imports(section: EnvSection) -> list | None:
        """Generate imports."""
        variables_ = [v for v in section.variables if v.from_model]
        extra_imports = [""]
        for v in variables_:
            name = to_snake_case(v.from_model or "")
            model_name = PydanticGenerator.capitalize(v.from_model or "")
            extra_imports.append(f"from .{name} import {model_name}Model")

        return extra_imports if len(extra_imports) > 1 else None

    @staticmethod
    def generate_literal(name: str) -> str:
        """Generate literal string for fastmcp."""
        return f'type: Literal["{name}"] = Field(default="{name}", exclude=True)'

    @staticmethod
    def generate_setting_getter(model_name: str, yaml_file: Path | None = None) -> list[str]:
        """Generate a cached getter function for a settings model."""
        model_name = model_name.replace("\n", "")
        func_name = f"get_{to_snake_case(model_name)}"

        getter_lines = [
            "@lru_cache(maxsize=1)",
            f"def {func_name}() -> {model_name}:",
            f'    """Return the cached application settings instance y {yaml_file or ""}."""',
        ]

        if yaml_file and "*" in str(yaml_file):
            getter_lines.extend([
                f'    path_obj = Path("{yaml_file}")',
                "    search_dir = path_obj.parent",
                "    search_pattern = path_obj.name",
                "    ",
                "    item_list = []",
                "    for file_path in sorted(search_dir.glob(search_pattern)):",
                "        data = _read_yaml(file_path) or {}",
                "        data['name'] = file_path.stem",
                "        item_list.append(data)",
                "    ",
                "    values = {'items': item_list}",
            ])
            getter_lines.extend([f"    return {model_name}.model_validate(values)", "", ""])
        elif yaml_file:
            getter_lines.extend([
                f'    values = _read_yaml(Path("{yaml_file}"))',
            ])

            getter_lines.extend([f"    return {model_name}.model_validate(values)", "", ""])
        else:
            getter_lines.extend([f"    return {model_name}()", "", ""])

        return getter_lines

    @staticmethod
    def codegen_app_settings(
        general_section: EnvSection, sections_with_classes: list[EnvSection], out: Path, models_dir: Path
    ) -> list[str]:
        """Return the root AppSettings class that composes all section classes."""
        lines = [
            *PydanticGenerator.build_header_files(),
            "",
            "",
            "class GeneralSettings(BaseSettings):",
            '    """Root application settings. Composes all section settings."""',
            "",
            "    model_config = SettingsConfigDict(",
            f"        from_attributes={general_section.from_attributes},",
            '        env_file=".env",',
            '        env_file_encoding="utf-8",',
            f'        env_prefix="{general_section.env_prefix}",',
            "        env_ignore_empty=True,",
            '        env_nested_delimiter="__",',
            "        case_sensitive=False,",
            '        extra="ignore",',
            "        populate_by_name=True,",
            '        env_prefix_target="all",',
            "    )",
            "",
        ]

        # flat vars (sections without env_prefix, e.g. General, Artifactory, AWS…)
        for var in general_section.variables:
            lines.append(PydanticGenerator.format_field(var))

        imports_headers = []
        init_imports = [PydanticGenerator.generate_init_import(general_section)]
        all_imports = [f'"{PydanticGenerator._section_class_name(general_section)}"\n']
        lru_caches_funcs = []

        # nested section instances
        for section in sections_with_classes:
            attr = section.attr if section.attr else section.name.lower().replace(" ", "_")
            class_name = PydanticGenerator._section_class_name(section)

            init_imports.append(PydanticGenerator.generate_init_import(section))
            all_imports.append(f'"{class_name}"\n')

            if section.type == SectionType.SETTINGS:
                lru_caches_funcs.extend(PydanticGenerator.generate_setting_getter(class_name, section.yaml_file))

            if not section.include_general:
                continue

            lines.append(f"    {attr}: {class_name} = Field(default_factory={class_name})")

            imports_headers.append(f"from . import {class_name}")

        PydanticGenerator.codegen_init(init_imports, all_imports, out)

        lines[1:1] = [i for i in init_imports if "generalsettings" not in i.lower()]

        name = to_snake_case(general_section.name)
        if general_section.type == SectionType.SETTINGS:
            name = "_".join([name, SectionType.SETTINGS.value])

        # Nombre del archivo en snake_case
        file_name = name + ".py"
        file_path = models_dir / file_name

        file_path.write_text("\n".join(lines), encoding="utf-8")

        parts = code_gen_conf.pydantic_folder.parts

        if parts and parts[0] == "src":
            parts = parts[1:]

        result = ".".join(parts)

        models_settings = [c.replace('"', "") for c in all_imports if "settings" in c.lower()]

        models_ = ",".join(models_settings)

        singleton_lines = [
            *imports_headers,
            f"from {result} import ({models_})",
            "import yaml",
            "",
            "",
            "def _read_yaml(config_path: Path) -> dict:",
            '    """Read YAML file safely."""',
            "    if not config_path.is_file():",
            "        return {}",
            "",
            '    with open(config_path, "r", encoding="utf-8") as f:',
            "        return yaml.safe_load(f) or {}",
            "",
            "",
            *lru_caches_funcs,
        ]
        return singleton_lines

    @staticmethod
    def generate_files(yaml_hash: str, s: EnvSpec, out: Path, master: Path) -> tuple:
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
                section_lines = PydanticGenerator.codegen_section(sect)
                sections_with_classes.append(sect)

                name = to_snake_case(sect.name)
                if sect.type == SectionType.SETTINGS:
                    name = "_".join([name, SectionType.SETTINGS.value])

                # Nombre del archivo en snake_case
                file_name = name + ".py"
                file_path = models_dir / file_name

                file_path.write_text("\n".join(section_lines), encoding="utf-8")
                typer.echo(f"   Model: {file_path}")
            else:
                general_section = sect

        lines = PydanticGenerator.build_header_files(yaml_hash)
        lines.extend(PydanticGenerator.codegen_app_settings(general_section, sections_with_classes, out, models_dir))

        out_path = Path(master)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines), encoding="utf-8")
        typer.echo(f"   Out: {out_path}")
        return out_path, models_dir
