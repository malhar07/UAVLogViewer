import os
import tempfile
import shutil
import logging
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from log_tools import LogTools
from function_calling import FunctionCallingManager
from llm_coordinator import LLMCoordinator, IterativeAnalysisCoordinator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="UAV Log Analysis Chatbot", description="Intelligent UAV flight log analysis with function calling")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the analysis system
log_tools = LogTools()
function_manager = FunctionCallingManager(log_tools)
llm_coordinator = LLMCoordinator(function_manager)
iterative_coordinator = IterativeAnalysisCoordinator(llm_coordinator)

# Keep track of uploaded logs
active_log_sessions: Dict[str, str] = {}

class ChatRequest(BaseModel):
    message: str
    log_id: str = None

class ChatResponse(BaseModel):
    response: str
    log_id: str = None
    success: bool = True
    tool_info: Dict[str, Any] = None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "UAV Log Analysis Chatbot"}

@app.post("/upload")
async def upload_log(file: UploadFile = File(...)):
    """Upload and register a UAV log file"""
    try:
        # Validate file
        if not file.filename.endswith(('.bin', '.BIN')):
            raise HTTPException(status_code=400, detail="Only .bin files are supported")
        
        if file.size > 100 * 1024 * 1024:  # 100MB limit
            raise HTTPException(status_code=400, detail="File too large (max 100MB)")
        
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix='_' + file.filename)
        
        try:
            # Save uploaded file to temporary location
            with os.fdopen(temp_fd, 'wb') as temp_file:
                shutil.copyfileobj(file.file, temp_file)
            
            # Register with log tools
            log_id = log_tools.register_log(temp_path)
            
            # Store session info
            session_id = str(uuid.uuid4())
            active_log_sessions[session_id] = log_id
            
            # Get basic metadata for confirmation
            metadata = log_tools.get_log_metadata(log_id)
            
            logger.info(f"Successfully uploaded and registered log: {file.filename} -> {log_id}")
            
            return {
                "message": f"Successfully uploaded {file.filename}",
                "log_id": log_id,
                "session_id": session_id,
                "metadata": metadata,
                "success": True
            }
            
        except Exception as e:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except:
                pass
            raise e
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat_with_log(request: ChatRequest):
    """Process user questions using intelligent function calling"""
    try:
        if not request.log_id:
            return ChatResponse(
                response="Please upload a flight log first before asking questions.",
                success=False
            )
        
        # Validate log exists
        if request.log_id not in log_tools.active_logs:
            return ChatResponse(
                response="Log not found. Please upload a flight log first.",
                success=False
            )
        
        logger.info(f"Processing question: '{request.message}' for log {request.log_id}")
        
        # Determine if this is a complex question that needs iterative analysis
        question_lower = request.message.lower()
        is_complex = any(word in question_lower for word in [
            'comprehensive', 'complete', 'overall', 'detailed', 'full analysis',
            'everything', 'all aspects', 'thorough'
        ])
        
        if is_complex:
            # Use iterative analysis for complex questions
            logger.info("Using iterative analysis for complex question")
            result = iterative_coordinator.process_complex_question(request.message, request.log_id)
        else:
            # Use standard single-pass analysis
            result = llm_coordinator.process_user_question(request.message, request.log_id)
        
        # Extract response and metadata
        answer = result.get("answer", "I couldn't process your question. Please try again.")
        tool_info = {
            "approach": "iterative" if is_complex else "single_pass",
            "success": result.get("success", False)
        }
        
        if "tool_plan" in result:
            tool_info["tools_used"] = [tool.get("function") for tool in result["tool_plan"]]
        
        if "iterations" in result:
            tool_info["iterations"] = result["total_iterations"]
        
        logger.info(f"Generated response for log {request.log_id}")
        
        return ChatResponse(
            response=answer,
            log_id=request.log_id,
            success=result.get("success", False),
            tool_info=tool_info
        )
        
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        return ChatResponse(
            response=f"I encountered an error processing your question: {str(e)}",
            log_id=request.log_id,
            success=False
        )

@app.get("/logs/{log_id}/metadata")
async def get_log_metadata(log_id: str):
    """Get metadata for a specific log"""
    try:
        metadata = log_tools.get_log_metadata(log_id)
        if "error" in metadata:
            raise HTTPException(status_code=404, detail="Log not found")
        return metadata
    except Exception as e:
        logger.error(f"Failed to get metadata for {log_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/{log_id}/summary")
async def get_log_summary(log_id: str):
    """Get a comprehensive summary of the log using function calling"""
    try:
        result = function_manager.execute_function("get_log_summary", log_id=log_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Failed to get summary for {log_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/logs/{log_id}/analyze")
async def analyze_log_aspect(log_id: str, analysis_type: str = "health"):
    """Perform specific analysis on a log"""
    try:
        analysis_map = {
            "health": "check_system_health",
            "battery": "analyze_battery_performance", 
            "flight_path": "analyze_flight_path",
            "attitude": "analyze_attitude_control",
            "events": "detect_flight_events",
            "gps": "analyze_gps_quality",
            "performance": "get_performance_metrics",
            "correlations": "analyze_correlations"
        }
        
        function_name = analysis_map.get(analysis_type)
        if not function_name:
            raise HTTPException(status_code=400, detail=f"Unknown analysis type: {analysis_type}")
        
        result = function_manager.execute_function(function_name, log_id=log_id)
        return result
        
    except Exception as e:
        logger.error(f"Analysis failed for {log_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools")
async def get_available_tools():
    """Get list of available analysis tools"""
    return {
        "tools": function_manager.get_function_definitions(),
        "description": "Available UAV log analysis tools with intelligent coordination"
    }

@app.delete("/logs/{log_id}")
async def cleanup_log(log_id: str):
    """Clean up a log session"""
    try:
        success = log_tools.cleanup_log(log_id)
        
        # Remove from active sessions
        sessions_to_remove = [k for k, v in active_log_sessions.items() if v == log_id]
        for session in sessions_to_remove:
            del active_log_sessions[session]
        
        return {"success": success, "message": f"Log {log_id} cleaned up"}
    except Exception as e:
        logger.error(f"Cleanup failed for {log_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_system_status():
    """Get system status and statistics"""
    try:
        # Check Ollama connection
        ollama_status = "unknown"
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            ollama_status = "connected" if response.status_code == 200 else "error"
        except:
            ollama_status = "disconnected"
        
        return {
            "active_logs": len(log_tools.active_logs),
            "active_sessions": len(active_log_sessions),
            "ollama_status": ollama_status,
            "available_tools": len(function_manager.get_function_definitions()),
            "system": "UAV Log Analysis with Intelligent Function Calling"
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting UAV Log Analysis Chatbot with Function Calling...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 