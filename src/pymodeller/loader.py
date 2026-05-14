"""Env-spec loader.

========================================================================================================================
Name:         core/env/loader.py
Description:  Parses env_data_model.yaml into typed Python dataclasses that represent
              every environment variable defined for the project.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from __future__ import annotations

from enum import StrEnum
from logging import getLogger
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator

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
_ANY = "Any"

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
    "dict": "dict",
    _ANY.lower(): _ANY,
    _ANY: _ANY,
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


class ValidationSpec(BaseModel):
    """Validation spec."""

    min_value: float | int | None = None
    max_value: float | int | None = None
    pattern: str | None = None
    min_length: int | None = None
    max_length: int | None = None
    enum: list[str] | None = None
    error_message: str = "Error message"


class DBSpec(BaseModel):
    """Configuration for Peewee/DB."""

    primary_key: list[str] | None = None
    table_name: str | None = None
    schema_name: str | None = Field(None, alias="schema")
    indexes: list[dict] | None = None
    constraints: list[str] | None = None


class DBField(BaseModel):
    """Configuration for para entrada."""

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


class EnvVarSpec(BaseModel):
    """Env vars spec."""

    name: str
    description: str = ""
    type: str = "str"
    default: Any = None
    required: bool = False
    secret: bool = False
    from_model: str | None = None
    exclude: bool = False
    section: str = ""
    alias: str = ""
    validation_alias: Any = None
    env_name: str = ""
    db_spec: DBField | None = None
    validation: ValidationSpec | None = None

    @model_validator(mode="before")
    @classmethod
    def pre_process_names(cls, data: dict) -> dict:
        """Preprocess names."""
        raw_name = data.get("name")
        if raw_name:
            data["name"] = to_snake_case(raw_name)
            if not data.get("alias"):
                data["alias"] = to_camel_case(raw_name)
            if not data.get("validation_alias"):
                data["validation_alias"] = get_variants(raw_name)

        if data.get("type") == "secret":
            data["type"] = "str"
            data["secret"] = True

        data["type"] = YAML_TYPE_MAP.get(str(data.get("type", "str")).lower(), "str")

        return data

    def display_value(self) -> str:
        """Return a masked or real default value for documentation purposes."""
        if self.secret:
            return ""
        return str(self.default) if self.default is not None else ""


class EnvSection(BaseModel):
    """A named group of environment variables."""

    name: str = "Default"
    description: str = "Auto-generated description"
    env_prefix: str = ""
    type: SectionType = SectionType.MODEL
    include_init_settings: bool = True
    include_general: bool = True
    attr: str = ''
    from_attributes: bool = True
    database: DBSpec | None = None
    yaml_file: Path | None = None
    include_literal: bool = True
    variables: list[EnvVarSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def propagate_section_context(self) -> EnvSection:
        """Name and prefix injection."""
        prefix = self.env_prefix.upper()
        for var in self.variables:
            var.section = self.name
            if not var.env_name:
                var.env_name = f"{prefix}_{var.name.upper()}" if prefix else var.name.upper()
        return self


class EnvSpec(BaseModel):
    """Full specification parsed from the YAML file."""

    sections: list[EnvSection] = Field(default_factory=list)

    @property
    def all_vars(self) -> list[EnvVarSpec]:
        """Flat list of all variable specifications."""
        return [var for section in self.sections for var in section.variables]

    @model_validator(mode="after")
    def validate_no_duplicates(self) -> EnvSpec:
        """Validation."""
        seen_env: set[str] = set()
        for sec in self.sections:
            if sec.type != SectionType.SETTINGS:
                continue
            seen_alias: set[str] = set()
            for var in sec.variables:
                if var.env_name in seen_env:
                    raise ValueError(f"Duplicate env: {var.env_name}")
                if var.alias in seen_alias:
                    raise ValueError(f"Duplicate alias: {var.alias}")
                seen_env.add(var.env_name)
                seen_alias.add(var.alias)
        return self


def load_env_spec(path: str | Path | None = None) -> EnvSpec:
    """Load env spec."""
    spec_path = Path(path or "models.yaml")

    if not spec_path.exists():
        raise FileNotFoundError(f"Spec file not found: {spec_path.absolute()}")

    files = [spec_path] if spec_path.is_file() else spec_path.glob("*.yaml")
    raw_data = {"sections": []}

    for f in files:
        with f.open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream) or {}
            raw_data["sections"].extend(data.get("sections", []))

    if not raw_data["sections"]:
        raise ValueError("No sections found in YAML")

    return EnvSpec(**raw_data)
