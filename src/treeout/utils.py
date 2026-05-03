"""Utility functions for directory tree processing."""

from pathlib import Path
from typing import List, Tuple, Optional, Pattern

from .types import TreeStats


def process_directory_items(
    items: List[Path],
    stats: TreeStats,
    exclude_pattern: Optional[Pattern] = None,
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

    stats.directories += len(dirs)
    stats.files += len(files)

    return files, dirs
