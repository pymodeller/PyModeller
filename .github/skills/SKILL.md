# MCP Framework — Local Development Standards

Reference Guide for maintainable, type-safe development.
See CONVENTIONS.md for the full architectural specification.

## Hard Constraints

To ensure environment consistency and local portability, the following prohibitions apply:

- IO & Logging: NEVER use print() or the standard logging module. Use the project-specific get_logger factory (powered by loguru) exclusively.
- Dependency Management: NEVER use pip. All environment and package operations must be handled via uv.
- File Manipulation: NEVER use sed -i due to BSD/GNU incompatibilities. Always use portable redirection: sed "..." f > f.tmp && mv f.tmp f.
- Type Hinting: NEVER use Union[X, Y] or Optional[X]. Strictly use modern Python 3.10+ syntax: X | Y and X | None.
- Automation: NEVER use standalone .sh scripts. Logic must reside in Makefile targets that delegate to Python CLI tools.

## Stack at a Glance

| Domain | Standard Implementation |
| :--- | :--- |
| Runtime | Python 3.13 strictly (utilizing match, tomllib, and TypeIs) |
| Package Ops | uv sync, uv add, uv run |
| CLI Engines | typer.Typer() with modular add_typer() composition |
| Observability | loguru via the internal get_logger(__name__) wrapper |
| Terminal UI | rich.console for Panels, Tables, and Progress tracking |
| Settings | pydantic-settings (v2+) with unique environment prefixes |

## Type Annotations

We prioritize readability and native protocols over legacy typing aliases.

```python  
from __future__ import annotations  
# Only for forward references  
from collections.abc import Callable, Sequence  # Avoid 'typing' aliases   

def fn(x: str, cb: Callable[[str], bool]) -> str | None:      
    """Example of modern union types and abstract collections."""     
    ... 
```
## Structured Logging

Logs must be contextual and descriptive to facilitate efficient local debugging.

```python  
from loguru import get_logger  
logger = get_logger(__name__)    
logger.info("Starting process: {name}", name=value)  
logger.warning("Condition met: {reason}", reason=details)  
logger.error("Execution failed: {err}", err=exc)  
```
## CLI Command Pattern

Commands are organized through sub-app composition to maintain scalability.

```python  
app = typer.Typer(name="sync-tool", help="Resource synchronization.")    
@app.command()  
def perform_sync(target: str = typer.Argument(..., help="Destination target.")) -> None:          
    """Sync local state with a remote destination."""          
    logger.info("Running sync for: {target}", target=target)   
    # Sub-apps are registered in the main entry point: 
    # main_app.add_typer(app) 
```
## Makefile Conventions

The Makefile serves as the primary developer interface:

- Binary Resolution: Never rely on the global $PATH. Dynamically resolve the virtual environment path (e.g., BIN := .venv/bin/).
- Logic Delegation: Keep targets minimal. The Makefile prepares the shell; Python handles the business logic.
- Environment Isolation: Always export variables to ensure visibility across sub-shells and spawned processes.

## Quality Gates (Run before any change)

Before committing code, the local quality pipeline must pass:

```bash  
make ci   # Executes: checkmake + ruff + typecheck + pytest  
```
This ensures the codebase remains compliant with our strict linting and typing standards.