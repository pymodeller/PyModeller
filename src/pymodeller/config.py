"""Load configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


def load_codegen_config(yaml_path: str | Path) -> dict[str, Any]:
    """Load configuration values from a YAML file into a dictionary.

    Expected YAML structure:
        config:
          - name: CODEGEN_OUT
            value: ./data_models.py
          - name: MODEL_FOLDER
            value: models
    """
    yaml_path = Path(yaml_path)

    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")

    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    config_list = data.get("config", [])

    if not isinstance(config_list, list):
        raise ValueError("The 'config' section must be a list of name/value pairs.")

    config_dict = {item["name"]: item.get("value") for item in config_list if "name" in item}

    return config_dict


class CodegenConfig(BaseModel):
    """Configuration for code generation."""

    spec: Path = Field(
        default=Path("py_modeller.yaml"),
        alias="SPEC",
        description="Input file for generated models.",
    )
    pydantic_out: Path | None = Field(
        default=None,
        alias="PYDANTIC_OUT",
        description="Output file for generated models.",
    )
    peewee_out: Path = Field(
        default=Path("./models/db_models.py"),
        alias="PEEWEE_OUT",
        description="Output file for generated models.",
    )
    pydantic_folder: Path = Field(
        default=Path("models/schemas"),
        alias="PYDANTIC_FOLDER",
        description="Directory where models will be stored.",
    )
    peewee_folder: Path = Field(
        default=Path("models/db"),
        alias="PEEWEE_FOLDER",
        description="Directory where models will be stored.",
    )
    environment_file: Path = Field(
        default=Path("environment.yaml"),
        alias="ENVIRONMENTS_FILE",
        description="Path to environment file.",
    )
    exceptions_file: Path | None = Field(
        default=None,
        alias="EXCEPTIONS_FILE",
        description="Path to exception file.",
    )
    exceptions_folder: Path | None = Field(
        default=None,
        alias="EXCEPTIONS_FOLDER",
        description="Path to exception file.",
    )
    import_settings_base_class: str | None = Field(
        default=None,
        alias="IMPORT_SETTINGS_BASE_CLASS",
        description="Import to base class.",
    )
    generate_init_models: bool = Field(
        default=True,
        alias="GENERATE_INIT_MODELS",
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


@lru_cache(maxsize=1)
def get_code_gen_config() -> CodegenConfig:
    """Get code gen config."""
    config_dict = load_codegen_config("py_modeller.yaml")
    return CodegenConfig(**config_dict)
