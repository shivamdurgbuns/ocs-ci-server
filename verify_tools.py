#!/usr/bin/env python3
"""
Verification script to test all 7 tools are properly integrated
"""

import tempfile
import os
import shutil
from pathlib import Path

# Import all tools
from tools.list_modules import list_modules_tool
from tools.get_summary import get_summary_tool
from tools.get_content import get_content_tool
from tools.search_code import search_code_tool
from tools.get_inheritance import get_inheritance_tool
from tools.find_test import find_test_tool
from tools.get_test_example import get_test_example_tool

# Import analyzers
from analyzers.ast_analyzer import ASTAnalyzer
from analyzers.import_resolver import ImportResolver
from analyzers.summarizer import Summarizer


def create_test_repo():
    """Create a minimal test repository"""
    temp_dir = tempfile.mkdtemp()

    # Create structure
    os.makedirs(os.path.join(temp_dir, 'ocs_ci'))
    os.makedirs(os.path.join(temp_dir, 'tests'))

    # Create a Python file
    with open(os.path.join(temp_dir, 'ocs_ci', 'example.py'), 'w') as f:
        f.write("""# Example module
class BaseClass:
    def base_method(self):
        pass

class ChildClass(BaseClass):
    def child_method(self):
        # TODO: Implement this
        pass
""")

    # Create a test file
    with open(os.path.join(temp_dir, 'tests', 'test_example.py'), 'w') as f:
        f.write("""# Test file
import pytest

@pytest.fixture
def my_fixture():
    return "data"

def test_example(my_fixture):
    # Test example functionality
    assert my_fixture == "data"
""")

    return temp_dir


def verify_all_tools():
    """Verify all 7 tools work"""

    print("Creating test repository...")
    repo_path = create_test_repo()

    try:
        # Initialize analyzers
        analyzer = ASTAnalyzer()
        resolver = ImportResolver(repo_path=repo_path)
        summarizer = Summarizer()

        results = {}

        # Test 1: list_modules
        print("\n1. Testing list_modules...")
        result = list_modules_tool(repo_path, path="", pattern="*")
        results['list_modules'] = 'error' not in result and 'items' in result
        print(f"   Result: {'✓ PASS' if results['list_modules'] else '✗ FAIL'}")

        # Test 2: get_summary
        print("\n2. Testing get_summary...")
        result = get_summary_tool(
            repo_path=repo_path,
            file_path="ocs_ci/example.py",
            class_name="ChildClass",
            analyzer=analyzer,
            resolver=resolver,
            summarizer=summarizer
        )
        results['get_summary'] = 'error' not in result
        print(f"   Result: {'✓ PASS' if results['get_summary'] else '✗ FAIL'}")

        # Test 3: get_content
        print("\n3. Testing get_content...")
        result = get_content_tool(
            repo_path=repo_path,
            file_path="ocs_ci/example.py"
        )
        results['get_content'] = 'error' not in result and 'content' in result
        print(f"   Result: {'✓ PASS' if results['get_content'] else '✗ FAIL'}")

        # Test 4: search_code
        print("\n4. Testing search_code...")
        result = search_code_tool(
            repo_path=repo_path,
            pattern="TODO",
            file_pattern="*.py"
        )
        results['search_code'] = 'error' not in result and 'matches' in result
        print(f"   Result: {'✓ PASS' if results['search_code'] else '✗ FAIL'}")

        # Test 5: get_inheritance
        print("\n5. Testing get_inheritance...")
        result = get_inheritance_tool(
            repo_path=repo_path,
            file_path="ocs_ci/example.py",
            class_name="ChildClass",
            analyzer=analyzer,
            resolver=resolver
        )
        results['get_inheritance'] = 'error' not in result and 'mro' in result
        print(f"   Result: {'✓ PASS' if results['get_inheritance'] else '✗ FAIL'}")

        # Test 6: find_test
        print("\n6. Testing find_test...")
        result = find_test_tool(
            repo_path=repo_path,
            test_name="test_example"
        )
        results['find_test'] = 'error' not in result and 'file_path' in result
        print(f"   Result: {'✓ PASS' if results['find_test'] else '✗ FAIL'}")

        # Test 7: get_test_example
        print("\n7. Testing get_test_example...")
        result = get_test_example_tool(
            repo_path=repo_path,
            pattern="example",
            max_results=5
        )
        results['get_test_example'] = 'error' not in result and 'examples' in result
        print(f"   Result: {'✓ PASS' if results['get_test_example'] else '✗ FAIL'}")

        # Summary
        print("\n" + "="*60)
        print("VERIFICATION SUMMARY")
        print("="*60)
        passed = sum(results.values())
        total = len(results)
        print(f"\nTools Verified: {passed}/{total}")

        for tool, success in results.items():
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"  {status}  {tool}")

        if passed == total:
            print("\n✓ All tools verified successfully!")
            return True
        else:
            print(f"\n✗ {total - passed} tool(s) failed verification")
            return False

    finally:
        # Cleanup
        shutil.rmtree(repo_path)
        print("\nCleaned up test repository")


if __name__ == "__main__":
    success = verify_all_tools()
    exit(0 if success else 1)
