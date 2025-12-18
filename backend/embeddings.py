"""
Embedding provider supporting multiple backends.
Generates vector embeddings for semantic search.
"""

import asyncio
from typing import List, Optional
import httpx

from config import Config


class EmbeddingProvider:
    """Generate embeddings using various providers."""
    
    def __init__(self, config: Config):
        self.config = config
        self.embedding_config = config.get_embedding_config()
        self.provider = self.embedding_config.get("provider", "openai")
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        if self.provider == "openai":
            return await self._embed_openai(texts)
        elif self.provider == "openrouter":
            return await self._embed_openrouter(texts)
        elif self.provider == "ollama":
            return await self._embed_ollama(texts)
        else:
            raise ValueError(f"Unknown embedding provider: {self.provider}")
    
    async def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        api_key = self.embedding_config.get("api_key")
        model = self.embedding_config.get("model", "text-embedding-3-small")
        
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        
        # OpenAI has batch limits, process in chunks
        batch_size = 100
        all_embeddings = []
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "input": batch,
                        "model": model
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"OpenAI API error: {response.text}")
                
                data = response.json()
                
                # Sort by index to maintain order
                sorted_data = sorted(data["data"], key=lambda x: x["index"])
                batch_embeddings = [item["embedding"] for item in sorted_data]
                all_embeddings.extend(batch_embeddings)
        
        return all_embeddings

    async def _embed_openrouter(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenRouter (supports any embedding model)."""
        api_key = self.embedding_config.get("api_key")
        model = self.embedding_config.get("model", "openai/text-embedding-3-small")
        base_url = self.embedding_config.get("base_url", "https://openrouter.ai/api/v1")

        if not api_key:
            raise ValueError("OpenRouter API key not configured")

        # OpenRouter uses OpenAI-compatible API
        batch_size = 100
        all_embeddings = []

        async with httpx.AsyncClient(timeout=60.0) as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                response = await client.post(
                    f"{base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "HTTP-Referer": "https://github.com/knowledge-ai/knowledge-ai",
                        "X-Title": "Knowledge AI",
                        "Content-Type": "application/json"
                    },
                    json={
                        "input": batch,
                        "model": model
                    }
                )

                if response.status_code != 200:
                    raise Exception(f"OpenRouter API error: {response.text}")

                data = response.json()

                # Sort by index to maintain order
                sorted_data = sorted(data["data"], key=lambda x: x["index"])
                batch_embeddings = [item["embedding"] for item in sorted_data]
                all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def _embed_ollama(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Ollama."""
        base_url = self.embedding_config.get("base_url", "http://localhost:11434")
        model = self.embedding_config.get("model", "nomic-embed-text")
        
        embeddings = []
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            for text in texts:
                response = await client.post(
                    f"{base_url}/api/embeddings",
                    json={
                        "model": model,
                        "prompt": text
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"Ollama API error: {response.text}")
                
                data = response.json()
                embeddings.append(data["embedding"])
        
        return embeddings
    
    def get_dimension(self) -> int:
        """Get the embedding dimension for the current provider."""
        dimensions = {
            "openai": {
                "text-embedding-3-small": 1536,
                "text-embedding-3-large": 3072,
                "text-embedding-ada-002": 1536,
            },
            "openrouter": {
                "openai/text-embedding-3-small": 1536,
                "openai/text-embedding-3-large": 3072,
                "openai/text-embedding-ada-002": 1536,
            },
            "ollama": {
                "nomic-embed-text": 768,
                "mxbai-embed-large": 1024,
                "all-minilm": 384,
            }
        }
        
        provider_dims = dimensions.get(self.provider, {})
        model = self.embedding_config.get("model", "")
        
        return provider_dims.get(model, 1536)  # Default to OpenAI small
