# server/api.py
import os
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import all modules
from core import LOG_MANAGER
from ai import ORCHESTRATOR  # Import the new orchestrator
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
            "intelligent_agents": "Intelligent agent orchestration with specialized analysis",
            "rag_analysis": "RAG-powered deep insights with vector database",
            "multimodal_analysis": "Dashboard image analysis with computer vision",
            "predictive_analysis": "Predictive maintenance and performance forecasting",
            "comparative_analysis": "Multi-flight comparison and trend analysis",
            "comprehensive_reports": "AI-generated comprehensive flight reports"
        },
        "endpoints": {
            "upload": "POST /upload - Upload log files",
            "chat": "POST /chat - Enhanced chat with AI assistant",
            "agent_chat": "POST /agent-chat - Chat with intelligent agent orchestration",
            "analyze_dashboard": "POST /analyze-dashboard - Analyze dashboard images",
            "generate_report": "POST /generate-report - Generate comprehensive reports",
            "rag_query": "POST /rag-query - Direct RAG database queries",
            "compare_flights": "POST /compare-flights - Compare multiple flights",
            "structured_analysis": "POST /analyze-structured - Get structured analysis results",
            "performance_metrics": "GET /logs/{id}/performance - Get performance metrics",
            "safety_assessment": "GET /logs/{id}/safety - Get safety assessment",
            "flight_quality": "GET /logs/{id}/quality - Get flight quality score"
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

@app.get("/logs/{log_id}/altitude_data")
async def get_altitude_data(log_id: str):
    """Get time-series altitude data for graphing"""
    try:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        if not analyzer:
            raise HTTPException(status_code=404, detail="Log not found")
        
        altitude_data = analyzer.get_altitude_series()
        
        return {
            "log_id": log_id,
            "data_type": "altitude",
            "altitude_series": altitude_data,
            "data_points": len(altitude_data),
            "units": "meters",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get altitude data: {str(e)}")

@app.get("/logs/{log_id}/speed_data")
async def get_speed_data(log_id: str):
    """Get time-series speed data for graphing"""
    try:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        if not analyzer:
            raise HTTPException(status_code=404, detail="Log not found")
        
        speed_data = analyzer.get_speed_series()
        
        return {
            "log_id": log_id,
            "data_type": "speed",
            "speed_series": speed_data,
            "data_points": len(speed_data),
            "units": "meters_per_second",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get speed data: {str(e)}")

@app.get("/logs/{log_id}/gps_data")
async def get_gps_data(log_id: str):
    """Get time-series GPS coordinate data for mapping"""
    try:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        if not analyzer:
            raise HTTPException(status_code=404, detail="Log not found")
        
        gps_data = analyzer.get_gps_coords_series()
        
        return {
            "log_id": log_id,
            "data_type": "gps_coordinates",
            "gps_series": gps_data,
            "data_points": len(gps_data),
            "coordinate_system": "WGS84",
            "units": {
                "latitude": "decimal_degrees",
                "longitude": "decimal_degrees", 
                "altitude": "meters",
                "speed": "meters_per_second"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get GPS data: {str(e)}")

@app.get("/logs/{log_id}/battery_data")
async def get_battery_data(log_id: str):
    """Get time-series battery data for power analysis"""
    try:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        if not analyzer:
            raise HTTPException(status_code=404, detail="Log not found")
        
        battery_data = analyzer.get_battery_series()
        
        return {
            "log_id": log_id,
            "data_type": "battery",
            "battery_series": battery_data,
            "data_points": len(battery_data),
            "units": {
                "voltage": "volts",
                "current": "amperes",
                "consumed": "milliamp_hours"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get battery data: {str(e)}")

@app.get("/logs/{log_id}/vibration_data")
async def get_vibration_data(log_id: str):
    """Get time-series vibration data for mechanical health analysis"""
    try:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        if not analyzer:
            raise HTTPException(status_code=404, detail="Log not found")
        
        vibration_data = analyzer.get_vibration_series()
        
        return {
            "log_id": log_id,
            "data_type": "vibration",
            "vibration_series": vibration_data,
            "data_points": len(vibration_data),
            "units": "acceleration_units",
            "axes": ["x", "y", "z"],
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get vibration data: {str(e)}")

@app.get("/logs/{log_id}/mode_changes")
async def get_mode_changes(log_id: str):
    """Get flight mode changes with timestamps"""
    try:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        if not analyzer:
            raise HTTPException(status_code=404, detail="Log not found")
        
        mode_changes = analyzer.get_mode_changes()
        
        return {
            "log_id": log_id,
            "data_type": "mode_changes",
            "mode_changes": mode_changes,
            "total_changes": len(mode_changes),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get mode changes: {str(e)}")

@app.get("/logs/{log_id}/flight_path")
async def get_flight_path(log_id: str):
    """Get complete flight path data optimized for mapping visualization"""
    try:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        if not analyzer:
            raise HTTPException(status_code=404, detail="Log not found")
        
        # Get GPS data for path
        gps_data = analyzer.get_gps_coords_series()
        
        # Get altitude data
        altitude_data = analyzer.get_altitude_series()
        
        # Get mode changes for context
        mode_changes = analyzer.get_mode_changes()
        
        # Get significant events
        events = analyzer.get_significant_events()
        
        return {
            "log_id": log_id,
            "flight_path": {
                "coordinates": gps_data,
                "altitude_profile": altitude_data,
                "mode_changes": mode_changes,
                "significant_events": events
            },
            "path_statistics": {
                "total_distance_m": _calculate_flight_distance(gps_data),
                "max_altitude_m": max([p["altitude_m"] for p in gps_data]) if gps_data else 0,
                "avg_speed_ms": sum([p["speed_ms"] for p in gps_data]) / len(gps_data) if gps_data else 0
            },
            "coordinate_system": "WGS84",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get flight path: {str(e)}")

def _calculate_flight_distance(gps_data: List[Dict]) -> float:
    """Calculate total flight distance from GPS coordinates"""
    if len(gps_data) < 2:
        return 0.0
    
    import math
    
    total_distance = 0.0
    for i in range(1, len(gps_data)):
        # Haversine formula for distance between GPS points
        lat1, lon1 = math.radians(gps_data[i-1]['latitude']), math.radians(gps_data[i-1]['longitude'])
        lat2, lon2 = math.radians(gps_data[i]['latitude']), math.radians(gps_data[i]['longitude'])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in meters
        total_distance += 6371000 * c
    
    return round(total_distance, 2)

@app.post("/agent-chat")
async def agent_chat(
    msg: str = Query(..., description="User message"),
    logId: Optional[str] = Query(None, description="Log ID for context"),
    analysis_mode: str = Query("standard", description="Analysis mode: quick, standard, deep, expert")
):
    """Enhanced chat with intelligent agent orchestration"""
    try:
        # Use the new orchestrator for intelligent routing
        response = ORCHESTRATOR.process_request(
            message=msg,
            log_id=logId,
            analysis_mode=analysis_mode
        )
        
        return {
            "response": response.get("response", "I couldn't process your request"),
            "agent_used": response.get("agent_used", "Unknown"),
            "confidence": response.get("confidence", 0.0),
            "task_type": response.get("task_type", "unknown"),
            "analysis_mode": analysis_mode,
            "intelligent_routing": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "response": f"❌ Agent chat error: {str(e)}",
            "error": True,
            "timestamp": datetime.now().isoformat()
        }

@app.post("/analyze-structured")
async def analyze_structured(
    log_id: str = Query(..., description="Log ID for analysis"),
    analysis_types: List[str] = Query(["flight", "safety", "performance"], description="Types of analysis to perform"),
    include_insights: bool = Query(True, description="Include AI-generated insights"),
    format_type: str = Query("json", description="Response format: json, summary, detailed")
):
    """Get structured analysis results for multiple analysis types"""
    try:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        if not analyzer:
            raise HTTPException(status_code=404, detail="Log not found")
        
        results = {
            "log_id": log_id,
            "analysis_types": analysis_types,
            "analyses": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Perform each requested analysis type
        for analysis_type in analysis_types:
            if analysis_type == "flight":
                results["analyses"]["flight"] = {
                    "summary": analyzer.get_summary(),
                    "altitude_profile": analyzer.get_altitude_series(),
                    "speed_profile": analyzer.get_speed_series(),
                    "flight_path": analyzer.get_gps_coords_series()
                }
            
            elif analysis_type == "safety":
                results["analyses"]["safety"] = {
                    "gps_issues": analyzer.detect_gps_issues(),
                    "significant_events": analyzer.get_significant_events(),
                    "mode_changes": analyzer.get_mode_changes(),
                }
            
            elif analysis_type == "performance":
                results["analyses"]["performance"] = {
                    "battery_data": analyzer.get_battery_series(),
                    "vibration_data": analyzer.get_vibration_series(),
                    "highest_altitude": analyzer.get_highest_altitude()
                }
        
        # Add AI insights if requested
        if include_insights:
            results["ai_insights"] = {}
            for analysis_type in analysis_types:
                insight_response = ORCHESTRATOR.process_request(
                    message=f"Provide insights for {analysis_type} analysis",
                    log_id=log_id,
                    analysis_mode="expert"
                )
                results["ai_insights"][analysis_type] = insight_response.get("response", "No insights available")
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Structured analysis failed: {str(e)}")

@app.get("/logs/{log_id}/performance")
async def get_performance_metrics(log_id: str):
    """Get comprehensive performance metrics"""
    try:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        if not analyzer:
            raise HTTPException(status_code=404, detail="Log not found")
        
        # Get raw data
        summary = analyzer.get_summary()
        battery_data = analyzer.get_battery_series()
        speed_data = analyzer.get_speed_series()
        altitude_data = analyzer.get_altitude_series()
        vibration_data = analyzer.get_vibration_series()
        
        # Calculate performance metrics
        performance_metrics = {
            "log_id": log_id,
            "flight_efficiency": {
                "duration_seconds": summary.get("duration_seconds", 0),
                "total_distance_m": _calculate_flight_distance(analyzer.get_gps_coords_series()),
                "average_speed_ms": sum([p.get("speed_ms", 0) for p in speed_data]) / max(len(speed_data), 1),
                "max_altitude_m": max([p.get("altitude_m", 0) for p in altitude_data]) if altitude_data else 0,
            },
            "power_efficiency": _calculate_power_metrics(battery_data),
            "stability_metrics": _calculate_stability_metrics(vibration_data),
            "communication_quality": {
                "total_messages": summary.get("total_messages", 0),
                "message_rate_hz": summary.get("total_messages", 0) / max(summary.get("duration_seconds", 1), 1),
                "unique_message_types": len(summary.get("message_types", []))
            },
            "overall_score": 0.0,  # Will be calculated
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate overall performance score (0-100)
        performance_metrics["overall_score"] = _calculate_performance_score(performance_metrics)
        
        return performance_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Performance metrics calculation failed: {str(e)}")

@app.get("/logs/{log_id}/safety")
async def get_safety_assessment(log_id: str):
    """Get comprehensive safety assessment"""
    try:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        if not analyzer:
            raise HTTPException(status_code=404, detail="Log not found")
        
        # Use the Safety Agent for comprehensive assessment
        safety_response = ORCHESTRATOR.process_request(
            message="Perform comprehensive safety assessment",
            log_id=log_id,
            analysis_mode="expert"
        )
        
        # Get additional safety data
        gps_issues = analyzer.detect_gps_issues()
        events = analyzer.get_significant_events()
        mode_changes = analyzer.get_mode_changes()
        
        # Calculate safety scores
        safety_assessment = {
            "log_id": log_id,
            "overall_safety_level": "SAFE",  # Default
            "safety_scores": {
                "gps_reliability": _calculate_gps_safety_score(gps_issues),
                "flight_stability": _calculate_stability_safety_score(mode_changes),
                "event_severity": _calculate_event_safety_score(events),
                "overall": 0.0
            },
            "risk_factors": _identify_risk_factors(gps_issues, events, mode_changes),
            "recommendations": _generate_safety_recommendations(gps_issues, events, mode_changes),
            "agent_analysis": safety_response.get("response", "No analysis available"),
            "detailed_assessment": {
                "gps_issues": gps_issues,
                "significant_events": events,
                "mode_changes": mode_changes
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate overall safety score and level
        overall_score = (
            safety_assessment["safety_scores"]["gps_reliability"] * 0.3 +
            safety_assessment["safety_scores"]["flight_stability"] * 0.3 +
            safety_assessment["safety_scores"]["event_severity"] * 0.4
        )
        safety_assessment["safety_scores"]["overall"] = overall_score
        
        if overall_score >= 90:
            safety_assessment["overall_safety_level"] = "EXCELLENT"
        elif overall_score >= 75:
            safety_assessment["overall_safety_level"] = "GOOD"
        elif overall_score >= 50:
            safety_assessment["overall_safety_level"] = "ACCEPTABLE"
        elif overall_score >= 25:
            safety_assessment["overall_safety_level"] = "POOR"
        else:
            safety_assessment["overall_safety_level"] = "CRITICAL"
        
        return safety_assessment
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Safety assessment failed: {str(e)}")

@app.get("/logs/{log_id}/quality")
async def get_flight_quality(log_id: str):
    """Get overall flight quality score and breakdown"""
    try:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        if not analyzer:
            raise HTTPException(status_code=404, detail="Log not found")
        
        # Get component scores
        summary = analyzer.get_summary()
        gps_data = analyzer.get_gps_coords_series()
        battery_data = analyzer.get_battery_series()
        vibration_data = analyzer.get_vibration_series()
        
        quality_metrics = {
            "log_id": log_id,
            "quality_components": {
                "data_completeness": _calculate_data_completeness_score(summary, gps_data, battery_data),
                "gps_accuracy": _calculate_gps_accuracy_score(gps_data),
                "flight_smoothness": _calculate_smoothness_score(vibration_data),
                "battery_health": _calculate_battery_health_score(battery_data),
                "telemetry_quality": _calculate_telemetry_quality_score(summary)
            },
            "overall_quality_score": 0.0,
            "quality_grade": "A",
            "strengths": [],
            "areas_for_improvement": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate weighted overall score
        components = quality_metrics["quality_components"]
        overall_score = (
            components["data_completeness"] * 0.25 +
            components["gps_accuracy"] * 0.25 +
            components["flight_smoothness"] * 0.20 +
            components["battery_health"] * 0.15 +
            components["telemetry_quality"] * 0.15
        )
        quality_metrics["overall_quality_score"] = overall_score
        
        # Assign quality grade
        if overall_score >= 95:
            quality_metrics["quality_grade"] = "A+"
        elif overall_score >= 90:
            quality_metrics["quality_grade"] = "A"
        elif overall_score >= 85:
            quality_metrics["quality_grade"] = "A-"
        elif overall_score >= 80:
            quality_metrics["quality_grade"] = "B+"
        elif overall_score >= 75:
            quality_metrics["quality_grade"] = "B"
        elif overall_score >= 70:
            quality_metrics["quality_grade"] = "B-"
        elif overall_score >= 65:
            quality_metrics["quality_grade"] = "C+"
        elif overall_score >= 60:
            quality_metrics["quality_grade"] = "C"
        else:
            quality_metrics["quality_grade"] = "D"
        
        # Generate insights
        quality_metrics["strengths"], quality_metrics["areas_for_improvement"] = _generate_quality_insights(components)
        
        return quality_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Flight quality assessment failed: {str(e)}")

@app.get("/logs/{log_id}/insights")
async def get_flight_insights(
    log_id: str,
    insight_type: str = Query("comprehensive", description="Type of insights: comprehensive, safety, performance, operational")
):
    """Get AI-generated insights for the flight"""
    try:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        if not analyzer:
            raise HTTPException(status_code=404, detail="Log not found")
        
        # Generate insights using the intelligent agent system
        insight_prompt = {
            "comprehensive": "Provide comprehensive insights about this flight covering all aspects",
            "safety": "Focus on safety-related insights and recommendations",
            "performance": "Analyze flight performance and efficiency metrics",
            "operational": "Provide operational insights for flight planning and execution"
        }.get(insight_type, "Provide comprehensive insights about this flight")
        
        response = ORCHESTRATOR.process_request(
            message=insight_prompt,
            log_id=log_id,
            analysis_mode="expert"
        )
        
        return {
            "log_id": log_id,
            "insight_type": insight_type,
            "insights": response.get("response", "No insights available"),
            "agent_used": response.get("agent_used", "Unknown"),
            "confidence": response.get("confidence", 0.0),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Insight generation failed: {str(e)}")

@app.post("/batch-analyze")
async def batch_analyze_logs(
    log_ids: List[str] = Query(..., description="List of log IDs to analyze"),
    analysis_types: List[str] = Query(["performance", "safety"], description="Types of analysis to perform"),
    compare_results: bool = Query(True, description="Include comparative analysis")
):
    """Perform batch analysis on multiple logs"""
    try:
        if len(log_ids) == 0:
            raise HTTPException(status_code=400, detail="No log IDs provided")
        
        batch_results = {
            "log_ids": log_ids,
            "analysis_types": analysis_types,
            "individual_results": {},
            "comparative_analysis": None,
            "batch_summary": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Analyze each log individually
        for log_id in log_ids:
            analyzer = LOG_MANAGER.get_analyzer(log_id)
            if analyzer:
                log_results = {}
                
                if "performance" in analysis_types:
                    # Get performance metrics (simplified)
                    summary = analyzer.get_summary()
                    log_results["performance"] = {
                        "duration": summary.get("duration_seconds", 0),
                        "max_altitude": max([p.get("altitude_m", 0) for p in analyzer.get_altitude_series()]) if analyzer.get_altitude_series() else 0,
                        "avg_speed": sum([p.get("speed_ms", 0) for p in analyzer.get_speed_series()]) / max(len(analyzer.get_speed_series()), 1)
                    }
                
                if "safety" in analysis_types:
                    log_results["safety"] = {
                        "gps_issues": analyzer.detect_gps_issues(),
                        "event_count": len(analyzer.get_significant_events())
                    }
                
                batch_results["individual_results"][log_id] = log_results
        
        # Perform comparative analysis if requested
        if compare_results and len(log_ids) > 1:
            comparison_response = ORCHESTRATOR.process_request(
                message=f"Compare these {len(log_ids)} flights and identify patterns",
                log_id=None,  # No specific log for comparison
                analysis_mode="expert"
            )
            batch_results["comparative_analysis"] = comparison_response.get("response", "No comparison available")
        
        # Generate batch summary
        batch_results["batch_summary"] = {
            "total_logs_analyzed": len([k for k, v in batch_results["individual_results"].items() if v]),
            "failed_analyses": len(log_ids) - len(batch_results["individual_results"]),
            "analysis_types_completed": analysis_types
        }
        
        return batch_results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")

# Helper functions for calculations
def _calculate_power_metrics(battery_data: List[Dict]) -> Dict[str, float]:
    """Calculate power efficiency metrics"""
    if not battery_data:
        return {"average_voltage": 0.0, "peak_current": 0.0, "total_consumption": 0.0}
    
    voltages = [p.get("voltage_v", 0) for p in battery_data]
    currents = [p.get("current_a", 0) for p in battery_data]
    
    return {
        "average_voltage": sum(voltages) / len(voltages) if voltages else 0.0,
        "peak_current": max(currents) if currents else 0.0,
        "total_consumption": sum([p.get("consumed_mah", 0) for p in battery_data]) if battery_data else 0.0
    }

def _calculate_stability_metrics(vibration_data: List[Dict]) -> Dict[str, float]:
    """Calculate flight stability metrics"""
    if not vibration_data:
        return {"avg_vibration_x": 0.0, "avg_vibration_y": 0.0, "avg_vibration_z": 0.0}
    
    return {
        "avg_vibration_x": sum([p.get("vibe_x", 0) for p in vibration_data]) / len(vibration_data),
        "avg_vibration_y": sum([p.get("vibe_y", 0) for p in vibration_data]) / len(vibration_data),
        "avg_vibration_z": sum([p.get("vibe_z", 0) for p in vibration_data]) / len(vibration_data)
    }

def _calculate_performance_score(metrics: Dict) -> float:
    """Calculate overall performance score (0-100)"""
    # Simplified scoring algorithm
    base_score = 75.0
    
    # Adjust based on efficiency metrics
    efficiency = metrics.get("flight_efficiency", {})
    duration = efficiency.get("duration_seconds", 0)
    
    if duration > 600:  # 10 minutes+
        base_score += 10
    elif duration < 60:  # Less than 1 minute
        base_score -= 15
    
    # Adjust based on communication quality
    comm = metrics.get("communication_quality", {})
    msg_rate = comm.get("message_rate_hz", 0)
    
    if msg_rate > 50:
        base_score += 5
    elif msg_rate < 10:
        base_score -= 10
    
    return max(0.0, min(100.0, base_score))

def _calculate_gps_safety_score(gps_issues: Dict) -> float:
    """Calculate GPS safety score (0-100)"""
    if gps_issues.get("has_gps_issues", False):
        return 50.0  # Moderate score if issues detected
    return 95.0  # High score if no issues

def _calculate_stability_safety_score(mode_changes: List) -> float:
    """Calculate stability safety score based on mode changes"""
    if len(mode_changes) > 15:
        return 40.0  # Many mode changes indicate instability
    elif len(mode_changes) > 10:
        return 70.0
    return 90.0

def _calculate_event_safety_score(events: List) -> float:
    """Calculate safety score based on significant events"""
    if not events:
        return 100.0
    
    critical_events = [e for e in events if e.get("severity", "").upper() == "CRITICAL"]
    warning_events = [e for e in events if e.get("severity", "").upper() == "WARNING"]
    
    if critical_events:
        return 20.0
    elif len(warning_events) > 5:
        return 50.0
    elif warning_events:
        return 75.0
    return 95.0

def _identify_risk_factors(gps_issues: Dict, events: List, mode_changes: List) -> List[str]:
    """Identify risk factors from flight data"""
    risks = []
    
    if gps_issues.get("has_gps_issues", False):
        risks.append("GPS signal reliability issues detected")
    
    if len(mode_changes) > 15:
        risks.append("Excessive flight mode changes indicate potential instability")
    
    critical_events = [e for e in events if e.get("severity", "").upper() == "CRITICAL"]
    if critical_events:
        risks.append(f"{len(critical_events)} critical events detected")
    
    return risks

def _generate_safety_recommendations(gps_issues: Dict, events: List, mode_changes: List) -> List[str]:
    """Generate safety recommendations"""
    recommendations = []
    
    if gps_issues.get("has_gps_issues", False):
        recommendations.append("Consider GPS calibration and check for interference sources")
    
    if len(mode_changes) > 15:
        recommendations.append("Review flight controller tuning and pilot input consistency")
    
    if not recommendations:
        recommendations.append("Flight appears to have operated within normal safety parameters")
    
    return recommendations

def _calculate_data_completeness_score(summary: Dict, gps_data: List, battery_data: List) -> float:
    """Calculate data completeness score"""
    score = 0.0
    
    if summary.get("total_messages", 0) > 1000:
        score += 40
    elif summary.get("total_messages", 0) > 100:
        score += 25
    
    if len(gps_data) > 50:
        score += 30
    elif len(gps_data) > 10:
        score += 20
    
    if len(battery_data) > 10:
        score += 30
    elif len(battery_data) > 0:
        score += 15
    
    return min(100.0, score)

def _calculate_gps_accuracy_score(gps_data: List) -> float:
    """Calculate GPS accuracy score"""
    if not gps_data:
        return 0.0
    
    hdop_values = [p.get("hdop", 99) for p in gps_data[:20]]  # Sample first 20 points
    if not hdop_values:
        return 50.0
    
    avg_hdop = sum(hdop_values) / len(hdop_values)
    
    if avg_hdop < 1.5:
        return 100.0
    elif avg_hdop < 3.0:
        return 85.0
    elif avg_hdop < 5.0:
        return 65.0
    else:
        return 30.0

def _calculate_smoothness_score(vibration_data: List) -> float:
    """Calculate flight smoothness score"""
    if not vibration_data:
        return 80.0  # Default score
    
    # Calculate average vibration magnitude
    total_vibe = 0.0
    for point in vibration_data:
        vibe_mag = (point.get("vibe_x", 0)**2 + point.get("vibe_y", 0)**2 + point.get("vibe_z", 0)**2)**0.5
        total_vibe += vibe_mag
    
    avg_vibe = total_vibe / len(vibration_data)
    
    if avg_vibe < 5.0:
        return 100.0
    elif avg_vibe < 15.0:
        return 80.0
    elif avg_vibe < 30.0:
        return 60.0
    else:
        return 30.0

def _calculate_battery_health_score(battery_data: List) -> float:
    """Calculate battery health score"""
    if not battery_data:
        return 70.0
    
    voltages = [p.get("voltage_v", 0) for p in battery_data if p.get("voltage_v", 0) > 0]
    if not voltages:
        return 50.0
    
    min_voltage = min(voltages)
    avg_voltage = sum(voltages) / len(voltages)
    
    # Assume LiPo battery (nominal 3.7V per cell, typical 4S = 14.8V nominal)
    if min_voltage > 14.0 and avg_voltage > 15.0:
        return 100.0
    elif min_voltage > 12.0 and avg_voltage > 14.0:
        return 85.0
    elif min_voltage > 10.0:
        return 60.0
    else:
        return 30.0

def _calculate_telemetry_quality_score(summary: Dict) -> float:
    """Calculate telemetry quality score"""
    msg_count = summary.get("total_messages", 0)
    duration = summary.get("duration_seconds", 1)
    msg_rate = msg_count / duration
    
    if msg_rate > 50:
        return 100.0
    elif msg_rate > 25:
        return 90.0
    elif msg_rate > 10:
        return 75.0
    elif msg_rate > 5:
        return 50.0
    else:
        return 25.0

def _generate_quality_insights(components: Dict) -> tuple:
    """Generate quality insights (strengths, improvements)"""
    strengths = []
    improvements = []
    
    for component, score in components.items():
        if score >= 90:
            strengths.append(f"Excellent {component.replace('_', ' ')}")
        elif score < 60:
            improvements.append(f"Improve {component.replace('_', ' ')}")
    
    if not strengths:
        strengths.append("Flight data captured successfully")
    if not improvements:
        improvements.append("Overall good flight quality")
    
    return strengths, improvements

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 