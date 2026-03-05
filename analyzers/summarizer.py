"""
Summarizer - Format analysis results for token efficiency

Optimizes output for Claude's understanding while minimizing tokens.
"""

from typing import Dict, List


class Summarizer:
    """Format parsed code into token-efficient summaries"""

    def format_class_summary(
        self,
        class_info: Dict,
        parent_classes: List[Dict],
        inherited_methods: Dict[str, List[Dict]]
    ) -> Dict:
        """
        Format class information with inheritance details

        Args:
            class_info: Basic class info from AST
            parent_classes: List of parent class info
            inherited_methods: Methods by parent class

        Returns:
            Token-optimized summary dict
        """
        summary = {
            'class_name': class_info['name'],
            'docstring': class_info.get('docstring', ''),
            'line_number': class_info.get('line_number', 0),
            'parent_classes': [
                {
                    'name': p['parent_name'],
                    'module': p.get('module', ''),
                    'file': p.get('file_path', '')
                }
                for p in parent_classes
            ],
            'own_methods': [
                {
                    'name': m['name'],
                    'signature': m['signature'],
                    'line': m.get('line_number', 0),
                    'docstring': m.get('docstring', '')
                }
                for m in class_info.get('methods', [])
            ],
            'inherited_methods': inherited_methods,
            'parent_count': len(parent_classes),
            'own_method_count': len(class_info.get('methods', [])),
            'total_inherited_count': sum(
                len(methods) for methods in inherited_methods.values()
            )
        }

        return summary

    def format_file_summary(self, file_info: Dict) -> Dict:
        """
        Format file-level summary

        Args:
            file_info: File information from analysis

        Returns:
            Token-optimized file summary
        """
        summary = {
            'file_path': file_info['file_path'],
            'classes': [
                {
                    'name': c['name'],
                    'docstring': c.get('docstring', ''),
                    'line': c.get('line_number', 0),
                    'method_count': len(c.get('methods', []))
                }
                for c in file_info.get('classes', [])
            ],
            'functions': [
                {
                    'name': f['name'],
                    'signature': f.get('signature', ''),
                    'line': f.get('line_number', 0)
                }
                for f in file_info.get('functions', [])
            ],
            'class_count': len(file_info.get('classes', [])),
            'function_count': len(file_info.get('functions', []))
        }

        return summary

    def format_method_list(self, methods: List[Dict]) -> List[str]:
        """Format method list compactly"""
        return [
            f"{m['name']}({', '.join(m.get('params', []))})"
            for m in methods
        ]
