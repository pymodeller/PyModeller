"""pymodeller-check: Development and CI utility tools.

========================================================================================================================
Name:         core/dev_tools.py
Description:  Static analysis, linting, and testing orchestrator for the PyModeller project.
              Supports Ruff for linting/formatting and Pyrefly for type checking.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from __future__ import annotations

from logging import getLogger

import typer

from pymodeller.tool_runner import ToolRunner

logger = getLogger(__name__)


def main_check() -> typer.Exit:
    """Orchestrate all static analysis checks.
    Includes formatting, linting, and type checking.
    """
    logger.info("--- Starting PyModeller Static Checks ---")

    # 1. Ruff: Formatting
    logger.info("Running Ruff Formatter...")
    ToolRunner.run_with_uv("ruff", ["format", "--config=pyproject.toml", "--exclude", r"\.venv"])

    # 2. Ruff: Linting and Fixes
    logger.info("Running Ruff Linter...")
    ToolRunner.run_with_uv("ruff", ["check", "--fix", "--config=pyproject.toml", "--exclude", r"\.venv"])

    # 3. Pyrefly: Static Type Analysis
    logger.info("Running Pyrefly Type Checker...")
    ToolRunner.run_with_uv("pyrefly", ["check", "src"])

    logger.info("Static checks completed successfully ✅")



def main_test() -> typer.Exit:
    """Execute the test suite using pytest."""
    logger.info("--- Starting PyModeller Test Suite ---")
    ToolRunner.run_with_uv("pytest", ["--check"])
    logger.info("All tests passed ✅")
    return typer.Exit(code=0)


def main_ci() -> typer.Exit:
    """Full CI pipeline: Checks followed by Tests."""
    logger.info("--- Starting PyModeller CI Pipeline ---")
    main_check()
    main_test()
    logger.info("CI Pipeline completed successfully ✅")
    return typer.Exit(code=0)


if __name__ == "__main__":
    # Default to main_check if run as a script
    main_check()
