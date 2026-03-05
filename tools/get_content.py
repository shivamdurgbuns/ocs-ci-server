"""
get_content tool - Read file content with optional line ranges

SECURITY: Includes path validation to prevent directory traversal attacks
and sensitive directory access.
"""

from pathlib import Path
from typing import Dict, Optional
from tools.security import validate_path


def get_content_tool(
    repo_path: str,
    file_path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    allow_sensitive: bool = False
) -> Dict:
    """
    Read file content with optional line range

    Args:
        repo_path: Path to ocs-ci repository root
        file_path: Relative path to file
        start_line: Starting line number (1-indexed, inclusive)
        end_line: Ending line number (1-indexed, inclusive)
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with content and metadata
    """
    # SECURITY: Validate path to prevent traversal attacks and sensitive access
    validation_error = validate_path(repo_path, file_path, allow_sensitive)
    if validation_error:
        return validation_error

    repo_root = Path(repo_path).resolve()
    target_path = (repo_root / file_path).resolve()

    if not target_path.exists():
        return {
            'error': 'FileNotFound',
            'message': f'File not found: {file_path}'
        }

    if not target_path.is_file():
        return {
            'error': 'NotAFile',
            'message': f'Path is not a file: {file_path}'
        }

    try:
        # Read file with encoding error handling
        with open(target_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        total_lines = len(lines)

        # Apply line range if specified
        if start_line is not None or end_line is not None:
            # Convert to 0-indexed
            start_idx = (start_line - 1) if start_line else 0
            end_idx = end_line if end_line else total_lines

            # Validate range
            if start_idx < 0 or start_idx >= total_lines:
                return {
                    'error': 'InvalidRange',
                    'message': f'Start line {start_line} out of range (1-{total_lines})'
                }

            if end_idx < start_idx or end_idx > total_lines:
                return {
                    'error': 'InvalidRange',
                    'message': f'End line {end_line} out of range ({start_line}-{total_lines})'
                }

            lines = lines[start_idx:end_idx]

        content = ''.join(lines)

        return {
            'file_path': file_path,
            'content': content,
            'total_lines': total_lines,
            'displayed_lines': len(lines),
            'start_line': start_line or 1,
            'end_line': end_line or total_lines
        }

    except UnicodeDecodeError:
        return {
            'error': 'BinaryFile',
            'message': f'File appears to be binary: {file_path}'
        }
    except PermissionError:
        return {
            'error': 'PermissionDenied',
            'message': f'Cannot read file: {file_path}'
        }
    except Exception as e:
        return {
            'error': 'ReadError',
            'message': f'Error reading file: {str(e)}'
        }
