# Knowledge AI 🧠

A powerful local RAG (Retrieval-Augmented Generation) application that lets you chat with your documents, search semantically through your files, and get tutored on your own content.

![Knowledge AI](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![React](https://img.shields.io/badge/react-18-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Features

### 💬 AI Chat with RAG
- Chat naturally with an AI that knows your documents
- Automatic context retrieval from your knowledge base
- Multiple conversation modes: Chat, Tutor, Summarize, Organize
- Source citations for transparency

### 🔍 Semantic Search
- Find content by meaning, not just keywords
- Vector embeddings for deep understanding
- Filter by file type and folder
- Relevance scoring

### 📚 AI Tutor
- **Quiz Mode**: Generate questions to test your knowledge
- **Explain Mode**: Get clear explanations of complex topics
- **Flashcards**: Create study cards automatically
- **Study Guides**: Generate comprehensive guides

### 📁 File Management
- Index entire folders recursively
- **Drag-and-drop file upload**
- **Multiple knowledge bases** - organize documents by project or topic
- Support for multiple file types:
  - Documents: PDF, DOCX, TXT, MD, RTF
  - Code: Python, JavaScript, TypeScript, Java, Go, Rust, etc.
  - Data: CSV, JSON, YAML, XML
  - Presentations: PPTX
  - Spreadsheets: XLSX
  - Notebooks: Jupyter (.ipynb)
- Real-time file watching (auto-reindex on changes)

### 🎯 Multiple AI Providers
- **Ollama** (Default): Run 100% locally with Llama, Mistral, or other models - completely private, no API keys needed
- **OpenRouter**: Access 200+ cloud models including Claude, GPT-4, Gemini, Llama with one API key
- **OpenAI**: GPT-4 for chat, text-embedding-3-small for embeddings (direct)
- **Anthropic**: Claude for intelligent conversations (direct)

## 🚀 Quick Start

### Prerequisites

- Python 3.10 - 3.13 (Python 3.14+ not yet supported)
- Node.js 18 or higher
- **Ollama** (recommended for local operation) - [Download here](https://ollama.com/download)
- Or a cloud API key (OpenRouter, OpenAI, or Anthropic)

### Installation

1. **Clone the repository:**

```bash
git clone https://github.com/Sim-Security/knowledge-ai.git
cd knowledge-ai
```

2. **Setup backend:**

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

3. **Setup frontend:**

```bash
cd ../frontend

# Install dependencies
npm install
```

4. **Start the application:**

**Option A - Use the start script (easiest):**
```bash
# Windows
start.bat

# macOS/Linux
./start.sh
```

**Option B - Manual start:**

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

5. **Open your browser:**
   Navigate to `http://localhost:3000`

6. **Configure API keys:**
   Click the Settings button in the sidebar to add your API keys.

## 📖 Usage Guide

### Indexing Your Documents

1. Go to the **Files** tab
2. Enter a path like `~/Documents/notes` or `/path/to/your/files`
3. **Select a filter preset:**
   - **Auto-detect**: Automatically detects project type (recommended)
   - **Code Project**: Ignores node_modules, venv, .git, etc.
   - **Notes & Documents**: Less strict, allows larger files
   - **Research & PDFs**: Includes PDFs, supports very large files
   - **No Filter**: Dangerous - indexes everything!
4. Click **Preview** to see what will be indexed
5. Click **Index Files** to start indexing

The system will automatically:
- Skip dependency folders (node_modules, venv, lib, etc.)
- Block sensitive files (.env, credentials, API keys)
- Detect and skip auto-generated/minified code
- Filter out binary and non-text files

## 🛡️ Smart Filtering

Knowledge AI includes intelligent file filtering to protect your sensitive data and avoid indexing useless files.

### What Gets Automatically Ignored

**Directories:**
- Version control: `.git`, `.svn`, `.hg`
- Dependencies: `node_modules`, `venv`, `vendor`, `lib`, `packages`
- Build outputs: `dist`, `build`, `out`, `target`
- IDE files: `.idea`, `.vscode`, `.vs`
- Caches: `.cache`, `.next`, `.nuxt`, `__pycache__`

**Files:**
- Lock files: `package-lock.json`, `yarn.lock`, `poetry.lock`
- Minified code: `*.min.js`, `*.min.css`, `*.bundle.js`
- Binary files: `*.exe`, `*.dll`, `*.so`, `*.pyc`
- Media: images, audio, video, fonts

**Sensitive Files (ALWAYS blocked):**
- Environment: `.env`, `.env.*`, `*.env`
- Credentials: `credentials.json`, `*secret*`, `*_key*`
- SSH/Certificates: `*.pem`, `*.key`, `id_rsa`
- Cloud configs: AWS, GCP, Azure credential files

### Custom Ignore Patterns

Create a `.knowledgeignore` file in any directory:

```gitignore
# Ignore test files
*_test.py
*.spec.js

# Ignore specific folders
drafts/
archive/

# Ignore by pattern
temp_*
*.backup
```

### Content-Based Filtering

The filter also scans file contents for:
- API keys and tokens (OpenAI, GitHub, AWS, etc.)
- Private keys and certificates
- Password patterns
- Auto-generated code markers

### Searching Your Knowledge

1. Go to the **Search** tab
2. Enter a natural language query like "machine learning optimization techniques"
3. Results are ranked by semantic similarity, not just keyword matching

### Chatting with Your Documents

1. Go to the **Chat** tab
2. Ask questions like:
   - "What did my notes say about project deadlines?"
   - "Summarize my research on neural networks"
   - "Explain the main concepts from my Python tutorials"
3. The AI will search your indexed documents and provide contextual answers

### Using the Tutor

1. Go to the **Tutor** tab
2. Select a mode:
   - **Quiz Me**: Test your understanding
   - **Explain**: Get clear explanations
   - **Flashcards**: Generate study cards
   - **Study Guide**: Create comprehensive guides
3. Optionally enter a topic to focus on
4. Click **Generate Learning Content**

## ⚙️ Configuration

Knowledge AI defaults to **local-first operation** with Ollama. No API keys required!

### Option 1: Local-First with Ollama (Default) 🏠

**100% private, offline operation - your data never leaves your computer!**

The startup script will automatically:
1. Check if Ollama is installed
2. Start Ollama if it's not running
3. Guide you to install models based on your hardware

**Install Ollama:**
```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows - download from https://ollama.com/download
```

**Model Selection (based on your hardware):**

The app detects your system's RAM and GPU to recommend the best models. In Settings, you'll see personalized recommendations like:

| Your Hardware | Recommended Chat Model | Size |
|---------------|----------------------|------|
| 4GB RAM | llama3.2:1b | ~1.3GB |
| 8GB RAM | llama3.2 | ~4.7GB |
| 16GB+ RAM | gemma2:9b or mistral | ~5GB |
| 64GB+ RAM | llama3.1:70b | ~40GB |

**Embedding model (always required for search):**
```bash
ollama pull nomic-embed-text   # ~300MB, works on any hardware
```

**Why Local?**
- 🔒 Maximum privacy - no data leaves your device
- 💰 Free after download - no API costs
- ⚡ No internet required
- 🎛️ Full control over your AI

---

### Option 2: OpenRouter (Cloud Alternative) �

**Access 200+ models with a single API key!**

1. Sign up at [OpenRouter](https://openrouter.ai)
2. Get your API key
3. Launch Knowledge AI and click Settings
4. Enter your OpenRouter API key
5. Change providers from Ollama to OpenRouter

**Popular Models Available:**
- **Chat**: Claude Sonnet 4, GPT-4o, Gemini 2.0 Flash (Free!), Llama 3.3, and 200+ more
- **Embeddings**: OpenAI text-embedding-3-small/large

---

### Option 3: Direct Provider Keys

Configure individual providers directly:

1. Launch the app and click Settings
2. Expand "Direct Provider Keys (Optional)"
3. Enter your API keys:
   - **OpenAI**: For embeddings and GPT-4 chat ([Get API key](https://platform.openai.com/api-keys))
   - **Anthropic**: For Claude chat ([Get API key](https://console.anthropic.com/))
4. Select your preferred providers

**Note:** You can mix providers! For example: Cloud chat + local Ollama embeddings for a hybrid setup.

### Environment Variables (Optional)

You can also configure via `.env` file in the backend directory:

```env
OPENROUTER_API_KEY=sk-or-v1-...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Supported File Types

| Category | Extensions |
|----------|------------|
| Documents | .txt, .md, .pdf, .docx, .rtf |
| Code | .py, .js, .ts, .jsx, .tsx, .java, .go, .rs, .rb, .php, .c, .cpp, .h, .cs, .swift, .kt |
| Config | .json, .yaml, .yml, .toml, .xml, .ini |
| Data | .csv, .tsv |
| Office | .pptx, .xlsx |
| Notebooks | .ipynb |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │  Chat   │ │ Search  │ │  Tutor  │ │  Files  │           │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │
└───────┼──────────┼──────────┼──────────┼───────────────────┘
        │          │          │          │
        └──────────┴──────────┴──────────┘
                       │
                  HTTP/REST
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                   FastAPI Backend                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │  Document    │ │  Embedding   │ │   AI Chat    │        │
│  │  Processor   │ │  Provider    │ │   Provider   │        │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘        │
│         │                │                │                 │
│  ┌──────┴────────────────┴────────────────┘                │
│  │              ChromaDB (Vector Store)                     │
│  └──────────────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────┘
```

## 🔒 Security

- API keys are encrypted at rest using Fernet encryption
- Configuration stored in `~/.knowledge-ai/` with secure permissions
- All data stays local (unless using cloud AI providers)

## 📝 API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/config` | Get configuration |
| POST | `/config` | Update configuration |
| POST | `/index` | Index files/folders |
| POST | `/search` | Semantic search |
| POST | `/chat` | Chat with RAG |
| POST | `/tutor` | Generate learning content |
| POST | `/organize` | Organize notes |
| GET | `/stats` | Get statistics |
| GET | `/files` | List indexed files |
| DELETE | `/index` | Clear all indexed data |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 📄 License

MIT License - feel free to use this for personal or commercial projects.

## 🙏 Acknowledgments

- [ChromaDB](https://www.trychroma.com/) - Vector database
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [React](https://react.dev/) - Frontend framework
- [Tailwind CSS](https://tailwindcss.com/) - Styling
- [Framer Motion](https://www.framer.com/motion/) - Animations

---

Built with ❤️ for knowledge management enthusiasts
