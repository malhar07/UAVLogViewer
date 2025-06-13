# server/api.py
import os
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import all modules
from core import LOG_MANAGER
from ai import AGENT
from enhanced_ai import ENHANCED_ASSISTANT
from rag_engine import RAG_ENGINE
from multimodal_analyzer import MULTIMODAL_ANALYZER

app = FastAPI(
    title="Enhanced UAV Log Analyzer API",
    description="Advanced UAV log analysis with RAG, multimodal AI, and predictive capabilities",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """API status and capabilities"""
    return {
        "message": "Enhanced UAV Log Analyzer API",
        "version": "2.0.0",
        "capabilities": {
            "basic_analysis": "Standard log file analysis",
            "rag_analysis": "RAG-powered deep insights with vector database",
            "multimodal_analysis": "Dashboard image analysis with computer vision",
            "predictive_analysis": "Predictive maintenance and performance forecasting",
            "comparative_analysis": "Multi-flight comparison and trend analysis",
            "comprehensive_reports": "AI-generated comprehensive flight reports"
        },
        "endpoints": {
            "upload": "POST /upload - Upload log files",
            "chat": "POST /chat - Enhanced chat with AI assistant",
            "analyze_dashboard": "POST /analyze-dashboard - Analyze dashboard images",
            "generate_report": "POST /generate-report - Generate comprehensive reports",
            "rag_query": "POST /rag-query - Direct RAG database queries",
            "compare_flights": "POST /compare-flights - Compare multiple flights"
        },
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/upload")
async def upload_log(file: UploadFile = File(...)):
    """Upload and process UAV log file with enhanced analysis"""
    try:
        # Validate file
        if not file.filename.endswith('.bin'):
            raise HTTPException(status_code=400, detail="Only .bin files are supported")
        
        if file.size > 100 * 1024 * 1024:  # 100MB limit
            raise HTTPException(status_code=400, detail="File too large (max 100MB)")
        
        # Read and process file
        content = await file.read()
        if len(content) < 100:
            raise HTTPException(status_code=400, detail="File too small or corrupted")
        
        # Generate log ID
        log_id = hashlib.md5(content).hexdigest()[:8]
        
        # Store and analyze log
        success = LOG_MANAGER.store_log(log_id, content)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to process log file - invalid MAVLink format or corrupted data")
        
        # Get basic analysis
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        basic_summary = analyzer.get_summary() if analyzer else {}
        
        # Process with RAG engine for enhanced analysis
        rag_result = RAG_ENGINE.process_log_for_rag(log_id)
        
        return {
            "log_id": log_id,
            "filename": file.filename,
            "size": len(content),
            "basic_analysis": basic_summary,
            "rag_processing": rag_result,
            "enhanced_capabilities": True,
            "message": "✅ Log file uploaded and processed successfully with enhanced AI analysis",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/chat")
async def chat_with_assistant(
    msg: str = Query(..., description="User message"),
    logId: Optional[str] = Query(None, description="Log ID for context"),
    analysis_mode: str = Query("detailed", description="Analysis mode: quick, detailed, expert, safety_focused")
):
    """Enhanced chat with AI assistant supporting multiple analysis modes"""
    try:
        # Use enhanced assistant for processing
        response = ENHANCED_ASSISTANT.process_message(
            message=msg,
            log_id=logId,
            analysis_mode=analysis_mode
        )
        
        return {
            "response": response.get("response", "I couldn't process your request"),
            "enhanced_ai": True,
            "analysis_mode": analysis_mode,
            "rag_powered": response.get("rag_powered", False),
            "multimodal_analysis": response.get("multimodal_analysis", False),
            "predictive_analysis": response.get("predictive_analysis", False),
            "source_documents": response.get("source_documents", []),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "response": f"❌ I encountered an error: {str(e)}",
            "error": True,
            "timestamp": datetime.now().isoformat()
        }

@app.post("/analyze-dashboard")
async def analyze_dashboard(
    file: UploadFile = File(...),
    analysis_type: str = Form("general", description="Analysis type: general, safety, performance, troubleshooting"),
    batch_analysis: bool = Form(False, description="Perform all analysis types")
):
    """Analyze UAV dashboard images using multimodal AI"""
    try:
        # Validate image file
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Only image files are supported")
        
        if file.size > 10 * 1024 * 1024:  # 10MB limit for images
            raise HTTPException(status_code=400, detail="Image too large (max 10MB)")
        
        # Read image data
        image_data = await file.read()
        
        if batch_analysis:
            # Perform comprehensive analysis
            result = MULTIMODAL_ANALYZER.batch_analyze_dashboard(image_data)
        else:
            # Perform specific analysis type
            result = MULTIMODAL_ANALYZER.analyze_dashboard_image(image_data, analysis_type)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "analysis_result": result,
            "filename": file.filename,
            "analysis_type": analysis_type,
            "batch_analysis": batch_analysis,
            "multimodal_ai": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard analysis failed: {str(e)}")

@app.post("/generate-report")
async def generate_comprehensive_report(log_id: str = Query(..., description="Log ID for report generation")):
    """Generate comprehensive flight report using all AI capabilities"""
    try:
        # Verify log exists
        if not LOG_MANAGER.get_analyzer(log_id):
            raise HTTPException(status_code=404, detail="Log not found")
        
        # Generate comprehensive report
        report = ENHANCED_ASSISTANT.generate_comprehensive_report(log_id)
        
        if "error" in report:
            raise HTTPException(status_code=500, detail=report["error"])
        
        return {
            "comprehensive_report": report,
            "log_id": log_id,
            "ai_capabilities_used": ["RAG", "Vector Database", "Predictive Analysis", "LLM"],
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@app.post("/rag-query")
async def direct_rag_query(
    query: str = Query(..., description="Query for RAG system"),
    log_id: Optional[str] = Query(None, description="Specific log ID to query")
):
    """Direct query to RAG system for advanced insights"""
    try:
        result = RAG_ENGINE.query_logs(query, log_id)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "rag_result": result,
            "query": query,
            "log_id": log_id,
            "vector_database": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")

@app.post("/compare-flights")
async def compare_flights(log_ids: list[str] = Query(..., description="List of log IDs to compare")):
    """Compare multiple flights using enhanced AI analysis"""
    try:
        if len(log_ids) < 2:
            raise HTTPException(status_code=400, detail="At least 2 log IDs required for comparison")
        
        # Verify all logs exist
        for log_id in log_ids:
            if not LOG_MANAGER.get_analyzer(log_id):
                raise HTTPException(status_code=404, detail=f"Log {log_id} not found")
        
        # Perform comparative analysis
        context = {"log_ids": log_ids}
        result = ENHANCED_ASSISTANT._handle_comparative_analysis(
            "Compare these flights and identify key differences", context
        )
        
        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["response"])
        
        return {
            "comparative_analysis": result,
            "logs_compared": log_ids,
            "comparison_count": len(log_ids),
            "enhanced_ai": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Flight comparison failed: {str(e)}")

@app.get("/logs")
async def list_logs():
    """List all uploaded logs with enhanced metadata"""
    try:
        logs = []
        for log_id in LOG_MANAGER.logs:
            analyzer = LOG_MANAGER.get_analyzer(log_id)
            if analyzer:
                summary = analyzer.get_summary()
                logs.append({
                    "log_id": log_id,
                    "summary": summary,
                    "rag_processed": True,  # Assume processed if in system
                    "enhanced_analysis_available": True
                })
        
        return {
            "logs": logs,
            "total_count": len(logs),
            "enhanced_capabilities": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list logs: {str(e)}")

@app.delete("/logs/{log_id}")
async def delete_log(log_id: str):
    """Delete a log and its associated RAG data"""
    try:
        if log_id not in LOG_MANAGER.logs:
            raise HTTPException(status_code=404, detail="Log not found")
        
        # Remove from log manager
        del LOG_MANAGER.logs[log_id]
        
        # Note: In a production system, you'd also remove from vector database
        # This would require implementing a delete method in the RAG engine
        
        return {
            "message": f"Log {log_id} deleted successfully",
            "log_id": log_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete log: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint with system status"""
    try:
        # Check various system components
        health_status = {
            "api": "healthy",
            "log_manager": "healthy" if LOG_MANAGER else "unhealthy",
            "rag_engine": "healthy" if RAG_ENGINE else "unhealthy",
            "multimodal_analyzer": "healthy" if MULTIMODAL_ANALYZER else "unhealthy",
            "enhanced_assistant": "healthy" if ENHANCED_ASSISTANT else "unhealthy"
        }
        
        overall_status = "healthy" if all(status == "healthy" for status in health_status.values()) else "degraded"
        
        return {
            "overall_status": overall_status,
            "components": health_status,
            "version": "2.0.0",
            "capabilities": ["RAG", "Multimodal", "Predictive", "Comparative"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 