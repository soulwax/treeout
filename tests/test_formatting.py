"""Tests for tree formatting features like directory slashes and root display."""

import re
from pathlib import Path

import pytest

from treeout.cli import create_tree_config, generate_output
from treeout.tree import process_tree_node
from treeout.types import NodeConfig


class MockArgs:
    """Mock class for argparse namespace."""

    # pylint: disable=too-few-public-methods
    # pylint: disable=too-many-instance-attributes
    def __init__(self, path="."):
        self.path = path
        self.max_depth = None
        self.size = False
        self.time = False
        self.color = False
        self.output = None
        self.stats = False
        self.no_color = True
        self.ignore_pattern = None
        self.ignore_patterns = None
        self.no_ignore = False
        self.show_all = False


@pytest.fixture
def test_directory_structure(tmp_path):
    """Create a test directory with nested structure."""
    # Create files
    (tmp_path / "file1.txt").write_text("content")
    (tmp_path / "file2.py").write_text("print('hello')")

    # Create nested directories with files
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    (dir1 / "nested_file.txt").write_text("nested content")

    dir2 = tmp_path / "dir2"
    dir2.mkdir()
    nested_dir = dir2 / "nested_dir"
    nested_dir.mkdir()
    (nested_dir / "deep_file.md").write_text("# Deep file")

    return tmp_path


def test_process_tree_node_directory_slash():
    """Test that directories get trailing slashes."""
    # Test with a directory
    test_dir = Path("/tmp/test_dir")
    config = NodeConfig(use_color=False)

    # Mock is_dir to return True
    orig_is_dir = Path.is_dir
    Path.is_dir = lambda self: True
    try:
        result = process_tree_node(test_dir, "", config)
        assert "test_dir/" in result, "Directory should have trailing slash"
    finally:
        # Restore original method
        Path.is_dir = orig_is_dir

    # Test with a file
    test_file = Path("/tmp/test_file.txt")
    # Mock is_dir to return False
    Path.is_dir = lambda self: False
    try:
        result = process_tree_node(test_file, "", config)
        assert "test_file.txt" in result, "File name should be present"
        assert "test_file.txt/" not in result, "File should not have trailing slash"
    finally:
        # Restore original method
        Path.is_dir = orig_is_dir


# pylint: disable=redefined-outer-name
def test_root_directory_in_output(test_directory_structure):
    """Test that the root directory name appears at the top of the output."""
    args = MockArgs(path=str(test_directory_structure))
    config = create_tree_config(args)

    output_lines = generate_output(config)

    # First line should be the directory name
    assert (
        output_lines[0] == test_directory_structure.name
    ), "Root directory name should be first line"

    # Verify some structure elements
    dir_pattern = re.compile(r"[├└]───.+/$")
    file_pattern = re.compile(r"[├└]───[^/]+$")

    dir_lines = [line for line in output_lines if dir_pattern.search(line)]
    file_lines = [line for line in output_lines if file_pattern.search(line)]

    assert len(dir_lines) > 0, "Should have directory entries with trailing slashes"
    assert len(file_lines) > 0, "Should have file entries without trailing slashes"


# pylint: disable=redefined-outer-name
def test_nested_directory_slashes(test_directory_structure):
    """Test that all directories at all levels have trailing slashes."""
    args = MockArgs(path=str(test_directory_structure))
    config = create_tree_config(args)

    output_lines = generate_output(config)

    # Check that dir1/ and dir2/ have slashes
    dir_entries = [line for line in output_lines if "dir1/" in line or "dir2/" in line]
    assert len(dir_entries) >= 2, "Should find dir1/ and dir2/ with slashes"

    # Check that nested_dir/ has a slash
    nested_entries = [line for line in output_lines if "nested_dir/" in line]
    assert len(nested_entries) >= 1, "Should find nested_dir/ with slash"

    # Check that no files have slashes
    file_entries_with_slash = [
        line
        for line in output_lines
        if any(
            f"{filename}/" in line
            for filename in ["file1.txt", "file2.py", "nested_file.txt", "deep_file.md"]
        )
    ]
    assert len(file_entries_with_slash) == 0, "Files should not have trailing slashes"


# pylint: disable=redefined-outer-name
def test_complete_tree_structure(test_directory_structure):
    """Test the complete tree structure format including root and slashes."""
    args = MockArgs(path=str(test_directory_structure))
    args.show_all = True  # Show all files
    config = create_tree_config(args)

    output_lines = generate_output(config)

    # Build a string representation of the expected structure (partial)
    expected_lines = [
        test_directory_structure.name,
        "├───file1.txt",
        "├───file2.py",
        "├───dir1/",
        "│   └───nested_file.txt",
        "└───dir2/",
        "    └───nested_dir/",
        "        └───deep_file.md",
    ]

    # Check that each expected line is in the output (allowing for different order)
    for expected in expected_lines:
        matching_lines = [line for line in output_lines if line.endswith(expected.split("───")[-1])]
        assert len(matching_lines) > 0, f"Expected to find '{expected}' in the output"
