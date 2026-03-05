import pytest
import tempfile
import os
from analyzers.import_resolver import ImportResolver


@pytest.fixture
def temp_file_with_imports():
    """Create a temporary Python file with imports"""
    content = '''
from ocs_ci.ocs.ocp import OCP
from ocs_ci.ocs import constants
import logging
import time

class Pod(OCP):
    """Pod class"""
    pass
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path
    os.unlink(temp_path)


def test_extract_imports(temp_file_with_imports):
    """Test extracting import statements"""
    resolver = ImportResolver(repo_path="/fake/path")
    imports = resolver.extract_imports(temp_file_with_imports)

    assert 'OCP' in imports['import_map']
    assert imports['import_map']['OCP'] == 'ocs_ci.ocs.ocp'
    assert 'constants' in imports['import_map']
    assert 'logging' in imports['import_map']


def test_resolve_parent_class(temp_file_with_imports):
    """Test resolving parent class location"""
    # Create a fake repo structure
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp()

    try:
        # Create ocs_ci/ocs/ocp.py
        os.makedirs(os.path.join(temp_dir, 'ocs_ci', 'ocs'))
        ocp_file = os.path.join(temp_dir, 'ocs_ci', 'ocs', 'ocp.py')
        with open(ocp_file, 'w') as f:
            f.write('class OCP:\n    pass\n')

        resolver = ImportResolver(repo_path=temp_dir)
        imports = resolver.extract_imports(temp_file_with_imports)

        # Get class node for Pod
        import ast
        with open(temp_file_with_imports, 'r') as f:
            tree = ast.parse(f.read())

        class_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'Pod':
                class_node = node
                break

        parent_info = resolver.resolve_parent_class(
            class_node,
            imports['import_map'],
            temp_file_with_imports
        )

        assert parent_info is not None
        assert parent_info['parent_name'] == 'OCP'
        assert parent_info['module'] == 'ocs_ci.ocs.ocp'
        assert parent_info['found'] is True

    finally:
        shutil.rmtree(temp_dir)


@pytest.fixture
def temp_file_with_multiple_inheritance():
    """Create a file with multiple inheritance"""
    content = '''
from ocs_ci.tests.fixtures import ManageTest, E2ETest
from ocs_ci.utility.polarion import Polarion

class TestNodes(ManageTest, E2ETest, Polarion):
    """Test class with multiple inheritance"""
    pass
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path
    os.unlink(temp_path)


def test_resolve_multiple_parent_classes(temp_file_with_multiple_inheritance):
    """Test resolving all parent classes (multiple inheritance)"""
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp()

    try:
        # Create fake parent class files
        os.makedirs(os.path.join(temp_dir, 'ocs_ci', 'tests', 'fixtures'))
        os.makedirs(os.path.join(temp_dir, 'ocs_ci', 'utility'))

        with open(os.path.join(temp_dir, 'ocs_ci', 'tests', 'fixtures', '__init__.py'), 'w') as f:
            f.write('class ManageTest:\n    pass\nclass E2ETest:\n    pass\n')

        with open(os.path.join(temp_dir, 'ocs_ci', 'utility', 'polarion.py'), 'w') as f:
            f.write('class Polarion:\n    pass\n')

        resolver = ImportResolver(repo_path=temp_dir)
        imports = resolver.extract_imports(temp_file_with_multiple_inheritance)

        # Get class node
        import ast
        with open(temp_file_with_multiple_inheritance, 'r') as f:
            tree = ast.parse(f.read())

        class_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'TestNodes':
                class_node = node
                break

        # Should resolve ALL parents
        parent_classes = resolver.resolve_parent_classes(
            class_node,
            imports['import_map'],
            temp_file_with_multiple_inheritance
        )

        assert len(parent_classes) == 3
        assert parent_classes[0]['parent_name'] == 'ManageTest'
        assert parent_classes[1]['parent_name'] == 'E2ETest'
        assert parent_classes[2]['parent_name'] == 'Polarion'
        assert all(p['found'] for p in parent_classes)

    finally:
        shutil.rmtree(temp_dir)


def test_get_method_resolution_order():
    """Test MRO calculation"""
    # Simple MRO test
    resolver = ImportResolver(repo_path="/fake")

    parent_classes = [
        {'parent_name': 'ManageTest', 'file_path': '/fake/manage.py'},
        {'parent_name': 'E2ETest', 'file_path': '/fake/e2e.py'},
    ]

    mro = resolver.get_method_resolution_order(
        'TestNodes',
        parent_classes,
        '/fake/test.py'
    )

    # MRO should be: TestNodes, ManageTest, E2ETest, object
    class_names = [c['class'] for c in mro]
    assert class_names[0] == 'TestNodes'
    assert class_names[1] == 'ManageTest'
    assert class_names[2] == 'E2ETest'
    assert class_names[-1] == 'object'
