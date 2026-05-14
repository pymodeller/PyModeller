from unittest.mock import MagicMock, patch

import pytest

from pymodeller.generators.env_generator import EnvGenerator
from pymodeller.loader import SectionType


@pytest.fixture
def generator() -> EnvGenerator:
    """Initialize the generator for testing."""
    return EnvGenerator()


def test_generate_example_content_filters_non_settings_sections(generator: EnvGenerator) -> None:
    """Test that only sections with type SectionType.SETTINGS are processed.

    Input: A spec with one SETTINGS section and one OTHER section.
    Output: Verifies create_section is only called for the SETTINGS section.
    """
    # 1. Setup Mocks
    mock_section_settings = MagicMock(type=SectionType.SETTINGS, variables=[MagicMock(secret=False)])
    mock_section_other = MagicMock(type=SectionType.MODEL, variables=[MagicMock(secret=False)])

    mock_spec = MagicMock()
    mock_spec.sections = [mock_section_settings, mock_section_other]

    # 2. Execute and Patch
    with patch.object(generator, "create_section") as mock_create_section, patch.object(generator.env, "get_template"):
        generator.generate_example_content(mock_spec)

        # 3. Assertions
        # Should only be called once (for the SETTINGS section)
        assert mock_create_section.call_count == 1
        # The first argument to the call is the section object
        called_section = mock_create_section.call_args[0][1]
        assert called_section.type == SectionType.SETTINGS


def test_generate_example_content_secrets_only_true(generator: EnvGenerator) -> None:
    """Test filtering when secrets_only is True.

    Input: A section with one secret variable and one public variable.
    Output: Verifies create_section only receives the secret variable.
    """
    # 1. Setup variables
    secret_var = MagicMock(secret=True)
    public_var = MagicMock(secret=False)

    mock_section = MagicMock(type=SectionType.SETTINGS, variables=[secret_var, public_var])
    mock_spec = MagicMock(sections=[mock_section])

    # 2. Execute
    with patch.object(generator, "create_section") as mock_create_section, patch.object(generator.env, "get_template"):
        generator.generate_example_content(mock_spec, secrets_only=True)

        # 3. Assertions
        # The third argument (variables_to_show) should only contain the secret_var
        variables_passed = mock_create_section.call_args[0][2]
        assert secret_var in variables_passed
        assert public_var not in variables_passed


def test_generate_example_content_skips_empty_variables_list(generator: EnvGenerator) -> None:
    """Test that sections with no matching variables (after filtering) are skipped.

    Input: secrets_only=True but section only contains public variables.
    Output: Verifies create_section is never called.
    """
    # 1. Setup
    public_var = MagicMock(secret=False)
    mock_section = MagicMock(type=SectionType.SETTINGS, variables=[public_var])
    mock_spec = MagicMock(sections=[mock_section])

    # 2. Execute
    with patch.object(generator, "create_section") as mock_create_section, patch.object(generator.env, "get_template"):
        generator.generate_example_content(mock_spec, secrets_only=True)

        # 3. Assertions
        # Since variables_to_show was empty, create_section should NOT be called (line 60-61)
        mock_create_section.assert_not_called()


def test_generate_environment_yaml_filters_secrets(generator: EnvGenerator) -> None:
    """Test that generate_environment_yaml excludes variables marked as secrets.

    Input:
        A spec containing one section with one secret variable and one public variable.
    Output:
        Verifies that create_section is called only with the public variable.
    """
    # 1. Setup Mock Variables
    public_var = MagicMock(secret=False, name="PublicVar")
    secret_var = MagicMock(secret=True, name="SecretVar")

    # 2. Setup Mock Section and Spec
    mock_section = MagicMock(type=SectionType.SETTINGS)
    mock_section.variables = [public_var, secret_var]

    mock_spec = MagicMock()
    mock_spec.sections = [mock_section]

    # 3. Patch create_section and template loading
    with patch.object(generator, "create_section") as mock_create_section, patch.object(generator.env, "get_template"):
        generator.generate_environment_yaml(mock_spec)

        # 4. Assertions
        # Get the list of variables passed to create_section (3rd argument)
        variables_passed = mock_create_section.call_args[0][2]

        assert public_var in variables_passed
        assert secret_var not in variables_passed
        assert len(variables_passed) == 1


def test_generate_environment_yaml_skips_sections_with_only_secrets(generator: EnvGenerator) -> None:
    """Test that sections containing only secret variables are skipped entirely.

    Input:
        A spec where the only SETTINGS section contains only secret variables.
    Output:
        Verifies that create_section is never called (due to the 'continue' block).
    """
    # 1. Setup Mock with only secrets
    secret_var = MagicMock(secret=True)
    mock_section = MagicMock(type=SectionType.SETTINGS, variables=[secret_var])
    mock_spec = MagicMock(sections=[mock_section])

    # 2. Execute
    with patch.object(generator, "create_section") as mock_create_section, patch.object(generator.env, "get_template"):
        generator.generate_environment_yaml(mock_spec)

        # 3. Assertions
        # create_section should not be called because variables_to_show becomes empty
        mock_create_section.assert_not_called()


# def test_generate_environment_yaml_renders_template(generator: EnvGenerator) -> None:
#     """Test that the method correctly calls the Jinja2 render method with the collected lines.
#
#     Input:
#         A valid spec with one public variable.
#     Output:
#         Verifies the template is rendered with the 'env_lines' key.
#     """
#     # 1. Setup
#     mock_var = MagicMock(secret=False)
#     mock_section = MagicMock(type=SectionType.SETTINGS, variables=[mock_var])
#     mock_spec = MagicMock(sections=[mock_section])
#
#     # Mock the template object
#     mock_template = MagicMock()
#
#     # 2. Execute
#     with (
#         patch.object(generator.env, "get_template", return_value=mock_template),
#         patch.object(generator, "create_section", side_effect=lambda lines, s, v: lines.append("test_line")),
#     ):
#         generator.generate_environment_yaml(mock_spec)
#
#         # 3. Assertions
#         # Verify the template was loaded by name
#         generator.env.get_template.assert_called_once_with("environment_yaml.jinja")
#
#         # Verify render was called with the lines appended by create_section
#         mock_template.render.assert_called_once_with(env_lines=["test_line"])
