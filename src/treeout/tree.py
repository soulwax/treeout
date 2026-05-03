"""Core tree generation functionality."""

import re
import stat
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Pattern, Set, Tuple

from .types import NodeConfig, TreeStats
from .utils import process_directory_path

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
    r"^\.treeignore$",
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

ARCHIVE_SUFFIXES = {".zip", ".tar", ".tgz", ".tar.gz"}


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
            for line in pattern_file:
                stripped_line = line.strip()
                if stripped_line and not stripped_line.startswith("#"):
                    patterns.add(stripped_line)
    except OSError as operating_system_error:
        print(
            "Warning: Could not read pattern file {}: {}".format(file_path, operating_system_error)
        )
    return patterns


def is_archive_file(path: Path) -> bool:
    """Return whether a path is a supported archive file."""
    name = path.name.lower()
    return any(name.endswith(suffix) for suffix in ARCHIVE_SUFFIXES)


def get_archive_entries(path: Path, max_entries: int = 50) -> List[str]:
    """Read a limited list of entries from a supported archive."""
    try:
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as archive:
                entries = sorted(archive.namelist())
        elif is_archive_file(path):
            with tarfile.open(path) as archive:
                entries = sorted(archive.getnames())
        else:
            return []
    except (OSError, tarfile.TarError, zipfile.BadZipFile):
        return ["[archive unreadable]"]

    limited_entries = entries[:max_entries]
    remaining = len(entries) - len(limited_entries)
    if remaining > 0:
        limited_entries.append(f"... ({remaining} more)")

    return limited_entries


def get_color_for_file(
    path: Path, use_color: bool, file_colors: Optional[Dict[str, str]] = None
) -> Tuple[str, str]:
    """Get the color code for a file and its reset code."""
    if not use_color:
        return "", ""

    if path.is_dir():
        return COLORS["blue"], COLORS["reset"]
    if path.is_symlink():
        return COLORS["yellow"], COLORS["reset"]

    color_map = FILE_COLORS if file_colors is None else file_colors
    color = color_map.get(path.suffix.lower(), "")
    return COLORS.get(color, ""), COLORS["reset"]


def get_file_info(
    path: Path,
    show_size: bool,
    show_date: bool,
    show_permissions: bool,
    git_status: Optional[str] = None,
) -> str:
    """Get additional file information based on flags."""
    info_parts = []
    if git_status:
        info_parts.append(f"[git:{git_status}]")
    if show_size and path.is_file():
        info_parts.append(f"[{get_size_str(path.stat().st_size)}]")
    if show_date:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        info_parts.append(mtime.strftime("[%Y-%m-%d %H:%M]"))
    if show_permissions:
        info_parts.append(f"[{stat.filemode(path.stat().st_mode)}]")
    return " ".join(info_parts)


def get_node_display_name(item: Path, config: NodeConfig) -> str:
    """Get a display name for a tree node."""
    color_start, color_end = get_color_for_file(item, config.use_color, config.file_colors)
    display_name = f"{item.name}/" if item.is_dir() else item.name
    return f"{color_start}{display_name}{color_end}"


def get_node_label(item: Path, config: NodeConfig, git_status: Optional[str] = None) -> str:
    """Get the complete display label for a tree node."""
    info = get_file_info(
        item,
        show_size=config.show_size,
        show_date=config.show_date,
        show_permissions=config.show_permissions,
        git_status=git_status,
    )
    info = f" {info}" if info else ""
    return f"{get_node_display_name(item, config)}{info}"


def process_tree_node(
    item: Path,
    prefix: str,
    config: NodeConfig,
    is_last_item: bool = False,
    git_status: Optional[str] = None,
) -> str:
    """Process a single tree node (file or directory)."""
    connector = "└───" if is_last_item else "├───"
    return f"{prefix}{connector}{get_node_label(item, config, git_status)}"


def process_archive_entries(
    item: Path,
    prefix: str,
    *,
    max_entries: int,
) -> List[str]:
    """Render archive entries as nested pseudo-tree nodes."""
    entries = get_archive_entries(item, max_entries)
    lines = []
    for index, entry in enumerate(entries):
        connector = "└───" if index == len(entries) - 1 else "├───"
        lines.append(f"{prefix}{connector}{entry}")
    return lines


def generate_tree(
    directory: Path,
    *,  # Ensure all additional params are keyword-only
    prefix: str = "",
    max_depth: Optional[int] = None,
    current_depth: int = 0,
    stats: Optional[TreeStats] = None,
    exclude_pattern: Optional[Pattern] = None,
    include_extensions: Optional[Set[str]] = None,
    include_globs: Optional[Set[str]] = None,
    git_statuses: Optional[Dict[Path, str]] = None,
    file_colors: Optional[Dict[str, str]] = None,
    inspect_archives: bool = False,
    archive_max_entries: int = 50,
    progress_callback: Optional[Callable[[Path], None]] = None,
    show_size: bool = False,
    show_date: bool = False,
    show_permissions: bool = False,
    use_color: bool = False,
) -> List[str]:
    """Generate a Windows-style ASCII tree structure for the given directory."""
    if stats is None:
        stats = TreeStats()
    if progress_callback:
        progress_callback(directory)

    lines = []
    files, dirs = process_directory_path(
        directory,
        stats,
        exclude_pattern,
        include_extensions,
        include_globs,
    )

    # Process files
    for index, item in enumerate(files):
        is_last_item = (index == len(files) - 1) and not dirs
        node_config = NodeConfig(
            show_size=show_size,
            show_date=show_date,
            show_permissions=show_permissions,
            use_color=use_color,
            file_colors=file_colors,
        )
        lines.append(
            process_tree_node(
                item=item,
                prefix=prefix,
                config=node_config,
                is_last_item=is_last_item,
                git_status=git_statuses.get(item.resolve()) if git_statuses else None,
            )
        )
        if inspect_archives and is_archive_file(item):
            archive_prefix = prefix + ("    " if is_last_item else "│   ")
            lines.extend(
                process_archive_entries(
                    item,
                    archive_prefix,
                    max_entries=archive_max_entries,
                )
            )

    # Process directories
    if max_depth is not None and current_depth >= max_depth:
        return lines

    for index, item in enumerate(dirs):
        is_last_item = index == len(dirs) - 1
        node_config = NodeConfig(
            show_size=show_size,
            show_date=show_date,
            show_permissions=show_permissions,
            use_color=use_color,
            file_colors=file_colors,
        )
        lines.append(
            process_tree_node(
                item=item,
                prefix=prefix,
                config=node_config,
                is_last_item=is_last_item,
                git_status=git_statuses.get(item.resolve()) if git_statuses else None,
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
                include_extensions=include_extensions,
                include_globs=include_globs,
                git_statuses=git_statuses,
                file_colors=file_colors,
                inspect_archives=inspect_archives,
                archive_max_entries=archive_max_entries,
                progress_callback=progress_callback,
                show_size=show_size,
                show_date=show_date,
                show_permissions=show_permissions,
                use_color=use_color,
            )
        )

    return lines


def generate_horizontal_tree(
    directory: Path,
    *,
    path_parts: Optional[List[str]] = None,
    max_depth: Optional[int] = None,
    current_depth: int = 0,
    stats: Optional[TreeStats] = None,
    exclude_pattern: Optional[Pattern] = None,
    include_extensions: Optional[Set[str]] = None,
    include_globs: Optional[Set[str]] = None,
    git_statuses: Optional[Dict[Path, str]] = None,
    file_colors: Optional[Dict[str, str]] = None,
    inspect_archives: bool = False,
    archive_max_entries: int = 50,
    progress_callback: Optional[Callable[[Path], None]] = None,
    show_size: bool = False,
    show_date: bool = False,
    show_permissions: bool = False,
    use_color: bool = False,
) -> List[str]:
    """Generate a flattened horizontal tree with paths joined by arrows."""
    if stats is None:
        stats = TreeStats()
    if path_parts is None:
        path_parts = []
    if progress_callback:
        progress_callback(directory)

    node_config = NodeConfig(
        show_size=show_size,
        show_date=show_date,
        show_permissions=show_permissions,
        use_color=use_color,
        file_colors=file_colors,
    )
    lines = []
    files, dirs = process_directory_path(
        directory,
        stats,
        exclude_pattern,
        include_extensions,
        include_globs,
    )

    for item in files:
        item_status = git_statuses.get(item.resolve()) if git_statuses else None
        item_label = get_node_label(item, node_config, item_status)
        lines.append(" > ".join(path_parts + [item_label]))
        if inspect_archives and is_archive_file(item):
            for entry in get_archive_entries(item, archive_max_entries):
                lines.append(
                    " > ".join(path_parts + [get_node_display_name(item, node_config), entry])
                )

    if max_depth is not None and current_depth >= max_depth:
        return lines

    for item in dirs:
        directory_status = git_statuses.get(item.resolve()) if git_statuses else None
        directory_label = get_node_label(item, node_config, directory_status)
        lines.append(" > ".join(path_parts + [directory_label]))
        lines.extend(
            generate_horizontal_tree(
                item,
                path_parts=path_parts + [get_node_display_name(item, node_config)],
                max_depth=max_depth,
                current_depth=current_depth + 1,
                stats=stats,
                exclude_pattern=exclude_pattern,
                include_extensions=include_extensions,
                include_globs=include_globs,
                git_statuses=git_statuses,
                file_colors=file_colors,
                inspect_archives=inspect_archives,
                archive_max_entries=archive_max_entries,
                progress_callback=progress_callback,
                show_size=show_size,
                show_date=show_date,
                show_permissions=show_permissions,
                use_color=use_color,
            )
        )

    return lines
