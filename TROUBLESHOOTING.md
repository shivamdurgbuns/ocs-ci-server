# OCS-CI MCP Server - Troubleshooting Guide

Version: 0.1.0
Last Updated: March 2, 2026

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Installation Issues](#installation-issues)
3. [Runtime Errors](#runtime-errors)
4. [Performance Problems](#performance-problems)
5. [Security Errors](#security-errors)
6. [Integration Issues](#integration-issues)
7. [Debug Mode](#debug-mode)
8. [Common Workflows](#common-workflows)

---

## Quick Diagnostics

### Run Verification Script

```bash
python verify_installation.py
```

Expected output:
```
✓ Python version: 3.11.9
✓ MCP package: installed
✓ Repository path: valid
✓ All tools: registered
✓ Tests: 89 passed

Status: OK
```

### Check Server Status

```bash
# Test server starts
python server.py --repo-path /path/to/ocs-ci --help

# Run quick test
pytest tests/test_server.py -v
```

### Verify Configuration

```bash
# Check config file exists
cat ~/.config/claude/config.json

# Verify paths are absolute
grep "repo-path" ~/.config/claude/config.json
```

---

## Installation Issues

### Issue: "ModuleNotFoundError: No module named 'mcp'"

**Symptom**:
```
ModuleNotFoundError: No module named 'mcp'
```

**Cause**: MCP package not installed

**Solution**:
```bash
# Install in current environment
pip install mcp

# Or reinstall server
cd /path/to/ocs-ci-server
pip install -e .

# Verify installation
pip list | grep mcp
```

---

### Issue: "pip install -e . fails"

**Symptom**:
```
ERROR: Failed building wheel for...
```

**Cause**: Missing build dependencies or wrong Python version

**Solution**:
```bash
# Check Python version (must be 3.9+)
python --version

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Try installation again
pip install -e .

# If still failing, install dependencies manually
pip install "mcp>=0.9.0"
```

---

### Issue: "Permission denied" during installation

**Symptom**:
```
PermissionError: [Errno 13] Permission denied
```

**Cause**: Installing system-wide without permissions

**Solutions**:

**Option 1: User installation**
```bash
pip install --user -e .
```

**Option 2: Virtual environment (recommended)**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -e .
```

**Option 3: Use sudo (not recommended)**
```bash
sudo pip install -e .
```

---

### Issue: "Command 'python' not found"

**Symptom**:
```
bash: python: command not found
```

**Cause**: Python not in PATH or named python3

**Solution**:
```bash
# Try python3 instead
python3 --version

# Create alias
alias python=python3

# Or update config.json
{
  "command": "python3",
  ...
}

# Or use absolute path
{
  "command": "/usr/bin/python3",
  ...
}
```

---

## Runtime Errors

### Issue: "Repository path does not exist"

**Symptom**:
```
Error: Repository path does not exist: /path/to/ocs-ci
```

**Cause**: Invalid --repo-path argument

**Solutions**:

**Check path exists**:
```bash
ls -la /path/to/ocs-ci
```

**Use absolute path**:
```json
{
  "args": [
    "/absolute/path/to/server.py",
    "--repo-path",
    "/absolute/path/to/ocs-ci"  // Not ~/ocs-ci or ./ocs-ci
  ]
}
```

**Verify ocs-ci structure**:
```bash
# Should have these directories
ls /path/to/ocs-ci/ocs_ci
ls /path/to/ocs-ci/tests
```

---

### Issue: "Access to sensitive directory denied: data"

**Symptom**:
```json
{
  "error": "AccessDenied",
  "message": "Access to sensitive directory denied: data"
}
```

**Cause**: Trying to access blocked directory

**Solutions**:

**Option 1: Don't access /data** (recommended)
- Use different path that doesn't include /data

**Option 2: Use --allow-sensitive** (DANGER)
```json
{
  "args": [
    "/path/to/server.py",
    "--repo-path", "/path/to/ocs-ci",
    "--allow-sensitive"  // WARNING: Security risk
  ]
}
```

**Blocked directories**:
- `/data` - Credentials and secrets
- `/.git` - Git internals
- `/.github` - GitHub workflows
- `/credentials` - Credential storage
- `/secrets` - Secret storage
- `/.env` - Environment files

---

### Issue: "Path escapes repository boundaries"

**Symptom**:
```json
{
  "error": "SecurityError",
  "message": "Path escapes repository boundaries: ../../../etc/passwd"
}
```

**Cause**: Directory traversal attempt

**Solution**:
- **Use relative paths from ocs-ci root only**
- **Don't use `../`**
- **Don't use absolute paths**

**Good**:
```
ocs_ci/ocs/ocp.py
tests/test_pvc.py
```

**Bad**:
```
../../../etc/passwd
/etc/passwd
./../../data/secrets
```

---

### Issue: "FileNotFoundError: [Errno 2] No such file"

**Symptom**:
```json
{
  "error": "FileNotFound",
  "message": "File not found: ocs_ci/ocs/missing.py"
}
```

**Cause**: File doesn't exist at specified path

**Solutions**:

**List directory first**:
```
# Use list_modules to find files
list_modules(path="ocs_ci/ocs", pattern="*.py")
```

**Check spelling**:
```
# Python is case-sensitive
ocp.py ✓
OCP.py ✗
Ocp.py ✗
```

**Verify path**:
```bash
# Manual check
ls /path/to/ocs-ci/ocs_ci/ocs/ocp.py
```

---

### Issue: "SyntaxError: invalid syntax"

**Symptom**:
```json
{
  "error": "SyntaxError",
  "message": "Failed to parse file: invalid syntax at line 45"
}
```

**Cause**: Python file has syntax errors

**Solutions**:

**Fix the syntax error in the file**:
```bash
# Check file manually
python -m py_compile /path/to/ocs-ci/file.py

# Use linter
pylint /path/to/ocs-ci/file.py
```

**Skip the file** if it's not valid Python:
- File might be template
- File might be incomplete
- Use different file

---

### Issue: "ClassNotFound: Class 'X' not found"

**Symptom**:
```json
{
  "error": "ClassNotFound",
  "message": "Class 'Pod' not found in ocs_ci/ocs/ocp.py"
}
```

**Cause**: Class doesn't exist in specified file

**Solutions**:

**Get file summary first**:
```
# List all classes in file
get_summary(file_path="ocs_ci/ocs/ocp.py")
```

**Check class name**:
```
# Case-sensitive
Pod ✓
pod ✗
POD ✗
```

**Search for class**:
```
# Find where class is defined
search_code(pattern="class Pod", file_pattern="*.py")
```

---

## Performance Problems

### Issue: "Search takes > 10 seconds"

**Symptom**: search_code is very slow

**Cause**: Searching entire repository without filters

**Solutions**:

**Use path filter**:
```python
# Instead of
search_code(pattern="test_")

# Use
search_code(pattern="test_", path="tests/manage")
```

**Use file pattern**:
```python
# Instead of
search_code(pattern="fixture")

# Use
search_code(pattern="fixture", file_pattern="conftest.py")
```

**Reduce context**:
```python
# Instead of
search_code(pattern="class", context_lines=10)

# Use
search_code(pattern="class", context_lines=0)
```

**More specific pattern**:
```python
# Instead of
search_code(pattern="test")  # Matches everything

# Use
search_code(pattern="def test_create_pvc")  # More specific
```

---

### Issue: "Server feels slow"

**Symptom**: All operations are slow

**Diagnostics**:

```bash
# Run performance benchmark
pytest tests/test_integration.py::test_performance_benchmark -v -s

# Check disk I/O
iostat 1 5

# Check repository size
du -sh /path/to/ocs-ci

# Check for other processes
top | grep python
```

**Solutions**:

**Check disk speed**:
- Use SSD instead of HDD
- Check disk isn't full (`df -h`)

**Check repository size**:
- Very large repos (>1GB) may be slower
- Consider excluding large directories

**Close other applications**:
- Free up CPU and memory
- Stop other Python processes

---

### Issue: "Out of memory"

**Symptom**:
```
MemoryError: Unable to allocate...
```

**Cause**: Very large file or search result

**Solutions**:

**Use line ranges**:
```python
# Instead of
get_content(file_path="huge_file.py")

# Use
get_content(file_path="huge_file.py", start_line=1, end_line=100)
```

**Limit search results**:
```python
# Use max_results
get_test_example(pattern="test", max_results=5)
```

**Increase memory**:
```bash
# Increase Python memory limit (Linux)
ulimit -v 2097152  # 2GB
```

---

## Security Errors

### Issue: "Cannot access .git directory"

**Symptom**:
```json
{
  "error": "AccessDenied",
  "message": "Access to sensitive directory denied: .git"
}
```

**Why blocked**: .git contains sensitive information

**Solution**: Don't access .git directory

- Git internals not needed for code analysis
- Use `git` command instead if needed
- If absolutely necessary, use --allow-sensitive (DANGER)

---

### Issue: "Cannot read credentials/secrets"

**Symptom**: Access denied to /data, /credentials, /secrets

**Why blocked**: These directories often contain sensitive data

**Solutions**:

**Don't store credentials in repository** (best practice)

**Use environment variables** instead:
```python
import os
password = os.getenv('PASSWORD')
```

**For debugging only**:
```bash
# Temporarily enable (REMOVE after debugging)
python server.py --repo-path /path/to/ocs-ci --allow-sensitive
```

---

## Integration Issues

### Issue: "Tools not showing in Claude Code"

**Symptom**: Claude Code doesn't see ocs-ci tools

**Diagnostics**:

```bash
# Check server starts
python server.py --repo-path /path/to/ocs-ci

# Check config.json syntax
python -m json.tool ~/.config/claude/config.json

# Check paths are absolute
cat ~/.config/claude/config.json | grep repo-path
```

**Solutions**:

**Fix config.json**:
```json
{
  "mcpServers": {
    "ocs-ci": {
      "command": "python",
      "args": [
        "/absolute/path/to/server.py",  // Must be absolute
        "--repo-path",
        "/absolute/path/to/ocs-ci"      // Must be absolute
      ]
    }
  }
}
```

**Restart Claude Code**:
```bash
# Completely quit and restart Claude Code
# Or use /reload command
```

**Check logs**:
```bash
# Claude Code logs (location varies by OS)
# Look for server startup errors
```

---

### Issue: "Server crashes on startup"

**Symptom**: Server exits immediately

**Diagnostics**:

```bash
# Run server manually to see errors
python server.py --repo-path /path/to/ocs-ci

# Check for Python errors
python -c "import mcp; print(mcp.__version__)"
```

**Common causes**:

1. **Missing dependencies**: `pip install -e .`
2. **Invalid repo path**: Check path exists
3. **Permission issues**: Check file permissions
4. **Python version**: Must be 3.9+

---

### Issue: "Timeout waiting for response"

**Symptom**: Tool calls time out

**Cause**: Operation takes too long or server hung

**Solutions**:

**Check server logs**:
```bash
# Server prints to stderr
# Check for errors or slow operations
```

**Simplify request**:
```python
# Instead of searching entire repo
search_code(pattern="test")

# Search smaller subset
search_code(pattern="test", path="tests/manage", max_results=10)
```

**Restart server**:
```bash
# Restart Claude Code to restart server
```

---

## Debug Mode

### Enable Debug Output

**Server debug**:
```bash
# Run server with debug output
python server.py --repo-path /path/to/ocs-ci 2>&1 | tee server.log
```

**Python debug**:
```bash
# Enable Python debug mode
PYTHONDEBUG=1 python server.py --repo-path /path/to/ocs-ci
```

**Test debug**:
```bash
# Run tests with verbose output
pytest tests/ -v -s

# Run single test with debug
pytest tests/test_server.py::test_server_initialization -v -s

# Enable pytest debug
pytest tests/ --log-cli-level=DEBUG
```

### Interpret Debug Output

**Server startup**:
```
Starting OCS-CI MCP Server          ← Server starting
Repository: /path/to/ocs-ci          ← Repository path valid
WARNING: Sensitive directory access ENABLED  ← --allow-sensitive flag set
```

**Tool calls** (add print statements):
```python
# In tool function
print(f"DEBUG: Tool called with args: {arguments}", file=sys.stderr)
```

---

## Common Workflows

### Workflow: Diagnose Installation

```bash
# 1. Check Python version
python --version  # Should be 3.9+

# 2. Check dependencies
pip list | grep mcp  # Should show mcp package

# 3. Test server
python server.py --help  # Should show usage

# 4. Run tests
pytest tests/test_server.py -v  # Should pass

# 5. Run verification
python verify_installation.py  # Should report OK
```

---

### Workflow: Diagnose Runtime Error

```bash
# 1. Run server manually
python server.py --repo-path /path/to/ocs-ci

# 2. Check for errors in output

# 3. Verify repository
ls /path/to/ocs-ci/ocs_ci

# 4. Run integration tests
pytest tests/test_integration.py -v

# 5. Check specific tool
pytest tests/test_list_modules.py -v
```

---

### Workflow: Diagnose Performance

```bash
# 1. Run performance benchmark
pytest tests/test_integration.py::test_performance_benchmark -v -s

# 2. Check disk I/O
iostat 1 5

# 3. Profile slow operation
python -m cProfile server.py --repo-path /path/to/ocs-ci

# 4. Check repository size
du -sh /path/to/ocs-ci
```

---

### Workflow: Diagnose Security Error

```bash
# 1. Identify blocked path
# Error message shows: "Access denied: data"

# 2. Check if path is necessary
# Can you use a different path?

# 3. If absolutely needed (RARE)
# Add --allow-sensitive flag temporarily

# 4. Remove flag after debugging
# Don't commit config with --allow-sensitive
```

---

## Getting Help

### Before Asking for Help

1. ✓ Run `verify_installation.py`
2. ✓ Check this troubleshooting guide
3. ✓ Read error message carefully
4. ✓ Run server manually to see errors
5. ✓ Check config.json syntax and paths

### Information to Provide

When asking for help, include:

```
1. Error message (full text)
2. Python version: python --version
3. MCP version: pip show mcp
4. Server version: cat pyproject.toml | grep version
5. OS: uname -a (Linux/macOS) or ver (Windows)
6. Config: cat ~/.config/claude/config.json
7. Steps to reproduce
8. Expected vs actual behavior
```

### Useful Commands

```bash
# Collect diagnostic info
python --version > diagnostic.txt
pip list >> diagnostic.txt
python server.py --help >> diagnostic.txt 2>&1
pytest tests/test_server.py -v >> diagnostic.txt 2>&1
```

---

## Known Issues

### Issue: Windows path separators

**Symptom**: Paths with backslashes fail

**Solution**: Use forward slashes even on Windows
```python
# Good
"ocs_ci/ocs/ocp.py"

# Bad
"ocs_ci\\ocs\\ocp.py"
```

---

### Issue: Symlinked repository

**Symptom**: Repository accessed via symlink

**Solution**: Use real path
```bash
# Find real path
realpath /symlink/to/ocs-ci

# Use real path in config
"--repo-path", "/real/path/to/ocs-ci"
```

---

### Issue: Repository on network drive

**Symptom**: Very slow performance

**Solution**: Clone repository to local disk
```bash
# Clone locally
git clone /network/ocs-ci /local/ocs-ci

# Update config
"--repo-path", "/local/ocs-ci"
```

---

## Testing Your Fix

After applying a fix:

```bash
# 1. Test server starts
python server.py --repo-path /path/to/ocs-ci
# Press Ctrl+C

# 2. Run relevant tests
pytest tests/test_<affected_tool>.py -v

# 3. Run integration tests
pytest tests/test_integration.py -v

# 4. Test in Claude Code
# Try the operation that was failing

# 5. Verify no regression
pytest tests/ -v
```

---

**Troubleshooting Guide Version**: 1.0
**Server Version**: 0.1.0
**Last Updated**: March 2, 2026
**Status**: Production Ready
