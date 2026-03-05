# OCS-CI MCP Server - API Reference

Version: 0.2.0
Last Updated: March 3, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [MCP Protocol](#mcp-protocol)
3. [Tool Schemas](#tool-schemas)
4. [Response Formats](#response-formats)
5. [Error Codes](#error-codes)
6. [Examples](#examples)

---

## Overview

The OCS-CI MCP Server exposes 13 tools via the Model Context Protocol (MCP). Each tool accepts structured input and returns JSON-formatted responses.

### Protocol Version

- **MCP Version**: 0.9.0+
- **Server Version**: 0.2.0
- **Protocol**: stdio (standard input/output)

### Base Configuration

```json
{
  "command": "python",
  "args": [
    "/path/to/server.py",
    "--repo-path", "/path/to/ocs-ci",
    "--allow-sensitive"  // Optional, dangerous
  ]
}
```

---

## MCP Protocol

### Server Capabilities

```json
{
  "capabilities": {
    "tools": {
      "listTools": true,
      "callTool": true
    }
  }
}
```

### Tool Discovery

**Request**: `tools/list`

**Response**:
```json
{
  "tools": [
    {
      "name": "list_modules",
      "description": "List files and directories in ocs-ci repository",
      "inputSchema": { ... }
    },
    ...
  ]
}
```

### Tool Invocation

**Request**: `tools/call`

```json
{
  "name": "list_modules",
  "arguments": {
    "path": "ocs_ci/ocs",
    "pattern": "*.py"
  }
}
```

**Response**:
```json
{
  "content": [
    {
      "type": "text",
      "text": "{...json response...}"
    }
  ]
}
```

---

## Tool Schemas

### 1. list_modules

**Description**: List files and directories in ocs-ci repository

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Path relative to ocs-ci root (default: root)",
      "default": ""
    },
    "pattern": {
      "type": "string",
      "description": "Filter pattern (e.g., '*.py')",
      "default": "*"
    }
  }
}
```

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| path | string | No | "" | Path relative to ocs-ci root |
| pattern | string | No | "*" | Glob pattern filter |

**Example Input**:
```json
{
  "path": "ocs_ci/ocs",
  "pattern": "*.py"
}
```

**Example Output**:
```json
{
  "path": "ocs_ci/ocs",
  "pattern": "*.py",
  "files": [
    {
      "name": "ocp.py",
      "type": "file",
      "size": 45234
    },
    {
      "name": "resources",
      "type": "directory"
    }
  ],
  "total": 68
}
```

**Security Notes**:
- Blocks access to sensitive directories unless --allow-sensitive
- Prevents path traversal attacks
- Returns relative paths only

---

### 2. get_summary

**Description**: Get summary of Python file or class with inheritance

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "file_path": {
      "type": "string",
      "description": "Path to Python file (relative to ocs-ci root)"
    },
    "class_name": {
      "type": "string",
      "description": "Class name (optional, for class-level summary)"
    }
  },
  "required": ["file_path"]
}
```

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| file_path | string | Yes | - | Path to Python file |
| class_name | string | No | null | Class name for class summary |

**Example Input**:
```json
{
  "file_path": "ocs_ci/ocs/resources/pod.py",
  "class_name": "Pod"
}
```

**Example Output** (Class Summary):
```json
{
  "type": "class",
  "name": "Pod",
  "file_path": "ocs_ci/ocs/resources/pod.py",
  "line_number": 45,
  "docstring": "Pod resource class for managing Kubernetes pods",
  "bases": ["OCS"],
  "methods": [
    {
      "name": "__init__",
      "line": 50,
      "params": ["self", "**kwargs"],
      "docstring": "Initialize Pod resource"
    },
    {
      "name": "exec_cmd",
      "line": 75,
      "params": ["self", "command", "timeout=60"],
      "docstring": "Execute command in pod"
    }
  ],
  "inherited_from": {
    "OCS": ["get", "create", "delete", "reload"],
    "OCP": ["exec_oc_cmd", "get_resource", "apply"]
  },
  "attributes": [
    {"name": "name", "line": 55},
    {"name": "namespace", "line": 56}
  ]
}
```

**Example Output** (File Summary):
```json
{
  "type": "file",
  "file_path": "ocs_ci/ocs/ocp.py",
  "classes": [
    {
      "name": "OCP",
      "line": 20,
      "bases": [],
      "methods": ["__init__", "exec_oc_cmd", "get_resource"],
      "docstring": "Base OCP resource class"
    }
  ],
  "functions": [
    {
      "name": "get_all_pods",
      "line": 250,
      "params": ["namespace"],
      "docstring": "Get all pods in namespace"
    }
  ],
  "imports": [
    "from kubernetes import client",
    "import subprocess"
  ]
}
```

---

### 3. get_content

**Description**: Read file content with optional line range

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "file_path": {
      "type": "string",
      "description": "Path to file (relative to ocs-ci root)"
    },
    "start_line": {
      "type": "integer",
      "description": "Starting line number (1-indexed, optional)"
    },
    "end_line": {
      "type": "integer",
      "description": "Ending line number (1-indexed, optional)"
    }
  },
  "required": ["file_path"]
}
```

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| file_path | string | Yes | - | Path to file |
| start_line | integer | No | 1 | Starting line (1-indexed) |
| end_line | integer | No | EOF | Ending line (1-indexed) |

**Example Input**:
```json
{
  "file_path": "ocs_ci/ocs/ocp.py",
  "start_line": 100,
  "end_line": 150
}
```

**Example Output**:
```json
{
  "file_path": "ocs_ci/ocs/ocp.py",
  "content": "class OCP:\n    \"\"\"OCP resource class\"\"\"...",
  "start_line": 100,
  "end_line": 150,
  "total_lines": 450,
  "lines_returned": 51
}
```

---

### 4. search_code

**Description**: Search for regex pattern in code files

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "pattern": {
      "type": "string",
      "description": "Regex pattern to search for"
    },
    "file_pattern": {
      "type": "string",
      "description": "File glob pattern (default: '*.py')",
      "default": "*.py"
    },
    "context_lines": {
      "type": "integer",
      "description": "Number of context lines (default: 2)",
      "default": 2
    },
    "path": {
      "type": "string",
      "description": "Path to search within (default: root)",
      "default": ""
    }
  },
  "required": ["pattern"]
}
```

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| pattern | string | Yes | - | Regex pattern |
| file_pattern | string | No | "*.py" | File glob filter |
| context_lines | integer | No | 2 | Lines before/after match |
| path | string | No | "" | Directory to search |

**Example Input**:
```json
{
  "pattern": "@pytest\\.fixture",
  "file_pattern": "*.py",
  "context_lines": 2,
  "path": "tests"
}
```

**Example Output**:
```json
{
  "pattern": "@pytest\\.fixture",
  "path": "tests",
  "file_pattern": "*.py",
  "matches": [
    {
      "file": "tests/conftest.py",
      "line_number": 45,
      "line": "@pytest.fixture(scope='session')",
      "context_before": [
        "",
        ""
      ],
      "context_after": [
        "def pod_factory():",
        "    \"\"\"Create Pod instances\"\"\""
      ]
    }
  ],
  "total_matches": 773,
  "files_searched": 120
}
```

---

### 5. get_inheritance

**Description**: Get full inheritance chain with methods and conflicts

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "file_path": {
      "type": "string",
      "description": "Path to Python file (relative to ocs-ci root)"
    },
    "class_name": {
      "type": "string",
      "description": "Class name to analyze"
    }
  },
  "required": ["file_path", "class_name"]
}
```

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| file_path | string | Yes | - | Path to Python file |
| class_name | string | Yes | - | Class to analyze |

**Example Input**:
```json
{
  "file_path": "ocs_ci/ocs/resources/pod.py",
  "class_name": "Pod"
}
```

**Example Output**:
```json
{
  "class_name": "Pod",
  "file_path": "ocs_ci/ocs/resources/pod.py",
  "inheritance_chain": ["Pod", "OCS", "OCP"],
  "mro": ["Pod", "OCS", "OCP", "object"],
  "methods_by_class": {
    "Pod": [
      {"name": "__init__", "line": 50},
      {"name": "exec_cmd", "line": 75},
      {"name": "get_logs", "line": 100}
    ],
    "OCS": [
      {"name": "get", "line": 30},
      {"name": "create", "line": 45},
      {"name": "delete", "line": 60}
    ],
    "OCP": [
      {"name": "exec_oc_cmd", "line": 25},
      {"name": "get_resource", "line": 50}
    ]
  },
  "overridden_methods": {
    "get": {
      "defined_in": ["OCS", "OCP"],
      "resolution": "OCS"
    }
  },
  "all_methods": [
    "exec_cmd", "get_logs", "__init__",
    "get", "create", "delete",
    "exec_oc_cmd", "get_resource"
  ]
}
```

---

### 6. find_test

**Description**: Find test by name or pytest nodeid

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "test_name": {
      "type": "string",
      "description": "Test name or nodeid (e.g., 'test_foo' or 'path/file.py::test_foo')"
    }
  },
  "required": ["test_name"]
}
```

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| test_name | string | Yes | - | Test name or nodeid |

**Example Input**:
```json
{
  "test_name": "test_create_pvc"
}
```

**Example Output**:
```json
{
  "test_name": "test_create_pvc",
  "matches": [
    {
      "file_path": "tests/manage/test_pvc.py",
      "full_path": "/abs/path/tests/manage/test_pvc.py",
      "line_number": 45,
      "test_type": "function",
      "class_name": null,
      "fixtures": ["pvc_factory", "teardown_factory"],
      "nodeid": "tests/manage/test_pvc.py::test_create_pvc",
      "markers": ["tier1", "polarion_id"],
      "docstring": "Test PVC creation and validation"
    }
  ],
  "total_matches": 1
}
```

**Test Types**:
- `function`: Standalone test function
- `method`: Test method in a class

---

### 7. get_test_example

**Description**: Find example tests matching pattern or using specific fixture

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "pattern": {
      "type": "string",
      "description": "Pattern to search for in test names or content"
    },
    "fixture_name": {
      "type": "string",
      "description": "Fixture name to filter by (optional)"
    },
    "path": {
      "type": "string",
      "description": "Path to search within (default: root)",
      "default": ""
    },
    "max_results": {
      "type": "integer",
      "description": "Maximum number of examples (default: 5)",
      "default": 5
    }
  },
  "required": ["pattern"]
}
```

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| pattern | string | Yes | - | Search pattern |
| fixture_name | string | No | null | Fixture filter |
| path | string | No | "" | Directory to search |
| max_results | integer | No | 5 | Maximum examples |

**Example Input**:
```json
{
  "pattern": "test_pvc",
  "fixture_name": "pvc_factory",
  "path": "tests",
  "max_results": 3
}
```

**Example Output**:
```json
{
  "pattern": "test_pvc",
  "fixture_filter": "pvc_factory",
  "path": "tests",
  "examples": [
    {
      "test_name": "test_create_pvc",
      "file_path": "tests/manage/test_pvc.py",
      "line_number": 45,
      "fixtures": ["pvc_factory", "teardown_factory"],
      "source": "def test_create_pvc(pvc_factory, teardown_factory):\n    \"\"\"Test PVC creation\"\"\"\n    pvc = pvc_factory()\n    assert pvc.status == 'Bound'\n",
      "markers": ["tier1"]
    }
  ],
  "total_found": 3,
  "max_results": 3
}
```

---

### 8. get_deployment_module

**Description**: List deployment modules in ocs_ci/deployment/ directory

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "pattern": {
      "type": "string",
      "description": "Filter pattern for filenames (e.g., '*aws*')",
      "default": "*"
    },
    "description": {
      "type": "string",
      "description": "Search term for module descriptions"
    }
  }
}
```

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| pattern | string | No | "*" | Filename filter pattern |
| description | string | No | null | Search in descriptions |

**Example Input**:
```json
{
  "pattern": "*aws*"
}
```

**Example Output**:
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

---

### 9. get_resource_module

**Description**: List resource modules in ocs_ci/ocs/resources/ directory

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "pattern": {
      "type": "string",
      "description": "Filter pattern for filenames (e.g., '*pod*')",
      "default": "*"
    },
    "description": {
      "type": "string",
      "description": "Search term for module descriptions"
    }
  }
}
```

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| pattern | string | No | "*" | Filename filter pattern |
| description | string | No | null | Search in descriptions |

**Example Input**:
```json
{
  "pattern": "*pod*"
}
```

**Example Output**:
```json
{
  "directory": "ocs_ci/ocs/resources",
  "pattern": "*pod*",
  "modules": [
    {
      "name": "pod",
      "path": "ocs_ci/ocs/resources/pod.py",
      "description": "Pod resource class for managing Kubernetes pods"
    }
  ],
  "total": 1
}
```

---

### 10. get_helper_module

**Description**: List helper modules in ocs_ci/helpers/ directory

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "pattern": {
      "type": "string",
      "description": "Filter pattern for filenames (e.g., '*dr*')",
      "default": "*"
    },
    "description": {
      "type": "string",
      "description": "Search term for module descriptions"
    }
  }
}
```

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| pattern | string | No | "*" | Filename filter pattern |
| description | string | No | null | Search in descriptions |

**Example Input**:
```json
{
  "description": "disaster recovery"
}
```

**Example Output**:
```json
{
  "directory": "ocs_ci/helpers",
  "description_search": "disaster recovery",
  "modules": [
    {
      "name": "dr_helpers",
      "path": "ocs_ci/helpers/dr_helpers.py",
      "description": "Helper functions for disaster recovery operations"
    }
  ],
  "total": 1
}
```

---

### 11. get_utility_module

**Description**: List utility modules in ocs_ci/utility/ directory

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "pattern": {
      "type": "string",
      "description": "Filter pattern for filenames (e.g., '*aws*')",
      "default": "*"
    },
    "description": {
      "type": "string",
      "description": "Search term for module descriptions"
    }
  }
}
```

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| pattern | string | No | "*" | Filename filter pattern |
| description | string | No | null | Search in descriptions |

**Example Input**:
```json
{
  "pattern": "*aws*"
}
```

**Example Output**:
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

---

### 12. get_conftest

**Description**: List conftest.py files in tests/ directory tree

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "pattern": {
      "type": "string",
      "description": "Filter pattern for paths (e.g., '*manage*')",
      "default": "*"
    },
    "description": {
      "type": "string",
      "description": "Search term for conftest descriptions"
    }
  }
}
```

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| pattern | string | No | "*" | Path filter pattern |
| description | string | No | null | Search in descriptions |

**Example Input**:
```json
{
  "pattern": "*manage*"
}
```

**Example Output**:
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

---

### 13. get_conf_file

**Description**: List configuration files in conf/ directory

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "pattern": {
      "type": "string",
      "description": "Filter pattern for filenames (e.g., '*.yaml')",
      "default": "*"
    },
    "description": {
      "type": "string",
      "description": "Search term for config file descriptions"
    }
  }
}
```

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| pattern | string | No | "*" | Filename filter pattern |
| description | string | No | null | Search in descriptions |

**Example Input**:
```json
{
  "pattern": "*.yaml"
}
```

**Example Output**:
```json
{
  "directory": "conf",
  "pattern": "*.yaml",
  "files": [
    {
      "name": "ocsci",
      "path": "conf/ocsci/default_config.yaml",
      "description": "Default OCS-CI configuration"
    }
  ],
  "total": 1
}
```

---

## Response Formats

### Success Response

All successful tool calls return:

```json
{
  "content": [
    {
      "type": "text",
      "text": "{...tool-specific JSON...}"
    }
  ]
}
```

The inner JSON varies by tool (see Tool Schemas above).

### Error Response

When errors occur:

```json
{
  "error": "ErrorType",
  "message": "Human-readable error message",
  "details": {
    "file_path": "invalid/path.py",
    "reason": "Additional context"
  }
}
```

---

## Error Codes

### Security Errors

#### AccessDenied
**Cause**: Attempting to access sensitive directory

**Example**:
```json
{
  "error": "AccessDenied",
  "message": "Access to sensitive directory denied: data"
}
```

**Solution**: Remove /data from path or use --allow-sensitive

#### SecurityError
**Cause**: Path traversal attempt

**Example**:
```json
{
  "error": "SecurityError",
  "message": "Path escapes repository boundaries: ../../../etc/passwd"
}
```

**Solution**: Use paths relative to ocs-ci root only

### File Errors

#### FileNotFound
**Cause**: File does not exist

**Example**:
```json
{
  "error": "FileNotFound",
  "message": "File not found: ocs_ci/ocs/missing.py"
}
```

**Solution**: Verify file path with list_modules

#### InvalidPath
**Cause**: Malformed path

**Example**:
```json
{
  "error": "InvalidPath",
  "message": "Invalid path format: /absolute/path.py"
}
```

**Solution**: Use relative paths from ocs-ci root

### Parsing Errors

#### SyntaxError
**Cause**: Python file has syntax errors

**Example**:
```json
{
  "error": "SyntaxError",
  "message": "Failed to parse file: invalid syntax at line 45"
}
```

**Solution**: Fix syntax errors in the file

#### ClassNotFound
**Cause**: Class doesn't exist in file

**Example**:
```json
{
  "error": "ClassNotFound",
  "message": "Class 'Missing' not found in ocs_ci/ocs/ocp.py"
}
```

**Solution**: Check class name spelling, get file summary first

### Search Errors

#### InvalidRegex
**Cause**: Invalid regex pattern

**Example**:
```json
{
  "error": "InvalidRegex",
  "message": "Invalid regex pattern: '[unclosed'"
}
```

**Solution**: Fix regex syntax

#### NoMatches
**Cause**: Pattern found no matches (informational)

**Example**:
```json
{
  "error": "NoMatches",
  "message": "No matches found for pattern: 'nonexistent'"
}
```

**Solution**: Try broader pattern or different path

### Test Errors

#### TestNotFound
**Cause**: Test doesn't exist

**Example**:
```json
{
  "error": "TestNotFound",
  "message": "No test found matching: test_missing"
}
```

**Solution**: Search for pattern with search_code

---

## Examples

### Example 1: Find and Analyze a Test

**Step 1: Find Test**
```json
// Request
{
  "name": "find_test",
  "arguments": {
    "test_name": "test_create_pvc"
  }
}

// Response
{
  "test_name": "test_create_pvc",
  "matches": [{
    "file_path": "tests/manage/test_pvc.py",
    "line_number": 45,
    "fixtures": ["pvc_factory"]
  }]
}
```

**Step 2: Get Test Code**
```json
// Request
{
  "name": "get_content",
  "arguments": {
    "file_path": "tests/manage/test_pvc.py",
    "start_line": 45,
    "end_line": 60
  }
}

// Response
{
  "content": "def test_create_pvc(pvc_factory):\n    ..."
}
```

### Example 2: Analyze Class Hierarchy

**Step 1: Get Class Summary**
```json
// Request
{
  "name": "get_summary",
  "arguments": {
    "file_path": "ocs_ci/ocs/resources/pod.py",
    "class_name": "Pod"
  }
}

// Response
{
  "type": "class",
  "name": "Pod",
  "bases": ["OCS"],
  "methods": [...]
}
```

**Step 2: Get Full Inheritance**
```json
// Request
{
  "name": "get_inheritance",
  "arguments": {
    "file_path": "ocs_ci/ocs/resources/pod.py",
    "class_name": "Pod"
  }
}

// Response
{
  "inheritance_chain": ["Pod", "OCS", "OCP"],
  "methods_by_class": {...}
}
```

### Example 3: Search and Filter

**Search with Filters**
```json
// Request
{
  "name": "search_code",
  "arguments": {
    "pattern": "@pytest\\.fixture",
    "path": "tests",
    "file_pattern": "conftest.py",
    "context_lines": 3
  }
}

// Response
{
  "matches": [
    {
      "file": "tests/conftest.py",
      "line_number": 45,
      "line": "@pytest.fixture(scope='session')",
      "context_after": ["def pod_factory():", ...]
    }
  ]
}
```

---

## Rate Limits

**None**: The server has no built-in rate limits.

Performance considerations:
- Searches are fast (0.01-10s)
- Summaries are cached during session
- File reads are direct I/O

---

## Versioning

**Current Version**: 0.1.0

**Version Format**: MAJOR.MINOR.PATCH

**Compatibility**:
- MAJOR: Breaking changes to API
- MINOR: New features, backward compatible
- PATCH: Bug fixes, backward compatible

---

## Security Considerations

### Path Validation

All paths are validated for:
1. **Directory traversal**: Blocked
2. **Sensitive directories**: Blocked (unless --allow-sensitive)
3. **Repository boundaries**: Enforced

### Sensitive Directories

Blocked by default:
- `data` - Credentials and secrets
- `.git` - Git internals
- `.github` - Workflow configurations
- `credentials` - Credential storage
- `secrets` - Secret storage
- `.env` - Environment files
- `__pycache__` - Python cache

### Best Practices

1. **Never use --allow-sensitive** in production
2. **Validate user input** before passing to tools
3. **Use relative paths** only
4. **Monitor access logs** for suspicious patterns

---

**API Version**: 0.2.0
**Document Version**: 1.1
**Last Updated**: March 3, 2026
**Status**: Production Ready
