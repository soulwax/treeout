"""Command line interface for treeout."""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import List, Optional, Set

from .tree import (
    DEFAULT_IGNORE_PATTERNS,
    compile_ignore_pattern,
    generate_tree,
    parse_pattern_file,
)
from .types import NodeConfig, TreeStats


@dataclass
class TreeConfig:
    """Tree generation configuration."""

    target_dir: Path
    output_file: Path
    exclude_pattern: Optional[Pattern]
    node_config: NodeConfig
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
    parser.add_argument("-c", "--color", action="store_true", help="Colorize output")
    parser.add_argument(
        "-o", "--output", type=str, help="Output file path (default: tree.txt in target directory)"
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


def get_ignore_patterns(args: argparse.Namespace) -> Set[str]:
    """Determine which patterns to ignore based on arguments."""
    if args.no_ignore or args.show_all:
        return set()

    patterns = set(DEFAULT_IGNORE_PATTERNS)
    if args.ignore_pattern:
        patterns.add(args.ignore_pattern)
    elif args.ignore_patterns:
        patterns.update(parse_pattern_file(args.ignore_patterns))

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

    patterns = get_ignore_patterns(args)
    use_color = args.color and not args.no_color and sys.stdout.isatty()
    output_file = args.output if args.output else target_dir / "tree.txt"

    return TreeConfig(
        target_dir=target_dir,
        output_file=Path(output_file),
        exclude_pattern=compile_ignore_pattern(patterns),
        node_config=NodeConfig(
            show_size=args.size,
            show_date=args.time,
            use_color=use_color,
        ),
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

    return lines


def process_root_directory(config: TreeConfig, stats: TreeStats) -> List[str]:
    """Process the root directory and generate initial output."""
    return generate_tree(
        directory=config.target_dir,
        max_depth=config.max_depth,
        stats=stats,
        exclude_pattern=config.exclude_pattern,
        show_size=config.node_config.show_size,
        show_date=config.node_config.show_date,
        use_color=config.node_config.use_color,
    )


def main() -> None:
    """Main entry point for the CLI."""
    config = create_tree_config(create_parser().parse_args())
    lines = generate_output(config)

    with open(config.output_file, "w", encoding="utf-8", newline="\r\n") as output_file:
        output_file.write("\n".join(lines))

    print("\n".join(lines))
    print(f"\nTree structure has been written to {config.output_file}")
