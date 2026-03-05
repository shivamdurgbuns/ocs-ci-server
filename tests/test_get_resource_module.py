"""
Tests for get_resource_module tool

These tests verify the get_resource_module tool correctly lists
resource modules from ocs_ci/ocs/resources/ directory.
"""

import os
import tempfile
from pathlib import Path
import pytest
from tools.get_resource_module import get_resource_module_tool
from analyzers.ast_analyzer import ASTAnalyzer


@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create ocs_ci/ocs/resources directory
        resources_dir = repo_path / "ocs_ci" / "ocs" / "resources"
        resources_dir.mkdir(parents=True)

        # Create test resource modules
        (resources_dir / "pvc.py").write_text(
            '"""PVC resource module"""\n'
            'class PVC:\n'
            '    """Persistent Volume Claim resource"""\n'
            '    pass\n'
        )

        (resources_dir / "pod.py").write_text(
            '"""Pod resource module"""\n'
            'class Pod:\n'
            '    """Kubernetes Pod resource"""\n'
            '    pass\n'
        )

        (resources_dir / "storage_cluster.py").write_text(
            '"""Storage Cluster resource module"""\n'
            'class StorageCluster:\n'
            '    """OCS Storage Cluster"""\n'
            '    pass\n'
        )

        # Create a subdirectory with a file (should not be included - not recursive)
        subdir = resources_dir / "utils"
        subdir.mkdir()
        (subdir / "helpers.py").write_text(
            '"""Resource helpers"""\n'
            'def helper():\n'
            '    pass\n'
        )

        yield str(repo_path)


@pytest.fixture
def analyzer():
    """Create an ASTAnalyzer instance."""
    return ASTAnalyzer()


def test_list_all_resource_modules(temp_repo, analyzer):
    """Test listing all resource modules."""
    result = get_resource_module_tool(
        repo_path=temp_repo,
        analyzer=analyzer
    )

    assert result["directory"] == "ocs_ci/ocs/resources"
    assert result["total_modules"] == 3
    assert result["filtered_modules"] == 3
    assert len(result["modules"]) == 3

    # Verify module names
    module_names = {m["name"] for m in result["modules"]}
    assert module_names == {"pvc.py", "pod.py", "storage_cluster.py"}

    # Verify each module has required fields
    for module in result["modules"]:
        assert "name" in module
        assert "path" in module
        assert "description" in module


def test_filter_by_pattern(temp_repo, analyzer):
    """Test filtering resource modules by pattern."""
    result = get_resource_module_tool(
        repo_path=temp_repo,
        pattern="*pvc*",
        analyzer=analyzer
    )

    assert result["directory"] == "ocs_ci/ocs/resources"
    assert result["total_modules"] == 3
    assert result["filtered_modules"] == 1
    assert len(result["modules"]) == 1
    assert result["modules"][0]["name"] == "pvc.py"


def test_security_validation(temp_repo, analyzer):
    """Test that security validation is applied."""
    result = get_resource_module_tool(
        repo_path=temp_repo,
        analyzer=analyzer,
        allow_sensitive=False
    )

    # Should succeed since ocs_ci/ocs/resources/ is not a sensitive directory
    assert result["total_modules"] == 3
