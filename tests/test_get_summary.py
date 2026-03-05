import pytest
import tempfile
import os
import shutil
from tools.get_summary import get_summary_tool
from analyzers.ast_analyzer import ASTAnalyzer
from analyzers.import_resolver import ImportResolver
from analyzers.summarizer import Summarizer


@pytest.fixture
def temp_repo_with_classes():
    """Create repo with class inheritance"""
    temp_dir = tempfile.mkdtemp()

    # Create base class
    os.makedirs(os.path.join(temp_dir, 'ocs_ci', 'ocs'))
    with open(os.path.join(temp_dir, 'ocs_ci', 'ocs', 'ocp.py'), 'w') as f:
        f.write('''
class OCP:
    """OCP base class"""

    def exec_oc_cmd(self, command):
        """Execute oc command"""
        pass

    def wait_for_resource(self):
        """Wait for resource"""
        pass
''')

    # Create child class
    os.makedirs(os.path.join(temp_dir, 'ocs_ci', 'ocs', 'resources'))
    with open(os.path.join(temp_dir, 'ocs_ci', 'ocs', 'resources', 'pod.py'), 'w') as f:
        f.write('''
from ocs_ci.ocs.ocp import OCP

class Pod(OCP):
    """Pod resource"""

    def get_logs(self, container=None):
        """Get pod logs"""
        pass
''')

    yield temp_dir
    shutil.rmtree(temp_dir)


def test_get_file_summary(temp_repo_with_classes):
    """Test getting file-level summary"""
    analyzer = ASTAnalyzer()
    resolver = ImportResolver(temp_repo_with_classes)
    summarizer = Summarizer()

    result = get_summary_tool(
        repo_path=temp_repo_with_classes,
        file_path='ocs_ci/ocs/resources/pod.py',
        class_name=None,
        analyzer=analyzer,
        resolver=resolver,
        summarizer=summarizer
    )

    assert 'classes' in result
    assert len(result['classes']) == 1
    assert result['classes'][0]['name'] == 'Pod'


def test_get_class_summary_with_inheritance(temp_repo_with_classes):
    """Test getting class summary with inherited methods"""
    analyzer = ASTAnalyzer()
    resolver = ImportResolver(temp_repo_with_classes)
    summarizer = Summarizer()

    result = get_summary_tool(
        repo_path=temp_repo_with_classes,
        file_path='ocs_ci/ocs/resources/pod.py',
        class_name='Pod',
        analyzer=analyzer,
        resolver=resolver,
        summarizer=summarizer
    )

    assert result['class_name'] == 'Pod'
    assert len(result['own_methods']) == 1
    assert result['own_methods'][0]['name'] == 'get_logs'

    # Should have inherited methods from OCP
    assert 'inherited_methods' in result
    assert 'OCP' in result['inherited_methods']
    assert len(result['inherited_methods']['OCP']) == 2


def test_path_traversal_blocked(temp_repo_with_classes):
    """Test that path traversal attacks are blocked"""
    analyzer = ASTAnalyzer()
    resolver = ImportResolver(temp_repo_with_classes)
    summarizer = Summarizer()

    result = get_summary_tool(
        repo_path=temp_repo_with_classes,
        file_path='../../../etc/passwd',
        class_name=None,
        analyzer=analyzer,
        resolver=resolver,
        summarizer=summarizer
    )

    assert 'error' in result
    assert result['error'] == 'SecurityError'


def test_sensitive_directory_blocked_data(temp_repo_with_classes):
    """Test that /data directory access is blocked"""
    # Create data directory with Python file
    os.makedirs(os.path.join(temp_repo_with_classes, 'data'))
    with open(os.path.join(temp_repo_with_classes, 'data', 'config.py'), 'w') as f:
        f.write('class Config:\n    pass\n')

    analyzer = ASTAnalyzer()
    resolver = ImportResolver(temp_repo_with_classes)
    summarizer = Summarizer()

    result = get_summary_tool(
        repo_path=temp_repo_with_classes,
        file_path='data/config.py',
        class_name=None,
        analyzer=analyzer,
        resolver=resolver,
        summarizer=summarizer
    )

    assert 'error' in result
    assert result['error'] == 'AccessDenied'
    assert 'sensitive' in result['message'].lower()


def test_sensitive_directory_allowed_with_flag(temp_repo_with_classes):
    """Test that sensitive directories can be accessed with flag"""
    # Create data directory with Python file
    os.makedirs(os.path.join(temp_repo_with_classes, 'data'))
    with open(os.path.join(temp_repo_with_classes, 'data', 'config.py'), 'w') as f:
        f.write('class Config:\n    pass\n')

    analyzer = ASTAnalyzer()
    resolver = ImportResolver(temp_repo_with_classes)
    summarizer = Summarizer()

    result = get_summary_tool(
        repo_path=temp_repo_with_classes,
        file_path='data/config.py',
        class_name=None,
        analyzer=analyzer,
        resolver=resolver,
        summarizer=summarizer,
        allow_sensitive=True
    )

    assert 'classes' in result
    assert len(result['classes']) == 1
    assert result['classes'][0]['name'] == 'Config'
