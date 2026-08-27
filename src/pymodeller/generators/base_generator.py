"""Base modular generator using inheritance pattern.

========================================================================================================================
Name:         pymodeller/generators/base_generator.py
Description:  Abstract base generator driving template code generation from YAML specifications.
Project:      PyModeller

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from pathlib import Path
import re
from typing import Generic, Type, TypeVar
import yaml
from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic import BaseModel
from pymodeller.loader import DestinationType

# Type variable constrained to Pydantic BaseModels
T = TypeVar("T", bound=BaseModel)


class BaseGenerator(Generic[T]):
    """Abstract base generator for creating Python code from Jinja2 templates and YAML specs.

    Subclasses must define `yaml_section`, `template_name`, and `model_class`.
    """

    yaml_section: str
    template_name: str
    model_class: Type[T]
    class_suffix: str = ""
    package_name: str = "pymodeller"
    templates_folder: str = "templates"

    def __init__(self, destination: DestinationType = DestinationType.INFRASTRUCTURE) -> None:
        """Initialize the base generator with environment settings and destination target.

        Args:
            destination (DestinationType): Target architectural layer for code generation.
        """
        self.destination: DestinationType = destination
        self.env: Environment = Environment(
            loader=PackageLoader(self.package_name, self.templates_folder),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert a CamelCase string to snake_case.

        Args:
            name (str): The string to convert.

        Returns:
            str: The converted snake_case string.
        """
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

    def parse_yaml(self, path: Path) -> list[T]:
        """Parse and validate items from a YAML file using the subclass model class.

        Args:
            path (Path): Path to the target YAML configuration file.

        Returns:
            list[T]: List of parsed and validated Pydantic models.
        """
        with open(path, encoding="utf-8") as f:
            data: dict = yaml.safe_load(f) or {}
            items: list[dict] = data.get(self.yaml_section, [])
            return [self.model_class.model_validate(item) for item in items]

    def get_class_name(self, spec: T) -> str:
        """Construct the generated class name used inside `__init__.py`.

        Subclasses can override this method for custom naming logic.

        Args:
            spec (T): The specification model instance.

        Returns:
            str: The formatted class name.
        """
        name: str = getattr(spec, "name")
        return f"{name}{self.class_suffix}"

    def generate(self, yaml_path: Path, output_dir: Path) -> list[Path]:
        """Read YAML definitions, render Jinja2 templates, and write generated files.

        Args:
            yaml_path (Path): Path to the source YAML file.
            output_dir (Path): Destination directory where files will be created.

        Raises:
            FileNotFoundError: If the provided YAML file path does not exist.

        Returns:
            list[Path]: List of generated file paths, including `__init__.py`.
        """
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"The file {yaml_path} does not exist.")

        specs: list[T] = self.parse_yaml(path)
        dest_specs: list[T] = [
            s for s in specs if getattr(s, "destination", self.destination) == self.destination
        ]

        if not dest_specs:
            return []

        output_dir.mkdir(parents=True, exist_ok=True)
        template = self.env.get_template(self.template_name)
        generated_files: list[Path] = []
        models_data: list[dict[str, str]] = []

        # Render individual module files
        for spec in dest_specs:
            name: str = getattr(spec, "name")
            content: str = template.render(spec=spec)
            module_name: str = self._to_snake_case(name)

            file_path: Path = output_dir / f"{module_name}.py"
            file_path.write_text(content, encoding="utf-8")
            generated_files.append(file_path)

            models_data.append({
                "module": module_name,
                "class_name": self.get_class_name(spec),
            })

        # Render module package __init__.py file
        init_template = self.env.get_template("init.jinja")
        init_content: str = init_template.render(models=models_data)
        init_file_path: Path = output_dir / "__init__.py"
        init_file_path.write_text(init_content, encoding="utf-8")
        generated_files.append(init_file_path)

        return generated_files