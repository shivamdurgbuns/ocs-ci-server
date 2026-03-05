"""
get_deployment_module tool - List deployment modules

SECURITY: Includes path validation via module_discovery helper.
"""

from typing import Dict, Optional
from tools.module_discovery import discover_modules


def get_deployment_module_tool(
    repo_path: str,
    pattern: str = "*",
    search_text: Optional[str] = None,
    analyzer=None,
    allow_sensitive: bool = False
) -> Dict:
    """
    List deployment modules in ocs_ci/deployment/

    Args:
        repo_path: Path to ocs-ci repository root
        pattern: Filename pattern (e.g., "*aws*")
        search_text: Search within descriptions
        analyzer: ASTAnalyzer instance
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with directory, total_modules, filtered_modules, modules list
    """
    return discover_modules(
        repo_path=repo_path,
        target_dir="ocs_ci/deployment",
        pattern=pattern,
        search_text=search_text,
        file_extension=".py",
        recursive=False,
        analyzer=analyzer,
        allow_sensitive=allow_sensitive
    )
