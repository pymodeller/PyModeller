"""Enum generator.

========================================================================================================================
Name:         pymodeller/generators/enum_generator.py
Description:  Generator for Enums extending BaseGenerator.
Project:      PyModeller

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from pydantic import Field

from pymodeller.generators.base_generator import BaseGenerator, NamedModel
from pymodeller.loader import DestinationType


class EnumerationSpec(NamedModel):
    """Specification model for Enumerations."""

    name: str = Field(..., description="Name of Enumeration")
    destination: DestinationType = DestinationType.INFRASTRUCTURE
    options: list[str] = Field(..., alias="options")
    description: str = Field(..., alias="description")


class EnumGenerator(BaseGenerator[EnumerationSpec]):
    """Generator to transform YAML definitions into Python Enum classes."""

    yaml_section: str = "enumerations"
    template_name: str = "enumerate.jinja"
    model_class: type[EnumerationSpec] = EnumerationSpec
    class_suffix: str = "Enum"
