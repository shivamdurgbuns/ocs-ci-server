"""
Tests for get_conftest tool

These tests verify the get_conftest tool correctly lists
conftest.py files from tests/ directory tree (recursive).
"""

import os
import tempfile
from pathlib import Path
import pytest
from tools.get_conftest import get_conftest_tool
from analyzers.ast_analyzer import ASTAnalyzer


@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create tests directory with conftest.py files at various levels
        tests_dir = repo_path / "tests"
        tests_dir.mkdir(parents=True)

        # Root level conftest.py
        (tests_dir / "conftest.py").write_text(
            '"""Root conftest"""\n'
            'import pytest\n'
        )

        # Functional tests subdirectory
        functional_dir = tests_dir / "functional"
        functional_dir.mkdir()
        (functional_dir / "conftest.py").write_text(
            '"""Functional test conftest"""\n'
            'import pytest\n'
        )

        # E2E tests subdirectory
        e2e_dir = tests_dir / "e2e"
        e2e_dir.mkdir()
        (e2e_dir / "conftest.py").write_text(
            '"""E2E test conftest"""\n'
            'import pytest\n'
        )

        # Nested conftest in functional/aws
        functional_aws = functional_dir / "aws"
        functional_aws.mkdir()
        (functional_aws / "conftest.py").write_text(
            '"""AWS functional test conftest"""\n'
            'import pytest\n'
        )

        # Create some non-conftest files (should not be included)
        (tests_dir / "test_example.py").write_text(
            '"""Example test"""\n'
            'def test_example():\n'
            '    pass\n'
        )

        yield str(repo_path)


@pytest.fixture
def analyzer():
    """Create an ASTAnalyzer instance."""
    return ASTAnalyzer()


def test_list_all_conftest_files(temp_repo, analyzer):
    """Test listing all conftest.py files recursively."""
    result = get_conftest_tool(
        repo_path=temp_repo,
        analyzer=analyzer
    )

    assert result["directory"] == "tests"
    # total_modules is 5 (all .py files), filtered_modules is 4 (conftest.py files only)
    assert result["total_modules"] == 5
    assert result["filtered_modules"] == 4
    assert len(result["modules"]) == 4

    # Verify all files are named conftest.py
    assert all(m["name"] == "conftest.py" for m in result["modules"])

    # Verify paths contain the expected subdirectories
    paths = {m["path"] for m in result["modules"]}
    assert any("tests/conftest.py" in p for p in paths)
    assert any("tests/functional/conftest.py" in p for p in paths)
    assert any("tests/e2e/conftest.py" in p for p in paths)
    assert any("tests/functional/aws/conftest.py" in p for p in paths)


def test_filter_by_path_pattern(temp_repo, analyzer):
    """Test filtering conftest.py files by path pattern."""
    result = get_conftest_tool(
        repo_path=temp_repo,
        pattern="*functional*",
        analyzer=analyzer
    )

    assert result["directory"] == "tests"
    # total_modules is 5 (all .py files), filtered by name to 4, then by path to 2
    assert result["total_modules"] == 5
    assert result["filtered_modules"] == 2  # functional/ and functional/aws/
    assert len(result["modules"]) == 2

    # Verify all filtered paths contain 'functional'
    for module in result["modules"]:
        assert "functional" in module["path"]


def test_security_validation(temp_repo, analyzer):
    """Test that security validation is applied."""
    result = get_conftest_tool(
        repo_path=temp_repo,
        analyzer=analyzer,
        allow_sensitive=False
    )

    # Should succeed since tests/ is not a sensitive directory
    # total_modules is 5 (all .py files)
    assert result["total_modules"] == 5
