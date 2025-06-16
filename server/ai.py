# server/ai.py - Enhanced Intelligent Agent Orchestration with RAG Integration
import os, re, json, requests
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from core import LOG_MANAGER

LLM_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")

class TaskType(Enum):
    """Task types for agent routing"""
    FLIGHT_ANALYSIS = "flight_analysis"
    SAFETY_ASSESSMENT = "safety_assessment"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    DIAGNOSTIC = "diagnostic"
    COMPARATIVE = "comparative"
    PREDICTIVE = "predictive"
    GENERAL_KNOWLEDGE = "general_knowledge"
    RAG_QUERY = "rag_query"  # Added RAG-specific routing

class AnalysisComplexity(Enum):
    """Analysis complexity levels"""
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"
    EXPERT = "expert"

@dataclass
class TaskContext:
    """Task context for agent decision making"""
    user_message: str
    log_id: Optional[str] = None
    task_type: Optional[TaskType] = None
    complexity: AnalysisComplexity = AnalysisComplexity.STANDARD
    requires_rag: bool = False
    requires_multimodal: bool = False
    priority: int = 0
    metadata: Dict[str, Any] = None

class IntelligentTaskRouter:
    """Intelligent task routing system with RAG awareness"""
    
    def __init__(self):
        self.routing_patterns = {
            TaskType.FLIGHT_ANALYSIS: [
                r"(altitude|height|elevation|climb|descent)",
                r"(speed|velocity|airspeed|groundspeed)",
                r"(flight|mission|path|route|waypoint)",
                r"(duration|time|length|how long)",
            ],
            TaskType.SAFETY_ASSESSMENT: [
                r"(safe|safety|risk|danger|hazard|critical)",
                r"(emergency|alert|warning|fault|failure)",
                r"(crash|collision|near miss|incident)",
                r"(gps.*loss|signal.*loss|communication.*loss)",
            ],
            TaskType.PERFORMANCE_ANALYSIS: [
                r"(performance|efficiency|optimization|improve)",
                r"(battery|power|energy|consumption)",
                r"(vibration|oscillation|instability)",
                r"(motor|propeller|rotor|engine)",
            ],
            TaskType.DIAGNOSTIC: [
                r"(error|problem|issue|fault|malfunction)",
                r"(diagnose|troubleshoot|debug|analyze)",
                r"(why|what.*wrong|what.*happened)",
                r"(sensor|imu|compass|barometer)",
            ],
            TaskType.COMPARATIVE: [
                r"(compare|comparison|versus|vs|difference)",
                r"(better|worse|improvement|degradation)",
                r"(baseline|reference|previous|last)",
            ],
            TaskType.PREDICTIVE: [
                r"(predict|forecast|future|trend|will)",
                r"(maintenance|service|replace|wear)",
                r"(expect|likely|probability|chance)",
            ],
            # RAG-specific patterns for deep log queries
            TaskType.RAG_QUERY: [
                r"(at.*seconds?|at.*minutes?|at.*time)",  # Time-specific queries
                r"(voltage.*at|current.*at|temperature.*at)",  # Specific data at time
                r"(during|when|while.*flying|throughout)",  # Contextual queries
                r"(show.*all|list.*all|find.*all)",  # Comprehensive queries
                r"(average.*during|maximum.*during|minimum.*during)",  # Calculated queries
            ],
        }
    
    def route_task(self, message: str, log_id: Optional[str] = None) -> TaskContext:
        """Route user message to appropriate task type with RAG awareness"""
        message_lower = message.lower()
        
        # Score each task type
        task_scores = {}
        for task_type, patterns in self.routing_patterns.items():
            score = sum(1 for pattern in patterns if re.search(pattern, message_lower))
            if score > 0:
                task_scores[task_type] = score
        
        # Determine best task type
        if task_scores:
            best_task = max(task_scores, key=task_scores.get)
        else:
            best_task = TaskType.GENERAL_KNOWLEDGE if not log_id else TaskType.FLIGHT_ANALYSIS
        
        # Override with RAG for complex log-specific queries
        if log_id and best_task != TaskType.GENERAL_KNOWLEDGE:
            rag_indicators = [
                "at", "during", "when", "while", "throughout", "show all", "list all",
                "voltage at", "current at", "seconds", "minutes", "average during"
            ]
            if any(indicator in message_lower for indicator in rag_indicators):
                best_task = TaskType.RAG_QUERY
        
        # Determine complexity
        complexity = AnalysisComplexity.STANDARD
        if any(word in message_lower for word in ["detailed", "comprehensive", "thorough", "expert"]):
            complexity = AnalysisComplexity.EXPERT
        elif any(word in message_lower for word in ["quick", "brief", "summary"]):
            complexity = AnalysisComplexity.QUICK
        elif any(word in message_lower for word in ["deep", "in-depth", "analyze"]):
            complexity = AnalysisComplexity.DEEP
        
        # Determine if RAG is needed
        requires_rag = log_id is not None and best_task not in [TaskType.GENERAL_KNOWLEDGE]
        
        return TaskContext(
            user_message=message,
            log_id=log_id,
            task_type=best_task,
            complexity=complexity,
            requires_rag=requires_rag,
            metadata={"routing_scores": task_scores}
        )

class SpecializedAgent:
    """Base class for specialized agents"""
    
    def __init__(self, name: str, expertise: List[str]):
        self.name = name
        self.expertise = expertise
        self.tool_registry = {}
    
    def can_handle(self, task_context: TaskContext) -> float:
        """Return confidence score (0-1) for handling this task"""
        raise NotImplementedError
    
    def execute_task(self, task_context: TaskContext) -> Dict[str, Any]:
        """Execute the assigned task"""
        raise NotImplementedError

class FlightAnalysisAgent(SpecializedAgent):
    """Specialized agent for flight analysis tasks"""
    
    def __init__(self):
        super().__init__("FlightAnalyst", ["flight_metrics", "trajectory_analysis", "performance_data"])
        self.tool_registry = {
            "get_summary": self._get_flight_summary,
            "get_altitude_profile": self._get_altitude_analysis,
            "get_speed_analysis": self._get_speed_analysis,
            "get_flight_path": self._get_path_analysis,
        }
    
    def can_handle(self, task_context: TaskContext) -> float:
        if task_context.task_type == TaskType.FLIGHT_ANALYSIS:
            return 0.9
        elif task_context.task_type in [TaskType.PERFORMANCE_ANALYSIS, TaskType.DIAGNOSTIC]:
            return 0.6
        return 0.2
    
    def execute_task(self, task_context: TaskContext) -> Dict[str, Any]:
        if not task_context.log_id:
            return {"error": "Flight analysis requires a log file"}
        
        analyzer = LOG_MANAGER.get_analyzer(task_context.log_id)
        if not analyzer:
            return {"error": "Log file not found"}
        
        # Determine specific analysis based on message
        message_lower = task_context.user_message.lower()
        
        if "altitude" in message_lower or "height" in message_lower:
            return self._get_altitude_analysis(task_context.log_id)
        elif "speed" in message_lower or "velocity" in message_lower:
            return self._get_speed_analysis(task_context.log_id)
        elif "path" in message_lower or "route" in message_lower:
            return self._get_path_analysis(task_context.log_id)
        else:
            return self._get_flight_summary(task_context.log_id)
    
    def _get_flight_summary(self, log_id: str) -> Dict[str, Any]:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        summary = analyzer.get_summary()
        return {
            "analysis_type": "flight_summary",
            "data": summary,
            "insights": self._generate_flight_insights(summary)
        }
    
    def _get_altitude_analysis(self, log_id: str) -> Dict[str, Any]:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        altitude_data = analyzer.get_altitude_series()
        max_alt = analyzer.get_highest_altitude()
        
        return {
            "analysis_type": "altitude_analysis",
            "data": {
                "altitude_series": altitude_data,
                "max_altitude": max_alt,
                "altitude_range": max([p["altitude_m"] for p in altitude_data]) - min([p["altitude_m"] for p in altitude_data]) if altitude_data else 0
            },
            "insights": self._generate_altitude_insights(altitude_data, max_alt)
        }
    
    def _get_speed_analysis(self, log_id: str) -> Dict[str, Any]:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        speed_data = analyzer.get_speed_series()
        
        return {
            "analysis_type": "speed_analysis", 
            "data": speed_data,
            "insights": self._generate_speed_insights(speed_data)
        }
    
    def _get_path_analysis(self, log_id: str) -> Dict[str, Any]:
        analyzer = LOG_MANAGER.get_analyzer(log_id)
        gps_data = analyzer.get_gps_coords_series()
        
        return {
            "analysis_type": "path_analysis",
            "data": gps_data,
            "insights": self._generate_path_insights(gps_data)
        }
    
    def _generate_flight_insights(self, summary: Dict) -> List[str]:
        insights = []
        if "duration_seconds" in summary:
            duration = summary["duration_seconds"]
            if duration < 60:
                insights.append("Very short flight - likely a test or configuration flight")
            elif duration > 3600:
                insights.append("Long duration flight - good for endurance testing")
        
        if "total_messages" in summary:
            msg_rate = summary["total_messages"] / summary.get("duration_seconds", 1)
            if msg_rate > 100:
                insights.append("High message rate indicates good telemetry connectivity")
            elif msg_rate < 10:
                insights.append("Low message rate may indicate connection issues")
        
        return insights
    
    def _generate_altitude_insights(self, altitude_data: List, max_alt: Dict) -> List[str]:
        insights = []
        if max_alt and "altitude_m" in max_alt:
            alt = max_alt["altitude_m"]
            if alt > 120:  # 400ft AGL limit in many regions
                insights.append("⚠️ Flight exceeded typical recreational altitude limits")
            elif alt < 5:
                insights.append("Low altitude flight - good for ground-level operations")
            else:
                insights.append("Flight altitude within normal recreational limits")
        
        return insights
    
    def _generate_speed_insights(self, speed_data: List) -> List[str]:
        insights = []
        if speed_data:
            speeds = [p["speed_ms"] for p in speed_data if "speed_ms" in p]
            if speeds:
                max_speed = max(speeds)
                if max_speed > 15:  # ~33 mph
                    insights.append("High speed flight - monitor for wind resistance")
                elif max_speed < 2:
                    insights.append("Low speed flight - good for precision operations")
        
        return insights
    
    def _generate_path_insights(self, gps_data: List) -> List[str]:
        insights = []
        if len(gps_data) > 10:
            # Check for GPS quality
            hdop_values = [p.get("hdop", 99) for p in gps_data[:10]]
            avg_hdop = sum(hdop_values) / len(hdop_values)
            if avg_hdop < 2:
                insights.append("Excellent GPS accuracy throughout flight")
            elif avg_hdop > 5:
                insights.append("⚠️ Poor GPS accuracy detected - consider GPS positioning")
        
        return insights

class SafetyAgent(SpecializedAgent):
    """Specialized agent for safety assessment"""
    
    def __init__(self):
        super().__init__("SafetyAnalyst", ["safety_protocols", "risk_assessment", "emergency_procedures"])
    
    def can_handle(self, task_context: TaskContext) -> float:
        if task_context.task_type == TaskType.SAFETY_ASSESSMENT:
            return 0.95
        elif task_context.task_type == TaskType.DIAGNOSTIC:
            return 0.7
        return 0.3
    
    def execute_task(self, task_context: TaskContext) -> Dict[str, Any]:
        if not task_context.log_id:
            return {"error": "Safety analysis requires a log file"}
        
        analyzer = LOG_MANAGER.get_analyzer(task_context.log_id)
        if not analyzer:
            return {"error": "Log file not found"}
        
        # Comprehensive safety analysis
        safety_report = {
            "analysis_type": "safety_assessment",
            "gps_issues": analyzer.detect_gps_issues(),
            "significant_events": analyzer.get_significant_events(),
            "mode_changes": analyzer.get_mode_changes(),
            "overall_assessment": "SAFE"  # Default
        }
        
        # Determine overall safety level
        events = safety_report["significant_events"]
        if any(event.get("severity", "").upper() == "CRITICAL" for event in events):
            safety_report["overall_assessment"] = "CRITICAL_ISSUES"
        elif any(event.get("severity", "").upper() == "WARNING" for event in events):
            safety_report["overall_assessment"] = "WARNINGS_PRESENT"
        
        safety_report["insights"] = self._generate_safety_insights(safety_report)
        
        return safety_report
    
    def _generate_safety_insights(self, safety_data: Dict) -> List[str]:
        insights = []
        
        # GPS analysis
        gps_issues = safety_data.get("gps_issues", {})
        if gps_issues.get("has_gps_issues", False):
            insights.append("⚠️ GPS signal issues detected - review navigation reliability")
        
        # Event analysis
        events = safety_data.get("significant_events", [])
        critical_events = [e for e in events if e.get("severity", "").upper() == "CRITICAL"]
        if critical_events:
            insights.append(f"🚨 {len(critical_events)} critical safety events detected")
        
        # Mode changes
        mode_changes = safety_data.get("mode_changes", [])
        if len(mode_changes) > 10:
            insights.append("Frequent mode changes detected - review flight stability")
        
        return insights

class RAGQueryAgent(SpecializedAgent):
    """Specialized agent for RAG-powered deep log queries"""
    
    def __init__(self):
        super().__init__("RAGAnalyst", ["deep_log_queries", "contextual_analysis", "time_series_search"])
    
    def can_handle(self, task_context: TaskContext) -> float:
        if task_context.task_type == TaskType.RAG_QUERY:
            return 0.95
        return 0.1
    
    def execute_task(self, task_context: TaskContext) -> Dict[str, Any]:
        if not task_context.log_id:
            return {"error": "RAG analysis requires a log file"}
        
        try:
            # Import RAG_ENGINE here to avoid circular imports
            from rag_engine import RAG_ENGINE
            
            # Query the RAG system
            rag_result = RAG_ENGINE.query_logs(task_context.user_message, task_context.log_id)
            
            if "error" in rag_result:
                return {"error": f"RAG query failed: {rag_result['error']}"}
            
            return {
                "analysis_type": "rag_query",
                "data": rag_result,
                "insights": ["Deep contextual analysis completed using RAG system"],
                "rag_powered": True
            }
            
        except Exception as e:
            return {"error": f"RAG analysis failed: {str(e)}"}

class AgentOrchestrator:
    """Enhanced orchestrator with RAG integration and LLM decision making"""
    
    def __init__(self):
        self.task_router = IntelligentTaskRouter()
        self.agents = [
            FlightAnalysisAgent(),
            SafetyAgent(),
            RAGQueryAgent(),  # Added RAG agent
        ]
        self.llm_url = LLM_URL
        self.llm_model = LLM_MODEL
    
    def process_request(self, message: str, log_id: Optional[str] = None, 
                       analysis_mode: str = "standard") -> Dict[str, Any]:
        """Enhanced processing with LLM decision-making and RAG integration"""
        try:
            # STEP 1: Initial LLM call for intent classification
            intent_result = self._classify_intent_with_llm(message, log_id)
            
            if "error" in intent_result:
                return self._handle_general_query(message, log_id)
            
            intent_type = intent_result.get("intent", "GENERAL_ANSWER")
            
            # STEP 2: Route based on LLM decision
            if intent_type == "GENERAL_ANSWER":
                return self._handle_general_query(message, log_id)
            
            elif intent_type == "TOOL_CALL":
                return self._handle_tool_call(message, log_id, intent_result)
            
            elif intent_type == "LOG_QUERY":
                return self._handle_rag_query(message, log_id, analysis_mode)
            
            else:
                # Fallback to agent orchestration
                return self._handle_agent_orchestration(message, log_id, analysis_mode)
                
        except Exception as e:
            return {
                "response": f"Agent orchestration failed: {str(e)}",
                "error": True,
                "timestamp": datetime.now().isoformat()
            }
    
    def _classify_intent_with_llm(self, message: str, log_id: Optional[str]) -> Dict[str, Any]:
        """Use LLM to classify user intent for routing"""
        try:
            prompt = f"""You are a UAV flight log analyst. Classify this user question into one of three categories:

User question: "{message}"
Log available: {"Yes" if log_id else "No"}

Respond with EXACTLY one of these:
- TOOL_CALL: <tool_name> (for basic flight metrics: get_summary, highest_altitude, gps_issues)
- LOG_QUERY: <original_question> (for specific time-based or detailed log questions)
- GENERAL_ANSWER: <brief_answer> (for general UAV knowledge questions)

Examples:
"How long was the flight?" → TOOL_CALL: get_summary
"What was the highest altitude?" → TOOL_CALL: highest_altitude
"Were there GPS issues?" → TOOL_CALL: gps_issues
"What was the battery voltage at 2 minutes?" → LOG_QUERY: What was the battery voltage at 2 minutes?
"Show me all mode changes" → LOG_QUERY: Show me all mode changes
"What is a drone?" → GENERAL_ANSWER: A drone is an unmanned aerial vehicle

Your response:"""

            response = requests.post(
                f"{self.llm_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}  # Low temperature for consistent classification
                },
                timeout=30
            )
            
            if response.status_code == 200:
                llm_response = response.json()["response"].strip()
                
                # Parse the LLM response
                if llm_response.startswith("TOOL_CALL:"):
                    tool_name = llm_response.replace("TOOL_CALL:", "").strip()
                    return {"intent": "TOOL_CALL", "tool_name": tool_name}
                elif llm_response.startswith("LOG_QUERY:"):
                    query = llm_response.replace("LOG_QUERY:", "").strip()
                    return {"intent": "LOG_QUERY", "query": query}
                elif llm_response.startswith("GENERAL_ANSWER:"):
                    answer = llm_response.replace("GENERAL_ANSWER:", "").strip()
                    return {"intent": "GENERAL_ANSWER", "answer": answer}
                else:
                    return {"error": "Failed to parse LLM intent classification"}
            else:
                return {"error": "LLM classification request failed"}
                
        except Exception as e:
            return {"error": f"Intent classification failed: {str(e)}"}
    
    def _handle_tool_call(self, message: str, log_id: str, intent_result: Dict) -> Dict[str, Any]:
        """Handle tool-based queries with RAG enhancement"""
        tool_name = intent_result.get("tool_name", "")
        
        if not log_id:
            return {
                "response": "To analyze flight data, please upload a .bin log file first.",
                "error": True
            }
        
        try:
            # Execute the tool
            tool_result = None
            if tool_name == "get_summary":
                analyzer = LOG_MANAGER.get_analyzer(log_id)
                tool_result = analyzer.get_summary() if analyzer else {"error": "Log not found"}
            elif tool_name == "highest_altitude":
                analyzer = LOG_MANAGER.get_analyzer(log_id)
                tool_result = analyzer.get_highest_altitude() if analyzer else {"error": "Log not found"}
            elif tool_name == "gps_issues":
                analyzer = LOG_MANAGER.get_analyzer(log_id)
                tool_result = analyzer.detect_gps_issues() if analyzer else {"error": "Log not found"}
            else:
                tool_result = {"error": f"Unknown tool: {tool_name}"}
            
            if "error" in tool_result:
                return {"response": f"❌ {tool_result['error']}", "error": True}
            
            # Get additional RAG context
            rag_context = self._get_rag_context(message, log_id)
            
            # Synthesize tool result with RAG context
            enhanced_result = self._synthesize_with_llm(tool_result, rag_context, message)
            
            return {
                "response": enhanced_result,
                "agent_used": "ToolAgent",
                "tool_used": tool_name,
                "rag_enhanced": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"response": f"Tool execution failed: {str(e)}", "error": True}
    
    def _handle_rag_query(self, message: str, log_id: str, analysis_mode: str) -> Dict[str, Any]:
        """Handle RAG-powered deep log queries"""
        if not log_id:
            return {
                "response": "RAG analysis requires a log file. Please upload a .bin file first.",
                "error": True
            }
        
        try:
            # Use the RAG agent
            task_context = TaskContext(
                user_message=message,
                log_id=log_id,
                task_type=TaskType.RAG_QUERY,
                complexity=AnalysisComplexity.DEEP
            )
            
            rag_agent = RAGQueryAgent()
            result = rag_agent.execute_task(task_context)
            
            if "error" in result:
                return {"response": f"❌ {result['error']}", "error": True}
            
            # Extract RAG response
            rag_data = result.get("data", {})
            rag_response = rag_data.get("response", "No response available")
            
            return {
                "response": rag_response,
                "agent_used": "RAGAnalyst",
                "rag_powered": True,
                "source_documents": rag_data.get("source_documents", []),
                "analysis_mode": analysis_mode,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"response": f"RAG query failed: {str(e)}", "error": True}
    
    def _handle_agent_orchestration(self, message: str, log_id: Optional[str], analysis_mode: str) -> Dict[str, Any]:
        """Handle requests through agent orchestration (existing logic)"""
        # Route the task
        task_context = self.task_router.route_task(message, log_id)
        
        # Find best agent for the task
        agent_scores = [(agent, agent.can_handle(task_context)) for agent in self.agents]
        best_agent, confidence = max(agent_scores, key=lambda x: x[1])
        
        # Execute task with best agent
        if confidence > 0.5:
            result = best_agent.execute_task(task_context)
            
            # Enhance result with LLM interpretation
            enhanced_result = self._enhance_with_llm(result, task_context, best_agent.name)
            
            return {
                "response": enhanced_result,
                "agent_used": best_agent.name,
                "confidence": confidence,
                "task_type": task_context.task_type.value,
                "analysis_mode": analysis_mode,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Fall back to general chat
            return self._handle_general_query(message, log_id)
    
    def _get_rag_context(self, message: str, log_id: str) -> str:
        """Get RAG context for enhancing tool results"""
        try:
            from rag_engine import RAG_ENGINE
            rag_result = RAG_ENGINE.query_logs(message, log_id)
            return rag_result.get("response", "No additional context available")
        except Exception:
            return "RAG context unavailable"
    
    def _synthesize_with_llm(self, tool_result: Dict, rag_context: str, original_question: str) -> str:
        """Synthesize tool result with RAG context using LLM"""
        try:
            prompt = f"""You are a UAV expert. Answer the user's question by combining tool data and contextual information.

User question: "{original_question}"

Tool result:
{json.dumps(tool_result, indent=2)}

Additional context from flight log:
{rag_context}

Provide a comprehensive, clear answer that:
1. Directly answers the user's question
2. Uses specific data from both sources
3. Provides relevant insights
4. Keeps the response concise and helpful

Response:"""

            response = requests.post(
                f"{self.llm_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()["response"].strip()
            else:
                # Fallback to tool result only
                return f"Analysis: {json.dumps(tool_result, indent=2)}"
                
        except Exception as e:
            return f"Tool result: {json.dumps(tool_result, indent=2)}"
    
    def _enhance_with_llm(self, analysis_result: Dict, task_context: TaskContext, agent_name: str) -> str:
        """Enhance agent analysis with LLM natural language response"""
        try:
            # Create prompt for LLM to interpret the analysis
            prompt = f"""You are a UAV expert interpreting analysis results from the {agent_name}.

User asked: "{task_context.user_message}"

Analysis results:
{json.dumps(analysis_result, indent=2)}

Provide a clear, concise response to the user's question based on these results. Focus on:
1. Direct answer to their question
2. Key insights from the data
3. Any safety considerations
4. Practical recommendations

Keep the response conversational and helpful."""

            response = requests.post(
                f"{self.llm_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()["response"].strip()
            else:
                # Fallback to structured response
                return self._format_structured_response(analysis_result, task_context)
                
        except Exception as e:
            return self._format_structured_response(analysis_result, task_context)
    
    def _format_structured_response(self, analysis_result: Dict, task_context: TaskContext) -> str:
        """Format structured response when LLM is unavailable"""
        if "error" in analysis_result:
            return f"❌ {analysis_result['error']}"
        
        response_parts = []
        
        # Add analysis type
        if "analysis_type" in analysis_result:
            response_parts.append(f"**{analysis_result['analysis_type'].replace('_', ' ').title()} Results:**")
        
        # Add key insights
        if "insights" in analysis_result:
            insights = analysis_result["insights"]
            if insights:
                response_parts.append("\n**Key Insights:**")
                for insight in insights:
                    response_parts.append(f"• {insight}")
        
        # Add data summary
        if "data" in analysis_result:
            data = analysis_result["data"]
            if isinstance(data, dict):
                response_parts.append(f"\n**Analysis completed** - {len(data)} data points processed")
        
        return "\n".join(response_parts) if response_parts else "Analysis completed successfully."
    
    def _handle_general_query(self, message: str, log_id: Optional[str]) -> Dict[str, Any]:
        """Handle general queries that don't match specialized agents"""
        try:
            prompt = f"""You are a helpful UAV/drone expert. Answer this question clearly and concisely:

Question: {message}

Provide practical, accurate information about UAVs, drones, flight operations, or aviation concepts."""

            response = requests.post(
                f"{self.llm_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "response": response.json()["response"].strip(),
                    "agent_used": "GeneralKnowledge",
                    "task_type": "general_knowledge",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "response": "I'm having trouble accessing the knowledge base right now. Please try again later.",
                    "error": True
                }
                
        except Exception as e:
            return {
                "response": f"General query processing failed: {str(e)}",
                "error": True
            }

# Legacy compatibility functions
def call_llm(prompt: str, temperature: float = 0.3) -> str:
    """Legacy LLM call function for backward compatibility"""
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
    except Exception as e:
        return f"Error: {str(e)}"

def chat(user_msg: str, log_id: Optional[str] = None, conversation_history: List[Dict[str, Any]] = None) -> str:
    """Legacy chat function - now routes through agent orchestrator"""
    orchestrator = AgentOrchestrator()
    result = orchestrator.process_request(user_msg, log_id)
    return result.get("response", "Sorry, I couldn't process your request.")

# Legacy tool functions for backward compatibility
def get_log_summary(log_id: str) -> Dict[str, Any]:
    analyzer = LOG_MANAGER.get_analyzer(log_id)
    return analyzer.get_summary() if analyzer else {"error": "Log not found"}

def get_highest_altitude(log_id: str) -> Dict[str, Any]:
    analyzer = LOG_MANAGER.get_analyzer(log_id)
    return analyzer.get_highest_altitude() if analyzer else {"error": "Log not found"}

def detect_gps_issues(log_id: str) -> Dict[str, Any]:
    analyzer = LOG_MANAGER.get_analyzer(log_id)
    return analyzer.detect_gps_issues() if analyzer else {"error": "Log not found"}

# Create global orchestrator instance
ORCHESTRATOR = AgentOrchestrator()

# Legacy agent class for backward compatibility
class SimpleAgent:
    def chat(self, message: str, log_id: Optional[str] = None) -> Dict[str, str]:
        result = ORCHESTRATOR.process_request(message, log_id)
        return {"response": result.get("response", "Processing failed")}

# Global agent instance
AGENT = SimpleAgent()