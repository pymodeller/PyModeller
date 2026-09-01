"""Utils module.

========================================================================================================================
Name:         pymodeller/utils.py
Description:  Utils module.
Project:      PyModeller

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

import ast
import hashlib
import re
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape


def get_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_hash(path: Path) -> str:
    """Generate hash."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def compare_dirs(dir1: Path, dir2: Path) -> dict:
    """Compare dirs."""
    files1 = {f.relative_to(dir1): f for f in dir1.rglob("*") if f.is_file()}
    files2 = {f.relative_to(dir2): f for f in dir2.rglob("*") if f.is_file()}

    set1 = set(files1.keys())
    set2 = set(files2.keys())

    added = set1 - set2
    removed = set2 - set1
    common = set1 & set2

    modified = [rel for rel in common if file_hash(files1[rel]) != file_hash(files2[rel])]

    return {
        "added": sorted(added),
        "removed": sorted(removed),
        "modified": sorted(modified),
        "equal": not (added or removed or modified),
    }


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case or UPPER_CASE to camelCase."""
    components = snake_str.lower().replace(" ", "").split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def to_snake_case(name: str) -> str:
    """Convert CamelCase or mixed strings to snake_case.

    Args:
        name: The string to convert (e.g., "CamelCase", "camelCase", "my-header").

    Returns:
        str: The converted snake_case string.
    """
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)

    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)

    return s2.replace(" ", "_").replace("-", "_").lower().replace("__", "_")


def to_pascal_case(text: str) -> str:
    """Generate class."""
    camel = to_camel_case(text)
    if not camel:
        return ""
    return camel[0].upper() + camel[1:]


def get_variants(name: str) -> str:
    """Convert a string into snake_case, camelCase, and UPPER_CASE.
    Returns a list of unique values.

    Args:
        name: The input string (supports snake_case, camelCase, etc.)

    Returns:
        List of unique strings: [snake, camel, upper]
    """
    # 1. Normalize: Handles camelCase, snake_case and spaces
    # It inserts a space before any capital letter and replaces separators with spaces
    normalized = re.sub(r"(?<!^)(?=[A-Z])", " ", name).replace("-", "_")

    # 2. Extract words and convert to lowercase
    words = [word.lower() for word in normalized.split() if word]

    if not words:
        return ""

    # 3. Build variants
    snake = to_snake_case(name)
    camel = to_camel_case(snake)
    upper = snake.upper()
    order_list = sorted({f'"{snake}"', f'"{camel}"', f'"{upper}"'})
    val_alias_opt = ",\n            ".join(order_list)
    return f"AliasChoices(\n            {val_alias_opt}\n        )"


def write_env_file(path: Path, data: dict, prefix: str = "") -> None:
    """Save env file."""
    lines = []

    def flatten(d: dict, current_prefix: str) -> None:
        """Flatten names."""
        for k, v in d.items():
            new_key = f"{current_prefix}{k.upper()}"
            if isinstance(v, dict):
                flatten(v, f"{new_key}__")
            else:
                lines.append(f"{new_key}={v}")

    flatten(data, prefix)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def deep_merge(base: dict, overrides: dict) -> dict:
    """Combine two dicts."""
    for key, value in overrides.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def generate_init_file(package_dir: Path | str) -> Path:
    """Inspects Python files within a directory, extracts classes, and generates an __init__.py file.

    Scans all `.py` files inside the target directory, gathers exported class definitions,
    and uses a Jinja2 template to generate an alphabetically sorted `__init__.py`.

    Args:
        package_dir: The directory path containing the Python files to inspect.

    Returns:
        Path: The file path to the generated `__init__.py`.
    """
    env = Environment(loader=PackageLoader("pymodeller", "templates"), autoescape=select_autoescape())

    package_path = Path(package_dir)
    models_data: list[dict[str, str]] = []

    # 1. Escanear todos los archivos .py (omitiendo __init__.py)
    for file_path in package_path.glob("*.py"):
        if file_path.name == "__init__.py":
            continue

        module_name = file_path.stem
        code = file_path.read_text(encoding="utf-8")

        # 2. Extraer los nombres de las clases definidas en el archivo con AST
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name not in ["Meta"]:
                models_data.append({
                    "module": module_name,
                    "class_name": node.name,
                })

    # 3. Ordenar alfabéticamente por nombre de la clase
    models_data.sort(key=lambda x: x["class_name"])

    # 4. Renderizar con Jinja2
    template = env.get_template("init.jinja")
    init_content = template.render(models=models_data)

    # 5. Escribir el __init__.py
    init_path = package_path / "__init__.py"
    init_path.write_text(init_content, encoding="utf-8")
    return init_path


def ensure_init_py_in_subdirectories(root_dir: str | Path) -> list[Path]:
    """Recursively walks through all directories starting from root_dir
    and creates an empty __init__.py file if one does not exist.

    Args:
        root_dir: The target directory path to inspect.

    Returns:
        List of Path objects representing all __init__.py files created.
    """
    base_path = Path(root_dir)

    if not base_path.exists():
        raise FileNotFoundError(f"The specified path does not exist: {base_path}")

    created_files: list[Path] = []

    # Check the root directory itself first
    directories = [d for d in base_path.rglob("*") if d.is_dir()]
    directories.sort(reverse=True)
    directories.append(base_path)

    # 2. Process each directory and generate its __init__.py file
    for folder in directories:
        init_file = folder / "__init__.py"
        # Check if __init__.py doesn't exist OR if it exists but is completely empty (size == 0)
        if not init_file.exists() or init_file.stat().st_size == 0:
            generated_path = generate_init_file(folder)
            created_files.append(generated_path)

    return created_files


def get_import_path(base_dir: str, subfolder: str, file_name: str) -> str:
    """Converts a file path structure into a valid Python dot-notation import path.

    Example:
        `'./src/event_driven'`, `'domain/schemas'`, `'user.py'`
        becomes `'event_driven.domain.schemas.user'`

    Args:
        base_dir: The base directory path (e.g., './src/event_driven').
        subfolder: The relative subfolder path (e.g., 'domain/schemas').
        file_name: The target filename (e.g., 'user.py').

    Returns:
        str: The dot-separated Python import module path.
    """
    path = Path(base_dir) / subfolder / file_name
    # Strip the .py extension and skip the root code folder (e.g., 'src') if it is not a package
    parts = [p for p in path.with_suffix("").parts if p not in (".", "src")]
    return ".".join(parts)
