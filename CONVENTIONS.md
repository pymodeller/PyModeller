# MCP Framework - Tech Stack & Code Conventions

This document is the technical reference for developers and AI agents working on this repository. It covers the stack, project structure, code conventions, and Makefile patterns. For workflows and architecture rules, see AGENTS.md.

---

## 🐍 Tech Stack

### Core dependencies (always prefer these)

| Library | Purpose | Usage |
|---|---|---|
| fastmcp | MCP server framework | Use FastMCP; tools are decorated with @mcp.tool() |
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
    ├── cli
    │     ├── __init__.py
    │     ├── cli.py
    │     ├── commands.py
    │     └── dev_tools.py
    ├── config.py
    ├── generators
    │     ├── __init__.py
    │     ├── enum_generator.py
    │     ├── peewee_generator.py
    │     └── pydantic_generator.py
    ├── loader.py
    ├── templates
    │     ├── __init__.py
    │     ├── base_settings.jinja
    │     ├── general_settings.jinja
    │     ├── init.jinja
    │     ├── master_pydantic.jinja
    │     ├── peewee_db.jinja
    │     ├── peewee_model.jinja
    │     └── pydantic_template.jinja
    ├── tool_runner.py
    ├── utils.py
    └── validator.py
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
