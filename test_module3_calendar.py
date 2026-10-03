"""
Module 3 Test Suite: Google Calendar MCP Sub-Agent.
Tests:
1. MCP Tools Discovery (over stdio FastMCP)
2. Create Event with Natural Language Time ("tomorrow at 3pm")
3. Conflict Detection Alert (creating another event at the exact same time)
4. List Upcoming Events (retrieves the scheduled event)
"""

import sys
import asyncio

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from mcp_tools.calendar import get_calendar_tools
from agents.calendar_agent import run_calendar_agent


async def test_module3():
    print("=" * 60)
    print("MODULE 3 TEST 1: Calendar MCP Tools Discovery")
    print("=" * 60)
    tools = await get_calendar_tools()
    tool_names = [t.name for t in tools]
    print(f"Discovered {len(tools)} Calendar MCP tools over stdio.")
    print("Tools:", tool_names)
    assert len(tools) >= 4
    assert "list_upcoming_events" in tool_names
    assert "create_event" in tool_names
    print("PASS: Calendar MCP server running over stdio!")

    print("\n" + "=" * 60)
    print("MODULE 3 TEST 2: Schedule Event with Natural Language Time")
    print("=" * 60)
    res_create = await run_calendar_agent(
        "Schedule a meeting called 'AI Project Review' tomorrow at 3pm with student@university.edu"
    )
    print("Agent Answer:\n", res_create["answer"])
    assert res_create["status"] == "success"
    assert "AI Project Review" in res_create["answer"] or "scheduled" in res_create["answer"].lower() or "created" in res_create["answer"].lower()
    print("PASS: Event successfully scheduled via natural language time resolution!")

    print("\n" + "=" * 60)
    print("MODULE 3 TEST 3: Conflict Detection Alert")
    print("=" * 60)
    # Attempt to schedule overlapping meeting at the exact same time
    res_conflict = await run_calendar_agent(
        "Schedule another meeting called 'Dentist Appointment' tomorrow at 3:30pm"
    )
    print("Status:", res_conflict["status"])
    print("Agent Answer:\n", res_conflict["answer"])
    assert res_conflict["status"] == "conflict"
    assert "conflict" in res_conflict["answer"].lower()
    print("PASS: Overlap detected and conflict alert reported accurately!")

    print("\n" + "=" * 60)
    print("MODULE 3 TEST 4: List Upcoming Events")
    print("=" * 60)
    res_list = await run_calendar_agent("What meetings do I have scheduled?")
    print("Agent Answer:\n", res_list["answer"])
    assert res_list["status"] == "success"
    assert "AI Project Review" in res_list["answer"]
    print("PASS: Upcoming events accurately retrieved from calendar!")

    print("\n" + "=" * 60)
    print("ALL MODULE 3 CALENDAR MCP TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_module3())
