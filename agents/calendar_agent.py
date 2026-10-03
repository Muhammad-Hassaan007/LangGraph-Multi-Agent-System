"""
Google Calendar Sub-Agent.
Responsible for reading meetings, creating meetings with conflict checking,
and handling natural language time parsing (e.g., 'tomorrow at 3pm') in the user's timezone.
"""

import json
import datetime
from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage
from dateutil import parser as dt_parser
from dateutil.relativedelta import relativedelta
import zoneinfo

from config import config
from mcp_tools.calendar import execute_calendar_tool, get_calendar_tools


CALENDAR_SYSTEM_PROMPT = """You are the Google Calendar Sub-Agent in an intelligent Multi-Agent System.
Your job is to manage calendar events, schedule meetings, and answer calendar questions.

Current System Date/Time in User Timezone ({timezone}):
{current_time}

Available Calendar MCP Tools:
- `list_upcoming_events`: List upcoming meetings. Args: {"max_results": int}
- `get_events_for_range`: Get events between two times. Args: {"start_time": "ISO-8601", "end_time": "ISO-8601"}
- `create_event`: Create an event. Args: {"title": "...", "start_time": "ISO-8601", "end_time": "ISO-8601", "attendees": ["email@example.com"], "timezone": "{timezone}", "check_conflicts": true}
- `update_event`: Update an event. Args: {"event_id": "...", "title": "...", "start_time": "...", "end_time": "..."}
- `delete_event`: Delete an event. Args: {"event_id": "..."}

CRITICAL INSTRUCTIONS:
1. Convert natural language times (e.g., 'tomorrow at 3pm', 'in 2 hours', 'Friday from 10am to 11am') into exact ISO-8601 strings based on the current date/time above. Default meeting duration is 1 hour if not specified.
2. If a tool call is needed, reply ONLY with a valid JSON block:
```json
{
  "tool": "tool_name",
  "args": { ... }
}
```
3. If no tool is needed, answer directly in markdown.
"""


def _get_current_time_str(tz_name: str = "Asia/Karachi") -> str:
    """Returns human-readable current time with timezone."""
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = datetime.timezone.utc
    now = datetime.datetime.now(tz)
    return now.strftime("%A, %B %d, %Y at %I:%M %p %Z")


def _call_gemini_llm(prompt: str) -> str:
    """Calls Gemini LLM with active model fallback."""
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
    raise last_err or RuntimeError("Failed to query Gemini LLM.")


async def run_calendar_agent(query: str) -> Dict[str, Any]:
    """
    Main execution pipeline for the Google Calendar Sub-Agent.
    """
    tz_name = config.TIMEZONE or "Asia/Karachi"
    curr_time_str = _get_current_time_str(tz_name)

    sys_prompt = CALENDAR_SYSTEM_PROMPT.replace("{timezone}", tz_name).replace("{current_time}", curr_time_str)

    plan_prompt = f"""{sys_prompt}

User Query: {query}

Determine the single best tool and JSON arguments to satisfy this request, or answer directly."""

    llm_output = _call_gemini_llm(plan_prompt)

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
        return {
            "answer": llm_output,
            "status": "direct_answer",
            "tool_used": None
        }

    tool_name = tool_call.get("tool")
    tool_args = tool_call.get("args", {})

    # Execute tool over stdio MCP
    exec_result = await execute_calendar_tool(tool_name, tool_args)

    if exec_result.get("status") == "error":
        return {
            "answer": f"Calendar operation failed: {exec_result.get('message')}",
            "status": "error",
            "tool_used": tool_name
        }

    raw_result = exec_result.get("result")
    raw_text = str(raw_result)

    # Check for conflict alert
    if "conflict_detected" in raw_text:
        return {
            "answer": (
                f"⚠️ **Scheduling Conflict Detected!**\n\n"
                f"You already have overlapping meetings during this time.\n"
                f"Conflict Details:\n```json\n{raw_text[:1500]}\n```\n"
                f"Please choose a different time slot or update your existing meeting."
            ),
            "status": "conflict",
            "tool_used": tool_name,
            "raw_data": raw_result
        }

    # Synthesize clean markdown response
    synth_prompt = f"""You are the Google Calendar Sub-Agent.
You ran `{tool_name}` with args: {json.dumps(tool_args)}.
Calendar Data returned:
{raw_text[:3000]}

User Query: {query}

Formulate a polite, clear, structured markdown response confirming the action or listing the events with their dates, times, and attendees.
Do not invent meetings not present in the data."""

    final_answer = _call_gemini_llm(synth_prompt)

    return {
        "answer": final_answer,
        "status": "success",
        "tool_used": tool_name,
        "raw_data": raw_result
    }


def calendar_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node function for Google Calendar Sub-Agent."""
    messages = state.get("messages", [])
    if not messages:
        last_query = "What meetings do I have coming up?"
    else:
        last_msg = messages[-1]
        last_query = getattr(last_msg, "content", str(last_msg))

    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    res = loop.run_until_complete(run_calendar_agent(last_query))
    return {
        "messages": [AIMessage(content=res.get("answer", ""))],
        "sender": "calendar_agent"
    }
