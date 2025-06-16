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
    
    def process_frontend_data(self, log_id: str, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process flight data received from the frontend UAV Log Viewer"""
        try:
            print(f"Processing frontend data for log_id: {log_id}")
            
            # Create documents for vector storage from frontend data
            documents = self._create_documents_from_frontend_data(flight_data, log_id)
            print(f"Created {len(documents)} documents")
            
            # Add to vector store
            if documents:
                print("Adding documents to vector store...")
                self.vectorstore.add_documents(documents)
                try:
                    self.vectorstore.persist()
                    print("Documents persisted successfully")
                except Exception as persist_error:
                    print(f"Persistence warning (may be auto-persisted): {persist_error}")
                
                # Verify documents were added
                test_docs = self.vectorstore.similarity_search(f"log {log_id}", k=1)
                print(f"Verification: Found {len(test_docs)} documents after adding")
            else:
                print("No documents were created!")
            
            # Perform advanced analysis on the frontend data
            try:
                analysis_results = self._perform_advanced_analysis(flight_data)
            except Exception as analysis_error:
                print(f"Analysis error (non-critical): {analysis_error}")
                analysis_results = {"error": "Analysis skipped for frontend data", "details": str(analysis_error)}
            
            return {
                "log_id": log_id,
                "documents_created": len(documents),
                "analysis": analysis_results,
                "status": "success",
                "source": "frontend_sync"
            }
            
        except Exception as e:
            print(f"Error processing frontend data: {e}")
            return {"error": f"Failed to process frontend data for RAG: {str(e)}"}
    
    def _create_documents_from_frontend_data(self, flight_data: Dict[str, Any], log_id: str) -> List[Document]:
        """Create documents for vector storage from frontend flight data"""
        documents = []
        
        try:
            # Create summary document
            summary = flight_data.get("summary", {})
            if summary:
                summary_text = f"""
Flight Summary for Log {log_id}:
Duration: {summary.get('duration', 'N/A')} seconds
Maximum Altitude: {summary.get('maxAltitude', 'N/A')} meters
Total Distance: {summary.get('totalDistance', 'N/A')} meters
Trajectory Points: {summary.get('trajectoryPoints', 'N/A')}
Start Time: {summary.get('startTime', 'N/A')}
Vehicle Type: {flight_data.get('vehicle', 'Unknown')}
Log Type: {flight_data.get('logType', 'bin')}
"""
                documents.append(Document(
                    page_content=summary_text,
                    metadata={"log_id": log_id, "type": "flight_summary", "source": "frontend"}
                ))
            
            # Create flight mode document
            flight_modes = flight_data.get("flightModeChanges", [])
            if flight_modes:
                modes_text = f"Flight Mode Changes for Log {log_id}:\n"
                for i, mode_change in enumerate(flight_modes):
                    if len(mode_change) >= 2:
                        timestamp = mode_change[0]
                        mode_name = mode_change[1]
                        modes_text += f"Time {timestamp}ms: {mode_name}\n"
                
                documents.append(Document(
                    page_content=modes_text,
                    metadata={"log_id": log_id, "type": "flight_modes", "source": "frontend"}
                ))
            
            # Create trajectory analysis document
            trajectory = flight_data.get("trajectory", [])
            if trajectory and len(trajectory) > 0:
                start_point = trajectory[0] if len(trajectory[0]) >= 4 else [0, 0, 0, 0]
                end_point = trajectory[-1] if len(trajectory[-1]) >= 4 else [0, 0, 0, 0]
                
                trajectory_text = f"""
Trajectory Analysis for Log {log_id}:
Total GPS Points: {len(trajectory)}
Start Position: Latitude {start_point[1]}, Longitude {start_point[0]}, Altitude {start_point[2]}m
End Position: Latitude {end_point[1]}, Longitude {end_point[0]}, Altitude {end_point[2]}m
Start Time: {start_point[3]}ms
End Time: {end_point[3]}ms
Flight Duration: {(end_point[3] - start_point[3]) / 1000:.1f} seconds

Flight Path Quality: Good GPS tracking with {len(trajectory)} recorded positions
"""
                documents.append(Document(
                    page_content=trajectory_text,
                    metadata={"log_id": log_id, "type": "trajectory_analysis", "source": "frontend"}
                ))
            
            # Create events document
            events = flight_data.get("events", [])
            if events:
                events_text = f"Flight Events for Log {log_id}:\n"
                for event in events:
                    if hasattr(event, 'get') or isinstance(event, dict):
                        events_text += f"Event: {event}\n"
                    else:
                        events_text += f"Event: {str(event)}\n"
                
                documents.append(Document(
                    page_content=events_text,
                    metadata={"log_id": log_id, "type": "flight_events", "source": "frontend"}
                ))
            
            # Create text messages document
            text_messages = flight_data.get("textMessages", [])
            if text_messages:
                messages_text = f"Text Messages for Log {log_id}:\n"
                for msg in text_messages:
                    messages_text += f"Message: {msg}\n"
                
                documents.append(Document(
                    page_content=messages_text,
                    metadata={"log_id": log_id, "type": "text_messages", "source": "frontend"}
                ))
            
            return documents
            
        except Exception as e:
            print(f"Error creating documents from frontend data: {e}")
            return []
    
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
        """Create detailed, context-rich documents for vector storage with granular flight descriptions"""
        documents = []
        
        try:
            # Get the analyzer to access time-series data
            analyzer = LOG_MANAGER.get_analyzer(log_id)
            if not analyzer:
                return documents
            
            # Create enhanced summary document with rich context
            summary = log_data.get("summary", {})
            if "error" not in summary:
                summary_text = self._create_detailed_summary(summary, log_data, log_id)
                documents.append(Document(
                    page_content=summary_text,
                    metadata={"log_id": log_id, "type": "summary", "timestamp": datetime.now().isoformat()}
                ))
            
            # Create time-based chunks with comprehensive descriptions
            time_chunks = self._create_time_based_chunks(analyzer, log_id)
            documents.extend(time_chunks)
            
            # Create analysis documents with natural language descriptions
            analysis_docs = self._create_analysis_documents(log_data, log_id)
            documents.extend(analysis_docs)
            
            # Create event-based documents
            event_docs = self._create_event_documents(analyzer, log_id)
            documents.extend(event_docs)
            
        except Exception as e:
            print(f"Error creating documents: {e}")
        
        return documents
    
    def _create_detailed_summary(self, summary: Dict, log_data: Dict, log_id: str) -> str:
        """Create a comprehensive, natural language summary"""
        duration = summary.get('duration_seconds', 0)
        total_msgs = summary.get('total_messages', 0)
        
        # Get additional context
        altitude_data = log_data.get('altitude_analysis', {})
        battery_data = log_data.get('battery_analysis', {})
        gps_data = log_data.get('gps_analysis', {})
        
        summary_text = f"""Flight Log Analysis for {log_id}:

FLIGHT OVERVIEW:
This UAV flight lasted {duration:.1f} seconds ({duration/60:.1f} minutes) and recorded {total_msgs:,} total telemetry messages. The log contains data from {len(summary.get('message_types', []))} different message types including GPS positioning, battery status, attitude control, and system health monitoring.

ALTITUDE PERFORMANCE:
"""
        
        if 'error' not in altitude_data:
            max_alt = altitude_data.get('highest_altitude_m', 0)
            avg_alt = altitude_data.get('average_altitude_m', 0)
            alt_time = altitude_data.get('max_altitude_time_s', 0)
            summary_text += f"The aircraft reached a maximum altitude of {max_alt:.1f} meters at {alt_time:.1f} seconds into the flight. The average flight altitude was {avg_alt:.1f} meters. "
        
        summary_text += "\nBATTERY STATUS:\n"
        if 'error' not in battery_data:
            min_volt = battery_data.get('min_voltage', 0)
            max_volt = battery_data.get('max_voltage', 0)
            health = battery_data.get('health', 'Unknown')
            summary_text += f"Battery performance was rated as {health}. Voltage ranged from {min_volt:.1f}V to {max_volt:.1f}V throughout the flight. "
        
        summary_text += "\nGPS PERFORMANCE:\n"
        if 'error' not in gps_data:
            total_readings = gps_data.get('total_gps_readings', 0)
            signal_loss = gps_data.get('signal_loss_events', 0)
            poor_signal = gps_data.get('poor_signal_events', 0)
            summary_text += f"GPS system recorded {total_readings} position readings. There were {signal_loss} signal loss events and {poor_signal} poor signal quality events during the flight."
        
        return summary_text
    
    def _create_time_based_chunks(self, analyzer: LogAnalyzer, log_id: str) -> List[Document]:
        """Create detailed time-based chunks describing flight segments"""
        documents = []
        
        try:
            # Get time-series data
            gps_data = analyzer.get_gps_coords_series()
            battery_data = analyzer.get_battery_series()
            altitude_data = analyzer.get_altitude_series()
            mode_changes = analyzer.get_mode_changes()
            events = analyzer.get_significant_events()
            
            # Create 10-second chunks with rich descriptions
            summary = analyzer.get_summary()
            duration = summary.get('duration_seconds', 0)
            chunk_size = 10  # seconds
            
            for chunk_start in range(0, int(duration), chunk_size):
                chunk_end = min(chunk_start + chunk_size, duration)
                chunk_description = self._describe_flight_segment(
                    chunk_start, chunk_end, gps_data, battery_data, 
                    altitude_data, mode_changes, events, log_id
                )
                
                if chunk_description.strip():
                    documents.append(Document(
                        page_content=chunk_description,
                        metadata={
                            "log_id": log_id,
                            "type": "time_chunk",
                            "start_time_s": chunk_start,
                            "end_time_s": chunk_end,
                            "timestamp": datetime.now().isoformat()
                        }
                    ))
        
        except Exception as e:
            print(f"Error creating time chunks: {e}")
        
        return documents
    
    def _describe_flight_segment(self, start_time: float, end_time: float, 
                                gps_data: List, battery_data: List, altitude_data: List,
                                mode_changes: List, events: List, log_id: str) -> str:
        """Create detailed natural language description of a flight segment"""
        
        description = f"Flight segment from {start_time:.1f}s to {end_time:.1f}s in log {log_id}:\n\n"
        
        # Filter data for this time segment
        segment_gps = [d for d in gps_data if isinstance(d, dict) and start_time <= d.get('time_s', 0) <= end_time]
        segment_battery = [d for d in battery_data if isinstance(d, dict) and start_time <= d.get('time_s', 0) <= end_time]
        segment_altitude = [d for d in altitude_data if isinstance(d, dict) and start_time <= d.get('time_s', 0) <= end_time]
        segment_modes = [d for d in mode_changes if isinstance(d, dict) and start_time <= d.get('time_s', 0) <= end_time]
        segment_events = [d for d in events if isinstance(d, dict) and start_time <= d.get('time_s', 0) <= end_time]
        
        # GPS and position analysis
        if segment_gps:
            avg_lat = sum(d['latitude'] for d in segment_gps) / len(segment_gps)
            avg_lon = sum(d['longitude'] for d in segment_gps) / len(segment_gps)
            avg_alt = sum(d['altitude_m'] for d in segment_gps) / len(segment_gps)
            avg_hdop = sum(d['hdop'] for d in segment_gps) / len(segment_gps)
            avg_sats = sum(d['satellites'] for d in segment_gps) / len(segment_gps)
            avg_speed = sum(d['speed_ms'] for d in segment_gps) / len(segment_gps)
            
            description += f"POSITION: Aircraft was flying at approximately {avg_lat:.6f}°N, {avg_lon:.6f}°E at an average altitude of {avg_alt:.1f} meters. "
            description += f"GPS quality showed HDOP of {avg_hdop:.1f} with {avg_sats:.0f} satellites tracked. "
            description += f"Ground speed averaged {avg_speed:.1f} m/s ({avg_speed*3.6:.1f} km/h). "
            
            # Check GPS quality
            if avg_hdop > 3.0:
                description += "GPS signal quality was poor during this segment. "
            elif avg_hdop < 1.5:
                description += "GPS signal quality was excellent during this segment. "
        
        # Battery analysis
        if segment_battery:
            voltages = [d.get('voltage_v', 0) for d in segment_battery if d.get('voltage_v', 0) > 0]
            currents = [d.get('current_a', 0) for d in segment_battery if d.get('current_a', 0) > 0]
            
            if voltages:
                avg_voltage = sum(voltages) / len(voltages)
                description += f"\nBATTERY: Average voltage was {avg_voltage:.2f}V. "
                
                if avg_voltage < 11.1:
                    description += "Battery voltage was critically low. "
                elif avg_voltage < 11.8:
                    description += "Battery voltage was in warning range. "
            
            if currents:
                avg_current = sum(currents) / len(currents)
                description += f"Current draw averaged {avg_current:.1f}A. "
        
        # Flight mode changes
        if segment_modes:
            for mode_change in segment_modes:
                mode_name = mode_change.get('mode', 'Unknown')
                time_s = mode_change.get('time_s', 0)
                description += f"\nMODE CHANGE: At {time_s:.1f}s, flight mode changed to {mode_name}. "
        
        # Significant events
        if segment_events:
            for event in segment_events:
                event_type = event.get('type', 'unknown')
                severity = event.get('severity', 'unknown')
                message = event.get('message', 'No details')
                time_s = event.get('time_s', 0)
                description += f"\n{severity.upper()} {event_type.upper()}: At {time_s:.1f}s - {message}. "
        
        return description
    
    def _create_analysis_documents(self, log_data: Dict, log_id: str) -> List[Document]:
        """Create detailed analysis documents with natural language descriptions"""
        documents = []
        
        # Battery analysis document
        battery_data = log_data.get('battery_analysis', {})
        if 'error' not in battery_data:
            battery_text = f"""Battery Performance Analysis for {log_id}:

The battery system showed {battery_data.get('health', 'unknown')} performance throughout this flight. 
Voltage ranged from {battery_data.get('min_voltage', 0):.2f}V to {battery_data.get('max_voltage', 0):.2f}V.
Average voltage was {battery_data.get('average_voltage', 0):.2f}V.
Total current consumption was {battery_data.get('total_consumption_mah', 0):.0f} mAh.

Battery health assessment: {battery_data.get('health_details', 'No detailed assessment available')}.
"""
            documents.append(Document(
                page_content=battery_text,
                metadata={"log_id": log_id, "type": "battery_analysis", "timestamp": datetime.now().isoformat()}
            ))
        
        # GPS analysis document
        gps_data = log_data.get('gps_analysis', {})
        if 'error' not in gps_data:
            gps_text = f"""GPS Performance Analysis for {log_id}:

GPS system recorded {gps_data.get('total_gps_readings', 0)} position readings during the flight.
Signal loss events: {gps_data.get('signal_loss_events', 0)}
Poor signal events: {gps_data.get('poor_signal_events', 0)}

First signal loss occurred at: {gps_data.get('first_signal_loss_time_s', 'N/A')} seconds
First poor signal occurred at: {gps_data.get('first_poor_signal_time_s', 'N/A')} seconds

GPS signal quality was {'excellent' if gps_data.get('signal_loss_events', 0) == 0 else 'poor with multiple interruptions'}.
"""
            documents.append(Document(
                page_content=gps_text,
                metadata={"log_id": log_id, "type": "gps_analysis", "timestamp": datetime.now().isoformat()}
            ))
        
        return documents
    
    def _create_event_documents(self, analyzer: LogAnalyzer, log_id: str) -> List[Document]:
        """Create documents for significant events with context"""
        documents = []
        
        try:
            events = analyzer.get_significant_events()
            
            # Group related events
            for event in events:
                if isinstance(event, dict) and event.get('severity') in ['high', 'medium']:
                    event_text = f"""Significant Event in {log_id}:

Time: {event.get('time_s', 0):.1f} seconds into flight
Type: {event.get('type', 'Unknown').title()}
Severity: {event.get('severity', 'Unknown').title()}
Message: {event.get('message', 'No details available')}

This event occurred during active flight operations and may indicate a system condition requiring attention.
"""
                    documents.append(Document(
                        page_content=event_text,
                        metadata={
                            "log_id": log_id,
                            "type": "event",
                            "event_time_s": event.get('time_s', 0),
                            "severity": event.get('severity', 'unknown'),
                            "timestamp": datetime.now().isoformat()
                        }
                    ))
        
        except Exception as e:
            print(f"Error creating event documents: {e}")
        
        return documents
    
    def query_logs(self, query: str, log_id: Optional[str] = None) -> Dict[str, Any]:
        """Query the vector database for log insights"""
        try:
            if not self.vectorstore:
                return {"error": "Vector store not initialized"}
            
            # Check if we have documents for this specific log_id
            if log_id:
                try:
                    # Try to retrieve documents without filter first (more compatible)
                    log_specific_docs = self.vectorstore.similarity_search(
                        f"log {log_id} flight summary", 
                        k=3
                    )
                    
                    # Check if any documents contain our log_id
                    relevant_docs = []
                    for doc in log_specific_docs:
                        if hasattr(doc, 'metadata') and doc.metadata.get('log_id') == log_id:
                            relevant_docs.append(doc)
                    
                    # If no relevant documents found, try a broader search
                    if not relevant_docs:
                        log_specific_docs = self.vectorstore.similarity_search(
                            f"flight data trajectory altitude", 
                            k=5
                        )
                        
                        # Check again for our log_id
                        for doc in log_specific_docs:
                            if hasattr(doc, 'metadata') and doc.metadata.get('log_id') == log_id:
                                relevant_docs.append(doc)
                    
                    # If still no documents, return helpful error
                    if not relevant_docs:
                        return {"error": f"No flight data found for log {log_id}. Please ensure the flight data is loaded first."}
                    
                    print(f"Found {len(relevant_docs)} relevant documents for log {log_id}")
                
                except Exception as e:
                    print(f"Error checking for log documents: {e}")
                    # Continue with regular query if filtering fails
            
            # Create retrieval QA chain with standard search (no filtering to avoid compatibility issues)
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5}),
                return_source_documents=True
            )
            
            # Create extremely restrictive prompt with log_id context
            context_part = f" for log {log_id}" if log_id else ""
            enhanced_query = f"""Answer this question using only the flight log data provided{context_part}. Give only the direct answer with no extra text.

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
                "query": query,
                "log_id": log_id
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