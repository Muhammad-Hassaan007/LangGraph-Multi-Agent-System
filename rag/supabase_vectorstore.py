"""
Supabase Vector Store integration module.
Connects directly to hosted Supabase PostgreSQL + pgvector.
Implements chunk insertion, isolated similarity retrieval, and document listing.
"""

from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from config import config


_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Returns a singleton Supabase client instance."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not config.is_supabase_configured():
        raise ValueError(
            "Supabase credentials are not configured in your .env file!\n"
            "Please open '.env' and set your real SUPABASE_URL and SUPABASE_KEY from your Supabase dashboard."
        )

    _supabase_client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _supabase_client


def _sanitize_record(val: Any) -> Any:
    """Recursively removes null bytes (\x00 / \u0000) that cause PostgreSQL 22P05 error."""
    if isinstance(val, str):
        return val.replace("\x00", "").replace("\u0000", "")
    elif isinstance(val, dict):
        return {k: _sanitize_record(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [_sanitize_record(x) for x in val]
    return val


def insert_document_chunks(records: List[Dict[str, Any]]) -> int:
    """
    Inserts a batch of document chunk records into the Supabase 'documents' table.
    
    Each record format:
    {
        "document_id": str,
        "content": str,
        "metadata": {
            "filename": str,
            "page": int,
            "page_number": int,
            "chunk_index": int,
            ...
        },
        "embedding": List[float]
    }
    """
    if not records:
        return 0

    client = get_supabase_client()
    table = config.SUPABASE_TABLE_NAME

    # Sanitize records to eliminate any null bytes rejected by PostgreSQL
    clean_records = [_sanitize_record(r) for r in records]

    # Supabase REST API handles batch inserts smoothly in chunks of 50-100
    batch_size = 50
    total_inserted = 0

    for i in range(0, len(clean_records), batch_size):
        batch = clean_records[i:i + batch_size]
        response = client.table(table).insert(batch).execute()
        if response.data:
            total_inserted += len(response.data)

    return total_inserted


def search_similar_chunks(
    query_embedding: List[float],
    document_id: Optional[str] = None,
    k: int = 4
) -> List[Dict[str, Any]]:
    """
    Performs vector similarity search via Supabase RPC 'match_documents'.
    Guarantees document isolation by filtering on document_id.
    
    Returns a list of dicts:
    [
        {
            "id": int,
            "document_id": str,
            "content": str,
            "metadata": dict,
            "similarity": float
        },
        ...
    ]
    """
    client = get_supabase_client()

    # Primary RPC parameters matching rag/schema.sql
    rpc_params = {
        "query_embedding": query_embedding,
        "match_count": k,
        "filter_document_id": document_id
    }

    try:
        response = client.rpc("match_documents", rpc_params).execute()
        return response.data or []
    except Exception as e:
        error_msg = str(e)
        # Resilient fallback in case existing Supabase DB used jsonb filter signature
        if "filter_document_id" in error_msg:
            try:
                fallback_params = {
                    "query_embedding": query_embedding,
                    "match_count": k,
                    "filter": {"document_id": document_id} if document_id else {}
                }
                fallback_resp = client.rpc("match_documents", fallback_params).execute()
                return fallback_resp.data or []
            except Exception:
                pass

        if "match_documents" in error_msg.lower() or "does not exist" in error_msg.lower():
            raise RuntimeError(
                "Supabase RPC function 'match_documents' was not found in your Supabase database.\n"
                "Please run the SQL script found in 'rag/schema.sql' in your Supabase SQL Editor.\n"
                f"Original error: {error_msg}"
            ) from e
        raise e


def list_indexed_documents() -> List[Dict[str, Any]]:
    """
    Fetches all distinct documents stored in Supabase with metadata summary.
    Returns list of:
    [
        {
            "document_id": "...",
            "filename": "...",
            "total_pages": int,
            "chunks_count": int,
            "created_at": "..."
        }
    ]
    """
    if not config.is_supabase_configured():
        return []

    client = get_supabase_client()
    table = config.SUPABASE_TABLE_NAME

    try:
        response = client.table(table).select("document_id, metadata, created_at").execute()
    except Exception as e:
        print(f"[Supabase Warning] Could not list documents: {e}")
        return []

    data = response.data or []
    docs_map: Dict[str, Dict[str, Any]] = {}

    for row in data:
        doc_id = row.get("document_id")
        meta = row.get("metadata") or {}
        if not doc_id:
            # Fallback to meta if older schema
            doc_id = meta.get("document_id")
        if not doc_id:
            continue

        if doc_id not in docs_map:
            docs_map[doc_id] = {
                "document_id": doc_id,
                "filename": meta.get("filename", "Unknown Document"),
                "total_pages": meta.get("total_pages", 1),
                "chunks_count": 0,
                "created_at": row.get("created_at")
            }
        docs_map[doc_id]["chunks_count"] += 1

    return list(docs_map.values())


def delete_document_by_id(document_id: str) -> bool:
    """
    Deletes all chunk vectors belonging to a specific document_id.
    Ensures clean document isolation and deletion.
    """
    if not config.is_supabase_configured():
        return False

    client = get_supabase_client()
    table = config.SUPABASE_TABLE_NAME

    try:
        # Delete by dedicated document_id column
        client.table(table).delete().eq("document_id", document_id).execute()
        return True
    except Exception as e:
        print(f"[Supabase Error] Failed to delete document {document_id}: {e}")
        return False


def delete_all_documents() -> bool:
    """
    Deletes all chunk vectors and documents from the Supabase 'documents' table.
    Ensures complete cleanup of the vector store.
    """
    if not config.is_supabase_configured():
        return False

    client = get_supabase_client()
    table = config.SUPABASE_TABLE_NAME

    try:
        # In Postgrest, we filter with neq id 0 or gt id 0 to match all records
        client.table(table).delete().gt("id", 0).execute()
        return True
    except Exception as e:
        print(f"[Supabase Error] Failed to delete all documents: {e}")
        return False

