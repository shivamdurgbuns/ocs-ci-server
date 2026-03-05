import pytest
import tempfile
import os
import shutil
from tools.get_test_example import get_test_example_tool


@pytest.fixture
def temp_repo():
    """Create a temporary fake repository with test files"""
    temp_dir = tempfile.mkdtemp()

    # Create structure
    os.makedirs(os.path.join(temp_dir, 'tests'))

    # Create test file 1
    with open(os.path.join(temp_dir, 'tests', 'test_pod.py'), 'w') as f:
        f.write("""# Pod tests
import pytest

@pytest.fixture
def pod_factory():
    return "factory"

def test_pod_creation(pod_factory):
    # Test creating a pod
    assert pod_factory

def test_pod_deletion():
    # Test deleting a pod
    pass
""")

    # Create test file 2
    with open(os.path.join(temp_dir, 'tests', 'test_pvc.py'), 'w') as f:
        f.write("""# PVC tests
import pytest

@pytest.fixture
def pvc_factory():
    return "pvc"

def test_pvc_creation(pvc_factory):
    # Test creating a PVC
    assert pvc_factory

def test_volume_attach():
    # Test attaching volume
    pass
""")

    yield temp_dir

    shutil.rmtree(temp_dir)


def test_get_test_example_by_pattern(temp_repo):
    """Test finding tests by pattern"""
    result = get_test_example_tool(temp_repo, pattern="pod")

    assert 'examples' in result
    assert len(result['examples']) > 0
    # Should find tests with "pod" in name or content
    assert any('pod' in ex['test_name'].lower() for ex in result['examples'])


def test_get_test_example_by_fixture(temp_repo):
    """Test finding tests by fixture name"""
    result = get_test_example_tool(temp_repo, pattern="", fixture_name="pod_factory")

    assert 'examples' in result
    # Should find test_pod_creation which uses pod_factory
    if result['examples']:
        assert any('pod_creation' in ex['test_name'] for ex in result['examples'])


def test_get_test_example_with_source(temp_repo):
    """Test that examples include source code"""
    result = get_test_example_tool(temp_repo, pattern="creation")

    assert 'examples' in result
    if result['examples']:
        example = result['examples'][0]
        assert 'source' in example
        assert 'def test_' in example['source']


def test_get_test_example_limit(temp_repo):
    """Test that results are limited"""
    result = get_test_example_tool(temp_repo, pattern="test", max_results=1)

    assert 'examples' in result
    assert len(result['examples']) <= 1


def test_path_traversal_blocked(temp_repo):
    """Test that path traversal attacks are blocked"""
    result = get_test_example_tool(temp_repo, pattern="test", path="../../../etc")

    assert 'error' in result
    assert result['error'] == 'SecurityError'


def test_sensitive_directory_blocked_data(temp_repo):
    """Test that /data directory access is blocked"""
    # Create data directory with test file
    os.makedirs(os.path.join(temp_repo, 'data'))
    with open(os.path.join(temp_repo, 'data', 'test_secrets.py'), 'w') as f:
        f.write('def test_secret():\n    pass\n')

    result = get_test_example_tool(temp_repo, pattern='test', path='data')

    assert 'error' in result
    assert result['error'] == 'AccessDenied'
    assert 'sensitive' in result['message'].lower()


def test_sensitive_directory_allowed_with_flag(temp_repo):
    """Test that sensitive directories can be searched with flag"""
    # Create data directory with test file
    os.makedirs(os.path.join(temp_repo, 'data'))
    with open(os.path.join(temp_repo, 'data', 'test_config.py'), 'w') as f:
        f.write('def test_config():\n    pass\n')

    result = get_test_example_tool(temp_repo, pattern='test', path='data', allow_sensitive=True)

    assert 'examples' in result
    assert len(result['examples']) >= 1
