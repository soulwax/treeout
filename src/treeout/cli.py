"""Command line interface for treeout."""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from html import escape as escape_html
from pathlib import Path
from re import Pattern
from typing import Dict, List, Optional, Set
from xml.sax.saxutils import escape as escape_xml

from .tree import (
    DEFAULT_IGNORE_PATTERNS,
    compile_ignore_pattern,
    generate_horizontal_tree,
    generate_tree,
    get_size_str,
    parse_pattern_file,
)
from .types import NodeConfig, TreeStats
from .utils import process_directory_path


@dataclass
# pylint: disable=too-many-instance-attributes
class TreeConfig:
    """Tree generation configuration."""

    target_dir: Path
    output_file: Path
    exclude_pattern: Optional[Pattern]
    node_config: NodeConfig
    include_extensions: Optional[Set[str]] = None
    include_globs: Optional[Set[str]] = None
    git_statuses: Optional[Dict[Path, str]] = None
    output_format: str = "text"
    layout: str = "vertical"
    compare_snapshot: Optional[Path] = None
    save_snapshot: Optional[Path] = None
    max_depth: Optional[int] = None
    show_stats: bool = False


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(description="Generate a directory tree structure")
    parser.add_argument(
        "path", nargs="?", default=".", help="Directory path to map (default: current directory)"
    )
    parser.add_argument("-d", "--max-depth", type=int, help="Maximum depth to traverse")
    parser.add_argument("-s", "--size", action="store_true", help="Show file sizes")
    parser.add_argument("-t", "--time", action="store_true", help="Show modification times")
    parser.add_argument(
        "-p", "--permissions", action="store_true", help="Show Unix-style file permissions"
    )
    parser.add_argument("-c", "--color", action="store_true", help="Colorize output")
    parser.add_argument(
        "--color-config",
        type=str,
        help="JSON file with a file_colors object mapping extensions to color names",
    )
    parser.add_argument(
        "--git-status",
        action="store_true",
        help="Show Git status markers for tracked and untracked paths",
    )
    parser.add_argument(
        "--layout",
        choices=("vertical", "horizontal"),
        default="vertical",
        help="Tree layout style (default: vertical)",
    )
    parser.add_argument(
        "--compare-snapshot",
        type=str,
        help="Compare file sizes against a previous snapshot JSON file",
    )
    parser.add_argument(
        "--save-snapshot",
        type=str,
        help="Write a file-size snapshot JSON file for a future comparison",
    )
    parser.add_argument(
        "-e",
        "--extension",
        action="append",
        dest="extensions",
        help="Only show files with this extension; repeat or comma-separate values",
    )
    parser.add_argument(
        "-g",
        "--glob",
        action="append",
        dest="glob_patterns",
        help="Only show files matching this glob; repeat or comma-separate values",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("text", "json", "xml", "yaml", "markdown", "html"),
        default="text",
        dest="output_format",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output file path (default: tree.<format extension> in target directory)",
    )
    parser.add_argument("--stats", action="store_true", help="Show summary statistics")
    parser.add_argument("--no-color", action="store_true", help="Disable color even if supported")

    ignore_group = parser.add_mutually_exclusive_group()
    ignore_group.add_argument(
        "-i", "--ignore-pattern", type=str, help="Additional regex pattern to ignore"
    )
    ignore_group.add_argument(
        "-I", "--ignore-patterns", type=str, help="File containing patterns to ignore"
    )
    ignore_group.add_argument(
        "--no-ignore", action="store_true", help="Disable default ignore patterns"
    )
    ignore_group.add_argument(
        "--show-all", action="store_true", help="Show all files (same as --no-ignore)"
    )
    return parser


def normalize_extensions(values: Optional[List[str]]) -> Optional[Set[str]]:
    """Normalize extension filters from CLI arguments."""
    if not values:
        return None

    extensions = set()
    for value in values:
        for extension in value.split(","):
            normalized = extension.strip().lower()
            if not normalized:
                continue
            extensions.add(normalized if normalized.startswith(".") else f".{normalized}")

    return extensions or None


def normalize_globs(values: Optional[List[str]]) -> Optional[Set[str]]:
    """Normalize glob filters from CLI arguments."""
    if not values:
        return None

    globs = set()
    for value in values:
        for glob in value.split(","):
            normalized = glob.strip().lower()
            if normalized:
                globs.add(normalized)

    return globs or None


def normalize_color_map(color_map: Dict[str, str]) -> Dict[str, str]:
    """Normalize extension-to-color mappings from a config file."""
    normalized = {}
    for extension, color in color_map.items():
        extension_key = extension.strip().lower()
        color_name = color.strip().lower()
        if extension_key and color_name:
            normalized[extension_key if extension_key.startswith(".") else f".{extension_key}"] = (
                color_name
            )
    return normalized


def load_color_config(file_path: Optional[str]) -> Optional[Dict[str, str]]:
    """Load custom file color mappings from a JSON config file."""
    if not file_path:
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError) as config_error:
        print(f"Warning: Could not read color config {file_path}: {config_error}", file=sys.stderr)
        return None

    file_colors = config.get("file_colors")
    if not isinstance(file_colors, dict):
        print(
            f"Warning: Color config {file_path} does not contain a file_colors object",
            file=sys.stderr,
        )
        return None

    return normalize_color_map(file_colors)


def parse_git_status_line(line: str) -> Optional[tuple]:
    """Parse one porcelain status line into a path and status label."""
    if len(line) < 4:
        return None

    status = line[:2].strip()
    path_text = line[3:].strip()
    if " -> " in path_text:
        path_text = path_text.split(" -> ", 1)[1]
    if path_text.startswith('"') and path_text.endswith('"'):
        path_text = path_text[1:-1]

    return path_text, status or "?"


def collect_git_statuses(target_dir: Path) -> Dict[Path, str]:
    """Collect Git status markers keyed by absolute path."""
    try:
        result = subprocess.run(
            ["git", "-C", str(target_dir), "status", "--porcelain=v1", "--untracked-files=normal"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return {}

    if result.returncode != 0:
        return {}

    statuses = {}
    for line in result.stdout.splitlines():
        parsed = parse_git_status_line(line)
        if parsed is None:
            continue
        path_text, status = parsed
        statuses[(target_dir / path_text).resolve()] = status

    return statuses


def collect_size_snapshot(
    directory: Path,
    *,
    root: Path,
    exclude_pattern: Optional[Pattern],
    include_extensions: Optional[Set[str]],
    include_globs: Optional[Set[str]],
    max_depth: Optional[int],
    current_depth: int = 0,
) -> Dict[str, int]:
    """Collect file sizes keyed by relative POSIX paths."""
    stats = TreeStats()
    files, dirs = process_directory_path(
        directory=directory,
        stats=stats,
        exclude_pattern=exclude_pattern,
        include_extensions=include_extensions,
        include_globs=include_globs,
    )
    snapshot = {
        file_path.relative_to(root).as_posix(): file_path.stat().st_size for file_path in files
    }

    if max_depth is not None and current_depth >= max_depth:
        return snapshot

    for dir_path in dirs:
        snapshot.update(
            collect_size_snapshot(
                dir_path,
                root=root,
                exclude_pattern=exclude_pattern,
                include_extensions=include_extensions,
                include_globs=include_globs,
                max_depth=max_depth,
                current_depth=current_depth + 1,
            )
        )

    return snapshot


def load_size_snapshot(file_path: Path) -> Dict[str, int]:
    """Load a size snapshot from JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as snapshot_file:
            payload = json.load(snapshot_file)
    except (OSError, json.JSONDecodeError) as snapshot_error:
        print(f"Warning: Could not read snapshot {file_path}: {snapshot_error}", file=sys.stderr)
        return {}

    files = payload.get("files", payload)
    if not isinstance(files, dict):
        return {}

    return {str(path): int(size) for path, size in files.items() if isinstance(size, int)}


def save_size_snapshot(file_path: Path, target_dir: Path, files: Dict[str, int]) -> None:
    """Save a size snapshot to JSON."""
    payload = {"root": str(target_dir), "files": files}
    with open(file_path, "w", encoding="utf-8", newline="\n") as snapshot_file:
        json.dump(payload, snapshot_file, indent=2, sort_keys=True)


def compare_size_snapshots(previous: Dict[str, int], current: Dict[str, int]) -> List[str]:
    """Build human-readable size comparison lines."""
    lines = ["\nSize comparison:"]
    paths = sorted(set(previous) | set(current))
    changed = False

    for path in paths:
        if path not in previous:
            lines.append(f"Added: {path} [{get_size_str(current[path])}]")
            changed = True
        elif path not in current:
            lines.append(f"Removed: {path} [{get_size_str(previous[path])}]")
            changed = True
        elif previous[path] != current[path]:
            delta = current[path] - previous[path]
            sign = "+" if delta >= 0 else "-"
            lines.append(
                "Changed: {} [{} -> {}, {}{}]".format(
                    path,
                    get_size_str(previous[path]),
                    get_size_str(current[path]),
                    sign,
                    get_size_str(abs(delta)),
                )
            )
            changed = True

    if not changed:
        lines.append("No size changes.")

    return lines


def get_default_output_file(target_dir: Path, output_format: str) -> Path:
    """Get the default output file for the selected format."""
    extensions = {
        "text": "txt",
        "json": "json",
        "xml": "xml",
        "yaml": "yaml",
        "markdown": "md",
        "html": "html",
    }
    return target_dir / f"tree.{extensions[output_format]}"


def get_ignore_patterns(args: argparse.Namespace, target_dir: Path) -> Set[str]:
    """Determine which patterns to ignore based on arguments."""
    if args.no_ignore or args.show_all:
        return set()

    patterns = set(DEFAULT_IGNORE_PATTERNS)
    if args.ignore_pattern:
        patterns.add(args.ignore_pattern)
    elif args.ignore_patterns:
        patterns.update(parse_pattern_file(args.ignore_patterns))

    treeignore_path = target_dir / ".treeignore"
    if treeignore_path.is_file():
        patterns.update(parse_pattern_file(str(treeignore_path)))

    return patterns


def create_tree_config(args: argparse.Namespace) -> TreeConfig:
    """Create tree configuration from arguments."""
    target_dir = Path(args.path).resolve()
    if not target_dir.exists():
        print("Error: Directory '{}' does not exist".format(args.path), file=sys.stderr)
        sys.exit(1)
    if not target_dir.is_dir():
        print(f"Error: '{args.path}' is not a directory", file=sys.stderr)
        sys.exit(1)

    patterns = get_ignore_patterns(args, target_dir)
    use_color = (
        args.output_format == "text" and args.color and not args.no_color and sys.stdout.isatty()
    )
    output_file = (
        args.output if args.output else get_default_output_file(target_dir, args.output_format)
    )

    return TreeConfig(
        target_dir=target_dir,
        output_file=Path(output_file),
        exclude_pattern=compile_ignore_pattern(patterns),
        node_config=NodeConfig(
            show_size=args.size,
            show_date=args.time,
            show_permissions=args.permissions,
            use_color=use_color,
            file_colors=load_color_config(args.color_config),
        ),
        include_extensions=normalize_extensions(args.extensions),
        include_globs=normalize_globs(args.glob_patterns),
        git_statuses=collect_git_statuses(target_dir) if args.git_status else None,
        output_format=args.output_format,
        layout=args.layout,
        compare_snapshot=Path(args.compare_snapshot) if args.compare_snapshot else None,
        save_snapshot=Path(args.save_snapshot) if args.save_snapshot else None,
        max_depth=args.max_depth,
        show_stats=args.stats,
    )


def generate_output(config: TreeConfig) -> List[str]:
    """Generate tree output based on configuration."""
    stats = TreeStats()

    # Start with the root directory name
    lines = [config.target_dir.name]

    # Process the root directory contents
    tree_lines = process_root_directory(config, stats)
    lines.extend(tree_lines)

    if config.show_stats:
        lines.extend(
            [
                "\nSummary:",
                f"Directories: {stats.directories}",
                f"Files: {stats.files}",
                *(f"Total size: {stats.total_size}" if config.node_config.show_size else []),
            ]
        )

    if config.compare_snapshot:
        current_snapshot = build_size_snapshot(config)
        lines.extend(
            compare_size_snapshots(load_size_snapshot(config.compare_snapshot), current_snapshot)
        )

    return lines


def process_root_directory(config: TreeConfig, stats: TreeStats) -> List[str]:
    """Process the root directory and generate initial output."""
    generator = generate_horizontal_tree if config.layout == "horizontal" else generate_tree
    return generator(
        directory=config.target_dir,
        max_depth=config.max_depth,
        stats=stats,
        exclude_pattern=config.exclude_pattern,
        include_extensions=config.include_extensions,
        include_globs=config.include_globs,
        git_statuses=config.git_statuses,
        file_colors=config.node_config.file_colors,
        show_size=config.node_config.show_size,
        show_date=config.node_config.show_date,
        show_permissions=config.node_config.show_permissions,
        use_color=config.node_config.use_color,
    )


def build_size_snapshot(config: TreeConfig) -> Dict[str, int]:
    """Build a size snapshot using the current filtering configuration."""
    return collect_size_snapshot(
        config.target_dir,
        root=config.target_dir,
        exclude_pattern=config.exclude_pattern,
        include_extensions=config.include_extensions,
        include_globs=config.include_globs,
        max_depth=config.max_depth,
    )


def serialize_output(lines: List[str], output_format: str) -> str:
    """Serialize tree lines into the requested output format."""
    if output_format == "text":
        return "\n".join(lines)
    if output_format == "json":
        return json.dumps({"root": lines[0] if lines else "", "lines": lines}, indent=2)
    if output_format == "xml":
        xml_lines = ['<?xml version="1.0" encoding="utf-8"?>', "<treeout>"]
        xml_lines.extend(f"  <line>{escape_xml(line)}</line>" for line in lines)
        xml_lines.append("</treeout>")
        return "\n".join(xml_lines)
    if output_format == "yaml":
        yaml_lines = [f"root: {json.dumps(lines[0] if lines else '')}", "lines:"]
        yaml_lines.extend(f"  - {json.dumps(line)}" for line in lines)
        return "\n".join(yaml_lines)
    if output_format == "markdown":
        return "\n".join(["```text", *lines, "```"])
    if output_format == "html":
        escaped_lines = escape_html("\n".join(lines))
        return "\n".join(
            [
                "<!doctype html>",
                '<html lang="en">',
                "<head>",
                '  <meta charset="utf-8">',
                "  <title>treeout</title>",
                "</head>",
                "<body>",
                f"<pre>{escaped_lines}</pre>",
                "</body>",
                "</html>",
            ]
        )
    raise ValueError(f"Unsupported output format: {output_format}")


def main() -> None:
    """Main entry point for the CLI."""
    config = create_tree_config(create_parser().parse_args())
    lines = generate_output(config)
    output = serialize_output(lines, config.output_format)

    with open(config.output_file, "w", encoding="utf-8", newline="\r\n") as output_file:
        output_file.write(output)

    if config.save_snapshot:
        save_size_snapshot(config.save_snapshot, config.target_dir, build_size_snapshot(config))

    print(output)
    print(f"\nTree structure has been written to {config.output_file}")
    if config.save_snapshot:
        print(f"Size snapshot has been written to {config.save_snapshot}")
