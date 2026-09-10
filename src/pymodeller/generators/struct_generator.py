"""Struct generator.

========================================================================================================================
Name:         pymodeller/generators/struct_generator.py
Description:  Generator for Structs extending BaseGenerator.
Project:      PyModeller

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from pydantic import BaseModel, Field

from pymodeller.generators.base_generator import BaseGenerator, NamedModel
from pymodeller.loader import DestinationType


class StructFieldSpec(BaseModel):
    """Spec para un campo dentro de un struct."""

    name: str = Field(..., alias="name")
    type: str = Field(..., alias="type")
    description: str = Field(default="", alias="description")


class StructSpec(NamedModel):
    """Spec struct."""

    destination: DestinationType = DestinationType.INFRASTRUCTURE
    description: str = Field(default="", alias="description")
    fields: list[StructFieldSpec] = Field(..., alias="fields")


class StructGenerator(BaseGenerator[StructSpec]):
    """Generator to transform YAML definitions into Python Struct/Data classes."""

    yaml_section: str = "structs"
    class_suffix: str = "Struct"
    template_name: str = "struct.jinja"
    model_class: type[StructSpec] = StructSpec
