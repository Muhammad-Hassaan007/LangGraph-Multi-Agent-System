"""
Knowledge Ingestion Pipeline.
Loads PDF documents, extracts text by page, splits into semantic chunks,
computes vector embeddings, and indexes them into Supabase pgvector with
isolated document metadata.
"""

import io
import uuid
from typing import List, Dict, Any
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import config
from rag.embeddings import get_embedding_model
from rag.supabase_vectorstore import insert_document_chunks


def extract_pages_from_pdf(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Reads a PDF file from bytes and extracts text page-by-page.
    Preserves page numbers (1-indexed) for citation tracking.
    Validates for corrupted, empty, or scanned image-only PDFs.
    """
    if not file_bytes or len(file_bytes) == 0:
        raise ValueError("The uploaded file is empty (0 bytes).")

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Corrupted or invalid PDF format: {str(e)}")

    if len(reader.pages) == 0:
        raise ValueError("The PDF contains no pages.")

    pages: List[Dict[str, Any]] = []
    total_pages = len(reader.pages)
    total_extracted_chars = 0

    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""

        # Remove null bytes (\x00 / \u0000) which PostgreSQL text/JSON types reject (error 22P05)
        page_text = page_text.replace("\x00", "").replace("\u0000", "")
        trimmed_text = page_text.strip()
        total_extracted_chars += len(trimmed_text)
        if trimmed_text:
            pages.append({
                "page_number": page_num,
                "text": trimmed_text,
                "total_pages": total_pages,
            })

    # Detect scanned image-only PDFs where OCR is missing
    if total_extracted_chars < 15 or len(pages) == 0:
        raise ValueError(
            f"Scanned image-only or unreadable PDF detected in '{filename}'. "
            "No extractable text was found. Please upload a PDF containing searchable text."
        )

    return pages


def chunk_extracted_pages(
    pages: List[Dict[str, Any]],
    document_id: str,
    filename: str,
    chunk_size: int = None,
    chunk_overlap: int = None
) -> List[Dict[str, Any]]:
    """
    Splits page texts into chunks using RecursiveCharacterTextSplitter.
    Attaches document_id, filename, and page_number to each chunk's metadata.
    """
    c_size = chunk_size or config.CHUNK_SIZE
    c_overlap = chunk_overlap or config.CHUNK_OVERLAP

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=c_size,
        chunk_overlap=c_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks: List[Dict[str, Any]] = []
    chunk_counter = 0

    for p in pages:
        page_num = p["page_number"]
        page_text = p["text"]
        total_pages = p["total_pages"]

        splits = text_splitter.split_text(page_text)
        for text_chunk in splits:
            cleaned_chunk = text_chunk.replace("\x00", "").replace("\u0000", "").strip()
            if not cleaned_chunk:
                continue

            chunk_counter += 1
            chunks.append({
                "content": cleaned_chunk,
                "metadata": {
                    "document_id": document_id,
                    "filename": filename.replace("\x00", "").replace("\u0000", ""),
                    "page": page_num,
                    "page_number": page_num,
                    "chunk_index": chunk_counter,
                    "total_pages": total_pages
                }
            })

    return chunks


def process_and_index_pdf(
    file_bytes: bytes,
    filename: str,
    document_id: str = None
) -> Dict[str, Any]:
    """
    Full pipeline to ingest a PDF:
    1. Validates file size and integrity.
    2. Extracts text per page.
    3. Splits text into overlapping chunks.
    4. Computes vector embeddings using active model.
    5. Saves chunks and vectors into Supabase pgvector.
    
    Returns indexing result metadata.
    """
    max_bytes = config.MAX_UPLOAD_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        mb = round(len(file_bytes) / (1024 * 1024), 2)
        raise ValueError(f"File size ({mb} MB) exceeds maximum allowed limit of {config.MAX_UPLOAD_MB} MB.")

    if not document_id:
        document_id = str(uuid.uuid4())

    pages = extract_pages_from_pdf(file_bytes, filename)
    chunks = chunk_extracted_pages(
        pages=pages,
        document_id=document_id,
        filename=filename,
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP
    )

    if not chunks:
        raise ValueError("Document produced 0 text chunks.")

    # Generate embeddings in batch
    embedder = get_embedding_model()
    chunk_texts = [c["content"] for c in chunks]
    embeddings = embedder.embed_documents(chunk_texts)

    # Combine chunk content, metadata, and embedding vector
    records = []
    for c, emb in zip(chunks, embeddings):
        records.append({
            "document_id": document_id,
            "content": c["content"],
            "metadata": c["metadata"],
            "embedding": emb
        })

    # Insert into Supabase pgvector
    total_inserted = insert_document_chunks(records)

    return {
        "success": True,
        "document_id": document_id,
        "filename": filename,
        "total_pages": pages[0]["total_pages"] if pages else 0,
        "chunks": total_inserted,
        "chunks_count": total_inserted,
        "message": f"Successfully indexed '{filename}' ({total_inserted} chunks stored in Supabase pgvector)."
    }
