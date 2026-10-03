"""
Helper functions and utilities for formatting, logging, and agent communications.
"""

from typing import Any, Dict
from langchain_core.messages import BaseMessage


def format_agent_response(sender: str, message: str) -> str:
    """Formats an agent's response with a clean visual banner."""
    return f"\n[{sender.upper()}]\n{message}\n"


def pretty_print_messages(messages: list[BaseMessage]) -> None:
    """Prints message history with clear sender roles for debugging."""
    for msg in messages:
        role = getattr(msg, "name", None) or msg.type
        print(f"[{role}]: {msg.content}")
