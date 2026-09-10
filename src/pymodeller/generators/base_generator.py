"""Base modular generator using inheritance pattern.

========================================================================================================================
Name:         pymodeller/generators/base_generator.py
Description:  Abstract base generator driving template code generation from YAML specifications.
Project:      PyModeller

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

import re
from pathlib import Path
from typing import TypeVar

import yaml
from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic import BaseModel

from pymodeller.loader import DestinationType


class NamedModel(BaseModel):
    """Base model ensuring the presence of a 'name' attribute."""

    name: str


# Type variable constrained to Pydantic BaseModels
T = TypeVar("T", bound=NamedModel)


class BaseGenerator[T: NamedModel]:
    """Abstract base generator for creating Python code from Jinja2 templates and YAML specs.

    Subclasses must define `yaml_section`, `template_name`, and `model_class`.
    """

    yaml_section: str
    template_name: str
    model_class: type[T]
    class_suffix: str = ""
    single_file: bool = False
    accumulate_imports: bool = False
    output_filename: str | None = None
    package_name: str = "pymodeller"
    templates_folder: str = "templates"

    __saved_imports__: list[dict] = []

    def __init__(
        self,
        destination: DestinationType = DestinationType.INFRASTRUCTURE,
        accumulate_imports: bool = False,
        output_filename: str | None = None,
    ) -> None:
        """Initialize the base generator with environment settings and destination target.

        Args:
            destination (DestinationType): Target architectural layer for code generation.
            accumulate_imports (bool | None): Override class-level accumulate_imports setting if provided.
            output_filename (str | None): Custom target filename when using single_file mode.
        """
        self.destination: DestinationType = destination
        self.accumulate_imports = accumulate_imports
        if output_filename is not None:
            self.output_filename = output_filename

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
        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

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
        name: str = spec.name
        return f"{name}{self.class_suffix}"

    def _get_single_output_filename(self) -> str:
        """Resolve the target output filename for single-file mode.

        Returns:
            str: The target file name ending with .py extension.
        """
        if self.output_filename:
            target = self.output_filename
        else:
            target = self.yaml_section

        target = self._to_snake_case(target)
        return target if target.endswith(".py") else f"{target}.py"

    def generate(self, yaml_path: Path, output_dir: Path) -> list[Path]:
        """Read YAML definitions, render Jinja2 templates, and write generated files.

        Args:
            yaml_path (Path): Path to the source YAML file.
            output_dir (Path): Destination directory where files will be created.

        Returns:
            list[Path]: List of generated file paths, including `__init__.py`.

        Raises:
            FileNotFoundError: If the provided YAML file path does not exist.
        """
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"The file {yaml_path} does not exist.")

        specs: list[T] = self.parse_yaml(path)
        #dest_specs: list[T] = [s for s in specs if getattr(s, "destination", self.destination) == self.destination]
        dest_specs: list[T] = [
            s.model_copy(update={"name": f"{self.get_class_name(s)}"})
            for s in specs
            if getattr(s, "destination", self.destination) == self.destination
        ]

        if not dest_specs:
            return []

        output_dir.mkdir(parents=True, exist_ok=True)
        template = self.env.get_template(self.template_name)
        generated_files: list[Path] = []
        models_data: list[dict[str, str]] = [] if len(self.__saved_imports__) == 0 else self.__saved_imports__

        if self.single_file:
            # Single destination file for all parsed specifications
            file_name = self._get_single_output_filename()
            file_path = output_dir / file_name

            # Render template passing the entire list of specifications
            content = template.render(specs=dest_specs, items=dest_specs)
            file_path.write_text(content, encoding="utf-8")
            generated_files.append(file_path)

            module_name = file_path.stem
            for spec in dest_specs:
                models_data.append({
                    "module": module_name,
                    "class_name": spec.name,
                })
        else:
            # Individual module per specification
            for spec in dest_specs:
                name: str = spec.name
                content: str = template.render(spec=spec)
                module_name: str = self._to_snake_case(name.removesuffix(self.class_suffix))

                file_path: Path = output_dir / f"{module_name}.py"
                file_path.write_text(content, encoding="utf-8")
                generated_files.append(file_path)

                models_data.append({
                    "module": module_name,
                    "class_name": spec.name,
                })

        # Render module package __init__.py file
        init_template = self.env.get_template("init.jinja")
        init_content: str = init_template.render(models=models_data)
        init_file_path: Path = output_dir / "__init__.py"
        init_file_path.write_text(init_content, encoding="utf-8")
        generated_files.append(init_file_path)

        if self.accumulate_imports:
            self.__saved_imports__.extend(models_data)

        return generated_files