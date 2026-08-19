"""Config file.

========================================================================================================================
Name:         pymodeller/config.py
Description:  Load configuration.
Project:      PyModeller

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
import tomllib


class DestinationConfig(BaseModel):
    """Output path configuration for a specific model type (e.g., infrastructure, domain)."""

    import_init_base_class: Path | None = None

    pydantic_model_folder: Path = Path("infraestructure/config/schemas")
    pydantic_settings_folder: Path = Path("infrastructure/config/settings")
    pydantic_settings_init: Path | None = Path("infrastructure/config/init_settings.py")

    peewee_folder: Path = Path("persistence/models")
    peewee_out: Path = Path("persistence/connection.py")

    exceptions_folder: Path = Path("exceptions")

    def resolve_paths(self, base_dir: Path) -> "DestinationConfig":
        """Resolve relative paths by prepending the project base directory."""
        return DestinationConfig(
            pydantic_model_folder=base_dir / self.pydantic_model_folder,
            pydantic_settings_folder=base_dir / self.pydantic_settings_folder,
            pydantic_settings_init=(
                base_dir / self.pydantic_settings_init
                if self.pydantic_settings_init
                else None
            ),
            peewee_folder=base_dir / self.peewee_folder,
            peewee_out=base_dir / self.peewee_out,
            exceptions_folder=base_dir / self.exceptions_folder,
        )


class CodegenConfig(BaseModel):
    """Main configuration model for code generation."""

    base_dir: Path = Field(
        default=Path("./src/event_driven"),
        description="Base root path used to resolve relative destination paths.",
        alias="base_dir",
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

    # Mapping of target environments: {"infrastructure": DestinationConfig, "domain": DestinationConfig}
    destinations: dict[str, DestinationConfig] = Field(default_factory=dict)

    def get_destination(self, model_type: str = "infrastructure") -> DestinationConfig:
        """Retrieve destination paths for a given model type with resolved base paths."""
        dest = self.destinations.get(model_type)
        if not dest:
            # Fallback to default destination if the model_type is not defined in TOML
            dest = DestinationConfig()
        return dest.resolve_paths(self.base_dir)


def load_codegen_config(
    toml_path: str | Path = Path("pyproject.toml"),
) -> dict[str, Any]:
    """Load values from section [tool.pymodeller] in pyproject.toml."""
    toml_path = Path(toml_path)

    if not toml_path.exists():
        raise FileNotFoundError(f"TOML configuration file not found: {toml_path}")

    with toml_path.open("rb") as f:
        data = tomllib.load(f)

    return data.get("tool", {}).get("pymodeller", {})


@lru_cache(maxsize=1)
def get_code_gen_config() -> CodegenConfig:
    """Retrieve and instantiate cached code generation configuration."""
    config_dict = load_codegen_config()
    return CodegenConfig(**config_dict)
