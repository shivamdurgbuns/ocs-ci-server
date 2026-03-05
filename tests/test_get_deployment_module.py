"""
Tests for get_deployment_module tool

These tests verify the get_deployment_module tool correctly lists
deployment modules from ocs_ci/deployment/ directory.
"""

import os
import tempfile
from pathlib import Path
import pytest
from tools.get_deployment_module import get_deployment_module_tool
from analyzers.ast_analyzer import ASTAnalyzer


@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create ocs_ci/deployment directory
        deployment_dir = repo_path / "ocs_ci" / "deployment"
        deployment_dir.mkdir(parents=True)

        # Create test deployment modules
        (deployment_dir / "aws.py").write_text(
            '"""AWS deployment module"""\n'
            'def deploy_aws():\n'
            '    """Deploy OCS on AWS"""\n'
            '    pass\n'
        )

        (deployment_dir / "azure.py").write_text(
            '"""Azure deployment module"""\n'
            'def deploy_azure():\n'
            '    """Deploy OCS on Azure"""\n'
            '    pass\n'
        )

        (deployment_dir / "gcp.py").write_text(
            '"""GCP deployment module"""\n'
            'def deploy_gcp():\n'
            '    """Deploy OCS on GCP"""\n'
            '    pass\n'
        )

        # Create a subdirectory with a file (should not be included - not recursive)
        subdir = deployment_dir / "helpers"
        subdir.mkdir()
        (subdir / "common.py").write_text(
            '"""Common deployment helpers"""\n'
            'def common_helper():\n'
            '    pass\n'
        )

        yield str(repo_path)


@pytest.fixture
def analyzer():
    """Create an ASTAnalyzer instance."""
    return ASTAnalyzer()


def test_list_all_deployment_modules(temp_repo, analyzer):
    """Test listing all deployment modules."""
    result = get_deployment_module_tool(
        repo_path=temp_repo,
        analyzer=analyzer
    )

    assert result["directory"] == "ocs_ci/deployment"
    assert result["total_modules"] == 3
    assert result["filtered_modules"] == 3
    assert len(result["modules"]) == 3

    # Verify module names
    module_names = {m["name"] for m in result["modules"]}
    assert module_names == {"aws.py", "azure.py", "gcp.py"}

    # Verify each module has required fields
    for module in result["modules"]:
        assert "name" in module
        assert "path" in module
        assert "description" in module


def test_filter_by_pattern(temp_repo, analyzer):
    """Test filtering deployment modules by pattern."""
    result = get_deployment_module_tool(
        repo_path=temp_repo,
        pattern="*aws*",
        analyzer=analyzer
    )

    assert result["directory"] == "ocs_ci/deployment"
    assert result["total_modules"] == 3
    assert result["filtered_modules"] == 1
    assert len(result["modules"]) == 1
    assert result["modules"][0]["name"] == "aws.py"


def test_filter_by_search_text(temp_repo, analyzer):
    """Test filtering deployment modules by search text in descriptions."""
    result = get_deployment_module_tool(
        repo_path=temp_repo,
        search_text="Azure",
        analyzer=analyzer
    )

    assert result["directory"] == "ocs_ci/deployment"
    assert result["total_modules"] == 3
    assert result["filtered_modules"] == 1
    assert len(result["modules"]) == 1
    assert result["modules"][0]["name"] == "azure.py"


def test_not_recursive(temp_repo, analyzer):
    """Test that subdirectories are not included (recursive=False)."""
    result = get_deployment_module_tool(
        repo_path=temp_repo,
        analyzer=analyzer
    )

    # Should only find 3 modules in deployment/, not the one in helpers/
    assert result["total_modules"] == 3
    module_names = {m["name"] for m in result["modules"]}
    assert "common.py" not in module_names


def test_security_validation(temp_repo, analyzer):
    """Test that security validation is applied."""
    # The discover_modules function should validate paths
    # This test ensures the wrapper passes through security settings
    result = get_deployment_module_tool(
        repo_path=temp_repo,
        analyzer=analyzer,
        allow_sensitive=False
    )

    # Should succeed since deployment/ is not a sensitive directory
    assert result["total_modules"] == 3


def test_invalid_repo_path(analyzer):
    """Test handling of invalid repository path."""
    result = get_deployment_module_tool(
        repo_path="/nonexistent/path",
        analyzer=analyzer
    )

    assert 'error' in result
    assert result['error'] == 'PathNotFound'


def test_missing_deployment_directory(analyzer):
    """Test handling when deployment directory doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create ocs_ci but not deployment subdirectory
        (repo_path / "ocs_ci").mkdir()

        result = get_deployment_module_tool(
            repo_path=str(repo_path),
            analyzer=analyzer
        )

        assert 'error' in result
        assert result['error'] == 'PathNotFound'


def test_combined_filters(temp_repo, analyzer):
    """Test combining pattern and search_text filters."""
    # Add a module that matches pattern but not search text
    deployment_dir = Path(temp_repo) / "ocs_ci" / "deployment"
    (deployment_dir / "aws_helpers.py").write_text(
        '"""Helper functions for something else"""\n'
        'def helper():\n'
        '    pass\n'
    )

    result = get_deployment_module_tool(
        repo_path=temp_repo,
        pattern="*aws*",
        search_text="AWS deployment",
        analyzer=analyzer
    )

    # Should only find aws.py (matches both pattern and search text)
    # aws_helpers.py matches pattern but not search text
    assert result["filtered_modules"] == 1
    assert result["modules"][0]["name"] == "aws.py"
