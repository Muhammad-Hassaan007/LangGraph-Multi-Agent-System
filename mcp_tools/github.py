"""
GitHub Model Context Protocol (MCP) Integration.
Connects to the official GitHub MCP server over stdio using the official mcp SDK
and langchain-mcp-adapters to expose real GitHub tools.
"""

import os
import sys
import shutil
import asyncio
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool

from config import config

# List of tools that modify state / create resources on GitHub
GITHUB_WRITE_TOOLS = {
    "create_or_update_file",
    "create_repository",
    "push_files",
    "create_issue",
    "create_pull_request",
    "fork_repository",
    "create_branch",
    "update_issue",
    "add_issue_comment",
    "create_pull_request_review",
    "merge_pull_request",
    "update_pull_request_branch",
}

_github_client = None
_github_tools: Optional[List[BaseTool]] = None
_lock = asyncio.Lock()


def get_node_path() -> str:
    """Finds the node executable on the system."""
    node_path = shutil.which("node")
    if not node_path:
        # Fallbacks for standard Windows locations
        candidates = [
            r"C:\Program Files\nodejs\node.exe",
            r"C:\Program Files (x86)\nodejs\node.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return "node"
    return node_path


def get_github_server_script() -> str:
    """Finds the installed @modelcontextprotocol/server-github entrypoint."""
    # Look in project root node_modules
    local_script = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "node_modules",
            "@modelcontextprotocol",
            "server-github",
            "dist",
            "index.js",
        )
    )
    if os.path.exists(local_script):
        return local_script

    # Fallback to frontend node_modules if present
    frontend_script = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "frontend",
            "node_modules",
            "@modelcontextprotocol",
            "server-github",
            "dist",
            "index.js",
        )
    )
    if os.path.exists(frontend_script):
        return frontend_script

    return local_script


def get_github_token() -> str:
    """Retrieves GitHub token from environment."""
    return (
        os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        or os.getenv("GITHUB_TOKEN")
        or config.GITHUB_PERSONAL_ACCESS_TOKEN
        or config.GITHUB_TOKEN
        or ""
    )


async def get_github_mcp_client():
    """Initializes and returns the MultiServerMCPClient instance for GitHub."""
    global _github_client
    if _github_client is not None:
        return _github_client

    from langchain_mcp_adapters.client import MultiServerMCPClient

    node_cmd = get_node_path()
    server_script = get_github_server_script()
    token = get_github_token()

    # Pass full environment including PATH so node can resolve dependencies
    env = dict(os.environ)
    if token:
        env["GITHUB_PERSONAL_ACCESS_TOKEN"] = token
        env["GITHUB_TOKEN"] = token

    _github_client = MultiServerMCPClient(
        {
            "github": {
                "command": node_cmd,
                "args": [server_script],
                "transport": "stdio",
                "env": env,
            }
        }
    )
    return _github_client


async def get_github_tools() -> List[BaseTool]:
    """
    Connects to the official GitHub MCP server and returns all 26 tools converted
    into LangChain-compatible Tool objects.
    """
    global _github_tools
    if _github_tools is not None:
        return _github_tools

    async with _lock:
        if _github_tools is not None:
            return _github_tools

        client = await get_github_mcp_client()
        tools = await client.get_tools()
        _github_tools = tools
        return _github_tools


async def execute_github_tool(tool_name: str, tool_args: Dict[str, Any], confirmed: bool = False) -> Dict[str, Any]:
    """
    Safely executes a GitHub MCP tool.
    If the tool is a write action and confirmed=False, returns a confirmation requirement
    WITHOUT executing the tool.
    """
    # Enforce Read-Only by default on write actions
    if tool_name in GITHUB_WRITE_TOOLS and not confirmed:
        return {
            "status": "requires_confirmation",
            "action": tool_name,
            "args": tool_args,
            "message": (
                f"⚠️ Action '{tool_name}' requires your confirmation before execution.\n"
                f"Parameters: {tool_args}\n"
                f"Please reply 'confirm' to execute this action, or 'cancel' to abort."
            ),
        }

    tools = await get_github_tools()
    tool_map = {t.name: t for t in tools}

    if tool_name not in tool_map:
        return {
            "status": "error",
            "message": f"Tool '{tool_name}' not found among GitHub MCP tools. Available tools: {list(tool_map.keys())}",
        }

    target_tool = tool_map[tool_name]
    try:
        result = await target_tool.ainvoke(tool_args)
        return {
            "status": "success",
            "result": result,
            "tool_name": tool_name,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"GitHub MCP tool execution failed: {str(e)}",
            "tool_name": tool_name,
        }
