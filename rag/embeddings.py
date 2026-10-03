"""
Embeddings configuration and initialization.
Provides the embedding model used for vectorizing text chunks.
Supports Google Gemini (gemini-embedding-001 with 768 dimensions)
and OpenAI (text-embedding-3-small with 1536 dimensions).
"""

from typing import List, Any
from langchain_core.embeddings import Embeddings
from config import config, is_valid_secret


class GeminiEmbeddings(Embeddings):
    """
    Direct wrapper around official google-genai SDK.
    Supports configurable models and output_dimensionality (e.g. 768).
    """

    def __init__(self, api_key: str, model: str = "gemini-embedding-001", dimension: int = 768):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.dimension = dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        from google.genai import types
        results: List[List[float]] = []
        if not texts:
            return results

        # Process in batches of 50 for ultra-fast vectorization
        batch_size = 50
        for i in range(0, len(texts), batch_size):
            batch = [t.strip() or " " for t in texts[i:i + batch_size]]
            try:
                resp = self.client.models.embed_content(
                    model=self.model,
                    contents=batch,
                    config=types.EmbedContentConfig(output_dimensionality=self.dimension)
                )
                for emb in resp.embeddings:
                    results.append(emb.values)
            except Exception:
                # Fallback to individual chunk embedding if a batch call fails
                for t in batch:
                    r = self.client.models.embed_content(
                        model=self.model,
                        contents=t,
                        config=types.EmbedContentConfig(output_dimensionality=self.dimension)
                    )
                    results.append(r.embeddings[0].values)
        return results

    def embed_query(self, text: str) -> List[float]:
        from google.genai import types
        clean_text = text.strip() or " "
        resp = self.client.models.embed_content(
            model=self.model,
            contents=clean_text,
            config=types.EmbedContentConfig(output_dimensionality=self.dimension)
        )
        return resp.embeddings[0].values


def get_embedding_dimension() -> int:
    """Returns the vector dimension for the active embedding model."""
    return config.EMBEDDING_DIMENSION


def get_embedding_model() -> Embeddings:
    """
    Initializes and returns the Embeddings instance.
    Uses Google Gemini if GEMINI_API_KEY is configured.
    Uses OpenAI if OPENAI_API_KEY is configured.
    """
    if is_valid_secret(config.GEMINI_API_KEY):
        return GeminiEmbeddings(
            api_key=config.GEMINI_API_KEY,
            model=config.GEMINI_EMBEDDING_MODEL,
            dimension=config.EMBEDDING_DIMENSION
        )

    if is_valid_secret(config.OPENAI_API_KEY):
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=config.EMBEDDING_MODEL,
            openai_api_key=config.OPENAI_API_KEY,
        )

    raise ValueError(
        "No active Embedding API key configured in .env!\n"
        "Please open your '.env' file and configure GEMINI_API_KEY or OPENAI_API_KEY."
    )
