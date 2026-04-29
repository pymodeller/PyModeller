# Tech Stack & Code Conventions

This document is the technical reference for developers and AI agents working on this repository. It covers the stack, project structure, code conventions, and Makefile patterns. For workflows and architecture rules, see AGENTS.md.

---

## 🐍 Tech Stack

### Core dependencies (always prefer these)

| Library | Purpose | Usage |
|---|---|---|
| typer | CLI commands | Create sub-apps with typer.Typer(), register with app.add_typer() |
| loguru | Logging | Use the internal get_logger factory — never print() or standard logging |
| rich | Terminal output | Use rich.console.Console and rich.panel.Panel for panels/tables |
| pydantic | Data models & settings | Use BaseSettings for config classes with env prefix |

### Dev toolchain

| Tool | Role | Key config |
|---|---|---|
| uv | Package manager | uv run, uv sync, uv add — never pip |
| ruff | Linter + formatter | Line length 120, complexity ≤ 10, Google docstrings |
| pyright | Type checker | Strict — always annotate all args and return types |
| pytest + pytest-asyncio | Tests | Full async support, coverage reports |
| pre-commit | Git hooks | Runs ruff + type checks before every commit |
| checkmake | Makefile linter | Strict target line limits — keep targets short |

### Python version
- Python 3.13 strictly (requires-python = ">=3.13,<3.14").
- Use modern syntax: X | Y unions, match statements, f-strings (3.12+), etc.
- Avoid typing module aliases that have collections.abc equivalents.

---

## 🗂 Project Structure

```
src
├── __main__.py
└── pymodeller
    ├── __init__.py
    ├── cli                                 # CLI folder
    │     ├── __init__.py
    │     ├── cli.py                        # CLI typer definition
    │     ├── commands.py                   # Commands definitios to use in typer
    │     └── dev_tools.py                  # Dev tools commands included in typer
    ├── config.py                           # General package configuration
    ├── generators
    │     ├── __init__.py
    │     ├── enum_generator.py             # Generator of enum class
    │     ├── peewee_generator.py           # Generador peeweee models
    │     └── pydantic_generator.py         # Generator of pydantic and pydantic_settings models
    ├── loader.py
    ├── templates                           # Folder with differents templates of jinja
    │     ├── __init__.py
    │     ├── base_settings.jinja           # Template for base settings with custom configuration
    │     ├── general_settings.jinja        # Template for others settings class with use base_settings
    │     ├── init.jinja                    # Init template
    │     ├── master_pydantic.jinja         # Master pydantic definitio
    │     ├── peewee_db.jinja               # Definition of database connection
    │     ├── peewee_model.jinja            # Definition of peewee models
    │     └── pydantic_template.jinja       # Template for basemodels from pydantic
    ├── tool_runner.py                      # Class that execute commands with uv or subprocess
    ├── utils.py                            # Group of useful function to execute the package
    └── validator.py                        # Validator, responsable of correct input
```
---

## ✍️ Code Conventions

### File header (required for every new Python file)

```python
"""Module title.

========================================================================================================================
Name:         path/filename.py
Description:  Brief description of the module's purpose.
Author:       PyModeller
Status:       Development
Copyright ©2026. All rights reserved.
========================================================================================================================
"""
```

### Docstrings — Google style

```python
def execute_action(flag: bool) -> bool:
    """Short one-line summary.

    Args:
        flag: Description of the input string.
        Returns:
            True if successful, False otherwise.
    """

```
### Imports — isort order

```python
from __future__ import annotations

from collections.abc import Callable

from loguru import logger


```
### Type annotations

- Always annotate all function arguments and return types.
- Prefer collections.abc over typing for Callable, Iterator, Sequence, etc.
- Use X | Y union syntax (Python 3.10+ style), not Union[X, Y].
- Use X | None instead of Optional[X].

---

## 🔧 Makefile Patterns

### Philosophy
- Short targets: Line limits are strictly enforced. Logic belongs in Python scripts or CLI commands.
- Unified entry points: Everything is a Make target or uv run <bin> ....
- Inheritance: Always export variables so child processes inherit .env settings.
