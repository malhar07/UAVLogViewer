from typing import Dict, List, Any, Optional
import json
import logging
import re
from log_parser import BinLogParser, LogMetadata, MAVLinkMessage

logger = logging.getLogger(__name__)

class LogAnalysisTools:
    """Tools that the LLM can use to analyze log files on demand"""
    
    def __init__(self):
        self.active_logs: Dict[str, BinLogParser] = {}
        self.log_metadata_cache: Dict[str, LogMetadata] = {}
    
    def register_log_file(self, log_id: str, file_path: str) -> Dict[str, Any]:
        """Register a new log file for analysis"""
        try:
            parser = BinLogParser(file_path)
            metadata = parser.quick_scan()
            
            self.active_logs[log_id] = parser
            self.log_metadata_cache[log_id] = metadata
            
            return {
                "success": True,
                "log_id": log_id,
                "metadata": {
                    "file_size_mb": round(metadata.file_size / (1024*1024), 2),
                    "message_types": metadata.message_types[:10],  # Limit for LLM context
                    "duration_seconds": metadata.duration,
                    "total_messages": metadata.total_messages,
                    "start_time": metadata.start_time,
                    "end_time": metadata.end_time
                }
            }
        except Exception as e:
            logger.error(f"Error registering log file: {e}")
            return {"success": False, "error": str(e)}
    
    def get_available_logs(self) -> Dict[str, Any]:
        """Get list of available log files"""
        return {
            "available_logs": list(self.active_logs.keys()),
            "total_logs": len(self.active_logs)
        }
    
    def extract_relevant_data(self, log_id: str, user_question: str) -> Dict[str, Any]:
        """Intelligently extract relevant data from log based on user's question"""
        if log_id not in self.active_logs:
            return {"error": "Log not found"}
        
        parser = self.active_logs[log_id]
        metadata = self.log_metadata_cache.get(log_id)
        
        # Analyze question to determine what data is needed
        data_requirements = self._analyze_question(user_question)
        
        # Extract the relevant data
        extracted_data = {}
        
        for message_type in data_requirements['message_types']:
            if message_type in metadata.message_types:
                # Get recent/relevant messages of this type
                messages = parser.get_messages(
                    message_type=message_type,
                    limit=data_requirements['sample_size']
                )
                
                if messages:
                    # Convert to simple dict format for LLM
                    extracted_data[message_type] = [
                        {
                            'timestamp': msg.timestamp,
                            'data': msg.data
                        } for msg in messages
                    ]
        
        # Calculate statistics if needed
        if data_requirements['needs_statistics']:
            extracted_data['statistics'] = self._calculate_statistics(extracted_data)
        
        return {
            "question": user_question,
            "data_analysis": data_requirements,
            "relevant_data": extracted_data,
            "metadata": {
                "log_duration": metadata.duration,
                "total_message_types": len(metadata.message_types),
                "data_source": "real_log_parsing"
            }
        }
    
    def _analyze_question(self, question: str) -> Dict[str, Any]:
        """Analyze user question to determine what log data is needed"""
        question_lower = question.lower()
        
        # Define keyword mappings to message types
        keyword_mappings = {
            'altitude': ['GPS', 'CTUN', 'BARO'],
            'height': ['GPS', 'CTUN', 'BARO'],
            'battery': ['BATT'],
            'voltage': ['BATT'],
            'current': ['BATT'],
            'power': ['BATT'],
            'attitude': ['ATT', 'IMU'],
            'orientation': ['ATT', 'IMU'],
            'roll': ['ATT'],
            'pitch': ['ATT'],
            'yaw': ['ATT'],
            'gps': ['GPS'],
            'location': ['GPS'],
            'position': ['GPS'],
            'coordinate': ['GPS'],
            'speed': ['GPS', 'NKF1'],
            'velocity': ['NKF1', 'GPS'],
            'flight': ['GPS', 'ATT', 'CTUN'],
            'takeoff': ['GPS', 'ATT', 'CTUN'],
            'landing': ['GPS', 'ATT', 'CTUN'],
            'motor': ['RCOU'],
            'servo': ['RCOU'],
            'control': ['RCIN', 'RCOU'],
            'throttle': ['CTUN', 'RCIN'],
            'navigation': ['NKF1', 'GPS'],
            'vibration': ['IMU', 'VIBE'],
            'error': ['ERR', 'MSG'],
            'mode': ['MODE'],
            'arm': ['MSG', 'MODE'],
            'disarm': ['MSG', 'MODE']
        }
        
        # Determine relevant message types
        relevant_types = set()
        for keyword, types in keyword_mappings.items():
            if keyword in question_lower:
                relevant_types.update(types)
        
        # If no specific keywords found, provide overview data
        if not relevant_types:
            relevant_types = {'GPS', 'ATT', 'BATT', 'CTUN'}
        
        # Determine if statistics are needed
        needs_stats = any(word in question_lower for word in [
            'max', 'min', 'average', 'highest', 'lowest', 'statistics',
            'summary', 'overview', 'total', 'duration', 'range'
        ])
        
        # Determine sample size based on question complexity
        if any(word in question_lower for word in ['all', 'entire', 'complete']):
            sample_size = 1000
        elif any(word in question_lower for word in ['recent', 'last', 'end']):
            sample_size = 50
        else:
            sample_size = 100
        
        return {
            'message_types': list(relevant_types),
            'needs_statistics': needs_stats,
            'sample_size': sample_size,
            'complexity': 'high' if len(relevant_types) > 3 else 'medium' if len(relevant_types) > 1 else 'simple'
        }
    
    def _calculate_statistics(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate useful statistics from extracted data"""
        stats = {}
        
        for message_type, messages in extracted_data.items():
            if not messages or message_type == 'statistics':
                continue
                
            type_stats = {}
            
            # Extract numeric values for statistics
            numeric_fields = {}
            for msg in messages:
                for key, value in msg['data'].items():
                    if isinstance(value, (int, float)):
                        if key not in numeric_fields:
                            numeric_fields[key] = []
                        numeric_fields[key].append(value)
            
            # Calculate min/max/avg for numeric fields
            for field, values in numeric_fields.items():
                if values:
                    type_stats[field] = {
                        'min': min(values),
                        'max': max(values),
                        'avg': sum(values) / len(values),
                        'count': len(values)
                    }
            
            if type_stats:
                stats[message_type] = type_stats
        
        return stats
    
    def get_log_metadata(self, log_id: str) -> Dict[str, Any]:
        """Get metadata for a specific log"""
        if log_id not in self.log_metadata_cache:
            return {"error": "Log not found"}
        
        metadata = self.log_metadata_cache[log_id]
        return {
            "log_id": log_id,
            "file_size_mb": round(metadata.file_size / (1024*1024), 2),
            "message_types": metadata.message_types,
            "duration_seconds": metadata.duration,
            "total_messages": metadata.total_messages,
            "start_time": metadata.start_time,
            "end_time": metadata.end_time
        }
    
    def get_messages(self, log_id: str, message_type: str, start_time: Optional[float] = None,
                    end_time: Optional[float] = None, limit: Optional[int] = 100) -> Dict[str, Any]:
        """Get specific messages from log"""
        if log_id not in self.active_logs:
            return {"error": "Log not found"}
        
        parser = self.active_logs[log_id]
        messages = parser.get_messages(message_type, start_time, end_time, limit)
        
        return {
            "message_type": message_type,
            "count": len(messages),
            "messages": [
                {
                    "timestamp": msg.timestamp,
                    "data": msg.data
                } for msg in messages
            ]
        }
    
    def query_log_data(self, log_id: str, query_details: str) -> Dict[str, Any]:
        """Handle complex queries about log data with real data extraction"""
        if log_id not in self.active_logs:
            return {"error": "Log not found"}
        
        # Use the intelligent data extraction
        return self.extract_relevant_data(log_id, query_details)

# Global instance
log_tools = LogAnalysisTools()

# Tool function definitions that the LLM can call
def get_available_logs() -> str:
    """Get list of available log files for analysis"""
    result = log_tools.get_available_logs()
    return json.dumps(result, indent=2)

def get_log_metadata(log_id: str) -> str:
    """Get metadata about a specific log file including duration, size, and available message types"""
    result = log_tools.get_log_metadata(log_id)
    return json.dumps(result, indent=2)

def get_message_types(log_id: str) -> str:
    """Get all available message types in the log with descriptions"""
    result = log_tools.get_message_types(log_id)
    return json.dumps(result, indent=2)

def get_log_time_range(log_id: str) -> str:
    """Get the time range (start, end, duration) of the log"""
    result = log_tools.get_log_time_range(log_id)
    return json.dumps(result, indent=2)

def get_messages(log_id: str, message_type: str, start_time: Optional[float] = None,
                end_time: Optional[float] = None, limit: int = 50) -> str:
    """Get specific messages from the log by type and optional time range
    
    Args:
        log_id: ID of the log file
        message_type: Type of message (e.g., 'GPS', 'ATT', 'BATT')
        start_time: Optional start time filter
        end_time: Optional end time filter  
        limit: Maximum number of messages to return (default 50)
    """
    result = log_tools.get_messages(log_id, message_type, start_time, end_time, limit)
    return json.dumps(result, indent=2)

def query_log_data(log_id: str, query_description: str) -> str:
    """Handle complex queries about log data
    
    Args:
        log_id: ID of the log file
        query_description: Natural language description of what to analyze
    """
    result = log_tools.query_log_data(log_id, query_description)
    return json.dumps(result, indent=2) 