# server/enhanced_ai.py
import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from rag_engine import RAG_ENGINE
from multimodal_analyzer import MULTIMODAL_ANALYZER
from ai import AGENT  # Import existing agent
import requests

class EnhancedUAVAssistant:
    """Enhanced UAV assistant with RAG, multimodal, and advanced AI capabilities"""
    
    def __init__(self):
        self.rag_engine = RAG_ENGINE
        self.multimodal_analyzer = MULTIMODAL_ANALYZER
        self.base_agent = AGENT
        
        # Enhanced capabilities
        self.capabilities = {
            "log_analysis": "Advanced log file analysis with RAG-powered insights",
            "multimodal_dashboard": "Dashboard image analysis using computer vision",
            "predictive_analysis": "Predictive maintenance and failure analysis",
            "comparative_analysis": "Compare multiple flights and identify patterns",
            "safety_assessment": "Comprehensive safety and risk assessment",
            "performance_optimization": "Flight performance optimization recommendations"
        }
        
        # Analysis modes
        self.analysis_modes = {
            "quick": "Fast analysis with basic insights",
            "detailed": "Comprehensive analysis with RAG-powered deep insights",
            "expert": "Expert-level analysis with predictive recommendations",
            "safety_focused": "Safety-critical analysis with risk assessment"
        }
    
    def process_message(self, message: str, log_id: Optional[str] = None, 
                       analysis_mode: str = "detailed", context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process user message with enhanced AI capabilities"""
        try:
            # Determine the type of request
            request_type = self._classify_request(message, log_id, context)
            
            # Route to appropriate handler
            if request_type == "base_agent_query":
                return self._handle_base_agent_query(message, log_id)
            elif request_type == "rag_query":
                return self._handle_rag_query(message, log_id, analysis_mode)
            elif request_type == "multimodal_analysis":
                return self._handle_multimodal_request(message, context)
            elif request_type == "comparative_analysis":
                return self._handle_comparative_analysis(message, context)
            elif request_type == "predictive_analysis":
                return self._handle_predictive_analysis(message, log_id)
            elif request_type == "general_chat":
                return self._handle_general_chat(message)
            else:
                # Fall back to base agent
                return self.base_agent.chat(message, log_id)
                
        except Exception as e:
            return {
                "response": f"I encountered an error while processing your request: {str(e)}",
                "error": True,
                "timestamp": datetime.now().isoformat()
            }
    
    def _classify_request(self, message: str, log_id: Optional[str], context: Optional[Dict]) -> str:
        """Classify the type of request to route to appropriate handler"""
        message_lower = message.lower()
        
        # Check for multimodal requests
        if context and "image_data" in context:
            return "multimodal_analysis"
        
        # Check for comparative analysis
        if any(keyword in message_lower for keyword in ["compare", "comparison", "versus", "vs", "difference"]):
            return "comparative_analysis"
        
        # Check for predictive analysis
        if any(keyword in message_lower for keyword in ["predict", "forecast", "future", "trend", "maintenance"]):
            return "predictive_analysis"
        
        # STRICT: Route log-specific queries to RAG with concise responses
        if log_id and any(keyword in message_lower for keyword in [
            "altitude", "highest", "maximum", "speed", "battery", "gps", 
            "flight time", "duration", "this flight", "the flight", "log",
            "signal loss", "errors", "vibration", "mode", "messages"
        ]):
            return "rag_query"
        
        # General UAV questions (even with log_id present)
        if any(keyword in message_lower for keyword in [
            "what is", "what are", "how does", "how do", "define", "explain",
            "what is a uav", "what is a drone", "how does gps work"
        ]):
            return "general_chat"
        
        # Default to general chat
        return "general_chat"
    
    def _handle_rag_query(self, message: str, log_id: str, analysis_mode: str) -> Dict[str, Any]:
        """Handle queries using RAG engine for deep insights"""
        try:
            # First, ensure the log is processed in the RAG system
            rag_result = self.rag_engine.process_log_for_rag(log_id)
            
            if "error" in rag_result:
                return {
                    "response": f"❌ I couldn't process the log file for advanced analysis: {rag_result['error']}",
                    "error": True
                }
            
            # Query the RAG system
            query_result = self.rag_engine.query_logs(message, log_id)
            
            if "error" in query_result:
                return {
                    "response": f"❌ RAG query failed: {query_result['error']}",
                    "error": True
                }
            
            # Format concise response - no more verbose formatting
            response = self._format_concise_response(query_result)
            
            return {
                "response": response,
                "rag_powered": True,
                "source_documents": query_result.get("source_documents", []),
                "analysis_mode": analysis_mode,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "response": f"❌ RAG analysis failed: {str(e)}",
                "error": True
            }
    
    def _handle_multimodal_request(self, message: str, context: Dict) -> Dict[str, Any]:
        """Handle multimodal dashboard analysis requests"""
        try:
            image_data = context.get("image_data")
            if not image_data:
                return {
                    "response": "❌ No image data provided for dashboard analysis",
                    "error": True
                }
            
            # Determine analysis type from message
            analysis_type = "general"
            message_lower = message.lower()
            
            if any(keyword in message_lower for keyword in ["safety", "safe", "alert", "warning"]):
                analysis_type = "safety"
            elif any(keyword in message_lower for keyword in ["performance", "efficiency", "speed"]):
                analysis_type = "performance"
            elif any(keyword in message_lower for keyword in ["troubleshoot", "problem", "issue", "error"]):
                analysis_type = "troubleshooting"
            
            # Analyze the dashboard image
            analysis_result = self.multimodal_analyzer.analyze_dashboard_image(image_data, analysis_type)
            
            if "error" in analysis_result:
                return {
                    "response": f"❌ Dashboard analysis failed: {analysis_result['error']}",
                    "error": True
                }
            
            # Format the multimodal response
            response = self._format_multimodal_response(analysis_result, message)
            
            return {
                "response": response,
                "multimodal_analysis": analysis_result,
                "analysis_type": analysis_type,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "response": f"❌ Multimodal analysis failed: {str(e)}",
                "error": True
            }
    
    def _handle_comparative_analysis(self, message: str, context: Dict) -> Dict[str, Any]:
        """Handle comparative analysis between multiple flights"""
        try:
            log_ids = context.get("log_ids", [])
            if len(log_ids) < 2:
                return {
                    "response": "❌ Comparative analysis requires at least 2 flight logs. Please upload multiple log files.",
                    "error": True
                }
            
            # Perform comparative analysis
            comparison_results = []
            
            for log_id in log_ids:
                # Process each log with RAG
                rag_result = self.rag_engine.process_log_for_rag(log_id)
                if "error" not in rag_result:
                    comparison_results.append({
                        "log_id": log_id,
                        "analysis": rag_result["analysis"]
                    })
            
            if not comparison_results:
                return {
                    "response": "❌ Could not analyze any of the provided log files for comparison",
                    "error": True
                }
            
            # Generate comparative insights
            comparative_response = self._generate_comparative_insights(comparison_results, message)
            
            return {
                "response": comparative_response,
                "comparative_analysis": True,
                "logs_compared": len(comparison_results),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "response": f"❌ Comparative analysis failed: {str(e)}",
                "error": True
            }
    
    def _handle_predictive_analysis(self, message: str, log_id: str) -> Dict[str, Any]:
        """Handle predictive analysis and maintenance recommendations"""
        try:
            # Get comprehensive log analysis
            rag_result = self.rag_engine.process_log_for_rag(log_id)
            
            if "error" in rag_result:
                return {
                    "response": f"❌ Could not perform predictive analysis: {rag_result['error']}",
                    "error": True
                }
            
            # Generate predictive insights
            predictive_query = f"""
            Based on the flight data and trends, provide predictive analysis for:
            {message}
            
            Include:
            1. Potential future issues based on current trends
            2. Maintenance recommendations and timing
            3. Performance degradation predictions
            4. Safety risk assessment
            5. Optimization opportunities
            """
            
            prediction_result = self.rag_engine.query_logs(predictive_query, log_id)
            
            if "error" in prediction_result:
                return {
                    "response": f"❌ Predictive query failed: {prediction_result['error']}",
                    "error": True
                }
            
            # Format predictive response
            response = self._format_predictive_response(prediction_result, rag_result)
            
            return {
                "response": response,
                "predictive_analysis": True,
                "maintenance_recommendations": self._extract_maintenance_recommendations(prediction_result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "response": f"❌ Predictive analysis failed: {str(e)}",
                "error": True
            }
    
    def _handle_base_agent_query(self, message: str, log_id: str) -> Dict[str, Any]:
        """Handle log-specific queries using the new function calling base agent"""
        try:
            # Call the base agent with function calling capabilities
            base_response = self.base_agent.chat(message, log_id=log_id)
            
            # Format the response to match the enhanced AI structure
            return {
                "response": base_response.get("response", "No response generated"),
                "function_calling": True,
                "rag_powered": False,
                "source_documents": [],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "response": f"❌ Function calling analysis failed: {str(e)}",
                "error": True
            }
    
    def _handle_general_chat(self, message: str) -> Dict[str, Any]:
        """Handle general chat messages - NO log data should be used"""
        # Call base agent with NO log_id to ensure no log data contamination
        return self.base_agent.chat(message, log_id=None)
    
    def _format_expert_response(self, query_result: Dict, rag_result: Dict) -> str:
        """Format response for expert-level analysis"""
        response = f"🔬 **Expert Analysis**\n\n"
        response += f"**Deep Insights:** {query_result['answer']}\n\n"
        
        if rag_result.get("analysis"):
            analysis = rag_result["analysis"]
            response += "**Technical Details:**\n"
            
            # Add battery analysis if available
            if "battery_analysis" in analysis:
                battery = analysis["battery_analysis"]
                response += f"• Battery Performance: {battery.get('health', 'Unknown')}\n"
                response += f"• Voltage Range: {battery.get('min_voltage', 0):.1f}V - {battery.get('max_voltage', 0):.1f}V\n"
            
            # Add vibration analysis
            if "vibration_analysis" in analysis:
                vibe = analysis["vibration_analysis"]
                response += f"• Vibration Status: {vibe.get('health', 'Unknown')}\n"
                response += f"• Max Vibration: {vibe.get('max_vibration', 0):.1f}\n"
        
        response += "\n**📊 Data Sources:** RAG-powered analysis with vector database insights"
        return response
    
    def _format_safety_response(self, query_result: Dict, rag_result: Dict) -> str:
        """Format response for safety-focused analysis"""
        response = f"🛡️ **Safety Assessment**\n\n"
        response += f"**Analysis:** {query_result['answer']}\n\n"
        
        if rag_result.get("analysis"):
            analysis = rag_result["analysis"]
            
            # Safety-critical information
            response += "**Safety Status:**\n"
            
            if "error_analysis" in analysis:
                errors = analysis["error_analysis"]
                critical_errors = []
                
                for category, error_list in errors.items():
                    if error_list and category in ["gps_issues", "power_issues", "sensor_failures"]:
                        critical_errors.extend(error_list)
                
                if critical_errors:
                    response += f"⚠️ **{len(critical_errors)} Critical Issues Detected**\n"
                    for error in critical_errors[:3]:  # Show top 3
                        response += f"• {error.get('message', 'Unknown error')}\n"
                else:
                    response += "✅ No critical safety issues detected\n"
        
        response += "\n🔍 **Recommendation:** Review all safety parameters before next flight"
        return response
    
    def _format_concise_response(self, query_result: Dict) -> str:
        """Format extremely concise response with no tool talk"""
        # Just return the direct answer, no formatting or metadata
        return query_result.get('answer', 'No data available')
    
    def _format_multimodal_response(self, analysis_result: Dict, original_message: str) -> str:
        """Format response for multimodal dashboard analysis"""
        insights = analysis_result.get("insights", {})
        
        response = f"🖼️ **Dashboard Analysis**\n\n"
        response += f"**Summary:** {insights.get('summary', 'Dashboard analyzed successfully')}\n\n"
        
        # Key findings
        findings = insights.get("key_findings", [])
        if findings:
            response += "**Key Observations:**\n"
            for finding in findings[:5]:
                response += f"• {finding}\n"
            response += "\n"
        
        # Recommendations
        recommendations = insights.get("recommendations", [])
        if recommendations:
            response += "**Recommendations:**\n"
            for rec in recommendations[:4]:
                response += f"• {rec}\n"
            response += "\n"
        
        # Alerts
        alerts = insights.get("alerts", [])
        if alerts:
            response += "**⚠️ Alerts:**\n"
            for alert in alerts[:3]:
                severity_emoji = "🔴" if alert.get("severity") == "high" else "🟡"
                response += f"{severity_emoji} {alert.get('message', 'Alert detected')}\n"
        
        response += f"\n🤖 **Analysis Type:** {analysis_result.get('analysis_type', 'general').title()}"
        return response
    
    def _generate_comparative_insights(self, comparison_results: List[Dict], message: str) -> str:
        """Generate comparative insights between multiple flights"""
        response = f"📊 **Comparative Flight Analysis**\n\n"
        response += f"**Comparing {len(comparison_results)} flights:**\n\n"
        
        # Extract key metrics for comparison
        flight_summaries = []
        for result in comparison_results:
            analysis = result["analysis"]
            summary = analysis.get("summary", {})
            flight_summaries.append({
                "log_id": result["log_id"],
                "duration": summary.get("duration_seconds", 0),
                "messages": summary.get("total_messages", 0),
                "altitude": analysis.get("altitude_analysis", {}).get("max_altitude_m", 0),
                "battery": analysis.get("battery_analysis", {}).get("min_voltage", 0)
            })
        
        # Generate comparisons
        if flight_summaries:
            # Duration comparison
            durations = [f["duration"] for f in flight_summaries]
            response += f"**Flight Durations:** {min(durations):.0f}s - {max(durations):.0f}s\n"
            
            # Altitude comparison
            altitudes = [f["altitude"] for f in flight_summaries]
            response += f"**Max Altitudes:** {min(altitudes):.1f}m - {max(altitudes):.1f}m\n"
            
            # Battery comparison
            batteries = [f["battery"] for f in flight_summaries if f["battery"] > 0]
            if batteries:
                response += f"**Battery Performance:** {min(batteries):.1f}V - {max(batteries):.1f}V\n"
        
        response += "\n💡 **Insights:** Use this comparison to identify performance trends and optimization opportunities"
        return response
    
    def _format_predictive_response(self, prediction_result: Dict, rag_result: Dict) -> str:
        """Format response for predictive analysis"""
        response = f"🔮 **Predictive Analysis**\n\n"
        response += f"**Forecast:** {prediction_result['answer']}\n\n"
        
        # Add maintenance timeline
        response += "**🔧 Maintenance Schedule:**\n"
        response += "• Next inspection: Within 10 flight hours\n"
        response += "• Battery check: Every 25 cycles\n"
        response += "• Propeller inspection: Every 50 flight hours\n\n"
        
        response += "**📈 Trend Analysis:** Based on current flight data patterns"
        return response
    
    def _extract_maintenance_recommendations(self, prediction_result: Dict) -> List[str]:
        """Extract maintenance recommendations from predictive analysis"""
        recommendations = []
        answer = prediction_result.get("answer", "").lower()
        
        if "battery" in answer:
            recommendations.append("Monitor battery voltage trends")
        if "vibration" in answer:
            recommendations.append("Check propeller balance and motor mounts")
        if "gps" in answer:
            recommendations.append("Verify GPS antenna and compass calibration")
        
        return recommendations
    
    def generate_comprehensive_report(self, log_id: str) -> Dict[str, Any]:
        """Generate a comprehensive flight report using all AI capabilities"""
        try:
            # Generate RAG-powered report
            rag_report = self.rag_engine.generate_flight_report(log_id)
            
            if "error" in rag_report:
                return rag_report
            
            # Add predictive insights
            predictive_analysis = self._handle_predictive_analysis(
                "Provide maintenance and performance predictions", log_id
            )
            
            # Combine all insights
            comprehensive_report = {
                "log_id": log_id,
                "generated_at": datetime.now().isoformat(),
                "rag_analysis": rag_report,
                "predictive_insights": predictive_analysis,
                "capabilities_used": ["RAG", "Predictive Analysis", "Vector Database"],
                "report_type": "comprehensive",
                "status": "success"
            }
            
            return comprehensive_report
            
        except Exception as e:
            return {"error": f"Comprehensive report generation failed: {str(e)}"}

# Global enhanced assistant instance
ENHANCED_ASSISTANT = EnhancedUAVAssistant() 