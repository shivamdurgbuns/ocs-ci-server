"""
Import Resolver - Track imports and resolve class inheritance

Prevents hallucinations by showing where inherited methods come from.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Optional


class ImportResolver:
    """Resolve imports and track class inheritance"""

    def __init__(self, repo_path: str):
        """
        Args:
            repo_path: Path to ocs-ci repository root
        """
        self.repo_path = repo_path

    def extract_imports(self, file_path: str) -> Dict:
        """
        Extract all import statements from a Python file

        Returns:
            {
                'from_imports': [...],
                'direct_imports': [...],
                'import_map': {name: module}
            }
        """
        try:
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read())
        except (OSError, SyntaxError):
            return {'from_imports': [], 'direct_imports': [], 'import_map': {}}

        from_imports = []
        direct_imports = []
        import_map = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                # from X import Y
                module = node.module or ''
                names = [alias.name for alias in node.names]
                from_imports.append({'module': module, 'names': names})

                # Build import map
                for name in names:
                    if name != '*':
                        import_map[name] = module

            elif isinstance(node, ast.Import):
                # import X
                for alias in node.names:
                    module = alias.name
                    name = alias.asname or module.split('.')[-1]
                    direct_imports.append({'module': module})
                    import_map[name] = module

        return {
            'from_imports': from_imports,
            'direct_imports': direct_imports,
            'import_map': import_map
        }

    def resolve_parent_class(
        self,
        class_node: ast.ClassDef,
        import_map: Dict[str, str],
        current_file: str
    ) -> Optional[Dict]:
        """
        Resolve parent class to file location

        Args:
            class_node: AST ClassDef node
            import_map: Dict mapping names to modules
            current_file: Current file being analyzed

        Returns:
            {
                'parent_name': str,
                'module': str,
                'file_path': str,
                'found': bool
            }
        """
        if not class_node.bases:
            return None

        # Get first parent (single inheritance for now)
        parent_base = class_node.bases[0]

        # Extract parent name
        if isinstance(parent_base, ast.Name):
            parent_name = parent_base.id
        elif isinstance(parent_base, ast.Attribute):
            parent_name = parent_base.attr
        else:
            return None

        # Resolve to module
        if parent_name in import_map:
            module_path = import_map[parent_name]
            file_path = self._module_to_filepath(module_path)

            return {
                'parent_name': parent_name,
                'module': module_path,
                'file_path': file_path,
                'found': os.path.exists(file_path)
            }

        return None

    def resolve_parent_classes(
        self,
        class_node: ast.ClassDef,
        import_map: Dict[str, str],
        current_file: str
    ) -> List[Dict]:
        """
        Resolve ALL parent classes (multiple inheritance)

        Returns:
            List of parent class info dicts
        """
        if not class_node.bases:
            return []

        parent_classes = []

        for idx, parent_base in enumerate(class_node.bases):
            # Extract parent name
            if isinstance(parent_base, ast.Name):
                parent_name = parent_base.id
            elif isinstance(parent_base, ast.Attribute):
                parent_name = parent_base.attr
            else:
                continue

            # Resolve to module and file
            if parent_name in import_map:
                module_path = import_map[parent_name]
                file_path = self._module_to_filepath(module_path)

                parent_classes.append({
                    'parent_name': parent_name,
                    'module': module_path,
                    'file_path': file_path,
                    'found': os.path.exists(file_path),
                    'order': idx
                })

        return parent_classes

    def get_method_resolution_order(
        self,
        class_name: str,
        parent_classes: List[Dict],
        current_file: str
    ) -> List[Dict]:
        """
        Calculate Method Resolution Order (MRO)

        Returns list of classes in resolution order:
        [CurrentClass, Parent1, Parent2, ..., object]
        """
        mro = [{'class': class_name, 'file': current_file}]

        # Add all parent classes in order
        for parent in parent_classes:
            mro.append({
                'class': parent['parent_name'],
                'file': parent['file_path']
            })

        # Add object at the end
        if not any(c['class'] == 'object' for c in mro):
            mro.append({'class': 'object', 'file': 'builtins'})

        return mro

    def _module_to_filepath(self, module_path: str) -> str:
        """Convert module path to file path"""
        # ocs_ci.ocs.ocp -> ocs_ci/ocs/ocp.py
        # Also check for ocs_ci/ocs/ocp/__init__.py
        relative_path = module_path.replace('.', '/')

        # Try .py file first
        py_file = os.path.join(self.repo_path, relative_path + '.py')
        if os.path.exists(py_file):
            return py_file

        # Try __init__.py in directory
        init_file = os.path.join(self.repo_path, relative_path, '__init__.py')
        if os.path.exists(init_file):
            return init_file

        # Return .py file path as default (even if it doesn't exist)
        return py_file
