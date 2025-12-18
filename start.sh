#!/bin/bash

# Knowledge AI Startup Script
# This script starts both the backend and frontend services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║   🧠 Knowledge AI - Personal Knowledge Management         ║"
echo "║      Local-First AI for Your Documents                    ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ============================================================
# Check Prerequisites
# ============================================================

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo ""
    echo "Please install Python 3.10-3.13:"
    echo "  macOS:  brew install python@3.12"
    echo "  Ubuntu: sudo apt install python3 python3-venv"
    echo "  Other:  https://www.python.org/downloads/"
    echo ""
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}Found $PYTHON_VERSION${NC}"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    echo ""
    echo "Please install Node.js 18 or higher:"
    echo "  macOS:  brew install node"
    echo "  Ubuntu: sudo apt install nodejs npm"
    echo "  Other:  https://nodejs.org/"
    echo ""
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "${GREEN}Found Node.js $NODE_VERSION${NC}"

# ============================================================
# Check Ollama (Local AI)
# ============================================================

echo ""
echo -e "${YELLOW}Checking Ollama (Local AI)...${NC}"

SKIP_OLLAMA=false

if ! command -v ollama &> /dev/null; then
    echo ""
    echo -e "${YELLOW}NOTE: Ollama is not installed.${NC}"
    echo ""
    echo "For 100% private, local AI operation, install Ollama:"
    echo "  curl -fsSL https://ollama.com/install.sh | sh"
    echo "  Or download: https://ollama.com/download"
    echo ""
    echo "Without Ollama, you'll need a cloud API key (OpenRouter, OpenAI, etc.)"
    echo "You can configure this in Settings after the app starts."
    echo ""
    SKIP_OLLAMA=true
fi

if [ "$SKIP_OLLAMA" = false ]; then
    echo -e "${GREEN}Found Ollama${NC}"
    
    # Check if Ollama is running
    if ! curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
        echo -e "${YELLOW}Starting Ollama service...${NC}"
        ollama serve &> /dev/null &
        sleep 3
        
        if ! curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
            echo -e "${YELLOW}WARNING: Could not start Ollama service automatically.${NC}"
            echo "Please start Ollama manually (run 'ollama serve' in another terminal)."
            SKIP_OLLAMA=true
        fi
    fi
    
    if [ "$SKIP_OLLAMA" = false ]; then
        echo -e "${GREEN}Ollama is running${NC}"
        
        # Check if ANY models are installed
        echo ""
        echo -e "${YELLOW}Checking for installed AI models...${NC}"
        
        MODEL_COUNT=$(ollama list 2>/dev/null | tail -n +2 | wc -l | tr -d ' ')
        
        if [ "$MODEL_COUNT" -eq 0 ]; then
            echo ""
            echo "No AI models are installed in Ollama."
            echo ""
            echo "The app will detect your hardware and recommend the best models."
            echo "After the app starts, go to Settings to see recommendations"
            echo "based on your system's RAM and GPU."
            echo ""
            echo "Or install models manually:"
            echo "  ollama pull llama3.2:1b     (small, fast, any hardware)"
            echo "  ollama pull llama3.2        (balanced, needs 8GB+ RAM)"
            echo "  ollama pull nomic-embed-text (required for search)"
            echo ""
            read -p "Press Enter to continue..."
        else
            echo -e "${GREEN}Found $MODEL_COUNT installed model(s)${NC}"
            
            # Check specifically for an embedding model
            if ! ollama list 2>/dev/null | grep -qE "nomic-embed-text|mxbai-embed|all-minilm"; then
                echo ""
                echo -e "${YELLOW}NOTE: No embedding model found.${NC}"
                echo "An embedding model is required for document search."
                echo ""
                echo "Recommended: ollama pull nomic-embed-text"
                echo ""
                echo "The app will prompt you to configure this in Settings."
                echo ""
            fi
        fi
    fi
fi

# ============================================================
# Function to cleanup on exit
# ============================================================

cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# ============================================================
# Setup Backend
# ============================================================

echo ""
echo -e "${GREEN}Setting up backend...${NC}"
cd "$BACKEND_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -q -r requirements.txt

# Start backend
echo -e "${GREEN}Starting backend server on http://localhost:8000${NC}"
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# ============================================================
# Setup Frontend
# ============================================================

echo -e "${GREEN}Setting up frontend...${NC}"
cd "$FRONTEND_DIR"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing Node.js dependencies...${NC}"
    npm install
fi

# Wait for backend to be ready
echo -e "${YELLOW}Waiting for backend to start...${NC}"
sleep 3

# Start frontend
echo -e "${GREEN}Starting frontend server on http://localhost:3000${NC}"
npm run dev &
FRONTEND_PID=$!

# ============================================================
# Done!
# ============================================================

echo -e "\n${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🚀 Knowledge AI is running!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e ""
echo -e "   Frontend:  ${BLUE}http://localhost:3000${NC}"
echo -e "   Backend:   ${BLUE}http://localhost:8000${NC}"
echo -e "   API Docs:  ${BLUE}http://localhost:8000/docs${NC}"
echo -e ""
if [ "$SKIP_OLLAMA" = false ]; then
    echo -e "   Using ${GREEN}LOCAL AI (Ollama)${NC} - your data stays private!"
else
    echo -e "   Configure your AI provider in ${YELLOW}Settings${NC}."
fi
echo -e ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo -e ""

# Wait for processes
wait
