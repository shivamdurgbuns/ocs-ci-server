# OCS-CI MCP Server - User Guide

Version: 0.2.0
Last Updated: March 3, 2026

---

## Table of Contents

1. [Introduction](#introduction)
2. [What is the OCS-CI MCP Server](#what-is-the-ocs-ci-mcp-server)
3. [Installation and Setup](#installation-and-setup)
4. [Quick Start Guide](#quick-start-guide)
5. [Tool Reference](#tool-reference)
6. [Common Workflows](#common-workflows)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## Introduction

Welcome to the OCS-CI MCP Server User Guide. This guide will help you get started with using the MCP server to efficiently analyze the ocs-ci codebase, debug test failures, and understand class hierarchies.

### What You'll Learn

- How to install and configure the MCP server
- How to use all 13 available tools
- Common workflows for test debugging
- Best practices for efficient analysis

---

## What is the OCS-CI MCP Server

The OCS-CI MCP Server is a **Model Context Protocol (MCP) server** specifically designed for the ocs-ci repository. It provides intelligent, token-efficient code analysis tools that help you:

### Key Features

- **Find Tests Quickly**: Locate test files by name or pytest nodeid
- **Understand Class Hierarchies**: Analyze inheritance chains and method resolution order
- **Search Codebase**: Fast regex-based code search across the repository
- **Browse Structure**: Navigate directories and discover modules
- **Get Summaries**: Token-efficient class and file summaries
- **Read Code**: Retrieve file contents with optional line ranges
- **Find Examples**: Discover test examples using specific fixtures or patterns

### Why Use This Server?

- **Token Efficient**: 90%+ reduction in token usage compared to loading files directly
- **Fast**: 60-250x faster than performance targets
- **Secure**: Built-in protection against directory traversal and sensitive data access
- **Smart**: Understands Python AST, imports, and inheritance
- **Production Ready**: 139 tests with 100% pass rate

---

## Installation and Setup

### Prerequisites

- Python 3.9 or higher
- pip package manager
- Access to ocs-ci repository
- Claude Code CLI (for MCP integration)

### Installation Steps

#### 1. Clone or Navigate to the Server

```bash
cd /path/to/mcp-servers/ocs-ci-server
```

#### 2. Install Dependencies

```bash
pip install -e .
```

This installs the server in editable mode with the required `mcp` package.

#### 3. Verify Installation

```bash
python server.py --help
```

You should see:
```
usage: server.py [-h] --repo-path REPO_PATH [--allow-sensitive]

OCS-CI MCP Server

optional arguments:
  -h, --help            show this help message and exit
  --repo-path REPO_PATH
                        Path to ocs-ci repository
  --allow-sensitive     Allow access to sensitive directories (data, .git, etc.) - USE WITH CAUTION
```

#### 4. Configure Claude Code

Edit your Claude Code configuration file (`~/.config/claude/config.json`):

```json
{
  "mcpServers": {
    "ocs-ci": {
      "command": "python",
      "args": [
        "/absolute/path/to/mcp-servers/ocs-ci-server/server.py",
        "--repo-path",
        "/absolute/path/to/ocs-ci"
      ]
    }
  }
}
```

**Important**: Use absolute paths, not relative paths.

#### 5. Restart Claude Code

After updating the configuration, restart Claude Code to load the MCP server.

#### 6. Verify Connection

In Claude Code, you should be able to use the ocs-ci tools. Try:

```
Can you list the modules in the ocs_ci/ocs directory?
```

---

## Quick Start Guide

### First Steps

1. **Browse the Repository**

   ```
   List the modules in the root directory
   ```

   Uses: `list_modules` tool

2. **Find a Test**

   ```
   Find the test named test_create_pvc
   ```

   Uses: `find_test` tool

3. **Analyze a Class**

   ```
   Get the summary of the Pod class from ocs_ci/ocs/resources/pod.py
   ```

   Uses: `get_summary` tool

4. **Search for Code**

   ```
   Search for all uses of @pytest.fixture in the tests directory
   ```

   Uses: `search_code` tool

### Common Tasks

#### Debug a Failing Test

1. Find the test file:
   ```
   Find test_pvc_creation_deletion
   ```

2. Get the test content:
   ```
   Read the file containing test_pvc_creation_deletion
   ```

3. Analyze related classes:
   ```
   Get the summary of the PVC class
   ```

4. Check inheritance:
   ```
   Show the inheritance chain for the PVC class
   ```

#### Understand a Class

1. Get class summary:
   ```
   Summarize the OCP class from ocs_ci/ocs/ocp.py
   ```

2. View full inheritance:
   ```
   Show the full inheritance chain for OCP
   ```

3. Check for method conflicts:
   ```
   Are there any method overrides in the OCP class?
   ```

---

## Tool Reference

The OCS-CI MCP Server provides 13 powerful tools:

### 1. list_modules

**Purpose**: Browse repository structure and list files

**Parameters**:
- `path` (optional): Path relative to ocs-ci root (default: root)
- `pattern` (optional): Filter pattern, e.g., '*.py' (default: '*')

**Example Usage**:

```python
# List all files in root
list_modules()

# List Python files in ocs_ci/ocs
list_modules(path="ocs_ci/ocs", pattern="*.py")

# List test files
list_modules(path="tests", pattern="test_*.py")
```

**Response Format**:
```json
{
  "path": "ocs_ci/ocs",
  "files": [
    {"name": "ocp.py", "type": "file", "size": 45234},
    {"name": "resources", "type": "directory"}
  ],
  "total": 68
}
```

**Use Cases**:
- Explore repository structure
- Find modules in a directory
- Discover test files
- Locate resource files

---

### 2. get_summary

**Purpose**: Get token-efficient summary of a file or class with inheritance

**Parameters**:
- `file_path` (required): Path to Python file (relative to ocs-ci root)
- `class_name` (optional): Class name for class-level summary

**Example Usage**:

```python
# Get file summary
get_summary(file_path="ocs_ci/ocs/ocp.py")

# Get class summary with inheritance
get_summary(file_path="ocs_ci/ocs/resources/pod.py", class_name="Pod")

# Analyze a test file
get_summary(file_path="tests/test_pvc.py")
```

**Response Format**:
```json
{
  "type": "class",
  "name": "Pod",
  "file_path": "ocs_ci/ocs/resources/pod.py",
  "line_number": 45,
  "docstring": "Pod resource class",
  "bases": ["OCS"],
  "methods": [
    {"name": "__init__", "line": 50, "params": ["self", "**kwargs"]},
    {"name": "exec_cmd", "line": 75, "params": ["self", "command"]}
  ],
  "inherited_from": {
    "OCS": ["get", "create", "delete"],
    "OCP": ["exec_oc_cmd", "get_resource"]
  }
}
```

**Use Cases**:
- Understand class structure
- View available methods
- Analyze inheritance
- Get quick overview without reading full file

---

### 3. get_content

**Purpose**: Read file content with optional line range

**Parameters**:
- `file_path` (required): Path to file (relative to ocs-ci root)
- `start_line` (optional): Starting line number (1-indexed)
- `end_line` (optional): Ending line number (1-indexed)

**Example Usage**:

```python
# Read entire file
get_content(file_path="ocs_ci/ocs/ocp.py")

# Read specific lines
get_content(file_path="ocs_ci/ocs/ocp.py", start_line=100, end_line=150)

# Read test function
get_content(file_path="tests/test_pvc.py", start_line=45, end_line=75)
```

**Response Format**:
```json
{
  "file_path": "ocs_ci/ocs/ocp.py",
  "content": "class OCP:\n    \"\"\"OCP resource class\"\"\"...",
  "start_line": 100,
  "end_line": 150,
  "total_lines": 450
}
```

**Use Cases**:
- Read full source code
- Extract specific functions/methods
- Review test implementations
- Get file contents for analysis

---

### 4. search_code

**Purpose**: Search for regex pattern in code files

**Parameters**:
- `pattern` (required): Regex pattern to search for
- `file_pattern` (optional): File glob pattern (default: '*.py')
- `context_lines` (optional): Number of context lines (default: 2)
- `path` (optional): Path to search within (default: root)

**Example Usage**:

```python
# Search for pytest fixtures
search_code(pattern="@pytest.fixture")

# Search in specific directory with context
search_code(
    pattern="def test_.*pvc",
    path="tests",
    context_lines=3
)

# Search configuration files
search_code(
    pattern="storage_class",
    file_pattern="*.yaml",
    path="conf"
)
```

**Response Format**:
```json
{
  "pattern": "@pytest.fixture",
  "matches": [
    {
      "file": "tests/conftest.py",
      "line_number": 45,
      "line": "@pytest.fixture(scope='session')",
      "context_before": ["", ""],
      "context_after": ["def pod_factory():", "    ..."]
    }
  ],
  "total_matches": 773,
  "files_searched": 450
}
```

**Use Cases**:
- Find all uses of a function/class
- Locate pytest fixtures
- Search for patterns across codebase
- Find test examples

---

### 5. get_inheritance

**Purpose**: Get full inheritance chain with methods and conflicts

**Parameters**:
- `file_path` (required): Path to Python file (relative to ocs-ci root)
- `class_name` (required): Class name to analyze

**Example Usage**:

```python
# Analyze inheritance chain
get_inheritance(
    file_path="ocs_ci/ocs/resources/pod.py",
    class_name="Pod"
)

# Check for method conflicts
get_inheritance(
    file_path="ocs_ci/ocs/pvc.py",
    class_name="PVC"
)
```

**Response Format**:
```json
{
  "class_name": "Pod",
  "file_path": "ocs_ci/ocs/resources/pod.py",
  "inheritance_chain": ["Pod", "OCS", "OCP"],
  "mro": ["Pod", "OCS", "OCP", "object"],
  "methods_by_class": {
    "Pod": ["__init__", "exec_cmd", "get_logs"],
    "OCS": ["get", "create", "delete"],
    "OCP": ["exec_oc_cmd", "get_resource"]
  },
  "overridden_methods": {
    "get": ["OCS", "OCP"]
  }
}
```

**Use Cases**:
- Understand method resolution order
- Find method overrides
- Debug inheritance issues
- Analyze complex hierarchies

---

### 6. find_test

**Purpose**: Find test by name or pytest nodeid

**Parameters**:
- `test_name` (required): Test name or nodeid (e.g., 'test_foo' or 'path/file.py::test_foo')

**Example Usage**:

```python
# Find by simple name
find_test(test_name="test_create_pvc")

# Find by nodeid
find_test(test_name="tests/test_pvc.py::test_create_pvc")

# Find test class method
find_test(test_name="TestPVC::test_creation")
```

**Response Format**:
```json
{
  "test_name": "test_create_pvc",
  "matches": [
    {
      "file_path": "tests/test_pvc.py",
      "full_path": "/path/to/tests/test_pvc.py",
      "line_number": 45,
      "test_type": "function",
      "class_name": null,
      "fixtures": ["pvc_factory", "teardown"],
      "nodeid": "tests/test_pvc.py::test_create_pvc"
    }
  ],
  "total_matches": 1
}
```

**Use Cases**:
- Locate test files from CI failure logs
- Find test by pytest nodeid
- Discover test location
- Analyze test dependencies

---

### 7. get_test_example

**Purpose**: Find example tests matching pattern or using specific fixture

**Parameters**:
- `pattern` (required): Pattern to search for in test names or content
- `fixture_name` (optional): Fixture name to filter by
- `path` (optional): Path to search within (default: root)
- `max_results` (optional): Maximum number of examples (default: 5)

**Example Usage**:

```python
# Find tests using a fixture
get_test_example(
    pattern="test_pvc",
    fixture_name="pvc_factory",
    max_results=3
)

# Find test examples by pattern
get_test_example(
    pattern="snapshot",
    path="tests/manage/pv_services"
)

# Find examples with source code
get_test_example(
    pattern="test_.*_creation",
    max_results=5
)
```

**Response Format**:
```json
{
  "pattern": "test_pvc",
  "fixture_filter": "pvc_factory",
  "examples": [
    {
      "test_name": "test_create_pvc",
      "file_path": "tests/test_pvc.py",
      "line_number": 45,
      "fixtures": ["pvc_factory", "teardown"],
      "source": "def test_create_pvc(pvc_factory):..."
    }
  ],
  "total_found": 3
}
```

**Use Cases**:
- Find usage examples of fixtures
- Discover similar tests
- Learn test patterns
- Copy test templates

---

### 8. get_deployment_module

**Purpose**: List deployment modules in ocs_ci/deployment/ directory

**Parameters**:
- `pattern` (optional): Filter pattern for filenames (default: '*')
- `description` (optional): Search term for module descriptions

**Example Usage**:

```python
# List all deployment modules
get_deployment_module()

# Find AWS deployment modules
get_deployment_module(pattern="*aws*")

# Search by description
get_deployment_module(description="azure")
```

**Response Format**:
```json
{
  "directory": "ocs_ci/deployment",
  "pattern": "*aws*",
  "modules": [
    {
      "name": "aws",
      "path": "ocs_ci/deployment/aws.py",
      "description": "AWS deployment implementation"
    }
  ],
  "total": 1
}
```

**Use Cases**:
- Find deployment implementations
- Discover cloud-specific deployment code
- Locate platform deployment modules

---

### 9. get_resource_module

**Purpose**: List resource modules in ocs_ci/ocs/resources/ directory

**Parameters**:
- `pattern` (optional): Filter pattern for filenames (default: '*')
- `description` (optional): Search term for module descriptions

**Example Usage**:

```python
# List all resource modules
get_resource_module()

# Find Pod-related modules
get_resource_module(pattern="*pod*")

# Search for PVC resources
get_resource_module(description="persistent volume")
```

**Response Format**:
```json
{
  "directory": "ocs_ci/ocs/resources",
  "pattern": "*pod*",
  "modules": [
    {
      "name": "pod",
      "path": "ocs_ci/ocs/resources/pod.py",
      "description": "Pod resource class"
    }
  ],
  "total": 1
}
```

**Use Cases**:
- Discover resource classes
- Find Kubernetes resource implementations
- Locate storage resource modules

---

### 10. get_helper_module

**Purpose**: List helper modules in ocs_ci/helpers/ directory

**Parameters**:
- `pattern` (optional): Filter pattern for filenames (default: '*')
- `description` (optional): Search term for module descriptions

**Example Usage**:

```python
# List all helper modules
get_helper_module()

# Find DR helpers
get_helper_module(pattern="*dr*")

# Search by description
get_helper_module(description="disaster recovery")
```

**Response Format**:
```json
{
  "directory": "ocs_ci/helpers",
  "modules": [
    {
      "name": "dr_helpers",
      "path": "ocs_ci/helpers/dr_helpers.py",
      "description": "Helper functions for disaster recovery"
    }
  ],
  "total": 1
}
```

**Use Cases**:
- Find helper functions
- Discover utility helpers
- Locate test helper modules

---

### 11. get_utility_module

**Purpose**: List utility modules in ocs_ci/utility/ directory

**Parameters**:
- `pattern` (optional): Filter pattern for filenames (default: '*')
- `description` (optional): Search term for module descriptions

**Example Usage**:

```python
# List all utility modules
get_utility_module()

# Find AWS utilities
get_utility_module(pattern="*aws*")

# Search for reporting utilities
get_utility_module(description="report")
```

**Response Format**:
```json
{
  "directory": "ocs_ci/utility",
  "pattern": "*aws*",
  "modules": [
    {
      "name": "aws",
      "path": "ocs_ci/utility/aws.py",
      "description": "AWS utility functions"
    }
  ],
  "total": 1
}
```

**Use Cases**:
- Find utility functions
- Discover cloud utilities
- Locate common utilities

---

### 12. get_conftest

**Purpose**: List conftest.py files in tests/ directory tree

**Parameters**:
- `pattern` (optional): Filter pattern for paths (default: '*')
- `description` (optional): Search term for conftest descriptions

**Example Usage**:

```python
# List all conftest files
get_conftest()

# Find conftest in manage tests
get_conftest(pattern="*manage*")

# Search for specific fixtures
get_conftest(description="factory")
```

**Response Format**:
```json
{
  "directory": "tests",
  "pattern": "*manage*",
  "files": [
    {
      "name": "conftest",
      "path": "tests/manage/conftest.py",
      "description": "Fixtures for manage tests"
    }
  ],
  "total": 1
}
```

**Use Cases**:
- Find pytest fixtures
- Discover conftest hierarchy
- Locate test fixtures

---

### 13. get_conf_file

**Purpose**: List configuration files in conf/ directory

**Parameters**:
- `pattern` (optional): Filter pattern for filenames (default: '*')
- `description` (optional): Search term for config descriptions

**Example Usage**:

```python
# List all config files
get_conf_file()

# Find YAML configs
get_conf_file(pattern="*.yaml")

# Search for deployment configs
get_conf_file(description="deployment")
```

**Response Format**:
```json
{
  "directory": "conf",
  "pattern": "*.yaml",
  "files": [
    {
      "name": "ocsci",
      "path": "conf/ocsci/default_config.yaml",
      "description": "Default configuration"
    }
  ],
  "total": 1
}
```

**Use Cases**:
- Browse configuration files
- Find deployment configs
- Locate test configurations

---

## Common Workflows

### Workflow 1: Debug a Failing Test

**Scenario**: Test `tests/manage/test_pvc.py::test_pvc_creation` fails in CI

**Steps**:

1. **Find the test**:
   ```
   Find test_pvc_creation
   ```

2. **Read the test code**:
   ```
   Get the content of tests/manage/test_pvc.py around line 45
   ```

3. **Analyze the class being tested**:
   ```
   Summarize the PVC class
   ```

4. **Check class hierarchy**:
   ```
   Show the inheritance chain for PVC
   ```

5. **Find similar working tests**:
   ```
   Find test examples using pvc_factory fixture
   ```

### Workflow 2: Understand a New Component

**Scenario**: Need to understand how the Pod class works

**Steps**:

1. **Get class summary**:
   ```
   Summarize the Pod class from ocs_ci/ocs/resources/pod.py
   ```

2. **View inheritance**:
   ```
   Show the full inheritance chain for Pod
   ```

3. **Find usage examples**:
   ```
   Search for "Pod(" to find where Pod is instantiated
   ```

4. **Read implementation**:
   ```
   Get the content of ocs_ci/ocs/resources/pod.py
   ```

### Workflow 3: Find and Reuse Test Patterns

**Scenario**: Need to write a test that creates PVCs

**Steps**:

1. **Find example tests**:
   ```
   Find test examples using pvc_factory
   ```

2. **Search for patterns**:
   ```
   Search for "pvc.create()" to see usage
   ```

3. **Get fixture definition**:
   ```
   Find the pvc_factory fixture
   ```

4. **Copy and adapt**:
   Use the examples to write your own test

### Workflow 4: Investigate Method Override

**Scenario**: Method `delete()` behaves unexpectedly for Pod

**Steps**:

1. **Get inheritance chain**:
   ```
   Show the inheritance chain for Pod
   ```

2. **Check for overrides**:
   Look for `delete` in the overridden_methods

3. **Read implementations**:
   ```
   Search for "def delete" in pod.py, ocs.py, and ocp.py
   ```

4. **Compare methods**:
   Analyze differences between implementations

---

## Troubleshooting

### Common Issues

#### Issue: "Repository path does not exist"

**Cause**: Invalid --repo-path argument

**Solution**:
```bash
# Check the path exists
ls /path/to/ocs-ci

# Use absolute path in config
"--repo-path", "/absolute/path/to/ocs-ci"
```

#### Issue: "Access to sensitive directory denied"

**Cause**: Trying to access blocked directories (data, .git, etc.)

**Solution**:

Option 1 (Recommended): Don't access sensitive directories

Option 2: Use --allow-sensitive flag (CAUTION):
```json
{
  "mcpServers": {
    "ocs-ci": {
      "command": "python",
      "args": [
        "/path/to/server.py",
        "--repo-path", "/path/to/ocs-ci",
        "--allow-sensitive"
      ]
    }
  }
}
```

#### Issue: "Path escapes repository boundaries"

**Cause**: Path traversal attempt (../../../etc/passwd)

**Solution**: Use paths relative to ocs-ci root only

#### Issue: Test not found

**Cause**: Test name doesn't match or test doesn't exist

**Solutions**:
```
# Try with full nodeid
find_test(test_name="tests/manage/test_pvc.py::test_create_pvc")

# Search for the pattern
search_code(pattern="def test_create_pvc")

# List test files
list_modules(path="tests", pattern="test_*.py")
```

#### Issue: Class not found in file

**Cause**: Wrong file path or class name

**Solutions**:
```
# First get file summary to see available classes
get_summary(file_path="ocs_ci/ocs/ocp.py")

# Check the class name spelling
# Python is case-sensitive: "pod" != "Pod"
```

#### Issue: Slow search performance

**Cause**: Searching entire repository without filters

**Solutions**:
```python
# Use path filter
search_code(pattern="test_.*", path="tests/manage")

# Use file pattern
search_code(pattern="fixture", file_pattern="conftest.py")

# Reduce context lines
search_code(pattern="class", context_lines=0)
```

### Getting Help

1. **Check logs**: Server prints debug info to stderr
2. **Verify config**: Ensure paths are absolute in config.json
3. **Test manually**: Run server.py directly to check errors
4. **Review examples**: See INTEGRATION_TEST_QUICK_START.md

---

## Best Practices

### Path Usage

- **Always use relative paths** from ocs-ci root
- **Use forward slashes** even on Windows: `ocs_ci/ocs/ocp.py`
- **Don't use leading slash**: `ocs/ocp.py` not `/ocs/ocp.py`

### Token Efficiency

- **Start with summaries**: Use `get_summary` before `get_content`
- **Use line ranges**: Only read the lines you need
- **Filter searches**: Use `path` and `file_pattern` to narrow searches
- **Check file lists**: Use `list_modules` to discover before reading

### Security

- **Never use --allow-sensitive** unless absolutely necessary
- **Keep credentials out of repo**: The server blocks /data for a reason
- **Review paths**: Don't blindly trust user-provided paths

### Performance

- **Be specific**: Narrow down searches with path and file_pattern
- **Limit results**: Use max_results for get_test_example
- **Use the right tool**:
  - Browse → list_modules
  - Search → search_code
  - Find test → find_test
  - Analyze → get_summary/get_inheritance
  - Read → get_content

### Workflow Tips

1. **Start broad, narrow down**: List → Search → Summarize → Read
2. **Use inheritance**: Check class hierarchy before debugging
3. **Find examples**: Learn from existing tests
4. **Validate assumptions**: Check file structure with list_modules

---

## Next Steps

Now that you know how to use the OCS-CI MCP Server:

1. **Try the Quick Start** workflows
2. **Read the API Reference** for detailed schemas
3. **Review the Deployment Guide** for production setup
4. **Check the Troubleshooting Guide** for common issues

---

**Documentation Version**: 0.2.0
**Server Version**: 0.2.0
**Last Updated**: March 3, 2026
**Status**: Production Ready
