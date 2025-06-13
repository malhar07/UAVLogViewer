# server/core.py
from dataclasses import dataclass
from pymavlink import mavutil
import itertools, statistics, uuid, tempfile, os
from typing import List, Dict, Any, Optional

@dataclass
class MAVMessage:
    timestamp: float
    msg_type: str
    data: Dict[str, Any]

class LogParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.connection = None
        self._messages_cache = None
    
    def _get_connection(self):
        """Get a fresh mavlink connection"""
        if self.connection:
            try:
                self.connection.close()
            except:
                pass
        self.connection = mavutil.mavlink_connection(self.file_path)
        return self.connection
    
    def get_messages(self, force_refresh=False) -> List[MAVMessage]:
        """Get all messages from the log file, with caching"""
        if self._messages_cache is not None and not force_refresh:
            return self._messages_cache
        
        messages = []
        conn = self._get_connection()
        
        try:
            while True:
                msg = conn.recv_match(blocking=False)
                if msg is None:
                    break
                
                # Convert to our format
                mav_msg = MAVMessage(
                    timestamp=msg._timestamp,
                    msg_type=msg.get_type(),
                    data={k: v for k, v in msg.to_dict().items() 
                          if not k.startswith('_') and k != 'mavpackettype'}
                )
                messages.append(mav_msg)
                
                # Limit to prevent memory issues
                if len(messages) > 50000:
                    break
                    
        except Exception as e:
            print(f"Error reading log: {e}")
            
        self._messages_cache = messages
        return messages

class LogAnalyzer:
    def __init__(self, parser: LogParser):
        self.parser = parser
    
    def get_summary(self) -> Dict[str, Any]:
        """Get basic log summary"""
        try:
            messages = self.parser.get_messages()
            if not messages:
                return {"error": "No messages found in log"}
            
            msg_types = set(msg.msg_type for msg in messages)
            first_time = messages[0].timestamp
            last_time = messages[-1].timestamp
            duration = last_time - first_time
            
            return {
                "total_messages": len(messages),
                "message_types": sorted(list(msg_types)),
                "duration_seconds": round(duration, 2),
                "start_time": first_time,
                "end_time": last_time,
                "log_file": os.path.basename(self.parser.file_path)
            }
        except Exception as e:
            return {"error": f"Failed to analyze log: {str(e)}"}
    
    def get_highest_altitude(self) -> Dict[str, Any]:
        """Find the highest altitude from GPS data"""
        try:
            messages = self.parser.get_messages()
            gps_messages = [msg for msg in messages if msg.msg_type == "GPS"]
            
            if not gps_messages:
                return {"error": "No GPS messages found"}
            
            altitudes = []
            for msg in gps_messages:
                alt = msg.data.get("Alt", 0)
                if alt and alt > 0:  # Filter out invalid readings
                    altitudes.append(alt)
            
            if not altitudes:
                return {"error": "No valid altitude data found"}
            
            max_alt = max(altitudes)
            avg_alt = sum(altitudes) / len(altitudes)
            
            return {
                "highest_altitude_mm": max_alt,
                "highest_altitude_m": round(max_alt / 1000, 2),
                "average_altitude_m": round(avg_alt / 1000, 2),
                "total_gps_readings": len(altitudes)
            }
        except Exception as e:
            return {"error": f"Failed to analyze altitude: {str(e)}"}
    
    def detect_gps_issues(self) -> Dict[str, Any]:
        """Detect GPS signal loss or poor accuracy"""
        try:
            messages = self.parser.get_messages()
            gps_messages = [msg for msg in messages if msg.msg_type == "GPS"]
            
            if not gps_messages:
                return {"error": "No GPS messages found"}
            
            poor_signal_events = []
            signal_loss_events = []
            
            for msg in gps_messages:
                hdop = msg.data.get("HDop", 0)
                fix_type = msg.data.get("FixType", 0)
                
                if hdop > 3.0:  # Poor accuracy
                    poor_signal_events.append({
                        "timestamp": msg.timestamp,
                        "hdop": hdop
                    })
                
                if fix_type < 3:  # No 3D fix
                    signal_loss_events.append({
                        "timestamp": msg.timestamp,
                        "fix_type": fix_type
                    })
            
            return {
                "total_gps_messages": len(gps_messages),
                "poor_signal_events": len(poor_signal_events),
                "signal_loss_events": len(signal_loss_events),
                "first_poor_signal": poor_signal_events[0]["timestamp"] if poor_signal_events else None,
                "first_signal_loss": signal_loss_events[0]["timestamp"] if signal_loss_events else None
            }
        except Exception as e:
            return {"error": f"Failed to analyze GPS: {str(e)}"}

class LogManager:
    def __init__(self):
        self.logs: Dict[str, LogParser] = {}
        self.analyzers: Dict[str, LogAnalyzer] = {}
        self.temp_files: Dict[str, str] = {}  # Track temp files for cleanup
    
    def load_log(self, file_path: str) -> str:
        """Load a log file and return a unique ID"""
        log_id = uuid.uuid4().hex[:8]
        
        try:
            parser = LogParser(file_path)
            analyzer = LogAnalyzer(parser)
            
            # Test that we can read the file
            summary = analyzer.get_summary()
            if "error" in summary:
                raise Exception(summary["error"])
            
            self.logs[log_id] = parser
            self.analyzers[log_id] = analyzer
            
            return log_id
        except Exception as e:
            raise Exception(f"Failed to load log: {str(e)}")
    
    def store_log(self, log_id: str, content: bytes) -> bool:
        """Store log content to a temporary file and create analyzer"""
        try:
            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix='.bin', prefix=f'uav_log_{log_id}_')
            
            # Write content to temp file
            with os.fdopen(temp_fd, 'wb') as temp_file:
                temp_file.write(content)
            
            # Create parser and analyzer
            parser = LogParser(temp_path)
            analyzer = LogAnalyzer(parser)
            
            # Test that we can read the file
            summary = analyzer.get_summary()
            if "error" in summary:
                # Clean up temp file on error
                os.unlink(temp_path)
                raise Exception(f"Invalid log file: {summary['error']}")
            
            # Store references
            self.logs[log_id] = parser
            self.analyzers[log_id] = analyzer
            self.temp_files[log_id] = temp_path
            
            return True
            
        except Exception as e:
            print(f"Failed to store log {log_id}: {str(e)}")
            return False
    
    def get_analyzer(self, log_id: str) -> Optional[LogAnalyzer]:
        """Get analyzer for a log ID"""
        return self.analyzers.get(log_id)
    
    def remove_log(self, log_id: str):
        """Remove a log from memory and clean up temp file"""
        if log_id in self.logs:
            try:
                self.logs[log_id].connection.close()
            except:
                pass
            del self.logs[log_id]
            del self.analyzers[log_id]
            
            # Clean up temp file
            if log_id in self.temp_files:
                try:
                    os.unlink(self.temp_files[log_id])
                except:
                    pass
                del self.temp_files[log_id]

# Global instance
LOG_MANAGER = LogManager() 