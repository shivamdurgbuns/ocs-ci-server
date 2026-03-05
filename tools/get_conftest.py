"""
get_conftest tool - List conftest.py files

SECURITY: Includes path validation via module_discovery helper.
"""

from typing import Dict, Optional
from tools.module_discovery import discover_modules


def get_conftest_tool(
    repo_path: str,
    pattern: str = "*",
    search_text: Optional[str] = None,
    analyzer=None,
    allow_sensitive: bool = False
) -> Dict:
    """
    List conftest.py files in tests/ directory tree

    Args:
        repo_path: Path to ocs-ci repository root
        pattern: Path pattern (e.g., "*functional*") - matches full path
        search_text: Search within descriptions
        analyzer: ASTAnalyzer instance
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with directory, total_modules, filtered_modules, modules list
    """
    result = discover_modules(
        repo_path=repo_path,
        target_dir="tests",
        pattern="conftest.py",
        search_text=search_text,
        file_extension=".py",
        recursive=True,
        analyzer=analyzer,
        allow_sensitive=allow_sensitive
    )

    # Apply path pattern filter if not default
    if pattern != "*":
        import fnmatch
        filtered = [
            m for m in result["modules"]
            if fnmatch.fnmatch(m["path"], f"*{pattern}*")
        ]
        result["filtered_modules"] = len(filtered)
        result["modules"] = filtered

    return result
