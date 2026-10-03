"""
Email Sub-Agent.
Responsible for composing, drafting, sending (with Human-in-the-Loop confirmation),
and scheduling emails using persistent APScheduler with SQLite job store.
"""

import json
import datetime
from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage
from dateutil import parser as dt_parser
import zoneinfo

from config import config
from mcp_tools.email import execute_email_tool, get_email_tools


EMAIL_SYSTEM_PROMPT = """You are the Email Sub-Agent in an intelligent Multi-Agent System.
Your job is to compose emails, save drafts, send emails (requiring human confirmation), and schedule emails.

Current System Date/Time in User Timezone ({timezone}):
{current_time}

Available Email MCP Tools:
- `write_email`: Formats and composes an email. Args: {"recipient": "email@example.com", "subject": "...", "body": "..."}
- `create_draft`: Saves an email as a draft. Args: {"recipient": "email@example.com", "subject": "...", "body": "..."}
- `send_email`: Sends an email. Args: {"recipient": "email@example.com", "subject": "...", "body": "...", "confirmed": false}
- `schedule_email`: Schedules an email for future delivery. Args: {"recipient": "email@example.com", "subject": "...", "body": "...", "send_at": "ISO-8601", "timezone": "{timezone}"}
- `list_scheduled_emails`: Lists currently queued scheduled emails. Args: {}
- `cancel_scheduled_email`: Cancels a scheduled email. Args: {"job_id": "..."}

CRITICAL RULES:
1. For sending emails: Always start with confirmed=false unless the user prompt explicitly confirms a previously reviewed draft.
2. For scheduling emails: Parse natural language times (e.g., 'tomorrow at 9am', 'on Monday at 2pm') into exact ISO-8601 datetime strings based on current date/time.
3. If a tool call is needed, reply ONLY with a valid JSON block:
```json
{
  "tool": "tool_name",
  "args": { ... }
}
```
4. If no tool is needed, answer directly in markdown.
"""


def _get_current_time_str(tz_name: str = "Asia/Karachi") -> str:
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = datetime.timezone.utc
    now = datetime.datetime.now(tz)
    return now.strftime("%A, %B %d, %Y at %I:%M %p %Z")


def _call_gemini_llm(prompt: str) -> str:
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


async def run_email_agent(
    query: str,
    confirmed: bool = False,
    pending_action: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main execution pipeline for the Email Sub-Agent.
    """
    # If resuming a confirmed pending send:
    if pending_action and confirmed:
        tool_name = pending_action.get("tool", "send_email")
        tool_args = dict(pending_action.get("args", {}), confirmed=True)
        exec_res = await execute_email_tool(tool_name, tool_args)
        raw_text = str(exec_res.get("result", {}))
        return {
            "answer": (
                f"✅ **Email Sent Successfully!**\n\n"
                f"- **To:** {tool_args.get('recipient')}\n"
                f"- **Subject:** {tool_args.get('subject')}\n\n"
                f"Delivery Details:\n```json\n{raw_text[:1000]}\n```"
            ),
            "status": "success",
            "tool_used": tool_name
        }

    tz_name = config.TIMEZONE or "Asia/Karachi"
    curr_time_str = _get_current_time_str(tz_name)
    sys_prompt = EMAIL_SYSTEM_PROMPT.replace("{timezone}", tz_name).replace("{current_time}", curr_time_str)

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

    # If the user is requesting to send an email and confirmed is False:
    if tool_name == "send_email" and not confirmed:
        tool_args["confirmed"] = False
        exec_res = await execute_email_tool(tool_name, tool_args)
        raw_res = exec_res.get("result", "")
        return {
            "answer": (
                f"⚠️ **Email Confirmation Required Before Sending**\n\n"
                f"Please review the email details below before sending:\n\n"
                f"*   **To:** `{tool_args.get('recipient')}`\n"
                f"*   **Subject:** {tool_args.get('subject')}\n"
                f"*   **Body:**\n"
                f"    > {tool_args.get('body')}\n\n"
                f"Would you like me to send this email? Please reply **confirm** to send, or specify edits."
            ),
            "status": "requires_confirmation",
            "pending_action": {
                "agent": "email_agent",
                "tool": "send_email",
                "args": tool_args
            },
            "tool_used": "send_email"
        }

    # Execute tool
    exec_res = await execute_email_tool(tool_name, tool_args)
    if exec_res.get("status") == "error":
        return {
            "answer": f"Email action failed: {exec_res.get('message')}",
            "status": "error",
            "tool_used": tool_name
        }

    raw_result = exec_res.get("result")
    raw_text = str(raw_result)

    synth_prompt = f"""You are the Email Sub-Agent.
You executed the tool `{tool_name}` with args: {json.dumps(tool_args)}.
Output returned from email server:
{raw_text[:3000]}

User Query: {query}

Formulate a professional, clean markdown response confirming the outcome (e.g. drafted, scheduled, listed, or cancelled).
Include all key details (recipient, subject, scheduled time, job ID)."""

    final_answer = _call_gemini_llm(synth_prompt)

    return {
        "answer": final_answer,
        "status": "success",
        "tool_used": tool_name,
        "raw_data": raw_result
    }


def email_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node function for Email Sub-Agent."""
    messages = state.get("messages", [])
    if not messages:
        last_query = "List my scheduled emails"
    else:
        last_msg = messages[-1]
        last_query = getattr(last_msg, "content", str(last_msg))

    confirmed = state.get("confirmed", False)
    pending_action = state.get("pending_action")

    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    res = loop.run_until_complete(run_email_agent(last_query, confirmed=confirmed, pending_action=pending_action))

    return {
        "messages": [AIMessage(content=res.get("answer", ""))],
        "sender": "email_agent",
        "pending_action": res.get("pending_action")
    }
