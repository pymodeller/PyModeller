"""Config file.

========================================================================================================================
Name:         pymodeller/config.py
Description:  Load configuration.
Project:      PyModeller

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    PyprojectTomlConfigSettingsSource,
    SettingsConfigDict,
)

from pymodeller.loader import DestinationType


class SourceType(StrEnum):
    """Source type."""

    YAML = "yaml"
    S3 = "s3"


class DestinationConfig(BaseModel):
    """Output path configuration for a specific model type (e.g., infrastructure, domain)."""

    import_init_base_class: Path | None = None

    destination_type: DestinationType = DestinationType.INFRASTRUCTURE

    pydantic_model_folder: Path = Path("infraestructure/config/schemas")
    pydantic_settings_folder: Path = Path("infrastructure/config/settings")
    pydantic_settings_init: Path | None = Path("infrastructure/config/init_settings.py")

    peewee_folder: Path = Path("persistence/models")
    peewee_out: Path = Path("persistence/connection.py")

    base_dir: Path = Path("./src")
    test_folder: Path = Path("tests")

    exceptions_folder: Path = Path("exceptions")
    enumerations_folder: Path = Path("enumerations")

    def resolve_paths(self, base_dir: Path, test_dir: Path, destination_type: DestinationType) -> "DestinationConfig":
        """Resolve relative paths by prepending the project base directory."""
        return DestinationConfig(
            destination_type=destination_type,
            pydantic_model_folder=base_dir / destination_type / self.pydantic_model_folder,
            pydantic_settings_folder=base_dir / destination_type / self.pydantic_settings_folder,
            pydantic_settings_init=(
                base_dir / destination_type / self.pydantic_settings_init if self.pydantic_settings_init else None
            ),
            peewee_folder=base_dir / destination_type / self.peewee_folder,
            peewee_out=base_dir / destination_type / self.peewee_out,
            exceptions_folder=base_dir / destination_type / self.exceptions_folder,
            test_folder=test_dir,
            base_dir=base_dir,
            enumerations_folder=base_dir / destination_type / self.enumerations_folder,
        )


class CodegenConfig(BaseSettings):
    """Main configuration model for code generation."""

    model_config = SettingsConfigDict(
        pyproject_toml_table_header=("tool", "pymodeller"),
        extra="ignore",
    )

    base_dir: Path = Field(
        default=Path("./src/event_driven"),
        description="Base root path used to resolve relative destination paths.",
        alias="base_dir",
    )

    test_dir: Path = Field(
        default=Path("./test"),
        description="Test root path used to resolve relative destination paths.",
        alias="test_dir",
    )

    # Global file inputs/settings
    models_yaml: Path = Field(
        default=Path("./pymodeller/models.yaml"),
        alias="models_yaml",  # Kept for backward compatibility
    )
    exceptions_yaml: Path = Field(
        default=Path("./pymodeller/exceptions.yaml"),
        alias="exceptions_yaml",
    )
    environment_file: Path = Field(default=Path("./environments.yaml"))
    generate_init_models: bool = Field(default=True)
    env: Path = Field(default=Path(".env"))
    env_example: Path = Field(default=Path(".env.example"))

    enabled_sources: list[SourceType] = Field(
        default_factory=lambda: [SourceType.YAML],
        description="List of sources",
    )

    env_prefix: str = Field(default="APP_ENV")

    pyproject_toml_table_header: list[str] | None = Field(
        default=None,
        description="Optional table header path in pyproject.toml (e.g., ['tool', 'my_app'])",
    )

    # Mapping of target environments: {"infrastructure": DestinationConfig, "domain": DestinationConfig}
    destinations: dict[DestinationType, DestinationConfig] = Field(default_factory=dict)

    @field_validator("enabled_sources", "pyproject_toml_table_header", mode="before")
    @classmethod
    def parse_enabled_sources(cls, v: Any) -> Any:
        """Parse 'yaml,s3' string from TOML into list of SourceType."""
        if isinstance(v, str):
            v = [item.strip().lower() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return [item.strip().lower() if isinstance(item, str) else item for item in v]
        return v

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customizes the configuration loading order for settings.

        Prioritizes constructor arguments (`init_settings`) first, followed by
        values parsed from the `pyproject.toml` file source.
        """
        return (
            init_settings,
            PyprojectTomlConfigSettingsSource(settings_cls),
        )

    def get_destination(self, model_type: DestinationType = DestinationType.INFRASTRUCTURE) -> DestinationConfig:
        """Retrieve destination paths for a given model type with resolved base paths."""
        dest = self.destinations.get(model_type)
        if not dest:
            # Fallback to default destination if the model_type is not defined in TOML
            dest = DestinationConfig()
        return dest.resolve_paths(self.base_dir, self.test_dir, model_type)

    def get_destinations(
        self, model_type: DestinationType | None = DestinationType.INFRASTRUCTURE
    ) -> dict[DestinationType, DestinationConfig]:
        """Get dict of detinations."""
        if model_type:
            return {model_type: self.get_destination(model_type)}

        return {
            name: dest.resolve_paths(self.base_dir, self.test_dir, name) for name, dest in self.destinations.items()
        }


@lru_cache(maxsize=1)
def get_code_gen_config() -> CodegenConfig:
    """Retrieve and instantiate cached code generation configuration."""
    return CodegenConfig()
