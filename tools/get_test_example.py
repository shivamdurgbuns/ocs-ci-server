"""
get_test_example tool - Find example tests matching criteria

SECURITY: Includes path validation to prevent directory traversal attacks
and sensitive directory access.
"""

import ast
from pathlib import Path
from typing import Dict, List, Optional
from tools.security import validate_path


def get_test_example_tool(
    repo_path: str,
    pattern: str,
    fixture_name: Optional[str] = None,
    path: str = "",
    max_results: int = 5,
    allow_sensitive: bool = False
) -> Dict:
    """
    Find example tests matching pattern or using specific fixture

    Args:
        repo_path: Path to ocs-ci repository root
        pattern: Pattern to search for in test names or content
        fixture_name: Optional fixture name to filter by
        path: Relative path within repo to search (default: root)
        max_results: Maximum number of examples to return
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with examples list
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

    # Find test files
    test_files = list(search_path.rglob('test_*.py')) + list(search_path.rglob('*_test.py'))

    examples = []

    for test_file in test_files:
        # Skip hidden files and __pycache__
        if any(part.startswith('.') or part == '__pycache__' for part in test_file.parts):
            continue

        # Search this file
        file_examples = _search_test_file(
            test_file,
            pattern,
            fixture_name,
            repo_root
        )

        examples.extend(file_examples)

        # Stop if we have enough
        if len(examples) >= max_results:
            break

    # Limit results
    examples = examples[:max_results]

    return {
        'pattern': pattern,
        'fixture_name': fixture_name,
        'total_found': len(examples),
        'examples': examples
    }


def _search_test_file(
    file_path: Path,
    pattern: str,
    fixture_name: Optional[str],
    repo_root: Path
) -> List[Dict]:
    """Search a single test file for matching tests"""

    examples = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)

        relative_path = str(file_path.relative_to(repo_root))

        # Find all test functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                # Check if it matches criteria
                if _matches_criteria(node, pattern, fixture_name, content):
                    # Extract source code
                    source = _extract_function_source(node, content)

                    # Extract fixtures
                    fixtures = _extract_fixtures(node)

                    examples.append({
                        'file_path': relative_path,
                        'test_name': node.name,
                        'line_number': node.lineno,
                        'fixtures': fixtures,
                        'source': source
                    })

    except (SyntaxError, UnicodeDecodeError, PermissionError):
        pass

    return examples


def _matches_criteria(
    node: ast.FunctionDef,
    pattern: str,
    fixture_name: Optional[str],
    content: str
) -> bool:
    """Check if test matches search criteria"""

    # Check fixture requirement
    if fixture_name:
        fixtures = _extract_fixtures(node)
        if fixture_name not in fixtures:
            return False

    # Check pattern (if provided)
    if pattern:
        # Check in function name
        if pattern.lower() in node.name.lower():
            return True

        # Check in docstring
        docstring = ast.get_docstring(node)
        if docstring and pattern.lower() in docstring.lower():
            return True

        # Pattern not found
        if not fixture_name:  # Only fail if we're not filtering by fixture
            return False

    return True


def _extract_fixtures(func_node: ast.FunctionDef) -> List[str]:
    """Extract fixture names from function parameters"""

    fixtures = []

    if not func_node.args:
        return fixtures

    # Get all parameter names (excluding self, cls)
    for arg in func_node.args.args:
        if arg.arg not in ['self', 'cls']:
            fixtures.append(arg.arg)

    return fixtures


def _extract_function_source(node: ast.FunctionDef, full_content: str) -> str:
    """Extract source code for a function"""

    try:
        lines = full_content.split('\n')

        # Get function lines (from lineno to end_lineno)
        if hasattr(node, 'end_lineno') and node.end_lineno:
            func_lines = lines[node.lineno - 1:node.end_lineno]
        else:
            # Fallback: take 20 lines from start
            func_lines = lines[node.lineno - 1:node.lineno + 19]

        return '\n'.join(func_lines)

    except:
        return ""
