"""
Module discovery helper utilities.

Provides shared functionality for discovering and analyzing modules
in the ocs-ci repository by type (fixtures, frameworks, helpers, etc.).
"""

import os
import ast
import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Any
from tools.security import validate_path


def discover_modules(
    repo_path: str,
    target_dir: str,
    pattern: str = "*",
    search_text: Optional[str] = None,
    file_extension: str = ".py",
    recursive: bool = False,
    analyzer: Optional[Any] = None,
    allow_sensitive: bool = False
) -> Dict:
    """
    Discover modules in a directory with optional filtering.

    Args:
        repo_path: Path to repository root
        target_dir: Directory to search (relative to repo_path)
        pattern: Filename pattern to match (default: "*")
        search_text: Optional text to search in description (case-insensitive)
        file_extension: File extension to filter (default: ".py")
        recursive: If True, search recursively (default: False)
        analyzer: Optional ASTAnalyzer instance for Python files
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with:
            - directory: The directory searched
            - total_modules: Total number of modules found (before filters)
            - filtered_modules: Number of modules after filters applied
            - modules: List of module dicts with name, path, description, size_bytes, lines
        Or error dict if validation fails
    """
    # SECURITY: Validate path
    validation_error = validate_path(repo_path, target_dir, allow_sensitive)
    if validation_error:
        return validation_error

    repo_root = Path(repo_path).resolve()
    target_path = (repo_root / target_dir).resolve()

    if not target_path.exists():
        return {
            'error': 'PathNotFound',
            'message': f'Path not found: {target_dir}'
        }

    if not target_path.is_dir():
        return {
            'error': 'NotADirectory',
            'message': f'Path is not a directory: {target_dir}'
        }

    all_modules = []

    try:
        if recursive:
            # Walk directory tree recursively
            for root, dirs, files in os.walk(target_path):
                # Filter out hidden directories and __pycache__ in-place
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

                for filename in files:
                    # Skip hidden files
                    if filename.startswith('.'):
                        continue

                    # Filter by extension
                    if not filename.endswith(file_extension):
                        continue

                    file_path = os.path.join(root, filename)
                    module_entry = _create_module_entry(
                        file_path, filename, repo_root, file_extension, analyzer
                    )
                    all_modules.append(module_entry)
        else:
            # Non-recursive: just list files in target directory
            for entry in target_path.iterdir():
                # Skip hidden files and __pycache__
                if entry.name.startswith('.') or entry.name == '__pycache__':
                    continue

                # Only process files
                if not entry.is_file():
                    continue

                # Filter by extension
                if not entry.name.endswith(file_extension):
                    continue

                file_path = str(entry)
                module_entry = _create_module_entry(
                    file_path, entry.name, repo_root, file_extension, analyzer
                )
                all_modules.append(module_entry)

    except PermissionError:
        return {
            'error': 'PermissionDenied',
            'message': f'Cannot read directory: {target_dir}'
        }

    # Track total before filters
    total_modules = len(all_modules)

    # Apply pattern filter
    if pattern != "*":
        all_modules = [m for m in all_modules if fnmatch.fnmatch(m['name'], pattern)]

    # Apply search text filter (case-insensitive substring match)
    if search_text:
        search_lower = search_text.lower()
        all_modules = [
            m for m in all_modules
            if search_lower in m['name'].lower() or search_lower in m['description'].lower()
        ]

    # Sort by name
    all_modules.sort(key=lambda m: m['name'])

    return {
        'directory': target_dir,
        'total_modules': total_modules,
        'filtered_modules': len(all_modules),
        'modules': all_modules
    }


def extract_description(file_path: str, analyzer: Any) -> str:
    """
    Extract description from Python file's module docstring.

    Args:
        file_path: Path to Python file
        analyzer: ASTAnalyzer instance

    Returns:
        First line of module docstring, truncated to 200 chars,
        or "No description available" if no docstring found
    """
    tree, error = analyzer.parse_file(file_path)
    if error or tree is None:
        return 'No description available'

    # Extract module docstring
    docstring = ast.get_docstring(tree)
    if not docstring:
        return 'No description available'

    # Get first line and truncate to 200 chars
    first_line = docstring.split('\n')[0].strip()
    if len(first_line) > 200:
        first_line = first_line[:200]

    return first_line


def extract_config_description(file_path: str) -> str:
    """
    Extract description from config file's first comment line.

    Args:
        file_path: Path to config file

    Returns:
        First comment line (without #), truncated to 200 chars,
        or "Configuration file" if no comment found
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Read first 10 lines
            for _ in range(10):
                line = f.readline()
                if not line:
                    break

                line = line.strip()
                # Find first comment line
                if line.startswith('#'):
                    # Remove # and strip whitespace
                    comment = line[1:].strip()
                    # Truncate to 200 chars
                    if len(comment) > 200:
                        comment = comment[:200]
                    return comment

        return 'Configuration file'

    except Exception:
        return 'Configuration file'


def _create_module_entry(
    file_path: str,
    filename: str,
    repo_root: Path,
    file_extension: str,
    analyzer
) -> Dict:
    """
    Create module entry dict with metadata

    Args:
        file_path: Absolute path to file
        filename: File name
        repo_root: Repository root path
        file_extension: Expected file extension
        analyzer: ASTAnalyzer instance (optional)

    Returns:
        Dict with name, path, description, size_bytes, lines
    """
    relative_path = os.path.relpath(file_path, repo_root)

    # Extract description
    if file_extension == '.py' and analyzer:
        description = extract_description(file_path, analyzer)
    elif file_extension != '.py':
        description = extract_config_description(file_path)
    else:
        description = 'No description available'

    # Get file stats
    stat = os.stat(file_path)
    lines = _count_lines(file_path)

    return {
        'name': filename,
        'path': relative_path,
        'description': description,
        'size_bytes': stat.st_size,
        'lines': lines
    }


def _count_lines(file_path: str) -> int:
    """
    Count lines in a file.

    Args:
        file_path: Path to file

    Returns:
        Number of lines in file, or 0 if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except (OSError, UnicodeDecodeError):
        return 0
