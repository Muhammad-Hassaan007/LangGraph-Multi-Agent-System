"""
Chat API router for FastAPI.
Accepts user questions, validates document isolation ID, and delegates to the RAG Agent.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from agents.rag_agent import answer_document_query


router = APIRouter(prefix="/api", tags=["chat"])


class ChatMessageItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    document_id: str = Field(..., min_length=1, description="Selected document ID for isolation")
    message: Optional[str] = Field(default=None, description="User's query (message field)")
    question: Optional[str] = Field(default=None, description="User's query (question field)")
    history: Optional[List[ChatMessageItem]] = Field(default=[], description="Previous conversation turns")


class SourceItem(BaseModel):
    filename: str
    page: int | str
    page_number: Optional[int | str] = None
    content: str
    similarity: Optional[float] = 0.0


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    document_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat_with_rag(request: ChatRequest):
    """
    RAG chat endpoint.
    Retrieves isolated chunks from Supabase for the specified document_id,
    and returns the LLM-generated answer with source page numbers.
    """
    query = (request.message or request.question or "").strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query message cannot be empty (provide either 'message' or 'question')."
        )

    if not request.document_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document ID is required to isolate RAG context."
        )

    try:
        # Convert history Pydantic models to dicts
        history_dicts = [{"role": h.role, "content": h.content} for h in (request.history or [])]

        result = answer_document_query(
            question=query,
            document_id=request.document_id.strip(),
            history=history_dicts
        )

        formatted_sources = []
        for s in result.get("sources", []):
            p = s.get("page") or s.get("page_number", 1)
            formatted_sources.append(
                SourceItem(
                    filename=s.get("filename", "document.pdf"),
                    page=p,
                    page_number=p,
                    content=s.get("content", ""),
                    similarity=s.get("similarity", 0.0)
                )
            )

        return ChatResponse(
            answer=result["answer"],
            sources=formatted_sources,
            document_id=result["document_id"]
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in RAG Agent processing: {str(exc)}"
        )
