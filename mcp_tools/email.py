"""
Email Model Context Protocol (MCP) Integration.
Connects to the Email FastMCP stdio server using langchain-mcp-adapters.
"""

import os
import sys

# Prevent mcp_tools from shadowing standard library 'email' package
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir in sys.path:
    sys.path.remove(_script_dir)

import asyncio
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool

_email_client = None
_email_tools: Optional[List[BaseTool]] = None
_lock = asyncio.Lock()


async def get_email_mcp_client():
    """Initializes and returns the MultiServerMCPClient for the Email MCP server."""
    global _email_client
    if _email_client is not None:
        return _email_client

    from langchain_mcp_adapters.client import MultiServerMCPClient

    server_script = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "email_server.py")
    )

    env = dict(os.environ)

    _email_client = MultiServerMCPClient(
        {
            "email": {
                "command": sys.executable,
                "args": [server_script],
                "transport": "stdio",
                "env": env,
            }
        }
    )
    return _email_client


async def get_email_tools() -> List[BaseTool]:
    """Retrieves all tools exposed by the Email MCP server."""
    global _email_tools
    if _email_tools is not None:
        return _email_tools

    async with _lock:
        if _email_tools is not None:
            return _email_tools

        client = await get_email_mcp_client()
        tools = await client.get_tools()
        _email_tools = tools
        return _email_tools


async def execute_email_tool(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """Executes an Email MCP tool over stdio transport."""
    tools = await get_email_tools()
    tool_map = {t.name: t for t in tools}

    if tool_name not in tool_map:
        return {
            "status": "error",
            "message": f"Tool '{tool_name}' not found. Available email tools: {list(tool_map.keys())}"
        }

    target_tool = tool_map[tool_name]
    try:
        result = await target_tool.ainvoke(tool_args)
        return {
            "status": "success",
            "result": result,
            "tool_name": tool_name
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Email tool execution error: {str(e)}",
            "tool_name": tool_name
        }
