"""Load configuration."""

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def load_codegen_config(toml_path: str | Path = Path("pyproject.toml")) -> dict[str, Any]:
    """Load values from section [tool.pymodeller] pyproject.toml."""
    toml_path = Path(toml_path)

    if not toml_path.exists():
        raise FileNotFoundError(f"File TOML not found: {toml_path}")

    with toml_path.open("rb") as f:
        data = tomllib.load(f)

    config_dict = data.get("tool", {}).get("pymodeller", {})

    return config_dict


class CodegenConfig(BaseModel):
    """Configuration for code generation."""

    spec: Path = Field(
        default=Path("py_modeller.yaml"),
        alias="spec",
        description="Input file for generated models.",
    )
    pydantic_out: Path | None = Field(
        default=None,
        alias="pydantic_out",
        description="Output file for generated models.",
    )
    peewee_out: Path = Field(
        default=Path("./models/db_models.py"),
        alias="peewee_out",
        description="Output file for generated models.",
    )
    pydantic_folder: Path = Field(
        default=Path("models/schemas"),
        alias="pydantic_folder",
        description="Directory where models will be stored.",
    )
    peewee_folder: Path = Field(
        default=Path("models/db"),
        alias="peewee_folder",
        description="Directory where models will be stored.",
    )
    environment_file: Path = Field(
        default=Path("environment.yaml"),
        alias="environment_file",
        description="Path to environment file.",
    )
    exceptions_file: Path | None = Field(
        default=None,
        alias="exceptions_file",
        description="Path to exception file.",
    )
    exceptions_folder: Path | None = Field(
        default=None,
        alias="exceptions_folder",
        description="Path to exception file.",
    )
    import_settings_base_class: str | None = Field(
        default=None,
        alias="import_settings_base_class",
        description="Import to base class.",
    )
    generate_init_models: bool = Field(
        default=True,
        alias="generate_init_models",
        description="Generate init models.",
    )
    env: Path = Field(
        default=Path(".env"),
        alias="env",
        description="Env file.",
    )
    env_example: Path = Field(
        default=Path(".env.example"),
        alias="env",
        description="Env example name.",
    )
    pymodeller_models: Path = Field(
        default=Path("./pymodeller/models.yml"),
        alias="pymodeller_models",
        description="Pymodeller models",
    )


@lru_cache(maxsize=1)
def get_code_gen_config() -> CodegenConfig:
    """Get code gen config."""
    config_dict = load_codegen_config()
    return CodegenConfig(**config_dict)
