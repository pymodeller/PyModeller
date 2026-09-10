"""Exception generators.

========================================================================================================================
Name:         pymodeller/generators/exception_generator.py
Description:  Domain and HTTP Exception generators extending BaseGenerator.
Project:      PyModeller

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from pathlib import Path

from pydantic import Field, computed_field

from pymodeller.generators.base_generator import BaseGenerator, NamedModel
from pymodeller.loader import DestinationType


class ExceptionSpec(NamedModel):
    """Validation schema for domain or standard exceptions defined in YAML."""

    name: str = Field(..., alias="class_name")
    description: str = Field("General error", alias="description")
    destination: DestinationType = Field(default=DestinationType.INFRASTRUCTURE, alias="destination")

    @computed_field
    @property
    def class_name(self) -> str:
        """Alias property to maintain compatibility with templates expecting 'class_name'."""
        return self.name


class HttpExceptionSpec(ExceptionSpec):
    """Validation schema for HTTP exceptions, including status code and error details."""

    status_code: int = Field(500, alias="status_code")
    detail: str = Field("Internal Server Error", alias="detail")
    is_http: bool = Field(True, alias="is_http")


class ExceptionGenerator(BaseGenerator[ExceptionSpec]):
    """Generator to transform YAML definitions into standard Python Exception classes."""

    yaml_section: str = "exceptions"
    template_name: str = "exceptions.jinja"
    class_suffix: str = "Error"
    model_class: type[ExceptionSpec] = ExceptionSpec
    single_file: bool = True

    def parse_yaml(self, path: Path) -> list[ExceptionSpec]:
        """Parse YAML file and retrieve only non-HTTP exceptions.

        Args:
            path (Path): Path to the target YAML configuration file.

        Returns:
            list[ExceptionSpec]: Filtered list of standard exception specifications.
        """
        all_specs = super().parse_yaml(path)
        return [spec for spec in all_specs if not getattr(spec, "is_http", False)]


class HttpExceptionGenerator(BaseGenerator[HttpExceptionSpec]):
    """Generator to transform YAML definitions into HTTP Exception classes."""

    yaml_section: str = "exceptions"
    single_file: bool = True
    class_suffix: str = "Exception"
    output_filename: str = "http_exceptions"
    template_name: str = "exceptions_http.jinja"
    model_class: type[HttpExceptionSpec] = HttpExceptionSpec

    def parse_yaml(self, path: Path) -> list[HttpExceptionSpec]:
        """Parse YAML file and retrieve only HTTP exceptions.

        Args:
            path (Path): Path to the target YAML configuration file.

        Returns:
            list[HttpExceptionSpec]: Filtered list of HTTP exception specifications.
        """
        all_specs = super().parse_yaml(path)
        return [spec for spec in all_specs if getattr(spec, "is_http", False)]
