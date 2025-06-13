# server/rag_engine.py
import os
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.schema import Document
from langchain_ollama import OllamaLLM
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import numpy as np
import pandas as pd
from core import LOG_MANAGER, LogAnalyzer

class UAVLogRAGEngine:
    """Advanced RAG engine for UAV log analysis with vector database"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=persist_directory)
        self.collection_name = "uav_logs"
        
        # Initialize LangChain components
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        # Initialize Ollama LLM
        self.llm = OllamaLLM(
            model=os.getenv("OLLAMA_MODEL", "phi3:mini"),
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434")
        )
        
        # Initialize vector store
        self.vectorstore = None
        self._initialize_vectorstore()
        
        # Knowledge base for UAV-specific insights
        self.uav_knowledge = self._load_uav_knowledge()
    
    def _initialize_vectorstore(self):
        """Initialize or load existing vector store"""
        try:
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
        except Exception as e:
            print(f"Error initializing vector store: {e}")
            # Create new collection if it doesn't exist
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
    
    def _load_uav_knowledge(self) -> Dict[str, Any]:
        """Load UAV domain knowledge for enhanced analysis"""
        return {
            "flight_modes": {
                "MANUAL": "Direct pilot control, no autopilot assistance",
                "STABILIZE": "Autopilot assists with attitude control",
                "ALT_HOLD": "Maintains altitude automatically",
                "LOITER": "Maintains position and altitude",
                "RTL": "Return to Launch mode",
                "AUTO": "Follows pre-programmed mission",
                "GUIDED": "Accepts commands from ground station",
                "LAND": "Automated landing sequence"
            },
            "critical_parameters": {
                "battery_voltage": {"min": 10.5, "warning": 11.1, "normal": 12.6},
                "gps_hdop": {"excellent": 1.0, "good": 2.0, "poor": 5.0},
                "vibration": {"low": 30, "medium": 60, "high": 90},
                "temperature": {"min": -10, "max": 60, "optimal": 25}
            },
            "error_patterns": {
                "gps_glitch": ["GPS_GLITCH", "GPS_FAILSAFE", "EKF_CHECK"],
                "vibration_issues": ["VIBRATION", "IMU_MISMATCH", "COMPASS_VARIANCE"],
                "power_issues": ["BATTERY_FAILSAFE", "LOW_VOLTAGE", "POWER_STATUS"],
                "sensor_failures": ["SENSOR_HEALTH", "AHRS_VARIANCE", "MAG_FIELD"]
            }
        }
    
    def process_log_for_rag(self, log_id: str) -> Dict[str, Any]:
        """Process a log file and add it to the vector database"""
        try:
            analyzer = LOG_MANAGER.get_analyzer(log_id)
            if not analyzer:
                return {"error": "Log not found"}
            
            # Extract comprehensive log data
            log_data = self._extract_comprehensive_data(analyzer)
            
            # Create documents for vector storage
            documents = self._create_documents(log_data, log_id)
            
            # Add to vector store
            if documents:
                self.vectorstore.add_documents(documents)
                self.vectorstore.persist()
            
            # Perform advanced analysis
            analysis_results = self._perform_advanced_analysis(log_data)
            
            return {
                "log_id": log_id,
                "documents_created": len(documents),
                "analysis": analysis_results,
                "status": "success"
            }
            
        except Exception as e:
            return {"error": f"Failed to process log for RAG: {str(e)}"}
    
    def _extract_comprehensive_data(self, analyzer: LogAnalyzer) -> Dict[str, Any]:
        """Extract comprehensive data from log for analysis"""
        messages = analyzer.parser.get_messages()
        
        # Group messages by type
        grouped_messages = {}
        for msg in messages:
            msg_type = msg.msg_type
            if msg_type not in grouped_messages:
                grouped_messages[msg_type] = []
            grouped_messages[msg_type].append(msg)
        
        # Extract key metrics
        flight_data = {
            "summary": analyzer.get_summary(),
            "altitude_analysis": analyzer.get_highest_altitude(),
            "gps_analysis": analyzer.detect_gps_issues(),
            "flight_modes": self._extract_flight_modes(grouped_messages),
            "battery_analysis": self._extract_battery_data(grouped_messages),
            "vibration_analysis": self._extract_vibration_data(grouped_messages),
            "error_analysis": self._extract_errors_and_events(grouped_messages),
            "performance_metrics": self._calculate_performance_metrics(grouped_messages)
        }
        
        return flight_data
    
    def _extract_flight_modes(self, grouped_messages: Dict) -> Dict[str, Any]:
        """Extract flight mode changes and analysis"""
        mode_messages = grouped_messages.get("MODE", [])
        if not mode_messages:
            return {"error": "No flight mode data found"}
        
        mode_changes = []
        for msg in mode_messages:
            mode_num = msg.data.get("Mode", 0)
            mode_name = self._get_mode_name(mode_num)
            mode_changes.append({
                "timestamp": msg.timestamp,
                "mode_number": mode_num,
                "mode_name": mode_name,
                "description": self.uav_knowledge["flight_modes"].get(mode_name, "Unknown mode")
            })
        
        return {
            "total_mode_changes": len(mode_changes),
            "mode_changes": mode_changes,
            "unique_modes": list(set(change["mode_name"] for change in mode_changes))
        }
    
    def _extract_battery_data(self, grouped_messages: Dict) -> Dict[str, Any]:
        """Extract and analyze battery performance"""
        battery_messages = grouped_messages.get("BATTERY_STATUS", []) or grouped_messages.get("BAT", [])
        if not battery_messages:
            return {"error": "No battery data found"}
        
        voltages = []
        currents = []
        remaining = []
        
        for msg in battery_messages:
            voltage = msg.data.get("Volt", 0) or msg.data.get("VoltR", 0)
            current = msg.data.get("Curr", 0) or msg.data.get("CurrTot", 0)
            remain = msg.data.get("Remaining", 0)
            
            if voltage > 0:
                voltages.append(voltage)
            if current > 0:
                currents.append(current)
            if remain > 0:
                remaining.append(remain)
        
        analysis = {
            "min_voltage": min(voltages) if voltages else 0,
            "max_voltage": max(voltages) if voltages else 0,
            "avg_voltage": np.mean(voltages) if voltages else 0,
            "avg_current": np.mean(currents) if currents else 0,
            "max_current": max(currents) if currents else 0,
            "final_remaining": remaining[-1] if remaining else 0
        }
        
        # Add health assessment
        min_volt = analysis["min_voltage"]
        thresholds = self.uav_knowledge["critical_parameters"]["battery_voltage"]
        
        if min_volt < thresholds["min"]:
            analysis["health"] = "CRITICAL - Voltage too low"
        elif min_volt < thresholds["warning"]:
            analysis["health"] = "WARNING - Low voltage detected"
        else:
            analysis["health"] = "GOOD - Voltage within normal range"
        
        return analysis
    
    def _extract_vibration_data(self, grouped_messages: Dict) -> Dict[str, Any]:
        """Extract and analyze vibration data"""
        vibe_messages = grouped_messages.get("VIBE", [])
        if not vibe_messages:
            return {"error": "No vibration data found"}
        
        vibe_x = []
        vibe_y = []
        vibe_z = []
        
        for msg in vibe_messages:
            vibe_x.append(msg.data.get("VibeX", 0))
            vibe_y.append(msg.data.get("VibeY", 0))
            vibe_z.append(msg.data.get("VibeZ", 0))
        
        max_vibe = max(max(vibe_x), max(vibe_y), max(vibe_z)) if vibe_x else 0
        avg_vibe = np.mean([np.mean(vibe_x), np.mean(vibe_y), np.mean(vibe_z)]) if vibe_x else 0
        
        # Health assessment
        thresholds = self.uav_knowledge["critical_parameters"]["vibration"]
        if max_vibe > thresholds["high"]:
            health = "CRITICAL - High vibration detected"
        elif max_vibe > thresholds["medium"]:
            health = "WARNING - Elevated vibration"
        else:
            health = "GOOD - Normal vibration levels"
        
        return {
            "max_vibration": max_vibe,
            "avg_vibration": avg_vibe,
            "max_x": max(vibe_x) if vibe_x else 0,
            "max_y": max(vibe_y) if vibe_y else 0,
            "max_z": max(vibe_z) if vibe_z else 0,
            "health": health
        }
    
    def _extract_errors_and_events(self, grouped_messages: Dict) -> Dict[str, Any]:
        """Extract and categorize errors and events"""
        error_messages = grouped_messages.get("ERR", []) + grouped_messages.get("EV", [])
        
        if not error_messages:
            return {"no_errors": True, "message": "No errors or events found"}
        
        categorized_errors = {
            "gps_issues": [],
            "vibration_issues": [],
            "power_issues": [],
            "sensor_failures": [],
            "other_errors": []
        }
        
        for msg in error_messages:
            error_text = str(msg.data)
            
            # Categorize based on error patterns
            categorized = False
            for category, patterns in self.uav_knowledge["error_patterns"].items():
                if any(pattern in error_text.upper() for pattern in patterns):
                    categorized_errors[category].append({
                        "timestamp": msg.timestamp,
                        "message": error_text,
                        "type": msg.msg_type
                    })
                    categorized = True
                    break
            
            if not categorized:
                categorized_errors["other_errors"].append({
                    "timestamp": msg.timestamp,
                    "message": error_text,
                    "type": msg.msg_type
                })
        
        return categorized_errors
    
    def _calculate_performance_metrics(self, grouped_messages: Dict) -> Dict[str, Any]:
        """Calculate advanced performance metrics"""
        gps_messages = grouped_messages.get("GPS", [])
        attitude_messages = grouped_messages.get("ATT", [])
        
        metrics = {}
        
        # GPS performance
        if gps_messages:
            hdop_values = [msg.data.get("HDop", 0) for msg in gps_messages if msg.data.get("HDop", 0) > 0]
            if hdop_values:
                metrics["gps_performance"] = {
                    "avg_hdop": np.mean(hdop_values),
                    "max_hdop": max(hdop_values),
                    "min_hdop": min(hdop_values)
                }
        
        # Attitude stability
        if attitude_messages:
            roll_values = [msg.data.get("Roll", 0) for msg in attitude_messages]
            pitch_values = [msg.data.get("Pitch", 0) for msg in attitude_messages]
            
            metrics["attitude_stability"] = {
                "roll_variance": np.var(roll_values) if roll_values else 0,
                "pitch_variance": np.var(pitch_values) if pitch_values else 0,
                "max_roll": max(roll_values) if roll_values else 0,
                "max_pitch": max(pitch_values) if pitch_values else 0
            }
        
        return metrics
    
    def _get_mode_name(self, mode_num: int) -> str:
        """Convert mode number to name (simplified)"""
        mode_map = {
            0: "MANUAL", 1: "CIRCLE", 2: "STABILIZE", 3: "TRAINING",
            4: "ACRO", 5: "FLY_BY_WIRE_A", 6: "FLY_BY_WIRE_B", 7: "CRUISE",
            8: "AUTOTUNE", 10: "AUTO", 11: "RTL", 12: "LOITER", 15: "GUIDED"
        }
        return mode_map.get(mode_num, f"MODE_{mode_num}")
    
    def _create_documents(self, log_data: Dict[str, Any], log_id: str) -> List[Document]:
        """Create LangChain documents from log data"""
        documents = []
        
        # Create document for summary
        summary_text = f"""
        Flight Log Summary for {log_id}:
        Duration: {log_data['summary'].get('duration_seconds', 0)} seconds
        Total Messages: {log_data['summary'].get('total_messages', 0)}
        Message Types: {', '.join(log_data['summary'].get('message_types', []))}
        """
        
        documents.append(Document(
            page_content=summary_text,
            metadata={"log_id": log_id, "type": "summary", "timestamp": datetime.now().isoformat()}
        ))
        
        # Create documents for each analysis section
        for section, data in log_data.items():
            if isinstance(data, dict) and "error" not in data:
                content = f"{section.replace('_', ' ').title()} Analysis:\n{json.dumps(data, indent=2)}"
                documents.append(Document(
                    page_content=content,
                    metadata={"log_id": log_id, "type": section, "timestamp": datetime.now().isoformat()}
                ))
        
        return documents
    
    def query_logs(self, query: str, log_id: Optional[str] = None) -> Dict[str, Any]:
        """Query the vector database for log insights"""
        try:
            if not self.vectorstore:
                return {"error": "Vector store not initialized"}
            
            # Create retrieval QA chain
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5}),
                return_source_documents=True
            )
            
            # Create extremely restrictive prompt
            enhanced_query = f"""Answer this question using only the flight log data provided. Give only the direct answer with no extra text.

Rules:
- Give ONLY the numerical answer with units
- Do NOT mention data sources, snippets, or analysis
- Do NOT add dates, times, or context unless specifically asked
- Do NOT explain your reasoning

Question: {query}

Direct answer:"""
            
            # Execute query
            result = qa_chain({"query": enhanced_query})
            
            return {
                "answer": result["result"],
                "source_documents": [
                    {
                        "content": doc.page_content[:200] + "...",
                        "metadata": doc.metadata
                    }
                    for doc in result["source_documents"]
                ],
                "query": query
            }
            
        except Exception as e:
            return {"error": f"Query failed: {str(e)}"}
    
    def generate_flight_report(self, log_id: str) -> Dict[str, Any]:
        """Generate a comprehensive flight report using RAG"""
        try:
            # Process log if not already in vector store
            self.process_log_for_rag(log_id)
            
            # Generate comprehensive report using multiple queries
            report_sections = {}
            
            queries = [
                "What was the overall flight performance and any issues detected?",
                "Analyze the battery performance and power consumption during the flight",
                "What flight modes were used and were there any mode changes?",
                "Were there any GPS or navigation issues during the flight?",
                "Analyze vibration levels and mechanical health indicators",
                "What safety recommendations can you provide based on this flight?"
            ]
            
            for i, query in enumerate(queries):
                section_name = f"section_{i+1}"
                result = self.query_logs(query, log_id)
                if "error" not in result:
                    report_sections[section_name] = {
                        "title": query,
                        "analysis": result["answer"]
                    }
            
            return {
                "log_id": log_id,
                "report_sections": report_sections,
                "generated_at": datetime.now().isoformat(),
                "status": "success"
            }
            
        except Exception as e:
            return {"error": f"Failed to generate report: {str(e)}"}
    
    def _perform_advanced_analysis(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform advanced analysis on the extracted log data"""
        try:
            analysis = {
                "flight_summary": {
                    "duration": log_data["summary"].get("duration_seconds", 0),
                    "total_messages": log_data["summary"].get("total_messages", 0),
                    "message_types_count": len(log_data["summary"].get("message_types", []))
                },
                "safety_assessment": self._assess_flight_safety(log_data),
                "performance_score": self._calculate_performance_score(log_data),
                "recommendations": self._generate_recommendations(log_data)
            }
            
            return analysis
            
        except Exception as e:
            return {"error": f"Advanced analysis failed: {str(e)}"}
    
    def _assess_flight_safety(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall flight safety based on log data"""
        safety_score = 100
        issues = []
        
        # Check battery health
        battery_data = log_data.get("battery_analysis", {})
        if "CRITICAL" in battery_data.get("health", ""):
            safety_score -= 30
            issues.append("Critical battery voltage detected")
        elif "WARNING" in battery_data.get("health", ""):
            safety_score -= 15
            issues.append("Low battery voltage warning")
        
        # Check vibration levels
        vibe_data = log_data.get("vibration_analysis", {})
        if "CRITICAL" in vibe_data.get("health", ""):
            safety_score -= 25
            issues.append("High vibration levels detected")
        elif "WARNING" in vibe_data.get("health", ""):
            safety_score -= 10
            issues.append("Elevated vibration levels")
        
        # Check GPS issues
        gps_data = log_data.get("gps_analysis", {})
        if gps_data.get("signal_loss_events", 0) > 0:
            safety_score -= 20
            issues.append(f"GPS signal loss events: {gps_data['signal_loss_events']}")
        
        # Check for errors
        error_data = log_data.get("error_analysis", {})
        if not error_data.get("no_errors", False):
            safety_score -= 15
            issues.append("Errors or events detected in flight log")
        
        safety_level = "EXCELLENT" if safety_score >= 90 else \
                      "GOOD" if safety_score >= 75 else \
                      "FAIR" if safety_score >= 60 else \
                      "POOR"
        
        return {
            "safety_score": max(0, safety_score),
            "safety_level": safety_level,
            "issues": issues,
            "assessment": f"Flight safety rated as {safety_level} with score {safety_score}/100"
        }
    
    def _calculate_performance_score(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall performance score"""
        performance_score = 100
        
        # Factor in flight duration (longer flights are generally better)
        duration = log_data["summary"].get("duration_seconds", 0)
        if duration < 30:
            performance_score -= 20
        elif duration > 300:  # 5+ minutes is good
            performance_score += 5
        
        # Factor in altitude performance
        altitude_data = log_data.get("altitude_analysis", {})
        if altitude_data.get("highest_altitude_m", 0) > 100:
            performance_score += 10
        
        # Factor in GPS performance
        gps_data = log_data.get("gps_analysis", {})
        if gps_data.get("poor_signal_events", 0) == 0:
            performance_score += 10
        
        return {
            "performance_score": min(100, max(0, performance_score)),
            "duration_factor": duration,
            "altitude_achieved": altitude_data.get("highest_altitude_m", 0),
            "gps_quality": "Good" if gps_data.get("poor_signal_events", 0) == 0 else "Poor"
        }
    
    def _generate_recommendations(self, log_data: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on log analysis"""
        recommendations = []
        
        # Battery recommendations
        battery_data = log_data.get("battery_analysis", {})
        if "CRITICAL" in battery_data.get("health", ""):
            recommendations.append("🔋 URGENT: Check battery health and replace if necessary")
        elif "WARNING" in battery_data.get("health", ""):
            recommendations.append("🔋 Monitor battery voltage closely on future flights")
        
        # Vibration recommendations
        vibe_data = log_data.get("vibration_analysis", {})
        if "CRITICAL" in vibe_data.get("health", ""):
            recommendations.append("⚠️ Check propeller balance and motor mounts for vibration issues")
        elif "WARNING" in vibe_data.get("health", ""):
            recommendations.append("🔧 Consider propeller balancing to reduce vibration")
        
        # GPS recommendations
        gps_data = log_data.get("gps_analysis", {})
        if gps_data.get("signal_loss_events", 0) > 0:
            recommendations.append("📡 Avoid flying in areas with poor GPS reception")
        
        # General recommendations
        duration = log_data["summary"].get("duration_seconds", 0)
        if duration < 60:
            recommendations.append("⏱️ Consider longer test flights to better assess performance")
        
        if not recommendations:
            recommendations.append("✅ Flight performance looks good - no specific recommendations")
        
        return recommendations

# Global RAG engine instance
RAG_ENGINE = UAVLogRAGEngine() 