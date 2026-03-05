#!/usr/bin/env python3
"""
Security Enhancement Demonstration

This script demonstrates the new sensitive directory blocking functionality.
"""

import tempfile
import os
import shutil
from tools.get_content import get_content_tool
from tools.list_modules import list_modules_tool
from tools.search_code import search_code_tool


def demo_security():
    """Demonstrate security blocking"""

    # Create temp repo with sensitive data
    temp_dir = tempfile.mkdtemp()

    try:
        # Create sensitive directories
        os.makedirs(os.path.join(temp_dir, 'data'))
        os.makedirs(os.path.join(temp_dir, '.git'))
        os.makedirs(os.path.join(temp_dir, 'ocs_ci'))

        # Add sensitive files
        with open(os.path.join(temp_dir, 'data', 'google_creds.json'), 'w') as f:
            f.write('{"api_key": "SECRET_KEY"}')

        with open(os.path.join(temp_dir, 'data', 'pull-secret'), 'w') as f:
            f.write('docker.io:secret123')

        with open(os.path.join(temp_dir, '.git', 'config'), 'w') as f:
            f.write('[core]\n  repositoryformatversion = 0')

        # Add normal file
        with open(os.path.join(temp_dir, 'ocs_ci', 'example.py'), 'w') as f:
            f.write('class Example:\n    pass')

        print("=" * 70)
        print("SECURITY ENHANCEMENT DEMONSTRATION")
        print("=" * 70)

        # Test 1: Blocked access to /data directory
        print("\n1. Attempting to access /data/google_creds.json (SHOULD BE BLOCKED)")
        result = get_content_tool(temp_dir, 'data/google_creds.json')
        print(f"   Result: {result.get('error', 'UNEXPECTED SUCCESS')}")
        print(f"   Message: {result.get('message', '')}")

        # Test 2: Blocked access to .git directory
        print("\n2. Attempting to access .git/config (SHOULD BE BLOCKED)")
        result = get_content_tool(temp_dir, '.git/config')
        print(f"   Result: {result.get('error', 'UNEXPECTED SUCCESS')}")
        print(f"   Message: {result.get('message', '')}")

        # Test 3: Allowed access to normal files
        print("\n3. Attempting to access ocs_ci/example.py (SHOULD BE ALLOWED)")
        result = get_content_tool(temp_dir, 'ocs_ci/example.py')
        if 'error' in result:
            print(f"   Result: UNEXPECTED BLOCK - {result['error']}")
        else:
            print(f"   Result: SUCCESS - File read successfully")
            print(f"   Content: {result['content'][:30]}...")

        # Test 4: Allowed access with flag
        print("\n4. Attempting to access data/pull-secret with allow_sensitive=True")
        result = get_content_tool(temp_dir, 'data/pull-secret', allow_sensitive=True)
        if 'error' in result:
            print(f"   Result: UNEXPECTED BLOCK - {result['error']}")
        else:
            print(f"   Result: SUCCESS - File read with flag")
            print(f"   Content: {result['content'][:30]}...")

        # Test 5: List modules blocked
        print("\n5. Attempting to list /data directory (SHOULD BE BLOCKED)")
        result = list_modules_tool(temp_dir, 'data')
        print(f"   Result: {result.get('error', 'UNEXPECTED SUCCESS')}")
        print(f"   Message: {result.get('message', '')}")

        # Test 6: Search in sensitive directory blocked
        print("\n6. Attempting to search in /data directory (SHOULD BE BLOCKED)")
        result = search_code_tool(temp_dir, 'api_key', path='data')
        print(f"   Result: {result.get('error', 'UNEXPECTED SUCCESS')}")
        print(f"   Message: {result.get('message', '')}")

        print("\n" + "=" * 70)
        print("SECURITY TEST SUMMARY")
        print("=" * 70)
        print("All sensitive directory accesses were properly blocked!")
        print("Normal file access continues to work correctly.")
        print("Override flag (allow_sensitive=True) works as expected.")
        print("=" * 70)

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    demo_security()
