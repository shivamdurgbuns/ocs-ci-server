# MCP Tools Expansion - Design Document

**Date**: March 3, 2026
**Version**: 1.0
**Status**: Approved

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Requirements](#requirements)
4. [Architecture](#architecture)
5. [Implementation Details](#implementation-details)
6. [Tool Specifications](#tool-specifications)
7. [Testing Strategy](#testing-strategy)
8. [Integration Plan](#integration-plan)
9. [Performance Expectations](#performance-expectations)
10. [Documentation Updates](#documentation-updates)

---

## Overview

This design adds 6 new MCP tools to the ocs-ci server for faster navigation to specific module types in the ocs-ci repository. Instead of browsing multiple directories or using generic search tools, users can directly discover modules by type with rich descriptions.

### Goals

- **Faster Navigation**: Direct access to specific module types (deployment, resources, helpers, utilities, config)
- **Rich Discovery**: Provide file paths + extracted descriptions to help users understand module purposes
- **Consistent Pattern**: Follow existing tool architecture and patterns
- **Powerful Filtering**: Support both filename pattern matching and description search

### New Tools

1. `get_conf_file` - List configuration files in `/conf/`
2. `get_conftest` - List conftest.py files in `/tests/` tree
3. `get_deployment_module` - List deployment modules in `/ocs_ci/deployment/`
4. `get_resource_module` - List resource modules in `/ocs_ci/ocs/resources/`
5. `get_helper_module` - List helper modules in `/ocs_ci/helpers/`
6. `get_utility_module` - List utility modules in `/ocs_ci/utility/`

---

## Problem Statement

### Current State

The ocs-ci MCP server provides 7 tools for code analysis:
- `list_modules` - Generic directory browsing
- `get_summary` - File/class summaries
- `get_content` - File content reading
- `search_code` - Regex search
- `get_inheritance` - Inheritance analysis
- `find_test` - Test discovery
- `get_test_example` - Test example search

### The Gap

Users need to:
1. Navigate to specific module types (e.g., "show me all deployment modules")
2. Understand what each module does without opening it
3. Find modules by name pattern or description

Current approach requires:
- Multiple `list_modules` calls to browse directories
- Multiple `get_summary` calls to understand modules
- Or using `search_code` which searches content, not structure

### Solution

Add specialized tools for each module type that:
- List all modules in the target directory
- Extract and display module descriptions
- Support filtering by filename pattern and description search
- Return results in a single, efficient call

---

## Requirements

### Functional Requirements

1. **Six New Tools**: One for each module type
2. **Description Extraction**: Parse docstrings from Python modules
3. **Dual Filtering**: Support both pattern (filename) and search (description) filters
4. **Metadata**: Return filename, path, description, size, line count
5. **Security**: Follow existing security validation patterns
6. **Performance**: < 1s per tool invocation for typical directories

### Non-Functional Requirements

1. **Consistency**: Match existing tool patterns and architecture
2. **Maintainability**: Share common logic via helper module
3. **Testability**: 100% test coverage with unit and integration tests
4. **Documentation**: Update all relevant docs
5. **Token Efficiency**: Truncate descriptions to maintain efficiency

---

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│                    Server Layer                         │
│  - Register 6 new tools                                 │
│  - Route requests to tool handlers                      │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────┴─────────────────────────────────────┐
│                   Tool Layer (NEW)                      │
│  ┌──────────────────────────────────────────────────┐   │
│  │  get_conf_file.py                                │   │
│  │  get_conftest.py                                 │   │
│  │  get_deployment_module.py                        │   │
│  │  get_resource_module.py                          │   │
│  │  get_helper_module.py                            │   │
│  │  get_utility_module.py                           │   │
│  └─────────────┬────────────────────────────────────┘   │
│                │ uses                                    │
│  ┌─────────────┴────────────────────────────────────┐   │
│  │  module_discovery.py (SHARED HELPER)             │   │
│  │  - discover_modules()                            │   │
│  │  - extract_description()                         │   │
│  │  - apply_filters()                               │   │
│  └─────────────┬────────────────────────────────────┘   │
└────────────────┼────────────────────────────────────────┘
                 │ uses
┌────────────────┴────────────────────────────────────────┐
│              Analyzer Layer (EXISTING)                  │
│  - ASTAnalyzer (parse Python, extract docstrings)       │
│  - Security (validate paths)                            │
└─────────────────────────────────────────────────────────┘
```

### Design Pattern: Approach 1 (Six Individual Tools)

**Why this approach?**

1. ✅ **Follows existing patterns** - One file per tool, matches current architecture
2. ✅ **Explicit and discoverable** - Users see 6 clear tools in MCP tool list
3. ✅ **DRY through sharing** - Common logic in `module_discovery.py`
4. ✅ **Easy to test** - Each tool testable independently
5. ✅ **Extensible** - Each tool can add specific behavior if needed
6. ✅ **Matches requirements** - User requested these specific tool names

**Alternative approaches considered:**
- Single parameterized tool: Less discoverable, different from existing pattern
- Hybrid with config: Added abstraction, less clear directory mapping

---

## Implementation Details

### Directory Mapping

| Tool | Target Directory | File Type | Recursive |
|------|------------------|-----------|-----------|
| `get_conf_file` | `/conf/` | YAML/config | No |
| `get_conftest` | `/tests/` | conftest.py only | Yes |
| `get_deployment_module` | `/ocs_ci/deployment/` | Python | No |
| `get_resource_module` | `/ocs_ci/ocs/resources/` | Python | No |
| `get_helper_module` | `/ocs_ci/helpers/` | Python | No |
| `get_utility_module` | `/ocs_ci/utility/` | Python | No |

### Shared Module Discovery Logic

**File**: `tools/module_discovery.py`

**Key Function**:
```python
def discover_modules(
    repo_path: str,
    target_dir: str,
    pattern: str = "*",
    search_text: Optional[str] = None,
    file_extension: str = ".py",
    recursive: bool = False,
    analyzer: Optional[ASTAnalyzer] = None,
    allow_sensitive: bool = False
) -> Dict:
    """
    Discover modules in a directory with filtering

    Args:
        repo_path: Path to ocs-ci repository root
        target_dir: Relative directory to search (e.g., "ocs_ci/deployment")
        pattern: Filename pattern (e.g., "*aws*")
        search_text: Search within descriptions (case-insensitive)
        file_extension: File extension to filter (default: ".py")
        recursive: Whether to search subdirectories
        analyzer: ASTAnalyzer instance for parsing
        allow_sensitive: Security flag

    Returns:
        Dict with directory, total_modules, filtered_modules, modules list
    """
```

**Algorithm**:
1. Validate path with `validate_path()`
2. Walk directory (recursive if needed)
3. Filter by file extension
4. For each file:
   - Extract description using `extract_description()`
   - Apply pattern filter (fnmatch)
   - Apply search filter (case-insensitive substring)
5. Collect metadata (name, path, description, size, lines)
6. Return formatted results

### Description Extraction

**For Python Files**:
```python
def extract_description(file_path: str, analyzer: ASTAnalyzer) -> str:
    """Extract module description from Python file"""
    try:
        # Parse AST
        tree = analyzer.parse_file(file_path)

        # Get module docstring (first expression if it's a string)
        if tree.body and isinstance(tree.body[0], ast.Expr):
            if isinstance(tree.body[0].value, ast.Str):
                docstring = tree.body[0].value.s
                # First line only, truncate at 200 chars
                first_line = docstring.split('\n')[0].strip()
                return first_line[:200]

        # Fallback: Look for first comment
        # ... implementation ...

        return "No description available"
    except:
        return "No description available"
```

**For Config Files (YAML)**:
```python
def extract_config_description(file_path: str) -> str:
    """Extract description from config file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read first 10 lines
            lines = [f.readline() for _ in range(10)]

        # Look for comment with "Description:" or first comment
        for line in lines:
            if line.strip().startswith('#'):
                desc = line.strip('#').strip()
                if desc:
                    return desc[:200]

        return "Configuration file"
    except:
        return "Configuration file"
```

### Filtering Logic

**Pattern Filter** (filename matching):
```python
import fnmatch

# Apply pattern to filename
if not fnmatch.fnmatch(file_name, pattern):
    continue  # Skip this file
```

**Search Filter** (description search):
```python
# Apply search to description
if search_text and search_text.lower() not in description.lower():
    continue  # Skip this file
```

**Combined Filters**: Both must match (AND logic)

### Special Case: get_conftest

Unlike other tools, `get_conftest` needs recursive search:
- Walk `/tests/` tree recursively
- Only match files named exactly `conftest.py`
- Return relative paths (e.g., `tests/functional/pv/conftest.py`)

---

## Tool Specifications

### Common Parameters

All tools share these parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `pattern` | string | No | `"*"` | Filename pattern (e.g., `"*aws*"`, `"pod*"`) |
| `search_text` | string | No | `null` | Search within descriptions (case-insensitive) |

### Common Response Format

All tools return:

```json
{
  "directory": "ocs_ci/deployment",
  "total_modules": 42,
  "filtered_modules": 3,
  "modules": [
    {
      "name": "aws.py",
      "path": "ocs_ci/deployment/aws.py",
      "description": "AWS deployment module for provisioning OCS clusters",
      "size_bytes": 35883,
      "lines": 1245
    },
    {
      "name": "azure.py",
      "path": "ocs_ci/deployment/azure.py",
      "description": "Azure deployment and cluster management utilities",
      "size_bytes": 8231,
      "lines": 287
    }
  ]
}
```

### Individual Tool Specs

#### 1. get_conf_file

```python
{
  "name": "get_conf_file",
  "description": "List configuration files in conf/ directory with descriptions",
  "inputSchema": {
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
}
```

**Target**: `/conf/`
**Extension**: All files (YAML, JSON, etc.)
**Recursive**: No

#### 2. get_conftest

```python
{
  "name": "get_conftest",
  "description": "List all conftest.py files in tests/ directory tree with descriptions",
  "inputSchema": {
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
}
```

**Target**: `/tests/`
**Extension**: `conftest.py` only
**Recursive**: Yes
**Note**: Pattern matches on full path, not just filename

#### 3. get_deployment_module

```python
{
  "name": "get_deployment_module",
  "description": "List deployment modules in ocs_ci/deployment/ with descriptions",
  "inputSchema": {
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
}
```

**Target**: `/ocs_ci/deployment/`
**Extension**: `.py`
**Recursive**: No

#### 4. get_resource_module

```python
{
  "name": "get_resource_module",
  "description": "List resource modules in ocs_ci/ocs/resources/ with descriptions",
  "inputSchema": {
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
}
```

**Target**: `/ocs_ci/ocs/resources/`
**Extension**: `.py`
**Recursive**: No

#### 5. get_helper_module

```python
{
  "name": "get_helper_module",
  "description": "List helper modules in ocs_ci/helpers/ with descriptions",
  "inputSchema": {
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
}
```

**Target**: `/ocs_ci/helpers/`
**Extension**: `.py`
**Recursive**: No

#### 6. get_utility_module

```python
{
  "name": "get_utility_module",
  "description": "List utility modules in ocs_ci/utility/ with descriptions",
  "inputSchema": {
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
}
```

**Target**: `/ocs_ci/utility/`
**Extension**: `.py`
**Recursive**: No

---

## Testing Strategy

### Test Coverage Target

- **Total new tests**: ~60 tests
- **Coverage**: 100% of new code
- **Test types**: Unit tests + Integration tests

### Unit Tests

#### 1. test_module_discovery.py (15-20 tests)

Test the shared helper module:

```python
class TestModuleDiscovery:
    def test_discover_modules_no_filter()
    def test_discover_modules_with_pattern()
    def test_discover_modules_with_search()
    def test_discover_modules_combined_filters()
    def test_discover_modules_recursive()
    def test_extract_description_with_docstring()
    def test_extract_description_no_docstring()
    def test_extract_description_multiline_docstring()
    def test_extract_config_description()
    def test_extract_config_description_no_comments()
    def test_empty_directory()
    def test_invalid_python_file()
    def test_pattern_matching_edge_cases()
    def test_search_case_insensitive()
    def test_description_truncation()
```

#### 2. Tool-Specific Tests (7 tests each × 6 tools = 42 tests)

Each tool test file follows this pattern:

```python
class TestGetDeploymentModule:
    def test_security_validation_path_traversal()
    def test_security_validation_sensitive_dir()
    def test_list_all_modules()
    def test_filter_by_pattern()
    def test_filter_by_search()
    def test_filter_combined()
    def test_empty_results()
```

**Test files**:
- `tests/test_get_conf_file.py`
- `tests/test_get_conftest.py`
- `tests/test_get_deployment_module.py`
- `tests/test_get_resource_module.py`
- `tests/test_get_helper_module.py`
- `tests/test_get_utility_module.py`

### Integration Tests

Add to `tests/test_integration.py`:

```python
class TestModuleDiscoveryIntegration:
    """Test against real ocs-ci repository"""

    def test_get_deployment_module_real_repo()
    def test_get_resource_module_real_repo()
    def test_get_helper_module_real_repo()
    def test_get_utility_module_real_repo()
    def test_get_conftest_real_repo()
    def test_module_descriptions_meaningful()
```

### Test Data

Create mock repository structure in `tests/fixtures/`:
```
tests/fixtures/mock_repo/
  conf/
    test_config.yaml
  tests/
    conftest.py
    functional/
      conftest.py
  ocs_ci/
    deployment/
      test_module.py
    helpers/
      test_helper.py
    ocs/
      resources/
        test_resource.py
    utility/
      test_util.py
```

---

## Integration Plan

### Changes to server.py

#### 1. Add Imports

```python
from tools.get_conf_file import get_conf_file_tool
from tools.get_conftest import get_conftest_tool
from tools.get_deployment_module import get_deployment_module_tool
from tools.get_resource_module import get_resource_module_tool
from tools.get_helper_module import get_helper_module_tool
from tools.get_utility_module import get_utility_module_tool
```

#### 2. Register Tools in list_tools()

Add 6 new `types.Tool(...)` entries to the return list.

#### 3. Add Handlers in call_tool()

Add 6 new `elif name == "..."` cases:

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
```

### File Structure

New files to create:
```
tools/
  module_discovery.py         # Shared helper (NEW)
  get_conf_file.py            # Tool 1 (NEW)
  get_conftest.py             # Tool 2 (NEW)
  get_deployment_module.py    # Tool 3 (NEW)
  get_resource_module.py      # Tool 4 (NEW)
  get_helper_module.py        # Tool 5 (NEW)
  get_utility_module.py       # Tool 6 (NEW)

tests/
  test_module_discovery.py    # Shared helper tests (NEW)
  test_get_conf_file.py       # Tool 1 tests (NEW)
  test_get_conftest.py        # Tool 2 tests (NEW)
  test_get_deployment_module.py   # Tool 3 tests (NEW)
  test_get_resource_module.py     # Tool 4 tests (NEW)
  test_get_helper_module.py       # Tool 5 tests (NEW)
  test_get_utility_module.py      # Tool 6 tests (NEW)
  fixtures/
    mock_repo/                # Mock test data (NEW)
```

---

## Performance Expectations

Based on existing tool performance (60-250x faster than targets), we expect:

| Tool | Directory Size | Expected Time | Target |
|------|----------------|---------------|--------|
| `get_conf_file` | ~10 files | < 0.1s | < 1s |
| `get_conftest` | ~20 files | < 0.5s | < 2s |
| `get_deployment_module` | ~40 files | < 0.3s | < 2s |
| `get_resource_module` | ~45 files | < 0.4s | < 2s |
| `get_helper_module` | ~30 files | < 0.3s | < 2s |
| `get_utility_module` | ~70 files | < 0.4s | < 2s |

**Performance Characteristics**:
- O(n) complexity where n = number of files
- Dominated by file I/O and AST parsing
- AST parsing: ~0.001-0.01s per file
- Pattern/search filtering: negligible overhead

**Optimization Strategies**:
- Reuse existing `ASTAnalyzer` instance (no new objects)
- Only parse first few lines for docstrings
- Early exit when filters don't match
- Truncate descriptions to 200 chars

---

## Documentation Updates

### Files to Update

#### 1. README.md

Change:
```markdown
The OCS-CI MCP Server provides 7 specialized tools...
```

To:
```markdown
The OCS-CI MCP Server provides 13 specialized tools...
```

Add new tools to table:
```markdown
| Tool | Purpose | Example Use Case |
|------|---------|------------------|
| **get_deployment_module** | List deployment modules | Find AWS deployment code |
| **get_resource_module** | List resource modules | Find Pod resource class |
| **get_helper_module** | List helper modules | Find DR helper functions |
| **get_utility_module** | List utility modules | Find AWS utility functions |
| **get_conftest** | List conftest files | Find pytest fixtures |
| **get_conf_file** | List config files | Browse configurations |
```

#### 2. API_REFERENCE.md

Add section for each new tool with:
- Tool name and description
- Parameters specification
- Response format
- Example request/response
- Common use cases

#### 3. USER_GUIDE.md

Add usage examples:
```markdown
### Finding Deployment Modules

Find all AWS-related deployment modules:
```
User: "Show me deployment modules related to AWS"
Tool: get_deployment_module(pattern="*aws*")
```

Find modules by description:
```
User: "Find deployment modules for bare metal"
Tool: get_deployment_module(search_text="bare metal")
```
```

#### 4. TOOLS_SUMMARY.md

Add one-line descriptions for each new tool.

#### 5. QUICK_REFERENCE.md

Add command quick reference:
```markdown
## Module Discovery

- `get_deployment_module(pattern="*aws*")` - Find AWS deployment modules
- `get_resource_module(search_text="pod")` - Search resource modules
- `get_helper_module()` - List all helpers
- `get_utility_module(pattern="*azure*")` - Find Azure utilities
- `get_conftest()` - List all conftest.py files
- `get_conf_file()` - List configuration files
```

#### 6. ARCHITECTURE.md

Update component diagrams and tool layer description to include new tools.

#### 7. CHANGELOG.md

Add entry:
```markdown
## [0.2.0] - 2026-03-03

### Added
- 6 new module discovery tools for faster navigation
- `get_deployment_module` - List deployment modules
- `get_resource_module` - List resource modules
- `get_helper_module` - List helper modules
- `get_utility_module` - List utility modules
- `get_conftest` - List conftest.py files
- `get_conf_file` - List configuration files
- Shared `module_discovery` helper for efficient module scanning
- Support for pattern filtering and description search
- 60+ new tests for comprehensive coverage
```

---

## Example Usage

### Use Case 1: Find AWS Deployment Code

```
User: "Show me all AWS deployment modules"

Tool Call:
get_deployment_module(pattern="*aws*")

Response:
{
  "directory": "ocs_ci/deployment",
  "total_modules": 42,
  "filtered_modules": 1,
  "modules": [
    {
      "name": "aws.py",
      "path": "ocs_ci/deployment/aws.py",
      "description": "AWS deployment module for provisioning OCS clusters on AWS infrastructure",
      "size_bytes": 35883,
      "lines": 1245
    }
  ]
}
```

### Use Case 2: Find Helper Modules for Disaster Recovery

```
User: "Find helper modules related to disaster recovery"

Tool Call:
get_helper_module(search_text="disaster recovery")

Response:
{
  "directory": "ocs_ci/helpers",
  "total_modules": 30,
  "filtered_modules": 2,
  "modules": [
    {
      "name": "dr_helpers.py",
      "path": "ocs_ci/helpers/dr_helpers.py",
      "description": "Disaster recovery helper functions for regional and metro DR operations",
      "size_bytes": 98409,
      "lines": 3245
    },
    {
      "name": "dr_helpers_ui.py",
      "path": "ocs_ci/helpers/dr_helpers_ui.py",
      "description": "UI automation helpers for disaster recovery operations",
      "size_bytes": 42787,
      "lines": 1456
    }
  ]
}
```

### Use Case 3: Find All Pytest Fixtures in Functional Tests

```
User: "Show me all conftest files in functional tests"

Tool Call:
get_conftest(pattern="*functional*")

Response:
{
  "directory": "tests",
  "total_modules": 19,
  "filtered_modules": 8,
  "modules": [
    {
      "name": "conftest.py",
      "path": "tests/functional/conftest.py",
      "description": "Pytest fixtures for functional test suite",
      "size_bytes": 12456,
      "lines": 432
    },
    {
      "name": "conftest.py",
      "path": "tests/functional/pv/conftest.py",
      "description": "PV test fixtures for volume operations",
      "size_bytes": 8234,
      "lines": 287
    }
  ]
}
```

### Use Case 4: Browse All Resource Modules

```
User: "List all resource modules"

Tool Call:
get_resource_module()

Response:
{
  "directory": "ocs_ci/ocs/resources",
  "total_modules": 45,
  "filtered_modules": 45,
  "modules": [
    {
      "name": "pod.py",
      "path": "ocs_ci/ocs/resources/pod.py",
      "description": "Pod resource management and operations",
      "size_bytes": 45632,
      "lines": 1543
    },
    {
      "name": "pvc.py",
      "path": "ocs_ci/ocs/resources/pvc.py",
      "description": "PersistentVolumeClaim resource operations",
      "size_bytes": 38421,
      "lines": 1287
    }
    // ... 43 more modules
  ]
}
```

---

## Security Considerations

All new tools follow existing security patterns:

1. **Path Validation**: Use `validate_path()` from `tools/security.py`
2. **Directory Traversal Prevention**: Validate all paths stay within repository
3. **Sensitive Directory Blocking**: Respect `allow_sensitive` flag
4. **No Code Execution**: Only AST parsing, no eval/exec
5. **Read-Only Operations**: No file modifications

### Security Testing

Each tool includes tests for:
- Path traversal attempts (`../../etc/passwd`)
- Sensitive directory access (`data/`, `.git/`)
- Repository boundary violations

---

## Migration Notes

### Backwards Compatibility

- ✅ **Fully backwards compatible** - No changes to existing tools
- ✅ **Additive only** - Only adding new tools
- ✅ **No breaking changes** - Existing tool signatures unchanged

### Deployment

1. Install new code
2. Restart MCP server
3. New tools appear automatically in Claude Code

No configuration changes required.

---

## Success Criteria

### Definition of Done

- [ ] All 6 tools implemented
- [ ] Shared helper module created
- [ ] 60+ tests written and passing
- [ ] Integration tests pass against real ocs-ci repo
- [ ] All documentation updated
- [ ] Performance targets met (< 1s per tool)
- [ ] Security validation passes
- [ ] Code review completed
- [ ] Version bumped to 0.2.0

### Validation

1. **Functional**: All tools return correct results for real ocs-ci repo
2. **Performance**: All tools complete in < 1s
3. **Quality**: 100% test pass rate, no regressions
4. **Documentation**: All docs updated and accurate
5. **User Experience**: Tools are discoverable and easy to use

---

## Timeline

Estimated implementation time: **2-3 hours**

1. **Shared Helper** (30 min)
   - Implement `module_discovery.py`
   - Write unit tests

2. **Six Tools** (60 min)
   - Implement 6 tool files (10 min each)
   - Write tool tests (7 tests per tool)

3. **Server Integration** (15 min)
   - Update `server.py`
   - Register tools

4. **Integration Tests** (15 min)
   - Add integration tests
   - Validate against real repo

5. **Documentation** (30 min)
   - Update 7 documentation files

6. **Testing & Validation** (15 min)
   - Run full test suite
   - Performance validation
   - Manual testing

---

## Future Enhancements

Potential future improvements (out of scope for this design):

1. **Caching**: Cache module descriptions for repeated queries
2. **Subdirectory Support**: Allow searching within subdirectories
3. **Advanced Filtering**: Regex patterns, multiple search terms
4. **Result Ranking**: Sort by relevance score
5. **Related Modules**: Show import relationships
6. **Usage Examples**: Extract usage examples from docstrings

---

## Appendix: Core Values Alignment

This design maintains the core values of the ocs-ci-server codebase:

### 1. Token Efficiency
- ✅ Truncate descriptions to 200 chars
- ✅ Return summaries, not full content
- ✅ Single call replaces multiple list/summary calls

### 2. Security by Default
- ✅ Path validation on all operations
- ✅ Sensitive directory blocking
- ✅ Repository boundary enforcement

### 3. Performance
- ✅ Expected performance: < 1s (well within targets)
- ✅ Reuse existing analyzer instances
- ✅ Efficient filtering algorithms

### 4. Consistency
- ✅ Follows existing tool pattern (one file per tool)
- ✅ Uses existing security validation
- ✅ Reuses existing analyzers
- ✅ Matches existing response formats

### 5. Testability
- ✅ 100% test coverage goal
- ✅ Unit + integration tests
- ✅ Clear separation of concerns

### 6. Maintainability
- ✅ Shared logic in helper module
- ✅ DRY principle applied
- ✅ Clear, documented code
- ✅ Follows existing patterns

### 7. Extensibility
- ✅ Easy to add more module types
- ✅ Can enhance individual tools
- ✅ Modular architecture

---

**Design Version**: 1.0
**Status**: Approved
**Next Step**: Create implementation plan with writing-plans skill
**Date**: March 3, 2026
