"""
Tests for get_helper_module tool

These tests verify the get_helper_module tool correctly lists
helper modules from ocs_ci/helpers/ directory.
"""

import os
import tempfile
from pathlib import Path
import pytest
from tools.get_helper_module import get_helper_module_tool
from analyzers.ast_analyzer import ASTAnalyzer


@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create ocs_ci/helpers directory
        helpers_dir = repo_path / "ocs_ci" / "helpers"
        helpers_dir.mkdir(parents=True)

        # Create test helper modules
        (helpers_dir / "helpers.py").write_text(
            '"""General helper functions"""\n'
            'def general_helper():\n'
            '    """General purpose helper"""\n'
            '    pass\n'
        )

        (helpers_dir / "performance_lib.py").write_text(
            '"""Performance testing library"""\n'
            'def benchmark():\n'
            '    """Run performance benchmark"""\n'
            '    pass\n'
        )

        (helpers_dir / "disruption_helpers.py").write_text(
            '"""Disruption testing helpers"""\n'
            'def disrupt():\n'
            '    """Cause disruption for testing"""\n'
            '    pass\n'
        )

        # Create a subdirectory with a file (should not be included - not recursive)
        subdir = helpers_dir / "internal"
        subdir.mkdir()
        (subdir / "utils.py").write_text(
            '"""Internal utilities"""\n'
            'def util():\n'
            '    pass\n'
        )

        yield str(repo_path)


@pytest.fixture
def analyzer():
    """Create an ASTAnalyzer instance."""
    return ASTAnalyzer()


def test_list_all_helper_modules(temp_repo, analyzer):
    """Test listing all helper modules."""
    result = get_helper_module_tool(
        repo_path=temp_repo,
        analyzer=analyzer
    )

    assert result["directory"] == "ocs_ci/helpers"
    assert result["total_modules"] == 3
    assert result["filtered_modules"] == 3
    assert len(result["modules"]) == 3

    # Verify module names
    module_names = {m["name"] for m in result["modules"]}
    assert module_names == {"helpers.py", "performance_lib.py", "disruption_helpers.py"}

    # Verify each module has required fields
    for module in result["modules"]:
        assert "name" in module
        assert "path" in module
        assert "description" in module


def test_filter_by_pattern(temp_repo, analyzer):
    """Test filtering helper modules by pattern."""
    result = get_helper_module_tool(
        repo_path=temp_repo,
        pattern="*performance*",
        analyzer=analyzer
    )

    assert result["directory"] == "ocs_ci/helpers"
    assert result["total_modules"] == 3
    assert result["filtered_modules"] == 1
    assert len(result["modules"]) == 1
    assert result["modules"][0]["name"] == "performance_lib.py"


def test_security_validation(temp_repo, analyzer):
    """Test that security validation is applied."""
    result = get_helper_module_tool(
        repo_path=temp_repo,
        analyzer=analyzer,
        allow_sensitive=False
    )

    # Should succeed since ocs_ci/helpers/ is not a sensitive directory
    assert result["total_modules"] == 3
