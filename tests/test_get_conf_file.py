"""
Tests for get_conf_file tool

These tests verify the get_conf_file tool correctly lists
configuration files from conf/ directory.
"""

import os
import tempfile
from pathlib import Path
import pytest
from tools.get_conf_file import get_conf_file_tool


@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create conf directory
        conf_dir = repo_path / "conf"
        conf_dir.mkdir(parents=True)

        # Create test config files (various types)
        (conf_dir / "ocsci_config.yaml").write_text(
            'cluster:\n'
            '  name: test-cluster\n'
        )

        (conf_dir / "deployment.yaml").write_text(
            'platform: aws\n'
            'region: us-east-1\n'
        )

        (conf_dir / "test_config.json").write_text(
            '{"test": "config"}\n'
        )

        (conf_dir / "defaults.ini").write_text(
            '[defaults]\n'
            'timeout=300\n'
        )

        # Create a subdirectory with a file (should not be included - not recursive)
        subdir = conf_dir / "templates"
        subdir.mkdir()
        (subdir / "template.yaml").write_text(
            'template: data\n'
        )

        yield str(repo_path)


def test_list_all_conf_files(temp_repo):
    """Test listing all config files."""
    result = get_conf_file_tool(
        repo_path=temp_repo
    )

    assert result["directory"] == "conf"
    assert result["total_modules"] == 4
    assert result["filtered_modules"] == 4
    assert len(result["modules"]) == 4

    # Verify file names
    file_names = {m["name"] for m in result["modules"]}
    assert file_names == {"ocsci_config.yaml", "deployment.yaml", "test_config.json", "defaults.ini"}

    # Verify each file has required fields (but no description since no analyzer)
    for file in result["modules"]:
        assert "name" in file
        assert "path" in file


def test_filter_by_pattern(temp_repo):
    """Test filtering config files by pattern."""
    result = get_conf_file_tool(
        repo_path=temp_repo,
        pattern="*.yaml"
    )

    assert result["directory"] == "conf"
    assert result["total_modules"] == 4
    assert result["filtered_modules"] == 2
    assert len(result["modules"]) == 2

    # Verify YAML files
    file_names = {m["name"] for m in result["modules"]}
    assert file_names == {"ocsci_config.yaml", "deployment.yaml"}


def test_security_validation(temp_repo):
    """Test that security validation is applied."""
    result = get_conf_file_tool(
        repo_path=temp_repo,
        allow_sensitive=False
    )

    # Should succeed since conf/ is not a sensitive directory
    assert result["total_modules"] == 4
