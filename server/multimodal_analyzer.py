# server/multimodal_analyzer.py
import os
import base64
import io
from typing import Dict, Any, Optional, List
from PIL import Image
import requests
import json
from datetime import datetime

class MultimodalDashboardAnalyzer:
    """Analyze monitoring dashboard images using multimodal AI capabilities"""
    
    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.vision_model = os.getenv("VISION_MODEL", "llava:latest")  # Multimodal model
        
        # Dashboard analysis prompts
        self.analysis_prompts = {
            "general": """
            Analyze this UAV monitoring dashboard image and provide insights about:
            1. Overall system health status
            2. Any warning indicators or alerts visible
            3. Key performance metrics displayed
            4. Recommended actions based on what you observe
            5. Any anomalies or concerning patterns
            
            Be specific about what you can see in the dashboard and provide actionable recommendations.
            """,
            
            "safety": """
            Focus on safety-critical aspects of this UAV dashboard:
            1. Are there any red alerts or warning indicators?
            2. What is the battery status and remaining flight time?
            3. Are GPS and navigation systems functioning properly?
            4. Any signs of system failures or degraded performance?
            5. Immediate safety recommendations
            """,
            
            "performance": """
            Analyze the performance metrics visible in this UAV dashboard:
            1. Flight performance indicators (speed, altitude, etc.)
            2. System resource utilization
            3. Communication signal strength
            4. Motor and propeller performance
            5. Efficiency metrics and optimization suggestions
            """,
            
            "troubleshooting": """
            Help troubleshoot any issues visible in this UAV dashboard:
            1. Identify any error messages or fault indicators
            2. Diagnose potential root causes of problems
            3. Suggest step-by-step troubleshooting procedures
            4. Recommend preventive maintenance actions
            5. When to abort mission vs continue flying
            """
        }
    
    def analyze_dashboard_image(self, image_data: bytes, analysis_type: str = "general") -> Dict[str, Any]:
        """Analyze a dashboard image using multimodal AI"""
        try:
            # Convert image to base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Get appropriate prompt
            prompt = self.analysis_prompts.get(analysis_type, self.analysis_prompts["general"])
            
            # Call multimodal model
            response = self._call_vision_model(image_b64, prompt)
            
            if "error" in response:
                return response
            
            # Extract insights and structure the response
            analysis_result = self._structure_analysis_response(response["analysis"], analysis_type)
            
            return {
                "analysis_type": analysis_type,
                "insights": analysis_result,
                "raw_analysis": response["analysis"],
                "timestamp": datetime.now().isoformat(),
                "model_used": self.vision_model,
                "status": "success"
            }
            
        except Exception as e:
            return {"error": f"Dashboard analysis failed: {str(e)}"}
    
    def _call_vision_model(self, image_b64: str, prompt: str) -> Dict[str, Any]:
        """Call Ollama vision model for image analysis"""
        try:
            payload = {
                "model": self.vision_model,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Lower temperature for more factual analysis
                    "top_p": 0.9
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=60  # Longer timeout for vision models
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {"analysis": result.get("response", "No analysis generated")}
            
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to connect to vision model: {str(e)}"}
        except Exception as e:
            return {"error": f"Vision model analysis failed: {str(e)}"}
    
    def _structure_analysis_response(self, raw_analysis: str, analysis_type: str) -> Dict[str, Any]:
        """Structure the raw analysis into organized insights"""
        
        # Basic structuring - in a real implementation, you might use NLP to extract specific sections
        structured = {
            "summary": self._extract_summary(raw_analysis),
            "key_findings": self._extract_key_findings(raw_analysis),
            "recommendations": self._extract_recommendations(raw_analysis),
            "alerts": self._extract_alerts(raw_analysis),
            "metrics": self._extract_metrics(raw_analysis)
        }
        
        # Add analysis-type specific structuring
        if analysis_type == "safety":
            structured["safety_status"] = self._assess_safety_status(raw_analysis)
            structured["critical_actions"] = self._extract_critical_actions(raw_analysis)
        
        elif analysis_type == "performance":
            structured["performance_score"] = self._assess_performance_score(raw_analysis)
            structured["optimization_tips"] = self._extract_optimization_tips(raw_analysis)
        
        elif analysis_type == "troubleshooting":
            structured["identified_issues"] = self._extract_issues(raw_analysis)
            structured["troubleshooting_steps"] = self._extract_troubleshooting_steps(raw_analysis)
        
        return structured
    
    def _extract_summary(self, text: str) -> str:
        """Extract a concise summary from the analysis"""
        lines = text.split('\n')
        # Look for summary-like content in the first few lines
        for line in lines[:5]:
            if len(line.strip()) > 50:  # Substantial content
                return line.strip()
        return "Dashboard analysis completed"
    
    def _extract_key_findings(self, text: str) -> List[str]:
        """Extract key findings from the analysis"""
        findings = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for numbered points or bullet points
            if (line.startswith(('1.', '2.', '3.', '4.', '5.', '-', '•')) and 
                len(line) > 10):
                # Clean up the finding
                finding = line.lstrip('123456789.-• ').strip()
                if finding:
                    findings.append(finding)
        
        return findings[:10]  # Limit to top 10 findings
    
    def _extract_recommendations(self, text: str) -> List[str]:
        """Extract recommendations from the analysis"""
        recommendations = []
        lines = text.split('\n')
        
        in_recommendations_section = False
        for line in lines:
            line = line.strip().lower()
            
            # Look for recommendation keywords
            if any(keyword in line for keyword in ['recommend', 'suggest', 'should', 'action']):
                in_recommendations_section = True
                # Extract the actual recommendation
                rec = line.split('recommend')[-1].split('suggest')[-1].strip()
                if len(rec) > 10:
                    recommendations.append(rec.capitalize())
            
            elif in_recommendations_section and line.startswith(('-', '•', '1.', '2.')):
                rec = line.lstrip('-•123456789. ').strip()
                if len(rec) > 10:
                    recommendations.append(rec.capitalize())
        
        return recommendations[:8]  # Limit to top 8 recommendations
    
    def _extract_alerts(self, text: str) -> List[Dict[str, str]]:
        """Extract alerts and warnings from the analysis"""
        alerts = []
        text_lower = text.lower()
        
        # Look for alert keywords
        alert_keywords = ['warning', 'alert', 'critical', 'error', 'fault', 'failure', 'danger']
        
        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower()
            for keyword in alert_keywords:
                if keyword in line_lower and len(line.strip()) > 15:
                    severity = "high" if keyword in ['critical', 'danger', 'failure'] else "medium"
                    alerts.append({
                        "message": line.strip(),
                        "severity": severity,
                        "type": keyword
                    })
                    break
        
        return alerts[:5]  # Limit to top 5 alerts
    
    def _extract_metrics(self, text: str) -> Dict[str, str]:
        """Extract numerical metrics mentioned in the analysis"""
        metrics = {}
        
        # Look for common UAV metrics patterns
        import re
        
        # Battery percentage
        battery_match = re.search(r'battery.*?(\d+)%', text.lower())
        if battery_match:
            metrics["battery_percentage"] = f"{battery_match.group(1)}%"
        
        # Altitude
        altitude_match = re.search(r'altitude.*?(\d+(?:\.\d+)?)\s*(m|ft|meter|feet)', text.lower())
        if altitude_match:
            metrics["altitude"] = f"{altitude_match.group(1)} {altitude_match.group(2)}"
        
        # Speed
        speed_match = re.search(r'speed.*?(\d+(?:\.\d+)?)\s*(m/s|mph|km/h)', text.lower())
        if speed_match:
            metrics["speed"] = f"{speed_match.group(1)} {speed_match.group(2)}"
        
        # GPS satellites
        gps_match = re.search(r'(\d+)\s*satellites?', text.lower())
        if gps_match:
            metrics["gps_satellites"] = gps_match.group(1)
        
        return metrics
    
    def _assess_safety_status(self, text: str) -> str:
        """Assess overall safety status from the analysis"""
        text_lower = text.lower()
        
        critical_keywords = ['critical', 'danger', 'emergency', 'abort', 'failure']
        warning_keywords = ['warning', 'caution', 'alert', 'concern']
        good_keywords = ['normal', 'good', 'healthy', 'stable', 'ok']
        
        if any(keyword in text_lower for keyword in critical_keywords):
            return "CRITICAL"
        elif any(keyword in text_lower for keyword in warning_keywords):
            return "WARNING"
        elif any(keyword in text_lower for keyword in good_keywords):
            return "GOOD"
        else:
            return "UNKNOWN"
    
    def _extract_critical_actions(self, text: str) -> List[str]:
        """Extract critical actions from safety analysis"""
        actions = []
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['immediately', 'urgent', 'critical', 'abort']):
                action = line.strip()
                if len(action) > 10:
                    actions.append(action)
        
        return actions[:5]
    
    def _assess_performance_score(self, text: str) -> str:
        """Assess performance score from analysis"""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in ['excellent', 'optimal', 'perfect']):
            return "EXCELLENT"
        elif any(keyword in text_lower for keyword in ['good', 'normal', 'stable']):
            return "GOOD"
        elif any(keyword in text_lower for keyword in ['fair', 'average', 'moderate']):
            return "FAIR"
        elif any(keyword in text_lower for keyword in ['poor', 'degraded', 'suboptimal']):
            return "POOR"
        else:
            return "UNKNOWN"
    
    def _extract_optimization_tips(self, text: str) -> List[str]:
        """Extract optimization tips from performance analysis"""
        tips = []
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['optimize', 'improve', 'enhance', 'better']):
                tip = line.strip()
                if len(tip) > 15:
                    tips.append(tip)
        
        return tips[:6]
    
    def _extract_issues(self, text: str) -> List[str]:
        """Extract identified issues from troubleshooting analysis"""
        issues = []
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['issue', 'problem', 'fault', 'error']):
                issue = line.strip()
                if len(issue) > 10:
                    issues.append(issue)
        
        return issues[:5]
    
    def _extract_troubleshooting_steps(self, text: str) -> List[str]:
        """Extract troubleshooting steps from analysis"""
        steps = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for step-like patterns
            if (line.startswith(('Step', 'step', '1.', '2.', '3.', 'First', 'Next', 'Then')) and 
                len(line) > 15):
                step = line.lstrip('Step step123456789. ').strip()
                if step:
                    steps.append(step.capitalize())
        
        return steps[:8]
    
    def batch_analyze_dashboard(self, image_data: bytes) -> Dict[str, Any]:
        """Perform all types of analysis on a dashboard image"""
        try:
            results = {}
            
            # Perform all analysis types
            for analysis_type in self.analysis_prompts.keys():
                result = self.analyze_dashboard_image(image_data, analysis_type)
                if "error" not in result:
                    results[analysis_type] = result
                else:
                    results[analysis_type] = {"error": result["error"]}
            
            # Generate comprehensive summary
            comprehensive_summary = self._generate_comprehensive_summary(results)
            
            return {
                "individual_analyses": results,
                "comprehensive_summary": comprehensive_summary,
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }
            
        except Exception as e:
            return {"error": f"Batch analysis failed: {str(e)}"}
    
    def _generate_comprehensive_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a comprehensive summary from all analysis types"""
        summary = {
            "overall_status": "UNKNOWN",
            "priority_actions": [],
            "key_insights": [],
            "safety_assessment": "UNKNOWN"
        }
        
        # Aggregate insights from all analyses
        all_findings = []
        all_recommendations = []
        all_alerts = []
        
        for analysis_type, result in results.items():
            if "error" not in result and "insights" in result:
                insights = result["insights"]
                all_findings.extend(insights.get("key_findings", []))
                all_recommendations.extend(insights.get("recommendations", []))
                all_alerts.extend(insights.get("alerts", []))
                
                # Update safety assessment
                if "safety_status" in insights:
                    summary["safety_assessment"] = insights["safety_status"]
        
        # Deduplicate and prioritize
        summary["key_insights"] = list(set(all_findings))[:8]
        summary["priority_actions"] = list(set(all_recommendations))[:6]
        
        # Determine overall status based on alerts
        if any(alert.get("severity") == "high" for alert in all_alerts):
            summary["overall_status"] = "CRITICAL"
        elif any(alert.get("severity") == "medium" for alert in all_alerts):
            summary["overall_status"] = "WARNING"
        else:
            summary["overall_status"] = "NORMAL"
        
        return summary

# Global multimodal analyzer instance
MULTIMODAL_ANALYZER = MultimodalDashboardAnalyzer() 