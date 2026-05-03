# treeout

A Python-based enhanced tree command that displays directory structures with additional features and customization options.

## Prerequisites

- Python 3.8 or higher
- No additional dependencies required

## Overview

`treeout` is a versatile command-line tool for visualizing directory structures. It provides more features than the standard Windows `tree` command and offers rich customization for project analysis, documentation, and file management.

## Features

- 📂 Detailed directory tree visualization
- 🎨 Colorized output with file type-based coloring
- 🧩 Custom color schemes via JSON
- 📏 Optional file size display
- 🕒 Optional timestamp information
- 🔐 Optional Unix-style permissions
- 🧭 Optional Git status markers
- 🚫 Configurable ignore patterns
- 🎯 File extension filtering
- 🔎 Glob-based file matching
- 📄 Text, JSON, XML, YAML, Markdown, and HTML output
- 🧾 Size snapshots for comparing runs
- 📊 Summary statistics
- 🌲 Depth control and vertical or horizontal layouts

## Installation

Install directly from PyPI:

```bash
pip install treeout
```

For local development, you can clone the repository:

```bash
git clone https://github.com/soulwax/treeout.git
```

Then install it from the repository root:

```bash
pip install -e . 
```

This installs the package as editable, creating a global `treeout` command while local changes are reflected immediately.

## Usage

### Basic tree view

```shell
treeout
```

### Show with colors and file sizes

```shell
treeout -c -s
```

### Show everything (including normally ignored directories)

```shell
treeout --show-all
```

### Show with file sizes, timestamps, and statistics

```shell
treeout -c -s -t --stats
```

### Show only Python and Markdown files

```shell
treeout -e py -e md
```

### Show files matching glob patterns

```shell
treeout -g "test_*.py" -g "*.md"
```

### Show Unix-style permissions

```shell
treeout -p
```

### Show Git status markers

```shell
treeout --git-status
```

### Use a custom color config

```shell
treeout -c --color-config treeout-colors.json
```

Example `treeout-colors.json`:

```json
{
  "file_colors": {
    ".py": "green",
    ".md": "cyan",
    ".json": "red"
  }
}
```

### Write JSON, YAML, XML, Markdown, or HTML

```shell
treeout --format json
treeout --format yaml -o project-tree.yaml
treeout --format html -o tree.html
```

### Use a horizontal path layout

```shell
treeout --layout horizontal
```

### Compare file sizes between runs

```shell
treeout --save-snapshot before.json
treeout --compare-snapshot before.json --save-snapshot after.json -s --stats
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `-d`, `--max-depth` | Maximum depth to traverse |
| `-s`, `--size` | Show file sizes |
| `-t`, `--time` | Show modification times |
| `-p`, `--permissions` | Show Unix-style file permissions |
| `-c`, `--color` | Colorize output |
| `--color-config` | JSON file with custom extension color mappings |
| `--git-status` | Show Git status markers for tracked and untracked paths |
| `-e`, `--extension` | Only show files with this extension; repeat or comma-separate values |
| `-g`, `--glob` | Only show files matching this glob; repeat or comma-separate values |
| `-f`, `--format` | Output format: text, json, xml, yaml, markdown, or html |
| `--layout` | Layout style: vertical or horizontal |
| `--compare-snapshot` | Compare file sizes against a previous snapshot JSON file |
| `--save-snapshot` | Write a file-size snapshot JSON file for future comparison |
| `--stats` | Show summary statistics |
| `--no-color` | Disable color even if supported |

### Pattern Handling Options

| Option | Description |
|--------|-------------|
| `-i`, `--ignore-pattern` | Additional regex pattern to ignore |
| `-I`, `--ignore-patterns` | File containing patterns to ignore |
| `--no-ignore` | Disable default ignore patterns |
| `--show-all` | Show all files (same as --no-ignore) |

`treeout` also reads `.treeignore` from the target directory when default ignore handling is enabled. Patterns are regexes matched against each basename, the same as `-i` and `-I`.

## Default Ignored Patterns

The following patterns are ignored by default (can be disabled with `--no-ignore`):

- `.git` - Git directory
- `.pytest_cache` - Pytest cache
- `.mypy_cache` - MyPy cache
- `__pycache__` - Python cache
- `node_modules` - Node.js modules
- `.vscode` - VSCode settings
- `.idea` - IntelliJ settings
- `.vs` - Visual Studio settings
- `.venv`, `venv`, `env`, `.env` - Virtual environments
- `.tox` - Tox testing
- `.coverage` - Coverage data
- `.treeignore` - Local treeout ignore file
- `.sass-cache` - SASS cache
- `.next` - Next.js build
- `dist` - Distribution directories
- `build` - Build directories
- `.*_cache` - Any cache directory

## Color Coding

When using the `-c` option, files are color-coded by type:

- 🔵 Blue - Directories
- 🟢 Green - Executable files (.exe, .sh, .py, etc.)
- 🟡 Yellow - Symlinks
- 💠 Cyan - Media files (images, audio, video)
- 🟣 Magenta - Archives (.zip, .tar, etc.)
- 🔴 Red - Special files (config files, json, etc.)

Custom color config files support these color names: `blue`, `green`, `yellow`, `cyan`, `magenta`, and `red`.

## Output Example

```powershell
Directory of D:\Project

├───README.md [2.5KB] [2024-01-24 15:30]
├───setup.py [1.2KB]
├───src
│   ├───main.py
│   └───utils
│       ├───helper.py
│       └───config.json
└───tests
    └───test_main.py

Summary:
Directories: 3
Files: 5
Total size: 15.7KB
```

## Output Files

The command writes the tree to the target directory by default. Text output uses `tree.txt`; other formats use matching extensions such as `tree.json`, `tree.yaml`, `tree.xml`, `tree.md`, or `tree.html`. Override the path with `-o`.

When using colors, color is only applied to text console output.

## Requirements

- Python 3.8 or higher
- No additional dependencies required

## TODOs

### High Priority

- [x] Rename and publish as a package on PyPI, modify script to be a CLI entry point
- [x] Add support for custom output formats (JSON, XML, YAML)
- [x] Add pattern support for file extensions (e.g., show only *.py files)
- [x] Allow specifying a start directory as command-line argument
- [x] Add file permission display option (Unix-style)
- [x] Support for `.treeignore` file in project root (similar to .gitignore)

### Nice to Have

- [ ] Add interactive mode with real-time directory navigation
- [x] Export to HTML and Markdown
- [ ] Export to PDF
- [x] Add Git status integration (show modified/untracked files)
- [x] Support for custom color schemes via config file
- [x] Add search functionality with glob patterns
- [x] Add size comparison between different runs
- [ ] Add progress bar for large directories
- [x] Add option for horizontal tree layout

### Future Considerations

- [ ] Add network share/remote filesystem support
- [ ] Create GUI interface with collapsible tree
- [ ] Add plugin system for custom file type handlers
- [ ] Support for archive inspection (peek into zip/tar files)
- [ ] Add multi-language support for output
- [ ] Create system tray monitoring for directory changes

## License

GPL-3.0 License, see [LICENSE](LICENSE) for details.

## Credits

This project was inspired by the standard `tree` command and aims to provide a more feature-rich alternative for Windows users. Feel free to contribute or suggest new features to enhance the tool further.

## Contact / Author

**For issues, suggestions, or feedback, please contact the author soulwax: [mail me](mailto:soulwax@cock.li); github user: [URL TO](https://github.com/soulwax) or create a new issue o n GitHub, or submit a pull request, any feedback is welcome.**

