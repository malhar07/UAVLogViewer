# UAV Log Viewer - AI Chatbot Integration

An intelligent chatbot system for UAV flight log analysis, powered by advanced AI technologies including RAG (Retrieval-Augmented Generation) and specialized agent orchestration, with integrated flight data visualization.

## ✨ Key Features

### Intelligent AI Chatbot:
- **Agent Orchestration**: Smart routing to specialized agents (Flight Analysis, Safety, RAG Query) based on intent.
- **RAG-Powered Insights**: Deep contextual analysis of flight segments using a ChromaDB vector database, providing detailed answers to complex natural language queries.
- **Natural Language Interface**: Conversational AI for asking questions about flight data in plain English.

### Integrated Flight Data Visualization:
- **Interactive Charts**: Real-time, interactive charts for altitude, speed, battery voltage/current, and GPS flight path.
- **Unified Pipeline**: Single .bin file upload for both chatbot analysis and dynamic visualizations, ensuring consistent data.

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   UAV Log Viewer System                    │
├─────────────────────────────────────────────────────────────┤
│  Frontend Web Interface (Vue.js)                          │
│  ├── File Upload (.bin logs)                              │
│  ├── Visualization Tab (Charts & GPS)                     │
│  └── Chat Tab (AI Assistant)                              │
├─────────────────────────────────────────────────────────────┤
│  Unified Data Pipeline                                      │
│  ├── .bin File Processing (pymavlink)                     │
│  ├── Global Store (Vuex)                                  │
│  └── Auto Data Sync (POST /sync-flight-data)              │
├─────────────────────────────────────────────────────────────┤
│  Dual Analysis Systems                                      │
│  ├── Visualization Engine (Chart.js, Interactive Charts)  │
│  └── AI Chatbot System                                    │
├─────────────────────────────────────────────────────────────┤
│  AI Chatbot Backend                                        │
│  ├── Agent Orchestrator (Intent Classification)           │
│  ├── Specialized Agents (Flight, Safety, RAG)            │
│  ├── RAG Engine (ChromaDB Vector Storage)                 │
│  └── LLM Integration (Ollama + LangChain)                 │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Technology Stack

- **AI Framework**: LangChain (Agents, RAG)
- **Vector Database**: ChromaDB
- **Local LLM**: Ollama (e.g., phi3:mini, llama3:latest)
- **Embeddings**: HuggingFace Sentence Transformers
- **Backend**: FastAPI
- **Parsing**: pymavlink

## 🚀 How to Run the System

### 📋 Prerequisites

- **Python 3.8+**
- **Ollama** (for local LLM)
- **Git**
- **npm** (for frontend dependencies)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd UAVLogViewer
```

### 2. Install Frontend Dependencies
```bash
# In the root directory (UAVLogViewer)
npm install
```

### 3. Install Backend Dependencies
```bash
cd server
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Setup Ollama
```bash
# Install Ollama (Download from https://ollama.ai or use brew install ollama on macOS)
ollama serve # Start Ollama service in a terminal
ollama pull phi3:mini # Pull a model (in another terminal)
```

### 5. Start the Backend Server
```bash
cd server
source .venv/bin/activate
python3 api.py
```

The chatbot API will be available at `http://localhost:8000`

### 6. Start the Frontend Development Server
```bash
# In the root directory (UAVLogViewer)
npm run dev
```

The web interface will be available at `http://localhost:8082`

## 📖 Usage Guide

1. **Open the Web Application**: Navigate to `http://localhost:8082`
2. **Upload Flight Log**: Drag and drop or select a `.bin` flight log file.
3. **View Visualizations**: Switch to the "Visualization" tab to see interactive flight charts.
4. **Ask Questions**: Use the "Chat" tab to interact with the AI assistant about your flight data.
5. **Analyze Results**: Compare visual charts with AI insights for comprehensive analysis.

## 🔧 Configuration

Create a `.env` file in the server directory:

```env
# Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=phi3:mini

# ChromaDB Configuration
CHROMA_DB_PATH=./chroma_db

# Agent Configuration (Optional, adjust as needed)
DEFAULT_AGENT_CONFIDENCE_THRESHOLD=0.7
RAG_CHUNK_SIZE=1000
RAG_OVERLAP=200
```
