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

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
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

# ============================================================================
# Pydantic Models
# ============================================================================

class IndexRequest(BaseModel):
    path: str
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
    top_k: int = Field(default=10, ge=1, le=50)
    file_types: Optional[List[str]] = None
    folder_filter: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
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
    embedding_provider: Optional[str] = None
    chat_provider: Optional[str] = None
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None


class FilterPreviewRequest(BaseModel):
    """Preview what files would be indexed without actually indexing."""
    path: str
    recursive: bool = True
    filter_preset: str = Field(default="auto", pattern="^(auto|code|notes|research|none)$")
    extra_ignore_patterns: Optional[List[str]] = None
    check_sensitive_content: bool = True


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
conversations: Dict[str, List[Dict]] = {}

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
    
    collection = chroma_client.get_or_create_collection(
        name="knowledge_base",
        metadata={"hnsw:space": "cosine"}
    )
    
    # Initialize default file filter
    file_filter = SmartFileFilter()
    
    # Initialize providers if API keys are configured
    config.load()
    if config.has_valid_config():
        embedding_provider = EmbeddingProvider(config)
        ai_chat = AIChat(config)
    
    # Initialize file observer
    file_observer = Observer()
    file_observer.start()
    
    print("🧠 Knowledge AI initialized successfully!")
    print(f"📁 Database location: {chroma_path}")
    print(f"🔍 Smart file filter active with {len(file_filter.ignore_dirs)} ignored directories")
    
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

async def index_single_file(file_path: str) -> Dict[str, Any]:
    """Index a single file and add to vector store."""
    if not embedding_provider:
        raise HTTPException(status_code=400, detail="Embedding provider not configured")
    
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
            collection.delete(where={"file_hash": file_hash})
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
        
        collection.add(
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

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "name": "Knowledge AI",
        "version": "1.0.0",
        "indexed_documents": collection.count() if collection else 0
    }

@app.get("/config")
async def get_config():
    """Get current configuration (without sensitive data)."""
    return {
        "embedding_provider": config.embedding_provider,
        "chat_provider": config.chat_provider,
        "ollama_base_url": config.ollama_base_url,
        "ollama_model": config.ollama_model,
        "has_openai_key": bool(config.openai_api_key),
        "has_anthropic_key": bool(config.anthropic_api_key),
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
    if update.embedding_provider is not None:
        config.embedding_provider = update.embedding_provider
    if update.chat_provider is not None:
        config.chat_provider = update.chat_provider
    if update.ollama_base_url is not None:
        config.ollama_base_url = update.ollama_base_url
    if update.ollama_model is not None:
        config.ollama_model = update.ollama_model
    
    config.save()
    
    # Reinitialize providers
    if config.has_valid_config():
        embedding_provider = EmbeddingProvider(config)
        ai_chat = AIChat(config)
    
    return {"status": "updated", "is_configured": config.has_valid_config()}

@app.post("/index")
async def index_directory(request: IndexRequest, background_tasks: BackgroundTasks):
    """Index a directory or file with smart filtering."""
    path = Path(request.path).expanduser().resolve()
    
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    
    if not embedding_provider:
        raise HTTPException(status_code=400, detail="Please configure an embedding provider first")
    
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
        
        result = await index_single_file(str(path))
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
                result = await index_single_file(str(file_path))
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
    
    if collection.count() == 0:
        return {"results": [], "message": "No documents indexed yet"}
    
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
    
    # Query ChromaDB
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=request.top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )
    
    # Format results
    formatted_results = []
    for i in range(len(results["ids"][0])):
        formatted_results.append({
            "id": results["ids"][0][i],
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "similarity": 1 - results["distances"][0][i]  # Convert distance to similarity
        })
    
    return {"results": formatted_results, "query": request.query}

@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat with AI using RAG."""
    if not ai_chat:
        raise HTTPException(status_code=400, detail="Chat provider not configured")
    
    # Get conversation history
    conv_id = request.conversation_id or hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
    if conv_id not in conversations:
        conversations[conv_id] = []
    
    # Get relevant context via semantic search
    context_results = []
    if collection.count() > 0 and embedding_provider:
        query_embedding = await embedding_provider.embed_texts([request.message])
        search_results = collection.query(
            query_embeddings=query_embedding,
            n_results=request.top_k,
            include=["documents", "metadatas"]
        )
        
        for i in range(len(search_results["ids"][0])):
            context_results.append({
                "content": search_results["documents"][0][i],
                "source": search_results["metadatas"][0][i].get("file_name", "Unknown")
            })
    
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
        history=conversations[conv_id],
        mode=request.mode
    )
    
    # Update conversation history
    conversations[conv_id].append({"role": "user", "content": request.message})
    conversations[conv_id].append({"role": "assistant", "content": response})
    
    # Keep history manageable
    if len(conversations[conv_id]) > 20:
        conversations[conv_id] = conversations[conv_id][-20:]
    
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
async def get_stats():
    """Get indexing statistics."""
    if not collection:
        return {"error": "Database not initialized"}
    
    total_chunks = collection.count()
    
    # Get unique files
    if total_chunks > 0:
        all_data = collection.get(include=["metadatas"])
        unique_files = set()
        file_types = {}
        
        for meta in all_data.get("metadatas", []):
            file_path = meta.get("file_path", "")
            file_type = meta.get("file_type", "unknown")
            unique_files.add(file_path)
            file_types[file_type] = file_types.get(file_type, 0) + 1
        
        return {
            "total_chunks": total_chunks,
            "unique_files": len(unique_files),
            "file_types": file_types,
            "watched_paths": list(watched_paths.keys())
        }
    
    return {
        "total_chunks": 0,
        "unique_files": 0,
        "file_types": {},
        "watched_paths": list(watched_paths.keys())
    }

@app.get("/files")
async def list_indexed_files():
    """List all indexed files."""
    if not collection or collection.count() == 0:
        return {"files": []}
    
    all_data = collection.get(include=["metadatas"])
    
    files = {}
    for meta in all_data.get("metadatas", []):
        file_path = meta.get("file_path", "")
        if file_path not in files:
            files[file_path] = {
                "path": file_path,
                "name": meta.get("file_name", ""),
                "type": meta.get("file_type", ""),
                "chunks": 0,
                "indexed_at": meta.get("indexed_at", "")
            }
        files[file_path]["chunks"] += 1
    
    return {"files": list(files.values())}

@app.delete("/files/{file_hash}")
async def remove_file(file_hash: str):
    """Remove a file from the index."""
    try:
        collection.delete(where={"file_hash": file_hash})
        return {"status": "deleted", "file_hash": file_hash}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/index")
async def clear_index():
    """Clear all indexed documents."""
    global collection
    
    try:
        chroma_client.delete_collection("knowledge_base")
        collection = chroma_client.create_collection(
            name="knowledge_base",
            metadata={"hnsw:space": "cosine"}
        )
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations")
async def list_conversations():
    """List all active conversations."""
    return {
        "conversations": [
            {"id": conv_id, "messages": len(msgs)}
            for conv_id, msgs in conversations.items()
        ]
    }

@app.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """Delete a conversation."""
    if conv_id in conversations:
        del conversations[conv_id]
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Conversation not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
