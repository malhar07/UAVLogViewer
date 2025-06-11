from typing import Dict, List, Any, Optional
import json
import logging
import re
from log_parser import BinLogParser, LogMetadata, MAVLinkMessage

logger = logging.getLogger(__name__)

class LogTools:
    """Tools that the LLM can use to analyze log files on demand"""
    
    def __init__(self):
        self.active_logs: Dict[str, BinLogParser] = {}
        self.log_metadata_cache: Dict[str, LogMetadata] = {}
    
    def register_log(self, file_path: str) -> str:
        """Register a log file and return its ID"""
        import uuid
        log_id = str(uuid.uuid4())[:8]
        
        try:
            parser = BinLogParser(file_path)
            metadata = parser.quick_scan()
            
            self.active_logs[log_id] = parser
            self.log_metadata_cache[log_id] = metadata
            
            return log_id
        except Exception as e:
            logger.error(f"Error registering log file: {e}")
            raise Exception(f"Failed to register log: {str(e)}")
    
    def cleanup_log(self, log_id: str) -> bool:
        """Clean up a log session"""
        try:
            if log_id in self.active_logs:
                del self.active_logs[log_id]
            if log_id in self.log_metadata_cache:
                del self.log_metadata_cache[log_id]
            return True
        except Exception as e:
            logger.error(f"Error cleaning up log {log_id}: {e}")
            return False
    
    def extract_messages(self, log_id: str, message_types: List[str]) -> Dict[str, Any]:
        """Extract messages of specified types with enhanced analysis"""
        if log_id not in self.active_logs:
            return {"error": "Log not found"}
        
        parser = self.active_logs[log_id]
        result = {}
        
        for message_type in message_types:
            try:
                messages = parser.get_messages(message_type, limit=200)
                if messages:
                    result[message_type] = [
                        {
                            'timestamp': msg.timestamp,
                            'data': msg.data
                        } for msg in messages
                    ]
                else:
                    result[message_type] = []
            except Exception as e:
                logger.warning(f"Could not extract {message_type} messages: {e}")
                result[message_type] = []
        
        # Add statistics
        result['statistics'] = self._calculate_statistics(result)
        
        return result
    
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
        
        # Extract and summarize the relevant data
        analysis_summary = {}
        
        for message_type in data_requirements['message_types']:
            if message_type in metadata.message_types:
                # Get messages with intelligent sampling based on question type
                messages = self._get_intelligent_sample(
                    parser, message_type, user_question, data_requirements
                )
                
                if messages:
                    # **NEW: Summarize the extracted messages**
                    summary = self._summarize_messages(message_type, messages, user_question)
                    if summary:
                        analysis_summary[message_type] = summary
        
        # Calculate statistics if needed
        raw_extracted_data = {}
        if data_requirements['needs_statistics']:
            # Get raw data for statistics calculation
            for message_type in data_requirements['message_types']:
                if message_type in metadata.message_types:
                    messages = self._get_intelligent_sample(
                        parser, message_type, user_question, data_requirements
                    )
                    if messages:
                        raw_extracted_data[message_type] = [
                            {
                                'timestamp': msg.timestamp,
                                'data': msg.data
                            } for msg in messages
                        ]
            
            analysis_summary['statistics'] = self._calculate_statistics(raw_extracted_data)
        
        return {
            "question": user_question,
            "data_analysis_requirements": data_requirements,
            "summary_of_relevant_data": analysis_summary,  # Key change here
            "metadata": {
                "log_duration": metadata.duration,
                "total_message_types": len(metadata.message_types),
                "data_source": "real_log_parsing",
                "sampling_strategy": data_requirements.get('sampling_strategy', 'standard')
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
        """Calculate comprehensive statistics including time-series analysis and correlations"""
        stats = {}
        
        for message_type, messages in extracted_data.items():
            if not messages or message_type == 'statistics':
                continue
                
            type_stats = {}
            
            # Extract numeric values for statistics
            numeric_fields = {}
            timestamps = []
            
            for msg in messages:
                timestamps.append(msg['timestamp'])
                for key, value in msg['data'].items():
                    if isinstance(value, (int, float)):
                        if key not in numeric_fields:
                            numeric_fields[key] = []
                        numeric_fields[key].append(value)
            
            # Calculate enhanced statistics for each numeric field
            for field, values in numeric_fields.items():
                if values and len(values) > 1:
                    field_stats = {
                        'min': min(values),
                        'max': max(values),
                        'avg': sum(values) / len(values),
                        'count': len(values)
                    }
                    
                    # Time-series analysis
                    if len(values) > 5:
                        # Start, middle, end analysis
                        start_val = values[0]
                        end_val = values[-1]
                        mid_idx = len(values) // 2
                        mid_val = values[mid_idx]
                        
                        field_stats['time_series'] = {
                            'start_value': start_val,
                            'mid_value': mid_val, 
                            'end_value': end_val,
                            'total_change': end_val - start_val,
                            'first_half_change': mid_val - start_val,
                            'second_half_change': end_val - mid_val
                        }
                        
                        # Detect significant changes
                        change_threshold = (max(values) - min(values)) * 0.1  # 10% of range
                        significant_changes = []
                        
                        for i in range(1, len(values)):
                            change = abs(values[i] - values[i-1])
                            if change > change_threshold:
                                significant_changes.append({
                                    'timestamp': timestamps[i],
                                    'change': values[i] - values[i-1],
                                    'from_value': values[i-1],
                                    'to_value': values[i]
                                })
                        
                        if significant_changes:
                            field_stats['significant_changes'] = significant_changes[:5]  # Limit to 5 most significant
                    
                    # Range and variance analysis
                    field_range = max(values) - min(values)
                    field_stats['range'] = field_range
                    
                    # Simple trend analysis
                    if len(values) > 3:
                        first_quarter = sum(values[:len(values)//4]) / (len(values)//4)
                        last_quarter = sum(values[-len(values)//4:]) / (len(values)//4)
                        trend_change = last_quarter - first_quarter
                        
                        if abs(trend_change) > field_range * 0.05:  # 5% of range
                            if trend_change > 0:
                                field_stats['trend'] = f"increasing (+{trend_change:.2f})"
                            else:
                                field_stats['trend'] = f"decreasing ({trend_change:.2f})"
                        else:
                            field_stats['trend'] = "stable"
                    
                    type_stats[field] = field_stats
            
            if type_stats:
                stats[message_type] = type_stats
        
        # Cross-message correlation analysis
        correlations = self._calculate_correlations(extracted_data)
        if correlations:
            stats['correlations'] = correlations
        
        return stats
    
    def _calculate_correlations(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate correlations between different message types"""
        correlations = {}
        
        # Common correlation analyses for UAV data
        correlation_pairs = [
            ('BATT', 'Volt', 'CTUN', 'ThO', 'Battery voltage vs Throttle'),
            ('BATT', 'Curr', 'CTUN', 'ThO', 'Battery current vs Throttle'),
            ('GPS', 'Alt', 'BATT', 'Volt', 'Altitude vs Battery voltage'),
            ('ATT', 'Roll', 'RCOU', 'C1', 'Roll vs Motor 1 output'),
            ('ATT', 'Pitch', 'RCOU', 'C2', 'Pitch vs Motor 2 output'),
            ('IMU', 'AccX', 'ATT', 'Roll', 'X-acceleration vs Roll'),
        ]
        
        for msg_type1, field1, msg_type2, field2, description in correlation_pairs:
            if msg_type1 in extracted_data and msg_type2 in extracted_data:
                corr_result = self._calculate_field_correlation(
                    extracted_data[msg_type1], field1,
                    extracted_data[msg_type2], field2,
                    description
                )
                if corr_result:
                    correlations[f"{msg_type1}_{field1}_vs_{msg_type2}_{field2}"] = corr_result
        
        return correlations
    
    def _calculate_field_correlation(self, messages1: List, field1: str, messages2: List, field2: str, description: str) -> Optional[Dict]:
        """Calculate correlation between two fields from different message types"""
        # Extract values with timestamps
        values1_with_time = []
        values2_with_time = []
        
        for msg in messages1:
            if field1 in msg['data'] and isinstance(msg['data'][field1], (int, float)):
                values1_with_time.append((msg['timestamp'], msg['data'][field1]))
        
        for msg in messages2:
            if field2 in msg['data'] and isinstance(msg['data'][field2], (int, float)):
                values2_with_time.append((msg['timestamp'], msg['data'][field2]))
        
        if len(values1_with_time) < 5 or len(values2_with_time) < 5:
            return None
        
        # Align data by timestamp (simple approach - find closest timestamps)
        aligned_pairs = []
        for timestamp1, value1 in values1_with_time:
            closest_match = min(values2_with_time, key=lambda x: abs(x[0] - timestamp1))
            if abs(closest_match[0] - timestamp1) < 5.0:  # Within 5 seconds
                aligned_pairs.append((value1, closest_match[1]))
        
        if len(aligned_pairs) < 5:
            return None
        
        # Calculate simple correlation coefficient
        x_values = [pair[0] for pair in aligned_pairs]
        y_values = [pair[1] for pair in aligned_pairs]
        
        n = len(aligned_pairs)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in aligned_pairs)
        sum_x2 = sum(x * x for x in x_values)
        sum_y2 = sum(y * y for y in y_values)
        
        # Pearson correlation coefficient
        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2))**0.5
        
        if denominator == 0:
            return None
        
        correlation = numerator / denominator
        
        # Interpret correlation strength
        abs_corr = abs(correlation)
        if abs_corr > 0.7:
            strength = "strong"
        elif abs_corr > 0.4:
            strength = "moderate"
        elif abs_corr > 0.2:
            strength = "weak"
        else:
            strength = "negligible"
        
        direction = "positive" if correlation > 0 else "negative"
        
        return {
            'correlation_coefficient': round(correlation, 3),
            'strength': strength,
            'direction': direction,
            'description': description,
            'interpretation': f"{strength} {direction} correlation ({correlation:.3f})",
            'sample_size': n
        }
    
    def detect_events(self, log_id: str, event_types: List[str] = None) -> Dict[str, Any]:
        """Detect significant events in the flight log"""
        if log_id not in self.active_logs:
            return {"error": "Log not found"}
        
        parser = self.active_logs[log_id]
        metadata = self.log_metadata_cache.get(log_id)
        
        events = {
            'flight_mode_changes': [],
            'errors_and_warnings': [],
            'critical_battery_events': [],
            'gps_events': [],
            'altitude_events': [],
            'system_events': []
        }
        
        # Flight mode changes
        if 'MODE' in metadata.message_types:
            mode_messages = parser.get_messages('MODE', limit=50)
            for msg in mode_messages:
                if 'Mode' in msg.data:
                    events['flight_mode_changes'].append({
                        'timestamp': msg.timestamp,
                        'mode': msg.data['Mode'],
                        'event': f"Flight mode changed to {msg.data['Mode']}"
                    })
        
        # Error messages
        if 'ERR' in metadata.message_types:
            error_messages = parser.get_messages('ERR', limit=100)
            for msg in error_messages:
                events['errors_and_warnings'].append({
                    'timestamp': msg.timestamp,
                    'subsystem': msg.data.get('Subsys', 'Unknown'),
                    'error_code': msg.data.get('ECode', 'Unknown'),
                    'event': f"Error in {msg.data.get('Subsys', 'Unknown')}: {msg.data.get('ECode', 'Unknown')}"
                })
        
        # System messages
        if 'MSG' in metadata.message_types:
            system_messages = parser.get_messages('MSG', limit=100)
            for msg in system_messages:
                message_text = msg.data.get('Message', '')
                if any(keyword in message_text.lower() for keyword in ['armed', 'disarmed', 'takeoff', 'land', 'rtl', 'emergency']):
                    events['system_events'].append({
                        'timestamp': msg.timestamp,
                        'message': message_text,
                        'event': f"System: {message_text}"
                    })
        
        # Battery critical events
        if 'BATT' in metadata.message_types:
            battery_messages = parser.get_messages('BATT', limit=200)
            for msg in battery_messages:
                voltage = msg.data.get('Volt', 0)
                if voltage < 10.5:
                    events['critical_battery_events'].append({
                        'timestamp': msg.timestamp,
                        'voltage': voltage,
                        'event': f"CRITICAL: Battery voltage dropped to {voltage:.2f}V"
                    })
                elif voltage < 11.1:
                    events['critical_battery_events'].append({
                        'timestamp': msg.timestamp,
                        'voltage': voltage,
                        'event': f"WARNING: Low battery voltage {voltage:.2f}V"
                    })
        
        # GPS events
        if 'GPS' in metadata.message_types:
            gps_messages = parser.get_messages('GPS', limit=100)
            for msg in gps_messages:
                hdop = msg.data.get('HDop', 0)
                if hdop > 3.0:
                    events['gps_events'].append({
                        'timestamp': msg.timestamp,
                        'hdop': hdop,
                        'event': f"Poor GPS quality: HDop {hdop:.2f}"
                    })
        
        # Altitude events (significant changes)
        if 'GPS' in metadata.message_types:
            gps_messages = parser.get_messages('GPS', limit=200)
            altitudes = [(msg.timestamp, msg.data.get('Alt', 0)) for msg in gps_messages if 'Alt' in msg.data]
            
            if len(altitudes) > 5:
                max_alt = max(altitudes, key=lambda x: x[1])
                min_alt = min(altitudes, key=lambda x: x[1])
                
                events['altitude_events'].append({
                    'timestamp': max_alt[0],
                    'altitude': max_alt[1],
                    'event': f"Maximum altitude reached: {max_alt[1]:.1f}m"
                })
                
                events['altitude_events'].append({
                    'timestamp': min_alt[0],
                    'altitude': min_alt[1],
                    'event': f"Minimum altitude: {min_alt[1]:.1f}m"
                })
        
        # Remove empty event categories
        events = {k: v for k, v in events.items() if v}
        
        return events
    
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

    def _get_intelligent_sample(self, parser, message_type: str, user_question: str, data_requirements: Dict) -> List:
        """Get intelligently sampled data based on question context"""
        question_lower = user_question.lower()
        
        # Determine sampling strategy
        if any(word in question_lower for word in ['highest', 'maximum', 'peak', 'max']):
            # For max questions, get samples around peak values
            return self._get_peak_samples(parser, message_type, ascending=False)
        
        elif any(word in question_lower for word in ['lowest', 'minimum', 'min']):
            # For min questions, get samples around minimum values  
            return self._get_peak_samples(parser, message_type, ascending=True)
        
        elif any(word in question_lower for word in ['takeoff', 'launch', 'start']):
            # For takeoff questions, get early flight data
            return self._get_temporal_samples(parser, message_type, start_percent=0, end_percent=20)
        
        elif any(word in question_lower for word in ['landing', 'end', 'final']):
            # For landing questions, get late flight data
            return self._get_temporal_samples(parser, message_type, start_percent=80, end_percent=100)
        
        elif any(word in question_lower for word in ['problem', 'issue', 'error', 'warning']):
            # For problem analysis, get diverse samples to find anomalies
            return self._get_anomaly_samples(parser, message_type)
        
        elif any(word in question_lower for word in ['trend', 'change', 'over time', 'throughout']):
            # For trend analysis, get evenly distributed samples
            return self._get_distributed_samples(parser, message_type, count=data_requirements['sample_size'])
        
        else:
            # Default: get recent data with some historical context
            return parser.get_messages(message_type, limit=data_requirements['sample_size'])

    def _get_peak_samples(self, parser, message_type: str, ascending: bool = False) -> List:
        """Get samples around peak/minimum values"""
        # Get more data to find peaks
        all_messages = parser.get_messages(message_type, limit=500)
        if not all_messages:
            return []
        
        # Find peak values based on message type
        if message_type == "GPS" or message_type == "CTUN":
            # For altitude analysis
            values_with_index = [(i, msg.data.get('Alt', 0)) for i, msg in enumerate(all_messages) if 'Alt' in msg.data]
        elif message_type == "BATT":
            # For battery analysis (voltage)
            values_with_index = [(i, msg.data.get('Volt', 0)) for i, msg in enumerate(all_messages) if 'Volt' in msg.data]
        else:
            # Return standard sample if no specific peak logic
            return all_messages[:50]
        
        if not values_with_index:
            return all_messages[:50]
        
        # Sort to find peak/minimum
        values_with_index.sort(key=lambda x: x[1], reverse=not ascending)
        
        # Get indices around the peak values
        peak_indices = set()
        for i, (idx, value) in enumerate(values_with_index[:5]):  # Top 5 peaks
            # Include surrounding context
            for offset in range(-5, 6):
                peak_indices.add(max(0, min(len(all_messages)-1, idx + offset)))
        
        # Return messages at peak indices, sorted by timestamp
        peak_messages = [all_messages[i] for i in sorted(peak_indices)]
        return peak_messages[:100]  # Limit to 100 messages

    def _get_temporal_samples(self, parser, message_type: str, start_percent: int, end_percent: int) -> List:
        """Get samples from specific time period of flight"""
        all_messages = parser.get_messages(message_type, limit=1000)
        if not all_messages:
            return []
        
        # Calculate time range
        total_messages = len(all_messages)
        start_idx = int(total_messages * start_percent / 100)
        end_idx = int(total_messages * end_percent / 100)
        
        return all_messages[start_idx:end_idx]

    def _get_anomaly_samples(self, parser, message_type: str) -> List:
        """Get samples that might contain anomalies or interesting events"""
        all_messages = parser.get_messages(message_type, limit=500)
        if not all_messages:
            return []
        
        anomaly_samples = []
        
        if message_type == "BATT":
            # Look for battery voltage drops
            for i, msg in enumerate(all_messages):
                voltage = msg.data.get('Volt', 12.0)
                if voltage < 11.5:  # Potential low voltage event
                    # Include context around the event
                    start_idx = max(0, i-5)
                    end_idx = min(len(all_messages), i+5)
                    anomaly_samples.extend(all_messages[start_idx:end_idx])
        
        elif message_type == "GPS":
            # Look for GPS quality issues or altitude changes
            for i, msg in enumerate(all_messages):
                hdop = msg.data.get('HDop', 1.0)
                if hdop > 2.5:  # Poor GPS quality
                    start_idx = max(0, i-3)
                    end_idx = min(len(all_messages), i+3)
                    anomaly_samples.extend(all_messages[start_idx:end_idx])
        
        elif message_type == "ATT":
            # Look for extreme attitude values
            for i, msg in enumerate(all_messages):
                roll = abs(msg.data.get('Roll', 0))
                pitch = abs(msg.data.get('Pitch', 0))
                if roll > 20 or pitch > 20:  # Extreme attitude
                    start_idx = max(0, i-3)
                    end_idx = min(len(all_messages), i+3)
                    anomaly_samples.extend(all_messages[start_idx:end_idx])
        
        # Remove duplicates and sort by timestamp
        unique_samples = []
        seen_timestamps = set()
        for msg in anomaly_samples:
            if msg.timestamp not in seen_timestamps:
                unique_samples.append(msg)
                seen_timestamps.add(msg.timestamp)
        
        # If no anomalies found, return distributed samples
        if not unique_samples:
            return self._get_distributed_samples(parser, message_type, count=50)
        
        return sorted(unique_samples, key=lambda x: x.timestamp)[:100]

    def _get_distributed_samples(self, parser, message_type: str, count: int) -> List:
        """Get evenly distributed samples across the flight"""
        all_messages = parser.get_messages(message_type, limit=1000)
        if not all_messages:
            return []
        
        if len(all_messages) <= count:
            return all_messages
        
        # Take every nth message to get even distribution
        step = len(all_messages) // count
        distributed_messages = []
        for i in range(0, len(all_messages), step):
            distributed_messages.append(all_messages[i])
            if len(distributed_messages) >= count:
                break
        
        return distributed_messages

    def _summarize_messages(self, message_type: str, messages: List, user_question: str) -> Optional[str]:
        """Summarizes a list of messages for a given type into human-readable insights"""
        if not messages:
            return None

        # Extract question intent for better summarization
        question_lower = user_question.lower()
        is_trend_question = any(word in question_lower for word in ['trend', 'change', 'over time', 'throughout'])
        is_max_min_question = any(word in question_lower for word in ['max', 'min', 'highest', 'lowest', 'peak'])
        is_problem_question = any(word in question_lower for word in ['problem', 'issue', 'error', 'warning', 'fail'])

        if message_type == "GPS":
            lats = [m.data.get('Lat') for m in messages if 'Lat' in m.data and m.data.get('Lat') != 0]
            lngs = [m.data.get('Lng') for m in messages if 'Lng' in m.data and m.data.get('Lng') != 0]
            alts = [m.data.get('Alt') for m in messages if 'Alt' in m.data]
            hdops = [m.data.get('HDop') for m in messages if 'HDop' in m.data]
            speeds = [m.data.get('Spd') for m in messages if 'Spd' in m.data]

            summary_parts = []
            
            if alts:
                alt_min, alt_max, alt_avg = min(alts), max(alts), sum(alts)/len(alts)
                summary_parts.append(f"Altitude: {alt_min:.1f}m to {alt_max:.1f}m (avg: {alt_avg:.1f}m)")
                
                if is_max_min_question:
                    summary_parts.append(f"Maximum altitude was {alt_max:.1f}m, minimum was {alt_min:.1f}m")
                
                if is_trend_question and len(messages) > 5:
                    first_alt = messages[0].data.get('Alt', 0)
                    last_alt = messages[-1].data.get('Alt', 0)
                    change = last_alt - first_alt
                    trend = "climbed" if change > 5 else "descended" if change < -5 else "remained stable"
                    summary_parts.append(f"Altitude trend: {trend} ({change:+.1f}m change from {first_alt:.1f}m to {last_alt:.1f}m)")

            if speeds:
                spd_min, spd_max, spd_avg = min(speeds), max(speeds), sum(speeds)/len(speeds)
                summary_parts.append(f"Ground speed: {spd_min:.1f} to {spd_max:.1f} m/s (avg: {spd_avg:.1f}m/s)")

            if hdops:
                hdop_avg = sum(hdops)/len(hdops)
                quality = "excellent" if hdop_avg < 1.0 else "good" if hdop_avg < 2.0 else "poor"
                summary_parts.append(f"GPS quality: {quality} (HDop avg: {hdop_avg:.2f})")

            if lats and lngs:
                lat_range = max(lats) - min(lats)
                lng_range = max(lngs) - min(lngs)
                if lat_range > 0.001 or lng_range > 0.001:  # Significant movement
                    summary_parts.append(f"Flight area: {lat_range:.4f}° lat × {lng_range:.4f}° lng")

            return " | ".join(summary_parts) if summary_parts else None

        elif message_type == "BATT":
            volts = [m.data.get('Volt') for m in messages if 'Volt' in m.data]
            currents = [m.data.get('Curr') for m in messages if 'Curr' in m.data]
            remainings = [m.data.get('RemPct') for m in messages if 'RemPct' in m.data]

            summary_parts = []
            
            if volts:
                volt_min, volt_max, volt_avg = min(volts), max(volts), sum(volts)/len(volts)
                summary_parts.append(f"Battery voltage: {volt_min:.2f}V to {volt_max:.2f}V (avg: {volt_avg:.2f}V)")
                
                # Battery health assessment
                if volt_min < 10.5:
                    summary_parts.append("⚠️ CRITICAL: Battery voltage dropped to critical levels")
                elif volt_min < 11.1:
                    summary_parts.append("⚠️ WARNING: Low battery voltage detected")
                
                if is_trend_question and len(volts) > 5:
                    voltage_drop = volts[0] - volts[-1]
                    summary_parts.append(f"Voltage trend: dropped {voltage_drop:.2f}V during flight")

            if currents:
                curr_min, curr_max, curr_avg = min(currents), max(currents), sum(currents)/len(currents)
                summary_parts.append(f"Current draw: {curr_min:.1f}A to {curr_max:.1f}A (avg: {curr_avg:.1f}A)")

            if remainings:
                rem_start, rem_end = remainings[0], remainings[-1]
                rem_used = rem_start - rem_end
                summary_parts.append(f"Battery used: {rem_used:.0f}% (from {rem_start:.0f}% to {rem_end:.0f}%)")

            return " | ".join(summary_parts) if summary_parts else None

        elif message_type == "ATT":
            rolls = [m.data.get('Roll') for m in messages if 'Roll' in m.data]
            pitches = [m.data.get('Pitch') for m in messages if 'Pitch' in m.data]
            yaws = [m.data.get('Yaw') for m in messages if 'Yaw' in m.data]

            summary_parts = []
            
            if rolls:
                roll_range = max(rolls) - min(rolls)
                roll_max_abs = max(abs(min(rolls)), abs(max(rolls)))
                stability = "unstable" if roll_range > 30 or roll_max_abs > 45 else "stable"
                summary_parts.append(f"Roll: ±{roll_max_abs:.1f}° max, {roll_range:.1f}° range ({stability})")

            if pitches:
                pitch_range = max(pitches) - min(pitches)
                pitch_max_abs = max(abs(min(pitches)), abs(max(pitches)))
                summary_parts.append(f"Pitch: ±{pitch_max_abs:.1f}° max, {pitch_range:.1f}° range")

            if yaws and len(yaws) > 5:
                yaw_changes = [abs(yaws[i] - yaws[i-1]) for i in range(1, len(yaws))]
                avg_yaw_rate = sum(yaw_changes) / len(yaw_changes) if yaw_changes else 0
                summary_parts.append(f"Yaw rate: {avg_yaw_rate:.1f}°/s average")

            return " | ".join(summary_parts) if summary_parts else None

        elif message_type == "CTUN":
            alts = [m.data.get('Alt') for m in messages if 'Alt' in m.data]
            climb_rates = [m.data.get('CRt') for m in messages if 'CRt' in m.data]
            throttles = [m.data.get('ThO') for m in messages if 'ThO' in m.data]

            summary_parts = []
            
            if alts:
                alt_min, alt_max = min(alts), max(alts)
                summary_parts.append(f"Control altitude: {alt_min:.1f}m to {alt_max:.1f}m")

            if climb_rates:
                max_climb = max(climb_rates)
                max_descent = min(climb_rates)
                summary_parts.append(f"Climb rate: +{max_climb:.1f} to {max_descent:.1f} m/s")

            if throttles:
                throttle_min, throttle_max, throttle_avg = min(throttles), max(throttles), sum(throttles)/len(throttles)
                summary_parts.append(f"Throttle: {throttle_min:.0f}% to {throttle_max:.0f}% (avg: {throttle_avg:.0f}%)")

            return " | ".join(summary_parts) if summary_parts else None

        elif message_type == "IMU":
            accel_x = [m.data.get('AccX') for m in messages if 'AccX' in m.data]
            accel_y = [m.data.get('AccY') for m in messages if 'AccY' in m.data]
            accel_z = [m.data.get('AccZ') for m in messages if 'AccZ' in m.data]

            summary_parts = []
            
            if accel_x and accel_y and accel_z:
                # Calculate vibration magnitude
                vibrations = []
                for i in range(len(accel_x)):
                    if i < len(accel_y) and i < len(accel_z):
                        magnitude = (accel_x[i]**2 + accel_y[i]**2 + accel_z[i]**2)**0.5
                        vibrations.append(magnitude)
                
                if vibrations:
                    vib_avg = sum(vibrations) / len(vibrations)
                    vib_level = "high" if vib_avg > 15 else "moderate" if vib_avg > 10 else "low"
                    summary_parts.append(f"Vibration: {vib_level} ({vib_avg:.1f}m/s² avg magnitude)")

            return " | ".join(summary_parts) if summary_parts else None

        elif message_type == "MSG":
            # Look for important messages
            msg_texts = [m.data.get('Message', '') for m in messages if 'Message' in m.data]
            
            important_msgs = []
            for msg_text in msg_texts:
                msg_lower = msg_text.lower()
                if any(word in msg_lower for word in ['error', 'fail', 'warn', 'critical', 'emergency']):
                    important_msgs.append(msg_text)
                elif any(word in msg_lower for word in ['armed', 'disarmed', 'mode', 'takeoff', 'land']):
                    important_msgs.append(msg_text)

            if important_msgs:
                return f"Key messages: {'; '.join(important_msgs[:5])}"  # Limit to 5 most important
            else:
                return f"System messages: {len(msg_texts)} routine messages"

        elif message_type == "ERR":
            # Error analysis
            error_codes = [m.data.get('Subsys') for m in messages if 'Subsys' in m.data]
            error_counts = {}
            for code in error_codes:
                if code:
                    error_counts[code] = error_counts.get(code, 0) + 1

            if error_counts:
                error_summary = [f"{subsys}: {count} errors" for subsys, count in error_counts.items()]
                return f"Errors detected: {'; '.join(error_summary)}"
            else:
                return "No specific errors identified"

        # Fallback for other message types
        return f"{message_type} data: {len(messages)} messages from {messages[0].timestamp:.1f}s to {messages[-1].timestamp:.1f}s"

# Global instance
log_tools = LogTools()

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