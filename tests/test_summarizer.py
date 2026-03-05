import pytest
from analyzers.summarizer import Summarizer


def test_format_class_summary():
    """Test formatting class summary"""
    summarizer = Summarizer()

    class_info = {
        'name': 'Pod',
        'docstring': 'Pod resource management',
        'methods': [
            {'name': 'get_logs', 'signature': 'get_logs(self, container=None)'}
        ]
    }

    parent_classes = [
        {'parent_name': 'OCP', 'module': 'ocs_ci.ocs.ocp', 'file_path': '/fake/ocp.py'}
    ]

    inherited_methods = {
        'OCP': [
            {'name': 'exec_oc_cmd', 'signature': 'exec_oc_cmd(self, command)'}
        ]
    }

    summary = summarizer.format_class_summary(
        class_info,
        parent_classes,
        inherited_methods
    )

    assert summary['class_name'] == 'Pod'
    assert summary['docstring'] == 'Pod resource management'
    assert len(summary['own_methods']) == 1
    assert 'OCP' in summary['inherited_methods']


def test_format_file_summary():
    """Test formatting file summary"""
    summarizer = Summarizer()

    file_info = {
        'file_path': 'ocs_ci/ocs/resources/pod.py',
        'classes': [
            {'name': 'Pod', 'docstring': 'Pod class'}
        ],
        'functions': [
            {'name': 'get_all_pods', 'signature': 'get_all_pods()'}
        ]
    }

    summary = summarizer.format_file_summary(file_info)

    assert summary['file_path'] == 'ocs_ci/ocs/resources/pod.py'
    assert len(summary['classes']) == 1
    assert len(summary['functions']) == 1
