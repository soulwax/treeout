"""Core tree generation functionality."""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Pattern, Set, Tuple

from .types import NodeConfig, TreeStats
from .utils import process_directory_items

DEFAULT_IGNORE_PATTERNS = {
    r"^\.git$",
    r"^\.pytest_cache$",
    r"^\.mypy_cache$",
    r"^__pycache__$",
    r"^node_modules$",
    r"^\.vscode$",
    r"^\.idea$",
    r"^\.vs$",
    r"^\.venv$",
    r"^venv$",
    r"^env$",
    r"^\.env$",
    r"^\.tox$",
    r"^\.coverage$",
    r"^\.sass-cache$",
    r"^\.next$",
    r"^dist$",
    r"^build$",
    r"^\..+_cache$",
}

COLORS = {
    "reset": "\033[0m",
    "blue": "\033[94m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "cyan": "\033[96m",
    "magenta": "\033[95m",
    "red": "\033[91m",
}

FILE_COLORS = {
    **dict.fromkeys([".exe", ".sh", ".bat", ".cmd", ".ps1", ".py"], "green"),
    **dict.fromkeys(
        [
            ".mp3",
            ".wav",
            ".flac",
            ".m4a",
            ".ogg",
            ".mp4",
            ".avi",
            ".mkv",
            ".mov",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
        ],
        "cyan",
    ),
    **dict.fromkeys([".zip", ".rar", ".7z", ".tar", ".gz"], "magenta"),
    **dict.fromkeys([".json", ".xml", ".yaml", ".yml", ".ini", ".conf"], "red"),
}


def get_size_str(size: int) -> str:
    """Convert size in bytes to human readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}PB"


def compile_ignore_pattern(patterns: Set[str]) -> Optional[Pattern]:
    """Compile multiple patterns into a single regex pattern."""
    if not patterns:
        return None
    combined_pattern = "|".join(f"(?:{pattern})" for pattern in patterns)
    return re.compile(combined_pattern)


def parse_pattern_file(file_path: str) -> Set[str]:
    """Parse a file containing ignore patterns."""
    patterns = set()
    try:
        with open(file_path, "r", encoding="utf-8") as pattern_file:
            patterns.update(
                line.strip() for line in pattern_file if line.strip() and not line.startswith("#")
            )
    except OSError as operating_system_error:
        print(
            "Warning: Could not read pattern file {}: {}".format(file_path, operating_system_error)
        )
    return patterns


def get_color_for_file(path: Path, use_color: bool) -> Tuple[str, str]:
    """Get the color code for a file and its reset code."""
    if not use_color:
        return "", ""

    if path.is_dir():
        return COLORS["blue"], COLORS["reset"]
    if path.is_symlink():
        return COLORS["yellow"], COLORS["reset"]

    color = FILE_COLORS.get(path.suffix.lower(), "")
    return COLORS.get(color, ""), COLORS["reset"]


def get_file_info(path: Path, show_size: bool, show_date: bool) -> str:
    """Get additional file information based on flags."""
    info_parts = []
    if show_size and path.is_file():
        info_parts.append(f"[{get_size_str(path.stat().st_size)}]")
    if show_date:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        info_parts.append(mtime.strftime("[%Y-%m-%d %H:%M]"))
    return " ".join(info_parts)


def process_tree_node(
    item: Path, prefix: str, config: NodeConfig, is_last_item: bool = False
) -> str:
    """Process a single tree node (file or directory)."""
    connector = "└───" if is_last_item else "├───"
    color_start, color_end = get_color_for_file(item, config.use_color)
    info = get_file_info(item, config.show_size, config.show_date)

    # Add trailing slash to directories
    display_name = f"{item.name}/" if item.is_dir() else item.name

    info = f" {info}" if info else ""
    return f"{prefix}{connector}{color_start}{display_name}{color_end}{info}"


def generate_tree(
    directory: Path,
    *,  # Ensure all additional params are keyword-only
    prefix: str = "",
    max_depth: Optional[int] = None,
    current_depth: int = 0,
    stats: Optional[TreeStats] = None,
    exclude_pattern: Optional[Pattern] = None,
    show_size: bool = False,
    show_date: bool = False,
    use_color: bool = False,
) -> List[str]:
    """Generate a Windows-style ASCII tree structure for the given directory."""
    if stats is None:
        stats = TreeStats()

    lines = []
    items = list(directory.iterdir())
    files, dirs = process_directory_items(items, stats, exclude_pattern)

    # Process files
    for index, item in enumerate(files):
        is_last_item = (index == len(files) - 1) and not dirs
        node_config = NodeConfig(show_size=show_size, show_date=show_date, use_color=use_color)
        lines.append(
            process_tree_node(
                item=item, prefix=prefix, config=node_config, is_last_item=is_last_item
            )
        )

    # Process directories
    if max_depth is not None and current_depth >= max_depth:
        return lines

    for index, item in enumerate(dirs):
        is_last_item = index == len(dirs) - 1
        node_config = NodeConfig(show_size=show_size, show_date=show_date, use_color=use_color)
        lines.append(
            process_tree_node(
                item=item, prefix=prefix, config=node_config, is_last_item=is_last_item
            )
        )

        # Use spaces for recursive traversal
        new_prefix = prefix + ("    " if is_last_item else "│   ")
        lines.extend(
            generate_tree(
                directory=item,
                prefix=new_prefix,
                max_depth=max_depth,
                current_depth=current_depth + 1,
                stats=stats,
                exclude_pattern=exclude_pattern,
                show_size=show_size,
                show_date=show_date,
                use_color=use_color,
            )
        )

    return lines
