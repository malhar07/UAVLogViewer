from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import requests
import json
import os
import uuid
from log_tools import log_tools

def get_relevant_log_data(log_id: str, question: str) -> str:
    """Automatically fetch relevant log data based on the user's question"""
    question_lower = question.lower()
    
    try:
        # Get basic metadata first
        metadata = log_tools.get_log_metadata(log_id)
        if "error" in metadata:
            return f"Error accessing log {log_id}: {metadata['error']}"
        
        relevant_data = []
        
        # Add basic log info
        relevant_data.append(f"Log Duration: {metadata.get('duration_seconds', 'Unknown')} seconds")
        relevant_data.append(f"File Size: {metadata.get('file_size_mb', 'Unknown')} MB")
        
        # Determine what data to fetch based on question keywords
        if any(word in question_lower for word in ['altitude', 'height', 'high', 'low', 'climb', 'descend']):
            # Fetch GPS and altitude data
            gps_data = log_tools.get_messages(log_id, "GPS", limit=10)
            if gps_data and "messages" in gps_data:
                altitudes = [msg.get("alt", 0) for msg in gps_data["messages"] if "alt" in msg]
                if altitudes:
                    relevant_data.append(f"Altitude data: Min={min(altitudes):.1f}m, Max={max(altitudes):.1f}m, Avg={sum(altitudes)/len(altitudes):.1f}m")
        
        if any(word in question_lower for word in ['battery', 'power', 'voltage', 'current']):
            # Fetch battery data
            batt_data = log_tools.get_messages(log_id, "BATT", limit=10)
            if batt_data and "messages" in batt_data:
                voltages = [msg.get("voltage", 0) for msg in batt_data["messages"] if "voltage" in msg]
                currents = [msg.get("current", 0) for msg in batt_data["messages"] if "current" in msg]
                if voltages:
                    relevant_data.append(f"Battery: Voltage={voltages[-1]:.1f}V, Current={currents[-1] if currents else 0:.1f}A")
        
        if any(word in question_lower for word in ['attitude', 'roll', 'pitch', 'yaw', 'orientation']):
            # Fetch attitude data
            att_data = log_tools.get_messages(log_id, "ATT", limit=5)
            if att_data and "messages" in att_data:
                latest_att = att_data["messages"][-1] if att_data["messages"] else {}
                if latest_att:
                    relevant_data.append(f"Latest Attitude: Roll={latest_att.get('roll', 0):.2f}°, Pitch={latest_att.get('pitch', 0):.2f}°, Yaw={latest_att.get('yaw', 0):.2f}°")
        
        if any(word in question_lower for word in ['location', 'position', 'coordinates', 'gps', 'latitude', 'longitude']):
            # Fetch GPS coordinates
            gps_data = log_tools.get_messages(log_id, "GPS", limit=5)
            if gps_data and "messages" in gps_data:
                latest_gps = gps_data["messages"][-1] if gps_data["messages"] else {}
                if latest_gps:
                    relevant_data.append(f"Latest Position: Lat={latest_gps.get('lat', 0):.6f}, Lng={latest_gps.get('lng', 0):.6f}")
        
        if any(word in question_lower for word in ['overview', 'summary', 'general', 'about']):
            # Provide general overview
            relevant_data.append(f"Available message types: {', '.join(metadata.get('message_types', [])[:5])}")
            relevant_data.append(f"Total messages: {metadata.get('total_messages', 'Unknown')}")
        
        return "\n".join(relevant_data) if relevant_data else "No specific data found for this question."
        
    except Exception as e:
        return f"Error fetching log data: {str(e)}"

app = FastAPI(title="UAV Log Viewer Chatbot API")

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    log_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    log_context: Optional[Dict[str, Any]] = None

class UploadResponse(BaseModel):
    log_id: str
    message: str

# Ollama API configuration
OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "phi3:mini"

def query_ollama_with_tools(message: str, log_context: Optional[str] = None) -> str:
    """Query Ollama model with automatic data fetching based on user question"""
    try:
        # If we have a log context, automatically fetch relevant data
        context_data = ""
        if log_context:
            context_data = get_relevant_log_data(log_context, message)
        
        # Create system prompt for direct answers
        system_prompt = """You are a UAV (drone) log analysis assistant. Answer questions directly based on the provided data.

Key instructions:
- Give direct, concise answers 
- Don't show code or tool calls
- If analyzing log data, use the specific data provided
- For general UAV questions, use your knowledge
- Be helpful and accurate"""

        full_prompt = f"{system_prompt}\n"
        if context_data:
            full_prompt += f"\nLog data for analysis:\n{context_data}\n"
        full_prompt += f"\nUser question: {message}\n\nAnswer:"
        
        payload = {
            "model": MODEL_NAME,
            "prompt": full_prompt,
            "stream": True,
            "options": {
                "temperature": 0.7,
                "num_predict": 150,
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

@app.post("/upload", response_model=UploadResponse)
async def upload_log_file(file: UploadFile = File(...)):
    """Upload a UAV log file for analysis"""
    if not file.filename.endswith(('.bin', '.tlog')):
        raise HTTPException(status_code=400, detail="Only .bin and .tlog files are supported")
    
    # Create uploads directory if it doesn't exist
    os.makedirs("uploads", exist_ok=True)
    
    # Generate unique log ID and save file
    log_id = str(uuid.uuid4())[:8]
    file_path = f"uploads/{log_id}_{file.filename}"
    
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Register the log file with our analysis tools
        result = log_tools.register_log_file(log_id, file_path)
        
        if result["success"]:
            return UploadResponse(
                log_id=log_id,
                message=f"Log file uploaded successfully. Log ID: {log_id}"
            )
        else:
            raise HTTPException(status_code=500, detail=f"Failed to process log file: {result['error']}")
            
    except Exception as e:
        # Clean up file if registration failed
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/logs")
async def get_available_logs():
    """Get list of available log files"""
    from log_tools import get_available_logs
    result = get_available_logs()
    return json.loads(result)

@app.get("/logs/{log_id}/metadata")
async def get_log_metadata_endpoint(log_id: str):
    """Get metadata for a specific log file"""
    from log_tools import get_log_metadata
    result = get_log_metadata(log_id)
    return json.loads(result)

@app.post("/chat", response_model=ChatResponse)
async def chat_with_log(request: ChatRequest):
    """Chat endpoint that provides intelligent log analysis"""
    try:
        # Prepare the context for the LLM
        context_data = {}
        
        if request.log_id:
            # Extract relevant data based on the user's question
            log_analysis = log_tools.extract_relevant_data(request.log_id, request.message)
            
            if "error" not in log_analysis:
                context_data = log_analysis
        
        # Prepare the system prompt with real data context
        system_prompt = create_analysis_prompt(request.message, context_data)
        
        # Call Ollama with the intelligent context
        ollama_response = requests.post("http://localhost:11434/api/generate", 
            json={
                "model": "phi3:mini",
                "prompt": system_prompt,
                "stream": False,
                "options": {
                    "num_predict": 200,
                    "temperature": 0.7
                }
            },
            timeout=120
        )
        
        if ollama_response.status_code == 200:
            response_data = ollama_response.json()
            ai_response = response_data.get("response", "No response generated")
            
            return ChatResponse(
                response=ai_response,
                log_context=context_data if context_data else None
            )
        else:
            return ChatResponse(
                response="Sorry, I'm having trouble analyzing the data right now.",
                log_context=None
            )
            
    except requests.exceptions.RequestException as e:
        return ChatResponse(
            response=f"Connection error: {str(e)}",
            log_context=None
        )
    except Exception as e:
        return ChatResponse(
            response=f"Error: {str(e)}",
            log_context=None
        )

def create_analysis_prompt(user_question: str, log_data: Dict[str, Any]) -> str:
    """Create an intelligent prompt with actual log data for analysis"""
    
    if not log_data or "relevant_data" not in log_data:
        # No log data available
        base_prompt = """You are a UAV flight log analyst. The user asked: "{}"

Unfortunately, no log file data is available for analysis. Please ask the user to upload a .bin log file first to provide specific analysis.

In the meantime, you can provide general information about what could be analyzed from UAV logs.""".format(user_question)
        return base_prompt
    
    # Extract the actual data
    relevant_data = log_data["relevant_data"]
    data_analysis = log_data["data_analysis"]
    metadata = log_data["metadata"]
    
    # Build context with real data
    context_parts = [
        f"User Question: {user_question}",
        f"Log Analysis: Analyzing {metadata.get('data_source', 'unknown')} data",
        f"Flight Duration: {metadata.get('log_duration', 'unknown')} seconds",
        ""
    ]
    
    # Add relevant data sections
    for message_type, messages in relevant_data.items():
        if message_type == 'statistics':
            continue
            
        context_parts.append(f"=== {message_type} Data ===")
        
        if not messages:
            context_parts.append("No data available")
            continue
            
        # Show sample of actual data
        for i, msg in enumerate(messages[:5]):  # Limit to first 5 messages
            timestamp = msg.get('timestamp', 'unknown')
            data = msg.get('data', {})
            
            # Format data nicely
            data_str = ", ".join([f"{k}={v}" for k, v in data.items() if not k.startswith('_')])
            context_parts.append(f"  Time {timestamp:.1f}s: {data_str}")
            
        if len(messages) > 5:
            context_parts.append(f"  ... and {len(messages) - 5} more messages")
        
        context_parts.append("")
    
    # Add statistics if available
    if 'statistics' in relevant_data:
        context_parts.append("=== Statistics ===")
        stats = relevant_data['statistics']
        for msg_type, type_stats in stats.items():
            context_parts.append(f"{msg_type}:")
            for field, field_stats in type_stats.items():
                min_val = field_stats.get('min', 'N/A')
                max_val = field_stats.get('max', 'N/A')
                avg_val = field_stats.get('avg', 'N/A')
                if isinstance(avg_val, float):
                    avg_val = round(avg_val, 2)
                context_parts.append(f"  {field}: min={min_val}, max={max_val}, avg={avg_val}")
        context_parts.append("")
    
    # Create the final prompt
    system_prompt = f"""You are an expert UAV flight log analyst. Based on the ACTUAL flight data below, provide a detailed analysis.

{chr(10).join(context_parts)}

Instructions:
1. Analyze the REAL data provided above
2. Answer the user's specific question using this actual flight data
3. Provide specific numbers, values, and insights from the data
4. If asking about maximums/minimums, use the statistics section
5. Be precise and cite actual values from the data
6. If data is insufficient, explain what additional data would be needed

Provide a clear, informative response based on this real flight data:"""
    
    return system_prompt

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 