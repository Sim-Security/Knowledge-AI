"""
Knowledge AI - Local File System RAG Application
A personal knowledge management system with semantic search and AI chat.
"""

import os
import hashlib
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import chromadb
from chromadb.config import Settings
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from document_processor import DocumentProcessor
from embeddings import EmbeddingProvider
from ai_chat import AIChat
from config import Config
from file_filter import SmartFileFilter, FilterStats, create_code_project_filter, create_notes_filter, create_research_filter
from system_utils import HardwareDetector, ModelRecommender, OllamaManager
import httpx

# ============================================================================
# Pydantic Models
# ============================================================================

class IndexRequest(BaseModel):
    path: str
    knowledge_base_id: Optional[str] = None  # If None, uses first/default KB
    recursive: bool = True
    watch: bool = False
    # Filter settings
    filter_preset: Optional[str] = Field(default="auto", pattern="^(auto|code|notes|research|none)$")
    extra_ignore_patterns: Optional[List[str]] = None
    extra_include_patterns: Optional[List[str]] = None
    check_sensitive_content: bool = True
    min_file_size: int = Field(default=50, ge=0)
    max_file_size: int = Field(default=10485760, ge=1024)  # 10MB default

class SearchRequest(BaseModel):
    query: str
    knowledge_base_id: Optional[str] = None  # If None, uses first/default KB
    search_all: bool = False  # If True, search all knowledge bases
    top_k: int = Field(default=10, ge=1, le=50)
    file_types: Optional[List[str]] = None
    folder_filter: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    knowledge_base_id: Optional[str] = None  # If None, uses first/default KB
    search_all: bool = False  # If True, search all knowledge bases for context
    conversation_id: Optional[str] = None
    mode: str = Field(default="chat", pattern="^(chat|tutor|summarize|organize)$")
    include_sources: bool = True
    top_k: int = Field(default=5, ge=1, le=20)

class TutorRequest(BaseModel):
    topic: Optional[str] = None
    document_ids: Optional[List[str]] = None
    mode: str = Field(default="quiz", pattern="^(quiz|explain|flashcards|study_guide)$")

class OrganizeRequest(BaseModel):
    document_ids: Optional[List[str]] = None
    action: str = Field(default="suggest_tags", pattern="^(suggest_tags|find_connections|summarize_all|create_outline)$")

class ConfigUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    embedding_provider: Optional[str] = None
    chat_provider: Optional[str] = None
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    ollama_embedding_model: Optional[str] = None
    openrouter_chat_model: Optional[str] = None
    openrouter_embedding_model: Optional[str] = None


class FilterPreviewRequest(BaseModel):
    """Preview what files would be indexed without actually indexing."""
    path: str
    recursive: bool = True
    filter_preset: str = Field(default="auto", pattern="^(auto|code|notes|research|none)$")
    extra_ignore_patterns: Optional[List[str]] = None
    check_sensitive_content: bool = True


class BrowseRequest(BaseModel):
    """Request model for browsing directories."""
    path: Optional[str] = None  # If None, returns home directory or drives


class RenameConversationRequest(BaseModel):
    """Request model for renaming a conversation."""
    title: str = Field(..., min_length=1, max_length=200)


class CreateKnowledgeBaseRequest(BaseModel):
    """Request model for creating a knowledge base."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class UpdateKnowledgeBaseRequest(BaseModel):
    """Request model for updating a knowledge base."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

# ============================================================================
# Global State
# ============================================================================

config = Config()
doc_processor = DocumentProcessor()
file_filter: Optional[SmartFileFilter] = None
embedding_provider: Optional[EmbeddingProvider] = None
ai_chat: Optional[AIChat] = None
chroma_client: Optional[chromadb.Client] = None
collection: Optional[chromadb.Collection] = None
file_observer: Optional[Observer] = None
watched_paths: Dict[str, bool] = {}

# Conversation storage with metadata
# Structure: {conv_id: {"title": str, "created_at": str, "updated_at": str, "messages": [...]}}
conversations: Dict[str, Dict[str, Any]] = {}
CONVERSATIONS_FILE = Path.home() / ".knowledge-ai" / "conversations.json"

# Knowledge base storage
# Structure: {kb_id: {"name": str, "description": str, "created_at": str, "embedding_dimension": int, ...}}
knowledge_bases: Dict[str, Dict[str, Any]] = {}
KNOWLEDGE_BASES_FILE = Path.home() / ".knowledge-ai" / "knowledge_bases.json"
active_collections: Dict[str, chromadb.Collection] = {}  # Cache of loaded collections


# ============================================================================
# Knowledge Base Persistence
# ============================================================================

def load_knowledge_bases() -> None:
    """Load knowledge bases metadata from disk."""
    global knowledge_bases
    if KNOWLEDGE_BASES_FILE.exists():
        try:
            with open(KNOWLEDGE_BASES_FILE, "r", encoding="utf-8") as f:
                knowledge_bases = json.load(f)
            print(f"📚 Loaded {len(knowledge_bases)} knowledge bases")
        except Exception as e:
            print(f"⚠️  Failed to load knowledge bases: {e}")
            knowledge_bases = {}
    else:
        knowledge_bases = {}


def save_knowledge_bases() -> None:
    """Persist knowledge bases metadata to disk."""
    try:
        KNOWLEDGE_BASES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(KNOWLEDGE_BASES_FILE, "w", encoding="utf-8") as f:
            json.dump(knowledge_bases, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️  Failed to save knowledge bases: {e}")


def get_collection_for_kb(kb_id: str) -> chromadb.Collection:
    """Get or create ChromaDB collection for a knowledge base."""
    global active_collections
    
    if kb_id in active_collections:
        return active_collections[kb_id]
    
    if kb_id not in knowledge_bases:
        raise HTTPException(status_code=404, detail=f"Knowledge base not found: {kb_id}")
    
    kb_data = knowledge_bases[kb_id]
    collection_name = f"kb_{kb_id}"
    
    # Get current embedding info
    current_provider = config.embedding_provider
    current_model = config.ollama_embedding_model if current_provider == "ollama" else config.openrouter_embedding_model
    current_dimension = embedding_provider.get_dimension() if embedding_provider else 1536
    
    # Check if collection exists
    existing_collections = [c.name for c in chroma_client.list_collections()]
    
    if collection_name in existing_collections:
        coll = chroma_client.get_collection(collection_name)
        # Check for dimension mismatch
        coll_metadata = coll.metadata or {}
        stored_dimension = coll_metadata.get("embedding_dimension")
        if stored_dimension and stored_dimension != current_dimension:
            stored_model = coll_metadata.get("embedding_model", "unknown")
            raise HTTPException(
                status_code=400, 
                detail=f"Embedding dimension mismatch! Collection was created with {stored_model} ({stored_dimension}D) "
                       f"but current model is {current_model} ({current_dimension}D). "
                       f"Either clear this knowledge base and re-index, or switch to a compatible embedding model."
            )
    else:
        # Create new collection with dimension metadata
        coll = chroma_client.create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_dimension": current_dimension,
                "embedding_provider": current_provider,
                "embedding_model": current_model,
                "knowledge_base_id": kb_id,
            }
        )
        # Update KB metadata
        kb_data["embedding_dimension"] = current_dimension
        kb_data["embedding_provider"] = current_provider
        kb_data["embedding_model"] = current_model
        save_knowledge_bases()
    
    active_collections[kb_id] = coll
    return coll


def create_default_knowledge_base() -> str:
    """Create a default knowledge base if none exist."""
    default_id = "general"
    if default_id not in knowledge_bases:
        knowledge_bases[default_id] = {
            "name": "General",
            "description": "Default knowledge base",
            "created_at": datetime.now().isoformat(),
        }
        save_knowledge_bases()
        print("📚 Created default 'General' knowledge base")
    return default_id


def get_default_kb_id() -> str:
    """Get the default knowledge base ID (first one if multiple exist)."""
    if not knowledge_bases:
        return create_default_knowledge_base()
    # Return 'general' if it exists, otherwise first one
    if "general" in knowledge_bases:
        return "general"
    return next(iter(knowledge_bases.keys()))

# ============================================================================
# Conversation Persistence
# ============================================================================

def load_conversations() -> None:
    """Load conversations from disk."""
    global conversations
    if CONVERSATIONS_FILE.exists():
        try:
            with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Migrate old format (list of messages) to new format (dict with metadata)
                for conv_id, conv_data in data.items():
                    if isinstance(conv_data, list):
                        # Old format - convert to new
                        conversations[conv_id] = {
                            "title": "Untitled Conversation",
                            "created_at": datetime.now().isoformat(),
                            "updated_at": datetime.now().isoformat(),
                            "messages": conv_data
                        }
                    else:
                        conversations[conv_id] = conv_data
            print(f"💬 Loaded {len(conversations)} conversations")
        except Exception as e:
            print(f"⚠️  Failed to load conversations: {e}")
            conversations = {}
    else:
        conversations = {}


def save_conversations() -> None:
    """Persist conversations to disk."""
    try:
        CONVERSATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(conversations, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️  Failed to save conversations: {e}")


def generate_title(message: str) -> str:
    """Generate a conversation title from the first message."""
    # Take first 50 chars, clean up
    title = message.strip()[:50]
    if len(message) > 50:
        title += "..."
    return title or "New Conversation"

# ============================================================================
# File Watcher
# ============================================================================

class FileChangeHandler(FileSystemEventHandler):
    """Handles file system changes for auto-reindexing."""
    
    def __init__(self, index_callback):
        self.index_callback = index_callback
        self._debounce_tasks = {}
    
    def on_modified(self, event):
        if not event.is_directory:
            self._schedule_reindex(event.src_path)
    
    def on_created(self, event):
        if not event.is_directory:
            self._schedule_reindex(event.src_path)
    
    def on_deleted(self, event):
        if not event.is_directory:
            self._schedule_delete(event.src_path)
    
    def _schedule_reindex(self, path: str):
        # Debounce rapid changes
        asyncio.create_task(self._debounced_reindex(path))
    
    async def _debounced_reindex(self, path: str):
        await asyncio.sleep(1)  # Wait for file to settle
        await self.index_callback(path)
    
    def _schedule_delete(self, path: str):
        # Remove from index
        if collection:
            file_hash = hashlib.md5(path.encode()).hexdigest()
            try:
                collection.delete(where={"file_path": path})
            except Exception as e:
                print(f"Error removing deleted file from index: {e}")

# ============================================================================
# Lifespan Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup application resources."""
    global chroma_client, collection, embedding_provider, ai_chat, file_observer, file_filter
    
    # Initialize ChromaDB
    chroma_path = Path.home() / ".knowledge-ai" / "chroma_db"
    chroma_path.mkdir(parents=True, exist_ok=True)
    
    chroma_client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Initialize default file filter
    file_filter = SmartFileFilter()
    
    # Initialize providers if API keys are configured
    config.load()
    if config.has_valid_config():
        embedding_provider = EmbeddingProvider(config)
        ai_chat = AIChat(config)
    
    # Get current embedding info
    current_provider = config.embedding_provider
    current_model = config.ollama_embedding_model if current_provider == "ollama" else config.openrouter_embedding_model
    current_dimension = embedding_provider.get_dimension() if embedding_provider else 1536
    
    # Check if collection exists and validate dimensions
    existing_collections = [c.name for c in chroma_client.list_collections()]
    
    if "knowledge_base" in existing_collections:
        collection = chroma_client.get_collection("knowledge_base")
        stored_metadata = collection.metadata or {}
        stored_dimension = stored_metadata.get("embedding_dimension")
        stored_provider = stored_metadata.get("embedding_provider")
        stored_model = stored_metadata.get("embedding_model")
        
        # If no stored dimension, try to detect from existing embeddings
        if not stored_dimension and collection.count() > 0:
            try:
                # Sample one embedding to get actual dimension
                sample = collection.get(limit=1, include=["embeddings"])
                embeddings = sample.get("embeddings")
                # Use explicit length check to avoid numpy array boolean ambiguity
                if embeddings is not None and len(embeddings) > 0 and len(embeddings[0]) > 0:
                    stored_dimension = len(embeddings[0])
                    stored_provider = "legacy"
                    stored_model = "unknown"
                    print(f"🔍 Detected legacy collection with {stored_dimension}D embeddings")
            except Exception as e:
                print(f"⚠️  Could not detect embedding dimension: {e}")
        
        # Check for dimension mismatch - WARN but don't auto-clear
        if stored_dimension and stored_dimension != current_dimension:
            print(f"⚠️  Embedding dimension mismatch detected!")
            print(f"   Collection was indexed with: {stored_provider}/{stored_model} ({stored_dimension}D)")
            print(f"   Current configuration: {current_provider}/{current_model} ({current_dimension}D)")
            print(f"   ⚠️  Queries will fail! Either:")
            print(f"      1. Switch to a {stored_dimension}D embedding model, OR")
            print(f"      2. Clear index and re-index with the new model")
            # Store mismatch info for API to report
            collection._dimension_mismatch = {
                "has_mismatch": True,
                "stored_dimension": stored_dimension,
                "stored_provider": stored_provider,
                "stored_model": stored_model,
                "current_dimension": current_dimension,
                "current_provider": current_provider,
                "current_model": current_model,
            }
        else:
            collection._dimension_mismatch = {"has_mismatch": False}
            print(f"📊 Collection ready: {stored_provider or 'unknown'}/{stored_model or 'unknown'} ({stored_dimension or 'empty'}D, {collection.count()} docs)")
    else:
        # Create new collection with dimension metadata
        collection = chroma_client.create_collection(
            name="knowledge_base",
            metadata={
                "hnsw:space": "cosine",
                "embedding_dimension": current_dimension,
                "embedding_provider": current_provider,
                "embedding_model": current_model,
            }
        )
        print(f"📊 New collection created for {current_provider}/{current_model} ({current_dimension}D)")
    
    # Initialize file observer
    file_observer = Observer()
    file_observer.start()
    
    # Load persisted conversations
    load_conversations()
    
    # Load knowledge bases and create default if none exist
    load_knowledge_bases()
    if not knowledge_bases:
        create_default_knowledge_base()
    
    print("🧠 Knowledge AI initialized successfully!")
    print(f"📁 Database location: {chroma_path}")
    print(f"🔍 Smart file filter active with {len(file_filter.ignore_dirs)} ignored directories")
    print(f"📚 {len(knowledge_bases)} knowledge base(s) available")
    
    yield
    
    # Cleanup
    if file_observer:
        file_observer.stop()
        file_observer.join()
    
    print("👋 Knowledge AI shutdown complete")

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Knowledge AI",
    description="Local file system RAG with semantic search and AI chat",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Helper Functions
# ============================================================================

async def index_single_file(file_path: str, target_collection: chromadb.Collection = None) -> Dict[str, Any]:
    """Index a single file and add to vector store.
    
    Args:
        file_path: Path to the file to index
        target_collection: ChromaDB collection to index into (uses global collection if None)
    """
    if not embedding_provider:
        raise HTTPException(status_code=400, detail="Embedding provider not configured")
    
    # Use provided collection or fall back to global
    coll = target_collection if target_collection is not None else collection
    if coll is None:
        raise HTTPException(status_code=400, detail="No collection available")
    
    path = Path(file_path)
    if not path.exists():
        return {"status": "skipped", "reason": "file not found"}
    
    # Check if file type is supported
    if not doc_processor.is_supported(path):
        return {"status": "skipped", "reason": "unsupported file type"}
    
    try:
        # Extract content
        content, metadata = doc_processor.process(path)
        if not content or len(content.strip()) < 10:
            return {"status": "skipped", "reason": "no content extracted"}
        
        # Chunk the content
        chunks = doc_processor.chunk_text(content, chunk_size=1000, overlap=200)
        
        # Generate embeddings
        embeddings = await embedding_provider.embed_texts(chunks)
        
        # Prepare for ChromaDB
        file_hash = hashlib.md5(str(path).encode()).hexdigest()
        
        # Remove existing entries for this file
        try:
            coll.delete(where={"file_hash": file_hash})
        except:
            pass
        
        # Add new entries
        ids = [f"{file_hash}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "file_path": str(path),
                "file_name": path.name,
                "file_type": path.suffix.lower(),
                "file_hash": file_hash,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "indexed_at": datetime.now().isoformat(),
                **metadata
            }
            for i in range(len(chunks))
        ]
        
        coll.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )
        
        return {
            "status": "indexed",
            "file": str(path),
            "chunks": len(chunks),
            "metadata": metadata
        }
        
    except Exception as e:
        return {"status": "error", "file": str(path), "error": str(e)}

# ============================================================================
# API Endpoints
# ============================================================================

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    knowledge_base_id: Optional[str] = Form(None)
):
    """Upload and index a file."""
    try:
        # Determine target KB
        kb_id = knowledge_base_id or get_default_kb_id()
        
        # Ensure uploads directory exists
        upload_dir = Path.home() / ".knowledge-ai" / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Safe filename
        safe_filename = Path(file.filename).name
        file_path = upload_dir / safe_filename
        
        # Handle duplicate filenames - append timestamp
        if file_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = file_path.stem
            suffix = file_path.suffix
            file_path = upload_dir / f"{stem}_{timestamp}{suffix}"
            
        # Write file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        # Index the file
        # Get collection for KB
        coll = get_collection_for_kb(kb_id)
        
        # Index
        result = await index_single_file(str(file_path), target_collection=coll)
        
        return {
            "status": "uploaded",
            "file": file.filename,
            "saved_as": str(file_path),
            "indexing_result": result,
            "knowledge_base_id": kb_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "name": "Knowledge AI",
        "version": "1.0.0",
        "indexed_documents": collection.count() if collection else 0
    }


@app.post("/browse")
async def browse_directory(request: BrowseRequest):
    """Browse directory contents for folder selection."""
    import platform
    
    items = []
    
    if request.path is None or request.path == "":
        # Return root-level options: home directory and shortcuts
        home = Path.home()
        current_path = str(home)
        
        # Add common user directories as shortcuts
        shortcuts = [
            ("Home", home),
            ("Desktop", home / "Desktop"),
            ("Documents", home / "Documents"),
            ("Downloads", home / "Downloads"),
        ]
        
        for name, shortcut_path in shortcuts:
            if shortcut_path.exists():
                items.append({
                    "name": name,
                    "path": str(shortcut_path),
                    "type": "shortcut",
                    "is_dir": True,
                })
        
        # On Windows, also list available drives
        if platform.system() == "Windows":
            import string
            for drive in string.ascii_uppercase:
                drive_path = f"{drive}:\\"
                if os.path.exists(drive_path):
                    items.append({
                        "name": f"{drive}:",
                        "path": drive_path,
                        "type": "drive",
                        "is_dir": True,
                    })
    else:
        # Browse the specified path
        try:
            path = Path(request.path).expanduser().resolve()
            current_path = str(path)
            
            if not path.exists():
                raise HTTPException(status_code=404, detail=f"Path not found: {path}")
            
            if not path.is_dir():
                raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")
            
            # List directory contents
            try:
                for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                    try:
                        is_dir = item.is_dir()
                        is_hidden = item.name.startswith('.')
                        
                        if is_dir:
                            items.append({
                                "name": item.name,
                                "path": str(item),
                                "type": "directory",
                                "is_dir": True,
                                "is_hidden": is_hidden,
                            })
                        else:
                            # Include files that can be indexed
                            suffix = item.suffix.lower()
                            supported_extensions = {'.txt', '.md', '.pdf', '.py', '.js', '.jsx', '.ts', '.tsx', 
                                                   '.html', '.css', '.json', '.yaml', '.yml', '.xml', '.csv',
                                                   '.doc', '.docx', '.pptx', '.ppt', '.rst', '.tex', '.log',
                                                   '.java', '.c', '.cpp', '.h', '.hpp', '.go', '.rs', '.rb',
                                                   '.php', '.sql', '.sh', '.bat', '.ps1', '.r', '.scala', '.swift'}
                            if suffix in supported_extensions:
                                items.append({
                                    "name": item.name,
                                    "path": str(item),
                                    "type": "file",
                                    "is_dir": False,
                                    "is_hidden": is_hidden,
                                    "extension": suffix,
                                })
                    except PermissionError:
                        # Skip items we can't access
                        continue
            except PermissionError:
                raise HTTPException(status_code=403, detail=f"Permission denied: {path}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # Get parent path for navigation
    parent_path = None
    if request.path:
        parent = Path(request.path).expanduser().resolve().parent
        if parent != Path(request.path).expanduser().resolve():
            parent_path = str(parent)
    
    return {
        "path": current_path if request.path else str(Path.home()),
        "parent": parent_path,
        "items": items,
    }


# ============================================================================
# Knowledge Base Endpoints
# ============================================================================

@app.get("/knowledge-bases")
async def list_knowledge_bases():
    """List all knowledge bases."""
    kb_list = []
    for kb_id, kb_data in knowledge_bases.items():
        # Get unique file count from ChromaDB collection (not chunks)
        try:
            coll = get_collection_for_kb(kb_id)
            chunk_count = coll.count()
            if chunk_count > 0:
                # Get unique files by counting distinct file paths
                all_data = coll.get(include=["metadatas"])
                unique_files = set(meta.get("file_path", "") for meta in all_data.get("metadatas", []))
                file_count = len(unique_files)
            else:
                file_count = 0
        except:
            file_count = 0
            chunk_count = 0
        
        kb_list.append({
            "id": kb_id,
            "name": kb_data.get("name", "Untitled"),
            "description": kb_data.get("description"),
            "created_at": kb_data.get("created_at"),
            "document_count": file_count,  # Unique files, not chunks
            "chunk_count": chunk_count,
            "embedding_provider": kb_data.get("embedding_provider"),
            "embedding_model": kb_data.get("embedding_model"),
        })
    
    # Sort by created_at
    kb_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {"knowledge_bases": kb_list}


@app.post("/knowledge-bases")
async def create_knowledge_base(request: CreateKnowledgeBaseRequest):
    """Create a new knowledge base."""
    # Generate unique ID from name
    base_id = request.name.lower().replace(" ", "_")[:20]
    base_id = "".join(c for c in base_id if c.isalnum() or c == "_")
    
    # Ensure uniqueness
    kb_id = base_id
    counter = 1
    while kb_id in knowledge_bases:
        kb_id = f"{base_id}_{counter}"
        counter += 1
    
    knowledge_bases[kb_id] = {
        "name": request.name,
        "description": request.description,
        "created_at": datetime.now().isoformat(),
    }
    save_knowledge_bases()
    
    # Pre-create the collection
    get_collection_for_kb(kb_id)
    
    return {
        "id": kb_id,
        "name": request.name,
        "description": request.description,
        "created_at": knowledge_bases[kb_id]["created_at"],
    }


@app.get("/knowledge-bases/{kb_id}")
async def get_knowledge_base(kb_id: str):
    """Get details of a specific knowledge base."""
    if kb_id not in knowledge_bases:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    kb_data = knowledge_bases[kb_id]
    
    try:
        coll = get_collection_for_kb(kb_id)
        doc_count = coll.count()
    except:
        doc_count = 0
    
    return {
        "id": kb_id,
        "name": kb_data.get("name", "Untitled"),
        "description": kb_data.get("description"),
        "created_at": kb_data.get("created_at"),
        "document_count": doc_count,
        "embedding_provider": kb_data.get("embedding_provider"),
        "embedding_model": kb_data.get("embedding_model"),
        "embedding_dimension": kb_data.get("embedding_dimension"),
    }


@app.patch("/knowledge-bases/{kb_id}")
async def update_knowledge_base(kb_id: str, request: UpdateKnowledgeBaseRequest):
    """Update a knowledge base's name or description."""
    if kb_id not in knowledge_bases:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    if request.name is not None:
        knowledge_bases[kb_id]["name"] = request.name
    if request.description is not None:
        knowledge_bases[kb_id]["description"] = request.description
    
    save_knowledge_bases()
    
    return {"status": "updated", "id": kb_id}


@app.delete("/knowledge-bases/{kb_id}")
async def delete_knowledge_base(kb_id: str):
    """Delete a knowledge base and its documents."""
    if kb_id not in knowledge_bases:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    # Don't allow deleting the last knowledge base
    if len(knowledge_bases) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last knowledge base")
    
    # Delete ChromaDB collection
    collection_name = f"kb_{kb_id}"
    try:
        existing_collections = [c.name for c in chroma_client.list_collections()]
        if collection_name in existing_collections:
            chroma_client.delete_collection(collection_name)
    except Exception as e:
        print(f"⚠️  Failed to delete collection: {e}")
    
    # Remove from cache
    if kb_id in active_collections:
        del active_collections[kb_id]
    
    # Remove from storage
    del knowledge_bases[kb_id]
    save_knowledge_bases()
    
    return {"status": "deleted", "id": kb_id}


@app.get("/config")
async def get_config():
    """Get current configuration (without sensitive data)."""
    return {
        "embedding_provider": config.embedding_provider,
        "chat_provider": config.chat_provider,
        "ollama_base_url": config.ollama_base_url,
        "ollama_model": config.ollama_model,
        "ollama_embedding_model": config.ollama_embedding_model,
        "openrouter_chat_model": config.openrouter_chat_model,
        "openrouter_embedding_model": config.openrouter_embedding_model,
        "has_openai_key": bool(config.openai_api_key),
        "has_anthropic_key": bool(config.anthropic_api_key),
        "has_openrouter_key": bool(config.openrouter_api_key),
        "is_configured": config.has_valid_config()
    }

@app.post("/config")
async def update_config(update: ConfigUpdate):
    """Update configuration."""
    global embedding_provider, ai_chat

    if update.openai_api_key is not None:
        config.openai_api_key = update.openai_api_key
    if update.anthropic_api_key is not None:
        config.anthropic_api_key = update.anthropic_api_key
    if update.openrouter_api_key is not None:
        config.openrouter_api_key = update.openrouter_api_key
    if update.embedding_provider is not None:
        config.embedding_provider = update.embedding_provider
    if update.chat_provider is not None:
        config.chat_provider = update.chat_provider
    if update.ollama_base_url is not None:
        config.ollama_base_url = update.ollama_base_url
    if update.ollama_model is not None:
        config.ollama_model = update.ollama_model
    if update.ollama_embedding_model is not None:
        config.ollama_embedding_model = update.ollama_embedding_model
    if update.openrouter_chat_model is not None:
        config.openrouter_chat_model = update.openrouter_chat_model
    if update.openrouter_embedding_model is not None:
        config.openrouter_embedding_model = update.openrouter_embedding_model

    config.save()

    # Reinitialize providers
    if config.has_valid_config():
        embedding_provider = EmbeddingProvider(config)
        ai_chat = AIChat(config)

    return {"status": "updated", "is_configured": config.has_valid_config()}


# All known embedding models with their dimensions
EMBEDDING_MODELS = {
    # OpenRouter / OpenAI models
    "openai/text-embedding-3-small": {"provider": "openrouter", "dimension": 1536, "name": "OpenAI Small"},
    "openai/text-embedding-3-large": {"provider": "openrouter", "dimension": 3072, "name": "OpenAI Large"},
    "openai/text-embedding-ada-002": {"provider": "openrouter", "dimension": 1536, "name": "OpenAI Ada"},
    # Ollama models
    "nomic-embed-text": {"provider": "ollama", "dimension": 768, "name": "Nomic Embed Text"},
    "mxbai-embed-large": {"provider": "ollama", "dimension": 1024, "name": "MixedBread Large"},
    "all-minilm": {"provider": "ollama", "dimension": 384, "name": "All-MiniLM"},
    "snowflake-arctic-embed": {"provider": "ollama", "dimension": 1024, "name": "Snowflake Arctic"},
    "bge-large": {"provider": "ollama", "dimension": 1024, "name": "BGE Large"},
    "bge-m3": {"provider": "ollama", "dimension": 1024, "name": "BGE-M3"},
}


@app.get("/embedding/status")
async def get_embedding_status():
    """Get current embedding/collection status and compatible models."""
    # Get collection info
    collection_info = {
        "document_count": collection.count() if collection else 0,
        "dimension": None,
        "provider": None,
        "model": None,
    }
    
    # Try to get dimension from metadata
    if collection:
        metadata = collection.metadata or {}
        collection_info["dimension"] = metadata.get("embedding_dimension")
        collection_info["provider"] = metadata.get("embedding_provider")
        collection_info["model"] = metadata.get("embedding_model")
        
        # If no metadata but has documents, try to detect dimension
        if not collection_info["dimension"] and collection.count() > 0:
            try:
                sample = collection.get(limit=1, include=["embeddings"])
                embeddings = sample.get("embeddings")
                if embeddings is not None and len(embeddings) > 0 and len(embeddings[0]) > 0:
                    collection_info["dimension"] = len(embeddings[0])
                    collection_info["provider"] = "legacy"
                    collection_info["model"] = "unknown"
            except:
                pass
    
    # Get current config
    current_provider = config.embedding_provider
    current_model = config.ollama_embedding_model if current_provider == "ollama" else config.openrouter_embedding_model
    current_dimension = embedding_provider.get_dimension() if embedding_provider else None
    
    # Check for mismatch
    has_mismatch = False
    if collection_info["dimension"] and current_dimension:
        has_mismatch = collection_info["dimension"] != current_dimension
    
    # Group models by dimension
    models_by_dimension = {}
    for model_id, info in EMBEDDING_MODELS.items():
        dim = info["dimension"]
        if dim not in models_by_dimension:
            models_by_dimension[dim] = []
        models_by_dimension[dim].append({
            "id": model_id,
            "name": info["name"],
            "provider": info["provider"],
            "dimension": dim,
            "compatible": collection_info["dimension"] is None or dim == collection_info["dimension"],
        })
    
    # Find compatible models for current collection
    compatible_models = []
    if collection_info["dimension"]:
        compatible_models = models_by_dimension.get(collection_info["dimension"], [])
    
    return {
        "collection": collection_info,
        "current": {
            "provider": current_provider,
            "model": current_model,
            "dimension": current_dimension,
        },
        "has_dimension_mismatch": has_mismatch,
        "compatible_models": compatible_models,
        "all_models_by_dimension": models_by_dimension,
    }

@app.get("/models/openrouter")
async def get_openrouter_models():
    """Fetch available models from OpenRouter API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://openrouter.ai/api/v1/models")

            if response.status_code != 200:
                return {"error": "Failed to fetch models"}

            data = response.json()

            # Categorize models
            chat_models = []
            embedding_models = []

            for model in data.get("data", []):
                model_info = {
                    "id": model["id"],
                    "name": model.get("name", model["id"]),
                    "description": model.get("description", ""),
                    "context_length": model.get("context_length", 0),
                    "pricing": model.get("pricing", {}),
                }

                # Categorize by type
                if "embed" in model["id"].lower():
                    embedding_models.append(model_info)
                else:
                    chat_models.append(model_info)

            return {
                "chat_models": chat_models,
                "embedding_models": embedding_models,
                "total": len(data.get("data", []))
            }
    except Exception as e:
        return {"error": str(e)}


@app.get("/models/ollama")
async def get_ollama_models():
    """Fetch available local Ollama models."""
    try:
        ollama_url = config.ollama_base_url or "http://localhost:11434"

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")

            if response.status_code != 200:
                return {"error": "Ollama not running or not accessible"}

            data = response.json()
            models = [
                {
                    "id": model["name"],
                    "name": model["name"],
                    "size": model.get("size", 0),
                    "modified": model.get("modified_at", "")
                }
                for model in data.get("models", [])
            ]

            return {"models": models, "total": len(models)}
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# System Detection & Local Mode Endpoints
# ============================================================================

class PullModelRequest(BaseModel):
    """Request model for pulling an Ollama model."""
    model_name: str


@app.get("/system/hardware")
async def get_system_hardware():
    """Detect system hardware (CPU, RAM, GPU) for local model recommendations."""
    try:
        system_info = HardwareDetector.get_system_info()
        gpu_info = HardwareDetector.detect_gpu()
        
        return {
            "system": system_info,
            "gpu": gpu_info
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/system/recommendations")
async def get_model_recommendations():
    """Get recommended local models based on detected hardware."""
    try:
        system_info = HardwareDetector.get_system_info()
        gpu_info = HardwareDetector.detect_gpu()
        
        hardware = {
            "system": system_info,
            "gpu": gpu_info
        }
        
        recommendations = ModelRecommender.recommend_models(hardware)
        
        return recommendations
    except Exception as e:
        return {"error": str(e)}


@app.get("/system/ollama/status")
async def get_ollama_status():
    """Check if Ollama is installed and running."""
    try:
        status = await OllamaManager.check_ollama_installed()
        return status
    except Exception as e:
        return {"error": str(e)}


@app.get("/system/ollama/models")
async def get_installed_ollama_models():
    """List locally installed Ollama models."""
    try:
        models = await OllamaManager.list_models()
        return {"models": models, "total": len(models)}
    except Exception as e:
        return {"error": str(e)}


@app.post("/system/ollama/pull")
async def pull_ollama_model(request: PullModelRequest):
    """Start pulling an Ollama model (downloads in background)."""
    try:
        result = await OllamaManager.pull_model(request.model_name)
        return result
    except Exception as e:
        return {"error": str(e)}


@app.get("/system/local-setup")
async def get_local_setup_info():
    """Get comprehensive local setup information: hardware, recommendations, and Ollama status."""
    try:
        # Get hardware info
        system_info = HardwareDetector.get_system_info()
        gpu_info = HardwareDetector.detect_gpu()
        
        hardware = {
            "system": system_info,
            "gpu": gpu_info
        }
        
        # Get recommendations
        recommendations = ModelRecommender.recommend_models(hardware)
        
        # Get Ollama status
        ollama_status = await OllamaManager.check_ollama_installed()
        
        # Get installed models if Ollama is running
        installed_models = []
        if ollama_status.get("running"):
            installed_models = await OllamaManager.list_models()
        
        # Check if recommended models are already installed
        recommended_chat = recommendations.get("chat", {}).get("recommended", "")
        recommended_embedding = recommendations.get("embedding", {}).get("recommended", "")
        
        installed_model_names = [m.get("name", "").split(":")[0] for m in installed_models]
        
        has_recommended_chat = any(recommended_chat.split(":")[0] in name for name in installed_model_names)
        has_recommended_embedding = any(recommended_embedding.split(":")[0] in name for name in installed_model_names)
        
        return {
            "hardware": hardware,
            "recommendations": recommendations,
            "ollama": {
                **ollama_status,
                "installed_models": installed_models
            },
            "ready_for_local": {
                "ollama_installed": ollama_status.get("installed", False),
                "ollama_running": ollama_status.get("running", False),
                "has_chat_model": has_recommended_chat,
                "has_embedding_model": has_recommended_embedding,
                "fully_ready": (
                    ollama_status.get("running", False) and
                    has_recommended_chat and
                    has_recommended_embedding
                )
            }
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/index")
async def index_directory(request: IndexRequest, background_tasks: BackgroundTasks):
    """Index a directory or file with smart filtering."""
    path = Path(request.path).expanduser().resolve()
    
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    
    if not embedding_provider:
        raise HTTPException(status_code=400, detail="Please configure an embedding provider first")
    
    # Get the target knowledge base collection
    kb_id = request.knowledge_base_id or get_default_kb_id()
    target_collection = get_collection_for_kb(kb_id)
    
    # Create file filter based on preset
    if request.filter_preset == "none":
        # No filtering - dangerous but allowed
        current_filter = None
    elif request.filter_preset == "code":
        current_filter = create_code_project_filter()
    elif request.filter_preset == "notes":
        current_filter = create_notes_filter()
    elif request.filter_preset == "research":
        current_filter = create_research_filter()
    else:  # "auto" - detect based on path contents
        # Check for common project indicators
        has_package_json = (path / "package.json").exists() if path.is_dir() else False
        has_pyproject = (path / "pyproject.toml").exists() if path.is_dir() else False
        has_cargo = (path / "Cargo.toml").exists() if path.is_dir() else False
        has_go_mod = (path / "go.mod").exists() if path.is_dir() else False
        
        if has_package_json or has_pyproject or has_cargo or has_go_mod:
            current_filter = create_code_project_filter()
        else:
            current_filter = SmartFileFilter(
                min_file_size=request.min_file_size,
                max_file_size=request.max_file_size,
                check_sensitive_content=request.check_sensitive_content,
                extra_ignore_patterns=request.extra_ignore_patterns,
                extra_include_patterns=request.extra_include_patterns,
            )
    
    # Apply custom settings to filter
    if current_filter and request.extra_ignore_patterns:
        current_filter.extra_ignore_patterns.update(request.extra_ignore_patterns)
    if current_filter and request.extra_include_patterns:
        current_filter.extra_include_patterns.update(request.extra_include_patterns)
    
    results = {
        "indexed": 0,
        "skipped": 0,
        "errors": 0,
        "files": [],
        "filter_stats": None,
        "sensitive_files_blocked": 0,
        "knowledge_base_id": kb_id,
    }
    
    if path.is_file():
        # Single file - still apply filter
        if current_filter:
            filter_result = current_filter.should_index(path, path.parent)
            if not filter_result.should_index:
                return {
                    **results,
                    "skipped": 1,
                    "files": [{
                        "status": "skipped",
                        "file": str(path),
                        "reason": filter_result.reason,
                        "category": filter_result.category
                    }]
                }
        
        result = await index_single_file(str(path), target_collection)
        results["files"].append(result)
        if result["status"] == "indexed":
            results["indexed"] += 1
        elif result["status"] == "skipped":
            results["skipped"] += 1
        else:
            results["errors"] += 1
    else:
        # Index directory with filtering
        pattern = "**/*" if request.recursive else "*"
        all_files = [f for f in path.glob(pattern) if f.is_file()]
        
        # Apply smart filter
        if current_filter:
            files_to_index, filter_stats = current_filter.filter_paths(
                all_files, 
                path, 
                read_content=True  # Enable content-based filtering
            )
            results["filter_stats"] = filter_stats.to_dict()
            results["sensitive_files_blocked"] = filter_stats.ignored_sensitive
        else:
            files_to_index = all_files
        
        # Now index only the filtered files
        for file_path in files_to_index:
            if doc_processor.is_supported(file_path):
                result = await index_single_file(str(file_path), target_collection)
                results["files"].append(result)
                if result["status"] == "indexed":
                    results["indexed"] += 1
                elif result["status"] == "skipped":
                    results["skipped"] += 1
                else:
                    results["errors"] += 1
    
    # Set up file watching if requested
    if request.watch and path.is_dir():
        handler = FileChangeHandler(index_single_file)
        file_observer.schedule(handler, str(path), recursive=request.recursive)
        watched_paths[str(path)] = True
        results["watching"] = True
    
    return results


@app.post("/index/preview")
async def preview_index(request: FilterPreviewRequest):
    """Preview what files would be indexed without actually indexing them."""
    path = Path(request.path).expanduser().resolve()
    
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    
    # Create filter based on preset
    if request.filter_preset == "code":
        current_filter = create_code_project_filter()
    elif request.filter_preset == "notes":
        current_filter = create_notes_filter()
    elif request.filter_preset == "research":
        current_filter = create_research_filter()
    elif request.filter_preset == "none":
        current_filter = None
    else:
        current_filter = SmartFileFilter(
            check_sensitive_content=request.check_sensitive_content,
            extra_ignore_patterns=request.extra_ignore_patterns,
        )
    
    if request.extra_ignore_patterns and current_filter:
        current_filter.extra_ignore_patterns.update(request.extra_ignore_patterns)
    
    # Scan files
    if path.is_file():
        all_files = [path]
    else:
        pattern = "**/*" if request.recursive else "*"
        all_files = [f for f in path.glob(pattern) if f.is_file()]
    
    # Categorize files
    will_index = []
    will_skip = []
    
    if current_filter:
        for file_path in all_files:
            # Quick filter without reading content
            result = current_filter.should_index(file_path, path)
            
            file_info = {
                "path": str(file_path),
                "name": file_path.name,
                "size": file_path.stat().st_size if file_path.exists() else 0,
                "type": file_path.suffix,
            }
            
            if result.should_index and doc_processor.is_supported(file_path):
                will_index.append(file_info)
            else:
                will_skip.append({
                    **file_info,
                    "reason": result.reason or "Unsupported file type",
                    "category": result.category or "unsupported",
                })
    else:
        for file_path in all_files:
            file_info = {
                "path": str(file_path),
                "name": file_path.name,
                "size": file_path.stat().st_size if file_path.exists() else 0,
                "type": file_path.suffix,
            }
            if doc_processor.is_supported(file_path):
                will_index.append(file_info)
            else:
                will_skip.append({
                    **file_info,
                    "reason": "Unsupported file type",
                    "category": "unsupported",
                })
    
    # Group skipped files by category
    skip_summary = {}
    for f in will_skip:
        cat = f.get("category", "other")
        if cat not in skip_summary:
            skip_summary[cat] = {"count": 0, "examples": []}
        skip_summary[cat]["count"] += 1
        if len(skip_summary[cat]["examples"]) < 5:
            skip_summary[cat]["examples"].append(f["name"])
    
    return {
        "path": str(path),
        "total_files": len(all_files),
        "will_index": len(will_index),
        "will_skip": len(will_skip),
        "index_preview": will_index[:50],  # First 50 files
        "skip_summary": skip_summary,
        "filter_config": current_filter.get_summary() if current_filter else None,
    }


@app.get("/filter/config")
async def get_filter_config():
    """Get current filter configuration and available presets."""
    return {
        "current_config": file_filter.get_summary() if file_filter else None,
        "presets": {
            "auto": "Automatically detect project type and apply appropriate filters",
            "code": "Optimized for code repositories (ignores node_modules, venv, etc.)",
            "notes": "Optimized for note-taking (less strict, allows larger files)",
            "research": "Optimized for research/academic (includes PDFs, very large files)",
            "none": "No filtering (use with caution!)",
        },
        "default_ignored_dirs": list(SmartFileFilter.DEFAULT_IGNORE_DIRS)[:20],  # Sample
        "default_ignored_files": list(SmartFileFilter.DEFAULT_IGNORE_FILES)[:20],  # Sample
        "sensitive_patterns_count": len(SmartFileFilter.SENSITIVE_PATTERNS),
    }

@app.post("/search")
async def semantic_search(request: SearchRequest):
    """Perform semantic search across indexed documents."""
    if not embedding_provider:
        raise HTTPException(status_code=400, detail="Embedding provider not configured")
    
    # Get the target collection(s)
    if request.search_all:
        # Search all knowledge bases
        collections_to_search = []
        for kb_id in knowledge_bases.keys():
            try:
                coll = get_collection_for_kb(kb_id)
                if coll.count() > 0:
                    collections_to_search.append((kb_id, coll))
            except:
                pass
        if not collections_to_search:
            return {"results": [], "message": "No documents indexed yet"}
    else:
        # Search specific knowledge base
        kb_id = request.knowledge_base_id or get_default_kb_id()
        target_collection = get_collection_for_kb(kb_id)
        if target_collection.count() == 0:
            return {"results": [], "message": "No documents indexed yet in this knowledge base"}
        collections_to_search = [(kb_id, target_collection)]
    
    # Generate query embedding
    query_embedding = await embedding_provider.embed_texts([request.query])
    
    # Build where filter
    where_filter = None
    if request.file_types or request.folder_filter:
        conditions = []
        if request.file_types:
            conditions.append({"file_type": {"$in": request.file_types}})
        if request.folder_filter:
            conditions.append({"file_path": {"$contains": request.folder_filter}})
        
        if len(conditions) == 1:
            where_filter = conditions[0]
        else:
            where_filter = {"$and": conditions}
    
    # Query all target collections
    all_results = []
    for kb_id, coll in collections_to_search:
        try:
            results = coll.query(
                query_embeddings=query_embedding,
                n_results=request.top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            for i in range(len(results["ids"][0])):
                all_results.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity": 1 - results["distances"][0][i],
                    "knowledge_base_id": kb_id,
                })
        except Exception as e:
            print(f"⚠️  Search error in {kb_id}: {e}")
            continue
    
    # Sort by similarity and limit to top_k
    all_results.sort(key=lambda x: x["similarity"], reverse=True)
    all_results = all_results[:request.top_k]
    
    return {"results": all_results, "query": request.query}

@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat with AI using RAG."""
    if not ai_chat:
        raise HTTPException(status_code=400, detail="Chat provider not configured")
    
    # Get or create conversation
    conv_id = request.conversation_id or hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
    is_new_conversation = conv_id not in conversations
    
    if is_new_conversation:
        conversations[conv_id] = {
            "title": "New Conversation",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": []
        }
    
    # Get relevant context via semantic search
    context_results = []
    if embedding_provider:
        # Get collections to search
        if request.search_all:
            collections_to_search = []
            for kb_id in knowledge_bases.keys():
                try:
                    coll = get_collection_for_kb(kb_id)
                    if coll.count() > 0:
                        collections_to_search.append((kb_id, coll))
                except:
                    pass
        else:
            kb_id = request.knowledge_base_id or get_default_kb_id()
            try:
                coll = get_collection_for_kb(kb_id)
                collections_to_search = [(kb_id, coll)] if coll.count() > 0 else []
            except:
                collections_to_search = []
        
        if collections_to_search:
            query_embedding = await embedding_provider.embed_texts([request.message])
            
            for kb_id, coll in collections_to_search:
                try:
                    search_results = coll.query(
                        query_embeddings=query_embedding,
                        n_results=request.top_k,
                        include=["documents", "metadatas", "distances"]
                    )
                    
                    for i in range(len(search_results["ids"][0])):
                        context_results.append({
                            "content": search_results["documents"][0][i],
                            "source": search_results["metadatas"][0][i].get("file_name", "Unknown"),
                            "knowledge_base": kb_id,
                            "similarity": 1 - search_results["distances"][0][i],
                        })
                except:
                    pass
            
            # Sort by similarity and take top_k
            context_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            context_results = context_results[:request.top_k]
    
    # Build context string
    context_str = ""
    if context_results:
        context_str = "\n\n---\n\n".join([
            f"Source: {r['source']}\n{r['content']}" 
            for r in context_results
        ])
    
    # Get AI response
    response = await ai_chat.chat(
        message=request.message,
        context=context_str,
        history=conversations[conv_id]["messages"],
        mode=request.mode
    )
    
    # Update conversation
    conversations[conv_id]["messages"].append({"role": "user", "content": request.message})
    conversations[conv_id]["messages"].append({"role": "assistant", "content": response})
    conversations[conv_id]["updated_at"] = datetime.now().isoformat()
    
    # Generate title from first user message if this is a new conversation
    if is_new_conversation:
        conversations[conv_id]["title"] = generate_title(request.message)
    
    # Keep history manageable
    if len(conversations[conv_id]["messages"]) > 20:
        conversations[conv_id]["messages"] = conversations[conv_id]["messages"][-20:]
    
    # Persist to disk
    save_conversations()
    
    result = {
        "response": response,
        "conversation_id": conv_id
    }
    
    if request.include_sources and context_results:
        result["sources"] = [{"source": r["source"], "preview": r["content"][:200] + "..."} for r in context_results]
    
    return result

@app.post("/tutor")
async def tutor_mode(request: TutorRequest):
    """Generate tutoring content based on indexed documents."""
    if not ai_chat:
        raise HTTPException(status_code=400, detail="Chat provider not configured")
    
    # Get relevant content
    context_results = []
    if collection.count() > 0 and embedding_provider:
        if request.topic:
            query_embedding = await embedding_provider.embed_texts([request.topic])
            search_results = collection.query(
                query_embeddings=query_embedding,
                n_results=10,
                include=["documents", "metadatas"]
            )
        elif request.document_ids:
            search_results = collection.get(
                ids=request.document_ids,
                include=["documents", "metadatas"]
            )
        else:
            # Get random sample
            search_results = collection.get(
                limit=10,
                include=["documents", "metadatas"]
            )
        
        docs = search_results.get("documents", [[]])[0] if "ids" in search_results else search_results.get("documents", [])
        metas = search_results.get("metadatas", [[]])[0] if "ids" in search_results else search_results.get("metadatas", [])
        
        for i, doc in enumerate(docs):
            context_results.append({
                "content": doc,
                "source": metas[i].get("file_name", "Unknown") if i < len(metas) else "Unknown"
            })
    
    if not context_results:
        return {"error": "No content found for tutoring. Please index some documents first."}
    
    # Generate tutoring content based on mode
    context_str = "\n\n".join([f"From {r['source']}:\n{r['content']}" for r in context_results])
    
    prompts = {
        "quiz": f"Based on this content, generate 5 quiz questions with answers to test understanding:\n\n{context_str}",
        "explain": f"Explain the key concepts from this content in simple terms, as if teaching a student:\n\n{context_str}",
        "flashcards": f"Create 10 flashcards (front/back format) from this content for studying:\n\n{context_str}",
        "study_guide": f"Create a comprehensive study guide with key points, summaries, and important terms from this content:\n\n{context_str}"
    }
    
    response = await ai_chat.chat(
        message=prompts[request.mode],
        context="",
        history=[],
        mode="tutor"
    )
    
    return {
        "mode": request.mode,
        "content": response,
        "sources": [r["source"] for r in context_results]
    }

@app.post("/organize")
async def organize_notes(request: OrganizeRequest):
    """AI-powered note organization and analysis."""
    if not ai_chat:
        raise HTTPException(status_code=400, detail="Chat provider not configured")
    
    # Get documents
    if request.document_ids:
        results = collection.get(
            ids=request.document_ids,
            include=["documents", "metadatas"]
        )
    else:
        results = collection.get(
            limit=50,
            include=["documents", "metadatas"]
        )
    
    docs = results.get("documents", [])
    metas = results.get("metadatas", [])
    
    if not docs:
        return {"error": "No documents found"}
    
    # Build content summary
    content_summary = []
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else {}
        content_summary.append({
            "file": meta.get("file_name", f"Document {i}"),
            "preview": doc[:500] if len(doc) > 500 else doc
        })
    
    content_str = "\n\n---\n\n".join([
        f"File: {c['file']}\nContent: {c['preview']}" 
        for c in content_summary
    ])
    
    prompts = {
        "suggest_tags": f"Analyze these documents and suggest relevant tags/categories for organizing them:\n\n{content_str}",
        "find_connections": f"Find connections, common themes, and relationships between these documents:\n\n{content_str}",
        "summarize_all": f"Provide a comprehensive summary of all the content in these documents:\n\n{content_str}",
        "create_outline": f"Create an organized outline/structure for all this content, grouping related topics:\n\n{content_str}"
    }
    
    response = await ai_chat.chat(
        message=prompts[request.action],
        context="",
        history=[],
        mode="organize"
    )
    
    return {
        "action": request.action,
        "result": response,
        "documents_analyzed": len(docs)
    }

@app.get("/stats")
async def get_stats(knowledge_base_id: Optional[str] = None):
    """Get indexing statistics for a knowledge base."""
    kb_id = knowledge_base_id or get_default_kb_id()
    
    try:
        coll = get_collection_for_kb(kb_id)
    except:
        return {"error": "Knowledge base not found"}
    
    total_chunks = coll.count()
    
    # Get unique files
    if total_chunks > 0:
        all_data = coll.get(include=["metadatas"])
        unique_files = set()
        file_types = {}
        
        for meta in all_data.get("metadatas", []):
            file_path = meta.get("file_path", "")
            file_type = meta.get("file_type", "unknown")
            unique_files.add(file_path)
            file_types[file_type] = file_types.get(file_type, 0) + 1
        
        return {
            "knowledge_base_id": kb_id,
            "total_chunks": total_chunks,
            "unique_files": len(unique_files),
            "file_types": file_types,
            "watched_paths": list(watched_paths.keys())
        }
    
    return {
        "knowledge_base_id": kb_id,
        "total_chunks": 0,
        "unique_files": 0,
        "file_types": {},
        "watched_paths": list(watched_paths.keys())
    }

@app.get("/files")
async def list_indexed_files(knowledge_base_id: Optional[str] = None):
    """List all indexed files in a knowledge base."""
    kb_id = knowledge_base_id or get_default_kb_id()
    
    try:
        coll = get_collection_for_kb(kb_id)
    except:
        return {"files": [], "knowledge_base_id": kb_id}
    
    if coll.count() == 0:
        return {"files": [], "knowledge_base_id": kb_id}
    
    all_data = coll.get(include=["metadatas"])
    
    files = {}
    for meta in all_data.get("metadatas", []):
        file_path = meta.get("file_path", "")
        if file_path not in files:
            files[file_path] = {
                "path": file_path,
                "name": meta.get("file_name", ""),
                "type": meta.get("file_type", ""),
                "chunks": 0,
                "indexed_at": meta.get("indexed_at", ""),
                "file_hash": meta.get("file_hash", ""),
            }
        files[file_path]["chunks"] += 1
    
    return {"files": list(files.values()), "knowledge_base_id": kb_id}

@app.delete("/files/{file_hash}")
async def remove_file(
    file_hash: str, 
    knowledge_base_id: Optional[str] = None,
    file_path: Optional[str] = None
):
    """Remove a file from the index."""
    kb_id = knowledge_base_id or get_default_kb_id()
    
    try:
        coll = get_collection_for_kb(kb_id)
        
        # Prefer deleting by file_path if provided, as it's more reliable
        if file_path:
            # We need to unquote the path if it was URL encoded (handles + as space)
            import urllib.parse
            decoded_path = urllib.parse.unquote_plus(file_path)
            coll.delete(where={"file_path": decoded_path})
        else:
            coll.delete(where={"file_hash": file_hash})
            
        return {"status": "deleted", "file_hash": file_hash, "knowledge_base_id": kb_id}
    except Exception as e:
        print(f"Error deleting file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/index")
async def clear_index(knowledge_base_id: Optional[str] = None):
    """Clear all indexed documents in a knowledge base."""
    kb_id = knowledge_base_id or get_default_kb_id()
    
    try:
        # Get current embedding configuration
        current_provider = config.embedding_provider
        current_model = config.ollama_embedding_model if current_provider == "ollama" else config.openrouter_embedding_model
        current_dimension = embedding_provider.get_dimension() if embedding_provider else 1536
        
        collection_name = f"kb_{kb_id}"
        
        # Delete and recreate the collection
        try:
            chroma_client.delete_collection(collection_name)
        except:
            pass
        
        # Remove from cache
        if kb_id in active_collections:
            del active_collections[kb_id]
        
        # Recreate the collection
        new_coll = chroma_client.create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_dimension": current_dimension,
                "embedding_provider": current_provider,
                "embedding_model": current_model,
                "knowledge_base_id": kb_id,
            }
        )
        active_collections[kb_id] = new_coll
        
        # Update KB metadata
        if kb_id in knowledge_bases:
            knowledge_bases[kb_id]["embedding_dimension"] = current_dimension
            knowledge_bases[kb_id]["embedding_provider"] = current_provider
            knowledge_bases[kb_id]["embedding_model"] = current_model
            save_knowledge_bases()
        
        return {
            "status": "cleared",
            "knowledge_base_id": kb_id,
            "embedding_info": {
                "provider": current_provider,
                "model": current_model,
                "dimension": current_dimension,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations")
async def list_conversations():
    """List all conversations with metadata."""
    conversation_list = []
    for conv_id, conv_data in conversations.items():
        conversation_list.append({
            "id": conv_id,
            "title": conv_data.get("title", "Untitled"),
            "message_count": len(conv_data.get("messages", [])),
            "created_at": conv_data.get("created_at"),
            "updated_at": conv_data.get("updated_at")
        })
    
    # Sort by updated_at descending (most recent first)
    conversation_list.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    
    return {"conversations": conversation_list}


@app.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    """Get a single conversation with all messages."""
    if conv_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv_data = conversations[conv_id]
    return {
        "id": conv_id,
        "title": conv_data.get("title", "Untitled"),
        "messages": conv_data.get("messages", []),
        "created_at": conv_data.get("created_at"),
        "updated_at": conv_data.get("updated_at")
    }


@app.post("/conversations")
async def create_conversation():
    """Create a new empty conversation."""
    conv_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
    conversations[conv_id] = {
        "title": "New Conversation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": []
    }
    save_conversations()
    
    return {
        "id": conv_id,
        "title": conversations[conv_id]["title"],
        "created_at": conversations[conv_id]["created_at"]
    }


@app.patch("/conversations/{conv_id}")
async def rename_conversation(conv_id: str, request: RenameConversationRequest):
    """Rename a conversation."""
    if conv_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversations[conv_id]["title"] = request.title
    conversations[conv_id]["updated_at"] = datetime.now().isoformat()
    save_conversations()
    
    return {"status": "updated", "title": request.title}


@app.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """Delete a conversation."""
    if conv_id in conversations:
        del conversations[conv_id]
        save_conversations()
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Conversation not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

