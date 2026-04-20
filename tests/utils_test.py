from pathlib import Path

from pymodeller.utils import compare_dirs, file_hash, get_variants, to_camel_case, to_snake_case


class TestUtils:
    """Unit tests for utility functions covering file operations and string manipulations."""

    # --- Tests for file_hash (Lines 10-13) ---

    def test_file_hash(self, tmp_path: Path) -> None:
        """Verify that file_hash generates a consistent SHA256 hex digest."""
        file = tmp_path / "test.txt"
        file.write_bytes(b"hello world")

        expected_hash = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        assert file_hash(file) == expected_hash

    # --- Tests for compare_dirs (Lines 18-30) ---

    def test_compare_dirs_full_scenario(self, tmp_path: Path) -> None:
        """Test directory comparison including added, removed, and modified files.
        This covers the logic for set differences and file hash comparisons.
        """
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        # 1. Added file (exists in dir1 but not dir2)
        (dir1 / "added.txt").write_text("new")

        # 2. Removed file (exists in dir2 but not dir1)
        (dir2 / "removed.txt").write_text("gone")

        # 3. Modified file (exists in both, different content)
        (dir1 / "mod.txt").write_text("v1")
        (dir2 / "mod.txt").write_text("v2")

        # 4. Equal file (exists in both, same content)
        (dir1 / "same.txt").write_text("equal")
        (dir2 / "same.txt").write_text("equal")

        result = compare_dirs(dir1, dir2)

        assert Path("added.txt") in result["added"]
        assert Path("removed.txt") in result["removed"]
        assert Path("mod.txt") in result["modified"]
        assert result["equal"] is False

    def test_compare_dirs_identical(self, tmp_path: Path) -> None:
        """Verify that 'equal' is True when directories are identical."""
        dir1 = tmp_path / "a"
        dir2 = tmp_path / "b"
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "file.txt").write_text("content")
        (dir2 / "file.txt").write_text("content")

        result = compare_dirs(dir1, dir2)
        assert result["equal"] is True

    # --- Tests for string conversions ---

    def test_to_camel_case(self) -> None:
        """Test snake_case and UPPER_CASE to camelCase conversion."""
        assert to_camel_case("snake_case_test") == "snakeCaseTest"
        assert to_camel_case("UPPER_CASE_TEST") == "upperCaseTest"
        assert to_camel_case("single") == "single"

    def test_to_snake_case(self) -> None:
        """Test various formats to snake_case conversion."""
        assert to_snake_case("CamelCase") == "camel_case"
        assert to_snake_case("my-header-test") == "my_header_test"
        assert to_snake_case("already_snake") == "already_snake"

    # --- Tests for get_variants (Line 78) ---

    def test_get_variants_success(self) -> None:
        """Verify the generation of AliasChoices string with unique sorted variants."""
        # Input 'user_id' should produce "user_id", "userId", "USER_ID"
        result = get_variants("user_id")

        # Check that it returns the formatted string with sorted aliases
        assert "AliasChoices" in result
        assert '"userId"' in result
        assert '"user_id"' in result
        assert '"USER_ID"' in result

    def test_get_variants_empty_input(self) -> None:
        """Ensure get_variants handles empty strings or whitespace (Line 78)."""
        # This covers the 'if not words: return ""' branch
        assert get_variants("") == ""
        assert get_variants("   ") == ""

    def test_get_variants_complex_input(self) -> None:
        """Test get_variants with mixed formatting."""
        result = get_variants("Complex-Input_test")
        # Should normalize to snake: complex_input_test, camel: complexInputTest, etc.
        assert "complex_input_test" in result
        assert "complexInputTest" in result
