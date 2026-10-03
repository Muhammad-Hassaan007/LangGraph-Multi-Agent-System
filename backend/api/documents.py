"""
Documents API router for FastAPI.
Lists and manages indexed documents in Supabase pgvector.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from rag.supabase_vectorstore import (
    list_indexed_documents, 
    delete_document_by_id,
    delete_all_documents
)


router = APIRouter(prefix="/api", tags=["documents"])


class DocumentItem(BaseModel):
    document_id: str
    filename: str
    total_pages: int
    chunks_count: int
    created_at: str | None = None


@router.get("/documents", response_model=List[DocumentItem])
async def get_documents():
    """
    Returns list of all documents indexed in Supabase pgvector.
    Used by the sidebar to populate the document list and selector.
    """
    try:
        docs = list_indexed_documents()
        return [
            DocumentItem(
                document_id=d["document_id"],
                filename=d["filename"],
                total_pages=d.get("total_pages", 1),
                chunks_count=d.get("chunks_count", 0),
                created_at=d.get("created_at")
            )
            for d in docs
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch documents: {str(exc)}"
        )


@router.delete("/documents/all")
@router.delete("/documents")
async def delete_all_documents_endpoint():
    """
    Deletes all vector chunks and documents from Supabase pgvector.
    Used by Settings to completely purge the knowledge base.
    """
    success = delete_all_documents()
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete all documents from Supabase."
        )
    return {
        "success": True,
        "message": "All documents and vector chunks have been deleted from Supabase pgvector."
    }


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Deletes all vector chunks associated with the specified document_id.
    """
    success = delete_document_by_id(document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document from Supabase."
        )
    return {"success": True, "message": f"Document {document_id} removed successfully."}

