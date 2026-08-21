"""Enum generator.

========================================================================================================================
Name:         pymodeller/generators/enum_generator.py
Description:  Generator enum.
Project:      PyModeller

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from jinja2 import Environment, PackageLoader, select_autoescape
import re
from pymodeller.loader import DestinationType


class EnumerationSpec(BaseModel):
    """Spec enum."""
    name: str = Field(..., alias="name")
    destination: DestinationType = DestinationType.INFRASTRUCTURE
    options: list[str] = Field(..., alias='options')
    description: str = Field(..., alias="description")


class EnumerationConfig(BaseModel):
    """Config enum."""

    enumerations: list[EnumerationSpec] = Field(..., alias="enumerations")


class EnumerationParser:
    """Lee el archivo YAML y lo convierte en objetos validados."""

    @staticmethod
    def parse_yaml(path: Path) -> list[EnumerationSpec]:
        """Parse yaml."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            config = EnumerationConfig(enumerations=data.get("enumerations", []))
            return config.enumerations


class EnumGenerator:
    """Generator to transform YAML definitions into Python Enum classes."""

    def __init__(self, destination: DestinationType = DestinationType.INFRASTRUCTURE) -> None:
        """Init exception generator."""
        self.env = Environment(
            loader=PackageLoader("pymodeller", "templates"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.destination = destination

    @staticmethod
    def _to_snake_case(name: str) -> str:
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

    def generate(self, yaml_path: Path, enum_dir: Path) -> list:
        """Lee el YAML, lo parsea y genera un archivo por cada enumeration."""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"El archivo {yaml_path} no existe.")

        specs = EnumerationParser.parse_yaml(path)
        dest_spec = [s for s in specs if s.destination == self.destination]

        if not dest_spec:
            return []

        enum_dir.mkdir(parents=True, exist_ok=True)
        template = self.env.get_template("enumerate.jinja")
        res = []
        models_data: list[dict[str, str]] = []
        for spec in dest_spec:
            content = template.render(spec=spec)

            module_name = self._to_snake_case(spec.name)

            filename = f"{module_name}.py"
            file_path = enum_dir / filename
            file_path.write_text(content, encoding="utf-8")
            res.append(file_path)

            models_data.append({
                "module": module_name,
                "class_name": spec.name + 'Enum',
            })

        init_template = self.env.get_template("init.jinja")
        init_content = init_template.render(models=models_data)
        init_file_path = enum_dir / "__init__.py"
        init_file_path.write_text(init_content, encoding="utf-8")
        res.append(init_file_path)

        return res


# Quick usage example
if __name__ == "__main__":
    EnumGenerator.generate(Path("enums.yaml"), Path("generated_enums.py"))
