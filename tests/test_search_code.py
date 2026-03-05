import pytest
import tempfile
import os
import shutil
from tools.search_code import search_code_tool


@pytest.fixture
def temp_repo():
    """Create a temporary fake repository"""
    temp_dir = tempfile.mkdtemp()

    # Create structure
    os.makedirs(os.path.join(temp_dir, 'ocs_ci'))
    os.makedirs(os.path.join(temp_dir, 'tests'))

    # Create files with searchable content
    with open(os.path.join(temp_dir, 'ocs_ci', 'example.py'), 'w') as f:
        f.write("""# Example module
class MyClass:
    def my_method(self):
        # TODO: Implement this
        pass
""")

    with open(os.path.join(temp_dir, 'tests', 'test_example.py'), 'w') as f:
        f.write("""# Test file
def test_function():
    # TODO: Add test
    assert True
""")

    yield temp_dir

    shutil.rmtree(temp_dir)


def test_search_code_basic(temp_repo):
    """Test basic pattern search"""
    result = search_code_tool(temp_repo, pattern="TODO", file_pattern="*.py")

    assert 'matches' in result
    assert 'total_matches' in result
    assert result['total_matches'] >= 2  # At least 2 TODO comments


def test_search_code_with_context(temp_repo):
    """Test search with context lines"""
    result = search_code_tool(temp_repo, pattern="TODO", file_pattern="*.py", context_lines=1)

    assert 'matches' in result
    # Check that context lines are included
    if result['matches']:
        match = result['matches'][0]
        assert 'context' in match or 'line' in match


def test_search_code_regex(temp_repo):
    """Test regex pattern search"""
    result = search_code_tool(temp_repo, pattern=r"def \w+\(", file_pattern="*.py")

    assert 'matches' in result
    assert result['total_matches'] >= 2  # my_method and test_function


def test_search_code_file_pattern(temp_repo):
    """Test file pattern filtering"""
    result = search_code_tool(temp_repo, pattern="TODO", file_pattern="test_*.py")

    assert 'matches' in result
    # Should only find matches in test files
    if result['matches']:
        assert all('test_' in match['file_path'] for match in result['matches'])


def test_path_traversal_blocked(temp_repo):
    """Test that path traversal attacks are blocked"""
    result = search_code_tool(temp_repo, pattern=".*", file_pattern="*.py", path="../../../etc")

    assert 'error' in result
    assert result['error'] == 'SecurityError'


def test_sensitive_directory_blocked_data(temp_repo):
    """Test that /data directory access is blocked"""
    # Create data directory with files
    os.makedirs(os.path.join(temp_repo, 'data'))
    with open(os.path.join(temp_repo, 'data', 'config.py'), 'w') as f:
        f.write('PASSWORD = "secret123"\n')

    result = search_code_tool(temp_repo, pattern="PASSWORD", file_pattern="*.py", path='data')

    assert 'error' in result
    assert result['error'] == 'AccessDenied'
    assert 'sensitive' in result['message'].lower()


def test_sensitive_directory_allowed_with_flag(temp_repo):
    """Test that sensitive directories can be searched with flag"""
    # Create data directory with files
    os.makedirs(os.path.join(temp_repo, 'data'))
    with open(os.path.join(temp_repo, 'data', 'config.py'), 'w') as f:
        f.write('PASSWORD = "secret123"\n')

    result = search_code_tool(temp_repo, pattern="PASSWORD", file_pattern="*.py", path='data', allow_sensitive=True)

    assert 'matches' in result
    assert result['total_matches'] >= 1
