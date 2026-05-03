"""Type definitions and shared classes for treeout."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class TreeStats:
    """Statistics collector for tree generation."""

    directories: int = 0
    files: int = 0
    total_size: int = 0

    def update_from_items(self, files: List[Path], show_size: bool = False) -> None:
        """Update statistics from a list of files."""
        self.files += len(files)
        if show_size:
            self.total_size += sum(f.stat().st_size for f in files)


@dataclass
class NodeConfig:
    """Configuration for tree node processing."""

    show_size: bool = False
    show_date: bool = False
    show_permissions: bool = False
    use_color: bool = False
    file_colors: Optional[Dict[str, str]] = None
