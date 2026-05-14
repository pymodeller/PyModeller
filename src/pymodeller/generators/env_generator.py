"""Env manager."""

from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from pymodeller.loader import SectionType


class EnvGenerator:
    """Service class to handle core env-spec logic."""

    def __init__(self) -> None:
        """Init env generator."""
        self.env = Environment(loader=PackageLoader("pymodeller", "templates"), autoescape=select_autoescape())

    @staticmethod
    def create_section(lines: list, section: Any, variables_to_show: list, separator: str = '=') -> None:
        """Create section for env file."""
        lines.append(f"# {'─' * 20} {section.name} {'─' * 20}")
        if section.description:
            lines.append(f"# {section.description}")

        for var in variables_to_show:
            badges = []
            if var.required:
                badges.append("✱ required")
            if var.secret:
                badges.append("🔒 secret")
            badge_str = f"  [{' | '.join(badges)}]" if badges else ""

            lines.append(f"# {var.description} | type: {var.type}{badge_str}")
            lines.append(f"{var.env_name.upper()}{separator}{var.display_value()}")

    def generate_example_content(self, spec: Any, secrets_only: bool = False) -> str:
        """Build the content for the .env.example file."""
        template = self.env.get_template("env_file.jinja")
        lines = []
        settings = [s for s in spec.sections if s.type == SectionType.SETTINGS]
        for section in settings:
            variables_to_show = [v for v in section.variables if not secrets_only or v.secret]
            if not variables_to_show:
                continue
            self.create_section(lines, section, variables_to_show)

        return template.render(env_lines=lines)

    def generate_environment_yaml(self, spec: Any) -> str:
        """Build the content for the .env.example file."""
        template = self.env.get_template("environment_yaml.jinja")
        lines = []
        settings = [s for s in spec.sections if s.type == SectionType.SETTINGS]
        for section in settings:
            variables_to_show = [v for v in section.variables if not v.secret]
            if not variables_to_show:
                continue
            self.create_section(lines, section, variables_to_show, separator=': ')

        return template.render(env_lines=lines)
