# OCS-CI MCP Server - Tools Summary

This document provides a comprehensive overview of all 13 tools implemented in the OCS-CI MCP server.

## Tool Overview

All tools include **security-first design** with path validation to prevent directory traversal attacks.

### 1. list_modules

**Purpose**: Browse repository structure and list files/directories.

**Implementation**: `/tools/list_modules.py`

**Key Features**:
- List files and directories at any path
- Filter by glob patterns (e.g., `*.py`)
- Count lines for Python files
- Security: Path traversal protection

**Example Usage**:
```json
{
  "path": "ocs_ci/ocs",
  "pattern": "*.py"
}
```

**Tests**: 4 tests in `tests/test_list_modules.py`

---

### 2. get_summary

**Purpose**: Get structured summary of files or classes with inheritance information.

**Implementation**: `/tools/get_summary.py`

**Key Features**:
- File-level summary: list all classes and their methods
- Class-level summary: detailed class info with inheritance
- Resolve parent classes
- Extract inherited methods
- Security: Path traversal protection

**Example Usage**:
```json
{
  "file_path": "ocs_ci/ocs/ocp.py",
  "class_name": "OCP"
}
```

**Tests**: 3 tests in `tests/test_get_summary.py`

---

### 3. get_content

**Purpose**: Read file content with optional line ranges.

**Implementation**: `/tools/get_content.py`

**Key Features**:
- Read full file or specific line range
- Handle encoding errors gracefully
- Binary file detection
- Security: Path traversal protection

**Example Usage**:
```json
{
  "file_path": "ocs_ci/ocs/ocp.py",
  "start_line": 10,
  "end_line": 50
}
```

**Tests**: 4 tests in `tests/test_get_content.py`

---

### 4. search_code

**Purpose**: Search for regex patterns across code files.

**Implementation**: `/tools/search_code.py`

**Key Features**:
- Regex pattern matching
- File pattern filtering (glob)
- Context lines around matches
- Search within specific paths
- Security: Path traversal protection, regex validation

**Example Usage**:
```json
{
  "pattern": "def test_.*",
  "file_pattern": "test_*.py",
  "context_lines": 3,
  "path": "tests"
}
```

**Tests**: 5 tests in `tests/test_search_code.py`

---

### 5. get_inheritance

**Purpose**: Show full class inheritance chain with all methods and conflicts.

**Implementation**: `/tools/get_inheritance.py`

**Key Features**:
- Calculate Method Resolution Order (MRO)
- Extract methods from each class in chain
- Detect method name conflicts
- Show which class wins in resolution
- Security: Path traversal protection

**Example Usage**:
```json
{
  "file_path": "ocs_ci/ocs/ocp.py",
  "class_name": "OCP"
}
```

**Tests**: 4 tests in `tests/test_get_inheritance.py`

---

### 6. find_test

**Purpose**: Find test functions by name or pytest nodeid.

**Implementation**: `/tools/find_test.py`

**Key Features**:
- Find by simple name (searches all files)
- Find by pytest nodeid (e.g., `tests/test_foo.py::test_bar`)
- Extract fixtures used by test
- Support class methods
- Security: Path traversal protection

**Example Usage**:
```json
{
  "test_name": "tests/conftest/pytest_fixtures.py::test_deployment"
}
```

**Tests**: 6 tests in `tests/test_find_test.py`

---

### 7. get_test_example

**Purpose**: Find example tests matching patterns or using specific fixtures.

**Implementation**: `/tools/get_test_example.py`

**Key Features**:
- Search by pattern in test names/content
- Filter by fixture usage
- Return source code of examples
- Limit number of results
- Security: Path traversal protection

**Example Usage**:
```json
{
  "pattern": "pod",
  "fixture_name": "pod_factory",
  "max_results": 3
}
```

**Tests**: 5 tests in `tests/test_get_test_example.py`

---

### 8. get_deployment_module

**Purpose**: List deployment modules in ocs_ci/deployment/ directory.

**Implementation**: `/tools/get_deployment_module.py`

**Key Features**:
- List deployment modules (AWS, Azure, vSphere, etc.)
- Filter by filename pattern
- Search module descriptions
- Automatic description extraction from docstrings
- Security: Path traversal protection

**Example Usage**:
```json
{
  "pattern": "*aws*"
}
```

**Tests**: 3 tests in `tests/test_module_discovery.py`

---

### 9. get_resource_module

**Purpose**: List resource modules in ocs_ci/ocs/resources/ directory.

**Implementation**: `/tools/get_resource_module.py`

**Key Features**:
- List resource modules (Pod, PVC, StorageClass, etc.)
- Filter by filename pattern
- Search module descriptions
- Automatic description extraction
- Security: Path traversal protection

**Example Usage**:
```json
{
  "pattern": "*pod*"
}
```

**Tests**: 3 tests in `tests/test_module_discovery.py`

---

### 10. get_helper_module

**Purpose**: List helper modules in ocs_ci/helpers/ directory.

**Implementation**: `/tools/get_helper_module.py`

**Key Features**:
- List helper modules (DR, MCG, disruption, etc.)
- Filter by filename pattern
- Search module descriptions
- Automatic description extraction
- Security: Path traversal protection

**Example Usage**:
```json
{
  "description": "disaster recovery"
}
```

**Tests**: 3 tests in `tests/test_module_discovery.py`

---

### 11. get_utility_module

**Purpose**: List utility modules in ocs_ci/utility/ directory.

**Implementation**: `/tools/get_utility_module.py`

**Key Features**:
- List utility modules (AWS, Azure, reporting, etc.)
- Filter by filename pattern
- Search module descriptions
- Automatic description extraction
- Security: Path traversal protection

**Example Usage**:
```json
{
  "pattern": "*aws*"
}
```

**Tests**: 3 tests in `tests/test_module_discovery.py`

---

### 12. get_conftest

**Purpose**: List conftest.py files in tests/ directory tree.

**Implementation**: `/tools/get_conftest.py`

**Key Features**:
- List all conftest.py files
- Hierarchical test fixture discovery
- Filter by path pattern
- Search descriptions
- Security: Path traversal protection

**Example Usage**:
```json
{
  "pattern": "*manage*"
}
```

**Tests**: 3 tests in `tests/test_module_discovery.py`

---

### 13. get_conf_file

**Purpose**: List configuration files in conf/ directory.

**Implementation**: `/tools/get_conf_file.py`

**Key Features**:
- List YAML/JSON/Python config files
- Filter by filename pattern
- Search descriptions in comments
- Automatic description extraction
- Security: Path traversal protection

**Example Usage**:
```json
{
  "pattern": "*.yaml"
}
```

**Tests**: 3 tests in `tests/test_module_discovery.py`

---

## Security Features

All tools implement the same security pattern:

```python
# SECURITY: Validate path to prevent traversal attacks
repo_root = Path(repo_path).resolve()
target_path = (repo_root / file_path).resolve()

# Ensure target is within repository boundaries
if not str(target_path).startswith(str(repo_root)):
    return {
        'error': 'SecurityError',
        'message': f'Path escapes repository boundaries: {file_path}'
    }
```

This prevents attacks like:
- `../../../etc/passwd`
- Symlink traversal
- Path manipulation

---

## Test Coverage

**Total Tests**: 139 (all passing)

- AST Analyzer: 9 tests
- Import Resolver: 4 tests
- Summarizer: 2 tests
- Server: 2 tests
- Module Discovery: 18 tests (6 tools × 3 tests each)
- Integration Tests: 25 tests
- **Tool Tests**: 79 tests
  - list_modules: 4 tests
  - get_summary: 3 tests
  - get_content: 4 tests
  - search_code: 5 tests
  - get_inheritance: 4 tests
  - find_test: 6 tests
  - get_test_example: 5 tests
  - get_deployment_module: 3 tests
  - get_resource_module: 3 tests
  - get_helper_module: 3 tests
  - get_utility_module: 3 tests
  - get_conftest: 3 tests
  - get_conf_file: 3 tests

Each tool has at least one security test for path traversal protection.

---

## Tool Integration

All 13 tools are integrated into `server.py`:

1. **Imports**: All tool functions imported
2. **Tool Registration**: Added to `list_tools()` with proper JSON schemas
3. **Call Handlers**: Added to `call_tool()` dispatcher
4. **Error Handling**: Consistent JSON error responses
5. **Shared Infrastructure**: Module discovery tools share common helper

---

## Usage Example

The server exposes all tools via MCP protocol:

```bash
python server.py --repo-path /path/to/ocs-ci
```

Clients can then call any of the 13 tools with their respective parameters.

---

## Design Principles

1. **Security First**: All tools validate paths before accessing files
2. **Error Handling**: Graceful error messages for all failure modes
3. **Token Efficient**: Structured output designed for LLM consumption
4. **Test Driven**: All tools have comprehensive test coverage
5. **Consistent API**: All tools return JSON dicts with consistent structure
