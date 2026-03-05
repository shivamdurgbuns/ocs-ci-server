"""
get_conf_file tool - List configuration files

SECURITY: Includes path validation via module_discovery helper.
"""

from typing import Dict, Optional
from tools.module_discovery import discover_modules


def get_conf_file_tool(
    repo_path: str,
    pattern: str = "*",
    search_text: Optional[str] = None,
    allow_sensitive: bool = False
) -> Dict:
    """
    List configuration files in conf/

    Args:
        repo_path: Path to ocs-ci repository root
        pattern: Filename pattern (e.g., "*.yaml")
        search_text: Search within descriptions
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with directory, total_modules, filtered_modules, modules list
    """
    return discover_modules(
        repo_path=repo_path,
        target_dir="conf",
        pattern=pattern,
        search_text=search_text,
        file_extension="",
        recursive=False,
        allow_sensitive=allow_sensitive
    )
