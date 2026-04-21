from pathlib import Path

from pymodeller.generators.enum_generator import EnumGenerator


def test_enum_generation_logic(tmp_path: Path) -> None:
    """Verify that YAML types are correctly converted to Python Enum syntax."""
    yaml_file = tmp_path / "test_enums.yaml"
    output_file = tmp_path / "output.py"

    yaml_content = """
    TestEnum:
      type: int
      values:
        VAL_A: 1
    """
    yaml_file.write_text(yaml_content)

    EnumGenerator.generate(yaml_file, output_file)

    generated_code = output_file.read_text()
    assert "class TestEnum(Enum):" in generated_code
    assert "VAL_A = 1" in generated_code  # Ensure no quotes for int
    assert '"""TestEnum auto-generated enum."""' in generated_code
