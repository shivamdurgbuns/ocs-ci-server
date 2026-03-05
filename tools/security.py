"""
Security utilities for path validation

Provides centralized security validation to prevent:
- Directory traversal attacks
- Access to sensitive directories
"""

from pathlib import Path
from typing import Dict, Optional, List

# Sensitive directories that should be blocked
SENSITIVE_PATHS = [
    'data',           # Contains credentials and secrets
    '.git',           # Git internals
    '.github',        # GitHub workflows/secrets
    'credentials',    # Common credential directory
    'secrets',        # Common secrets directory
    '.env',           # Environment files
    '__pycache__',    # Python cache (not sensitive but not useful)
]


def validate_path(
    repo_path: str,
    file_path: str,
    allow_sensitive: bool = False
) -> Optional[Dict]:
    """
    Validate path for security issues

    Args:
        repo_path: Repository root path
        file_path: Relative path to validate
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Error dict if validation fails, None if valid
    """
    # Normalize paths
    repo_root = Path(repo_path).resolve()
    target_path = (repo_root / file_path).resolve()

    # Check 1: Directory traversal protection
    if not str(target_path).startswith(str(repo_root)):
        return {
            'error': 'SecurityError',
            'message': f'Path escapes repository boundaries: {file_path}'
        }

    # Check 2: Sensitive directory protection (unless explicitly allowed)
    if not allow_sensitive:
        path_parts = Path(file_path).parts
        for part in path_parts:
            if part in SENSITIVE_PATHS:
                return {
                    'error': 'AccessDenied',
                    'message': f'Access to sensitive directory denied: {part}'
                }

    return None  # Valid path
