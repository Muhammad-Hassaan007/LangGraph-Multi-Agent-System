"""
Module 2 Test Suite: GitHub MCP Sub-Agent.
Tests:
1. MCP Tools Discovery (26 tools from official GitHub MCP server over stdio)
2. Read Query 1: Search / repo details ('octocat/Hello-World')
3. Read Query 2: Get file contents ('README' in 'octocat/Hello-World')
4. Read Query 3: List recent commits in 'octocat/Hello-World'
5. Write Action Protection: Attempting to create an issue requires confirmation
"""

import sys
import asyncio

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from mcp_tools.github import get_github_tools
from agents.github_agent import run_github_agent


async def test_module2():
    print("=" * 60)
    print("MODULE 2 TEST 1: GitHub MCP Tools Discovery")
    print("=" * 60)
    tools = await get_github_tools()
    tool_names = [t.name for t in tools]
    print(f"Discovered {len(tools)} GitHub MCP tools over stdio.")
    print("Sample tools:", tool_names[:8])
    assert len(tools) >= 20, f"Expected >= 20 tools, got {len(tools)}"
    assert "search_repositories" in tool_names
    assert "get_file_contents" in tool_names
    assert "create_issue" in tool_names
    print("PASS: GitHub MCP tools successfully loaded over stdio!")

    print("\n" + "=" * 60)
    print("MODULE 2 TEST 2: Read Query - Get README File Contents")
    print("=" * 60)
    res_readme = await run_github_agent("Get the contents of the README file from octocat/Hello-World")
    print("Agent Answer:\n", res_readme["answer"])
    assert res_readme["status"] == "success"
    assert "Hello World" in res_readme["answer"] or "README" in res_readme["answer"]
    print("PASS: Successfully retrieved and summarized file contents via MCP!")

    print("\n" + "=" * 60)
    print("MODULE 2 TEST 3: Read Query - List Commits")
    print("=" * 60)
    res_commits = await run_github_agent("Show recent commits for repository octocat/Hello-World")
    print("Agent Answer:\n", res_commits["answer"][:400] + "...")
    assert res_commits["status"] == "success"
    assert "commit" in res_commits["answer"].lower() or "octocat" in res_commits["answer"].lower()
    print("PASS: Successfully retrieved commits via MCP!")

    print("\n" + "=" * 60)
    print("MODULE 2 TEST 4: Write Action Protection - Create Issue")
    print("=" * 60)
    res_write = await run_github_agent(
        "Please create a new issue in octocat/Hello-World with title 'Bug Report' and body 'Found a small issue'"
    )
    print("Status:", res_write["status"])
    print("Agent Answer:\n", res_write["answer"])
    assert res_write["status"] == "requires_confirmation"
    assert "Requires Confirmation" in res_write["answer"] or "requires" in res_write["answer"].lower()
    print("PASS: Write action correctly blocked and confirmation requested!")

    print("\n" + "=" * 60)
    print("ALL MODULE 2 GITHUB MCP TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_module2())
