"""File title.

========================================================================================================================
Name:         core/cli.py
Description:  CLI entry-point for env-spec operations: example, check, diff, codegen, drift.
              Uses Typer for CLI parsing and a Service-based approach for logic.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

import typer

from pymodeller.cli.commands import check, codegen, drift, example, setup, show_version
from pymodeller.cli.dev_tools import main_check, main_ci, main_test

app = typer.Typer(
    name="pymodeller",
    help="CLI tools for PyModeller",
    epilog="Dev Commands: dev [check | test | ci] -> Use 'pymodeller dev --help' for details.",
    no_args_is_help=True,
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

app.add_typer(dev_app, name="dev", help="Development and CI/CD tools for PyModeller")
app.command()(setup)
app.command()(example)
app.command()(check)
app.command()(codegen)
app.command()(drift)


@app.callback()
def core(version: bool | None = typer.Option(None, "--version", "-v", callback=show_version, is_eager=True)) -> None:
    """Console-script entry point — registered as 'orion-mcp'."""
    pass


def main() -> None:
    """Console-script entry point — registered as 'orion-mcp'."""
    app()


if __name__ == "__main__":
    main()
