"""Env validator.

========================================================================================================================
Name:         core/env/validator.py
Description:  Validates the runtime environment against the env_spec.yaml contract.
              Reports missing required variables, type mismatches, and secret exposure
              with structured, human-readable output via the project logger.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum
from logging import getLogger
from pathlib import Path

from pymodeller.loader import BOOL_VALUES, YAML_TYPE_MAP, EnvSpec, EnvVarSpec, load_env_spec

logger = getLogger(__name__)

# Python builtins keyed by normalised YAML type name
_PYTHON_CAST: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
}


class IssueKind(StrEnum):
    """Issue kind."""

    MISSING = "missing"
    EMPTY_REQUIRED = "empty_required"
    TYPE_ERROR = "type_error"


# ──────────────────────────────────────────────────────────────────────────────
# Result dataclasses
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class VarIssue:
    """A single validation problem for one environment variable."""

    name: str
    section: str
    issue: IssueKind
    detail: str = ""


@dataclass
class EnvValidationResult:
    """Aggregated result of a full environment validation run."""

    issues: list[VarIssue] = field(default_factory=list)
    checked: int = 0

    @property
    def ok(self) -> bool:
        """True when no issues were found."""
        return len(self.issues) == 0

    @property
    def missing(self) -> list[VarIssue]:
        """Variables that are required but completely absent from the environment."""
        return [i for i in self.issues if i.issue == IssueKind.MISSING]

    @property
    def empty_required(self) -> list[VarIssue]:
        """Variables that are required but set to an empty string."""
        return [i for i in self.issues if i.issue == IssueKind.EMPTY_REQUIRED]

    @property
    def type_errors(self) -> list[VarIssue]:
        """Variables whose value cannot be coerced to the declared type."""
        return [i for i in self.issues if i.issue == IssueKind.TYPE_ERROR]


# ──────────────────────────────────────────────────────────────────────────────
# Exception
# ──────────────────────────────────────────────────────────────────────────────


class EnvValidationError(RuntimeError):
    """Raised when required environment variables are missing or malformed."""

    def __init__(self, result: EnvValidationResult) -> None:
        """Initialise the error with a full validation result."""
        self.result = result
        lines = [f"Environment validation failed ({len(result.issues)} issue(s)):"]
        for issue in result.issues:
            lines.append(f"  [{issue.issue.upper()}] {issue.name} ({issue.section}) — {issue.detail}")
        super().__init__("\n".join(lines))


# ──────────────────────────────────────────────────────────────────────────────
# Validator
# ──────────────────────────────────────────────────────────────────────────────


class EnvValidator:
    """Validates the running process environment against an EnvSpec.

    Usage::

        spec = load_env_spec("env_spec.yaml")
        validator = EnvValidator(spec)
        result = validator.validate()
        if not result.ok:
            validator.report(result)
    """

    def __init__(self, spec: EnvSpec) -> None:
        """Initialise the validator with a parsed EnvSpec."""
        self._spec = spec

    # ── public ────────────────────────────────────────────────────────────────

    def validate(self, env: dict[str, str] | None = None) -> EnvValidationResult:
        """Run the full validation pass.

        Args:
            env: Optional dict of environment variables to validate against.
                 Defaults to ``os.environ``.

        Returns:
            EnvValidationResult with all discovered issues.
        """
        env = env if env is not None else dict(os.environ)
        result = EnvValidationResult()

        for var in self._spec.all_vars:
            result.checked += 1
            raw_value = env.get(var.env_name)

            # ── presence checks ───────────────────────────────────────────────
            if raw_value is None:
                if var.required:
                    result.issues.append(
                        VarIssue(
                            name=var.name,
                            section=var.section,
                            issue=IssueKind.MISSING,
                            detail=f"Required variable not set. {var.description}",
                        )
                    )
                # optional & absent → nothing to do
                continue

            if var.required and raw_value.strip() == "":
                result.issues.append(
                    VarIssue(
                        name=var.name,
                        section=var.section,
                        issue=IssueKind.EMPTY_REQUIRED,
                        detail="Variable is required but its value is empty.",
                    )
                )
                continue

            # ── type check ────────────────────────────────────────────────────
            type_issue = self._check_type(var, raw_value)
            if type_issue:
                result.issues.append(type_issue)

        return result

    @staticmethod
    def report(result: EnvValidationResult) -> None:
        """Log a human-readable summary of the validation result.

        Args:
            result: The result produced by :meth:`validate`.
        """
        total = result.checked
        issues = len(result.issues)

        if result.ok:
            logger.info(f"✅ ENV OK — {total} variables checked, no issues found.")
            return

        logger.error(f"❌ ENV ISSUES — {total} checked, {issues} problem(s) found:")

        if result.missing:
            logger.error(f"  Missing required ({len(result.missing)}):")
            for issue in result.missing:
                logger.error(f"    ✗ {issue.name:<35} [{issue.section}] {issue.detail}")

        if result.empty_required:
            logger.error(f"  Empty required ({len(result.empty_required)}):")
            for issue in result.empty_required:
                logger.error(f"    ✗ {issue.name:<35} [{issue.section}] {issue.detail}")

        if result.type_errors:
            logger.warning(f"  Type errors ({len(result.type_errors)}):")
            for issue in result.type_errors:
                logger.warning(f"    ⚠ {issue.name:<35} [{issue.section}] {issue.detail}")

    # ── private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _check_type(var: EnvVarSpec, raw_value: str) -> VarIssue | None:
        """Attempt to coerce *raw_value* to the declared type.

        Returns a VarIssue if coercion fails, otherwise None.
        """
        # Empty value — nothing to cast, skip silently
        if not raw_value.strip():
            return None

        normalised = YAML_TYPE_MAP.get(var.type.lower())
        cast = _PYTHON_CAST.get(normalised or "")

        if cast is None:
            # Unknown type declared in spec — skip silently
            return None

        try:
            if cast is bool:
                if raw_value.strip().lower() not in BOOL_VALUES:
                    raise ValueError(raw_value)
            else:
                cast(raw_value)
        except (ValueError, TypeError):
            display = raw_value if len(raw_value) <= 40 else raw_value[:37] + "..."
            return VarIssue(
                name=var.name,
                section=var.section,
                issue=IssueKind.TYPE_ERROR,
                detail=f"Cannot cast '{display}' to {var.type}.",
            )

        return None


# ──────────────────────────────────────────────────────────────────────────────
# Convenience function
# ──────────────────────────────────────────────────────────────────────────────


def validate_env(
    spec_path: str | Path | None = None,
    *,
    env: dict[str, str] | None = None,
    raise_on_error: bool = False,
) -> EnvValidationResult:
    """Load the env spec and validate the current environment in one call.

    Typical usage at application startup::

        from pyModeller import validate_env

        validate_env(raise_on_error=True)

    Args:
        spec_path: Path to ``env_spec.yaml``. Defaults to CWD.
        env: Override for the environment dict (useful in tests).
        raise_on_error: If True, raises EnvValidationError when required
                        variables are missing or empty.

    Returns:
        EnvValidationResult

    Raises:
        EnvValidationError: Only when *raise_on_error* is True and issues exist.
        FileNotFoundError: If the spec file cannot be found.
    """
    spec = load_env_spec(spec_path)
    validator = EnvValidator(spec)
    result = validator.validate(env=env)
    validator.report(result)

    if raise_on_error and not result.ok:
        critical = result.missing + result.empty_required
        if critical:
            raise EnvValidationError(result)

    return result
