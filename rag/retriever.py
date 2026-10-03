"""
RAG Retriever Module.
Takes a natural language query and document_id, generates query embedding,
and retrieves isolated matching chunks from Supabase pgvector.
"""

from typing import List, Dict, Any, Optional
from rag.embeddings import get_embedding_model
from rag.supabase_vectorstore import search_similar_chunks


def retrieve_relevant_chunks(
    query: str,
    document_id: Optional[str] = None,
    k: int = 4
) -> List[Dict[str, Any]]:
    """
    Embeds the user query and retrieves top-k matching chunks from Supabase.
    Strictly filters by document_id when provided for document isolation.
    """
    if not query.strip():
        return []

    # Embed the query
    embedder = get_embedding_model()
    query_vector = embedder.embed_query(query)

    # Perform similarity search in Supabase pgvector
    raw_results = search_similar_chunks(
        query_embedding=query_vector,
        document_id=document_id,
        k=k
    )

    formatted_results = []
    for item in raw_results:
        meta = item.get("metadata") or {}
        p_num = meta.get("page") or meta.get("page_number", 1)
        formatted_results.append({
            "content": item.get("content", ""),
            "page": p_num,
            "page_number": p_num,
            "filename": meta.get("filename", "Unknown"),
            "document_id": item.get("document_id") or meta.get("document_id", document_id),
            "chunk_index": meta.get("chunk_index"),
            "similarity": item.get("similarity", 0.0)
        })

    return formatted_results
