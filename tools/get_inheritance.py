"""
get_inheritance tool - Show full class inheritance chain

SECURITY: Includes path validation to prevent directory traversal attacks
and sensitive directory access.
"""

import ast
from pathlib import Path
from typing import Dict
from analyzers.ast_analyzer import ASTAnalyzer
from analyzers.import_resolver import ImportResolver
from tools.security import validate_path


def get_inheritance_tool(
    repo_path: str,
    file_path: str,
    class_name: str,
    analyzer: ASTAnalyzer,
    resolver: ImportResolver,
    allow_sensitive: bool = False
) -> Dict:
    """
    Get full inheritance chain with all methods and conflicts

    Args:
        repo_path: Path to ocs-ci repository root
        file_path: Relative path to file
        class_name: Name of the class to analyze
        analyzer: AST analyzer instance
        resolver: Import resolver instance
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with MRO, all methods, and conflicts
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

    try:
        # Parse file to find class
        with open(target_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())

        # Find the class node
        class_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                class_node = node
                break

        if not class_node:
            return {
                'error': 'ClassNotFound',
                'message': f'Class {class_name} not found in file'
            }

        # Get imports
        imports = resolver.extract_imports(str(target_path))

        # Resolve parent classes first
        parent_classes = resolver.resolve_parent_classes(
            class_node,
            imports['import_map'],
            str(target_path)
        )

        # Get MRO using resolver
        mro = resolver.get_method_resolution_order(
            class_name,
            parent_classes,
            str(target_path)
        )

        # Extract methods from each class in MRO
        all_methods = {}
        for mro_class in mro:
            class_name_in_mro = mro_class['class']
            file_path_in_mro = mro_class['file']

            # Skip builtins
            if file_path_in_mro == 'builtins':
                all_methods[class_name_in_mro] = []
                continue

            methods = _extract_methods_from_class(
                file_path_in_mro,
                class_name_in_mro,
                analyzer
            )
            all_methods[class_name_in_mro] = methods

        # Detect conflicts (method name appears in multiple classes)
        conflicts = _detect_conflicts(all_methods)

        return {
            'class_name': class_name,
            'file_path': file_path,
            'mro': mro,
            'all_methods': all_methods,
            'conflicts': conflicts
        }

    except SyntaxError as e:
        return {
            'error': 'SyntaxError',
            'message': f'Failed to parse file: {str(e)}'
        }
    except Exception as e:
        return {
            'error': 'AnalysisError',
            'message': f'Error analyzing inheritance: {str(e)}'
        }


def _extract_methods_from_class(
    file_path: str,
    class_name: str,
    analyzer: ASTAnalyzer
) -> list:
    """Extract methods from a specific class"""

    try:
        classes = analyzer.extract_classes(file_path)

        for cls in classes:
            if cls['name'] == class_name:
                return cls.get('methods', [])

    except:
        pass

    return []


def _detect_conflicts(all_methods: Dict) -> list:
    """Detect method name conflicts across inheritance chain"""

    conflicts = []
    method_occurrences = {}

    # Count occurrences of each method name
    for class_name, methods in all_methods.items():
        for method in methods:
            method_name = method['name']
            if method_name not in method_occurrences:
                method_occurrences[method_name] = []
            method_occurrences[method_name].append(class_name)

    # Find methods that appear in multiple classes
    for method_name, classes in method_occurrences.items():
        if len(classes) > 1:
            conflicts.append({
                'method_name': method_name,
                'defined_in': classes,
                'resolution': classes[0]  # First in MRO wins
            })

    return conflicts
