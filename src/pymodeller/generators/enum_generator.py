"""Generator enum."""

from pathlib import Path
from typing import Any

import yaml


class EnumGenerator:
    """Generator to transform YAML definitions into Python Enum classes."""

    @staticmethod
    def generate(yaml_path: Path, output_path: Path) -> None:
        """Reads the YAML file and writes a Python module with Enum classes.

        Args:
            yaml_path: Path to the input YAML configuration.
            output_path: Path where the .py file will be created.
        """
        with open(yaml_path) as f:
            data: dict[str, Any] = yaml.safe_load(f)

        lines = ['"""Auto-generated Enums from YAML spec."""', "from enum import Enum", "", ""]

        for enum_name, config in data.items():
            base_type = config.get("type", "str")
            values = config.get("values", {})

            lines.append(f"class {enum_name}(Enum):")
            lines.append(f'    """{enum_name} auto-generated enum."""')
            lines.append("")

            for key, value in values.items():
                # Format value based on type
                formatted_value = f'"{value}"' if base_type == "str" else value

                lines.append(f"    {key.upper()} = {formatted_value}")

            lines.append("")  # Space between classes

        output_path.write_text("\n".join(lines), encoding="utf-8")


# Quick usage example
if __name__ == "__main__":
    EnumGenerator.generate(Path("enums.yaml"), Path("generated_enums.py"))
