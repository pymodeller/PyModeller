"""Exception generator.

========================================================================================================================
Name:         pymodeller/generators/exception_generator.py
Description:  Exception generator extending BaseGenerator.
Project:      PyModeller

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from pathlib import Path

from pydantic import Field

from pymodeller.generators.base_generator import BaseGenerator, NamedModel
from pymodeller.loader import DestinationType


class ExceptionSpec(NamedModel):
    """Esquema de validación para cada excepción en el YAML."""

    class_name: str = Field(..., alias="class_name")
    status_code: int = Field(500, alias="status_code")
    detail: str = Field("Internal Server Error", alias="detail")
    is_http: bool = Field(True, alias="is_http")
    description: str = Field("General error", alias="description")
    destination: DestinationType = Field(default=DestinationType.INFRASTRUCTURE, alias="destination")

    @property
    def name(self) -> str:
        """Satisface la interfaz NamedModel utilizando class_name."""
        return self.class_name


class ExceptionGenerator(BaseGenerator[ExceptionSpec]):
    """Service class to handle exception code generation logic."""

    yaml_section: str = "exceptions"
    template_name: str = "exceptions.jinja"
    model_class: type[ExceptionSpec] = ExceptionSpec

    def generate(self, yaml_path: Path, output_dir: Path) -> list[Path]:
        """Lee el YAML, filtra por destino y genera los módulos agrupados de excepciones."""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"El archivo {yaml_path} no existe.")

        specs: list[ExceptionSpec] = self.parse_yaml(path)
        dest_specs: list[ExceptionSpec] = [
            s for s in specs if getattr(s, "destination", self.destination) == self.destination
        ]

        if not dest_specs:
            return []

        output_dir.mkdir(parents=True, exist_ok=True)
        templates = ["exceptions.jinja", "exceptions_http.jinja"]
        generated_files: list[Path] = []

        for template_name in templates:
            flag_http = "http" in template_name
            target_specs = [spec for spec in dest_specs if spec.is_http == flag_http]

            if target_specs:
                template = self.env.get_template(template_name)
                content = template.render(exceptions=target_specs)

                file_stem = Path(template_name).stem
                file_path = output_dir / f"{file_stem}.py"
                file_path.write_text(content, encoding="utf-8")
                generated_files.append(file_path)

        if generated_files:
            init_file_path = output_dir / "__init__.py"
            init_file_path.write_text("", encoding="utf-8")
            generated_files.append(init_file_path)

        return generated_files
