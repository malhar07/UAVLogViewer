import json
import logging
from typing import Dict, List, Any, Optional, Callable
from log_tools import LogTools

logger = logging.getLogger(__name__)

class FunctionCallingManager:
    """Manages function calling for the UAV log analysis chatbot"""
    
    def __init__(self, log_tools: LogTools):
        self.log_tools = log_tools
        self.tools = self._define_tools()
        
    def _define_tools(self) -> Dict[str, Callable]:
        """Define available tools for function calling"""
        return {
            "get_log_summary": self.get_log_summary,
            "analyze_battery_performance": self.analyze_battery_performance,
            "analyze_flight_path": self.analyze_flight_path,
            "analyze_attitude_control": self.analyze_attitude_control,
            "detect_flight_events": self.detect_flight_events,
            "get_message_statistics": self.get_message_statistics,
            "analyze_correlations": self.analyze_correlations,
            "check_system_health": self.check_system_health,
            "analyze_gps_quality": self.analyze_gps_quality,
            "get_performance_metrics": self.get_performance_metrics
        }
    
    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """Get OpenAI-style function definitions for the LLM"""
        return [
            {
                "name": "get_log_summary",
                "description": "Get a comprehensive summary of the entire flight log including duration, messages, and basic flight info",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "log_id": {"type": "string", "description": "The log identifier"}
                    },
                    "required": ["log_id"]
                }
            },
            {
                "name": "analyze_battery_performance",
                "description": "Analyze battery voltage, current, and consumption throughout the flight",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "log_id": {"type": "string", "description": "The log identifier"},
                        "focus": {"type": "string", "description": "What to focus on: 'voltage', 'current', 'consumption', or 'all'", "default": "all"}
                    },
                    "required": ["log_id"]
                }
            },
            {
                "name": "analyze_flight_path",
                "description": "Analyze GPS coordinates, altitude changes, and flight pattern",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "log_id": {"type": "string", "description": "The log identifier"},
                        "include_waypoints": {"type": "boolean", "description": "Whether to include waypoint analysis", "default": False}
                    },
                    "required": ["log_id"]
                }
            },
            {
                "name": "analyze_attitude_control",
                "description": "Analyze roll, pitch, yaw stability and control system performance",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "log_id": {"type": "string", "description": "The log identifier"},
                        "axis": {"type": "string", "description": "Which axis to focus on: 'roll', 'pitch', 'yaw', or 'all'", "default": "all"}
                    },
                    "required": ["log_id"]
                }
            },
            {
                "name": "detect_flight_events",
                "description": "Detect significant events like mode changes, errors, critical battery levels, and system events",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "log_id": {"type": "string", "description": "The log identifier"},
                        "event_types": {"type": "array", "items": {"type": "string"}, "description": "Types of events to focus on"}
                    },
                    "required": ["log_id"]
                }
            },
            {
                "name": "get_message_statistics",
                "description": "Get detailed statistics for specific message types with time-series analysis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "log_id": {"type": "string", "description": "The log identifier"},
                        "message_types": {"type": "array", "items": {"type": "string"}, "description": "Message types to analyze (e.g., ['BATT', 'GPS', 'ATT'])"}
                    },
                    "required": ["log_id", "message_types"]
                }
            },
            {
                "name": "analyze_correlations",
                "description": "Analyze correlations between different flight parameters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "log_id": {"type": "string", "description": "The log identifier"},
                        "parameters": {"type": "array", "items": {"type": "string"}, "description": "Specific parameter pairs to analyze"}
                    },
                    "required": ["log_id"]
                }
            },
            {
                "name": "check_system_health",
                "description": "Perform overall system health check including sensors, motors, and subsystems",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "log_id": {"type": "string", "description": "The log identifier"}
                    },
                    "required": ["log_id"]
                }
            },
            {
                "name": "analyze_gps_quality",
                "description": "Analyze GPS signal quality, accuracy, and satellite count",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "log_id": {"type": "string", "description": "The log identifier"}
                    },
                    "required": ["log_id"]
                }
            },
            {
                "name": "get_performance_metrics",
                "description": "Calculate key performance metrics like efficiency, stability, and control precision",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "log_id": {"type": "string", "description": "The log identifier"},
                        "metric_type": {"type": "string", "description": "Type of metrics: 'efficiency', 'stability', 'control', or 'all'", "default": "all"}
                    },
                    "required": ["log_id"]
                }
            }
        ]
    
    def get_log_summary(self, log_id: str) -> Dict[str, Any]:
        """Get comprehensive log summary"""
        try:
            metadata = self.log_tools.get_log_metadata(log_id)
            if "error" in metadata:
                return metadata
            
            # Get basic flight info
            summary = {
                "log_id": log_id,
                "duration_seconds": metadata.get("duration", 0),
                "total_messages": metadata.get("total_messages", 0),
                "message_types": list(metadata.get("message_types", [])),
                "start_time": metadata.get("start_time"),
                "end_time": metadata.get("end_time"),
            }
            
            # Add flight mode summary if available
            if 'MODE' in metadata.get("message_types", []):
                mode_data = self.log_tools.extract_messages(log_id, ['MODE'])
                if 'MODE' in mode_data:
                    modes = [msg['data'].get('Mode', 'Unknown') for msg in mode_data['MODE']]
                    summary["flight_modes"] = list(set(modes))
            
            # Add altitude range if GPS available
            if 'GPS' in metadata.get("message_types", []):
                gps_data = self.log_tools.extract_messages(log_id, ['GPS'])
                if 'GPS' in gps_data:
                    altitudes = [msg['data'].get('Alt', 0) for msg in gps_data['GPS'] if 'Alt' in msg['data']]
                    if altitudes:
                        summary["altitude_range"] = {
                            "min": min(altitudes),
                            "max": max(altitudes),
                            "range": max(altitudes) - min(altitudes)
                        }
            
            return {"summary": summary, "insights": "Basic flight log summary with key metrics"}
            
        except Exception as e:
            logger.error(f"Error getting log summary: {e}")
            return {"error": f"Failed to get log summary: {str(e)}"}
    
    def analyze_battery_performance(self, log_id: str, focus: str = "all") -> Dict[str, Any]:
        """Analyze battery performance during flight"""
        try:
            battery_data = self.log_tools.extract_messages(log_id, ['BATT'])
            if "error" in battery_data:
                return battery_data
            
            if 'BATT' not in battery_data or not battery_data['BATT']:
                return {"error": "No battery data available"}
            
            analysis = {}
            messages = battery_data['BATT']
            
            # Extract voltage, current, and other battery metrics
            voltages = [msg['data'].get('Volt', 0) for msg in messages if 'Volt' in msg['data']]
            currents = [msg['data'].get('Curr', 0) for msg in messages if 'Curr' in msg['data']]
            timestamps = [msg['timestamp'] for msg in messages]
            
            if focus in ['voltage', 'all'] and voltages:
                voltage_analysis = {
                    "start_voltage": voltages[0],
                    "end_voltage": voltages[-1],
                    "min_voltage": min(voltages),
                    "max_voltage": max(voltages),
                    "voltage_drop": voltages[0] - voltages[-1],
                    "critical_events": len([v for v in voltages if v < 10.5])
                }
                
                # Voltage trend analysis
                if len(voltages) > 10:
                    first_quarter = sum(voltages[:len(voltages)//4]) / (len(voltages)//4)
                    last_quarter = sum(voltages[-len(voltages)//4:]) / (len(voltages)//4)
                    voltage_analysis["discharge_rate"] = (first_quarter - last_quarter) / (timestamps[-1] - timestamps[0]) * 3600  # V/hour
                
                analysis["voltage"] = voltage_analysis
            
            if focus in ['current', 'all'] and currents:
                current_analysis = {
                    "avg_current": sum(currents) / len(currents),
                    "max_current": max(currents),
                    "min_current": min(currents),
                    "current_spikes": len([c for c in currents if c > 50])  # Assuming 50A is high
                }
                analysis["current"] = current_analysis
            
            if focus in ['consumption', 'all'] and voltages and currents:
                # Calculate power consumption
                powers = [v * c for v, c in zip(voltages, currents) if v > 0 and c > 0]
                if powers:
                    total_energy = sum(powers) * (timestamps[-1] - timestamps[0]) / 3600  # Wh approximation
                    analysis["consumption"] = {
                        "avg_power": sum(powers) / len(powers),
                        "max_power": max(powers),
                        "estimated_energy_used": total_energy
                    }
            
            insights = []
            if 'voltage' in analysis:
                if analysis['voltage']['voltage_drop'] > 2.0:
                    insights.append("Significant voltage drop during flight - monitor battery health")
                if analysis['voltage']['critical_events'] > 0:
                    insights.append(f"Battery reached critical voltage levels {analysis['voltage']['critical_events']} times")
            
            if 'current' in analysis and analysis['current']['current_spikes'] > 0:
                insights.append(f"Detected {analysis['current']['current_spikes']} current spikes - check for aggressive maneuvers")
            
            return {"analysis": analysis, "insights": " | ".join(insights) if insights else "Battery performance appears normal"}
            
        except Exception as e:
            logger.error(f"Error analyzing battery: {e}")
            return {"error": f"Failed to analyze battery: {str(e)}"}
    
    def analyze_flight_path(self, log_id: str, include_waypoints: bool = False) -> Dict[str, Any]:
        """Analyze flight path and GPS data"""
        try:
            gps_data = self.log_tools.extract_messages(log_id, ['GPS'])
            if "error" in gps_data:
                return gps_data
            
            if 'GPS' not in gps_data or not gps_data['GPS']:
                return {"error": "No GPS data available"}
            
            messages = gps_data['GPS']
            
            # Extract coordinates and altitude
            latitudes = [msg['data'].get('Lat', 0) for msg in messages if 'Lat' in msg['data']]
            longitudes = [msg['data'].get('Lng', 0) for msg in messages if 'Lng' in msg['data']]
            altitudes = [msg['data'].get('Alt', 0) for msg in messages if 'Alt' in msg['data']]
            speeds = [msg['data'].get('Spd', 0) for msg in messages if 'Spd' in msg['data']]
            
            analysis = {}
            
            if latitudes and longitudes:
                analysis["coordinates"] = {
                    "start_position": {"lat": latitudes[0], "lng": longitudes[0]},
                    "end_position": {"lat": latitudes[-1], "lng": longitudes[-1]},
                    "lat_range": max(latitudes) - min(latitudes),
                    "lng_range": max(longitudes) - min(longitudes)
                }
                
                # Calculate approximate distance traveled
                total_distance = 0
                for i in range(1, len(latitudes)):
                    # Simple distance calculation (not accounting for Earth curvature)
                    lat_diff = latitudes[i] - latitudes[i-1]
                    lng_diff = longitudes[i] - longitudes[i-1]
                    total_distance += (lat_diff**2 + lng_diff**2)**0.5 * 111000  # Rough conversion to meters
                
                analysis["distance"] = {
                    "total_distance_m": total_distance,
                    "straight_line_distance": ((latitudes[-1] - latitudes[0])**2 + (longitudes[-1] - longitudes[0])**2)**0.5 * 111000
                }
            
            if altitudes:
                analysis["altitude"] = {
                    "start_altitude": altitudes[0],
                    "max_altitude": max(altitudes),
                    "min_altitude": min(altitudes),
                    "altitude_gain": max(altitudes) - min(altitudes)
                }
            
            if speeds:
                analysis["speed"] = {
                    "avg_speed": sum(speeds) / len(speeds),
                    "max_speed": max(speeds),
                    "min_speed": min(speeds)
                }
            
            insights = []
            if 'distance' in analysis:
                efficiency = analysis['distance']['straight_line_distance'] / analysis['distance']['total_distance_m'] if analysis['distance']['total_distance_m'] > 0 else 0
                if efficiency < 0.5:
                    insights.append("Flight path shows significant deviation - possible manual control or waypoint mission")
                else:
                    insights.append("Flight path is relatively direct")
            
            if 'altitude' in analysis and analysis['altitude']['altitude_gain'] > 100:
                insights.append(f"Significant altitude changes of {analysis['altitude']['altitude_gain']:.1f}m")
            
            return {"analysis": analysis, "insights": " | ".join(insights) if insights else "Flight path analysis complete"}
            
        except Exception as e:
            logger.error(f"Error analyzing flight path: {e}")
            return {"error": f"Failed to analyze flight path: {str(e)}"}
    
    def analyze_attitude_control(self, log_id: str, axis: str = "all") -> Dict[str, Any]:
        """Analyze attitude control performance"""
        try:
            att_data = self.log_tools.extract_messages(log_id, ['ATT'])
            if "error" in att_data:
                return att_data
            
            if 'ATT' not in att_data or not att_data['ATT']:
                return {"error": "No attitude data available"}
            
            messages = att_data['ATT']
            analysis = {}
            
            # Extract attitude data
            if axis in ['roll', 'all']:
                rolls = [msg['data'].get('Roll', 0) for msg in messages if 'Roll' in msg['data']]
                if rolls:
                    analysis["roll"] = {
                        "max_roll": max(rolls),
                        "min_roll": min(rolls),
                        "avg_roll": sum(rolls) / len(rolls),
                        "roll_range": max(rolls) - min(rolls),
                        "stability": "good" if max(abs(r) for r in rolls) < 0.3 else "moderate" if max(abs(r) for r in rolls) < 0.7 else "poor"
                    }
            
            if axis in ['pitch', 'all']:
                pitches = [msg['data'].get('Pitch', 0) for msg in messages if 'Pitch' in msg['data']]
                if pitches:
                    analysis["pitch"] = {
                        "max_pitch": max(pitches),
                        "min_pitch": min(pitches),
                        "avg_pitch": sum(pitches) / len(pitches),
                        "pitch_range": max(pitches) - min(pitches),
                        "stability": "good" if max(abs(p) for p in pitches) < 0.3 else "moderate" if max(abs(p) for p in pitches) < 0.7 else "poor"
                    }
            
            if axis in ['yaw', 'all']:
                yaws = [msg['data'].get('Yaw', 0) for msg in messages if 'Yaw' in msg['data']]
                if yaws:
                    analysis["yaw"] = {
                        "yaw_range": max(yaws) - min(yaws),
                        "avg_yaw": sum(yaws) / len(yaws),
                        "yaw_changes": len([i for i in range(1, len(yaws)) if abs(yaws[i] - yaws[i-1]) > 0.5])
                    }
            
            insights = []
            for axis_name, axis_data in analysis.items():
                if 'stability' in axis_data:
                    if axis_data['stability'] == 'poor':
                        insights.append(f"{axis_name.capitalize()} shows poor stability - check PID tuning")
                    elif axis_data['stability'] == 'good':
                        insights.append(f"{axis_name.capitalize()} control is stable")
            
            return {"analysis": analysis, "insights": " | ".join(insights) if insights else "Attitude control analysis complete"}
            
        except Exception as e:
            logger.error(f"Error analyzing attitude: {e}")
            return {"error": f"Failed to analyze attitude: {str(e)}"}
    
    def detect_flight_events(self, log_id: str, event_types: List[str] = None) -> Dict[str, Any]:
        """Detect flight events using the enhanced event detection"""
        try:
            events = self.log_tools.detect_events(log_id, event_types)
            if "error" in events:
                return events
            
            # Summarize events
            event_summary = {}
            total_events = 0
            
            for event_type, event_list in events.items():
                if event_list:
                    event_summary[event_type] = len(event_list)
                    total_events += len(event_list)
            
            insights = []
            if total_events == 0:
                insights.append("No significant events detected - clean flight")
            else:
                insights.append(f"Detected {total_events} significant events")
                
                if 'errors_and_warnings' in events and events['errors_and_warnings']:
                    insights.append(f"{len(events['errors_and_warnings'])} errors/warnings found")
                
                if 'critical_battery_events' in events and events['critical_battery_events']:
                    insights.append(f"{len(events['critical_battery_events'])} critical battery events")
            
            return {
                "events": events,
                "summary": event_summary,
                "insights": " | ".join(insights)
            }
            
        except Exception as e:
            logger.error(f"Error detecting events: {e}")
            return {"error": f"Failed to detect events: {str(e)}"}
    
    def get_message_statistics(self, log_id: str, message_types: List[str]) -> Dict[str, Any]:
        """Get detailed statistics for specific message types"""
        try:
            data = self.log_tools.extract_messages(log_id, message_types)
            if "error" in data:
                return data
            
            insights = []
            for msg_type in message_types:
                if msg_type in data and data[msg_type]:
                    count = len(data[msg_type])
                    insights.append(f"{msg_type}: {count} messages")
                else:
                    insights.append(f"{msg_type}: No data available")
            
            return {
                "statistics": data.get('statistics', {}),
                "message_data": data,
                "insights": " | ".join(insights)
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": f"Failed to get statistics: {str(e)}"}
    
    def analyze_correlations(self, log_id: str, parameters: List[str] = None) -> Dict[str, Any]:
        """Analyze correlations between flight parameters"""
        try:
            # Get comprehensive data for correlation analysis
            message_types = ['BATT', 'GPS', 'ATT', 'CTUN', 'RCOU', 'IMU']
            data = self.log_tools.extract_messages(log_id, message_types)
            
            if "error" in data:
                return data
            
            correlations = data.get('statistics', {}).get('correlations', {})
            
            insights = []
            strong_correlations = []
            
            for corr_name, corr_data in correlations.items():
                if corr_data.get('strength') in ['strong', 'moderate']:
                    strong_correlations.append(f"{corr_data['description']}: {corr_data['interpretation']}")
            
            if strong_correlations:
                insights.extend(strong_correlations[:3])  # Top 3 correlations
            else:
                insights.append("No strong correlations detected")
            
            return {
                "correlations": correlations,
                "insights": " | ".join(insights)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing correlations: {e}")
            return {"error": f"Failed to analyze correlations: {str(e)}"}
    
    def check_system_health(self, log_id: str) -> Dict[str, Any]:
        """Perform comprehensive system health check"""
        try:
            # Combine multiple analyses for health check
            events = self.detect_flight_events(log_id)
            battery = self.analyze_battery_performance(log_id)
            gps = self.analyze_gps_quality(log_id)
            
            health_score = 100
            issues = []
            
            # Check for errors
            if 'events' in events and 'errors_and_warnings' in events['events']:
                error_count = len(events['events']['errors_and_warnings'])
                health_score -= min(error_count * 10, 30)
                if error_count > 0:
                    issues.append(f"{error_count} system errors detected")
            
            # Check battery health
            if 'analysis' in battery and 'voltage' in battery['analysis']:
                if battery['analysis']['voltage'].get('critical_events', 0) > 0:
                    health_score -= 20
                    issues.append("Critical battery voltage events")
                if battery['analysis']['voltage'].get('voltage_drop', 0) > 2.0:
                    health_score -= 10
                    issues.append("Significant battery voltage drop")
            
            # Check GPS quality
            if 'analysis' in gps and 'quality_issues' in gps['analysis']:
                gps_issues = gps['analysis']['quality_issues']
                if gps_issues > 5:
                    health_score -= 15
                    issues.append("GPS quality issues detected")
            
            health_status = "excellent" if health_score >= 90 else "good" if health_score >= 70 else "fair" if health_score >= 50 else "poor"
            
            return {
                "health_score": health_score,
                "status": health_status,
                "issues": issues,
                "insights": f"System health: {health_status} ({health_score}/100)" + (f" - Issues: {', '.join(issues)}" if issues else " - No major issues detected")
            }
            
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return {"error": f"Failed to check system health: {str(e)}"}
    
    def analyze_gps_quality(self, log_id: str) -> Dict[str, Any]:
        """Analyze GPS signal quality"""
        try:
            gps_data = self.log_tools.extract_messages(log_id, ['GPS'])
            if "error" in gps_data:
                return gps_data
            
            if 'GPS' not in gps_data or not gps_data['GPS']:
                return {"error": "No GPS data available"}
            
            messages = gps_data['GPS']
            
            hdops = [msg['data'].get('HDop', 0) for msg in messages if 'HDop' in msg['data']]
            num_svs = [msg['data'].get('NSats', 0) for msg in messages if 'NSats' in msg['data']]
            
            analysis = {}
            
            if hdops:
                avg_hdop = sum(hdops) / len(hdops)
                max_hdop = max(hdops)
                quality_issues = len([h for h in hdops if h > 2.0])
                
                analysis["hdop"] = {
                    "average": avg_hdop,
                    "maximum": max_hdop,
                    "quality": "excellent" if avg_hdop < 1.0 else "good" if avg_hdop < 2.0 else "fair" if avg_hdop < 3.0 else "poor"
                }
                analysis["quality_issues"] = quality_issues
            
            if num_svs:
                avg_sats = sum(num_svs) / len(num_svs)
                min_sats = min(num_svs)
                
                analysis["satellites"] = {
                    "average": avg_sats,
                    "minimum": min_sats,
                    "quality": "excellent" if avg_sats > 12 else "good" if avg_sats > 8 else "fair" if avg_sats > 6 else "poor"
                }
            
            insights = []
            if 'hdop' in analysis:
                insights.append(f"GPS accuracy: {analysis['hdop']['quality']} (HDop: {analysis['hdop']['average']:.2f})")
            if 'satellites' in analysis:
                insights.append(f"Satellite coverage: {analysis['satellites']['quality']} (avg: {analysis['satellites']['average']:.1f} sats)")
            
            return {"analysis": analysis, "insights": " | ".join(insights)}
            
        except Exception as e:
            logger.error(f"Error analyzing GPS: {e}")
            return {"error": f"Failed to analyze GPS: {str(e)}"}
    
    def get_performance_metrics(self, log_id: str, metric_type: str = "all") -> Dict[str, Any]:
        """Calculate performance metrics"""
        try:
            # Combine multiple analyses for performance metrics
            battery = self.analyze_battery_performance(log_id)
            attitude = self.analyze_attitude_control(log_id)
            flight_path = self.analyze_flight_path(log_id)
            
            metrics = {}
            
            if metric_type in ['efficiency', 'all'] and 'analysis' in battery:
                if 'consumption' in battery['analysis']:
                    power_data = battery['analysis']['consumption']
                    metrics["efficiency"] = {
                        "power_consumption": power_data.get('avg_power', 0),
                        "energy_efficiency": "good" if power_data.get('avg_power', 1000) < 500 else "moderate"
                    }
            
            if metric_type in ['stability', 'all'] and 'analysis' in attitude:
                stability_scores = []
                for axis, data in attitude['analysis'].items():
                    if 'stability' in data:
                        score = 3 if data['stability'] == 'good' else 2 if data['stability'] == 'moderate' else 1
                        stability_scores.append(score)
                
                if stability_scores:
                    avg_stability = sum(stability_scores) / len(stability_scores)
                    metrics["stability"] = {
                        "score": avg_stability,
                        "rating": "excellent" if avg_stability > 2.5 else "good" if avg_stability > 2 else "needs_improvement"
                    }
            
            if metric_type in ['control', 'all'] and 'analysis' in flight_path:
                if 'distance' in flight_path['analysis']:
                    distance_data = flight_path['analysis']['distance']
                    efficiency_ratio = distance_data.get('straight_line_distance', 1) / distance_data.get('total_distance_m', 1)
                    metrics["control_precision"] = {
                        "path_efficiency": efficiency_ratio,
                        "rating": "excellent" if efficiency_ratio > 0.8 else "good" if efficiency_ratio > 0.6 else "moderate"
                    }
            
            insights = []
            for metric_name, metric_data in metrics.items():
                if 'rating' in metric_data:
                    insights.append(f"{metric_name}: {metric_data['rating']}")
            
            return {"metrics": metrics, "insights": " | ".join(insights) if insights else "Performance metrics calculated"}
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {"error": f"Failed to calculate metrics: {str(e)}"}
    
    def execute_function(self, function_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a specific function"""
        if function_name not in self.tools:
            return {"error": f"Unknown function: {function_name}"}
        
        try:
            return self.tools[function_name](**kwargs)
        except Exception as e:
            logger.error(f"Error executing {function_name}: {e}")
            return {"error": f"Failed to execute {function_name}: {str(e)}"} 