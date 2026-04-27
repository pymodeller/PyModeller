"""Utils module."""

import hashlib
import re
from pathlib import Path


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
