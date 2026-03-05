import pytest
from server import OCCIMCPServer


def test_server_initialization():
    """Test server can be initialized"""
    server = OCCIMCPServer(repo_path="/fake/path")
    assert server.repo_path == "/fake/path"
    assert server.analyzer is not None
    assert server.resolver is not None


def test_server_has_required_attributes():
    """Test server has all required components"""
    server = OCCIMCPServer(repo_path="/fake/path")
    assert hasattr(server, 'analyzer')
    assert hasattr(server, 'resolver')
    assert hasattr(server, 'summarizer')
