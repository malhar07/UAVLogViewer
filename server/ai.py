# server/ai.py
import os, re, json, requests
from typing import Optional, Dict, Any
from core import LOG_MANAGER

LLM_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")

def call_llm(prompt: str, temperature: float = 0.3) -> str:
    """Call Ollama LLM with error handling"""
    try:
        response = requests.post(
            f"{LLM_URL}/api/generate",
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature}
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["response"].strip()
    except requests.exceptions.RequestException as e:
        return f"Sorry, I'm having trouble connecting to the AI service. Please make sure the backend is running and Ollama is available. Error: {str(e)}"
    except Exception as e:
        return f"An error occurred while processing your request: {str(e)}"

def get_log_summary(log_id: str) -> Dict[str, Any]:
    """Get comprehensive log summary"""
    analyzer = LOG_MANAGER.get_analyzer(log_id)
    if not analyzer:
        return {"error": "Log not found. Please upload a log file first."}
    
    return analyzer.get_summary()

def get_highest_altitude(log_id: str) -> Dict[str, Any]:
    """Get highest altitude from log"""
    analyzer = LOG_MANAGER.get_analyzer(log_id)
    if not analyzer:
        return {"error": "Log not found. Please upload a log file first."}
    
    return analyzer.get_highest_altitude()

def detect_gps_issues(log_id: str) -> Dict[str, Any]:
    """Detect GPS signal issues"""
    analyzer = LOG_MANAGER.get_analyzer(log_id)
    if not analyzer:
        return {"error": "Log not found. Please upload a log file first."}
    
    return analyzer.detect_gps_issues()

# Available tools registry
TOOLS = {
    "get_summary": {
        "function": get_log_summary,
        "description": "Get a comprehensive summary of the flight log including duration, message types, and basic statistics"
    },
    "highest_altitude": {
        "function": get_highest_altitude,
        "description": "Find the highest altitude reached during the flight"
    },
    "gps_issues": {
        "function": detect_gps_issues,
        "description": "Detect GPS signal loss or accuracy issues during the flight"
    }
}

def analyze_user_intent(user_msg: str, has_log: bool) -> Dict[str, Any]:
    """Analyze what the user wants and determine if tools are needed"""
    user_msg_lower = user_msg.lower()
    
    # Keywords that indicate log analysis is needed
    log_keywords = [
        "summary", "duration", "flight time", "total time", "how long",
        "altitude", "highest", "maximum", "max alt", "peak",
        "gps", "signal", "loss", "accuracy", "fix",
        "messages", "data", "log", "analysis", "statistics"
    ]
    
    # Check if user is asking for log analysis
    needs_log_analysis = any(keyword in user_msg_lower for keyword in log_keywords)
    
    if not needs_log_analysis:
        return {"needs_tools": False, "tool": None}
    
    if not has_log:
        return {"needs_tools": False, "tool": None, "error": "log_required"}
    
    # Determine which tool to use
    if any(word in user_msg_lower for word in ["summary", "duration", "flight time", "total time", "how long", "overview"]):
        return {"needs_tools": True, "tool": "get_summary"}
    elif any(word in user_msg_lower for word in ["altitude", "highest", "maximum", "max", "peak", "elevation"]):
        return {"needs_tools": True, "tool": "highest_altitude"}
    elif any(word in user_msg_lower for word in ["gps", "signal", "loss", "accuracy", "fix", "satellite"]):
        return {"needs_tools": True, "tool": "gps_issues"}
    else:
        return {"needs_tools": True, "tool": "get_summary"}  # Default to summary

def format_tool_result(tool_name: str, result: Dict[str, Any], user_msg: str) -> str:
    """Format tool results into human-readable responses"""
    if "error" in result:
        return f"❌ {result['error']}"
    
    if tool_name == "get_summary":
        duration_min = result.get("duration_seconds", 0) / 60
        return f"""📊 **Flight Log Summary**

🕒 **Duration**: {duration_min:.1f} minutes ({result.get('duration_seconds', 0):.1f} seconds)
📨 **Total Messages**: {result.get('total_messages', 0):,}
📋 **Message Types**: {len(result.get('message_types', []))} different types
📁 **Log File**: {result.get('log_file', 'Unknown')}

The flight lasted {duration_min:.1f} minutes and recorded {result.get('total_messages', 0):,} telemetry messages."""
    
    elif tool_name == "highest_altitude":
        max_alt_m = result.get("highest_altitude_m", 0)
        avg_alt_m = result.get("average_altitude_m", 0)
        return f"""🏔️ **Altitude Analysis**

📈 **Highest Altitude**: {max_alt_m} meters ({max_alt_m * 3.28084:.1f} feet)
📊 **Average Altitude**: {avg_alt_m} meters ({avg_alt_m * 3.28084:.1f} feet)
📡 **GPS Readings**: {result.get('total_gps_readings', 0):,} data points

The aircraft reached a maximum altitude of {max_alt_m} meters during this flight."""
    
    elif tool_name == "gps_issues":
        poor_signal = result.get("poor_signal_events", 0)
        signal_loss = result.get("signal_loss_events", 0)
        total_gps = result.get("total_gps_messages", 0)
        
        if poor_signal == 0 and signal_loss == 0:
            return f"""✅ **GPS Status: Excellent**

📡 **Total GPS Messages**: {total_gps:,}
🎯 **Signal Quality**: No accuracy issues detected
🔒 **Fix Status**: Stable 3D fix maintained

Your GPS performed excellently throughout the flight with no signal issues detected."""
        else:
            return f"""⚠️ **GPS Issues Detected**

📡 **Total GPS Messages**: {total_gps:,}
📉 **Poor Signal Events**: {poor_signal}
❌ **Signal Loss Events**: {signal_loss}

{f"First poor signal at: {result.get('first_poor_signal', 'N/A')}" if poor_signal > 0 else ""}
{f"First signal loss at: {result.get('first_signal_loss', 'N/A')}" if signal_loss > 0 else ""}"""
    
    return str(result)

def chat(user_msg: str, log_id: Optional[str] = None) -> str:
    """Main chat function with improved agent logic"""
    try:
        # Analyze user intent
        intent = analyze_user_intent(user_msg, bool(log_id))
        
        # Handle case where log analysis is needed but no log is provided
        if intent.get("error") == "log_required":
            return "To analyze flight data, please upload a .bin log file first. You can drag and drop it into the upload area or click to browse for files."
        
        # If no tools needed, use LLM for general conversation
        if not intent.get("needs_tools"):
            prompt = f"""You are a concise UAV/drone expert. Answer ONLY general questions about UAVs, drones, and aviation concepts using your knowledge.

CRITICAL RULES:
- Answer ONLY from general knowledge about UAVs/drones
- Do NOT mention any specific flight logs, data, or analysis
- Do NOT use phrases like "based on analysis" or "according to data"
- Be concise and direct
- If the question is not about UAVs/drones, say: "I can only assist with questions about UAVs and drones."

Question: {user_msg}

Answer:"""
            return call_llm(prompt)
        
        # If tools needed, execute the tool
        tool_name = intent["tool"]
        tool_func = TOOLS[tool_name]["function"]
        result = tool_func(log_id)
        
        # Return formatted result directly (no need for LLM processing)
        return format_tool_result(tool_name, result, user_msg)
        
    except Exception as e:
        return f"An error occurred while processing your request: {str(e)}"

# Create a simple agent class for compatibility
class SimpleAgent:
    def chat(self, message: str, log_id: Optional[str] = None) -> Dict[str, str]:
        response = chat(message, log_id)
        return {"response": response}

# Export the agent instance
AGENT = SimpleAgent()