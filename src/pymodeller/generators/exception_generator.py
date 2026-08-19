"""Exception generator.

========================================================================================================================
Name:         pymodeller/generators/exception_generator.py
Description:  Exception generator.
Project:      PyModeller

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from pathlib import Path

import yaml
from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic import BaseModel, Field

from pymodeller.loader import DestinationType


class ExceptionSpec(BaseModel):
    """Esquema de validación para cada excepción en el YAML."""

    class_name: str = Field(..., alias="class_name")
    status_code: int = Field(500, alias="status_code")
    detail: str = Field("Internal Server Error", alias="detail")
    is_http: bool = Field(True, alias="is_http")
    description: str = Field("General error", alias="description")
    destination: str = Field(default=DestinationType.INFRASTRUCTURE, alias="destination")


class ExceptionConfig(BaseModel):
    """Contenedor para la lista de excepciones."""

    exceptions: list[ExceptionSpec]


class ExceptionParser:
    """Lee el archivo YAML y lo convierte en objetos validados."""

    @staticmethod
    def parse_yaml(path: Path) -> list[ExceptionSpec]:
        """Parse yaml."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            config = ExceptionConfig(exceptions=data.get("exceptions", []))
            return config.exceptions


class ExceptionGenerator:
    """Service class to handle exception code generation logic."""

    def __init__(self, destination: DestinationType = DestinationType.INFRASTRUCTURE) -> None:
        """Init exception generator."""
        self.env = Environment(
            loader=PackageLoader("pymodeller", "templates"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.destination = destination

    def generate(self, yaml_path: Path, exception_dir: Path) -> list:
        """Lee el YAML, lo parsea y genera el contenido del archivo."""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"El archivo {yaml_path} no existe.")

        specs = ExceptionParser.parse_yaml(path)
        dest_spec = [s for s in specs if s.destination == self.destination]

        templates = [Path("exceptions.jinja"), Path("http_exceptions.jinja")]
        res = []

        for t in templates:
            template = self.env.get_template(t.name)
            flag_http = 'http' in t.name

            spect_ = [d for d in dest_spec if d.is_http == flag_http]
            content = template.render(exceptions=spect_) if len(spect_) > 0 else None
            if content:
                exception_dir.mkdir(parents=True, exist_ok=True)
                file_path = exception_dir / f"{t.stem}.py"
                file_path.write_text(content, encoding="utf-8")
                res.append(file_path)

        if len(res) > 0:
            init_file_path = exception_dir / "__init__.py"
            init_file_path.write_text("", encoding="utf-8")
            res.append(init_file_path)

        return res