"""Tests for the treeout package."""

from pathlib import Path

import pytest

from treeout.tree import (
    DEFAULT_IGNORE_PATTERNS,
    compile_ignore_pattern,
    generate_tree,
)
from treeout.types import TreeStats


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
