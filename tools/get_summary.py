"""
get_summary tool - Get file/class summary with inheritance

SECURITY: Includes path validation to prevent directory traversal attacks
and sensitive directory access.
"""

import os
from pathlib import Path
from typing import Dict, Optional
from analyzers.ast_analyzer import ASTAnalyzer
from analyzers.import_resolver import ImportResolver
from analyzers.summarizer import Summarizer
from tools.security import validate_path


def get_summary_tool(
    repo_path: str,
    file_path: str,
    class_name: Optional[str],
    analyzer: ASTAnalyzer,
    resolver: ImportResolver,
    summarizer: Summarizer,
    allow_sensitive: bool = False
) -> Dict:
    """
    Get summary of file or class with inheritance info

    Args:
        repo_path: Repository root path
        file_path: Relative path to file
        class_name: Class name (None for file-level summary)
        analyzer: AST analyzer instance
        resolver: Import resolver instance
        summarizer: Summarizer instance
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Summary dict
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

    # Parse file
    classes = analyzer.extract_classes(str(target_path))

    if class_name:
        # Class-level summary
        return _get_class_summary(
            str(target_path),
            class_name,
            classes,
            analyzer,
            resolver,
            summarizer
        )
    else:
        # File-level summary
        return summarizer.format_file_summary({
            'file_path': file_path,
            'classes': classes,
            'functions': []  # TODO: extract functions
        })


def _get_class_summary(
    file_path: str,
    class_name: str,
    classes: list,
    analyzer: ASTAnalyzer,
    resolver: ImportResolver,
    summarizer: Summarizer
) -> Dict:
    """Get summary for a specific class with inheritance"""

    # Find the class
    class_info = None
    for cls in classes:
        if cls['name'] == class_name:
            class_info = cls
            break

    if not class_info:
        return {
            'error': 'ClassNotFound',
            'message': f'Class {class_name} not found in file'
        }

    # Get imports
    imports = resolver.extract_imports(file_path)

    # Get parent classes (multiple inheritance)
    import ast
    with open(file_path, 'r') as f:
        tree = ast.parse(f.read())

    class_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            class_node = node
            break

    parent_classes = []
    if class_node:
        parent_classes = resolver.resolve_parent_classes(
            class_node,
            imports['import_map'],
            file_path
        )

    # Get inherited methods
    inherited_methods = {}
    for parent in parent_classes:
        if parent['found']:
            parent_methods = _extract_parent_methods(
                parent['file_path'],
                parent['parent_name'],
                analyzer
            )
            inherited_methods[parent['parent_name']] = parent_methods

    # Format summary
    return summarizer.format_class_summary(
        class_info,
        parent_classes,
        inherited_methods
    )


def _extract_parent_methods(
    parent_file: str,
    parent_class_name: str,
    analyzer: ASTAnalyzer
) -> list:
    """Extract methods from parent class"""

    if not os.path.exists(parent_file):
        return []

    classes = analyzer.extract_classes(parent_file)

    for cls in classes:
        if cls['name'] == parent_class_name:
            return cls.get('methods', [])

    return []
