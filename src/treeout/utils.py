"""Utility functions for directory tree processing."""

import fnmatch
from pathlib import Path
from typing import List, Optional, Pattern, Set, Tuple

from .types import TreeStats


def process_directory_items(
    items: List[Path],
    stats: TreeStats,
    exclude_pattern: Optional[Pattern] = None,
    include_extensions: Optional[Set[str]] = None,
    include_globs: Optional[Set[str]] = None,
) -> Tuple[List[Path], List[Path]]:
    """Process directory items, sorting them and updating statistics."""
    files = sorted(
        [file_path for file_path in items if file_path.is_file()],
        key=lambda file_name: file_name.name.lower(),
    )
    dirs = sorted(
        [dir_path for dir_path in items if dir_path.is_dir()],
        key=lambda dir_name: dir_name.name.lower(),
    )

    if exclude_pattern:
        files = [f for f in files if not exclude_pattern.match(f.name)]
        dirs = [d for d in dirs if not exclude_pattern.match(d.name)]

    if include_extensions:
        files = [f for f in files if f.suffix.lower() in include_extensions]

    if include_globs:
        files = [
            f
            for f in files
            if any(fnmatch.fnmatchcase(f.name.lower(), glob) for glob in include_globs)
        ]

    stats.directories += len(dirs)
    stats.files += len(files)
    stats.total_size += sum(file_path.stat().st_size for file_path in files)

    return files, dirs


def process_directory_path(
    directory: Path,
    stats: TreeStats,
    exclude_pattern: Optional[Pattern] = None,
    include_extensions: Optional[Set[str]] = None,
    include_globs: Optional[Set[str]] = None,
) -> Tuple[List[Path], List[Path]]:
    """Process a directory path using the same filtering and sorting rules."""
    return process_directory_items(
        list(directory.iterdir()),
        stats,
        exclude_pattern,
        include_extensions,
        include_globs,
    )
