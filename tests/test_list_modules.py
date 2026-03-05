import pytest
import tempfile
import os
import shutil
from tools.list_modules import list_modules_tool


@pytest.fixture
def temp_repo():
    """Create a temporary fake repository"""
    temp_dir = tempfile.mkdtemp()

    # Create structure
    os.makedirs(os.path.join(temp_dir, 'ocs_ci', 'ocs'))
    os.makedirs(os.path.join(temp_dir, 'tests'))

    # Create some files
    with open(os.path.join(temp_dir, 'ocs_ci', 'ocs', 'ocp.py'), 'w') as f:
        f.write('# OCP module\nclass OCP:\n    pass\n')

    with open(os.path.join(temp_dir, 'tests', 'test_example.py'), 'w') as f:
        f.write('def test_example():\n    pass\n')

    yield temp_dir

    shutil.rmtree(temp_dir)


def test_list_modules_root(temp_repo):
    """Test listing modules at root"""
    result = list_modules_tool(temp_repo, path="", pattern="*")

    assert 'items' in result
    assert any(item['name'] == 'ocs_ci' for item in result['items'])
    assert any(item['name'] == 'tests' for item in result['items'])


def test_list_modules_subdirectory(temp_repo):
    """Test listing modules in subdirectory"""
    result = list_modules_tool(temp_repo, path="ocs_ci/ocs", pattern="*.py")

    assert 'items' in result
    assert any(item['name'] == 'ocp.py' for item in result['items'])


def test_list_modules_pattern_filter(temp_repo):
    """Test pattern filtering"""
    result = list_modules_tool(temp_repo, path="", pattern="*.py")

    # Should not include directories
    assert all(item['type'] == 'file' for item in result['items'])


def test_path_traversal_blocked(temp_repo):
    """Test that path traversal attacks are blocked"""
    result = list_modules_tool(temp_repo, path="../../../etc", pattern="*")

    assert 'error' in result
    assert result['error'] == 'SecurityError'


def test_sensitive_directory_blocked_data(temp_repo):
    """Test that /data directory access is blocked"""
    # Create data directory
    os.makedirs(os.path.join(temp_repo, 'data'))
    with open(os.path.join(temp_repo, 'data', 'secrets.yaml'), 'w') as f:
        f.write('password: secret123')

    result = list_modules_tool(temp_repo, path='data', pattern='*')

    assert 'error' in result
    assert result['error'] == 'AccessDenied'
    assert 'sensitive' in result['message'].lower()


def test_sensitive_directory_blocked_git(temp_repo):
    """Test that .git directory access is blocked"""
    result = list_modules_tool(temp_repo, path='.git', pattern='*')

    assert 'error' in result
    assert result['error'] == 'AccessDenied'


def test_sensitive_directory_allowed_with_flag(temp_repo):
    """Test that sensitive directories can be accessed with flag"""
    # Create data directory with file
    os.makedirs(os.path.join(temp_repo, 'data'))
    with open(os.path.join(temp_repo, 'data', 'test.txt'), 'w') as f:
        f.write('test content')

    result = list_modules_tool(temp_repo, path='data', pattern='*', allow_sensitive=True)

    assert 'items' in result
    assert any(item['name'] == 'test.txt' for item in result['items'])
