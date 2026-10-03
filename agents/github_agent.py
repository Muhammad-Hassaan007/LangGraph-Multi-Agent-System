"""
GitHub Sub-Agent.
Responsible for interacting with GitHub repositories (issues, PRs, commits, code searches, file contents)
via the official GitHub Model Context Protocol (MCP) server over stdio.
Enforces Read-Only by default; any write action requires explicit user confirmation.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from config import config, is_valid_secret
from mcp_tools.github import (
    get_github_tools,
    execute_github_tool,
    GITHUB_WRITE_TOOLS,
)

logger = logging.getLogger("github_agent")

GITHUB_SYSTEM_PROMPT = """You are the GitHub Sub-Agent in an intelligent Multi-Agent System.
Your job is to answer GitHub questions and interact with repositories using the official GitHub Model Context Protocol (MCP) server.

You have access to real GitHub tools:
- `search_repositories`: Search for repositories. Args: {"query": "..."}
- `get_file_contents`: Read repository files or directories. Args: {"owner": "...", "repo": "...", "path": "..."}
- `list_commits`: List commits in a repo. Args: {"owner": "...", "repo": "...", "sha": "..."}
- `list_issues`: List issues. Args: {"owner": "...", "repo": "...", "state": "open|closed|all"}
- `get_issue`: Get issue details. Args: {"owner": "...", "repo": "...", "issue_number": int}
- `list_pull_requests`: List PRs. Args: {"owner": "...", "repo": "...", "state": "open|closed|all"}
- `get_pull_request`: Get PR details. Args: {"owner": "...", "repo": "...", "pull_number": int}
- `search_code`: Search code across repos. Args: {"query": "..."}
- `create_issue`: Create an issue (WRITE ACTION - Requires Confirmation). Args: {"owner": "...", "repo": "...", "title": "...", "body": "..."}
- `create_pull_request`: Create PR (WRITE ACTION - Requires Confirmation). Args: {"owner": "...", "repo": "...", "title": "...", "head": "...", "base": "..."}

INSTRUCTIONS:
1. Examine the user's request.
2. If a tool call is needed, output a valid JSON object with the following schema ONLY:
```json
{
  "tool": "tool_name",
  "args": { ... }
}
```
3. If no tool is needed (e.g. general greeting or explanation), answer directly in regular markdown text.
4. For write actions (create_issue, etc.), identify the parameters accurately so user confirmation can be requested before any execution.
"""


def _call_gemini_llm(prompt: str) -> str:
    """Calls Gemini LLM with retry across active models."""
    from google import genai
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    
    models = [config.GEMINI_CHAT_MODEL, "gemini-3.6-flash", "gemini-3.1-flash-lite-preview", "gemini-3-flash-preview"]
    models = list(dict.fromkeys(models))
    
    last_err = None
    for model_name in models:
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if resp.text:
                return resp.text.strip()
        except Exception as e:
            last_err = e
            continue
            
    raise last_err or RuntimeError("Failed to obtain response from Gemini.")


async def run_github_agent(
    query: str,
    confirmed: bool = False,
    pending_action: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main entrypoint for the GitHub Sub-Agent.
    Handles planning, MCP tool execution, confirmation checks, and response synthesis.
    """
    # If the user previously had a pending write action and is now confirming:
    if pending_action and confirmed:
        tool_name = pending_action.get("tool")
        tool_args = pending_action.get("args", {})
        result = await execute_github_tool(tool_name, tool_args, confirmed=True)
        if result.get("status") == "success":
            return {
                "answer": f"✅ Successfully executed `{tool_name}` with parameters: {json.dumps(tool_args)}.\n\nResult:\n```json\n{json.dumps(result.get('result', {}), indent=2)[:1500]}\n```",
                "status": "success",
                "tool_used": tool_name
            }
        else:
            return {
                "answer": f"❌ Action `{tool_name}` failed: {result.get('message')}",
                "status": "error",
                "tool_used": tool_name
            }

    # Step 1: Let LLM plan which GitHub MCP tool to use
    plan_prompt = f"""{GITHUB_SYSTEM_PROMPT}

User Request: {query}

Determine the single best tool and JSON arguments to satisfy this request, or answer directly if no tool is required."""

    llm_output = _call_gemini_llm(plan_prompt)

    # Step 2: Check if LLM requested a tool call
    tool_call = None
    if "```json" in llm_output:
        try:
            json_str = llm_output.split("```json")[1].split("```")[0].strip()
            tool_call = json.loads(json_str)
        except Exception:
            pass
    elif llm_output.strip().startswith("{") and llm_output.strip().endswith("}"):
        try:
            tool_call = json.loads(llm_output.strip())
        except Exception:
            pass

    if not tool_call or "tool" not in tool_call:
        # LLM answered directly without needing a tool
        return {
            "answer": llm_output,
            "status": "direct_answer",
            "tool_used": None
        }

    tool_name = tool_call.get("tool")
    tool_args = tool_call.get("args", {})
    print(f"[GitHubAgent] Planning tool: {tool_name}, args: {tool_args}")

    # Step 3: Check if the tool is a write action needing confirmation
    if tool_name in GITHUB_WRITE_TOOLS and not confirmed:
        return {
            "answer": (
                f"⚠️ **Action Requires Confirmation**\n\n"
                f"The GitHub sub-agent is requesting to execute a write operation:\n"
                f"- **Tool**: `{tool_name}`\n"
                f"- **Arguments**: ```json\n{json.dumps(tool_args, indent=2)}\n```\n\n"
                f"Please confirm whether you want to proceed with this action."
            ),
            "status": "requires_confirmation",
            "pending_action": {
                "agent": "github_agent",
                "tool": tool_name,
                "args": tool_args
            },
            "tool_used": tool_name
        }

    # Step 4: Execute the MCP tool over stdio
    tool_exec_result = await execute_github_tool(tool_name, tool_args, confirmed=confirmed)

    # Agentic resilience: If get_file_contents failed with Not Found, try alt path (with or without .md)
    if (
        tool_name == "get_file_contents"
        and tool_exec_result.get("status") == "error"
        and "Not Found" in tool_exec_result.get("message", "")
    ):
        orig_path = tool_args.get("path", "")
        alt_path = orig_path[:-3] if orig_path.endswith(".md") else f"{orig_path}.md"
        retry_args = dict(tool_args, path=alt_path)
        alt_result = await execute_github_tool(tool_name, retry_args, confirmed=confirmed)
        if alt_result.get("status") == "success":
            tool_exec_result = alt_result
            tool_args = retry_args

    if tool_exec_result.get("status") == "error":
        return {
            "answer": f"GitHub MCP tool execution failed: {tool_exec_result.get('message')}",
            "status": "error",
            "tool_used": tool_name
        }

    # Step 5: Synthesize tool output into a user-friendly response
    raw_result = tool_exec_result.get("result")
    raw_text = str(raw_result)[:4000]

    synth_prompt = f"""You are the GitHub Sub-Agent. 
You invoked the GitHub MCP tool `{tool_name}` with arguments `{json.dumps(tool_args)}`.
Here is the data returned from the GitHub MCP server:

{raw_text}

User Request: {query}

Please formulate a helpful, well-structured, clear markdown answer based on this GitHub data.
Include repository links, commit SHAs, issue numbers, or file contents where relevant.
Do not make up facts not present in the data."""

    final_answer = _call_gemini_llm(synth_prompt)

    return {
        "answer": final_answer,
        "status": "success",
        "tool_used": tool_name,
        "raw_data": raw_result
    }


def github_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for GitHub Sub-Agent integration.
    """
    messages = state.get("messages", [])
    if not messages:
        last_query = "List my repositories"
    else:
        last_msg = messages[-1]
        last_query = getattr(last_msg, "content", str(last_msg))

    confirmed = state.get("confirmed", False)
    pending_action = state.get("pending_action")

    # Run the async agent synchronously for LangGraph node
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    res = loop.run_until_complete(run_github_agent(last_query, confirmed=confirmed, pending_action=pending_action))

    answer = res.get("answer", "")
    new_pending = res.get("pending_action")

    return {
        "messages": [AIMessage(content=answer)],
        "sender": "github_agent",
        "pending_action": new_pending
    }
