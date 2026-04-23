"""Env-spec loader.

========================================================================================================================
Name:         core/env/loader.py
Description:  Parses env_data_model.yaml into typed Python dataclasses that represent
              every environment variable defined for the project.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from logging import getLogger
from pathlib import Path

import yaml

from pymodeller.utils import get_variants, to_camel_case, to_snake_case

logger = getLogger(__name__)

# Default location of the spec file
DEFAULT_SPEC_PATH = Path("env_data_model.yaml")
_PND_UINT8 = "pnd.NpNDArrayUint8"
_PND_INT8 = "pnd.NpNDArrayInt8"
_PND_F32 = "pnd.NpNDArrayFp32"
_PATH = "Path"
_FLOAT = "float"
_INT = "int"
_STR = "str"
_BOOL = "bool"

# Single source of truth for YAML type -> Python type name normalization
YAML_TYPE_MAP: dict[str, str] = {
    "string": _STR,
    "integer": _INT,
    "number": _FLOAT,
    "secret": _STR,  # Normalized to str + secret flag in __post_init__
    "boolean": _BOOL,
    "object": "object",
    "datetime": "datetime",
    "model": "model",
    "list": "list",
    _STR: _STR,
    _INT: _INT,
    _FLOAT: _FLOAT,
    _BOOL: _BOOL,
    _PATH.lower(): _PATH,
    _PATH: _PATH,
    _PND_INT8: _PND_INT8,
    _PND_UINT8: _PND_UINT8,
    _PND_F32: _PND_F32,
    _PND_INT8.lower(): _PND_INT8,
    _PND_UINT8.lower(): _PND_UINT8,
    _PND_F32.lower(): _PND_F32,
}

BOOL_TRUTHY: frozenset[str] = frozenset({"true", "1", "yes", "on"})
BOOL_FALSY: frozenset[str] = frozenset({"false", "0", "no", "off"})
BOOL_VALUES: frozenset[str] = BOOL_TRUTHY | BOOL_FALSY


class SectionType(StrEnum):
    """Section type."""

    SETTINGS = "settings"
    MODEL = "model"
    PEEWEE = "peewee"


@dataclass(frozen=True)
class DBSpec:
    """Configuración específica para Peewee/DB."""

    primary_key: list[str] | None = None  # Lista de nombres de campos
    table_name: str | None = None
    schema: str | None = None
    indexes: list[dict] | None = None
    constraints: list[str] | None = None


@dataclass(frozen=True)
class DBField:
    """Configuración específica para entrada."""

    max_length: int | None = None
    allow_null: bool = False
    index: bool = False
    unique: bool = False
    column_name: str | None = None

    primary_key: bool = False
    constraints: list[str] | None = None

    foreign_key: str | None = None
    backref: str | None = None
    on_delete: str | None = None

    choices: list[str] | None = None

    max_digits: int | None = None
    decimal_places: int | None = None

    default_callable: str | None = None


@dataclass(frozen=True)
class EnvVarSpec:
    """Specification for a single environment variable."""

    name: str
    description: str = ""
    type: str = "str"
    default: str | None = None
    required: bool = False
    secret: bool = False
    from_model: str | None = None
    section: str = ""
    alias: str = ""
    validation_alias: str = ""
    env_name: str = ""  # Final ENV var name (e.g., SERVER__HOST)
    db_spec: DBField | None = None

    def __post_init__(self) -> None:
        """Derive alias and handle secret type sugar."""
        # Auto-generate camelCase alias if not provided
        if not self.alias:
            object.__setattr__(self, "alias", to_camel_case(self.name))

        # 'secret' type is a shortcut for type: str + secret: true
        if self.type == "secret":
            object.__setattr__(self, "type", "str")
            object.__setattr__(self, "secret", True)

    def display_value(self) -> str:
        """Return a masked or real default value for documentation purposes."""
        if self.secret:
            return ""
        return str(self.default) if self.default is not None else ""


@dataclass
class EnvSection:
    """A named group of environment variables."""

    name: str
    description: str = ""
    env_prefix: str = ""
    type: SectionType = SectionType.SETTINGS
    include_general: bool = True
    from_attributes: bool = True
    attr: str = ""
    database: DBSpec | None = None
    yaml_file: Path | None = None
    include_literal: bool = False  # This is for fastapi
    variables: list[EnvVarSpec] = field(default_factory=list)


@dataclass
class EnvSpec:
    """Full specification parsed from the YAML file."""

    sections: list[EnvSection] = field(default_factory=list)

    @property
    def all_vars(self) -> list[EnvVarSpec]:
        """Flat list of all variable specifications."""
        return [var for section in self.sections for var in section.variables]

    def validate_no_duplicates(self) -> None:
        """Ensure no collisions between environment names or Python aliases."""
        seen_env: set[str] = set()

        for sec in self.sections:
            seen_alias: set[str] = set()
            for var in sec.variables:
                if var.env_name in seen_env:
                    raise ValueError(f"Duplicate environment variable name: {var.env_name}")
                if var.alias in seen_alias:
                    raise ValueError(f"Duplicate Python alias: {var.alias}")
                seen_env.add(var.env_name)
                seen_alias.add(var.alias)


def load_env_spec(path: str | Path | None = None) -> EnvSpec:
    """Load and parse the env_spec YAML file."""
    spec_path = Path(path or DEFAULT_SPEC_PATH)

    if not spec_path.exists():
        raise FileNotFoundError(f"Spec file not found: {spec_path.absolute()}")

    with spec_path.open(encoding="utf-8") as f:
        raw_data = yaml.safe_load(f) or {}

    raw_sections: list | None = raw_data.get("sections", None)

    if not raw_sections:
        raise ValueError("Empty sections")

    parsed_sections = []

    for raw_sec in raw_sections:
        sec_name = raw_sec.get("name", "Default")
        prefix = raw_sec.get("env_prefix", "").upper()

        # Parse variables within the section
        vars_list = []
        for v in raw_sec.get("variables", []):
            raw_name = v["name"]
            env_name = f"{prefix}_{raw_name}" if prefix else raw_name

            db_finfo = v.get("db_spec", None)
            db_f_ = DBField(**db_finfo) if db_finfo else None

            type_ = YAML_TYPE_MAP.get(str(v.get("type", "str")).lower(), "str")
            vars_list.append(
                EnvVarSpec(
                    name=to_snake_case(raw_name),
                    description=v.get("description", ""),
                    from_model=v.get("from_model", None),
                    type=type_,
                    default=v.get("default"),
                    required=bool(v.get("required", False)),
                    secret=bool(v.get("secret", False)),
                    section=sec_name,
                    alias=v.get("alias", ""),
                    db_spec=db_f_,
                    validation_alias=get_variants(raw_name),
                    env_name=env_name,
                )
            )

        db_info = raw_sec.get("database", None)
        db_ = DBSpec(**db_info) if db_info else None

        parsed_sections.append(
            EnvSection(
                name=sec_name,
                description=raw_sec.get("description", "Auto-generated description"),
                include_general=raw_sec.get("include_general", True),
                include_literal=raw_sec.get("include_literal", True),
                yaml_file=raw_sec.get("yaml_file", None),
                from_attributes=raw_sec.get("from_attributes", True),
                env_prefix=prefix,
                variables=vars_list,
                type=SectionType(raw_sec.get("type", SectionType.MODEL.value)),
                database=db_,
            )
        )

    spec = EnvSpec(sections=parsed_sections)
    spec.validate_no_duplicates()
    return spec
