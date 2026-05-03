"""Enhanced directory tree visualization tool."""

from .types import TreeStats, NodeConfig
from .tree import (
    generate_tree,
    get_size_str,
    get_color_for_file,
    get_file_info,
    compile_ignore_pattern,
    parse_pattern_file,
    DEFAULT_IGNORE_PATTERNS,
)

__version__ = "0.2.15"

__all__ = [
    "TreeStats",
    "NodeConfig",
    "generate_tree",
    "get_size_str",
    "get_color_for_file",
    "get_file_info",
    "compile_ignore_pattern",
    "parse_pattern_file",
    "DEFAULT_IGNORE_PATTERNS",
]
