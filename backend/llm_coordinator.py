import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
import requests
from function_calling import FunctionCallingManager

logger = logging.getLogger(__name__)

class LLMCoordinator:
    """Coordinates LLM interactions with intelligent tool use"""
    
    def __init__(self, function_manager: FunctionCallingManager, ollama_base_url: str = "http://localhost:11434"):
        self.function_manager = function_manager
        self.ollama_base_url = ollama_base_url
        self.model = "phi3:mini"
        
    def process_user_question(self, question: str, log_id: str) -> Dict[str, Any]:
        """Process a user question with intelligent tool coordination"""
        try:
            # Step 1: Let LLM analyze the question and decide which tools to use
            tool_plan = self._create_tool_execution_plan(question, log_id)
            
            # Step 2: Execute the planned tools
            tool_results = self._execute_tools(tool_plan)
            
            # Step 3: Let LLM synthesize the results into a final answer
            final_answer = self._synthesize_answer(question, tool_results)
            
            return {
                "answer": final_answer,
                "tool_plan": tool_plan,
                "tool_results": tool_results,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error in LLM coordination: {e}")
            return {
                "answer": f"I encountered an error while analyzing your question: {str(e)}",
                "error": str(e),
                "success": False
            }
    
    def _create_tool_execution_plan(self, question: str, log_id: str) -> List[Dict[str, Any]]:
        """Let LLM create a plan for which tools to use"""
        
        planning_prompt = f"""You are a UAV flight log analysis expert. A user has asked: "{question}"

You have access to these analysis tools:
1. get_log_summary - Get basic flight info and overview
2. analyze_battery_performance - Analyze battery voltage, current, consumption
3. analyze_flight_path - Analyze GPS coordinates, altitude, distance
4. analyze_attitude_control - Analyze roll, pitch, yaw stability
5. detect_flight_events - Find mode changes, errors, critical events
6. get_message_statistics - Get detailed statistics for specific message types
7. analyze_correlations - Find correlations between different parameters
8. check_system_health - Overall system health assessment
9. analyze_gps_quality - GPS signal quality and satellite count
10. get_performance_metrics - Calculate efficiency, stability, control metrics

Based on the user's question, create an execution plan. Output ONLY a JSON array of tool calls needed, in order of execution.

Example format:
[
    {{"function": "get_log_summary", "params": {{"log_id": "{log_id}"}}, "reason": "Need basic flight overview"}},
    {{"function": "analyze_battery_performance", "params": {{"log_id": "{log_id}", "focus": "voltage"}}, "reason": "User asked about battery"}}
]

User question: "{question}"
Log ID: "{log_id}"

Respond with ONLY the JSON array, no other text:"""

        try:
            response = self._call_ollama(planning_prompt)
            
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
                return plan
            else:
                # Fallback plan if JSON parsing fails
                return self._create_fallback_plan(question, log_id)
                
        except Exception as e:
            logger.warning(f"Failed to create tool plan: {e}, using fallback")
            return self._create_fallback_plan(question, log_id)
    
    def _create_fallback_plan(self, question: str, log_id: str) -> List[Dict[str, Any]]:
        """Create a fallback plan based on keyword matching"""
        plan = []
        question_lower = question.lower()
        
        # Always start with basic summary
        plan.append({
            "function": "get_log_summary",
            "params": {"log_id": log_id},
            "reason": "Get basic flight overview"
        })
        
        # Battery-related questions
        if any(word in question_lower for word in ['battery', 'voltage', 'current', 'power', 'consumption']):
            plan.append({
                "function": "analyze_battery_performance",
                "params": {"log_id": log_id},
                "reason": "User asked about battery performance"
            })
        
        # Flight path questions
        if any(word in question_lower for word in ['flight', 'path', 'route', 'gps', 'altitude', 'distance', 'coordinate']):
            plan.append({
                "function": "analyze_flight_path",
                "params": {"log_id": log_id},
                "reason": "User asked about flight path"
            })
        
        # Control/stability questions
        if any(word in question_lower for word in ['control', 'stability', 'roll', 'pitch', 'yaw', 'attitude']):
            plan.append({
                "function": "analyze_attitude_control",
                "params": {"log_id": log_id},
                "reason": "User asked about flight control"
            })
        
        # Event/problem questions
        if any(word in question_lower for word in ['error', 'problem', 'issue', 'event', 'warning', 'fail']):
            plan.append({
                "function": "detect_flight_events",
                "params": {"log_id": log_id},
                "reason": "User asked about problems or events"
            })
        
        # Health check questions
        if any(word in question_lower for word in ['health', 'overall', 'system', 'status', 'check']):
            plan.append({
                "function": "check_system_health",
                "params": {"log_id": log_id},
                "reason": "User asked about system health"
            })
        
        # Performance questions
        if any(word in question_lower for word in ['performance', 'efficiency', 'metric']):
            plan.append({
                "function": "get_performance_metrics",
                "params": {"log_id": log_id},
                "reason": "User asked about performance"
            })
        
        # If no specific keywords, add event detection as catch-all
        if len(plan) == 1:  # Only summary so far
            plan.append({
                "function": "detect_flight_events",
                "params": {"log_id": log_id},
                "reason": "General analysis for unknown question type"
            })
        
        return plan
    
    def _execute_tools(self, tool_plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute the planned tools and collect results"""
        results = {}
        
        for i, tool_call in enumerate(tool_plan):
            function_name = tool_call.get("function")
            params = tool_call.get("params", {})
            reason = tool_call.get("reason", "")
            
            try:
                logger.info(f"Executing tool {i+1}/{len(tool_plan)}: {function_name} - {reason}")
                result = self.function_manager.execute_function(function_name, **params)
                results[f"tool_{i+1}_{function_name}"] = {
                    "function": function_name,
                    "reason": reason,
                    "result": result,
                    "success": "error" not in result
                }
                
            except Exception as e:
                logger.error(f"Tool execution failed for {function_name}: {e}")
                results[f"tool_{i+1}_{function_name}"] = {
                    "function": function_name,
                    "reason": reason,
                    "result": {"error": f"Tool execution failed: {str(e)}"},
                    "success": False
                }
        
        return results
    
    def _synthesize_answer(self, question: str, tool_results: Dict[str, Any]) -> str:
        """Let LLM synthesize tool results into a coherent answer"""
        
        # Prepare tool results summary for LLM
        results_summary = self._create_results_summary(tool_results)
        
        synthesis_prompt = f"""You are an expert UAV flight log analyst. A user asked: "{question}"

I executed several analysis tools and got the following results:

{results_summary}

Based on these tool results, provide a comprehensive, helpful answer to the user's question. 

Guidelines:
1. Be specific and cite the actual data from the analysis
2. If there are concerning findings, highlight them clearly
3. Provide practical recommendations when appropriate
4. Keep the answer conversational but informative
5. If some tools failed, work with the available data
6. Structure your response logically

User's question: "{question}"

Your response:"""

        try:
            response = self._call_ollama(synthesis_prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to synthesize answer: {e}")
            # Fallback: create a basic summary from tool results
            return self._create_fallback_answer(tool_results)
    
    def _create_results_summary(self, tool_results: Dict[str, Any]) -> str:
        """Create a formatted summary of tool results for the LLM"""
        summary_parts = []
        
        for tool_key, tool_data in tool_results.items():
            function_name = tool_data["function"]
            reason = tool_data["reason"]
            result = tool_data["result"]
            success = tool_data["success"]
            
            if success:
                insights = result.get("insights", "No specific insights")
                summary_parts.append(f"""
TOOL: {function_name}
PURPOSE: {reason}
INSIGHTS: {insights}
DATA: {json.dumps(result, indent=2)}
""")
            else:
                error = result.get("error", "Unknown error")
                summary_parts.append(f"""
TOOL: {function_name}
PURPOSE: {reason}
STATUS: FAILED - {error}
""")
        
        return "\n".join(summary_parts)
    
    def _create_fallback_answer(self, tool_results: Dict[str, Any]) -> str:
        """Create a fallback answer if LLM synthesis fails"""
        insights = []
        
        for tool_data in tool_results.values():
            if tool_data["success"]:
                result = tool_data["result"]
                if "insights" in result:
                    insights.append(result["insights"])
        
        if insights:
            return "Based on the analysis:\n\n" + "\n\n".join(insights)
        else:
            return "I was able to analyze the flight log but encountered some issues with generating insights. Please try rephrasing your question or asking about specific aspects like battery performance, flight path, or system health."
    
    def _call_ollama(self, prompt: str) -> str:
        """Make a call to Ollama LLM"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for more consistent tool planning
                    "top_p": 0.9,
                    "top_k": 40
                }
            }
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()["response"]
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                
        except requests.RequestException as e:
            raise Exception(f"Failed to connect to Ollama: {str(e)}")
        except Exception as e:
            raise Exception(f"LLM call failed: {str(e)}")

class IterativeAnalysisCoordinator:
    """Handles iterative analysis for complex questions"""
    
    def __init__(self, llm_coordinator: LLMCoordinator):
        self.llm_coordinator = llm_coordinator
        
    def process_complex_question(self, question: str, log_id: str, max_iterations: int = 3) -> Dict[str, Any]:
        """Process complex questions that might need multiple analysis rounds"""
        
        all_results = []
        current_question = question
        
        for iteration in range(max_iterations):
            logger.info(f"Starting analysis iteration {iteration + 1}")
            
            # Process current question
            result = self.llm_coordinator.process_user_question(current_question, log_id)
            all_results.append(result)
            
            if not result["success"]:
                break
                
            # Check if we need follow-up analysis
            follow_up = self._determine_follow_up(question, result, iteration)
            
            if not follow_up:
                break  # No more follow-up needed
            
            current_question = follow_up
            
        # Synthesize all iterations into final answer
        final_answer = self._synthesize_iterative_results(question, all_results)
        
        return {
            "answer": final_answer,
            "iterations": all_results,
            "total_iterations": len(all_results),
            "success": True
        }
    
    def _determine_follow_up(self, original_question: str, current_result: Dict[str, Any], iteration: int) -> Optional[str]:
        """Determine if follow-up analysis is needed"""
        
        # Check for indicators that more analysis is needed
        answer = current_result.get("answer", "")
        
        # Simple heuristics for follow-up
        if iteration == 0:
            # First iteration - check if we found any concerning issues
            if any(word in answer.lower() for word in ['error', 'critical', 'warning', 'problem', 'issue']):
                return "What specific problems or errors were detected in this flight log? Provide detailed analysis."
        
        elif iteration == 1:
            # Second iteration - check if we need performance analysis
            if 'performance' in original_question.lower() or 'efficiency' in original_question.lower():
                return "Calculate detailed performance metrics and correlations for this flight."
        
        return None  # No follow-up needed
    
    def _synthesize_iterative_results(self, original_question: str, all_results: List[Dict[str, Any]]) -> str:
        """Synthesize results from multiple iterations"""
        
        if len(all_results) == 1:
            return all_results[0].get("answer", "Analysis completed.")
        
        # Combine insights from all iterations
        combined_insights = []
        
        for i, result in enumerate(all_results):
            answer = result.get("answer", "")
            if answer:
                combined_insights.append(f"Analysis Phase {i+1}:\n{answer}")
        
        if combined_insights:
            return "\n\n" + "\n\n".join(combined_insights)
        else:
            return "Completed multi-phase analysis of the flight log." 