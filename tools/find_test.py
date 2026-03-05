"""
find_test tool - Find test by name or nodeid

SECURITY: Includes path validation to prevent directory traversal attacks
and sensitive directory access.
"""

import ast
from pathlib import Path
from typing import Dict, List
from tools.security import validate_path


def find_test_tool(repo_path: str, test_name: str, allow_sensitive: bool = False) -> Dict:
    """
    Find test by name or pytest nodeid

    Args:
        repo_path: Path to ocs-ci repository root
        test_name: Test name or pytest nodeid (e.g., "test_foo" or "path/file.py::test_foo")
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with test location and metadata
    """
    repo_root = Path(repo_path).resolve()

    # Parse nodeid if provided
    if '::' in test_name:
        file_path, test_path = test_name.split('::', 1)

        # SECURITY: Validate path to prevent traversal attacks and sensitive access
        validation_error = validate_path(repo_path, file_path, allow_sensitive)
        if validation_error:
            return validation_error

        target_path = (repo_root / file_path).resolve()

        # Parse class::method if present
        if '::' in test_path:
            class_name, method_name = test_path.split('::', 1)
            return _find_test_in_file(target_path, method_name, class_name, file_path, repo_root)
        else:
            return _find_test_in_file(target_path, test_path, None, file_path, repo_root)
    else:
        # Search all test files
        return _search_all_tests(repo_root, test_name)


def _find_test_in_file(
    file_path: Path,
    test_name: str,
    class_name: str,
    original_path: str,
    repo_root: Path
) -> Dict:
    """Find test in a specific file"""

    if not file_path.exists():
        return {
            'error': 'FileNotFound',
            'message': f'File not found: {original_path}'
        }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())

        # Find the test function
        test_info = _find_test_node(tree, test_name, class_name)

        if not test_info:
            return {
                'error': 'TestNotFound',
                'message': f'Test {test_name} not found in {original_path}'
            }

        # Extract fixtures from function parameters
        fixtures = _extract_fixtures(test_info['node'])

        return {
            'file_path': original_path,
            'line_number': test_info['line_number'],
            'test_name': test_name,
            'class_name': class_name,
            'fixtures': fixtures
        }

    except SyntaxError as e:
        return {
            'error': 'SyntaxError',
            'message': f'Failed to parse file: {str(e)}'
        }


def _search_all_tests(repo_root: Path, test_name: str) -> Dict:
    """Search all test files for a test by name"""

    # Search for test files
    test_files = list(repo_root.rglob('test_*.py')) + list(repo_root.rglob('*_test.py'))

    for test_file in test_files:
        # Skip hidden files and __pycache__
        if any(part.startswith('.') or part == '__pycache__' for part in test_file.parts):
            continue

        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())

            # Search for test
            test_info = _find_test_node(tree, test_name, None)

            if test_info:
                fixtures = _extract_fixtures(test_info['node'])
                relative_path = str(test_file.relative_to(repo_root))

                return {
                    'file_path': relative_path,
                    'line_number': test_info['line_number'],
                    'test_name': test_name,
                    'class_name': test_info.get('class_name'),
                    'fixtures': fixtures
                }

        except (SyntaxError, UnicodeDecodeError, PermissionError):
            continue

    return {
        'error': 'TestNotFound',
        'message': f'Test {test_name} not found in repository'
    }


def _find_test_node(tree: ast.AST, test_name: str, class_name: str = None) -> Dict:
    """Find test function node in AST"""

    for node in ast.walk(tree):
        # If searching within a class
        if class_name and isinstance(node, ast.ClassDef) and node.name == class_name:
            # Search for method within class
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == test_name:
                    return {
                        'node': item,
                        'line_number': item.lineno,
                        'class_name': class_name
                    }

        # Search for standalone function
        elif not class_name and isinstance(node, ast.FunctionDef) and node.name == test_name:
            # Check if this function is not inside a class
            # (simple check: if parent is Module or not ClassDef)
            return {
                'node': node,
                'line_number': node.lineno
            }

    return None


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
