# OCS-CI MCP Server - Quick Reference

## Running the Server

```bash
python server.py --repo-path /path/to/ocs-ci
```

## Available Tools (13)

### 1. list_modules
Browse repository structure
```json
{
  "path": "ocs_ci/ocs",
  "pattern": "*.py"
}
```

### 2. get_summary
Get file/class summary with inheritance
```json
{
  "file_path": "ocs_ci/ocs/ocp.py",
  "class_name": "OCP"
}
```

### 3. get_content
Read file content (optionally with line range)
```json
{
  "file_path": "ocs_ci/ocs/ocp.py",
  "start_line": 10,
  "end_line": 50
}
```

### 4. search_code
Search for regex patterns
```json
{
  "pattern": "def test_.*",
  "file_pattern": "test_*.py",
  "context_lines": 3
}
```

### 5. get_inheritance
Show full inheritance chain with methods
```json
{
  "file_path": "ocs_ci/ocs/ocp.py",
  "class_name": "OCP"
}
```

### 6. find_test
Find test by name or nodeid
```json
{
  "test_name": "tests/conftest.py::test_deployment"
}
```

### 7. get_test_example
Find example tests
```json
{
  "pattern": "pod",
  "fixture_name": "pod_factory",
  "max_results": 5
}
```

### 8. get_deployment_module
List deployment modules
```json
{
  "pattern": "*aws*"
}
```

### 9. get_resource_module
List resource modules
```json
{
  "pattern": "*pod*"
}
```

### 10. get_helper_module
List helper modules
```json
{
  "description": "disaster recovery"
}
```

### 11. get_utility_module
List utility modules
```json
{
  "pattern": "*aws*"
}
```

### 12. get_conftest
List conftest files
```json
{
  "pattern": "*manage*"
}
```

### 13. get_conf_file
List config files
```json
{
  "pattern": "*.yaml"
}
```

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific tool
python -m pytest tests/test_get_content.py -v

# Verify all tools
python verify_tools.py
```

## Project Structure

```
ocs-ci-server/
├── analyzers/          # Core analysis modules
│   ├── ast_analyzer.py
│   ├── import_resolver.py
│   └── summarizer.py
├── tools/              # 13 MCP tools
│   ├── list_modules.py
│   ├── get_summary.py
│   ├── get_content.py
│   ├── search_code.py
│   ├── get_inheritance.py
│   ├── find_test.py
│   └── get_test_example.py
├── tests/              # 48 tests
│   └── test_*.py
└── server.py           # MCP server entry point
```

## Security

All tools validate paths to prevent traversal attacks:
- ✅ `../../../etc/passwd` → Blocked
- ✅ Symlink traversal → Blocked
- ✅ All file access stays within repo

## Test Coverage

- **Total**: 139 tests
- **Pass Rate**: 100%
- **Security**: 13 path traversal tests
- **Module Discovery**: 18 tests (6 tools × 3 tests)
- **Integration**: 25 tests
