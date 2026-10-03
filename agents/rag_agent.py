"""
RAG Sub-Agent implemented as a LangGraph Graph.
Architecture:
  embed_query -> retrieve -> generate_answer

Exposes:
  run_rag(question, document_id)
  rag_node(state)  -- For LangGraph Supervisor integration
"""

from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage

from config import config, is_valid_secret
from rag.embeddings import get_embedding_model
from rag.supabase_vectorstore import search_similar_chunks


class RAGState(TypedDict):
    question: str
    document_id: str
    query_embedding: Optional[List[float]]
    retrieved_chunks: Optional[List[Dict[str, Any]]]
    answer: Optional[str]
    sources: Optional[List[Dict[str, Any]]]


def embed_query_node(state: RAGState) -> Dict[str, Any]:
    """Node 1: Generates query embedding vector."""
    question = state["question"].strip()
    if not question:
        return {"query_embedding": None}

    embedder = get_embedding_model()
    vector = embedder.embed_query(question)
    return {"query_embedding": vector}


def retrieve_node(state: RAGState) -> Dict[str, Any]:
    """Node 2: Queries Supabase pgvector with strict document_id isolation and similarity threshold."""
    query_embedding = state.get("query_embedding")
    document_id = state.get("document_id")

    if not query_embedding or not document_id:
        return {"retrieved_chunks": [], "sources": []}

    raw_results = search_similar_chunks(
        query_embedding=query_embedding,
        document_id=document_id,
        k=config.TOP_K
    )

    filtered_chunks = []
    sources = []
    seen_sources = set()

    for item in raw_results:
        similarity = item.get("similarity", 0.0)
        # Apply minimum similarity cutoff
        if similarity < config.MIN_SIMILARITY:
            continue

        filtered_chunks.append(item)
        meta = item.get("metadata") or {}
        p_num = meta.get("page") or meta.get("page_number", 1)
        fname = meta.get("filename", "document.pdf")
        content_snippet = (item.get("content") or "").strip()

        source_key = (fname, p_num, content_snippet[:60])
        if source_key not in seen_sources:
            seen_sources.add(source_key)
            sources.append({
                "filename": fname,
                "page": p_num,
                "page_number": p_num,
                "content": content_snippet,
                "similarity": round(float(similarity), 4)
            })

    return {
        "retrieved_chunks": filtered_chunks,
        "sources": sources
    }


def generate_answer_node(state: RAGState) -> Dict[str, Any]:
    """Node 3: Generates answer strictly grounded in retrieved chunks with citations."""
    retrieved_chunks = state.get("retrieved_chunks") or []
    question = state["question"]
    sources = state.get("sources") or []

    # Strict anti-hallucination rule: No relevant chunks found
    if not retrieved_chunks:
        return {
            "answer": "The information was not found in the document.",
            "sources": []
        }

    # Format context excerpts
    context_blocks = []
    for idx, c in enumerate(retrieved_chunks, 1):
        meta = c.get("metadata") or {}
        fname = meta.get("filename", "document.pdf")
        p_num = meta.get("page") or meta.get("page_number", 1)
        text = c.get("content", "").strip()
        context_blocks.append(f"[Excerpt {idx} | Source: {fname}, Page {p_num}]:\n{text}")

    context_str = "\n\n".join(context_blocks)

    system_prompt = f"""You are the RAG Sub-Agent in an intelligent Multi-Agent Assistant.
Answer the user's question based STRICTLY and ONLY on the provided document excerpts below.

CRITICAL RULES:
1. Ground your answer completely in the provided excerpts.
2. If the excerpts do not contain sufficient information to answer the question, reply EXACTLY with:
"The information was not found in the document."
3. Do NOT extrapolate, speculate, or invent facts.
4. When stating facts, explicitly reference the source page number (e.g., 'According to page 2...').

Document Context:
{context_str}

User Question: {question}

Answer:"""

    # Generate answer with Gemini or OpenAI
    if is_valid_secret(config.GEMINI_API_KEY):
        import time
        from google import genai
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        
        models_to_try = [config.GEMINI_CHAT_MODEL, "gemini-3.6-flash", "gemini-3.1-flash-lite-preview", "gemini-3-flash-preview"]
        # Remove duplicates while preserving order
        models_to_try = list(dict.fromkeys(models_to_try))
        
        last_error = None
        answer_text = None
        for model_name in models_to_try:
            for attempt in range(3):
                try:
                    resp = client.models.generate_content(
                        model=model_name,
                        contents=system_prompt
                    )
                    answer_text = resp.text.strip() if resp.text else ""
                    break
                except Exception as e:
                    last_error = e
                    err_msg = str(e)
                    if ("503" in err_msg or "UNAVAILABLE" in err_msg or "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg):
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    else:
                        break
            if answer_text is not None:
                break
                
        if answer_text is None:
            raise last_error or RuntimeError("Failed to generate answer from Gemini API.")
    elif is_valid_secret(config.OPENAI_API_KEY):
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        llm = ChatOpenAI(model=config.DEFAULT_LLM_MODEL, temperature=0.1, openai_api_key=config.OPENAI_API_KEY)
        resp = llm.invoke([HumanMessage(content=system_prompt)])
        answer_text = resp.content.strip()
    else:
        raise ValueError("No LLM API key configured in .env.")

    if "information was not found" in answer_text.lower() or "not found in the document" in answer_text.lower():
        return {
            "answer": "The information was not found in the document.",
            "sources": []
        }

    return {
        "answer": answer_text,
        "sources": sources
    }


def create_rag_graph():
    """Builds and compiles the RAG Sub-Agent LangGraph graph."""
    workflow = StateGraph(RAGState)
    workflow.add_node("embed_query", embed_query_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate_answer", generate_answer_node)

    workflow.set_entry_point("embed_query")
    workflow.add_edge("embed_query", "retrieve")
    workflow.add_edge("retrieve", "generate_answer")
    workflow.add_edge("generate_answer", END)

    return workflow.compile()


# Singleton compiled graph
_rag_graph = None


def get_rag_graph():
    global _rag_graph
    if _rag_graph is None:
        _rag_graph = create_rag_graph()
    return _rag_graph


def run_rag(question: str, document_id: str) -> Dict[str, Any]:
    """
    Main entry point for Module 1 RAG query execution.
    Executes the LangGraph graph: embed_query -> retrieve -> generate_answer.
    """
    graph = get_rag_graph()
    initial_state: RAGState = {
        "question": question,
        "document_id": document_id,
        "query_embedding": None,
        "retrieved_chunks": None,
        "answer": None,
        "sources": None
    }
    result = graph.invoke(initial_state)
    return {
        "answer": result.get("answer", "The information was not found in the document."),
        "sources": result.get("sources", []),
        "document_id": document_id
    }


def answer_document_query(question: str, document_id: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """Compatibility wrapper for chat endpoint."""
    return run_rag(question=question, document_id=document_id)


def rag_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for Supervisor routing in Module 5.
    """
    messages = state.get("messages", [])
    last_query = messages[-1].content if messages else ""
    document_id = state.get("document_id")

    if not document_id:
        return {
            "messages": [AIMessage(content="Please select a document from the sidebar first to ask document-specific questions.", name="rag_agent")],
            "sender": "rag_agent"
        }

    res = run_rag(question=last_query, document_id=document_id)
    return {
        "messages": [AIMessage(content=res["answer"], name="rag_agent")],
        "sender": "rag_agent",
        "sources": res.get("sources", [])
    }
