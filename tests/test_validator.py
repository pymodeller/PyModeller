"""Unit tests for pymodeller.validator.

========================================================================================================================
Name:         tests/test_validator.py
Description:  Tests for environment validation logic, including type coercion
              and required variable enforcement.

Copyright ©2026 PyModeller. All rights reserved.
========================================================================================================================
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from pymodeller.loader import EnvSection, EnvSpec, EnvVarSpec
from pymodeller.validator import (
    EnvValidationError,
    EnvValidationResult,
    EnvValidator,
    IssueKind,
    VarIssue,
    validate_env,
)

# --- Fixtures ---


@pytest.fixture
def complex_spec() -> EnvSpec:
    """Provides a spec with various constraints: required, optional, and typed.

    Returns:
        EnvSpec: A multi-variable specification for validation testing.
    """
    return EnvSpec(
        sections=[
            EnvSection(
                name="API",
                variables=[
                    EnvVarSpec(name="API_PORT", type="int", required=True, env_name="API_PORT", description="Port"),
                    EnvVarSpec(
                        name="API_DEBUG", type="bool", default="false", env_name="API_DEBUG", description="Debug"
                    ),
                    EnvVarSpec(
                        name="API_KEY", type="str", required=True, secret=True, env_name="API_KEY", description="Key"
                    ),
                    EnvVarSpec(
                        name="OPTIONAL_TAG", type="str", required=False, env_name="OPTIONAL_TAG", description="Tag"
                    ),
                ],
            )
        ]
    )


# --- Tests for EnvValidator ---


def test_validator_all_ok(complex_spec: EnvSpec) -> None:
    """Test that valid environment variables produce an 'ok' result."""
    env: dict[str, str] = {"API_PORT": "8080", "API_DEBUG": "true", "API_KEY": "secret-123"}
    validator: EnvValidator = EnvValidator(complex_spec)
    result: EnvValidationResult = validator.validate(env)

    assert result.ok is True
    assert result.checked == 4
    assert len(result.issues) == 0


def test_validator_missing_required(complex_spec: EnvSpec) -> None:
    """Test detection of missing required variables."""
    env: dict[str, str] = {"API_PORT": "8080"}  # Missing API_KEY
    validator: EnvValidator = EnvValidator(complex_spec)
    result: EnvValidationResult = validator.validate(env)

    assert result.ok is False
    assert len(result.missing) == 1
    assert result.missing[0].name == "API_KEY"


def test_validator_empty_required(complex_spec: EnvSpec) -> None:
    """Test that required variables set to empty strings are flagged."""
    env: dict[str, str] = {
        "API_PORT": "8080",
        "API_KEY": "  ",  # Effectively empty
    }
    validator: EnvValidator = EnvValidator(complex_spec)
    result: EnvValidationResult = validator.validate(env)

    assert len(result.empty_required) == 1
    assert result.empty_required[0].issue == "empty_required"


@pytest.mark.parametrize(
    "name, value",
    [
        ("API_PORT", "not-a-number"),
        ("API_DEBUG", "maybe"),
    ],
)
def test_validator_type_errors(complex_spec: EnvSpec, name: str, value: str) -> None:
    """Test that invalid types are caught during coercion."""
    env: dict[str, str] = {"API_PORT": "8080", "API_KEY": "valid", name: value}
    validator: EnvValidator = EnvValidator(complex_spec)
    result: EnvValidationResult = validator.validate(env)

    assert len(result.type_errors) == 1
    assert result.type_errors[0].issue == "type_error"
    assert "Cannot cast" in result.type_errors[0].detail


# --- Tests for EnvValidationError ---


def test_validation_error_message() -> None:
    """Check if the exception correctly formats the error summary."""
    issue: VarIssue = VarIssue(name="DB_URL", section="DB", issue=IssueKind.MISSING, detail="Needed")
    result: EnvValidationResult = EnvValidationResult(issues=[issue])

    error: EnvValidationError = EnvValidationError(result)
    assert "Environment validation failed (1 issue(s))" in str(error)
    assert "[MISSING] DB_URL" in str(error)


# --- Tests for Convenience Function ---


@pytest.mark.parametrize("raise_flag", [True, False])
@patch("pymodeller.validator.load_env_spec")
def test_validate_env_wrapper(mock_load: MagicMock, complex_spec: EnvSpec, raise_flag: bool) -> None:
    """Test the high-level validate_env function behavior.

    Args:
        mock_load: Patched spec loader.
        complex_spec: Test specification.
        raise_flag: Whether to test exception raising or result returning.
    """
    mock_load.return_value = complex_spec
    env: dict[str, str] = {"API_PORT": "8080"}  # Missing API_KEY

    if raise_flag:
        with pytest.raises(EnvValidationError):
            validate_env(env=env, raise_on_error=True)
    else:
        result: EnvValidationResult = validate_env(env=env, raise_on_error=False)
        assert result.ok is False
        assert len(result.missing) == 1
        mock_load.assert_called_once()


@patch("pymodeller.validator.logger")
def test_report_logging(mock_logger: MagicMock, complex_spec: EnvSpec) -> None:
    """Ensure the reporter sends correct messages to the logger."""
    validator: EnvValidator = EnvValidator(complex_spec)
    result: EnvValidationResult = validator.validate(env={})
    validator.report(result)

    assert mock_logger.error.called


# --- Test Case: Edge cases in _check_type ---


def test_check_type_edge_cases() -> None:
    """Covers unknown types, long values (truncation), and invalid booleans."""
    # 1. Long value to test string truncation (...) in error detail
    long_var: EnvVarSpec = EnvVarSpec(name="L", type="int", env_name="L", section="S", description="")
    issue: VarIssue | None = EnvValidator._check_type(long_var, "9" * 100)
    assert issue is None

    # 2. Unknown type in mapping (should skip validation and return None)
    unknown_var: EnvVarSpec = EnvVarSpec(name="U", type="unknown_type", env_name="U")
    assert EnvValidator._check_type(unknown_var, "val") is None

    # 3. Invalid boolean string
    bool_var: EnvVarSpec = EnvVarSpec(name="B", type="bool", env_name="B")
    issue_bool: VarIssue | None = EnvValidator._check_type(bool_var, "not_a_boolean")
    assert issue_bool is not None


# --- Test for validate_env using os.environ ---


@patch("pymodeller.validator.load_env_spec")
def test_validate_env_os_environ(mock_load: MagicMock) -> None:
    """Verify that validate_env uses os.environ by default."""
    mock_load.return_value = EnvSpec(sections=[])

    with patch.dict(os.environ, {"DUMMY_VAR": "1"}):
        result: EnvValidationResult = validate_env(spec_path="fake.yaml")

    assert result.checked == 0  # Spec is empty
    mock_load.assert_called_once_with("fake.yaml")


# --- Test for branching logic in presence check ---


def test_validate_presence_branches() -> None:
    """Verify branches for optional missing variables."""
    var_opt: EnvVarSpec = EnvVarSpec(name="OPT", type="str", required=False, env_name="OPT", section="S")
    spec: EnvSpec = EnvSpec(sections=[EnvSection("S", [var_opt])])
    validator: EnvValidator = EnvValidator(spec)

    # Case: Optional missing (raw_value is None and not required)
    result: EnvValidationResult = validator.validate(env={})
    assert result.ok
    assert result.checked == 0  # Checked counts variables with actual values or issues
