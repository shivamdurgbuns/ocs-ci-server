"""
list_modules tool - Browse ocs-ci repository structure

SECURITY: Includes path validation to prevent directory traversal attacks
and sensitive directory access.
"""

import os
from pathlib import Path
from typing import Dict, List
import fnmatch
from tools.security import validate_path


def list_modules_tool(repo_path: str, path: str = "", pattern: str = "*", allow_sensitive: bool = False) -> Dict:
    """
    List files and directories in ocs-ci repository

    Args:
        repo_path: Path to ocs-ci repository root
        path: Relative path within repo (default: root)
        pattern: Filter pattern (default: "*")
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with items list
    """
    # SECURITY: Validate path to prevent traversal attacks and sensitive access
    validation_error = validate_path(repo_path, path, allow_sensitive)
    if validation_error:
        return validation_error

    repo_root = Path(repo_path).resolve()
    target_path = (repo_root / path).resolve()

    if not target_path.exists():
        return {
            'error': 'PathNotFound',
            'message': f'Path not found: {path}'
        }

    if not target_path.is_dir():
        return {
            'error': 'NotADirectory',
            'message': f'Path is not a directory: {path}'
        }

    items = []

    try:
        for entry in sorted(target_path.iterdir()):
            # Skip hidden files and __pycache__
            if entry.name.startswith('.') or entry.name == '__pycache__':
                continue

            # Apply pattern filter
            if not fnmatch.fnmatch(entry.name, pattern):
                continue

            if entry.is_file():
                items.append({
                    'name': entry.name,
                    'type': 'file',
                    'size_bytes': entry.stat().st_size,
                    'lines': _count_lines(entry) if entry.suffix == '.py' else None
                })
            elif entry.is_dir():
                # Count files in directory
                file_count = len([f for f in entry.iterdir() if f.is_file()])
                items.append({
                    'name': entry.name,
                    'type': 'directory',
                    'file_count': file_count
                })

    except PermissionError:
        return {
            'error': 'PermissionDenied',
            'message': f'Cannot read directory: {path}'
        }

    return {
        'path': path,
        'total_items': len(items),
        'items': items
    }


def _count_lines(file_path: Path) -> int:
    """Count lines in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except:
        return 0
