"""Tests for the treeout package."""

import zipfile
from pathlib import Path

import pytest

from treeout.tree import (
    DEFAULT_IGNORE_PATTERNS,
    compile_ignore_pattern,
    generate_tree,
    get_archive_entries,
    process_tree_node,
)
from treeout.types import NodeConfig, TreeStats


@pytest.fixture
def test_directory(tmp_path: Path) -> Path:
    """Create a test directory structure."""
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    (dir1 / "file1.txt").write_text("content")
    (dir2 / "file2.py").write_text("print('hello')")

    return tmp_path


# pylint: disable=redefined-outer-name
def test_tree_generation(test_directory: Path) -> None:
    """Test basic tree generation functionality."""
    stats = TreeStats()
    tree_output = generate_tree(
        directory=test_directory,
        stats=stats,
        show_size=True,
        show_date=True,
    )

    assert stats.directories == 2
    assert stats.files == 2

    assert len(tree_output) > 0
    assert any("dir1" in line for line in tree_output)
    assert any("dir2" in line for line in tree_output)
    assert any("file1.txt" in line for line in tree_output)
    assert any("file2.py" in line for line in tree_output)


# pylint: disable=redefined-outer-name
def test_ignore_patterns(test_directory: Path) -> None:
    """Test pattern-based file/directory ignoring."""
    pycache_dir = test_directory / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "module.cpython-39.pyc").write_text("")

    stats = TreeStats()
    pattern = compile_ignore_pattern(DEFAULT_IGNORE_PATTERNS)
    tree_output = generate_tree(
        directory=test_directory,
        stats=stats,
        exclude_pattern=pattern,
    )

    assert not any("__pycache__" in line for line in tree_output)
    assert stats.directories == 2


def test_empty_directory(tmp_path: Path) -> None:
    """Test tree generation with empty directory."""
    stats = TreeStats()
    tree_output = generate_tree(directory=tmp_path, stats=stats)

    assert stats.directories == 0
    assert stats.files == 0
    assert not tree_output


# pylint: disable=redefined-outer-name
def test_max_depth(test_directory: Path) -> None:
    """Test max depth limitation."""
    nested = test_directory / "level1" / "level2" / "level3"
    nested.mkdir(parents=True)
    (nested / "deep_file.txt").write_text("deep")
    (test_directory / "level1" / "shallow_file.txt").write_text("shallow")

    stats = TreeStats()
    tree_output = generate_tree(
        directory=test_directory,
        max_depth=1,
        stats=stats,
    )

    assert any("level1" in line for line in tree_output)
    assert any("shallow_file.txt" in line for line in tree_output)
    assert not any("level2" in line for line in tree_output)
    assert not any("level3" in line for line in tree_output)
    assert not any("deep_file.txt" in line for line in tree_output)
    assert not any("level1" in line for line in tree_output if "shallow_file.txt" in line)


# pylint: disable=redefined-outer-name
def test_extension_filter(test_directory: Path) -> None:
    """Test filtering displayed files by extension."""
    stats = TreeStats()
    tree_output = generate_tree(
        directory=test_directory,
        stats=stats,
        include_extensions={".py"},
    )

    assert stats.files == 1
    assert any("file2.py" in line for line in tree_output)
    assert not any("file1.txt" in line for line in tree_output)


# pylint: disable=redefined-outer-name
def test_glob_filter(test_directory: Path) -> None:
    """Test filtering displayed files by glob pattern."""
    stats = TreeStats()
    tree_output = generate_tree(
        directory=test_directory,
        stats=stats,
        include_globs={"file2.*"},
    )

    assert stats.files == 1
    assert any("file2.py" in line for line in tree_output)
    assert not any("file1.txt" in line for line in tree_output)


def test_permissions_display(tmp_path: Path) -> None:
    """Test Unix-style permission display."""
    test_file = tmp_path / "file.txt"
    test_file.write_text("content")

    result = process_tree_node(test_file, "", NodeConfig(show_permissions=True))

    assert "file.txt" in result
    assert "[-" in result


def test_git_status_display(tmp_path: Path) -> None:
    """Test Git status marker display."""
    test_file = tmp_path / "file.txt"
    test_file.write_text("content")

    result = process_tree_node(test_file, "", NodeConfig(), git_status="M")

    assert "file.txt" in result
    assert "[git:M]" in result


def test_custom_file_color_display(tmp_path: Path) -> None:
    """Test custom extension color mapping."""
    test_file = tmp_path / "README.md"
    test_file.write_text("content")

    result = process_tree_node(
        test_file,
        "",
        NodeConfig(use_color=True, file_colors={".md": "red"}),
    )

    assert "\033[91mREADME.md\033[0m" in result


def test_archive_inspection_zip(tmp_path: Path) -> None:
    """Test rendering entries inside zip archives."""
    archive_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("alpha.txt", "alpha")
        archive.writestr("nested/beta.py", "beta")

    tree_output = generate_tree(
        directory=tmp_path,
        inspect_archives=True,
        archive_max_entries=10,
    )

    assert any("bundle.zip" in line for line in tree_output)
    assert any("alpha.txt" in line for line in tree_output)
    assert any("nested/beta.py" in line for line in tree_output)


def test_archive_entry_limit(tmp_path: Path) -> None:
    """Test archive entry truncation."""
    archive_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("a.txt", "a")
        archive.writestr("b.txt", "b")

    assert get_archive_entries(archive_path, max_entries=1) == ["a.txt", "... (1 more)"]


def test_progress_callback(test_directory: Path) -> None:
    """Test traversal progress callback."""
    visited = []

    generate_tree(
        directory=test_directory,
        progress_callback=lambda directory: visited.append(directory.name),
    )

    assert test_directory.name in visited
    assert "dir1" in visited
    assert "dir2" in visited
