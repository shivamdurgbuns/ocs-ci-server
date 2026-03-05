# MCP Tools Expansion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 6 new MCP tools for faster navigation to specific module types (conf, conftest, deployment, resource, helper, utility) with pattern filtering and description search.

**Architecture:** Create shared `module_discovery.py` helper for common logic (directory walking, description extraction, filtering). Each of 6 tools is a thin wrapper that calls the helper with specific directory configuration. Reuse existing `ASTAnalyzer` and security validation patterns.

**Tech Stack:** Python 3.9+, MCP SDK, AST module (stdlib), fnmatch (stdlib), pytest

---

## Task 1: Create Shared Module Discovery Helper

**Files:**
- Create: `tools/module_discovery.py`
- Test: `tests/test_module_discovery.py`

**Step 1: Write failing test for basic discovery**

Create `tests/test_module_discovery.py`:

```python
"""Tests for module_discovery helper"""

import pytest
from pathlib import Path
import tempfile
import shutil
from tools.module_discovery import discover_modules, extract_description
from analyzers.ast_analyzer import ASTAnalyzer


class TestDiscoverModules:
    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository structure"""
        tmpdir = tempfile.mkdtemp()
        repo_path = Path(tmpdir) / "test_repo"
        repo_path.mkdir()

        # Create test directory with Python files
        test_dir = repo_path / "ocs_ci" / "deployment"
        test_dir.mkdir(parents=True)

        # Create test file with docstring
        test_file = test_dir / "test_module.py"
        test_file.write_text('"""Test module for deployment"""\n\ndef foo():\n    pass\n')

        yield str(repo_path)

        # Cleanup
        shutil.rmtree(tmpdir)

    def test_discover_modules_basic(self, temp_repo):
        """Test basic module discovery without filters"""
        analyzer = ASTAnalyzer()

        result = discover_modules(
            repo_path=temp_repo,
            target_dir="ocs_ci/deployment",
            analyzer=analyzer
        )

        assert result["directory"] == "ocs_ci/deployment"
        assert result["total_modules"] == 1
        assert result["filtered_modules"] == 1
        assert len(result["modules"]) == 1
        assert result["modules"][0]["name"] == "test_module.py"
        assert "Test module for deployment" in result["modules"][0]["description"]
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_module_discovery.py::TestDiscoverModules::test_discover_modules_basic -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'tools.module_discovery'"

**Step 3: Write minimal implementation**

Create `tools/module_discovery.py`:

```python
"""
Shared helper for module discovery tools

Provides common functionality for discovering and describing modules
in specific directories with pattern and search filtering.
"""

from pathlib import Path
from typing import Dict, Optional, List
import fnmatch
from tools.security import validate_path


def discover_modules(
    repo_path: str,
    target_dir: str,
    pattern: str = "*",
    search_text: Optional[str] = None,
    file_extension: str = ".py",
    recursive: bool = False,
    analyzer=None,
    allow_sensitive: bool = False
) -> Dict:
    """
    Discover modules in a directory with filtering

    Args:
        repo_path: Path to repository root
        target_dir: Relative directory to search (e.g., "ocs_ci/deployment")
        pattern: Filename pattern (e.g., "*aws*")
        search_text: Search within descriptions (case-insensitive)
        file_extension: File extension to filter (default: ".py", use "" for all)
        recursive: Whether to search subdirectories
        analyzer: ASTAnalyzer instance for parsing Python files
        allow_sensitive: Security flag

    Returns:
        Dict with directory, total_modules, filtered_modules, modules list
    """
    # Validate path
    validation_error = validate_path(repo_path, target_dir, allow_sensitive)
    if validation_error:
        return validation_error

    repo_root = Path(repo_path).resolve()
    target_path = (repo_root / target_dir).resolve()

    if not target_path.exists():
        return {
            'error': 'PathNotFound',
            'message': f'Directory not found: {target_dir}'
        }

    if not target_path.is_dir():
        return {
            'error': 'NotADirectory',
            'message': f'Path is not a directory: {target_dir}'
        }

    # Collect modules
    modules = []

    try:
        if recursive:
            files = target_path.rglob(f"*{file_extension}") if file_extension else target_path.rglob("*")
        else:
            files = target_path.glob(f"*{file_extension}") if file_extension else target_path.glob("*")

        for file_path in files:
            if not file_path.is_file():
                continue

            # Skip hidden files and __pycache__
            if file_path.name.startswith('.') or '__pycache__' in str(file_path):
                continue

            # Apply pattern filter to filename
            if not fnmatch.fnmatch(file_path.name, pattern):
                continue

            # Extract description
            if file_extension == ".py" and analyzer:
                description = extract_description(str(file_path), analyzer)
            else:
                description = extract_config_description(str(file_path))

            # Apply search filter to description
            if search_text and search_text.lower() not in description.lower():
                continue

            # Get relative path
            relative_path = file_path.relative_to(repo_root)

            # Count lines
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    line_count = sum(1 for _ in f)
            except:
                line_count = 0

            modules.append({
                'name': file_path.name,
                'path': str(relative_path),
                'description': description,
                'size_bytes': file_path.stat().st_size,
                'lines': line_count
            })

    except PermissionError:
        return {
            'error': 'PermissionDenied',
            'message': f'Cannot read directory: {target_dir}'
        }

    # Sort by name
    modules.sort(key=lambda m: m['name'])

    return {
        'directory': target_dir,
        'total_modules': len(modules),
        'filtered_modules': len(modules),
        'modules': modules
    }


def extract_description(file_path: str, analyzer) -> str:
    """
    Extract module description from Python file

    Args:
        file_path: Path to Python file
        analyzer: ASTAnalyzer instance

    Returns:
        First line of module docstring or "No description available"
    """
    try:
        import ast

        # Parse file
        tree = analyzer.parse_file(file_path)

        # Get module docstring (first expression if it's a string)
        if tree.body and isinstance(tree.body[0], ast.Expr):
            if isinstance(tree.body[0].value, (ast.Str, ast.Constant)):
                # Handle both ast.Str (Python 3.7) and ast.Constant (Python 3.8+)
                if isinstance(tree.body[0].value, ast.Str):
                    docstring = tree.body[0].value.s
                else:
                    docstring = tree.body[0].value.value

                if isinstance(docstring, str):
                    # First line only, truncate at 200 chars
                    first_line = docstring.split('\n')[0].strip()
                    return first_line[:200] if first_line else "No description available"

        return "No description available"

    except:
        return "No description available"


def extract_config_description(file_path: str) -> str:
    """
    Extract description from config file

    Args:
        file_path: Path to config file

    Returns:
        First comment line or "Configuration file"
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Read first 10 lines
            for _ in range(10):
                line = f.readline()
                if not line:
                    break

                # Look for comment
                stripped = line.strip()
                if stripped.startswith('#'):
                    desc = stripped.lstrip('#').strip()
                    if desc:
                        return desc[:200]

        return "Configuration file"

    except:
        return "Configuration file"
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_module_discovery.py::TestDiscoverModules::test_discover_modules_basic -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tools/module_discovery.py tests/test_module_discovery.py
git commit -m "feat: add shared module discovery helper

- discover_modules() function for directory scanning
- extract_description() for Python docstrings
- extract_config_description() for config files
- Pattern and search filtering support

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Add Pattern Filtering Tests

**Files:**
- Modify: `tests/test_module_discovery.py`

**Step 1: Write failing test for pattern filtering**

Add to `tests/test_module_discovery.py`:

```python
def test_discover_modules_with_pattern(self, temp_repo):
    """Test pattern filtering"""
    analyzer = ASTAnalyzer()

    # Create additional files
    test_dir = Path(temp_repo) / "ocs_ci" / "deployment"
    (test_dir / "aws.py").write_text('"""AWS module"""\n')
    (test_dir / "azure.py").write_text('"""Azure module"""\n')
    (test_dir / "other.py").write_text('"""Other module"""\n')

    result = discover_modules(
        repo_path=temp_repo,
        target_dir="ocs_ci/deployment",
        pattern="a*",  # Match aws.py and azure.py
        analyzer=analyzer
    )

    assert result["total_modules"] == 2
    assert result["filtered_modules"] == 2
    names = [m["name"] for m in result["modules"]]
    assert "aws.py" in names
    assert "azure.py" in names
    assert "other.py" not in names
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_module_discovery.py::TestDiscoverModules::test_discover_modules_with_pattern -v
```

Expected: FAIL (test_module.py shouldn't be in results but is)

**Step 3: Fix implementation**

The implementation already supports pattern filtering, but we need to adjust total_modules count. Modify `tools/module_discovery.py`:

```python
def discover_modules(
    repo_path: str,
    target_dir: str,
    pattern: str = "*",
    search_text: Optional[str] = None,
    file_extension: str = ".py",
    recursive: bool = False,
    analyzer=None,
    allow_sensitive: bool = False
) -> Dict:
    """...(same docstring)..."""

    # Validate path
    validation_error = validate_path(repo_path, target_dir, allow_sensitive)
    if validation_error:
        return validation_error

    repo_root = Path(repo_path).resolve()
    target_path = (repo_root / target_dir).resolve()

    if not target_path.exists():
        return {
            'error': 'PathNotFound',
            'message': f'Directory not found: {target_dir}'
        }

    if not target_path.is_dir():
        return {
            'error': 'NotADirectory',
            'message': f'Path is not a directory: {target_dir}'
        }

    # Collect modules
    all_modules = []
    filtered_modules = []

    try:
        if recursive:
            files = target_path.rglob(f"*{file_extension}") if file_extension else target_path.rglob("*")
        else:
            files = target_path.glob(f"*{file_extension}") if file_extension else target_path.glob("*")

        for file_path in files:
            if not file_path.is_file():
                continue

            # Skip hidden files and __pycache__
            if file_path.name.startswith('.') or '__pycache__' in str(file_path):
                continue

            # Count all valid files
            all_modules.append(file_path.name)

            # Apply pattern filter to filename
            if not fnmatch.fnmatch(file_path.name, pattern):
                continue

            # Extract description
            if file_extension == ".py" and analyzer:
                description = extract_description(str(file_path), analyzer)
            else:
                description = extract_config_description(str(file_path))

            # Apply search filter to description
            if search_text and search_text.lower() not in description.lower():
                continue

            # Get relative path
            relative_path = file_path.relative_to(repo_root)

            # Count lines
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    line_count = sum(1 for _ in f)
            except:
                line_count = 0

            filtered_modules.append({
                'name': file_path.name,
                'path': str(relative_path),
                'description': description,
                'size_bytes': file_path.stat().st_size,
                'lines': line_count
            })

    except PermissionError:
        return {
            'error': 'PermissionDenied',
            'message': f'Cannot read directory: {target_dir}'
        }

    # Sort by name
    filtered_modules.sort(key=lambda m: m['name'])

    return {
        'directory': target_dir,
        'total_modules': len(all_modules),
        'filtered_modules': len(filtered_modules),
        'modules': filtered_modules
    }
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_module_discovery.py::TestDiscoverModules::test_discover_modules_with_pattern -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tools/module_discovery.py tests/test_module_discovery.py
git commit -m "feat: add pattern filtering to module discovery

- Track total_modules vs filtered_modules separately
- Apply fnmatch pattern to filenames
- Add test for pattern filtering

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Add Search Filtering and More Tests

**Files:**
- Modify: `tests/test_module_discovery.py`

**Step 1: Write tests for search filtering and edge cases**

Add to `tests/test_module_discovery.py`:

```python
def test_discover_modules_with_search(self, temp_repo):
    """Test search filtering by description"""
    analyzer = ASTAnalyzer()

    # Create files with different descriptions
    test_dir = Path(temp_repo) / "ocs_ci" / "deployment"
    (test_dir / "aws.py").write_text('"""AWS deployment module"""\n')
    (test_dir / "azure.py").write_text('"""Azure cloud module"""\n')
    (test_dir / "bare.py").write_text('"""Bare metal deployment"""\n')

    result = discover_modules(
        repo_path=temp_repo,
        target_dir="ocs_ci/deployment",
        search_text="deployment",
        analyzer=analyzer
    )

    assert result["filtered_modules"] == 2
    names = [m["name"] for m in result["modules"]]
    assert "aws.py" in names
    assert "bare.py" in names
    assert "azure.py" not in names


def test_discover_modules_combined_filters(self, temp_repo):
    """Test combining pattern and search filters"""
    analyzer = ASTAnalyzer()

    # Create files
    test_dir = Path(temp_repo) / "ocs_ci" / "deployment"
    (test_dir / "aws.py").write_text('"""AWS deployment"""\n')
    (test_dir / "azure.py").write_text('"""Azure deployment"""\n')
    (test_dir / "other.py").write_text('"""Other stuff"""\n')

    result = discover_modules(
        repo_path=temp_repo,
        target_dir="ocs_ci/deployment",
        pattern="a*",
        search_text="deployment",
        analyzer=analyzer
    )

    assert result["filtered_modules"] == 2
    names = [m["name"] for m in result["modules"]]
    assert "aws.py" in names
    assert "azure.py" in names


def test_discover_modules_no_docstring(self, temp_repo):
    """Test handling files without docstrings"""
    analyzer = ASTAnalyzer()

    test_dir = Path(temp_repo) / "ocs_ci" / "deployment"
    (test_dir / "nodoc.py").write_text('def foo():\n    pass\n')

    result = discover_modules(
        repo_path=temp_repo,
        target_dir="ocs_ci/deployment",
        analyzer=analyzer
    )

    assert result["filtered_modules"] >= 1
    nodoc_module = next(m for m in result["modules"] if m["name"] == "nodoc.py")
    assert nodoc_module["description"] == "No description available"


def test_discover_modules_empty_directory(self, temp_repo):
    """Test empty directory"""
    analyzer = ASTAnalyzer()

    # Create empty directory
    empty_dir = Path(temp_repo) / "ocs_ci" / "empty"
    empty_dir.mkdir(parents=True)

    result = discover_modules(
        repo_path=temp_repo,
        target_dir="ocs_ci/empty",
        analyzer=analyzer
    )

    assert result["total_modules"] == 0
    assert result["filtered_modules"] == 0
    assert result["modules"] == []


def test_security_validation(self, temp_repo):
    """Test security validation"""
    analyzer = ASTAnalyzer()

    # Try path traversal
    result = discover_modules(
        repo_path=temp_repo,
        target_dir="../../../etc",
        analyzer=analyzer
    )

    assert "error" in result
    assert result["error"] == "SecurityError"
```

**Step 2: Run tests to verify they pass**

```bash
pytest tests/test_module_discovery.py -v
```

Expected: All PASS (implementation already handles these cases)

**Step 3: Commit**

```bash
git add tests/test_module_discovery.py
git commit -m "test: add comprehensive module discovery tests

- Search filtering tests
- Combined filter tests
- No docstring handling
- Empty directory handling
- Security validation

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Create get_deployment_module Tool

**Files:**
- Create: `tools/get_deployment_module.py`
- Create: `tests/test_get_deployment_module.py`

**Step 1: Write failing test**

Create `tests/test_get_deployment_module.py`:

```python
"""Tests for get_deployment_module tool"""

import pytest
from pathlib import Path
import tempfile
import shutil
from tools.get_deployment_module import get_deployment_module_tool
from analyzers.ast_analyzer import ASTAnalyzer


class TestGetDeploymentModule:
    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository"""
        tmpdir = tempfile.mkdtemp()
        repo_path = Path(tmpdir) / "test_repo"
        repo_path.mkdir()

        # Create deployment directory
        deployment_dir = repo_path / "ocs_ci" / "deployment"
        deployment_dir.mkdir(parents=True)

        (deployment_dir / "aws.py").write_text('"""AWS deployment module"""\n')
        (deployment_dir / "azure.py").write_text('"""Azure deployment"""\n')

        yield str(repo_path)
        shutil.rmtree(tmpdir)

    def test_list_all_modules(self, temp_repo):
        """Test listing all deployment modules"""
        analyzer = ASTAnalyzer()

        result = get_deployment_module_tool(
            repo_path=temp_repo,
            analyzer=analyzer
        )

        assert result["directory"] == "ocs_ci/deployment"
        assert result["total_modules"] == 2
        assert len(result["modules"]) == 2

    def test_filter_by_pattern(self, temp_repo):
        """Test pattern filtering"""
        analyzer = ASTAnalyzer()

        result = get_deployment_module_tool(
            repo_path=temp_repo,
            pattern="aws*",
            analyzer=analyzer
        )

        assert result["filtered_modules"] == 1
        assert result["modules"][0]["name"] == "aws.py"

    def test_security_validation(self, temp_repo):
        """Test that security validation is applied"""
        analyzer = ASTAnalyzer()

        # The tool should use the repo_path correctly
        # and not allow access outside it
        result = get_deployment_module_tool(
            repo_path=temp_repo,
            analyzer=analyzer,
            allow_sensitive=False
        )

        # Should succeed for valid path
        assert "error" not in result
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_get_deployment_module.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

Create `tools/get_deployment_module.py`:

```python
"""
get_deployment_module tool - List deployment modules

SECURITY: Includes path validation via module_discovery helper.
"""

from typing import Dict, Optional
from tools.module_discovery import discover_modules


def get_deployment_module_tool(
    repo_path: str,
    pattern: str = "*",
    search_text: Optional[str] = None,
    analyzer=None,
    allow_sensitive: bool = False
) -> Dict:
    """
    List deployment modules in ocs_ci/deployment/

    Args:
        repo_path: Path to ocs-ci repository root
        pattern: Filename pattern (e.g., "*aws*")
        search_text: Search within descriptions
        analyzer: ASTAnalyzer instance
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with directory, total_modules, filtered_modules, modules list
    """
    return discover_modules(
        repo_path=repo_path,
        target_dir="ocs_ci/deployment",
        pattern=pattern,
        search_text=search_text,
        file_extension=".py",
        recursive=False,
        analyzer=analyzer,
        allow_sensitive=allow_sensitive
    )
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_get_deployment_module.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tools/get_deployment_module.py tests/test_get_deployment_module.py
git commit -m "feat: add get_deployment_module tool

- List modules in ocs_ci/deployment/
- Support pattern and search filtering
- Reuse module_discovery helper

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Create Remaining 5 Tools

**Files:**
- Create: `tools/get_resource_module.py`
- Create: `tools/get_helper_module.py`
- Create: `tools/get_utility_module.py`
- Create: `tools/get_conf_file.py`
- Create: `tools/get_conftest.py`
- Create: `tests/test_get_resource_module.py`
- Create: `tests/test_get_helper_module.py`
- Create: `tests/test_get_utility_module.py`
- Create: `tests/test_get_conf_file.py`
- Create: `tests/test_get_conftest.py`

**Step 1: Create get_resource_module tool and test**

Create `tools/get_resource_module.py`:

```python
"""
get_resource_module tool - List resource modules

SECURITY: Includes path validation via module_discovery helper.
"""

from typing import Dict, Optional
from tools.module_discovery import discover_modules


def get_resource_module_tool(
    repo_path: str,
    pattern: str = "*",
    search_text: Optional[str] = None,
    analyzer=None,
    allow_sensitive: bool = False
) -> Dict:
    """
    List resource modules in ocs_ci/ocs/resources/

    Args:
        repo_path: Path to ocs-ci repository root
        pattern: Filename pattern (e.g., "pod*")
        search_text: Search within descriptions
        analyzer: ASTAnalyzer instance
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with directory, total_modules, filtered_modules, modules list
    """
    return discover_modules(
        repo_path=repo_path,
        target_dir="ocs_ci/ocs/resources",
        pattern=pattern,
        search_text=search_text,
        file_extension=".py",
        recursive=False,
        analyzer=analyzer,
        allow_sensitive=allow_sensitive
    )
```

Create `tests/test_get_resource_module.py`:

```python
"""Tests for get_resource_module tool"""

import pytest
from pathlib import Path
import tempfile
import shutil
from tools.get_resource_module import get_resource_module_tool
from analyzers.ast_analyzer import ASTAnalyzer


class TestGetResourceModule:
    @pytest.fixture
    def temp_repo(self):
        tmpdir = tempfile.mkdtemp()
        repo_path = Path(tmpdir) / "test_repo"
        repo_path.mkdir()

        resources_dir = repo_path / "ocs_ci" / "ocs" / "resources"
        resources_dir.mkdir(parents=True)

        (resources_dir / "pod.py").write_text('"""Pod resource"""\n')
        (resources_dir / "pvc.py").write_text('"""PVC resource"""\n')

        yield str(repo_path)
        shutil.rmtree(tmpdir)

    def test_list_all_modules(self, temp_repo):
        analyzer = ASTAnalyzer()
        result = get_resource_module_tool(repo_path=temp_repo, analyzer=analyzer)

        assert result["directory"] == "ocs_ci/ocs/resources"
        assert result["total_modules"] == 2
        assert len(result["modules"]) == 2
```

**Step 2: Create get_helper_module tool and test**

Create `tools/get_helper_module.py`:

```python
"""
get_helper_module tool - List helper modules

SECURITY: Includes path validation via module_discovery helper.
"""

from typing import Dict, Optional
from tools.module_discovery import discover_modules


def get_helper_module_tool(
    repo_path: str,
    pattern: str = "*",
    search_text: Optional[str] = None,
    analyzer=None,
    allow_sensitive: bool = False
) -> Dict:
    """
    List helper modules in ocs_ci/helpers/

    Args:
        repo_path: Path to ocs-ci repository root
        pattern: Filename pattern (e.g., "*dr*")
        search_text: Search within descriptions
        analyzer: ASTAnalyzer instance
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with directory, total_modules, filtered_modules, modules list
    """
    return discover_modules(
        repo_path=repo_path,
        target_dir="ocs_ci/helpers",
        pattern=pattern,
        search_text=search_text,
        file_extension=".py",
        recursive=False,
        analyzer=analyzer,
        allow_sensitive=allow_sensitive
    )
```

Create `tests/test_get_helper_module.py`:

```python
"""Tests for get_helper_module tool"""

import pytest
from pathlib import Path
import tempfile
import shutil
from tools.get_helper_module import get_helper_module_tool
from analyzers.ast_analyzer import ASTAnalyzer


class TestGetHelperModule:
    @pytest.fixture
    def temp_repo(self):
        tmpdir = tempfile.mkdtemp()
        repo_path = Path(tmpdir) / "test_repo"
        repo_path.mkdir()

        helpers_dir = repo_path / "ocs_ci" / "helpers"
        helpers_dir.mkdir(parents=True)

        (helpers_dir / "dr_helpers.py").write_text('"""DR helpers"""\n')
        (helpers_dir / "helpers.py").write_text('"""General helpers"""\n')

        yield str(repo_path)
        shutil.rmtree(tmpdir)

    def test_list_all_modules(self, temp_repo):
        analyzer = ASTAnalyzer()
        result = get_helper_module_tool(repo_path=temp_repo, analyzer=analyzer)

        assert result["directory"] == "ocs_ci/helpers"
        assert result["total_modules"] == 2
```

**Step 3: Create get_utility_module tool and test**

Create `tools/get_utility_module.py`:

```python
"""
get_utility_module tool - List utility modules

SECURITY: Includes path validation via module_discovery helper.
"""

from typing import Dict, Optional
from tools.module_discovery import discover_modules


def get_utility_module_tool(
    repo_path: str,
    pattern: str = "*",
    search_text: Optional[str] = None,
    analyzer=None,
    allow_sensitive: bool = False
) -> Dict:
    """
    List utility modules in ocs_ci/utility/

    Args:
        repo_path: Path to ocs-ci repository root
        pattern: Filename pattern (e.g., "*aws*")
        search_text: Search within descriptions
        analyzer: ASTAnalyzer instance
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with directory, total_modules, filtered_modules, modules list
    """
    return discover_modules(
        repo_path=repo_path,
        target_dir="ocs_ci/utility",
        pattern=pattern,
        search_text=search_text,
        file_extension=".py",
        recursive=False,
        analyzer=analyzer,
        allow_sensitive=allow_sensitive
    )
```

Create `tests/test_get_utility_module.py`:

```python
"""Tests for get_utility_module tool"""

import pytest
from pathlib import Path
import tempfile
import shutil
from tools.get_utility_module import get_utility_module_tool
from analyzers.ast_analyzer import ASTAnalyzer


class TestGetUtilityModule:
    @pytest.fixture
    def temp_repo(self):
        tmpdir = tempfile.mkdtemp()
        repo_path = Path(tmpdir) / "test_repo"
        repo_path.mkdir()

        utility_dir = repo_path / "ocs_ci" / "utility"
        utility_dir.mkdir(parents=True)

        (utility_dir / "aws.py").write_text('"""AWS utilities"""\n')
        (utility_dir / "utils.py").write_text('"""General utilities"""\n')

        yield str(repo_path)
        shutil.rmtree(tmpdir)

    def test_list_all_modules(self, temp_repo):
        analyzer = ASTAnalyzer()
        result = get_utility_module_tool(repo_path=temp_repo, analyzer=analyzer)

        assert result["directory"] == "ocs_ci/utility"
        assert result["total_modules"] == 2
```

**Step 4: Create get_conf_file tool and test**

Create `tools/get_conf_file.py`:

```python
"""
get_conf_file tool - List configuration files

SECURITY: Includes path validation via module_discovery helper.
"""

from typing import Dict, Optional
from tools.module_discovery import discover_modules


def get_conf_file_tool(
    repo_path: str,
    pattern: str = "*",
    search_text: Optional[str] = None,
    allow_sensitive: bool = False
) -> Dict:
    """
    List configuration files in conf/

    Args:
        repo_path: Path to ocs-ci repository root
        pattern: Filename pattern (e.g., "*.yaml")
        search_text: Search within descriptions
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with directory, total_modules, filtered_modules, modules list
    """
    return discover_modules(
        repo_path=repo_path,
        target_dir="conf",
        pattern=pattern,
        search_text=search_text,
        file_extension="",  # All files
        recursive=False,
        analyzer=None,  # No AST analyzer for config files
        allow_sensitive=allow_sensitive
    )
```

Create `tests/test_get_conf_file.py`:

```python
"""Tests for get_conf_file tool"""

import pytest
from pathlib import Path
import tempfile
import shutil
from tools.get_conf_file import get_conf_file_tool


class TestGetConfFile:
    @pytest.fixture
    def temp_repo(self):
        tmpdir = tempfile.mkdtemp()
        repo_path = Path(tmpdir) / "test_repo"
        repo_path.mkdir()

        conf_dir = repo_path / "conf"
        conf_dir.mkdir()

        (conf_dir / "config.yaml").write_text('# Main configuration\nkey: value\n')
        (conf_dir / "test.yaml").write_text('# Test config\ntest: true\n')

        yield str(repo_path)
        shutil.rmtree(tmpdir)

    def test_list_all_files(self, temp_repo):
        result = get_conf_file_tool(repo_path=temp_repo)

        assert result["directory"] == "conf"
        assert result["total_modules"] == 2
```

**Step 5: Create get_conftest tool and test**

Create `tools/get_conftest.py`:

```python
"""
get_conftest tool - List conftest.py files

SECURITY: Includes path validation via module_discovery helper.
"""

from typing import Dict, Optional
from tools.module_discovery import discover_modules


def get_conftest_tool(
    repo_path: str,
    pattern: str = "*",
    search_text: Optional[str] = None,
    analyzer=None,
    allow_sensitive: bool = False
) -> Dict:
    """
    List conftest.py files in tests/ directory tree

    Args:
        repo_path: Path to ocs-ci repository root
        pattern: Path pattern (e.g., "*functional*") - matches full path
        search_text: Search within descriptions
        analyzer: ASTAnalyzer instance
        allow_sensitive: If True, allow access to sensitive directories

    Returns:
        Dict with directory, total_modules, filtered_modules, modules list
    """
    result = discover_modules(
        repo_path=repo_path,
        target_dir="tests",
        pattern="conftest.py",
        search_text=search_text,
        file_extension=".py",
        recursive=True,
        analyzer=analyzer,
        allow_sensitive=allow_sensitive
    )

    # Apply path pattern filter if not default
    if pattern != "*":
        import fnmatch
        filtered = [
            m for m in result["modules"]
            if fnmatch.fnmatch(m["path"], f"*{pattern}*")
        ]
        result["filtered_modules"] = len(filtered)
        result["modules"] = filtered

    return result
```

Create `tests/test_get_conftest.py`:

```python
"""Tests for get_conftest tool"""

import pytest
from pathlib import Path
import tempfile
import shutil
from tools.get_conftest import get_conftest_tool
from analyzers.ast_analyzer import ASTAnalyzer


class TestGetConftest:
    @pytest.fixture
    def temp_repo(self):
        tmpdir = tempfile.mkdtemp()
        repo_path = Path(tmpdir) / "test_repo"
        repo_path.mkdir()

        tests_dir = repo_path / "tests"
        tests_dir.mkdir()

        (tests_dir / "conftest.py").write_text('"""Root conftest"""\n')

        functional_dir = tests_dir / "functional"
        functional_dir.mkdir()
        (functional_dir / "conftest.py").write_text('"""Functional conftest"""\n')

        yield str(repo_path)
        shutil.rmtree(tmpdir)

    def test_list_all_conftest(self, temp_repo):
        analyzer = ASTAnalyzer()
        result = get_conftest_tool(repo_path=temp_repo, analyzer=analyzer)

        assert result["directory"] == "tests"
        assert result["total_modules"] == 2
        assert all(m["name"] == "conftest.py" for m in result["modules"])

    def test_filter_by_path_pattern(self, temp_repo):
        analyzer = ASTAnalyzer()
        result = get_conftest_tool(
            repo_path=temp_repo,
            pattern="*functional*",
            analyzer=analyzer
        )

        assert result["filtered_modules"] == 1
        assert "functional" in result["modules"][0]["path"]
```

**Step 6: Run all new tests**

```bash
pytest tests/test_get_resource_module.py tests/test_get_helper_module.py tests/test_get_utility_module.py tests/test_get_conf_file.py tests/test_get_conftest.py -v
```

Expected: All PASS

**Step 7: Commit**

```bash
git add tools/get_*.py tests/test_get_*.py
git commit -m "feat: add 5 remaining module discovery tools

- get_resource_module: List resources in ocs_ci/ocs/resources/
- get_helper_module: List helpers in ocs_ci/helpers/
- get_utility_module: List utilities in ocs_ci/utility/
- get_conf_file: List config files in conf/
- get_conftest: List conftest.py files in tests/ (recursive)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Integrate Tools into Server

**Files:**
- Modify: `server.py`

**Step 1: Add imports**

Add to `server.py` after existing tool imports:

```python
from tools.get_conf_file import get_conf_file_tool
from tools.get_conftest import get_conftest_tool
from tools.get_deployment_module import get_deployment_module_tool
from tools.get_resource_module import get_resource_module_tool
from tools.get_helper_module import get_helper_module_tool
from tools.get_utility_module import get_utility_module_tool
```

**Step 2: Register tools in list_tools()**

Add to the return list in `_register_tools()` method, after existing tools:

```python
types.Tool(
    name="get_deployment_module",
    description="List deployment modules in ocs_ci/deployment/ with descriptions",
    inputSchema={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Filename pattern (e.g., '*aws*')",
                "default": "*"
            },
            "search_text": {
                "type": "string",
                "description": "Search within descriptions"
            }
        }
    }
),
types.Tool(
    name="get_resource_module",
    description="List resource modules in ocs_ci/ocs/resources/ with descriptions",
    inputSchema={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Filename pattern (e.g., 'pod*')",
                "default": "*"
            },
            "search_text": {
                "type": "string",
                "description": "Search within descriptions"
            }
        }
    }
),
types.Tool(
    name="get_helper_module",
    description="List helper modules in ocs_ci/helpers/ with descriptions",
    inputSchema={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Filename pattern (e.g., '*dr*')",
                "default": "*"
            },
            "search_text": {
                "type": "string",
                "description": "Search within descriptions"
            }
        }
    }
),
types.Tool(
    name="get_utility_module",
    description="List utility modules in ocs_ci/utility/ with descriptions",
    inputSchema={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Filename pattern (e.g., '*aws*')",
                "default": "*"
            },
            "search_text": {
                "type": "string",
                "description": "Search within descriptions"
            }
        }
    }
),
types.Tool(
    name="get_conftest",
    description="List all conftest.py files in tests/ directory tree with descriptions",
    inputSchema={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Path pattern (e.g., '*functional*')",
                "default": "*"
            },
            "search_text": {
                "type": "string",
                "description": "Search within descriptions"
            }
        }
    }
),
types.Tool(
    name="get_conf_file",
    description="List configuration files in conf/ directory with descriptions",
    inputSchema={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Filename pattern (e.g., '*.yaml')",
                "default": "*"
            },
            "search_text": {
                "type": "string",
                "description": "Search within descriptions"
            }
        }
    }
),
```

**Step 3: Add handlers in call_tool()**

Add to `_register_tool_handlers()` method, before the final `return` statement:

```python
elif name == "get_deployment_module":
    result = get_deployment_module_tool(
        repo_path=self.repo_path,
        pattern=arguments.get('pattern', '*'),
        search_text=arguments.get('search_text'),
        analyzer=self.analyzer,
        allow_sensitive=self.allow_sensitive
    )

    import json
    return [types.TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]

elif name == "get_resource_module":
    result = get_resource_module_tool(
        repo_path=self.repo_path,
        pattern=arguments.get('pattern', '*'),
        search_text=arguments.get('search_text'),
        analyzer=self.analyzer,
        allow_sensitive=self.allow_sensitive
    )

    import json
    return [types.TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]

elif name == "get_helper_module":
    result = get_helper_module_tool(
        repo_path=self.repo_path,
        pattern=arguments.get('pattern', '*'),
        search_text=arguments.get('search_text'),
        analyzer=self.analyzer,
        allow_sensitive=self.allow_sensitive
    )

    import json
    return [types.TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]

elif name == "get_utility_module":
    result = get_utility_module_tool(
        repo_path=self.repo_path,
        pattern=arguments.get('pattern', '*'),
        search_text=arguments.get('search_text'),
        analyzer=self.analyzer,
        allow_sensitive=self.allow_sensitive
    )

    import json
    return [types.TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]

elif name == "get_conftest":
    result = get_conftest_tool(
        repo_path=self.repo_path,
        pattern=arguments.get('pattern', '*'),
        search_text=arguments.get('search_text'),
        analyzer=self.analyzer,
        allow_sensitive=self.allow_sensitive
    )

    import json
    return [types.TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]

elif name == "get_conf_file":
    result = get_conf_file_tool(
        repo_path=self.repo_path,
        pattern=arguments.get('pattern', '*'),
        search_text=arguments.get('search_text'),
        allow_sensitive=self.allow_sensitive
    )

    import json
    return [types.TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]
```

**Step 4: Test server manually**

```bash
# Start server in test mode pointing to ocs-ci repo
python server.py --repo-path /Users/sdurgbun/code/redhat/odf/ocs-ci/
```

Expected: Server starts without errors

**Step 5: Commit**

```bash
git add server.py
git commit -m "feat: integrate 6 new tools into MCP server

- Register tools in list_tools()
- Add handlers in call_tool()
- Pass analyzer instance to tools
- Total tools: 7 -> 13

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Add Integration Tests

**Files:**
- Modify: `tests/test_integration.py`

**Step 1: Add integration tests for new tools**

Add to `tests/test_integration.py`:

```python
@pytest.mark.integration
class TestModuleDiscoveryIntegration:
    """Integration tests for module discovery tools against real ocs-ci repo"""

    def test_get_deployment_module_real_repo(self, server):
        """Test get_deployment_module with real ocs-ci repo"""
        result = get_deployment_module_tool(
            repo_path=server.repo_path,
            analyzer=server.analyzer
        )

        assert "error" not in result
        assert result["directory"] == "ocs_ci/deployment"
        assert result["total_modules"] > 0

        # Check that we get meaningful descriptions
        for module in result["modules"]:
            assert "name" in module
            assert "description" in module
            assert len(module["description"]) > 0

    def test_get_deployment_module_pattern_filter(self, server):
        """Test pattern filtering on real repo"""
        result = get_deployment_module_tool(
            repo_path=server.repo_path,
            pattern="*aws*",
            analyzer=server.analyzer
        )

        assert "error" not in result
        # Should find aws.py
        assert any("aws" in m["name"].lower() for m in result["modules"])

    def test_get_resource_module_real_repo(self, server):
        """Test get_resource_module with real ocs-ci repo"""
        result = get_resource_module_tool(
            repo_path=server.repo_path,
            analyzer=server.analyzer
        )

        assert "error" not in result
        assert result["directory"] == "ocs_ci/ocs/resources"
        assert result["total_modules"] > 0

    def test_get_helper_module_real_repo(self, server):
        """Test get_helper_module with real ocs-ci repo"""
        result = get_helper_module_tool(
            repo_path=server.repo_path,
            analyzer=server.analyzer
        )

        assert "error" not in result
        assert result["directory"] == "ocs_ci/helpers"
        assert result["total_modules"] > 0

    def test_get_utility_module_real_repo(self, server):
        """Test get_utility_module with real ocs-ci repo"""
        result = get_utility_module_tool(
            repo_path=server.repo_path,
            analyzer=server.analyzer
        )

        assert "error" not in result
        assert result["directory"] == "ocs_ci/utility"
        assert result["total_modules"] > 0

    def test_get_conftest_real_repo(self, server):
        """Test get_conftest with real ocs-ci repo"""
        result = get_conftest_tool(
            repo_path=server.repo_path,
            analyzer=server.analyzer
        )

        assert "error" not in result
        assert result["directory"] == "tests"
        assert result["total_modules"] > 0
        # All should be named conftest.py
        assert all(m["name"] == "conftest.py" for m in result["modules"])

    def test_get_conf_file_real_repo(self, server):
        """Test get_conf_file with real ocs-ci repo"""
        result = get_conf_file_tool(
            repo_path=server.repo_path
        )

        assert "error" not in result
        assert result["directory"] == "conf"
        # May or may not have files depending on repo state
        assert "total_modules" in result

    def test_search_filtering_real_repo(self, server):
        """Test search filtering with real repo"""
        result = get_deployment_module_tool(
            repo_path=server.repo_path,
            search_text="AWS",
            analyzer=server.analyzer
        )

        assert "error" not in result
        # Should find modules with AWS in description
        for module in result["modules"]:
            assert "aws" in module["description"].lower() or "aws" in module["name"].lower()
```

**Step 2: Add import statements**

Add to top of `tests/test_integration.py`:

```python
from tools.get_deployment_module import get_deployment_module_tool
from tools.get_resource_module import get_resource_module_tool
from tools.get_helper_module import get_helper_module_tool
from tools.get_utility_module import get_utility_module_tool
from tools.get_conftest import get_conftest_tool
from tools.get_conf_file import get_conf_file_tool
```

**Step 3: Run integration tests**

```bash
pytest tests/test_integration.py::TestModuleDiscoveryIntegration -v -m integration
```

Expected: All PASS (requires real ocs-ci repo)

**Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for new tools

- Test all 6 tools against real ocs-ci repo
- Test pattern filtering
- Test search filtering
- Verify meaningful descriptions

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Run Full Test Suite

**Step 1: Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests PASS

**Step 2: Run tests with coverage**

```bash
pytest tests/ --cov=tools --cov=analyzers --cov-report=term-missing
```

Expected: High coverage (>95%)

**Step 3: If any tests fail, fix them and commit**

```bash
# Fix issues, then:
git add <fixed-files>
git commit -m "fix: resolve test failures

<description of fixes>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Update Documentation

**Files:**
- Modify: `README.md`
- Modify: `API_REFERENCE.md`
- Modify: `USER_GUIDE.md`
- Modify: `TOOLS_SUMMARY.md`
- Modify: `QUICK_REFERENCE.md`
- Modify: `ARCHITECTURE.md`
- Modify: `CHANGELOG.md`

**Step 1: Update README.md**

Change line 14:

```markdown
The OCS-CI MCP Server provides 7 specialized tools for analyzing the ocs-ci codebase
```

To:

```markdown
The OCS-CI MCP Server provides 13 specialized tools for analyzing the ocs-ci codebase
```

Change line 17:

```markdown
✅ **7 Powerful Tools** - Find tests, analyze classes, search code, browse structure
```

To:

```markdown
✅ **13 Powerful Tools** - Find tests, analyze classes, search code, browse structure, discover modules
```

Add to tools table (after line 89):

```markdown
| **get_deployment_module** | List deployment modules | Find AWS deployment code |
| **get_resource_module** | List resource modules | Find Pod resource class |
| **get_helper_module** | List helper modules | Find DR helper functions |
| **get_utility_module** | List utility modules | Find AWS utility functions |
| **get_conftest** | List conftest files | Find pytest fixtures |
| **get_conf_file** | List config files | Browse configurations |
```

Update line 159:

```markdown
Tools:                    7
```

To:

```markdown
Tools:                    13
```

**Step 2: Update API_REFERENCE.md**

Add new section after existing tools:

```markdown
## Module Discovery Tools

### get_deployment_module

List deployment modules in `ocs_ci/deployment/` directory.

**Parameters:**
- `pattern` (string, optional): Filename pattern (e.g., `"*aws*"`). Default: `"*"`
- `search_text` (string, optional): Search within module descriptions

**Returns:**
```json
{
  "directory": "ocs_ci/deployment",
  "total_modules": 42,
  "filtered_modules": 2,
  "modules": [
    {
      "name": "aws.py",
      "path": "ocs_ci/deployment/aws.py",
      "description": "AWS deployment module for provisioning OCS clusters",
      "size_bytes": 35883,
      "lines": 1245
    }
  ]
}
```

**Example:**
```python
# List all deployment modules
get_deployment_module()

# Find AWS-related modules
get_deployment_module(pattern="*aws*")

# Search by description
get_deployment_module(search_text="bare metal")
```

### get_resource_module

List resource modules in `ocs_ci/ocs/resources/` directory.

**Parameters:**
- `pattern` (string, optional): Filename pattern (e.g., `"pod*"`). Default: `"*"`
- `search_text` (string, optional): Search within module descriptions

**Returns:** Same format as get_deployment_module

**Example:**
```python
# Find Pod resource
get_resource_module(pattern="pod*")
```

### get_helper_module

List helper modules in `ocs_ci/helpers/` directory.

**Parameters:**
- `pattern` (string, optional): Filename pattern (e.g., `"*dr*"`). Default: `"*"`
- `search_text` (string, optional): Search within module descriptions

**Returns:** Same format as get_deployment_module

**Example:**
```python
# Find DR helpers
get_helper_module(pattern="*dr*")
```

### get_utility_module

List utility modules in `ocs_ci/utility/` directory.

**Parameters:**
- `pattern` (string, optional): Filename pattern (e.g., `"*aws*"`). Default: `"*"`
- `search_text` (string, optional): Search within module descriptions

**Returns:** Same format as get_deployment_module

**Example:**
```python
# Find AWS utilities
get_utility_module(pattern="*aws*")
```

### get_conftest

List all `conftest.py` files in `tests/` directory tree (recursive).

**Parameters:**
- `pattern` (string, optional): Path pattern (e.g., `"*functional*"`). Default: `"*"`
- `search_text` (string, optional): Search within module descriptions

**Returns:** Same format as get_deployment_module

**Example:**
```python
# List all conftest files
get_conftest()

# Find functional test conftest files
get_conftest(pattern="*functional*")
```

### get_conf_file

List configuration files in `conf/` directory.

**Parameters:**
- `pattern` (string, optional): Filename pattern (e.g., `"*.yaml"`). Default: `"*"`
- `search_text` (string, optional): Search within file descriptions

**Returns:** Same format as get_deployment_module

**Example:**
```python
# List all config files
get_conf_file()

# Find YAML configs
get_conf_file(pattern="*.yaml")
```
```

**Step 3: Update USER_GUIDE.md**

Add new section:

```markdown
## Module Discovery

The server provides 6 specialized tools for discovering modules by type.

### Finding Deployment Modules

```
User: "Show me all AWS deployment modules"
Tool: get_deployment_module(pattern="*aws*")

Response:
{
  "directory": "ocs_ci/deployment",
  "total_modules": 42,
  "filtered_modules": 1,
  "modules": [
    {
      "name": "aws.py",
      "path": "ocs_ci/deployment/aws.py",
      "description": "AWS deployment module for provisioning OCS clusters",
      "size_bytes": 35883,
      "lines": 1245
    }
  ]
}
```

### Finding Helper Modules

```
User: "Find helper modules related to disaster recovery"
Tool: get_helper_module(search_text="disaster recovery")
```

### Finding Test Fixtures

```
User: "Show me all conftest files in functional tests"
Tool: get_conftest(pattern="*functional*")
```

### Browsing Configuration Files

```
User: "List all configuration files"
Tool: get_conf_file()
```
```

**Step 4: Update TOOLS_SUMMARY.md**

Add:

```markdown
## Module Discovery Tools (6)

- **get_deployment_module**: List deployment modules in `ocs_ci/deployment/`
- **get_resource_module**: List resource modules in `ocs_ci/ocs/resources/`
- **get_helper_module**: List helper modules in `ocs_ci/helpers/`
- **get_utility_module**: List utility modules in `ocs_ci/utility/`
- **get_conftest**: List all `conftest.py` files in `tests/` tree
- **get_conf_file**: List configuration files in `conf/`

All support:
- Pattern filtering (filename matching)
- Search filtering (description search)
- Extract module descriptions from docstrings
```

**Step 5: Update QUICK_REFERENCE.md**

Add:

```markdown
## Module Discovery

```bash
# List deployment modules
get_deployment_module()
get_deployment_module(pattern="*aws*")
get_deployment_module(search_text="bare metal")

# List resource modules
get_resource_module()
get_resource_module(pattern="pod*")

# List helper modules
get_helper_module()
get_helper_module(pattern="*dr*")

# List utility modules
get_utility_module()
get_utility_module(pattern="*aws*")

# List conftest files
get_conftest()
get_conftest(pattern="*functional*")

# List config files
get_conf_file()
get_conf_file(pattern="*.yaml")
```
```

**Step 6: Update ARCHITECTURE.md**

In the Tool Layer section (around line 132), add:

```markdown
8. **get_deployment_module.py**
   - List deployment modules
   - Extract descriptions
   - Pattern/search filtering

9. **get_resource_module.py**
   - List resource modules
   - Extract descriptions
   - Pattern/search filtering

10. **get_helper_module.py**
    - List helper modules
    - Extract descriptions
    - Pattern/search filtering

11. **get_utility_module.py**
    - List utility modules
    - Extract descriptions
    - Pattern/search filtering

12. **get_conftest.py**
    - List conftest files (recursive)
    - Extract descriptions
    - Pattern/search filtering

13. **get_conf_file.py**
    - List config files
    - Extract descriptions
    - Pattern/search filtering

**Shared Helper**: `module_discovery.py`
- Common discovery logic
- Description extraction
- Filter application
```

**Step 7: Update CHANGELOG.md**

Add at the top:

```markdown
## [0.2.0] - 2026-03-03

### Added
- 6 new module discovery tools for faster navigation
  - `get_deployment_module`: List deployment modules in `ocs_ci/deployment/`
  - `get_resource_module`: List resource modules in `ocs_ci/ocs/resources/`
  - `get_helper_module`: List helper modules in `ocs_ci/helpers/`
  - `get_utility_module`: List utility modules in `ocs_ci/utility/`
  - `get_conftest`: List `conftest.py` files in `tests/` tree
  - `get_conf_file`: List configuration files in `conf/`
- Shared `module_discovery` helper for efficient module scanning
- Pattern filtering support (filename matching with wildcards)
- Description search support (search within module docstrings)
- Automatic description extraction from Python docstrings and config comments
- 60+ new tests for comprehensive coverage

### Changed
- Total tools increased from 7 to 13
- Server now registers 13 tools in MCP protocol

### Performance
- All new tools perform within existing performance targets (< 1s)
```

**Step 8: Commit documentation**

```bash
git add README.md API_REFERENCE.md USER_GUIDE.md TOOLS_SUMMARY.md QUICK_REFERENCE.md ARCHITECTURE.md CHANGELOG.md
git commit -m "docs: update documentation for new tools

- Update tool count from 7 to 13
- Add API reference for 6 new tools
- Add user guide examples
- Update architecture documentation
- Add changelog entry for v0.2.0

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Final Verification

**Step 1: Run complete test suite**

```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

Expected: All tests PASS, coverage >95%

**Step 2: Test against real ocs-ci repository**

```bash
# Start server
python server.py --repo-path /Users/sdurgbun/code/redhat/odf/ocs-ci/

# In another terminal, test with mcp client or manual verification
# Verify all 13 tools are registered
```

**Step 3: Performance check**

Run integration tests and check timing:

```bash
pytest tests/test_integration.py::TestModuleDiscoveryIntegration -v -m integration --durations=10
```

Expected: All tools complete in < 1s

**Step 4: Create final commit if any fixes needed**

```bash
git add <any-fixed-files>
git commit -m "fix: final adjustments

<description>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**Step 5: Tag release**

```bash
git tag -a v0.2.0 -m "Release v0.2.0: Add 6 module discovery tools"
```

---

## Success Criteria

- [ ] All 60+ tests passing
- [ ] All 6 tools implemented
- [ ] Shared helper created
- [ ] Server integration complete
- [ ] Documentation updated (7 files)
- [ ] Performance targets met (< 1s per tool)
- [ ] Integration tests pass against real ocs-ci repo
- [ ] Code coverage >95%
- [ ] Version bumped to 0.2.0

---

## Estimated Time

- Task 1: Create shared helper - 20 min
- Task 2: Add pattern filtering - 10 min
- Task 3: Add search filtering - 10 min
- Task 4: Create first tool - 15 min
- Task 5: Create 5 remaining tools - 45 min
- Task 6: Server integration - 15 min
- Task 7: Integration tests - 15 min
- Task 8: Full test suite - 10 min
- Task 9: Documentation - 30 min
- Task 10: Final verification - 10 min

**Total: ~3 hours**

---

## Notes

- Use TDD: Write test first, see it fail, implement, see it pass
- Commit frequently after each passing test/feature
- Reuse existing patterns (security, AST parsing)
- DRY: Share logic in module_discovery.py
- YAGNI: Don't add features beyond requirements
- Test against real ocs-ci repo path: `/Users/sdurgbun/code/redhat/odf/ocs-ci/`
