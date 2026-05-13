"""Exception generator. """

from pathlib import Path
from typing import List

import yaml
from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic import BaseModel, Field


class ExceptionSpec(BaseModel):
    """Esquema de validación para cada excepción en el YAML."""
    class_name: str = Field(..., alias="class_name")
    status_code: int = Field(500, alias="status_code")
    detail: str = Field("Internal Server Error", alias="detail")
    description: str = Field("General error", alias="description")


class ExceptionConfig(BaseModel):
    """Contenedor para la lista de excepciones."""
    exceptions: List[ExceptionSpec]


class ExceptionParser:
    """Lee el archivo YAML y lo convierte en objetos validados."""

    @staticmethod
    def parse_yaml(path: Path) -> List[ExceptionSpec]:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            config = ExceptionConfig(exceptions=data.get("exceptions", []))
            return config.exceptions


class ExceptionGenerator:
    """Service class to handle exception code generation logic."""

    def __init__(self) -> None:
        """Init exception generator."""
        self.env = Environment(
            loader=PackageLoader("pymodeller", "templates"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def generate(self, yaml_path: Path) -> str:
        """ Lee el YAML, lo parsea y genera el contenido del archivo. """
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"El archivo {yaml_path} no existe.")

        specs = ExceptionParser.parse_yaml(path)

        template = self.env.get_template("exceptions.jinja")
        return template.render(exceptions=specs)