"""
AI Chat module with RAG support.
Handles conversations with context from indexed documents.
"""

from typing import List, Dict, Optional
import httpx
import json

from config import Config


class AIChat:
    """AI chat with RAG support using multiple providers."""
    
    SYSTEM_PROMPTS = {
        "chat": """You are a knowledgeable AI assistant helping users understand and work with their personal documents and notes. 

When answering questions:
- Use the provided context from the user's documents to give accurate, relevant answers
- Cite specific documents when referencing information
- If the context doesn't contain relevant information, say so and offer general knowledge
- Be conversational and helpful
- Ask clarifying questions if needed

Context from user's documents will be provided before each question.""",

        "tutor": """You are an expert tutor helping users learn from their own documents and notes.

Your role is to:
- Explain concepts clearly and thoroughly
- Create effective learning materials (quizzes, flashcards, study guides)
- Break down complex topics into understandable parts
- Use examples and analogies from the user's own materials when possible
- Encourage active learning and critical thinking
- Adapt explanations to the user's level of understanding

Always be encouraging and supportive while maintaining accuracy.""",

        "summarize": """You are an expert at analyzing and summarizing documents.

Your task is to:
- Create clear, concise summaries that capture key information
- Identify main themes, arguments, and conclusions
- Highlight important details and relationships
- Organize information logically
- Use bullet points or structured formats when helpful

Focus on accuracy and comprehensiveness while being concise.""",

        "organize": """You are an expert at organizing and structuring information.

Your task is to:
- Analyze documents and suggest organizational structures
- Identify themes, categories, and relationships
- Suggest tags and labels for content
- Find connections between different pieces of content
- Create outlines and hierarchies
- Recommend ways to better structure knowledge

Be thorough and provide actionable suggestions."""
    }
    
    def __init__(self, config: Config):
        self.config = config
        self.chat_config = config.get_chat_config()
        self.provider = self.chat_config.get("provider", "anthropic")
    
    async def chat(
        self,
        message: str,
        context: str = "",
        history: List[Dict] = None,
        mode: str = "chat"
    ) -> str:
        """
        Generate a chat response with optional RAG context.
        
        Args:
            message: User's message
            context: Retrieved context from documents
            history: Conversation history
            mode: Chat mode (chat, tutor, summarize, organize)
            
        Returns:
            AI response string
        """
        if history is None:
            history = []
        
        system_prompt = self.SYSTEM_PROMPTS.get(mode, self.SYSTEM_PROMPTS["chat"])
        
        # Build the full prompt with context
        if context:
            full_message = f"""Here is relevant context from the user's documents:

<context>
{context}
</context>

User's question/request: {message}"""
        else:
            full_message = message
        
        if self.provider == "anthropic":
            return await self._chat_anthropic(system_prompt, full_message, history)
        elif self.provider == "openai":
            return await self._chat_openai(system_prompt, full_message, history)
        elif self.provider == "ollama":
            return await self._chat_ollama(system_prompt, full_message, history)
        else:
            raise ValueError(f"Unknown chat provider: {self.provider}")
    
    async def _chat_anthropic(
        self,
        system: str,
        message: str,
        history: List[Dict]
    ) -> str:
        """Chat using Anthropic Claude API."""
        api_key = self.chat_config.get("api_key")
        model = self.chat_config.get("model", "claude-sonnet-4-20250514")
        
        if not api_key:
            raise ValueError("Anthropic API key not configured")
        
        # Build messages array
        messages = []
        for msg in history[-10:]:  # Last 10 messages for context
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        messages.append({"role": "user", "content": message})
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "max_tokens": 4096,
                    "system": system,
                    "messages": messages
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Anthropic API error: {response.text}")
            
            data = response.json()
            return data["content"][0]["text"]
    
    async def _chat_openai(
        self,
        system: str,
        message: str,
        history: List[Dict]
    ) -> str:
        """Chat using OpenAI API."""
        api_key = self.chat_config.get("api_key")
        model = self.chat_config.get("model", "gpt-4o")
        
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        
        # Build messages array
        messages = [{"role": "system", "content": system}]
        for msg in history[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        messages.append({"role": "user", "content": message})
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 4096
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.text}")
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def _chat_ollama(
        self,
        system: str,
        message: str,
        history: List[Dict]
    ) -> str:
        """Chat using Ollama local API."""
        base_url = self.chat_config.get("base_url", "http://localhost:11434")
        model = self.chat_config.get("model", "llama3.2")
        
        # Build messages array
        messages = [{"role": "system", "content": system}]
        for msg in history[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        messages.append({"role": "user", "content": message})
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.text}")
            
            data = response.json()
            return data["message"]["content"]
    
    async def stream_chat(
        self,
        message: str,
        context: str = "",
        history: List[Dict] = None,
        mode: str = "chat"
    ):
        """
        Stream chat response (generator).
        Only supported for some providers.
        """
        # For now, fall back to non-streaming
        response = await self.chat(message, context, history, mode)
        yield response
