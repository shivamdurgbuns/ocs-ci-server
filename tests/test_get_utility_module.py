"""
Tests for get_utility_module tool

These tests verify the get_utility_module tool correctly lists
utility modules from ocs_ci/utility/ directory.
"""

import os
import tempfile
from pathlib import Path
import pytest
from tools.get_utility_module import get_utility_module_tool
from analyzers.ast_analyzer import ASTAnalyzer


@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create ocs_ci/utility directory
        utility_dir = repo_path / "ocs_ci" / "utility"
        utility_dir.mkdir(parents=True)

        # Create test utility modules
        (utility_dir / "utils.py").write_text(
            '"""General utilities"""\n'
            'def utility_function():\n'
            '    """Utility function"""\n'
            '    pass\n'
        )

        (utility_dir / "templating.py").write_text(
            '"""Template processing utilities"""\n'
            'def process_template():\n'
            '    """Process templates"""\n'
            '    pass\n'
        )

        (utility_dir / "retry.py").write_text(
            '"""Retry utilities"""\n'
            'def retry_operation():\n'
            '    """Retry failed operations"""\n'
            '    pass\n'
        )

        # Create a subdirectory with a file (should not be included - not recursive)
        subdir = utility_dir / "aws"
        subdir.mkdir()
        (subdir / "utils.py").write_text(
            '"""AWS utilities"""\n'
            'def aws_util():\n'
            '    pass\n'
        )

        yield str(repo_path)


@pytest.fixture
def analyzer():
    """Create an ASTAnalyzer instance."""
    return ASTAnalyzer()


def test_list_all_utility_modules(temp_repo, analyzer):
    """Test listing all utility modules."""
    result = get_utility_module_tool(
        repo_path=temp_repo,
        analyzer=analyzer
    )

    assert result["directory"] == "ocs_ci/utility"
    assert result["total_modules"] == 3
    assert result["filtered_modules"] == 3
    assert len(result["modules"]) == 3

    # Verify module names
    module_names = {m["name"] for m in result["modules"]}
    assert module_names == {"utils.py", "templating.py", "retry.py"}

    # Verify each module has required fields
    for module in result["modules"]:
        assert "name" in module
        assert "path" in module
        assert "description" in module


def test_filter_by_pattern(temp_repo, analyzer):
    """Test filtering utility modules by pattern."""
    result = get_utility_module_tool(
        repo_path=temp_repo,
        pattern="*retry*",
        analyzer=analyzer
    )

    assert result["directory"] == "ocs_ci/utility"
    assert result["total_modules"] == 3
    assert result["filtered_modules"] == 1
    assert len(result["modules"]) == 1
    assert result["modules"][0]["name"] == "retry.py"


def test_security_validation(temp_repo, analyzer):
    """Test that security validation is applied."""
    result = get_utility_module_tool(
        repo_path=temp_repo,
        analyzer=analyzer,
        allow_sensitive=False
    )

    # Should succeed since ocs_ci/utility/ is not a sensitive directory
    assert result["total_modules"] == 3
