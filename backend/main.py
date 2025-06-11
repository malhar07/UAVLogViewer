from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import json

app = FastAPI(title="UAV Log Viewer Chatbot API")

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    status: str

# Ollama API configuration
OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "phi3:mini"

def query_ollama(message: str) -> str:
    """Query Ollama Llama3 model with the user message using streaming"""
    try:
        payload = {
            "model": MODEL_NAME,
            "prompt": f"You are a UAV assistant. Be concise. Question: {message}",
            "stream": True,
            "options": {
                "temperature": 0.7,
                "num_predict": 150,  # Limit response length for speed
                "top_p": 0.9,
                "repeat_penalty": 1.1
            }
        }
        
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=120,
            stream=True
        )
        
        if response.status_code == 200:
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        if 'response' in chunk:
                            full_response += chunk['response']
                        if chunk.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
            
            return full_response if full_response else "Sorry, I couldn't generate a response."
        else:
            return f"Error: Ollama service returned status {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        return "Error: Cannot connect to Ollama. Please make sure Ollama is running on localhost:11434"
    except requests.exceptions.Timeout:
        return "Error: Request to Ollama timed out. Please try again."
    except Exception as e:
        return f"Error: {str(e)}"

@app.get("/")
async def root():
    return {"message": "UAV Log Viewer Chatbot API is running!"}

@app.get("/health")
async def health_check():
    """Check if Ollama is accessible"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            has_llama3 = any(MODEL_NAME in model.get("name", "") for model in models)
            return {
                "ollama_status": "connected",
                "llama3_available": has_llama3,
                "models": [model.get("name") for model in models]
            }
        else:
            return {"ollama_status": "error", "message": "Cannot access Ollama"}
    except Exception as e:
        return {"ollama_status": "disconnected", "error": str(e)}

@app.post("/chat", response_model=ChatResponse)
async def chat_with_ollama(chat_message: ChatMessage):
    """Send user message to Ollama and return response"""
    if not chat_message.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Query Ollama
    ollama_response = query_ollama(chat_message.message)
    
    return ChatResponse(
        response=ollama_response,
        status="success"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 