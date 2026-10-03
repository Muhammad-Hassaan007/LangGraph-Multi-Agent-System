"""
Agent API Router for FastAPI.
Provides the universal /api/agent endpoint for the LangGraph Supervisor Multi-Agent System,
plus endpoints to view and manage persistent scheduled emails.
"""

import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from supervisor import process_user_query
from mcp_tools.email import execute_email_tool

router = APIRouter(prefix="/api", tags=["agent"])


class HistoryItem(BaseModel):
    role: str
    content: str


class AgentRequest(BaseModel):
    query: Optional[str] = Field(default=None, description="User prompt (query)")
    message: Optional[str] = Field(default=None, description="User prompt (message alias)")
    question: Optional[str] = Field(default=None, description="User prompt (question alias)")
    document_id: Optional[str] = Field(default=None, description="Selected document ID for RAG context")
    confirmed: Optional[bool] = Field(default=False, description="User confirmation flag for write actions")
    pending_action: Optional[Dict[str, Any]] = Field(default=None, description="Action payload being confirmed")
    history: Optional[List[HistoryItem]] = Field(default=[], description="Previous conversation turns")


class AgentResponse(BaseModel):
    answer: str
    sender: str
    sources: Optional[List[Dict[str, Any]]] = []
    pending_action: Optional[Dict[str, Any]] = None
    status: str = "success"


@router.post("/agent", response_model=AgentResponse)
async def chat_with_multi_agent_system(request: AgentRequest):
    """
    Universal Multi-Agent System endpoint.
    Routes queries to RAG, GitHub MCP, Calendar MCP, or Email MCP sub-agents,
    with Human-in-the-Loop confirmation support.
    """
    prompt = (request.query or request.message or request.question or "").strip()
    if not prompt and not request.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User prompt cannot be empty."
        )

    history_list = [h.model_dump() for h in request.history] if request.history else []

    try:
        result = await process_user_query(
            query=prompt,
            document_id=request.document_id,
            confirmed=bool(request.confirmed),
            pending_action=request.pending_action,
            history=history_list
        )
        return AgentResponse(
            answer=result.get("answer", ""),
            sender=result.get("sender", "supervisor"),
            sources=result.get("sources", []),
            pending_action=result.get("pending_action"),
            status=result.get("status", "success")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-Agent System error: {str(e)}"
        )


@router.get("/scheduled-emails")
async def list_scheduled_emails_endpoint():
    """Returns all queued scheduled emails from the persistent SQLite job store."""
    try:
        res = await execute_email_tool("list_scheduled_emails", {})
        raw_result = res.get("result", [])
        clean_jobs = []
        if isinstance(raw_result, list):
            for item in raw_result:
                if isinstance(item, dict) and "text" in item:
                    try:
                        parsed = json.loads(item["text"])
                        if isinstance(parsed, list):
                            clean_jobs.extend(parsed)
                        elif isinstance(parsed, dict):
                            clean_jobs.append(parsed)
                    except Exception:
                        clean_jobs.append({"id": "unknown", "name": item["text"]})
                elif isinstance(item, dict):
                    clean_jobs.append(item)
        elif isinstance(raw_result, str):
            try:
                clean_jobs = json.loads(raw_result)
            except Exception:
                clean_jobs = [{"id": "unknown", "name": raw_result}]
        return {"scheduled_emails": clean_jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scheduled-emails/{job_id}")
async def cancel_scheduled_email_endpoint(job_id: str):
    """Cancels a scheduled email job."""
    try:
        res = await execute_email_tool("cancel_scheduled_email", {"job_id": job_id})
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class GitHubSearchRequest(BaseModel):
    query: str
    search_type: Optional[str] = "repositories"


@router.post("/github/search")
async def github_search_endpoint(request: GitHubSearchRequest):
    """
    Direct GitHub search endpoint using the official GitHub MCP sub-agent over stdio.
    Supports searching repositories, code, commits, and issues.
    """
    from agents.github_agent import run_github_agent
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    # Formulate query for the agent if specific type selected
    st = (request.search_type or "repositories").lower()
    if st == "repositories" and not any(k in query.lower() for k in ["repo", "search"]):
        formatted_query = f"Search repositories matching: {query}"
    elif st == "code" and not any(k in query.lower() for k in ["code", "file", "contents"]):
        formatted_query = f"Search code or file contents for: {query}"
    elif st == "commits" and not any(k in query.lower() for k in ["commit", "log"]):
        formatted_query = f"List commits related to: {query}"
    elif st == "issues" and not any(k in query.lower() for k in ["issue", "pr", "pull"]):
        formatted_query = f"List open issues or PRs related to: {query}"
    else:
        formatted_query = query

    try:
        result = await run_github_agent(formatted_query)
        return {
            "status": "success",
            "query": query,
            "search_type": request.search_type,
            "answer": result.get("answer", ""),
            "tool_used": result.get("tool_used"),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"GitHub MCP search error: {str(e)}"
        )

