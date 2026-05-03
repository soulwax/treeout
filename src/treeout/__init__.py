"""Enhanced directory tree visualization tool."""

from .tree import (
    DEFAULT_IGNORE_PATTERNS,
    compile_ignore_pattern,
    generate_tree,
    get_color_for_file,
    get_file_info,
    get_size_str,
    parse_pattern_file,
)
from .types import NodeConfig, TreeStats

__version__ = "0.9.0"

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
