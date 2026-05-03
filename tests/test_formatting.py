"""Tests for tree formatting features like directory slashes and root display."""

import re
from pathlib import Path

import pytest

from treeout.cli import (
    compare_size_snapshots,
    create_tree_config,
    generate_output,
    get_default_output_file,
    load_color_config,
    load_size_snapshot,
    normalize_extensions,
    normalize_globs,
    parse_git_status_line,
    save_size_snapshot,
    serialize_output,
)
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
        self.permissions = False
        self.color = False
        self.color_config = None
        self.git_status = False
        self.layout = "vertical"
        self.compare_snapshot = None
        self.save_snapshot = None
        self.inspect_archives = False
        self.archive_max_entries = 50
        self.progress = False
        self.extensions = None
        self.glob_patterns = None
        self.output_format = "text"
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


def test_normalize_extensions():
    """Test extension filter normalization from CLI values."""
    assert normalize_extensions(["py,.MD", "txt"]) == {".py", ".md", ".txt"}
    assert normalize_extensions(None) is None


def test_normalize_globs():
    """Test glob filter normalization from CLI values."""
    assert normalize_globs(["*.PY,README.*", "test_*"]) == {"*.py", "readme.*", "test_*"}
    assert normalize_globs(None) is None


def test_load_color_config(tmp_path):
    """Test loading custom extension color mappings."""
    config_file = tmp_path / "treeout-colors.json"
    config_file.write_text('{"file_colors": {"md": "cyan", ".py": "red"}}')

    assert load_color_config(str(config_file)) == {".md": "cyan", ".py": "red"}


def test_parse_git_status_line():
    """Test parsing Git porcelain status lines."""
    assert parse_git_status_line(" M README.md") == ("README.md", "M")
    assert parse_git_status_line("?? new file.txt") == ("new file.txt", "??")
    assert parse_git_status_line("R  old.py -> new.py") == ("new.py", "R")
    assert parse_git_status_line("") is None


def test_default_output_file_uses_format_extension(tmp_path):
    """Test default output filenames for non-text formats."""
    assert get_default_output_file(tmp_path, "text") == tmp_path / "tree.txt"
    assert get_default_output_file(tmp_path, "json") == tmp_path / "tree.json"
    assert get_default_output_file(tmp_path, "markdown") == tmp_path / "tree.md"


def test_serialize_output_formats():
    """Test supported output serializers."""
    lines = ["root", "├───file.txt"]

    assert serialize_output(lines, "text") == "root\n├───file.txt"
    assert '"root": "root"' in serialize_output(lines, "json")
    assert "<line>root</line>" in serialize_output(lines, "xml")
    assert 'root: "root"' in serialize_output(lines, "yaml")
    assert serialize_output(lines, "markdown").startswith("```text\nroot")
    assert "<pre>root" in serialize_output(lines, "html")


# pylint: disable=redefined-outer-name
def test_horizontal_layout_output(test_directory_structure):
    """Test flattened horizontal tree output."""
    args = MockArgs(path=str(test_directory_structure))
    args.layout = "horizontal"
    config = create_tree_config(args)

    output_lines = generate_output(config)

    assert any("dir2/ > nested_dir/ > deep_file.md" in line for line in output_lines)
    assert not any("│" in line for line in output_lines)


def test_size_snapshot_save_load_and_compare(tmp_path):
    """Test snapshot persistence and size comparison output."""
    snapshot_file = tmp_path / "snapshot.json"
    save_size_snapshot(snapshot_file, tmp_path, {"file.txt": 4})

    assert load_size_snapshot(snapshot_file) == {"file.txt": 4}

    comparison = compare_size_snapshots(
        {"file.txt": 4, "removed.txt": 2},
        {"file.txt": 7, "added.txt": 1},
    )

    assert "Added: added.txt [1.0B]" in comparison
    assert "Removed: removed.txt [2.0B]" in comparison
    assert "Changed: file.txt [4.0B -> 7.0B, +3.0B]" in comparison


# pylint: disable=redefined-outer-name
def test_treeignore_file_is_applied(test_directory_structure):
    """Test that .treeignore patterns are read from the target directory."""
    (test_directory_structure / ".treeignore").write_text("^file1\\.txt$\n# comment\n^dir1$")

    args = MockArgs(path=str(test_directory_structure))
    config = create_tree_config(args)
    output_lines = generate_output(config)

    assert not any("file1.txt" in line for line in output_lines)
    assert not any("dir1/" in line for line in output_lines)
    assert any("file2.py" in line for line in output_lines)
