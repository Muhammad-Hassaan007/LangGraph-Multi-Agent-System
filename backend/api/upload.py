"""
Upload API router for FastAPI.
Accepts PDF files, validates size & format, chunks & computes embeddings,
and indexes vectors into Supabase pgvector.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from rag.ingest import process_and_index_pdf


router = APIRouter(prefix="/api", tags=["upload"])

# Maximum allowed PDF file size: 25 MB
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024


class UploadResponse(BaseModel):
    success: bool
    document_id: str
    filename: str
    chunks: int
    chunks_count: Optional[int] = None
    total_pages: Optional[int] = 1
    message: str


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Accepts a PDF file upload, validates it, and runs the RAG ingestion pipeline.
    """
    # 1. Validate file extension and content type
    filename = file.filename or "uploaded_document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Only PDF (.pdf) files are accepted."
        )

    # 2. Read file content and check size limit
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(e)}"
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty."
        )

    if len(content) > MAX_FILE_SIZE_BYTES:
        mb_size = round(len(content) / (1024 * 1024), 2)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({mb_size} MB) exceeds maximum allowed limit of 25 MB."
        )

    # 3. Process and index into Supabase pgvector
    try:
        result = process_and_index_pdf(file_bytes=content, filename=filename)
        chunk_total = result.get("chunks", result.get("chunks_count", 0))
        return UploadResponse(
            success=True,
            document_id=result["document_id"],
            filename=result["filename"],
            chunks=chunk_total,
            chunks_count=chunk_total,
            total_pages=result.get("total_pages", 1),
            message=result.get("message", "Document processed and indexed successfully.")
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(run_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error indexing document in Supabase: {str(exc)}"
        )
