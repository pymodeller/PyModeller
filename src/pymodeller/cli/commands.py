"""Env-spec management CLI.

========================================================================================================================
Name:         pymodeller/env/cli.py
Description:  CLI entry-point for env-spec operations: example, check, diff, codegen, drift.
              Uses Typer for CLI parsing and a Service-based approach for logic.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

import typer
from dotenv import dotenv_values
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from pymodeller import __version__
from pymodeller.config import get_code_gen_config
from pymodeller.generators.env_generator import EnvGenerator
from pymodeller.generators.peewee_generator import PeeweeGenerator
from pymodeller.generators.pydantic_generator import _YAML_HASH_MARKER, PydanticGenerator
from pymodeller.loader import load_env_spec
from pymodeller.tool_runner import ToolRunner
from pymodeller.utils import compare_dirs, file_hash, get_file_hash
from pymodeller.validator import validate_env

# --- Constants & Defaults ---

code_gen_conf = get_code_gen_config()
console = Console()

_CONFIG_TOML = "--config=pyproject.toml"


# --- CLI Commands ---


def example(
    spec: Annotated[Path, typer.Option("--spec", "-s", help="Path to env_spec.yaml")] = code_gen_conf.spec,
    out: Annotated[Path, typer.Option("--out", "-o", help="Output path for .env.example")] = code_gen_conf.env_example,
    secrets_only: Annotated[bool, typer.Option("--secrets", "-ss", help="Flag for only secrets in .env")] = False,
) -> typer.Exit:
    """Generate a template .env.example from the YAML spec."""
    s = load_env_spec(spec)
    content = EnvGenerator().generate_example_content(spec=s, secrets_only=secrets_only)

    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    extra_comments = "with only secrets" if secrets_only else ""
    typer.echo(f" ✅ Created {out} {extra_comments}")
    return typer.Exit(code=0)


def yaml_file(
    spec: Annotated[Path, typer.Option("--spec", "-s", help="Path to env_spec.yaml")] = code_gen_conf.spec,
    out: Annotated[
        Path, typer.Option("--out", "-o", help="Output path for environment.yaml")
    ] = code_gen_conf.environment_file,
) -> typer.Exit:
    """Generate environment.yaml from the YAML spec."""
    s = load_env_spec(spec)
    content = EnvGenerator().generate_environment_yaml(spec=s)

    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    typer.echo(f" ✅ Created {out}.")
    return typer.Exit(code=0)


def check(
    spec: Annotated[Path, typer.Option("--spec", "-s", help="Path to env_spec.yaml")] = code_gen_conf.spec,
    env: Annotated[Path, typer.Option("--env", "-e", help="Path to .env file")] = code_gen_conf.env,
) -> typer.Exit:
    """Validate current .env file against the specification."""
    env_path = Path(env)
    if not env_path.exists():
        typer.echo(f"❌ {env} not found.")
        raise typer.Exit(1)

    values = {k: v for k, v in dotenv_values(env_path).items() if v is not None}
    result = validate_env(spec_path=spec, env=values)

    if not result.ok:
        typer.echo(f"❌ Issues found in {env}:")
        for issue in result.issues:
            typer.echo(f"  - {issue.name}: {issue.detail}")
        raise typer.Exit(1)

    typer.echo(f"✅ {env} is valid.")
    return typer.Exit(code=0)


def codegen(
    spec: Annotated[Path, typer.Option("--spec", "-s", help="Path to env_spec.yaml")] = code_gen_conf.spec,
    pydantic_out: Annotated[
        Path, typer.Option("--pydantic-out", "-pyo", help="Path for the generated Pydantic models")
    ] = code_gen_conf.pydantic_folder,
    peewee_out: Annotated[
        Path, typer.Option("--peewee-out", "-pwo", help="Path for the generated Peewee models")
    ] = code_gen_conf.peewee_folder,
    pydantic_master: Annotated[
        Path, typer.Option("--pydantic-master", "-pym", help="Path for the generated main Pydantic module")
    ] = code_gen_conf.pydantic_out,
    peewee_master: Annotated[
        Path, typer.Option("--peewee-master", "-pem", help="Path for the generated main Peewee module")
    ] = code_gen_conf.peewee_out,
) -> typer.Exit:
    """Generate typed Pydantic models for the environment."""
    s = load_env_spec(spec)
    yaml_hash = get_file_hash(Path(spec))

    typer.secho(" Step 1: Generating Pydantic Models", bold=True)
    out_path, models_dir = PydanticGenerator().generate_files(yaml_hash, s, pydantic_out, pydantic_master)

    if out_path:
        typer.secho("Step 1.A. Executing ruff commands over files generated", fg=typer.colors.BRIGHT_GREEN)
        ToolRunner.run_with_uv("ruff", ["check", str(out_path), _CONFIG_TOML, "--fix"])
        ToolRunner.run_with_uv("ruff", ["check", str(models_dir), _CONFIG_TOML, "--fix"])
        ToolRunner.run_with_uv("ruff", ["format", str(out_path), _CONFIG_TOML])
        ToolRunner.run_with_uv("ruff", ["format", str(models_dir), _CONFIG_TOML])
        typer.secho(
            f"      ✅ Pydantic models generated at {pydantic_out}",
            bold=True,
            fg=typer.colors.CYAN,
        )
    else:
        typer.secho(
            "      No declared pydantic models",
            bold=True,
            fg=typer.colors.CYAN,
        )

    typer.secho(" Step 2: Generating Peewee Models", bold=True)
    p_path, pm_dir = PeeweeGenerator().generate_files(s, peewee_out, peewee_master)

    if p_path:
        typer.secho("Step 2.A. Executing ruff commands over files generated", fg=typer.colors.BRIGHT_GREEN)
        ToolRunner.run_with_uv("ruff", ["check", str(p_path), _CONFIG_TOML, "--fix"])
        ToolRunner.run_with_uv("ruff", ["check", str(pm_dir), _CONFIG_TOML, "--fix"])
        ToolRunner.run_with_uv("ruff", ["format", str(p_path), _CONFIG_TOML])
        ToolRunner.run_with_uv("ruff", ["format", str(pm_dir), _CONFIG_TOML])
        typer.secho(
            f"      ✅ Peewee models generated at {peewee_out}",
            bold=True,
            fg=typer.colors.CYAN,
        )
    else:
        typer.secho(
            "      No declared peewee models",
            bold=True,
            fg=typer.colors.CYAN,
        )
    return typer.Exit(code=0)


def drift(
    spec: Annotated[Path, typer.Option("--spec", "-s", help="Path to env_spec.yaml")] = code_gen_conf.spec,
    data_model: Annotated[
        Path, typer.Option("--data-model", "-d", help="Path for the generated settings module")
    ] = code_gen_conf.pydantic_out,
) -> typer.Exit:
    """Check drift between YAML spec and generated code."""
    spec_path = Path(spec)
    dm_path = Path(data_model)
    banner_full("Checking differences between YAML and models.")
    if not dm_path.exists():
        typer.secho("❌ Data model file missing. Run codegen first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    current_hash = get_file_hash(spec_path)

    stored_hash = None
    with dm_path.open() as f:
        for line in f:
            if line.startswith(_YAML_HASH_MARKER):
                stored_hash = line.replace(_YAML_HASH_MARKER, "").strip()
                break

    if current_hash != stored_hash:
        typer.secho("❌ Drift detected! YAML spec has changed. Please run codegen.", fg=typer.colors.RED)
        raise typer.Exit(1)
    typer.secho(" No differences found. ", fg=typer.colors.CYAN)

    banner_full("Checking differences between models and yaml.")
    typer.secho(
        " Executing following commands:\n 1. Create tmp files \n 2. Calculating hash of generated code",
        fg=typer.colors.CYAN,
    )

    sync(spec)

    typer.echo("✅ No drift detected. Files are in sync.")
    return typer.Exit(code=0)


def sync(
    spec: Annotated[Path, typer.Option("--spec", "-s", help="Path to env_spec.yaml")] = code_gen_conf.spec,
) -> typer.Exit:
    """Check if generated models are in sync with the YAML spec."""
    original_cwd = Path.cwd()
    banner_full("Creating temporal files", "spring_green1")
    with tempfile.TemporaryDirectory(dir=".") as tmpdir:
        tmpdir = Path(tmpdir).relative_to(Path.cwd())

        tmp_pydantic_master = tmpdir / code_gen_conf.pydantic_out
        tmp_peewee_master = tmpdir / code_gen_conf.peewee_out
        tmp_pydantic_folder = tmpdir / code_gen_conf.pydantic_folder
        tmp_peewee_folder = tmpdir / code_gen_conf.peewee_folder

        codegen(
            spec=spec,
            peewee_master=tmp_peewee_master,
            pydantic_master=tmp_pydantic_master,
            peewee_out=tmp_peewee_folder,
            pydantic_out=tmp_pydantic_folder,
        )

        result_pydantic = compare_dirs(
            tmpdir / code_gen_conf.pydantic_folder,
            original_cwd / code_gen_conf.pydantic_folder,
        )
        result_peewee = compare_dirs(
            tmpdir / code_gen_conf.peewee_folder,
            original_cwd / code_gen_conf.peewee_folder,
        )
        banner_full("Comparing differences", "spring_green1")
        print_diff("Pydantic", result_pydantic)
        print_diff("Peewee", result_peewee)

        master_diff = {}

        if tmp_peewee_master.exists() and code_gen_conf.peewee_out.exists():
            master_diff.setdefault(
                "pydantic_master", file_hash(tmp_pydantic_master) != file_hash(code_gen_conf.pydantic_out)
            )

        if tmp_peewee_master.exists() and code_gen_conf.peewee_out.exists():
            master_diff.setdefault("peewee_master", file_hash(tmp_peewee_master) != file_hash(code_gen_conf.peewee_out))

        show_master_diff(master_diff)
        return typer.Exit(code=0)


def show_version(value: bool) -> typer.Exit | None:
    """Show version."""
    if value:
        typer.echo(f"PyModeller version {__version__}")
        raise typer.Exit(code=0)


def show_master_diff(master_diff: dict) -> None:
    """Show diff."""
    has_diff = False

    for name, diff in master_diff.items():
        if diff:
            has_diff = True

            path = ""
            if name == "pydantic_master":
                path = code_gen_conf.pydantic_out
            elif name == "peewee_master":
                path = code_gen_conf.peewee_out

            typer.secho(f" ❌ Modified: {path}", fg=typer.colors.RED)

    if not has_diff:
        typer.secho(" ✅ Master files are in sync", fg=typer.colors.GREEN, bold=True)


def print_diff(name: str, diff: dict) -> None:
    """Show the results."""
    typer.echo(f"\nComparing {name} models")

    if diff["equal"]:
        typer.echo("   ✅ In sync")
        return

    if diff["added"]:
        typer.echo("  + Added:")
        for f in diff["added"]:
            typer.echo(f"     - {f}")

    if diff["removed"]:
        typer.echo("  - Removed:")
        for f in diff["removed"]:
            typer.echo(f"     - {f}")

    if diff["modified"]:
        typer.echo("  ✏️ Modified:")
        for f in diff["modified"]:
            typer.echo(f"     - {f}")


def banner_full(message: str, color: str = "green") -> None:
    """Create a banner."""
    width = int(console.size.width * 2 / 3)
    console.print(
        Panel(
            Text(message, style=f"bold {color}", justify="center"),
            border_style=color,
            expand=True,
            width=width,
        )
    )


def setup() -> typer.Exit:
    """Generate models from yaml and .env.example."""
    codegen()
    example()
    return typer.Exit(code=0)
