"""
Supervisor Agent for LangGraph Multi-Agent System.
Orchestrates routing between:
1. 'rag_agent': Document retrieval and Q&A over Supabase pgvector
2. 'github_agent': GitHub MCP tools (code, PRs, issues, commits, repos)
3. 'calendar_agent': Google Calendar MCP tools (events, meetings, conflict detection)
4. 'email_agent': Email MCP tools (drafting, sending, persistent APScheduler)
5. 'FINISH': Conversation turn complete or direct conversational response.
Supports multi-turn chaining and human-in-the-loop confirmation.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, END

from config import config
from state import AgentState
from agents.rag_agent import answer_document_query
from agents.github_agent import run_github_agent
from agents.calendar_agent import run_calendar_agent
from agents.email_agent import run_email_agent

logger = logging.getLogger("supervisor")

SUPERVISOR_ROUTING_PROMPT = """You are the Supervisor Agent of a powerful Multi-Agent Assistant.
You oversee four specialized sub-agents:
1. `rag_agent`: Answers questions strictly grounded in uploaded PDF documents via Supabase vector store.
2. `github_agent`: Queries GitHub repositories, commits, issues, PRs, and reads file contents via GitHub MCP server.
3. `calendar_agent`: Manages calendar events, checks scheduling conflicts, and schedules meetings.
4. `email_agent`: Composes drafts, sends emails (requiring human confirmation), and schedules emails via persistent scheduler.

RULES FOR ROUTING:
1. Examine the conversation history and the latest user request.
2. If the user request is a general greeting, clarification, or general conversation (e.g. 'Hello', 'What can you do?'), you should answer directly and route to `FINISH`.
3. If the user asks about a document, PDF, or uploaded file, route to `rag_agent`.
4. If the user asks about GitHub (repositories, code search, pull requests, issues, commits, repo files), route to `github_agent`.
5. If the user asks about calendar (meetings, schedule, appointments, events, conflicts), route to `calendar_agent`.
6. If the user asks about email (drafting, writing, sending, or scheduling an email), route to `email_agent`.
7. For multi-step tasks (e.g. 'Read the document, then email the summary'):
   - If document retrieval has not happened yet, route to `rag_agent`.
   - Once `rag_agent` has responded, route to `email_agent` with the findings.
   - Once all steps are satisfied, route to `FINISH`.

Output your decision as a valid JSON object ONLY:
```json
{
  "next_agent": "rag_agent" | "github_agent" | "calendar_agent" | "email_agent" | "FINISH",
  "direct_response": "..." // Only provide if next_agent is FINISH and you are replying directly
}
```
"""


def _call_gemini_llm(prompt: str) -> str:
    """Calls Gemini LLM with resilient model fallback."""
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


def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    Supervisor router node.
    Inspects messages and decides next_agent or FINISH.
    """
    messages = state.get("messages", [])
    if not messages:
        return {
            "next_agent": "FINISH",
            "messages": [AIMessage(content="Hello! I am your AI Multi-Agent Assistant. How can I help you today?")],
            "sender": "supervisor"
        }

    # If this is a confirmed Human-in-the-Loop action, route directly to the intended sub-agent
    if state.get("confirmed") and state.get("pending_action"):
        target_agent = state.get("pending_action", {}).get("agent")
        if target_agent in ["email_agent", "github_agent", "calendar_agent", "rag_agent"]:
            return {"next_agent": target_agent}

    # Format transcript for supervisor decision
    history_lines = []
    for m in messages[-6:]:
        role = getattr(m, "type", "message")
        content = getattr(m, "content", str(m))
        history_lines.append(f"{role.upper()}: {content}")
    history_str = "\n".join(history_lines)

    sender = state.get("sender")
    last_user_query = ""
    for m in reversed(messages):
        if getattr(m, "type", "") == "human":
            last_user_query = getattr(m, "content", "")
            break

    # If a worker just finished, check for chaining or conclude turn
    if sender in ["rag_agent", "github_agent", "calendar_agent", "email_agent"]:
        q_lower = last_user_query.lower()
        has_email_chain = any(w in q_lower for w in [
            "and email", "then email", "email the", "send email", "send an email",
            "send mail", "send a mail", "aur mail", "aur email", "or aik mail", "or mail",
            "mail send", "mail bhej", "email bhej"
        ])
        has_calendar_chain = any(w in q_lower for w in [
            "and schedule", "then schedule", "and calendar", "aur calendar", "calendar me"
        ])
        if has_email_chain and sender != "email_agent":
            return {"next_agent": "email_agent"}
        elif has_calendar_chain and sender != "calendar_agent":
            return {"next_agent": "calendar_agent"}
        else:
            return {"next_agent": "FINISH"}

    prompt = f"""{SUPERVISOR_ROUTING_PROMPT}

Recent Conversation History:
{history_str}

Last Active Worker: {sender or 'None'}
Last User Input: {last_user_query}

Decide the next action:"""

    llm_output = _call_gemini_llm(prompt)

    decision = None
    if "```json" in llm_output:
        try:
            json_str = llm_output.split("```json")[1].split("```")[0].strip()
            decision = json.loads(json_str)
        except Exception:
            pass
    elif llm_output.strip().startswith("{") and llm_output.strip().endswith("}"):
        try:
            decision = json.loads(llm_output.strip())
        except Exception:
            pass

    if not decision:
        # Fallback keyword routing
        q_lower = last_user_query.lower()
        if any(w in q_lower for w in ["pdf", "document", "shor", "pulsar", "quantum"]):
            decision = {"next_agent": "rag_agent"}
        elif any(w in q_lower for w in ["github", "repo", "commit", "issue", "pull request", "octocat"]):
            decision = {"next_agent": "github_agent"}
        elif any(w in q_lower for w in ["calendar", "meeting", "schedule meeting", "appointment"]):
            decision = {"next_agent": "calendar_agent"}
        elif any(w in q_lower for w in ["email", "mail", "draft", "send email", "schedule email"]):
            decision = {"next_agent": "email_agent"}
        else:
            decision = {"next_agent": "FINISH", "direct_response": "I am here to help you with document analysis, GitHub repositories, Google Calendar, and email management."}

    next_agent = decision.get("next_agent", "FINISH")
    direct_resp = decision.get("direct_response")

    if next_agent == "FINISH" and direct_resp and sender != "supervisor":
        return {
            "next_agent": "FINISH",
            "messages": [AIMessage(content=direct_resp)],
            "sender": "supervisor"
        }

    return {
        "next_agent": next_agent
    }


def rag_node(state: AgentState) -> Dict[str, Any]:
    """Node wrapper for RAG Sub-Agent."""
    messages = state.get("messages", [])
    last_query = ""
    for m in reversed(messages):
        if getattr(m, "type", "") == "human":
            last_query = getattr(m, "content", "")
            break

    doc_id = state.get("document_id")
    if not doc_id:
        return {
            "messages": [AIMessage(content="Please select or upload a document first before querying the RAG agent.")],
            "sender": "rag_agent",
            "next_agent": "FINISH"
        }

    res = answer_document_query(question=last_query, document_id=doc_id)
    return {
        "messages": [AIMessage(content=res.get("answer", ""))],
        "sender": "rag_agent",
        "sources": res.get("sources", [])
    }


async def github_node(state: AgentState) -> Dict[str, Any]:
    """Node wrapper for GitHub Sub-Agent."""
    messages = state.get("messages", [])
    last_query = ""
    for m in reversed(messages):
        if getattr(m, "type", "") == "human":
            last_query = getattr(m, "content", "")
            break

    confirmed = state.get("confirmed", False)
    pending_action = state.get("pending_action")

    res = await run_github_agent(last_query, confirmed=confirmed, pending_action=pending_action)

    return {
        "messages": [AIMessage(content=res.get("answer", ""))],
        "sender": "github_agent",
        "pending_action": res.get("pending_action")
    }


async def calendar_node(state: AgentState) -> Dict[str, Any]:
    """Node wrapper for Google Calendar Sub-Agent."""
    messages = state.get("messages", [])
    last_query = ""
    for m in reversed(messages):
        if getattr(m, "type", "") == "human":
            last_query = getattr(m, "content", "")
            break

    res = await run_calendar_agent(last_query)
    return {
        "messages": [AIMessage(content=res.get("answer", ""))],
        "sender": "calendar_agent"
    }


async def email_node(state: AgentState) -> Dict[str, Any]:
    """Node wrapper for Email Sub-Agent."""
    messages = state.get("messages", [])
    last_query = ""
    for m in reversed(messages):
        if getattr(m, "type", "") == "human":
            last_query = getattr(m, "content", "")
            break

    confirmed = state.get("confirmed", False)
    pending_action = state.get("pending_action")

    res = await run_email_agent(last_query, confirmed=confirmed, pending_action=pending_action)

    return {
        "messages": [AIMessage(content=res.get("answer", ""))],
        "sender": "email_agent",
        "pending_action": res.get("pending_action")
    }


def create_supervisor_graph():
    """Builds and compiles the full Multi-Agent LangGraph system."""
    workflow = StateGraph(AgentState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("rag_agent", rag_node)
    workflow.add_node("github_agent", github_node)
    workflow.add_node("calendar_agent", calendar_node)
    workflow.add_node("email_agent", email_node)

    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state["next_agent"],
        {
            "rag_agent": "rag_agent",
            "github_agent": "github_agent",
            "calendar_agent": "calendar_agent",
            "email_agent": "email_agent",
            "FINISH": END,
        }
    )

    # Route sub-agents back to supervisor for multi-step chaining or completion
    workflow.add_edge("rag_agent", "supervisor")
    workflow.add_edge("github_agent", "supervisor")
    workflow.add_edge("calendar_agent", "supervisor")
    workflow.add_edge("email_agent", "supervisor")

    workflow.set_entry_point("supervisor")

    return workflow.compile()


# Singleton compiled multi-agent graph
_compiled_system = None


def get_multi_agent_system():
    global _compiled_system
    if _compiled_system is None:
        _compiled_system = create_supervisor_graph()
    return _compiled_system


async def process_user_query(
    query: str,
    document_id: Optional[str] = None,
    confirmed: bool = False,
    pending_action: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Unified entrypoint for running the LangGraph Multi-Agent system.
    """
    app = get_multi_agent_system()

    # Build messages sequence from conversation history
    messages: List[BaseMessage] = []
    if history:
        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=query))

    initial_state: AgentState = {
        "messages": messages,
        "next_agent": None,
        "sender": None,
        "document_id": document_id,
        "confirmed": confirmed,
        "pending_action": pending_action,
        "sources": []
    }

    # Run graph execution asynchronously
    final_state = await app.ainvoke(initial_state, {"recursion_limit": 10})

    final_messages = final_state.get("messages", [])
    last_ai_content = "Task completed."
    for m in reversed(final_messages):
        if getattr(m, "type", "") == "ai":
            last_ai_content = getattr(m, "content", "")
            break

    return {
        "answer": last_ai_content,
        "sender": final_state.get("sender") or "supervisor",
        "sources": final_state.get("sources", []),
        "pending_action": final_state.get("pending_action"),
        "status": "requires_confirmation" if final_state.get("pending_action") else "success"
    }
