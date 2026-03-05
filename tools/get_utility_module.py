"""
get_utility_module tool - List utility modules

SECURITY: Includes path validation via module_discovery helper.
"""

from typing import Dict, Optional
from tools.module_discovery import discover_modules


def get_utility_module_tool(
    repo_path: str,
    pattern: str = "*",
    search_text: Optional[str] = None,
    analyzer=None,
    allow_sensitive: bool = False
) -> Dict:
    """
    List utility modules in ocs_ci/utility/

    Args:
        repo_path: Path to ocs-ci repository root
        pattern: Filename pattern (e.g., "*retry*")
        search_text: Search within descriptions
        analyzer: ASTAnalyzer instance
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with directory, total_modules, filtered_modules, modules list
    """
    return discover_modules(
        repo_path=repo_path,
        target_dir="ocs_ci/utility",
        pattern=pattern,
        search_text=search_text,
        file_extension=".py",
        recursive=False,
        analyzer=analyzer,
        allow_sensitive=allow_sensitive
    )
