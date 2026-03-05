"""Tests for module_discovery helper functions."""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from analyzers.ast_analyzer import ASTAnalyzer
from tools.module_discovery import discover_modules, extract_description, extract_config_description


@pytest.fixture
def temp_repo():
    """Create a temporary fake repository."""
    temp_dir = tempfile.mkdtemp()

    # Create structure
    os.makedirs(os.path.join(temp_dir, 'ocs_ci', 'framework'))
    os.makedirs(os.path.join(temp_dir, 'tests'))
    os.makedirs(os.path.join(temp_dir, 'conf'))
    os.makedirs(os.path.join(temp_dir, '__pycache__'))  # Should be skipped
    os.makedirs(os.path.join(temp_dir, '.hidden'))  # Should be skipped

    # Create Python files with docstrings
    with open(os.path.join(temp_dir, 'ocs_ci', 'framework', 'pytest_customization.py'), 'w') as f:
        f.write('"""\nPytest customization module.\nProvides custom pytest hooks.\n"""\n\nclass Custom:\n    pass\n')

    with open(os.path.join(temp_dir, 'ocs_ci', 'framework', 'helpers.py'), 'w') as f:
        f.write('"""Helper utilities for testing."""\n\ndef helper():\n    pass\n')

    with open(os.path.join(temp_dir, 'ocs_ci', 'framework', 'no_docstring.py'), 'w') as f:
        f.write('# No docstring here\n\nclass Test:\n    pass\n')

    # Create config file with comment
    with open(os.path.join(temp_dir, 'conf', 'ocsci.conf'), 'w') as f:
        f.write('# Main configuration file for OCS-CI\n# Second line\nkey=value\n')

    # Create config file without comment
    with open(os.path.join(temp_dir, 'conf', 'minimal.conf'), 'w') as f:
        f.write('key=value\n')

    # Create file in __pycache__ (should be skipped)
    with open(os.path.join(temp_dir, '__pycache__', 'test.pyc'), 'w') as f:
        f.write('bytecode')

    # Create file in .hidden (should be skipped)
    with open(os.path.join(temp_dir, '.hidden', 'secret.py'), 'w') as f:
        f.write('secret_data = "hidden"')

    yield temp_dir

    shutil.rmtree(temp_dir)


def test_discover_modules_basic(temp_repo):
    """Test basic module discovery."""
    analyzer = ASTAnalyzer()
    result = discover_modules(
        repo_path=temp_repo,
        target_dir='ocs_ci/framework',
        analyzer=analyzer
    )

    assert result['directory'] == 'ocs_ci/framework'
    assert result['total_modules'] == 3
    assert result['filtered_modules'] == 3
    assert len(result['modules']) == 3

    # Check module structure
    module_names = [m['name'] for m in result['modules']]
    assert 'helpers.py' in module_names
    assert 'no_docstring.py' in module_names
    assert 'pytest_customization.py' in module_names

    # Check descriptions
    helpers = next(m for m in result['modules'] if m['name'] == 'helpers.py')
    assert helpers['description'] == 'Helper utilities for testing.'
    assert helpers['path'] == 'ocs_ci/framework/helpers.py'
    assert helpers['size_bytes'] > 0
    assert helpers['lines'] > 0

    pytest_custom = next(m for m in result['modules'] if m['name'] == 'pytest_customization.py')
    assert pytest_custom['description'] == 'Pytest customization module.'

    no_doc = next(m for m in result['modules'] if m['name'] == 'no_docstring.py')
    assert no_doc['description'] == 'No description available'


def test_discover_modules_pattern_filter(temp_repo):
    """Test pattern filtering."""
    analyzer = ASTAnalyzer()
    result = discover_modules(
        repo_path=temp_repo,
        target_dir='ocs_ci/framework',
        pattern='helper*',
        analyzer=analyzer
    )

    assert result['total_modules'] == 3
    assert result['filtered_modules'] == 1
    assert len(result['modules']) == 1
    assert result['modules'][0]['name'] == 'helpers.py'


def test_discover_modules_search_filter(temp_repo):
    """Test search text filtering."""
    analyzer = ASTAnalyzer()
    result = discover_modules(
        repo_path=temp_repo,
        target_dir='ocs_ci/framework',
        search_text='pytest',
        analyzer=analyzer
    )

    assert result['total_modules'] == 3
    assert result['filtered_modules'] == 1
    assert len(result['modules']) == 1
    assert result['modules'][0]['name'] == 'pytest_customization.py'


def test_discover_modules_combined_filters(temp_repo):
    """Test combining pattern and search filters."""
    analyzer = ASTAnalyzer()
    result = discover_modules(
        repo_path=temp_repo,
        target_dir='ocs_ci/framework',
        pattern='*.py',
        search_text='helper',
        analyzer=analyzer
    )

    assert result['total_modules'] == 3
    assert result['filtered_modules'] == 1
    assert result['modules'][0]['name'] == 'helpers.py'


def test_discover_modules_recursive(temp_repo):
    """Test recursive discovery."""
    analyzer = ASTAnalyzer()
    result = discover_modules(
        repo_path=temp_repo,
        target_dir='ocs_ci',
        recursive=True,
        analyzer=analyzer
    )

    # Should find all .py files under ocs_ci recursively
    assert result['total_modules'] == 3
    assert result['filtered_modules'] == 3


def test_discover_modules_skips_hidden(temp_repo):
    """Test that hidden files and __pycache__ are skipped."""
    analyzer = ASTAnalyzer()
    result = discover_modules(
        repo_path=temp_repo,
        target_dir='.',
        recursive=True,
        analyzer=analyzer
    )

    # Should not find files in .hidden or __pycache__
    paths = [m['path'] for m in result['modules']]
    assert not any('.hidden' in p for p in paths)
    assert not any('__pycache__' in p for p in paths)


def test_discover_modules_sorted(temp_repo):
    """Test that modules are sorted by name."""
    analyzer = ASTAnalyzer()
    result = discover_modules(
        repo_path=temp_repo,
        target_dir='ocs_ci/framework',
        analyzer=analyzer
    )

    names = [m['name'] for m in result['modules']]
    assert names == sorted(names)


def test_discover_modules_security_validation(temp_repo):
    """Test security validation."""
    analyzer = ASTAnalyzer()
    result = discover_modules(
        repo_path=temp_repo,
        target_dir='../../../etc',
        analyzer=analyzer
    )

    assert 'error' in result
    assert result['error'] == 'SecurityError'


def test_discover_modules_sensitive_directory(temp_repo):
    """Test sensitive directory blocking."""
    # Create data directory
    os.makedirs(os.path.join(temp_repo, 'data'))
    with open(os.path.join(temp_repo, 'data', 'secrets.py'), 'w') as f:
        f.write('password = "secret"')

    analyzer = ASTAnalyzer()
    result = discover_modules(
        repo_path=temp_repo,
        target_dir='data',
        analyzer=analyzer
    )

    assert 'error' in result
    assert result['error'] == 'AccessDenied'


def test_discover_modules_sensitive_allowed(temp_repo):
    """Test allowing access to sensitive directories."""
    # Create data directory
    os.makedirs(os.path.join(temp_repo, 'data'))
    with open(os.path.join(temp_repo, 'data', 'test.py'), 'w') as f:
        f.write('"""Test module."""\ndata = 1')

    analyzer = ASTAnalyzer()
    result = discover_modules(
        repo_path=temp_repo,
        target_dir='data',
        analyzer=analyzer,
        allow_sensitive=True
    )

    assert 'modules' in result
    assert len(result['modules']) == 1


def test_discover_modules_config_files(temp_repo):
    """Test discovering config files."""
    result = discover_modules(
        repo_path=temp_repo,
        target_dir='conf',
        file_extension='.conf'
    )

    assert result['total_modules'] == 2
    assert result['filtered_modules'] == 2

    # Check descriptions
    ocsci = next(m for m in result['modules'] if m['name'] == 'ocsci.conf')
    assert ocsci['description'] == 'Main configuration file for OCS-CI'

    minimal = next(m for m in result['modules'] if m['name'] == 'minimal.conf')
    assert minimal['description'] == 'Configuration file'


def test_discover_modules_permission_error(temp_repo):
    """Test handling permission errors."""
    # Create a directory and make it unreadable
    restricted_dir = os.path.join(temp_repo, 'restricted')
    os.makedirs(restricted_dir)
    os.chmod(restricted_dir, 0o000)

    try:
        result = discover_modules(
            repo_path=temp_repo,
            target_dir='restricted'
        )

        # Should handle gracefully
        assert 'error' in result or 'modules' in result
    finally:
        # Restore permissions for cleanup
        os.chmod(restricted_dir, 0o755)


def test_extract_description_with_docstring(temp_repo):
    """Test extracting description from Python file with docstring."""
    analyzer = ASTAnalyzer()
    file_path = os.path.join(temp_repo, 'ocs_ci', 'framework', 'helpers.py')

    description = extract_description(file_path, analyzer)
    assert description == 'Helper utilities for testing.'


def test_extract_description_multiline_docstring(temp_repo):
    """Test extracting first line from multiline docstring."""
    analyzer = ASTAnalyzer()
    file_path = os.path.join(temp_repo, 'ocs_ci', 'framework', 'pytest_customization.py')

    description = extract_description(file_path, analyzer)
    assert description == 'Pytest customization module.'


def test_extract_description_no_docstring(temp_repo):
    """Test fallback when no docstring exists."""
    analyzer = ASTAnalyzer()
    file_path = os.path.join(temp_repo, 'ocs_ci', 'framework', 'no_docstring.py')

    description = extract_description(file_path, analyzer)
    assert description == 'No description available'


def test_extract_description_truncation(temp_repo):
    """Test description truncation to 200 chars."""
    # Create file with very long docstring
    long_file = os.path.join(temp_repo, 'long_desc.py')
    with open(long_file, 'w') as f:
        f.write('"""' + 'A' * 250 + '"""\n')

    analyzer = ASTAnalyzer()
    description = extract_description(long_file, analyzer)
    assert len(description) == 200


def test_extract_config_description_with_comment(temp_repo):
    """Test extracting description from config file with comment."""
    file_path = os.path.join(temp_repo, 'conf', 'ocsci.conf')

    description = extract_config_description(file_path)
    assert description == 'Main configuration file for OCS-CI'


def test_extract_config_description_no_comment(temp_repo):
    """Test fallback when config file has no comment."""
    file_path = os.path.join(temp_repo, 'conf', 'minimal.conf')

    description = extract_config_description(file_path)
    assert description == 'Configuration file'


def test_extract_config_description_truncation(temp_repo):
    """Test config description truncation to 200 chars."""
    # Create config file with very long comment
    long_file = os.path.join(temp_repo, 'long_config.conf')
    with open(long_file, 'w') as f:
        f.write('# ' + 'B' * 250 + '\n')

    description = extract_config_description(long_file)
    assert len(description) == 200
