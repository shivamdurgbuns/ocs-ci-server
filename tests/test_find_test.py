import pytest
import tempfile
import os
import shutil
from tools.find_test import find_test_tool


@pytest.fixture
def temp_repo():
    """Create a temporary fake repository with test files"""
    temp_dir = tempfile.mkdtemp()

    # Create structure
    os.makedirs(os.path.join(temp_dir, 'tests'))

    # Create test file
    with open(os.path.join(temp_dir, 'tests', 'test_example.py'), 'w') as f:
        f.write("""# Test module
import pytest

@pytest.fixture
def my_fixture():
    return "data"

def test_simple():
    assert True

def test_with_fixture(my_fixture):
    assert my_fixture == "data"

class TestClass:
    def test_method(self):
        pass
""")

    yield temp_dir

    shutil.rmtree(temp_dir)


def test_find_test_by_name(temp_repo):
    """Test finding test by function name"""
    result = find_test_tool(temp_repo, test_name="test_simple")

    assert 'file_path' in result
    assert 'line_number' in result
    assert 'test_example.py' in result['file_path']


def test_find_test_by_nodeid(temp_repo):
    """Test finding test by pytest nodeid"""
    result = find_test_tool(temp_repo, test_name="tests/test_example.py::test_simple")

    assert 'file_path' in result
    assert 'line_number' in result
    assert result['line_number'] > 0


def test_find_test_class_method(temp_repo):
    """Test finding test method in class"""
    result = find_test_tool(temp_repo, test_name="tests/test_example.py::TestClass::test_method")

    assert 'file_path' in result
    assert 'line_number' in result


def test_find_test_with_fixtures(temp_repo):
    """Test extracting fixtures used by test"""
    result = find_test_tool(temp_repo, test_name="test_with_fixture")

    assert 'fixtures' in result
    assert 'my_fixture' in result['fixtures']


def test_find_test_not_found(temp_repo):
    """Test error handling for missing test"""
    result = find_test_tool(temp_repo, test_name="test_nonexistent")

    assert 'error' in result
    assert result['error'] == 'TestNotFound'


def test_path_traversal_blocked(temp_repo):
    """Test that path traversal attacks are blocked"""
    result = find_test_tool(temp_repo, test_name="../../../etc/passwd::test")

    assert 'error' in result
    assert result['error'] == 'SecurityError'


def test_sensitive_directory_blocked_data(temp_repo):
    """Test that /data directory access is blocked"""
    # Create data directory with test file
    os.makedirs(os.path.join(temp_repo, 'data'))
    with open(os.path.join(temp_repo, 'data', 'test_secrets.py'), 'w') as f:
        f.write('def test_secret():\n    pass\n')

    result = find_test_tool(temp_repo, test_name='data/test_secrets.py::test_secret')

    assert 'error' in result
    assert result['error'] == 'AccessDenied'
    assert 'sensitive' in result['message'].lower()


def test_sensitive_directory_allowed_with_flag(temp_repo):
    """Test that sensitive directories can be accessed with flag"""
    # Create data directory with test file
    os.makedirs(os.path.join(temp_repo, 'data'))
    with open(os.path.join(temp_repo, 'data', 'test_config.py'), 'w') as f:
        f.write('def test_config():\n    pass\n')

    result = find_test_tool(temp_repo, test_name='data/test_config.py::test_config', allow_sensitive=True)

    assert 'file_path' in result
    assert 'line_number' in result
