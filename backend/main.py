"""
FastAPI application entry point for the LangGraph Multi-Agent System backend.
Provides REST endpoints for PDF upload, Supabase RAG queries, and document management.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.upload import router as upload_router
from backend.api.chat import router as chat_router
from backend.api.documents import router as documents_router
from backend.api.agent import router as agent_router
from config import config

app = FastAPI(
    title="LangGraph Multi-Agent AI System API",
    description="Backend API powering Supabase pgvector RAG and Multi-Agent orchestration.",
    version="1.0.0",
)

# Explicit origins allowed for local React development
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(upload_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(agent_router)


@app.get("/")
async def root():
    return {
        "status": "online",
        "system": "LangGraph Multi-Agent AI System",
        "version": "1.0.0",
        "active_module": "Module 1 - RAG Sub-Agent & Supabase pgvector"
    }


@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health check endpoint to test connection status."""
    return {
        "status": "healthy",
        "llm_configured": config.is_llm_configured(),
        "supabase_configured": config.is_supabase_configured(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
