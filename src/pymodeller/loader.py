"""Env-spec loader.

========================================================================================================================
Name:        core/env/loader.py
Description: Parses env_data_model.yaml into typed Pydantic models that represent
             every environment variable defined for the project.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from __future__ import annotations

from enum import StrEnum
from logging import Logger, getLogger
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from pymodeller.utils import get_variants, to_camel_case, to_snake_case

logger: Logger = getLogger(__name__)

DEFAULT_SPEC_PATH: Path = Path("environment.yaml")

BOOL_TRUTHY: frozenset[str] = frozenset({"true", "1", "yes", "on"})
BOOL_FALSY: frozenset[str] = frozenset({"false", "0", "no", "off"})
BOOL_VALUES: frozenset[str] = BOOL_TRUTHY | BOOL_FALSY

# Mapping from raw YAML type strings to normalized Python type names
YAML_TYPE_MAP: dict[str, str] = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "secret": "str",
    "boolean": "bool",
    "object": "object",
    "datetime": "datetime",
    "model": "model",
    "list": "list",
    "dict": "dict",
    "path": "Path",
    "pnd.ndarrayint8": "pnd.NpNDArrayInt8",
    "pnd.ndarrayuint8": "pnd.NpNDArrayUint8",
    "pnd.ndarrayfp32": "pnd.NpNDArrayFp32",
}


class DestinationType(StrEnum):
    """Destination module layer for the generated model."""

    INFRASTRUCTURE = "infrastructure"
    DOMAIN = "domain"


class SectionType(StrEnum):
    """Categorization for environment configuration sections."""

    SETTINGS = "settings"
    MODEL = "model"
    PEEWEE = "peewee"


class DBField(BaseModel):
    """Database column specification for ORM code generation."""

    max_length: int | None = Field(default=None)
    allow_null: bool = False
    index: bool = False
    unique: bool = False
    column_name: str | None = Field(default=None)
    primary_key: bool = False
    constraints: list[str] | None = Field(default=None)
    foreign_key: str | None = Field(default=None)
    backref: str | None = Field(default=None)
    on_delete: str | None = Field(default=None)
    choices: list[str] | None = Field(default=None)
    max_digits: int | None = Field(default=None)
    decimal_places: int | None = Field(default=None)
    default_callable: str | None = Field(default=None)


class DBSpec(BaseModel):
    """Database table-level configuration for Peewee models."""

    primary_key: list[str] | None = Field(default=None)
    table_name: str | None = Field(default=None)
    schema_db: str | None = Field(
        default=None,
        alias="schema",
        description="Database schema name",
    )
    indexes: list[dict[str, Any]] | None = Field(default=None)
    constraints: list[str] | None = Field(default=None)


class EnvVarSpec(BaseModel):
    """Specification for a single environment variable."""

    name: str
    description: str = ""
    type: str = "str"
    default: Any | None = Field(default=None)
    required: bool = False
    secret: bool = False
    from_model: str | None = Field(default=None)
    from_enum: str | None = Field(default=None)
    exclude: bool = False
    section: str = ""
    alias: str = ""
    validation_alias: list[str] | str = ""
    env_name: str = ""
    db_spec: DBField | None = Field(default=None)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Normalize the variable name to snake_case."""
        return to_snake_case(v)

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        """Map generic or YAML type names to standardized Python types."""
        return YAML_TYPE_MAP.get(str(v).lower(), str(v))

    @model_validator(mode="after")
    def compute_derived_fields(self) -> EnvVarSpec:
        """Derive aliases, environmental names, and secret status post-initialization."""
        # 1. Fallback to camelCase alias if not explicitly declared
        if not self.alias:
            self.alias = to_camel_case(self.name)

        # 2. Generate case variations for validation alias if absent
        if not self.validation_alias:
            self.validation_alias = get_variants(self.name)

        # 3. Automatically detect secrets via URI/ARN patterns
        search_prefixes: tuple[str, ...] = ("arn:aws:", "s3://")
        if self.default and isinstance(self.default, str) and any(p in self.default for p in search_prefixes):
            self.secret = True

        # 4. Handle 'secret' sugar syntax (maps to type: str + secret: true)
        if self.type == "secret":
            self.type = "str"
            self.secret = True

        return self

    def display_value(self) -> str:
        """Return a masked or plain default value suitable for documentation output."""
        if self.secret or self.default is None:
            return ""
        return str(self.default)


class EnvSection(BaseModel):
    """A logical grouping of related environment variables."""

    name: str = "Default"
    description: str = "Auto-generated description"
    env_prefix: str = ""
    destination: DestinationType = DestinationType.INFRASTRUCTURE
    type: SectionType = SectionType.MODEL
    include_init_settings: bool = True
    include_general: bool = True
    include_literal: bool = True
    from_attributes: bool = True
    attr: str = ""
    database: DBSpec | None = Field(default=None)
    yaml_file: Path | None = Field(default=None)
    variables: list[EnvVarSpec] = Field(default_factory=list)
    pyproject_toml_table_header: list[str] | None = Field(default=None)

    @field_validator("env_prefix", mode="before")
    @classmethod
    def uppercase_prefix(cls, v: str) -> str:
        """Ensure environmental variable prefix is uppercase."""
        return v.upper() if v else ""

    @field_validator("pyproject_toml_table_header", mode="before")
    @classmethod
    def parse_pyproject_header(cls, v: object) -> list[str] | None:
        """Parse comma-separated string headers into a list of strings."""
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v  # type: ignore[return-value]

    @model_validator(mode="after")
    def propagate_section_to_variables(self) -> EnvSection:
        """Propagate section metadata and environment prefixes down to child variables."""
        prefix: str = self.env_prefix
        for var in self.variables:
            var.section = self.name
            if not var.env_name:
                var.env_name = f"{prefix}_{var.name}" if prefix else var.name
        return self


class EnvSpec(BaseModel):
    """Complete specification container parsed from YAML source files."""

    sections: list[EnvSection] = Field(default_factory=list)

    @property
    def all_vars(self) -> list[EnvVarSpec]:
        """A flattened list of all variable specifications across sections."""
        return [var for section in self.sections for var in section.variables]

    @model_validator(mode="after")
    def validate_no_duplicates(self) -> EnvSpec:
        """Ensure no name collisions exist between env variable keys or Python aliases."""
        seen_env: set[str] = set()

        for sec in self.sections:
            if sec.type != SectionType.SETTINGS:
                continue
            seen_alias: set[str] = set()
            for var in sec.variables:
                if var.env_name in seen_env:
                    raise ValueError(f"Duplicate environment variable name: {var.env_name}")
                if var.alias in seen_alias:
                    raise ValueError(f"Duplicate Python alias: {var.alias}")
                seen_env.add(var.env_name)
                seen_alias.add(var.alias)
        return self


def load_env_spec(path: str | Path | None = None) -> EnvSpec:
    """Load and parse the environment specification file or directory containing YAML specs.

    Args:
        path: Path to a YAML file or directory containing spec files. Defaults to DEFAULT_SPEC_PATH.

    Returns:
        EnvSpec: Fully validated specification model populated from YAML content.

    Raises:
        FileNotFoundError: If the designated spec path does not exist.
        ValueError: If no section definitions were found.
    """
    spec_path: Path = Path(path or DEFAULT_SPEC_PATH)

    if not spec_path.exists():
        raise FileNotFoundError(f"Spec file not found: {spec_path.absolute()}")

    raw_sections: list[dict[str, Any]] = []

    if spec_path.is_dir():
        yaml_files: list[Path] = list(spec_path.glob("*.yaml")) + list(spec_path.glob("*.yml"))
        for file in yaml_files:
            with file.open(encoding="utf-8") as f:
                data: dict[str, Any] = yaml.safe_load(f) or {}
                raw_sections.extend(data.get("models", []))
    else:
        with spec_path.open(encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
            raw_sections = data.get("models", [])

    if not raw_sections:
        raise ValueError("Empty sections")

    return EnvSpec(sections=raw_sections)
