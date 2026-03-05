import pytest
import tempfile
import os
from pathlib import Path
from analyzers.ast_analyzer import ASTAnalyzer


@pytest.fixture
def temp_python_file():
    """Create a temporary Python file for testing"""
    content = '''
"""Test module docstring"""

class MyClass:
    """MyClass docstring"""

    def method_one(self, arg1, arg2):
        """Method one docstring"""
        return arg1 + arg2

    def method_two(self):
        """Method two docstring"""
        pass

def standalone_function():
    """Standalone function"""
    return "hello"
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


def test_parse_file_returns_ast_tree(temp_python_file):
    """Test that parse_file returns a valid AST tree"""
    analyzer = ASTAnalyzer()
    tree, error = analyzer.parse_file(temp_python_file)

    assert tree is not None
    assert error is None
    assert hasattr(tree, 'body')


def test_extract_classes_from_file(temp_python_file):
    """Test extracting class information"""
    analyzer = ASTAnalyzer()
    classes = analyzer.extract_classes(temp_python_file)

    assert len(classes) == 1
    assert classes[0]['name'] == 'MyClass'
    assert classes[0]['docstring'] == 'MyClass docstring'
    assert len(classes[0]['methods']) == 2


def test_extract_methods_from_class(temp_python_file):
    """Test extracting method information"""
    analyzer = ASTAnalyzer()
    classes = analyzer.extract_classes(temp_python_file)
    methods = classes[0]['methods']

    assert methods[0]['name'] == 'method_one'
    assert methods[0]['signature'] == 'method_one(self, arg1, arg2)'
    assert methods[0]['docstring'] == 'Method one docstring'


def test_parse_file_with_syntax_error():
    """Test handling of syntax errors"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('def broken syntax here')
        temp_path = f.name

    try:
        analyzer = ASTAnalyzer()
        tree, error = analyzer.parse_file(temp_path)

        assert tree is None
        assert error is not None
        assert error['error'] == 'SyntaxError'
    finally:
        os.unlink(temp_path)


def test_extract_classes_with_inheritance():
    """Test extracting classes with base classes"""
    content = '''
class BaseClass:
    """Base class"""
    pass

class DerivedClass(BaseClass):
    """Derived class"""
    def method(self):
        pass
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        analyzer = ASTAnalyzer()
        classes = analyzer.extract_classes(temp_path)

        assert len(classes) == 2
        assert classes[0]['name'] == 'BaseClass'
        assert classes[0]['bases'] == []
        assert classes[1]['name'] == 'DerivedClass'
        assert classes[1]['bases'] == ['BaseClass']
    finally:
        os.unlink(temp_path)


def test_extract_methods_with_various_signatures():
    """Test extracting methods with different signatures"""
    content = '''
class MyClass:
    def no_args(self):
        pass

    def with_args(self, arg1, arg2, arg3):
        pass

    def with_defaults(self, arg1, arg2=None):
        pass

    def with_varargs(self, *args):
        pass

    def with_kwargs(self, **kwargs):
        pass

    def with_all(self, arg1, *args, **kwargs):
        pass
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        analyzer = ASTAnalyzer()
        classes = analyzer.extract_classes(temp_path)
        methods = classes[0]['methods']

        assert len(methods) == 6
        assert methods[0]['signature'] == 'no_args(self)'
        assert methods[1]['signature'] == 'with_args(self, arg1, arg2, arg3)'
        assert methods[3]['signature'] == 'with_varargs(self, *args)'
        assert methods[4]['signature'] == 'with_kwargs(self, **kwargs)'
        assert methods[5]['signature'] == 'with_all(self, arg1, *args, **kwargs)'
    finally:
        os.unlink(temp_path)


def test_extract_classes_preserves_line_numbers():
    """Test that line numbers are correctly recorded"""
    content = '''
# Line 2

class FirstClass:  # Line 4
    def method_one(self):  # Line 5
        pass

class SecondClass:  # Line 8
    def method_two(self):  # Line 9
        pass
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        analyzer = ASTAnalyzer()
        classes = analyzer.extract_classes(temp_path)

        assert classes[0]['line_number'] == 4
        assert classes[0]['methods'][0]['line_number'] == 5
        assert classes[1]['line_number'] == 8
        assert classes[1]['methods'][0]['line_number'] == 9
    finally:
        os.unlink(temp_path)


def test_extract_classes_empty_file():
    """Test extracting classes from empty file"""
    content = '''
# Just a comment
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        analyzer = ASTAnalyzer()
        classes = analyzer.extract_classes(temp_path)

        assert len(classes) == 0
    finally:
        os.unlink(temp_path)


def test_class_without_docstring():
    """Test extracting class without docstring"""
    content = '''
class NoDocstring:
    def method(self):
        return 42
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        analyzer = ASTAnalyzer()
        classes = analyzer.extract_classes(temp_path)

        assert classes[0]['docstring'] is None
        assert classes[0]['methods'][0]['docstring'] is None
    finally:
        os.unlink(temp_path)
