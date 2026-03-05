"""AST Analyzer for parsing Python files.

This module provides functionality to parse Python files using Abstract Syntax Trees (AST)
and extract structured information about classes, methods, docstrings, and more.
"""

import ast
from typing import Tuple, Optional, Dict, List, Any


class ASTAnalyzer:
    """Analyzer for extracting structured information from Python files using AST."""

    def parse_file(self, file_path: str) -> Tuple[Optional[ast.AST], Optional[Dict[str, Any]]]:
        """Parse a Python file and return the AST tree.

        Args:
            file_path: Path to the Python file to parse

        Returns:
            Tuple of (AST tree, error dict). If successful, returns (tree, None).
            If there's an error, returns (None, error_dict).
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source, filename=file_path)
            return tree, None
        except SyntaxError as e:
            return None, {
                'error': 'SyntaxError',
                'message': str(e),
                'line': e.lineno,
                'offset': e.offset
            }
        except Exception as e:
            return None, {
                'error': type(e).__name__,
                'message': str(e)
            }

    def extract_classes(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract all classes from a Python file.

        Args:
            file_path: Path to the Python file

        Returns:
            List of dictionaries containing class information including:
            - name: Class name
            - docstring: Class docstring
            - line_number: Line number where class is defined
            - methods: List of method dictionaries
            - bases: List of base class names
        """
        tree, error = self.parse_file(file_path)
        if error or tree is None:
            return []

        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = {
                    'name': node.name,
                    'docstring': ast.get_docstring(node),
                    'line_number': node.lineno,
                    'methods': self._extract_methods_from_class(node),
                    'bases': [self._get_base_name(base) for base in node.bases]
                }
                classes.append(class_info)

        return classes

    def _extract_methods_from_class(self, class_node: ast.ClassDef) -> List[Dict[str, Any]]:
        """Extract methods from a class AST node.

        Args:
            class_node: AST ClassDef node

        Returns:
            List of dictionaries containing method information including:
            - name: Method name
            - signature: Method signature string
            - docstring: Method docstring
            - line_number: Line number where method is defined
        """
        methods = []
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = {
                    'name': item.name,
                    'signature': self._get_function_signature(item),
                    'docstring': ast.get_docstring(item),
                    'line_number': item.lineno
                }
                methods.append(method_info)

        return methods

    def _get_function_signature(self, func_node: ast.FunctionDef) -> str:
        """Get function signature as a string.

        Args:
            func_node: AST FunctionDef node

        Returns:
            Function signature string (e.g., "func_name(arg1, arg2)")
        """
        args = func_node.args
        arg_strings = []

        # Regular arguments
        for arg in args.args:
            arg_strings.append(arg.arg)

        # Handle *args
        if args.vararg:
            arg_strings.append(f"*{args.vararg.arg}")

        # Handle **kwargs
        if args.kwarg:
            arg_strings.append(f"**{args.kwarg.arg}")

        return f"{func_node.name}({', '.join(arg_strings)})"

    def _get_base_name(self, base_node: ast.expr) -> str:
        """Extract base class name from AST node.

        Args:
            base_node: AST expression node representing a base class

        Returns:
            Base class name as string
        """
        if isinstance(base_node, ast.Name):
            return base_node.id
        elif isinstance(base_node, ast.Attribute):
            # Handle cases like module.ClassName
            parts = []
            node = base_node
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            parts.reverse()
            return '.'.join(parts)
        else:
            return str(ast.unparse(base_node))
