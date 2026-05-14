"""CLI for pymodeller.

========================================================================================================================
Name:         core/cli.py
Description:  CLI entry-point for env-spec operations: example, check, diff, codegen, drift.
              Uses Typer for CLI parsing and a Service-based approach for logic.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

import pyfiglet
import typer
from rich.console import Console

from pymodeller.cli.commands import check, codegen, drift, example, setup, show_version, yaml_file, generate_env
from pymodeller.cli.dev_tools import main_check, main_ci, main_test

epilog = (
    "Dev Commands: dev [check | test | ci] -> Use 'pymodeller dev --help' for details.\n\n"
    "Env Commands: env [example | create] -> Use 'pymodeller env --help' for details."
)


app = typer.Typer(
    name="pymodeller",
    help="CLI tools for PyModeller",
    epilog=epilog,
    no_args_is_help=False,
    add_completion=False,
)


dev_app = typer.Typer(
    name="dev",
    help="DEV tools for PyModeller",
    no_args_is_help=True,
    add_completion=False,
)
dev_app.command(name="check")(main_check)
dev_app.command(name="test")(main_test)
dev_app.command(name="ci")(main_ci)


env_app = typer.Typer(
    name="env",
    help="env tools for PyModeller",
    no_args_is_help=True,
    add_completion=False,
)
env_app.command()(example)
env_app.command(name="yaml")(yaml_file)
env_app.command()(generate_env)


app.add_typer(dev_app, name="dev", help="Development and CI/CD tools for PyModeller")
app.add_typer(env_app, name="env", help="Env tools to create .env files")
app.command()(setup)
app.command()(check)
app.command()(codegen)
app.command()(drift)


def print_logo() -> None:
    """Print logo."""
    logo = pyfiglet.figlet_format("PyModeller", font="slant")

    console = Console()
    console.print(f"[bold cyan]{logo}[/bold cyan]")


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool | None = typer.Option(
        None, "--version", "-v", callback=show_version, is_eager=True, help="Show version and exit"
    ),
) -> None:
    """Core entry point for PyModeller CLI."""
    if ctx.invoked_subcommand is None:
        print_logo()
        typer.echo(ctx.get_help())


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
