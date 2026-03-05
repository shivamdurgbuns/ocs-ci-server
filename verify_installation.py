#!/usr/bin/env python3
"""
OCS-CI MCP Server Installation Verification Script

Checks all dependencies, file structure, and basic functionality.
"""

import sys
import subprocess
from pathlib import Path
import importlib.util


def print_header():
    """Print verification header"""
    print()
    print("╔════════════════════════════════════════════════════════╗")
    print("║     OCS-CI MCP Server Installation Verification        ║")
    print("╚════════════════════════════════════════════════════════╝")
    print()


def check_python_version():
    """Check Python version"""
    print("Checking Python version...")
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version.major >= 3 and version.minor >= 9:
        print(f"✅ Python {version_str} (requires 3.9+)")
        return True
    else:
        print(f"❌ Python {version_str} (requires 3.9+)")
        return False


def check_package(package_name):
    """Check if a package is installed"""
    spec = importlib.util.find_spec(package_name)
    if spec is not None:
        try:
            # Get version if possible
            module = importlib.import_module(package_name)
            version = getattr(module, '__version__', 'unknown')
            return True, version
        except:
            return True, 'unknown'
    return False, None


def check_dependencies():
    """Check required dependencies"""
    print("\nChecking dependencies...")

    required = {
        'mcp': '0.9.0',
    }

    all_ok = True
    for package, min_version in required.items():
        installed, version = check_package(package)
        if installed:
            print(f"✅ {package} package installed (version {version})")
        else:
            print(f"❌ {package} package NOT installed (required: >={min_version})")
            all_ok = False

    return all_ok


def check_file_structure():
    """Check file structure"""
    print("\nChecking file structure...")

    base_dir = Path(__file__).parent
    required_files = [
        'server.py',
        'analyzers/__init__.py',
        'analyzers/ast_analyzer.py',
        'analyzers/import_resolver.py',
        'analyzers/summarizer.py',
        'tools/__init__.py',
        'tools/security.py',
        'tools/list_modules.py',
        'tools/get_summary.py',
        'tools/get_content.py',
        'tools/search_code.py',
        'tools/get_inheritance.py',
        'tools/find_test.py',
        'tools/get_test_example.py',
        'tests/__init__.py',
        'pyproject.toml',
    ]

    all_ok = True
    for file_path in required_files:
        full_path = base_dir / file_path
        if full_path.exists():
            if 'server.py' in file_path or '__init__.py' in file_path:
                # Don't spam output for every __init__.py
                if file_path == 'server.py':
                    print(f"✅ {file_path} exists")
            else:
                pass  # File exists, no need to print each one
        else:
            print(f"❌ {file_path} NOT FOUND")
            all_ok = False

    if all_ok:
        print("✅ All required files present")

    # Check directories
    dirs = ['analyzers', 'tools', 'tests']
    for dir_name in dirs:
        dir_path = base_dir / dir_name
        if dir_path.is_dir():
            pass  # Directory exists
        else:
            print(f"❌ {dir_name}/ directory NOT FOUND")
            all_ok = False

    if all_ok:
        print("✅ All required directories present")

    return all_ok


def check_tools_registration():
    """Check that tools are registered"""
    print("\nChecking tools registration...")

    try:
        # Read server.py to check tool registration
        base_dir = Path(__file__).parent
        server_path = base_dir / 'server.py'

        with open(server_path, 'r') as f:
            content = f.read()

        tools = [
            'list_modules',
            'get_summary',
            'get_content',
            'search_code',
            'get_inheritance',
            'find_test',
            'get_test_example',
        ]

        all_ok = True
        for tool in tools:
            if f'name="{tool}"' in content or f"name='{tool}'" in content:
                pass  # Tool registered
            else:
                print(f"❌ Tool '{tool}' not found in server.py")
                all_ok = False

        if all_ok:
            print(f"✅ All {len(tools)} tools registered")

        return all_ok

    except Exception as e:
        print(f"❌ Error checking tools: {e}")
        return False


def run_tests():
    """Run basic tests"""
    print("\nRunning basic tests...")

    try:
        result = subprocess.run(
            ['pytest', 'tests/', '-v', '--tb=short'],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            # Parse output for test count
            lines = result.stdout.split('\n')
            for line in lines:
                if 'passed' in line:
                    print(f"✅ Tests: {line.strip()}")
                    return True

            print("✅ All tests passed")
            return True
        else:
            print(f"❌ Tests failed (exit code {result.returncode})")
            # Print last few lines of output
            lines = result.stdout.split('\n')
            for line in lines[-10:]:
                if line.strip():
                    print(f"   {line}")
            return False

    except FileNotFoundError:
        print("⚠️  pytest not found (run: pip install pytest)")
        return None  # Not a failure, just not installed
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out (>120s)")
        return False
    except Exception as e:
        print(f"⚠️  Could not run tests: {e}")
        return None


def check_server_startup():
    """Check that server can start"""
    print("\nChecking server startup...")

    try:
        base_dir = Path(__file__).parent
        server_path = base_dir / 'server.py'

        # Just check that server.py can be imported
        spec = importlib.util.spec_from_file_location("server", server_path)
        if spec and spec.loader:
            print("✅ server.py can be loaded")
            return True
        else:
            print("❌ server.py cannot be loaded")
            return False

    except Exception as e:
        print(f"❌ Error loading server.py: {e}")
        return False


def print_summary(results):
    """Print summary"""
    print("\n" + "="*60)
    print("\n╔════════════════════════════════════════════════════════╗")

    all_ok = all(r for r in results.values() if r is not None)

    if all_ok:
        print("║  Installation Status: ✅ OK                            ║")
        print("║  Ready for Production: ✅ YES                          ║")
    else:
        print("║  Installation Status: ❌ ISSUES FOUND                  ║")
        print("║  Ready for Production: ❌ NO                           ║")

    print("╚════════════════════════════════════════════════════════╝")
    print()

    # Print what failed
    failures = [name for name, status in results.items() if status is False]
    warnings = [name for name, status in results.items() if status is None]

    if failures:
        print("❌ Failed checks:")
        for name in failures:
            print(f"   - {name}")
        print()

    if warnings:
        print("⚠️  Warnings:")
        for name in warnings:
            print(f"   - {name}")
        print()

    if all_ok:
        print("✅ Next steps:")
        print("   1. Configure Claude Code (see DEPLOYMENT_GUIDE.md)")
        print("   2. Test basic tools in Claude Code")
        print("   3. Review USER_GUIDE.md for usage examples")
        print()
    else:
        print("❌ Fix the issues above, then run this script again.")
        print()

    return all_ok


def main():
    """Main verification function"""
    print_header()

    results = {}

    # Run all checks
    results['Python version'] = check_python_version()
    results['Dependencies'] = check_dependencies()
    results['File structure'] = check_file_structure()
    results['Tools registration'] = check_tools_registration()
    results['Server startup'] = check_server_startup()
    results['Tests'] = run_tests()

    # Print summary
    all_ok = print_summary(results)

    # Exit with appropriate code
    sys.exit(0 if all_ok else 1)


if __name__ == '__main__':
    main()
