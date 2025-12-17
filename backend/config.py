"""
Configuration management for Knowledge AI.
Handles API keys and provider settings with secure storage.
"""

import os
import json
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
import base64
import hashlib


class Config:
    """Configuration manager with encrypted storage for API keys."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".knowledge-ai"
        self.config_file = self.config_dir / "config.json"
        self.key_file = self.config_dir / ".key"
        
        # Configuration values
        self.openai_api_key: Optional[str] = None
        self.anthropic_api_key: Optional[str] = None
        self.embedding_provider: str = "openai"  # openai, ollama
        self.chat_provider: str = "anthropic"  # openai, anthropic, ollama
        self.ollama_base_url: str = "http://localhost:11434"
        self.ollama_model: str = "llama3.2"
        self.ollama_embedding_model: str = "nomic-embed-text"
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_encryption_key(self) -> bytes:
        """Get or create encryption key for API keys."""
        if self.key_file.exists():
            return self.key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
            self.key_file.chmod(0o600)  # Secure permissions
            return key
    
    def _encrypt(self, value: str) -> str:
        """Encrypt a string value."""
        if not value:
            return ""
        f = Fernet(self._get_encryption_key())
        return f.encrypt(value.encode()).decode()
    
    def _decrypt(self, value: str) -> str:
        """Decrypt an encrypted string."""
        if not value:
            return ""
        try:
            f = Fernet(self._get_encryption_key())
            return f.decrypt(value.encode()).decode()
        except Exception:
            return ""
    
    def load(self):
        """Load configuration from disk."""
        if not self.config_file.exists():
            return
        
        try:
            data = json.loads(self.config_file.read_text())
            
            # Decrypt API keys
            if "openai_api_key" in data:
                self.openai_api_key = self._decrypt(data["openai_api_key"])
            if "anthropic_api_key" in data:
                self.anthropic_api_key = self._decrypt(data["anthropic_api_key"])
            
            # Load other settings
            self.embedding_provider = data.get("embedding_provider", "openai")
            self.chat_provider = data.get("chat_provider", "anthropic")
            self.ollama_base_url = data.get("ollama_base_url", "http://localhost:11434")
            self.ollama_model = data.get("ollama_model", "llama3.2")
            self.ollama_embedding_model = data.get("ollama_embedding_model", "nomic-embed-text")
            
        except Exception as e:
            print(f"Error loading config: {e}")
    
    def save(self):
        """Save configuration to disk."""
        data = {
            "openai_api_key": self._encrypt(self.openai_api_key) if self.openai_api_key else "",
            "anthropic_api_key": self._encrypt(self.anthropic_api_key) if self.anthropic_api_key else "",
            "embedding_provider": self.embedding_provider,
            "chat_provider": self.chat_provider,
            "ollama_base_url": self.ollama_base_url,
            "ollama_model": self.ollama_model,
            "ollama_embedding_model": self.ollama_embedding_model,
        }
        
        self.config_file.write_text(json.dumps(data, indent=2))
        self.config_file.chmod(0o600)  # Secure permissions
    
    def has_valid_config(self) -> bool:
        """Check if we have valid configuration for at least one provider."""
        # Check embedding provider
        has_embeddings = False
        if self.embedding_provider == "openai" and self.openai_api_key:
            has_embeddings = True
        elif self.embedding_provider == "ollama":
            has_embeddings = True  # Ollama doesn't need API key
        
        # Check chat provider
        has_chat = False
        if self.chat_provider == "openai" and self.openai_api_key:
            has_chat = True
        elif self.chat_provider == "anthropic" and self.anthropic_api_key:
            has_chat = True
        elif self.chat_provider == "ollama":
            has_chat = True
        
        return has_embeddings and has_chat
    
    def get_embedding_config(self) -> dict:
        """Get configuration for embedding provider."""
        if self.embedding_provider == "openai":
            return {
                "provider": "openai",
                "api_key": self.openai_api_key,
                "model": "text-embedding-3-small"
            }
        elif self.embedding_provider == "ollama":
            return {
                "provider": "ollama",
                "base_url": self.ollama_base_url,
                "model": self.ollama_embedding_model
            }
        return {}
    
    def get_chat_config(self) -> dict:
        """Get configuration for chat provider."""
        if self.chat_provider == "openai":
            return {
                "provider": "openai",
                "api_key": self.openai_api_key,
                "model": "gpt-4o"
            }
        elif self.chat_provider == "anthropic":
            return {
                "provider": "anthropic",
                "api_key": self.anthropic_api_key,
                "model": "claude-sonnet-4-20250514"
            }
        elif self.chat_provider == "ollama":
            return {
                "provider": "ollama",
                "base_url": self.ollama_base_url,
                "model": self.ollama_model
            }
        return {}
