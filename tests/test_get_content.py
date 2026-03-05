import pytest
import tempfile
import os
import shutil
from tools.get_content import get_content_tool


@pytest.fixture
def temp_repo():
    """Create a temporary fake repository"""
    temp_dir = tempfile.mkdtemp()

    # Create structure
    os.makedirs(os.path.join(temp_dir, 'ocs_ci'))

    # Create a Python file with known content
    file_content = """# Example file
class TestClass:
    def method_one(self):
        pass

    def method_two(self):
        return True

def function_example():
    pass
"""
    with open(os.path.join(temp_dir, 'ocs_ci', 'example.py'), 'w') as f:
        f.write(file_content)

    yield temp_dir

    shutil.rmtree(temp_dir)


def test_get_content_full_file(temp_repo):
    """Test reading full file content"""
    result = get_content_tool(temp_repo, "ocs_ci/example.py")

    assert 'content' in result
    assert 'total_lines' in result
    assert result['total_lines'] == 10
    assert 'class TestClass' in result['content']
    assert 'def function_example' in result['content']


def test_get_content_line_range(temp_repo):
    """Test reading specific line range"""
    result = get_content_tool(temp_repo, "ocs_ci/example.py", start_line=2, end_line=4)

    assert 'content' in result
    assert 'class TestClass' in result['content']
    assert 'function_example' not in result['content']  # Line 9, outside range


def test_get_content_file_not_found(temp_repo):
    """Test error handling for missing file"""
    result = get_content_tool(temp_repo, "nonexistent.py")

    assert 'error' in result
    assert result['error'] == 'FileNotFound'


def test_path_traversal_blocked(temp_repo):
    """Test that path traversal attacks are blocked"""
    result = get_content_tool(temp_repo, "../../../etc/passwd")

    assert 'error' in result
    assert result['error'] == 'SecurityError'


def test_sensitive_directory_blocked_data(temp_repo):
    """Test that /data directory access is blocked"""
    # Create data directory with sensitive file
    os.makedirs(os.path.join(temp_repo, 'data'))
    with open(os.path.join(temp_repo, 'data', 'secrets.yaml'), 'w') as f:
        f.write('password: secret123')

    result = get_content_tool(temp_repo, file_path='data/secrets.yaml')

    assert 'error' in result
    assert result['error'] == 'AccessDenied'
    assert 'sensitive' in result['message'].lower()


def test_sensitive_directory_blocked_git(temp_repo):
    """Test that .git directory access is blocked"""
    result = get_content_tool(temp_repo, file_path='.git/config')

    assert 'error' in result
    assert result['error'] == 'AccessDenied'


def test_sensitive_directory_allowed_with_flag(temp_repo):
    """Test that sensitive directories can be accessed with flag"""
    # Create data directory with file
    os.makedirs(os.path.join(temp_repo, 'data'))
    with open(os.path.join(temp_repo, 'data', 'test.txt'), 'w') as f:
        f.write('test content')

    result = get_content_tool(temp_repo, file_path='data/test.txt', allow_sensitive=True)

    assert 'content' in result
    assert result['content'] == 'test content'
