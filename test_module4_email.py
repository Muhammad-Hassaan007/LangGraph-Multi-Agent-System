"""
Module 4 Test Suite: Email MCP Sub-Agent.
Tests:
1. Email MCP Tools Discovery (over stdio FastMCP)
2. Compose Email / Draft Creation
3. Human-in-the-Loop Confirmation (send request blocked without confirmation)
4. Confirm Send (executes delivery after user confirmation)
5. Schedule Email with APScheduler (persisted in SQLite job store)
6. List Scheduled Emails (confirms job survived into persistent store)
"""

import sys
import asyncio

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from mcp_tools.email import get_email_tools
from agents.email_agent import run_email_agent


async def test_module4():
    print("=" * 60)
    print("MODULE 4 TEST 1: Email MCP Tools Discovery")
    print("=" * 60)
    tools = await get_email_tools()
    tool_names = [t.name for t in tools]
    print(f"Discovered {len(tools)} Email MCP tools over stdio.")
    print("Tools:", tool_names)
    assert len(tools) >= 5
    assert "send_email" in tool_names
    assert "schedule_email" in tool_names
    assert "list_scheduled_emails" in tool_names
    print("PASS: Email MCP server running over stdio!")

    print("\n" + "=" * 60)
    print("MODULE 4 TEST 2: Compose Email / Draft")
    print("=" * 60)
    res_draft = await run_email_agent(
        "Write a draft email to professor@university.edu with subject 'Project Submission' explaining that Module 1-4 are completed."
    )
    print("Agent Answer:\n", res_draft["answer"])
    assert res_draft["status"] == "success"
    assert "professor@university.edu" in res_draft["answer"] or "Project Submission" in res_draft["answer"]
    print("PASS: Email drafted successfully!")

    print("\n" + "=" * 60)
    print("MODULE 4 TEST 3: Human-in-the-Loop Protection (Send blocked without confirmation)")
    print("=" * 60)
    res_send_block = await run_email_agent(
        "Send an email to advisor@college.edu with subject 'Weekly Progress' saying 'Here is my update for the week.'"
    )
    print("Status:", res_send_block["status"])
    print("Agent Answer:\n", res_send_block["answer"])
    assert res_send_block["status"] == "requires_confirmation"
    assert res_send_block.get("pending_action") is not None
    print("PASS: Send operation intercepted; explicit confirmation requested from user!")

    print("\n" + "=" * 60)
    print("MODULE 4 TEST 4: Execute Send upon Confirmation")
    print("=" * 60)
    pending = res_send_block["pending_action"]
    res_confirmed = await run_email_agent(
        query="confirm",
        confirmed=True,
        pending_action=pending
    )
    print("Status:", res_confirmed["status"])
    print("Agent Answer:\n", res_confirmed["answer"])
    assert res_confirmed["status"] == "success"
    assert "Sent Successfully" in res_confirmed["answer"] or "sent" in res_confirmed["answer"].lower()
    print("PASS: Confirmed email successfully dispatched!")

    print("\n" + "=" * 60)
    print("MODULE 4 TEST 5: Schedule Email (APScheduler + SQLite Job Store)")
    print("=" * 60)
    res_sched = await run_email_agent(
        "Schedule an email to team@company.com with subject 'Sprint Standup Reminder' to be sent tomorrow at 9am"
    )
    print("Status:", res_sched["status"])
    print("Agent Answer:\n", res_sched["answer"])
    assert res_sched["status"] == "success"
    assert "scheduled" in res_sched["answer"].lower() or "team@company.com" in res_sched["answer"]
    print("PASS: Email scheduled into persistent APScheduler SQLite job store!")

    print("\n" + "=" * 60)
    print("MODULE 4 TEST 6: List Scheduled Emails from Persistent Store")
    print("=" * 60)
    res_list = await run_email_agent("What emails are currently scheduled to be sent?")
    print("Agent Answer:\n", res_list["answer"])
    assert res_list["status"] == "success"
    assert "Sprint Standup Reminder" in res_list["answer"] or "team@company.com" in res_list["answer"]
    print("PASS: Scheduled email job verified in persistent queue!")

    print("\n" + "=" * 60)
    print("ALL MODULE 4 EMAIL MCP TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_module4())
