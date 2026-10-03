"""
Google Calendar Model Context Protocol (MCP) Integration.
Connects to the Calendar FastMCP stdio server using langchain-mcp-adapters.
"""

import os
import sys
import asyncio
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool

_calendar_client = None
_calendar_tools: Optional[List[BaseTool]] = None
_lock = asyncio.Lock()


async def get_calendar_mcp_client():
    """Initializes and returns the MultiServerMCPClient for the Calendar MCP server."""
    global _calendar_client
    if _calendar_client is not None:
        return _calendar_client

    from langchain_mcp_adapters.client import MultiServerMCPClient

    server_script = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "calendar_server.py")
    )

    env = dict(os.environ)

    _calendar_client = MultiServerMCPClient(
        {
            "calendar": {
                "command": sys.executable,
                "args": [server_script],
                "transport": "stdio",
                "env": env,
            }
        }
    )
    return _calendar_client


async def get_calendar_tools() -> List[BaseTool]:
    """Retrieves all tools exposed by the Calendar MCP server."""
    global _calendar_tools
    if _calendar_tools is not None:
        return _calendar_tools

    async with _lock:
        if _calendar_tools is not None:
            return _calendar_tools

        client = await get_calendar_mcp_client()
        tools = await client.get_tools()
        _calendar_tools = tools
        return _calendar_tools


async def execute_calendar_tool(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """Executes a Calendar MCP tool over stdio transport."""
    tools = await get_calendar_tools()
    tool_map = {t.name: t for t in tools}

    if tool_name not in tool_map:
        return {
            "status": "error",
            "message": f"Tool '{tool_name}' not found. Available tools: {list(tool_map.keys())}"
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
            "message": f"Calendar tool execution error: {str(e)}",
            "tool_name": tool_name
        }
