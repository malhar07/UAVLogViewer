# server/ai.py
import os, re, json, requests
from typing import Optional, Dict, Any, List
from core import LOG_MANAGER

LLM_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")

def call_llm(prompt: str, temperature: float = 0.3) -> str:
    """Call Ollama LLM with error handling (legacy function)"""
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

def call_llm_with_tools(messages: List[Dict[str, Any]], temperature: float = 0.3, force_tool: Optional[str] = None) -> Dict[str, Any]:
    """
    Call Ollama LLM with tool definitions.
    Returns a dictionary with either 'content' or 'tool_calls'.
    """
    try:
        # For now, we'll use a simpler approach since Ollama's function calling support varies by model
        # We'll simulate function calling by using a structured prompt
        
        # Convert messages to a single prompt for the legacy API
        system_prompt = ""
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            elif msg["role"] == "user":
                user_messages.append(msg["content"])
            elif msg["role"] == "tool":
                # Tool results are included in the conversation
                user_messages.append(f"Tool result: {msg['content']}")
        
        # Create a structured prompt that encourages the LLM to decide on tool usage
        if force_tool == "none":
            # Force content response after tool execution
            prompt = f"""{system_prompt}

Previous conversation and tool results:
{chr(10).join(user_messages)}

Based on the tool results above, provide a direct, concise answer to the user's question. Do not mention tools or analysis methods."""
        else:
            # Let LLM decide whether to use tools
            user_question = user_messages[-1] if user_messages else ""
            
            prompt = f"""You are a UAV analyst. For the user question: "{user_question}"

If this question is about analyzing a specific flight log, respond with exactly: TOOL_CALL: <tool_name>
If this is a general UAV question, respond with exactly: GENERAL_ANSWER: <your_answer>

Available tools:
- get_summary (for flight duration, time, message counts)
- highest_altitude (for altitude questions)
- gps_issues (for GPS problems)

Examples:
"what was the highest altitude?" → TOOL_CALL: highest_altitude
"how long was the flight?" → TOOL_CALL: get_summary
"what is a drone?" → GENERAL_ANSWER: A drone is an unmanned aerial vehicle

Your response:"""

        response = requests.post(
            f"{LLM_URL}/api/generate",
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature}
            },
            timeout=60
        )
        response.raise_for_status()
        
        llm_response = response.json()["response"].strip()
        
        # Parse the structured response
        if llm_response.startswith("TOOL_CALL:"):
            tool_name = llm_response.replace("TOOL_CALL:", "").strip()
            # Generate a mock tool call structure
            return {
                "tool_calls": [{
                    "id": "call_1",
                    "function": {
                        "name": tool_name,
                        "arguments": {"log_id": "placeholder"}  # Will be replaced with actual log_id
                    }
                }]
            }
        elif llm_response.startswith("GENERAL_ANSWER:"):
            content = llm_response.replace("GENERAL_ANSWER:", "").strip()
            return {"content": content}
        else:
            # Default to content if format is not recognized
            return {"content": llm_response}
            
    except requests.exceptions.RequestException as e:
        return {"error": f"Sorry, I'm having trouble connecting to the AI service. Please make sure the backend is running and Ollama is available. Error: {str(e)}"}
    except Exception as e:
        return {"error": f"An error occurred while processing your request: {str(e)}"}

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
    },
    "general_knowledge": {
        "function": None,  # This won't be called, it's just a signal for the LLM
        "description": "Answer a general question about UAVs, drones, or aviation concepts using your built-in knowledge. Use this only if the question is not about a specific flight log."
    }
}

def get_tool_schema() -> List[Dict[str, Any]]:
    """Generate tool schema for LLM function calling"""
    schema = []
    for name, tool_info in TOOLS.items():
        properties = {}
        required = []

        if name == "get_summary":
            properties = {"log_id": {"type": "string", "description": "The ID of the flight log to summarize"}}
            required = ["log_id"]
        elif name == "highest_altitude":
            properties = {"log_id": {"type": "string", "description": "The ID of the flight log to analyze for highest altitude"}}
            required = ["log_id"]
        elif name == "gps_issues":
            properties = {"log_id": {"type": "string", "description": "The ID of the flight log to check for GPS issues"}}
            required = ["log_id"]
        elif name == "general_knowledge":
            properties = {"question": {"type": "string", "description": "The general UAV question asked by the user"}}
            required = ["question"]

        schema.append({
            "type": "function",
            "function": {
                "name": name,
                "description": tool_info["description"],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        })
    return schema

# analyze_user_intent function removed - now handled by LLM decision making

def format_tool_result(tool_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare tool results for LLM consumption (structured data for natural language generation)"""
    if "error" in result:
        return {"status": "error", "message": result['error']}
    
    # Standardize units and provide concise facts for LLM to consume
    formatted_data = {}
    
    if tool_name == "get_summary":
        duration_seconds = result.get("duration_seconds")
        formatted_data = {
            "duration_seconds": f"{duration_seconds:.1f}" if duration_seconds is not None else "N/A",
            "total_messages": result.get("total_messages", 0),
            "unique_message_types": len(result.get("message_types", []))
        }
    
    elif tool_name == "highest_altitude":
        # Convert from mm to meters if needed (assuming core.py returns in mm)
        max_alt_raw = result.get("highest_altitude_m", 0)
        avg_alt_raw = result.get("average_altitude_m", 0)
        
        # Check if values are suspiciously small (likely in mm)
        if max_alt_raw < 1 and max_alt_raw > 0:
            max_alt_m = max_alt_raw  # Already in meters
            avg_alt_m = avg_alt_raw  # Already in meters
        else:
            # Assume it's in mm and convert
            max_alt_m = max_alt_raw / 1000 if max_alt_raw > 0 else max_alt_raw
            avg_alt_m = avg_alt_raw / 1000 if avg_alt_raw > 0 else avg_alt_raw
        
        formatted_data = {
            "highest_altitude_meters": f"{max_alt_m:.2f}" if max_alt_m is not None else "N/A",
            "average_altitude_meters": f"{avg_alt_m:.2f}" if avg_alt_m is not None else "N/A",
            "total_gps_readings": result.get("total_gps_readings", 0)
        }
        if max_alt_raw < 1 and max_alt_raw > 0:
            formatted_data["unit_note"] = "Values appear to be in meters"
        else:
            formatted_data["unit_note"] = "Values converted from millimeters to meters"
    
    elif tool_name == "gps_issues":
        formatted_data = {
            "total_gps_messages": result.get("total_gps_messages", 0),
            "poor_signal_events": result.get("poor_signal_events", 0),
            "signal_loss_events": result.get("signal_loss_events", 0)
        }
        if result.get("first_poor_signal"):
            formatted_data["first_poor_signal_timestamp"] = result["first_poor_signal"]
        if result.get("first_signal_loss"):
            formatted_data["first_signal_loss_timestamp"] = result["first_signal_loss"]
    
    return formatted_data

# Define a system prompt that encourages tool use and general knowledge
SYSTEM_PROMPT = """You are a highly skilled and EXTREMELY concise UAV Flight Log Analyst AI.
Your ONLY goal is to answer user questions accurately and directly.

You can answer general questions about UAVs or analyze specific flight logs using your available tools.

Strict Rules:
- If a user asks a general question about UAVs (e.g., "What is a drone?", "How does GPS work?"), answer only from your general knowledge.
- If a user asks a question about an uploaded flight log (e.g., "flight time", "altitude", "GPS signal"), you MUST use your tools to analyze the log.
- NEVER mention tool names (e.g., 'get_summary', 'highest_altitude'). Present tool results as your own analysis.
- NEVER provide unsolicited advice, recommendations, or speculative deductions.
- NEVER include conversational filler, introductions, or conclusions.
- NEVER explain your internal processing (e.g., "based on our analysis").
- Be EXTREMELY concise. For numerical answers, give only the number and standard units (e.g., "15.34 seconds", "64.3 meters").
- If the required log data is insufficient for a log-specific question, state: "I cannot find specific information for that in the flight log."
- If the user input is irrelevant or gibberish, respond ONLY with: "I can only assist with questions about Unmanned Aerial Vehicles (UAVs) and their flight logs. Please provide relevant input."
"""

def chat(user_msg: str, log_id: Optional[str] = None, conversation_history: List[Dict[str, Any]] = None) -> str:
    """Main chat function with LLM-driven tool use agent logic"""
    if conversation_history is None:
        conversation_history = []

    # Add the system prompt at the beginning of the conversation
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

    # Add current user message
    messages.append({"role": "user", "content": user_msg})

    try:
        # First LLM call: Decide whether to use a tool or answer directly
        llm_response = call_llm_with_tools(messages)

        if "error" in llm_response:
            return llm_response["error"]  # Handle connection/other errors

        if "content" in llm_response:
            # LLM decided to answer directly (general knowledge or irrelevant input)
            return llm_response["content"]
        
        elif "tool_calls" in llm_response:
            # LLM decided to call a tool
            tool_calls = llm_response["tool_calls"]
            
            # For this simple agent, we'll execute the first tool call
            first_tool_call = tool_calls[0]['function']
            tool_name = first_tool_call['name']
            tool_args = first_tool_call['arguments']

            # Validate tool arguments (e.g., ensure log_id is provided if needed)
            if 'log_id' in tool_args and not log_id:
                return "To analyze flight data, please upload a .bin log file first. You can drag and drop it into the upload area or click to browse for files."
            
            # If the LLM tried to call a log tool without a log_id, it might pass an empty or dummy one
            # Ensure the actual log_id from the session is used
            if 'log_id' in tool_args:
                tool_args['log_id'] = log_id
            
            if tool_name not in TOOLS:
                return f"AI tried to use an unknown tool: {tool_name}. This indicates an internal error."

            # Execute the tool function
            tool_function = TOOLS[tool_name]["function"]
            
            # --- Special Handling for general_knowledge ---
            if tool_name == "general_knowledge":
                # LLM explicitly decided to answer generally, no actual tool call
                # Re-prompt LLM with only the system prompt and general question
                general_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                general_messages.append({"role": "user", "content": tool_args.get("question", user_msg)})
                general_response = call_llm_with_tools(general_messages, force_tool="none")
                return general_response.get("content", "I am unable to answer that general question.")

            # For log-related tools:
            tool_result = tool_function(**tool_args)

            # Check for log_id error from tool function
            if isinstance(tool_result, dict) and "error" in tool_result and tool_result["error"] == "Log not found. Please upload a log file first.":
                return "I cannot analyze flight data without an active log. Please upload a log file first."
            
            # Format the tool result for LLM consumption
            formatted_result = format_tool_result(tool_name, tool_result)
            
            # Now, send the tool's formatted result back to the LLM for natural language formatting
            messages.append({"role": "assistant", "content": f"I'll analyze the flight log data."})
            messages.append({"role": "tool", "tool_call_id": tool_calls[0]['id'], "content": json.dumps(formatted_result)})

            # Second LLM call: Generate natural language response based on tool output
            final_llm_response = call_llm_with_tools(messages, force_tool="none")
            
            if "content" in final_llm_response:
                return final_llm_response["content"]
            else:
                # Fallback: return a direct answer from the formatted result
                if tool_name == "highest_altitude":
                    return formatted_result.get("highest_altitude_meters", "N/A") + " meters"
                elif tool_name == "get_summary":
                    return formatted_result.get("duration_seconds", "N/A") + " seconds"
                else:
                    return "Analysis completed but response formatting failed."

    except Exception as e:
        return f"An error occurred in the agent: {str(e)}"

# Create a simple agent class for compatibility
class SimpleAgent:
    def chat(self, message: str, log_id: Optional[str] = None) -> Dict[str, str]:
        response = chat(message, log_id)
        return {"response": response}

# Export the agent instance
AGENT = SimpleAgent()