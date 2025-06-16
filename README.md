# UAV Log Viewer - AI Chatbot Integration

An intelligent chatbot system for UAV flight log analysis, powered by advanced AI technologies including RAG (Retrieval-Augmented Generation) and specialized agent orchestration.

## 🤖 Overview

This project adds a sophisticated AI chatbot capability to the UAV Log Viewer platform. The chatbot can analyze flight logs, answer questions about flight data, and provide intelligent insights using natural language processing and retrieval-augmented generation.

## ✨ Chatbot Features

### 🧠 **Intelligent Agent System**
- **Specialized Agents**: FlightAnalysisAgent, SafetyAgent, and RAGQueryAgent
- **Smart Routing**: Automatic intent classification and agent selection
- **Context Awareness**: Maintains conversation context across interactions
- **Confidence Scoring**: Provides reliability metrics for responses

### 🔍 **RAG-Powered Analysis**
- **Vector Database**: ChromaDB integration for semantic search
- **Rich Context**: 10-second flight segments with detailed descriptions
- **Source Attribution**: Tracks analysis sources and evidence
- **Deep Insights**: LangChain-powered contextual understanding

### 💬 **Natural Language Interface**
- **Conversational AI**: Ask questions about flights in plain English
- **Multi-turn Conversations**: Maintains context across multiple questions
- **Intelligent Responses**: Combines tool results with RAG context
- **Fallback Handling**: Graceful handling of unclear queries

### 🎯 **Query Types Supported**
- **Flight Analysis**: "What was the maximum altitude during this flight?"
- **Safety Assessment**: "Were there any safety issues during the flight?"
- **Performance Metrics**: "How was the battery performance?"
- **Technical Diagnostics**: "What caused the vibration spike at 5 minutes?"
- **General Knowledge**: "What is HDOP in GPS systems?"

## 🏗️ Chatbot Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Chatbot System                       │
├─────────────────────────────────────────────────────────────┤
│  Chat Interface (POST /agent-chat)                        │
│  ├── Message Processing                                   │
│  ├── Intent Classification                                │
│  └── Response Generation                                  │
├─────────────────────────────────────────────────────────────┤
│  Agent Orchestrator                                        │
│  ├── LLM-based Intent Classification                      │
│  ├── Agent Selection & Routing                            │
│  └── Response Synthesis                                   │
├─────────────────────────────────────────────────────────────┤
│  Specialized Agents                                        │
│  ├── FlightAnalysisAgent (altitude, speed, performance)   │
│  ├── SafetyAgent (risk assessment, warnings)              │
│  └── RAGQueryAgent (deep log queries)                     │
├─────────────────────────────────────────────────────────────┤
│  RAG Engine                                                │
│  ├── ChromaDB Vector Database                             │
│  ├── Flight Segment Embeddings                            │
│  ├── Semantic Search                                      │
│  └── Context Retrieval                                    │
├─────────────────────────────────────────────────────────────┤
│  LLM Integration                                           │
│  ├── Ollama Local LLM                                     │
│  ├── LangChain Framework                                  │
│  └── Prompt Engineering                                   │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Chatbot Technology Stack

- **AI Framework**: LangChain for agent orchestration
- **Vector Database**: ChromaDB for semantic search and RAG
- **Local LLM**: Ollama (phi3:mini, llama3:latest)
- **Embeddings**: HuggingFace Sentence Transformers
- **Backend Integration**: FastAPI endpoints
- **Agent System**: Custom specialized agents with tool calling
- **Context Management**: Conversation state and memory handling

## 📋 Prerequisites

- **Python 3.8+**
- **Ollama** (for local LLM)
- **Git**

## 🚀 How to Run the Chatbot

### 1. Clone the Repository
```bash
git clone <repository-url>
cd UAVLogViewer
```

### 2. Install Dependencies
```bash
cd server
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Setup Ollama
```bash
# Install Ollama (macOS)
brew install ollama

# Or download from https://ollama.ai

# Start Ollama service
ollama serve

# Pull a model (in another terminal)
ollama pull phi3:mini
# or
ollama pull llama3:latest
```

### 4. Start the Server
```bash
cd server
source .venv/bin/activate
python3 api.py
```

The chatbot API will be available at `http://localhost:8000`

### 5. API Documentation
- **Interactive API Docs**: `http://localhost:8000/docs`
- **Chatbot Endpoint**: `POST /agent-chat`

## 📖 Chatbot Usage Guide

### 1. Upload a Flight Log
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_flight_log.bin"
```

### 2. Get Log ID
```bash
curl "http://localhost:8000/logs"
```

### 3. Chat with the AI Assistant

#### Basic Flight Analysis
```bash
curl -X POST "http://localhost:8000/agent-chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What was the maximum altitude during this flight?",
    "log_id": "your_log_id"
  }'
```

#### Safety Assessment
```bash
curl -X POST "http://localhost:8000/agent-chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Were there any safety issues during the flight?",
    "log_id": "your_log_id"
  }'
```

#### Performance Analysis
```bash
curl -X POST "http://localhost:8000/agent-chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How was the battery performance throughout the flight?",
    "log_id": "your_log_id"
  }'
```

#### Technical Diagnostics
```bash
curl -X POST "http://localhost:8000/agent-chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain the vibration levels during takeoff",
    "log_id": "your_log_id"
  }'
```

## 📊 Chatbot API Endpoints

### Primary Chatbot Endpoint
- `POST /agent-chat` - Main chatbot interface for AI-powered flight analysis

### Request Format
```json
{
  "message": "Your question about the flight",
  "log_id": "flight_log_identifier"
}
```

### Response Format
```json
{
  "response": "AI-generated response",
  "agent_used": "FlightAnalysisAgent",
  "confidence": 0.95,
  "sources": ["flight_segment_1", "flight_segment_2"],
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Supporting Endpoints
- `POST /upload` - Upload flight log for analysis
- `GET /logs` - List available logs for chatbot queries

## 🎯 Chatbot Use Cases

### 🏢 **Commercial Operations**
- **Fleet Monitoring**: "How did aircraft N123 perform compared to yesterday?"
- **Safety Compliance**: "Were there any regulatory violations during this flight?"
- **Maintenance Planning**: "What maintenance issues does this flight data suggest?"
- **Pilot Training**: "What could the pilot have done better during landing?"

### 🔬 **Research & Development**
- **Data Analysis**: "What patterns do you see in the GPS accuracy data?"
- **Algorithm Testing**: "How did the new flight controller perform?"
- **Performance Metrics**: "Compare the efficiency of this flight to optimal parameters"
- **Academic Research**: "Explain the correlation between vibration and motor performance"

### 🛠️ **Hobbyist & Developers**
- **Flight Improvement**: "What caused the altitude fluctuations at 3 minutes?"
- **Troubleshooting**: "Why did the battery drain faster than expected?"
- **Learning**: "Explain what HDOP means and why it matters"
- **Performance Optimization**: "How can I improve my flight efficiency?"

## 🔧 Chatbot Configuration

### Environment Variables
Create a `.env` file in the server directory:

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=phi3:mini

# ChromaDB Configuration
CHROMA_DB_PATH=./chroma_db

# Agent Configuration
DEFAULT_AGENT_CONFIDENCE_THRESHOLD=0.7
RAG_CHUNK_SIZE=1000
RAG_OVERLAP=200
```

### Supported Models
- **phi3:mini**: Lightweight and efficient, currently used (2.2 GB)
- **llama3:latest**: More capable but larger, available option (4.7 GB)
- **mistral**: Fast responses, good for quick queries
- **codellama**: Better for technical/diagnostic queries

### Agent Specializations
- **FlightAnalysisAgent**: Altitude, speed, performance metrics
- **SafetyAgent**: Risk assessment, warnings, compliance
- **RAGQueryAgent**: Deep log analysis, complex queries

## 🧠 How the Chatbot Works

### 1. Intent Classification
When you ask a question, the system uses LLM-based classification to determine:
- **TOOL_CALL**: Needs specific flight data (altitude, battery, etc.)
- **LOG_QUERY**: Requires deep RAG analysis of flight segments
- **GENERAL_ANSWER**: General knowledge about UAVs/aviation

### 2. Agent Selection
Based on the intent, the orchestrator selects the appropriate agent:
- **FlightAnalysisAgent**: For performance and metrics questions
- **SafetyAgent**: For safety and risk-related queries
- **RAGQueryAgent**: For complex analysis requiring flight context

### 3. Response Generation
The selected agent:
- Executes relevant tools to get flight data
- Searches the vector database for relevant context
- Combines results with LLM reasoning
- Provides a comprehensive, source-attributed response

### 4. Confidence Scoring
Each response includes a confidence score to help you understand the reliability of the analysis.

## 🔮 Future Enhancements

- [ ] Multi-turn conversation memory
- [ ] Voice interface integration
- [ ] Custom agent training for specific aircraft types
- [ ] Real-time flight monitoring chat
- [ ] Integration with flight planning software
- [ ] Mobile app chatbot interface

---

**Built with ❤️ for the UAV community**
