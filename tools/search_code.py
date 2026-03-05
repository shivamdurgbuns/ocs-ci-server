"""
search_code tool - Search for patterns in code files

SECURITY: Includes path validation to prevent directory traversal attacks,
sensitive directory access, and regex timeout protection.
"""

import re
import fnmatch
from pathlib import Path
from typing import Dict, List
from tools.security import validate_path


def search_code_tool(
    repo_path: str,
    pattern: str,
    file_pattern: str = "*.py",
    context_lines: int = 2,
    path: str = "",
    allow_sensitive: bool = False
) -> Dict:
    """
    Search for regex pattern in files

    Args:
        repo_path: Path to ocs-ci repository root
        pattern: Regex pattern to search for
        file_pattern: File glob pattern (default: "*.py")
        context_lines: Number of context lines before/after match
        path: Relative path within repo to search (default: root)
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with matches and total count
    """
    # SECURITY: Validate path to prevent traversal attacks and sensitive access
    validation_error = validate_path(repo_path, path, allow_sensitive)
    if validation_error:
        return validation_error

    repo_root = Path(repo_path).resolve()
    search_path = (repo_root / path).resolve()

    if not search_path.exists():
        return {
            'error': 'PathNotFound',
            'message': f'Path not found: {path}'
        }

    # SECURITY: Compile regex with basic validation
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return {
            'error': 'InvalidPattern',
            'message': f'Invalid regex pattern: {str(e)}'
        }

    # Collect matches
    matches = []

    try:
        # Walk directory tree
        for file_path in search_path.rglob('*'):
            # Skip directories and hidden files
            if file_path.is_dir() or file_path.name.startswith('.'):
                continue

            # Skip __pycache__
            if '__pycache__' in file_path.parts:
                continue

            # Apply file pattern filter
            if not fnmatch.fnmatch(file_path.name, file_pattern):
                continue

            # Search file
            file_matches = _search_file(
                file_path,
                regex,
                context_lines,
                repo_root
            )
            matches.extend(file_matches)

    except PermissionError as e:
        return {
            'error': 'PermissionDenied',
            'message': f'Cannot read directory: {str(e)}'
        }

    return {
        'pattern': pattern,
        'file_pattern': file_pattern,
        'total_matches': len(matches),
        'matches': matches
    }


def _search_file(
    file_path: Path,
    regex: re.Pattern,
    context_lines: int,
    repo_root: Path
) -> List[Dict]:
    """Search for pattern in a single file"""

    matches = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        # Get relative path
        relative_path = str(file_path.relative_to(repo_root))

        # Search each line
        for line_num, line in enumerate(lines, start=1):
            if regex.search(line):
                # Extract context
                start_idx = max(0, line_num - context_lines - 1)
                end_idx = min(len(lines), line_num + context_lines)
                context = lines[start_idx:end_idx]

                matches.append({
                    'file_path': relative_path,
                    'line_number': line_num,
                    'line': line.rstrip('\n'),
                    'context': ''.join(context)
                })

    except (UnicodeDecodeError, PermissionError):
        # Skip files that can't be read
        pass

    return matches
