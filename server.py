#!/usr/bin/env python3
"""
OCS-CI MCP Server

Model Context Protocol server for ocs-ci repository analysis.
Provides token-efficient code exploration and test failure analysis.
"""

import sys
import argparse
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from analyzers.ast_analyzer import ASTAnalyzer
from analyzers.import_resolver import ImportResolver
from analyzers.summarizer import Summarizer
from tools.list_modules import list_modules_tool
from tools.get_summary import get_summary_tool
from tools.get_content import get_content_tool
from tools.search_code import search_code_tool
from tools.get_inheritance import get_inheritance_tool
from tools.find_test import find_test_tool
from tools.get_test_example import get_test_example_tool
from tools.get_conf_file import get_conf_file_tool
from tools.get_conftest import get_conftest_tool
from tools.get_deployment_module import get_deployment_module_tool
from tools.get_resource_module import get_resource_module_tool
from tools.get_helper_module import get_helper_module_tool
from tools.get_utility_module import get_utility_module_tool

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    import mcp.types as types
except ImportError:
    print("Error: MCP package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)


class OCCIMCPServer:
    """OCS-CI MCP Server implementation"""

    def __init__(self, repo_path: str, allow_sensitive: bool = False):
        """
        Initialize MCP server

        Args:
            repo_path: Path to ocs-ci repository
            allow_sensitive: If True, allow access to sensitive directories (data, .git, etc.)
        """
        self.repo_path = repo_path
        self.allow_sensitive = allow_sensitive
        self.analyzer = ASTAnalyzer()
        self.resolver = ImportResolver(repo_path=repo_path)
        self.summarizer = Summarizer()

        # MCP server instance
        self.server = Server("ocs-ci-server")

        # Register tools
        self._register_tools()
        self._register_tool_handlers()

    def _register_tools(self):
        """Register all MCP tools"""

        @self.server.list_tools()
        async def list_tools() -> list[types.Tool]:
            """List available tools"""
            return [
                types.Tool(
                    name="list_modules",
                    description="List files and directories in ocs-ci repository",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path relative to ocs-ci root (default: root)",
                                "default": ""
                            },
                            "pattern": {
                                "type": "string",
                                "description": "Filter pattern (e.g., '*.py')",
                                "default": "*"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="get_summary",
                    description="Get summary of Python file or class with inheritance",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to Python file (relative to ocs-ci root)"
                            },
                            "class_name": {
                                "type": "string",
                                "description": "Class name (optional, for class-level summary)"
                            }
                        },
                        "required": ["file_path"]
                    }
                ),
                types.Tool(
                    name="get_content",
                    description="Read file content with optional line range",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to file (relative to ocs-ci root)"
                            },
                            "start_line": {
                                "type": "integer",
                                "description": "Starting line number (1-indexed, optional)"
                            },
                            "end_line": {
                                "type": "integer",
                                "description": "Ending line number (1-indexed, optional)"
                            }
                        },
                        "required": ["file_path"]
                    }
                ),
                types.Tool(
                    name="search_code",
                    description="Search for regex pattern in code files",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Regex pattern to search for"
                            },
                            "file_pattern": {
                                "type": "string",
                                "description": "File glob pattern (default: '*.py')",
                                "default": "*.py"
                            },
                            "context_lines": {
                                "type": "integer",
                                "description": "Number of context lines (default: 2)",
                                "default": 2
                            },
                            "path": {
                                "type": "string",
                                "description": "Path to search within (default: root)",
                                "default": ""
                            }
                        },
                        "required": ["pattern"]
                    }
                ),
                types.Tool(
                    name="get_inheritance",
                    description="Get full inheritance chain with methods and conflicts",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to Python file (relative to ocs-ci root)"
                            },
                            "class_name": {
                                "type": "string",
                                "description": "Class name to analyze"
                            }
                        },
                        "required": ["file_path", "class_name"]
                    }
                ),
                types.Tool(
                    name="find_test",
                    description="Find test by name or pytest nodeid",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "test_name": {
                                "type": "string",
                                "description": "Test name or nodeid (e.g., 'test_foo' or 'path/file.py::test_foo')"
                            }
                        },
                        "required": ["test_name"]
                    }
                ),
                types.Tool(
                    name="get_test_example",
                    description="Find example tests matching pattern or using specific fixture",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Pattern to search for in test names or content"
                            },
                            "fixture_name": {
                                "type": "string",
                                "description": "Fixture name to filter by (optional)"
                            },
                            "path": {
                                "type": "string",
                                "description": "Path to search within (default: root)",
                                "default": ""
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of examples (default: 5)",
                                "default": 5
                            }
                        },
                        "required": ["pattern"]
                    }
                ),
                types.Tool(
                    name="get_deployment_module",
                    description="List deployment modules in ocs_ci/deployment/ with descriptions",
                    inputSchema={
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
                ),
                types.Tool(
                    name="get_resource_module",
                    description="List resource modules in ocs_ci/ocs/resources/ with descriptions",
                    inputSchema={
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
                ),
                types.Tool(
                    name="get_helper_module",
                    description="List helper modules in ocs_ci/helpers/ with descriptions",
                    inputSchema={
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
                ),
                types.Tool(
                    name="get_utility_module",
                    description="List utility modules in ocs_ci/utility/ with descriptions",
                    inputSchema={
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
                ),
                types.Tool(
                    name="get_conftest",
                    description="List all conftest.py files in tests/ directory tree with descriptions",
                    inputSchema={
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
                ),
                types.Tool(
                    name="get_conf_file",
                    description="List configuration files in conf/ directory with descriptions",
                    inputSchema={
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
                ),
            ]

    def _register_tool_handlers(self):
        """Register tool call handlers"""

        @self.server.call_tool()
        async def call_tool(
            name: str,
            arguments: dict
        ) -> list[types.TextContent]:
            """Handle tool calls"""

            if name == "list_modules":
                result = list_modules_tool(
                    repo_path=self.repo_path,
                    path=arguments.get('path', ''),
                    pattern=arguments.get('pattern', '*'),
                    allow_sensitive=self.allow_sensitive
                )

                import json
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            elif name == "get_summary":
                result = get_summary_tool(
                    repo_path=self.repo_path,
                    file_path=arguments.get('file_path'),
                    class_name=arguments.get('class_name'),
                    analyzer=self.analyzer,
                    resolver=self.resolver,
                    summarizer=self.summarizer,
                    allow_sensitive=self.allow_sensitive
                )

                import json
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            elif name == "get_content":
                result = get_content_tool(
                    repo_path=self.repo_path,
                    file_path=arguments.get('file_path'),
                    start_line=arguments.get('start_line'),
                    end_line=arguments.get('end_line'),
                    allow_sensitive=self.allow_sensitive
                )

                import json
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            elif name == "search_code":
                result = search_code_tool(
                    repo_path=self.repo_path,
                    pattern=arguments.get('pattern'),
                    file_pattern=arguments.get('file_pattern', '*.py'),
                    context_lines=arguments.get('context_lines', 2),
                    path=arguments.get('path', ''),
                    allow_sensitive=self.allow_sensitive
                )

                import json
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            elif name == "get_inheritance":
                result = get_inheritance_tool(
                    repo_path=self.repo_path,
                    file_path=arguments.get('file_path'),
                    class_name=arguments.get('class_name'),
                    analyzer=self.analyzer,
                    resolver=self.resolver,
                    allow_sensitive=self.allow_sensitive
                )

                import json
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            elif name == "find_test":
                result = find_test_tool(
                    repo_path=self.repo_path,
                    test_name=arguments.get('test_name'),
                    allow_sensitive=self.allow_sensitive
                )

                import json
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            elif name == "get_test_example":
                result = get_test_example_tool(
                    repo_path=self.repo_path,
                    pattern=arguments.get('pattern'),
                    fixture_name=arguments.get('fixture_name'),
                    path=arguments.get('path', ''),
                    max_results=arguments.get('max_results', 5),
                    allow_sensitive=self.allow_sensitive
                )

                import json
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

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

            elif name == "get_resource_module":
                result = get_resource_module_tool(
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

            elif name == "get_helper_module":
                result = get_helper_module_tool(
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

            elif name == "get_utility_module":
                result = get_utility_module_tool(
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

            elif name == "get_conftest":
                result = get_conftest_tool(
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

            elif name == "get_conf_file":
                result = get_conf_file_tool(
                    repo_path=self.repo_path,
                    pattern=arguments.get('pattern', '*'),
                    search_text=arguments.get('search_text'),
                    allow_sensitive=self.allow_sensitive
                )

                import json
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="OCS-CI MCP Server")
    parser.add_argument(
        "--repo-path",
        required=True,
        help="Path to ocs-ci repository"
    )
    parser.add_argument(
        "--allow-sensitive",
        action="store_true",
        help="Allow access to sensitive directories (data, .git, etc.) - USE WITH CAUTION"
    )

    args = parser.parse_args()

    # Validate repo path
    repo_path = Path(args.repo_path)
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}", file=sys.stderr)
        sys.exit(1)

    # Create and run server
    server = OCCIMCPServer(repo_path=str(repo_path), allow_sensitive=args.allow_sensitive)

    print(f"Starting OCS-CI MCP Server", file=sys.stderr)
    print(f"Repository: {repo_path}", file=sys.stderr)
    if args.allow_sensitive:
        print("WARNING: Sensitive directory access ENABLED", file=sys.stderr)

    asyncio.run(server.run())


if __name__ == "__main__":
    main()
