"""Struct generator.

========================================================================================================================
Name:         pymodeller/generators/struct_generator.py
Description:  Generator struct.
Project:      PyModeller

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from pathlib import Path
import re
import yaml
from jinja2 import Environment, PackageLoader, select_autoescape
from pymodeller.loader import DestinationType
from pydantic import BaseModel, Field

class StructFieldSpec(BaseModel):
    """Spec para un campo dentro de un struct."""
    name: str = Field(..., alias="name")
    type: str = Field(..., alias="type")
    description: str = Field(default="", alias="description")


class StructSpec(BaseModel):
    """Spec struct."""
    name: str = Field(..., alias="name")
    destination: DestinationType = DestinationType.INFRASTRUCTURE
    description: str = Field(default="", alias="description")
    fields: list[StructFieldSpec] = Field(..., alias="fields")


class StructConfig(BaseModel):
    """Config struct."""
    structs: list[StructSpec] = Field(..., alias="structs")


class StructParser:
    """Lee el archivo YAML y lo convierte en objetos validados para Structs."""

    @staticmethod
    def parse_yaml(path: Path) -> list[StructSpec]:
        """Parse yaml."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            config = StructConfig(structs=data.get("structs", []))
            return config.structs


class StructGenerator:
    """Generator to transform YAML definitions into Python Struct/Data classes."""

    def __init__(self, destination: DestinationType = DestinationType.INFRASTRUCTURE) -> None:
        """Init struct generator."""
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

    def generate(self, yaml_path: Path, output_dir: Path) -> list[Path]:
        """Lee el YAML, lo parsea y genera un archivo por cada struct."""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"El archivo {yaml_path} no existe.")

        specs = StructParser.parse_yaml(path)
        dest_spec = [s for s in specs if s.destination == self.destination]

        if not dest_spec:
            return []

        output_dir.mkdir(parents=True, exist_ok=True)
        template = self.env.get_template("struct.jinja")
        res = []
        models_data: list[dict[str, str]] = []

        for spec in dest_spec:
            content = template.render(spec=spec)
            module_name = self._to_snake_case(spec.name)

            filename = f"{module_name}.py"
            file_path = output_dir / filename
            file_path.write_text(content, encoding="utf-8")
            res.append(file_path)

            models_data.append({
                "module": module_name,
                "class_name": spec.name,
            })

        init_template = self.env.get_template("init.jinja")
        init_content = init_template.render(models=models_data)
        init_file_path = output_dir / "__init__.py"
        init_file_path.write_text(init_content, encoding="utf-8")
        res.append(init_file_path)

        return res