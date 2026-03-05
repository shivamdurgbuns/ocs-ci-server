"""
Integration tests for ocs-ci MCP server against real ocs-ci repository.

These tests validate the entire system against the actual ocs-ci codebase.
Set OCS_CI_REPO_PATH to the path of a local ocs-ci clone to run them:

    export OCS_CI_REPO_PATH=/path/to/ocs-ci
    pytest tests/test_integration.py -v -m integration
"""

import os
import pytest
import time
from pathlib import Path
from server import OCCIMCPServer
from tools.list_modules import list_modules_tool
from tools.get_summary import get_summary_tool
from tools.get_content import get_content_tool
from tools.search_code import search_code_tool
from tools.get_inheritance import get_inheritance_tool
from tools.find_test import find_test_tool
from tools.get_test_example import get_test_example_tool
from tools.get_deployment_module import get_deployment_module_tool
from tools.get_resource_module import get_resource_module_tool
from tools.get_helper_module import get_helper_module_tool
from tools.get_utility_module import get_utility_module_tool
from tools.get_conftest import get_conftest_tool
from tools.get_conf_file import get_conf_file_tool


def _get_real_repo_path():
    """Resolve real ocs-ci repo path from environment; None if not set or invalid."""
    path = os.environ.get("OCS_CI_REPO_PATH")
    if not path or not path.strip():
        return None
    resolved = Path(path.strip()).resolve()
    return str(resolved) if resolved.exists() and resolved.is_dir() else None


@pytest.fixture
def real_repo_path():
    """Path to real ocs-ci repository; skips integration tests if not configured."""
    path = _get_real_repo_path()
    if path is None:
        pytest.skip(
            "Set OCS_CI_REPO_PATH to the path of an ocs-ci clone to run integration tests"
        )
    return path


@pytest.fixture
def real_server(real_repo_path):
    """Create server instance pointing to real ocs-ci repository"""
    return OCCIMCPServer(repo_path=real_repo_path)


@pytest.fixture
def real_server_with_sensitive(real_repo_path):
    """Create server instance with sensitive directory access enabled"""
    return OCCIMCPServer(repo_path=real_repo_path, allow_sensitive=True)


# ============================================================================
# Test 1: Real Pod Class Analysis
# ============================================================================

@pytest.mark.integration
def test_analyze_real_pod_class(real_server):
    """Test analyzing the real Pod class from ocs-ci"""
    result = get_summary_tool(
        repo_path=real_server.repo_path,
        file_path="ocs_ci/ocs/resources/pod.py",
        class_name="Pod",
        analyzer=real_server.analyzer,
        resolver=real_server.resolver,
        summarizer=real_server.summarizer
    )

    # Verify results
    assert 'class_name' in result
    assert result['class_name'] == 'Pod'
    assert 'own_methods' in result
    assert 'inherited_methods' in result

    # Pod inherits from OCP
    assert 'parent_classes' in result
    assert len(result['parent_classes']) > 0

    # Verify Pod has its own methods
    assert len(result['own_methods']) > 0

    # Verify inherited methods from OCP
    assert len(result['inherited_methods']) > 0


# ============================================================================
# Test 2: Real Repository Browsing
# ============================================================================

@pytest.mark.integration
def test_browse_real_repository(real_server):
    """Test browsing real ocs-ci repository structure"""

    # List root directory
    result = list_modules_tool(
        real_server.repo_path,
        path="",
        pattern="*"
    )

    assert 'items' in result
    items = result['items']
    item_names = [item['name'] for item in items]

    # Check for expected directories
    assert 'ocs_ci' in item_names
    assert 'tests' in item_names

    # List Python files in ocs_ci/ocs
    result = list_modules_tool(
        real_server.repo_path,
        path="ocs_ci/ocs",
        pattern="*.py"
    )

    assert 'items' in result
    items = result['items']
    item_names = [item['name'] for item in items]

    # ocp.py should exist
    assert 'ocp.py' in item_names


@pytest.mark.integration
def test_browse_resources_directory(real_server):
    """Test browsing ocs_ci/ocs/resources directory"""
    result = list_modules_tool(
        real_server.repo_path,
        path="ocs_ci/ocs/resources",
        pattern="*.py"
    )

    assert 'items' in result
    items = result['items']
    item_names = [item['name'] for item in items]

    # pod.py should exist in resources
    assert 'pod.py' in item_names


# ============================================================================
# Test 3: Search Across Real Codebase
# ============================================================================

@pytest.mark.integration
def test_search_real_codebase(real_server):
    """Test searching across real ocs-ci codebase"""

    # Search for class Pod pattern
    result = search_code_tool(
        repo_path=real_server.repo_path,
        pattern=r"class Pod\(",
        file_pattern="*.py",
        context_lines=0
    )

    assert 'matches' in result
    assert 'total_matches' in result
    assert result['total_matches'] > 0

    # Verify at least one match is in pod.py
    matches = result['matches']
    pod_matches = [m for m in matches if 'pod.py' in m['file_path']]
    assert len(pod_matches) > 0


@pytest.mark.integration
def test_search_with_context(real_server):
    """Test searching with context lines"""
    result = search_code_tool(
        repo_path=real_server.repo_path,
        pattern=r"class OCP\(",
        file_pattern="*.py",
        context_lines=3
    )

    assert 'matches' in result
    assert result['total_matches'] > 0

    # Verify context is included
    matches = result['matches']
    if len(matches) > 0:
        first_match = matches[0]
        assert 'context' in first_match
        # Context is a single string with before/match/after
        assert isinstance(first_match['context'], str)
        assert len(first_match['context']) > 0


# ============================================================================
# Test 4: Find Real Test
# ============================================================================

@pytest.mark.integration
def test_find_real_test(real_server):
    """Test finding a real test in ocs-ci"""

    # Find tests matching "test_pvc" - use more generic pattern
    result = find_test_tool(
        repo_path=real_server.repo_path,
        test_name="test_pod"
    )

    # find_test may or may not find results, check it doesn't crash
    assert 'error' not in result or result.get('error') == 'TestNotFound'

    if 'matches' in result:
        assert len(result['matches']) > 0


@pytest.mark.integration
def test_find_test_by_nodeid(real_server):
    """Test finding test by pytest nodeid pattern"""

    # Search for any test file
    result = find_test_tool(
        repo_path=real_server.repo_path,
        test_name="test_"
    )

    # Should find many tests
    if 'matches' in result:
        assert len(result['matches']) > 0


# ============================================================================
# Test 5: Read Real File Content
# ============================================================================

@pytest.mark.integration
def test_read_real_file(real_server):
    """Test reading real file content"""
    result = get_content_tool(
        repo_path=real_server.repo_path,
        file_path="ocs_ci/ocs/ocp.py",
        start_line=1,
        end_line=50
    )

    assert 'content' in result
    assert 'class OCP' in result['content']
    assert 'file_path' in result
    assert result['file_path'] == 'ocs_ci/ocs/ocp.py'


@pytest.mark.integration
def test_read_entire_file(real_server):
    """Test reading entire file without line limits"""
    result = get_content_tool(
        repo_path=real_server.repo_path,
        file_path="ocs_ci/ocs/__init__.py"
    )

    assert 'content' in result
    assert 'file_path' in result


# ============================================================================
# Test 6: Sensitive Directory Blocking
# ============================================================================

@pytest.mark.integration
def test_sensitive_directory_blocked_integration(real_server):
    """Test that sensitive directories are blocked in real repo"""

    # Try to access data directory
    result = get_content_tool(
        repo_path=real_server.repo_path,
        file_path="data/auth.yaml"
    )

    assert 'error' in result
    assert result['error'] == 'AccessDenied'
    assert 'sensitive' in result['message'].lower()


@pytest.mark.integration
def test_sensitive_directory_allowed_with_flag(real_server_with_sensitive):
    """Test that sensitive directories can be accessed with flag"""

    # Try to list data directory with flag enabled
    result = list_modules_tool(
        real_server_with_sensitive.repo_path,
        path="data",
        pattern="*",
        allow_sensitive=True
    )

    # Should succeed (not return AccessDenied error)
    assert 'items' in result or 'error' not in result or result.get('error') != 'AccessDenied'


@pytest.mark.integration
def test_git_directory_blocked(real_server):
    """Test that .git directory is blocked"""
    result = list_modules_tool(
        real_server.repo_path,
        path=".git",
        pattern="*"
    )

    assert 'error' in result
    assert result['error'] == 'AccessDenied'


# ============================================================================
# Test 7: Performance Benchmark
# ============================================================================

@pytest.mark.integration
def test_performance_benchmark(real_server):
    """Benchmark performance on real repository"""

    # Measure analysis time for Pod class
    start = time.time()
    result = get_summary_tool(
        repo_path=real_server.repo_path,
        file_path="ocs_ci/ocs/resources/pod.py",
        class_name="Pod",
        analyzer=real_server.analyzer,
        resolver=real_server.resolver,
        summarizer=real_server.summarizer
    )
    duration = time.time() - start

    assert 'class_name' in result
    assert result['class_name'] == 'Pod'
    assert duration < 5.0  # Should complete in under 5 seconds

    print(f"\n[PERFORMANCE] Pod class analysis: {duration:.3f}s")


@pytest.mark.integration
def test_search_performance(real_server):
    """Benchmark search performance"""

    start = time.time()
    result = search_code_tool(
        repo_path=real_server.repo_path,
        pattern=r"def test_",
        file_pattern="*.py",
        context_lines=0,
        path="tests"
    )
    duration = time.time() - start

    assert 'matches' in result
    assert duration < 10.0  # Should complete in under 10 seconds

    print(f"\n[PERFORMANCE] Search for test functions: {duration:.3f}s ({result['total_matches']} matches)")


# ============================================================================
# Test 8: Multiple Inheritance Detection
# ============================================================================

@pytest.mark.integration
def test_real_multiple_inheritance(real_server):
    """Test detecting multiple inheritance in real ocs-ci classes"""

    # Search for classes with multiple inheritance
    result = search_code_tool(
        repo_path=real_server.repo_path,
        pattern=r"class \w+\([^)]+,[^)]+\):",  # Multiple parents
        file_pattern="*.py",
        context_lines=0
    )

    assert 'matches' in result
    assert 'total_matches' in result
    # ocs-ci may or may not have multiple inheritance - just check search works
    assert result['total_matches'] >= 0


# ============================================================================
# Test 9: End-to-End Workflow
# ============================================================================

@pytest.mark.integration
def test_end_to_end_workflow(real_server):
    """Test complete workflow: browse -> analyze -> read"""

    # Step 1: Browse to find files
    browse_result = list_modules_tool(
        real_server.repo_path,
        path="ocs_ci/ocs/resources",
        pattern="*.py"
    )
    assert 'items' in browse_result
    item_names = [item['name'] for item in browse_result['items']]
    assert 'pod.py' in item_names

    # Step 2: Get summary of file
    summary_result = get_summary_tool(
        repo_path=real_server.repo_path,
        file_path="ocs_ci/ocs/resources/pod.py",
        class_name=None,
        analyzer=real_server.analyzer,
        resolver=real_server.resolver,
        summarizer=real_server.summarizer
    )
    assert 'classes' in summary_result

    # Verify Pod class exists
    class_names = [c['name'] for c in summary_result['classes']]
    assert 'Pod' in class_names

    # Step 3: Read specific content
    content_result = get_content_tool(
        repo_path=real_server.repo_path,
        file_path="ocs_ci/ocs/resources/pod.py",
        start_line=1,
        end_line=20
    )
    assert 'content' in content_result

    print(f"\n[WORKFLOW] Browse -> Analyze -> Read completed successfully")


@pytest.mark.integration
def test_workflow_class_analysis(real_server):
    """Test workflow for analyzing a specific class"""

    # Step 1: Search for Pod class
    search_result = search_code_tool(
        repo_path=real_server.repo_path,
        pattern=r"class Pod\(",
        file_pattern="*.py",
        context_lines=0
    )
    assert search_result['total_matches'] > 0

    # Step 2: Get detailed class summary
    class_result = get_summary_tool(
        repo_path=real_server.repo_path,
        file_path="ocs_ci/ocs/resources/pod.py",
        class_name="Pod",
        analyzer=real_server.analyzer,
        resolver=real_server.resolver,
        summarizer=real_server.summarizer
    )
    assert class_result['class_name'] == 'Pod'
    assert len(class_result['own_methods']) > 0

    # Step 3: Get full inheritance chain
    inheritance_result = get_inheritance_tool(
        repo_path=real_server.repo_path,
        file_path="ocs_ci/ocs/resources/pod.py",
        class_name="Pod",
        analyzer=real_server.analyzer,
        resolver=real_server.resolver
    )
    assert 'class_name' in inheritance_result
    assert 'mro' in inheritance_result

    print(f"\n[WORKFLOW] Class analysis workflow completed successfully")


# ============================================================================
# Test 10: Error Handling
# ============================================================================

@pytest.mark.integration
def test_error_handling_integration(real_server):
    """Test error handling with real repository"""

    # Non-existent file
    result = get_summary_tool(
        repo_path=real_server.repo_path,
        file_path="nonexistent/file.py",
        class_name=None,
        analyzer=real_server.analyzer,
        resolver=real_server.resolver,
        summarizer=real_server.summarizer
    )
    assert 'error' in result

    # Non-existent class
    result = get_summary_tool(
        repo_path=real_server.repo_path,
        file_path="ocs_ci/ocs/ocp.py",
        class_name="NonExistentClass",
        analyzer=real_server.analyzer,
        resolver=real_server.resolver,
        summarizer=real_server.summarizer
    )
    assert 'error' in result


@pytest.mark.integration
def test_error_invalid_line_range(real_server):
    """Test error handling for invalid line ranges"""

    # Invalid line range (start > end)
    result = get_content_tool(
        repo_path=real_server.repo_path,
        file_path="ocs_ci/ocs/ocp.py",
        start_line=100,
        end_line=50
    )

    # Should handle gracefully
    assert 'error' in result or 'content' in result


@pytest.mark.integration
def test_error_invalid_regex(real_server):
    """Test error handling for invalid regex patterns"""

    # Invalid regex pattern
    result = search_code_tool(
        repo_path=real_server.repo_path,
        pattern=r"[invalid(",  # Unclosed bracket
        file_pattern="*.py",
        context_lines=0
    )

    # Should return error
    assert 'error' in result


# ============================================================================
# Additional Integration Tests
# ============================================================================

@pytest.mark.integration
def test_get_test_example_integration(real_server):
    """Test finding example tests in real repository"""

    result = get_test_example_tool(
        repo_path=real_server.repo_path,
        pattern="pvc",
        max_results=3
    )

    # Should find some test examples
    if 'examples' in result:
        assert len(result['examples']) > 0

        # Verify structure
        for example in result['examples']:
            assert 'file_path' in example
            assert 'test_name' in example


@pytest.mark.integration
def test_inheritance_chain_real(real_server):
    """Test getting full inheritance chain from real classes"""

    result = get_inheritance_tool(
        repo_path=real_server.repo_path,
        file_path="ocs_ci/ocs/resources/pod.py",
        class_name="Pod",
        analyzer=real_server.analyzer,
        resolver=real_server.resolver
    )

    assert 'class_name' in result
    assert result['class_name'] == 'Pod'
    assert 'mro' in result

    # Pod should have at least OCS/OCP in its MRO
    mro = result['mro']
    assert len(mro) > 0

    # Verify MRO structure
    for level in mro:
        assert 'class' in level
        assert 'file' in level


@pytest.mark.integration
def test_repository_exists(real_repo_path):
    """Verify real repository exists and has expected structure"""
    repo_path = Path(real_repo_path)

    assert repo_path.exists(), f"Repository not found at {real_repo_path}"
    assert repo_path.is_dir(), f"Repository path is not a directory: {real_repo_path}"

    # Check for key directories
    assert (repo_path / "ocs_ci").exists(), "ocs_ci directory not found"
    assert (repo_path / "ocs_ci" / "ocs").exists(), "ocs_ci/ocs directory not found"
    assert (repo_path / "tests").exists(), "tests directory not found"

    # Check for key files
    assert (repo_path / "ocs_ci" / "ocs" / "ocp.py").exists(), "ocp.py not found"
    assert (repo_path / "ocs_ci" / "ocs" / "resources" / "pod.py").exists(), "pod.py not found"


@pytest.mark.integration
def test_comprehensive_search(real_server):
    """Test comprehensive search across repository"""

    # Search for all test fixtures
    result = search_code_tool(
        repo_path=real_server.repo_path,
        pattern=r"@pytest\.fixture",
        file_pattern="*.py",
        context_lines=1,
        path="tests"
    )

    assert 'matches' in result
    assert result['total_matches'] > 0

    print(f"\n[SEARCH] Found {result['total_matches']} pytest fixtures")


@pytest.mark.integration
def test_file_listing_performance(real_server):
    """Test performance of directory listing"""

    start = time.time()
    # List all items in ocs_ci/ocs (more interesting than root)
    result = list_modules_tool(
        real_server.repo_path,
        path="ocs_ci/ocs",
        pattern="*.py"
    )
    duration = time.time() - start

    assert 'items' in result
    assert len(result['items']) > 0
    assert duration < 2.0  # Should be fast

    print(f"\n[PERFORMANCE] List ocs_ci/ocs Python files: {duration:.3f}s ({len(result['items'])} files)")


# ============================================================================
# Test 11: Module Discovery Integration Tests
# ============================================================================

@pytest.mark.integration
class TestModuleDiscoveryIntegration:
    """Integration tests for module discovery tools against real ocs-ci repo"""

    def test_get_deployment_module_real_repo(self, real_server):
        """Test get_deployment_module with real ocs-ci repo"""
        result = get_deployment_module_tool(
            repo_path=real_server.repo_path,
            analyzer=real_server.analyzer
        )

        assert "error" not in result
        assert result["directory"] == "ocs_ci/deployment"
        assert result["total_modules"] > 0

        # Check meaningful descriptions
        for module in result["modules"]:
            assert "name" in module
            assert "description" in module
            assert len(module["description"]) > 0

    def test_get_deployment_module_pattern_filter(self, real_server):
        """Test pattern filtering on real repo"""
        result = get_deployment_module_tool(
            repo_path=real_server.repo_path,
            pattern="*aws*",
            analyzer=real_server.analyzer
        )

        assert "error" not in result
        # Should find aws.py
        assert any("aws" in m["name"].lower() for m in result["modules"])

    def test_get_resource_module_real_repo(self, real_server):
        """Test get_resource_module with real ocs-ci repo"""
        result = get_resource_module_tool(
            repo_path=real_server.repo_path,
            analyzer=real_server.analyzer
        )

        assert "error" not in result
        assert result["directory"] == "ocs_ci/ocs/resources"
        assert result["total_modules"] > 0

    def test_get_helper_module_real_repo(self, real_server):
        """Test get_helper_module with real ocs-ci repo"""
        result = get_helper_module_tool(
            repo_path=real_server.repo_path,
            analyzer=real_server.analyzer
        )

        assert "error" not in result
        assert result["directory"] == "ocs_ci/helpers"
        assert result["total_modules"] > 0

    def test_get_utility_module_real_repo(self, real_server):
        """Test get_utility_module with real ocs-ci repo"""
        result = get_utility_module_tool(
            repo_path=real_server.repo_path,
            analyzer=real_server.analyzer
        )

        assert "error" not in result
        assert result["directory"] == "ocs_ci/utility"
        assert result["total_modules"] > 0

    def test_get_conftest_real_repo(self, real_server):
        """Test get_conftest with real ocs-ci repo"""
        result = get_conftest_tool(
            repo_path=real_server.repo_path,
            analyzer=real_server.analyzer
        )

        assert "error" not in result
        assert result["directory"] == "tests"
        assert result["total_modules"] > 0
        # All should be named conftest.py
        assert all(m["name"] == "conftest.py" for m in result["modules"])

    def test_get_conf_file_real_repo(self, real_server):
        """Test get_conf_file with real ocs-ci repo"""
        result = get_conf_file_tool(
            repo_path=real_server.repo_path
        )

        assert "error" not in result
        assert result["directory"] == "conf"
        # May or may not have files
        assert "total_modules" in result

    def test_search_filtering_real_repo(self, real_server):
        """Test search filtering with real repo"""
        result = get_deployment_module_tool(
            repo_path=real_server.repo_path,
            search_text="AWS",
            analyzer=real_server.analyzer
        )

        assert "error" not in result
        # Should find modules with AWS in description or name
        for module in result["modules"]:
            desc_match = "aws" in module["description"].lower()
            name_match = "aws" in module["name"].lower()
            assert desc_match or name_match
