"""
State definition for the LangGraph Multi-Agent System.
Defines the shared graph state schema passed between supervisor and sub-agents.
"""

from typing import Annotated, Sequence, TypedDict, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Shared state for the multi-agent system.
    
    Attributes:
        messages: The sequence of chat messages accumulated across turns.
                  Uses `add_messages` reducer to append new messages automatically.
        next_agent: The name of the next agent routed by the supervisor,
                    or 'FINISH' when the task is resolved.
        sender: The name of the agent who last responded.
        document_id: Selected document ID for RAG sub-agent isolation.
        confirmed: Whether the user confirmed a pending write action.
        pending_action: Details of a pending action requiring confirmation.
        sources: Citation sources returned by RAG agent.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next_agent: Optional[str]
    sender: Optional[str]
    document_id: Optional[str]
    confirmed: Optional[bool]
    pending_action: Optional[Dict[str, Any]]
    sources: Optional[List[Dict[str, Any]]]
