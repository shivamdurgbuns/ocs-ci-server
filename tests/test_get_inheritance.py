import pytest
import tempfile
import os
import shutil
from pathlib import Path
from tools.get_inheritance import get_inheritance_tool
from analyzers.ast_analyzer import ASTAnalyzer
from analyzers.import_resolver import ImportResolver


@pytest.fixture
def temp_repo():
    """Create a temporary fake repository with inheritance"""
    temp_dir = tempfile.mkdtemp()

    # Create structure
    os.makedirs(os.path.join(temp_dir, 'ocs_ci'))

    # Create base class
    with open(os.path.join(temp_dir, 'ocs_ci', 'base.py'), 'w') as f:
        f.write("""# Base class
class BaseClass:
    def base_method(self):
        pass

    def shared_method(self):
        pass
""")

    # Create child class
    with open(os.path.join(temp_dir, 'ocs_ci', 'child.py'), 'w') as f:
        f.write("""# Child class
from ocs_ci.base import BaseClass

class ChildClass(BaseClass):
    def child_method(self):
        pass

    def shared_method(self):
        # Override
        pass
""")

    yield temp_dir

    shutil.rmtree(temp_dir)


def test_get_inheritance_basic(temp_repo):
    """Test basic inheritance resolution"""
    analyzer = ASTAnalyzer()
    resolver = ImportResolver(repo_path=temp_repo)

    result = get_inheritance_tool(
        repo_path=temp_repo,
        file_path="ocs_ci/child.py",
        class_name="ChildClass",
        analyzer=analyzer,
        resolver=resolver
    )

    assert 'mro' in result
    assert 'all_methods' in result
    # Should have ChildClass and BaseClass in MRO
    assert len(result['mro']) >= 2


def test_get_inheritance_methods(temp_repo):
    """Test inherited methods extraction"""
    analyzer = ASTAnalyzer()
    resolver = ImportResolver(repo_path=temp_repo)

    result = get_inheritance_tool(
        repo_path=temp_repo,
        file_path="ocs_ci/child.py",
        class_name="ChildClass",
        analyzer=analyzer,
        resolver=resolver
    )

    assert 'all_methods' in result
    # Should include methods from both classes
    all_method_names = []
    for class_methods in result['all_methods'].values():
        all_method_names.extend([m['name'] for m in class_methods])

    assert 'child_method' in all_method_names
    assert 'base_method' in all_method_names


def test_get_inheritance_conflicts(temp_repo):
    """Test method conflict detection"""
    analyzer = ASTAnalyzer()
    resolver = ImportResolver(repo_path=temp_repo)

    result = get_inheritance_tool(
        repo_path=temp_repo,
        file_path="ocs_ci/child.py",
        class_name="ChildClass",
        analyzer=analyzer,
        resolver=resolver
    )

    assert 'conflicts' in result
    # shared_method is overridden
    if result['conflicts']:
        assert any('shared_method' in str(c) for c in result['conflicts'])


def test_path_traversal_blocked(temp_repo):
    """Test that path traversal attacks are blocked"""
    analyzer = ASTAnalyzer()
    resolver = ImportResolver(repo_path=temp_repo)

    result = get_inheritance_tool(
        repo_path=temp_repo,
        file_path="../../../etc/passwd",
        class_name="SomeClass",
        analyzer=analyzer,
        resolver=resolver
    )

    assert 'error' in result
    assert result['error'] == 'SecurityError'


def test_sensitive_directory_blocked_data(temp_repo):
    """Test that /data directory access is blocked"""
    # Create data directory with Python file
    os.makedirs(os.path.join(temp_repo, 'data'))
    with open(os.path.join(temp_repo, 'data', 'config.py'), 'w') as f:
        f.write('class Config:\n    pass\n')

    analyzer = ASTAnalyzer()
    resolver = ImportResolver(repo_path=temp_repo)

    result = get_inheritance_tool(
        repo_path=temp_repo,
        file_path='data/config.py',
        class_name='Config',
        analyzer=analyzer,
        resolver=resolver
    )

    assert 'error' in result
    assert result['error'] == 'AccessDenied'
    assert 'sensitive' in result['message'].lower()


def test_sensitive_directory_allowed_with_flag(temp_repo):
    """Test that sensitive directories can be accessed with flag"""
    # Create data directory with Python file
    os.makedirs(os.path.join(temp_repo, 'data'))
    with open(os.path.join(temp_repo, 'data', 'config.py'), 'w') as f:
        f.write('class Config:\n    pass\n')

    analyzer = ASTAnalyzer()
    resolver = ImportResolver(repo_path=temp_repo)

    result = get_inheritance_tool(
        repo_path=temp_repo,
        file_path='data/config.py',
        class_name='Config',
        analyzer=analyzer,
        resolver=resolver,
        allow_sensitive=True
    )

    assert 'mro' in result
    assert 'all_methods' in result
