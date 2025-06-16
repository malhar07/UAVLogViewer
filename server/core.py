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
        self._start_time = None
    
    def _get_relative_time(self, absolute_timestamp: float) -> float:
        """Convert absolute timestamp to relative time from start of log"""
        if self._start_time is None:
            messages = self.parser.get_messages()
            if messages:
                self._start_time = messages[0].timestamp
            else:
                self._start_time = 0
        return round(absolute_timestamp - self._start_time, 2)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get enhanced log summary with accurate duration calculation"""
        try:
            messages = self.parser.get_messages()
            if not messages:
                return {"error": "No messages found in log"}
            
            msg_types = set(msg.msg_type for msg in messages)
            first_time = messages[0].timestamp
            last_time = messages[-1].timestamp
            duration = last_time - first_time
            
            # Set start time for relative calculations
            self._start_time = first_time
            
            return {
                "total_messages": len(messages),
                "message_types": sorted(list(msg_types)),
                "duration_seconds": round(duration, 2),
                "start_time_unix": first_time,
                "end_time_unix": last_time,
                "log_file": os.path.basename(self.parser.file_path)
            }
        except Exception as e:
            return {"error": f"Failed to analyze log: {str(e)}"}
    
    def get_altitude_series(self) -> List[Dict[str, float]]:
        """Get time-series altitude data in standard units (meters)"""
        try:
            messages = self.parser.get_messages()
            
            altitude_data = []
            
            # Try GPS messages first
            gps_messages = [msg for msg in messages if msg.msg_type == "GPS"]
            for msg in gps_messages:
                alt_mm = msg.data.get("Alt", 0)
                if alt_mm is not None and alt_mm > 0:
                    altitude_data.append({
                        "time_s": self._get_relative_time(msg.timestamp),
                        "altitude_m": round(alt_mm / 1000.0, 2),  # Convert mm to meters
                        "timestamp": msg.timestamp
                    })
            
            # If no GPS altitude, try barometer data
            if not altitude_data:
                baro_messages = [msg for msg in messages if msg.msg_type == "BARO"]
                for msg in baro_messages:
                    alt_m = msg.data.get("Alt", 0)
                    if alt_m is not None:
                        altitude_data.append({
                            "time_s": self._get_relative_time(msg.timestamp),
                            "altitude_m": round(alt_m, 2),  # Already in meters
                            "timestamp": msg.timestamp
                        })
            
            # If still no altitude, try EKF position data
            if not altitude_data:
                ekf_messages = [msg for msg in messages if msg.msg_type in ["XKF1", "NKF1"]]
                for msg in ekf_messages:
                    alt_m = msg.data.get("PD", 0)  # Down position (negative)
                    if alt_m is not None:
                        altitude_data.append({
                            "time_s": self._get_relative_time(msg.timestamp),
                            "altitude_m": round(-alt_m, 2),  # Convert negative down to positive altitude
                            "timestamp": msg.timestamp
                        })
            
            return altitude_data
        except Exception as e:
            return [{"error": f"Failed to get altitude series: {str(e)}"}]
    
    def get_gps_coords_series(self) -> List[Dict[str, Any]]:
        """Get time-series GPS coordinate data with all relevant parameters"""
        try:
            messages = self.parser.get_messages()
            
            # Try multiple message types for GPS data
            gps_messages = []
            
            # Standard GPS messages
            gps_messages.extend([msg for msg in messages if msg.msg_type == "GPS"])
            
            # ArduPilot specific: Position from EKF
            gps_messages.extend([msg for msg in messages if msg.msg_type in ["POS", "GPOS"]])
            
            # If no GPS messages, try extracting from EKF (Extended Kalman Filter) data
            if not gps_messages:
                gps_messages.extend([msg for msg in messages if msg.msg_type in ["XKF1", "NKF1"]])
            
            gps_data = []
            for msg in gps_messages:
                data = msg.data
                
                # Handle different message types
                if msg.msg_type == "GPS":
                    if data.get("Lat") and data.get("Lng"):
                        gps_point = {
                            "time_s": self._get_relative_time(msg.timestamp),
                            "latitude": data.get("Lat", 0) / 1e7,  # Convert to decimal degrees
                            "longitude": data.get("Lng", 0) / 1e7,  # Convert to decimal degrees
                            "altitude_m": round(data.get("Alt", 0) / 1000.0, 2),  # mm to meters
                            "fix_type": data.get("FixType", 0),
                            "satellites": data.get("NSats", 0),
                            "hdop": data.get("HDop", 0) / 100.0,  # Convert to standard HDOP
                            "speed_ms": round(data.get("Spd", 0) / 100.0, 2),  # cm/s to m/s
                            "course_deg": data.get("GCrs", 0) / 100.0,  # Convert to degrees
                            "timestamp": msg.timestamp
                        }
                        gps_data.append(gps_point)
                
                elif msg.msg_type in ["POS", "GPOS"]:
                    if data.get("Lat") and data.get("Lng"):
                        gps_point = {
                            "time_s": self._get_relative_time(msg.timestamp),
                            "latitude": data.get("Lat", 0),  # Already in decimal degrees
                            "longitude": data.get("Lng", 0),  # Already in decimal degrees
                            "altitude_m": round(data.get("Alt", 0), 2),  # Already in meters
                            "fix_type": 3,  # Assume 3D fix for POS messages
                            "satellites": data.get("NSats", 0),
                            "hdop": data.get("HDop", 1.0),  # Default HDOP
                            "speed_ms": round(data.get("Spd", 0), 2),  # Already in m/s
                            "course_deg": data.get("GCrs", 0),  # Already in degrees
                            "timestamp": msg.timestamp
                        }
                        gps_data.append(gps_point)
                
                elif msg.msg_type in ["XKF1", "NKF1"]:
                    # EKF position data
                    if data.get("PN") is not None and data.get("PE") is not None:
                        # EKF gives North/East position in meters from origin
                        # Convert to approximate lat/lon (this is rough approximation)
                        lat_approx = data.get("PN", 0) / 111320.0  # meters to degrees (rough)
                        lng_approx = data.get("PE", 0) / 111320.0  # meters to degrees (rough)
                        
                        gps_point = {
                            "time_s": self._get_relative_time(msg.timestamp),
                            "latitude": lat_approx,
                            "longitude": lng_approx,
                            "altitude_m": round(data.get("PD", 0), 2),  # Down position (negative altitude)
                            "fix_type": 3,  # Assume 3D fix
                            "satellites": 8,  # Default for EKF
                            "hdop": 1.0,  # Default HDOP
                            "speed_ms": round((data.get("VN", 0)**2 + data.get("VE", 0)**2)**0.5, 2),  # Speed from N/E velocity
                            "course_deg": 0,  # Not easily available from EKF
                            "timestamp": msg.timestamp
                        }
                        gps_data.append(gps_point)
            
            return gps_data
        except Exception as e:
            return [{"error": f"Failed to get GPS series: {str(e)}"}]
    
    def get_battery_series(self) -> List[Dict[str, float]]:
        """Get time-series battery data in standard units (Volts, Amps)"""
        try:
            messages = self.parser.get_messages()
            battery_messages = [msg for msg in messages if msg.msg_type in ["BAT", "CURR"]]
            
            battery_data = []
            for msg in battery_messages:
                data = msg.data
                battery_point = {
                    "time_s": self._get_relative_time(msg.timestamp),
                    "timestamp": msg.timestamp
                }
                
                # Handle different battery message types
                if msg.msg_type == "BAT":
                    # ArduPilot BAT messages: Volt is in centivolts (V*100)
                    battery_point.update({
                        "voltage_v": round(data.get("Volt", 0) / 100.0, 2),  # cV to V
                        "current_a": round(data.get("Curr", 0) / 100.0, 2),  # cA to A
                        "consumed_mah": data.get("CurrTot", 0)
                    })
                elif msg.msg_type == "CURR":
                    # CURR messages also use centivolts and centiamps
                    battery_point.update({
                        "voltage_v": round(data.get("Volt", 0) / 100.0, 2),  # cV to V
                        "current_a": round(data.get("Curr", 0) / 100.0, 2),  # cA to A
                        "consumed_mah": data.get("CurrTot", 0)
                    })
                
                battery_data.append(battery_point)
            
            return battery_data
        except Exception as e:
            return [{"error": f"Failed to get battery series: {str(e)}"}]
    
    def get_speed_series(self) -> List[Dict[str, float]]:
        """Get time-series speed data in standard units (m/s)"""
        try:
            messages = self.parser.get_messages()
            
            speed_data = []
            
            # Try GPS speed first
            gps_messages = [msg for msg in messages if msg.msg_type == "GPS"]
            for msg in gps_messages:
                spd_cms = msg.data.get("Spd", 0)
                if spd_cms is not None:
                    speed_data.append({
                        "time_s": self._get_relative_time(msg.timestamp),
                        "speed_ms": round(spd_cms / 100.0, 2),  # cm/s to m/s
                        "source": "GPS",
                        "timestamp": msg.timestamp
                    })
            
            # Try airspeed if available
            airspeed_messages = [msg for msg in messages if msg.msg_type == "ARSP"]
            for msg in airspeed_messages:
                airspeed = msg.data.get("Airspeed", 0)
                if airspeed is not None:
                    speed_data.append({
                        "time_s": self._get_relative_time(msg.timestamp),
                        "speed_ms": round(airspeed, 2),  # Already in m/s
                        "source": "Airspeed",
                        "timestamp": msg.timestamp
                    })
            
            # If no GPS or airspeed, try EKF velocity data
            if not speed_data:
                ekf_messages = [msg for msg in messages if msg.msg_type in ["XKF1", "NKF1"]]
                for msg in ekf_messages:
                    vn = msg.data.get("VN", 0)  # North velocity
                    ve = msg.data.get("VE", 0)  # East velocity
                    if vn is not None and ve is not None:
                        ground_speed = round((vn**2 + ve**2)**0.5, 2)
                        speed_data.append({
                            "time_s": self._get_relative_time(msg.timestamp),
                            "speed_ms": ground_speed,
                            "source": "EKF",
                            "timestamp": msg.timestamp
                        })
            
            return sorted(speed_data, key=lambda x: x["time_s"])
        except Exception as e:
            return [{"error": f"Failed to get speed series: {str(e)}"}]
    
    def get_vibration_series(self) -> List[Dict[str, float]]:
        """Get time-series vibration data"""
        try:
            messages = self.parser.get_messages()
            vibe_messages = [msg for msg in messages if msg.msg_type == "VIBE"]
            
            vibe_data = []
            for msg in vibe_messages:
                data = msg.data
                vibe_data.append({
                    "time_s": self._get_relative_time(msg.timestamp),
                    "vibe_x": round(data.get("VibeX", 0), 2),
                    "vibe_y": round(data.get("VibeY", 0), 2),
                    "vibe_z": round(data.get("VibeZ", 0), 2),
                    "clipping_x": data.get("Clip0", 0),
                    "clipping_y": data.get("Clip1", 0),
                    "clipping_z": data.get("Clip2", 0),
                    "timestamp": msg.timestamp
                })
            
            return vibe_data
        except Exception as e:
            return [{"error": f"Failed to get vibration series: {str(e)}"}]
    
    def get_mode_changes(self) -> List[Dict[str, Any]]:
        """Get flight mode changes with timestamps"""
        try:
            messages = self.parser.get_messages()
            mode_messages = [msg for msg in messages if msg.msg_type == "MODE"]
            
            mode_changes = []
            for msg in mode_messages:
                data = msg.data
                mode_changes.append({
                    "time_s": self._get_relative_time(msg.timestamp),
                    "mode_num": data.get("ModeNum", 0),
                    "mode": data.get("Mode", "Unknown"),
                    "reason": data.get("Rsn", "Unknown"),
                    "timestamp": msg.timestamp
                })
            
            return mode_changes
        except Exception as e:
            return [{"error": f"Failed to get mode changes: {str(e)}"}]
    
    def get_significant_events(self) -> List[Dict[str, Any]]:
        """Get significant events (errors, warnings, state changes)"""
        try:
            messages = self.parser.get_messages()
            
            events = []
            
            # Error messages
            error_messages = [msg for msg in messages if msg.msg_type in ["ERR", "EV"]]
            for msg in error_messages:
                data = msg.data
                events.append({
                    "time_s": self._get_relative_time(msg.timestamp),
                    "type": "error" if msg.msg_type == "ERR" else "event",
                    "severity": "high" if msg.msg_type == "ERR" else "medium",
                    "message": data.get("Subsys", "Unknown"),
                    "error_code": data.get("ECode", 0),
                    "timestamp": msg.timestamp
                })
            
            # MSG (text messages)
            msg_messages = [msg for msg in messages if msg.msg_type == "MSG"]
            for msg in msg_messages:
                data = msg.data
                events.append({
                    "time_s": self._get_relative_time(msg.timestamp),
                    "type": "message",
                    "severity": "low",
                    "message": data.get("Message", ""),
                    "timestamp": msg.timestamp
                })
            
            return sorted(events, key=lambda x: x["time_s"])
        except Exception as e:
            return [{"error": f"Failed to get significant events: {str(e)}"}]
    
    def get_highest_altitude(self) -> Dict[str, Any]:
        """Find the highest altitude from GPS data with enhanced accuracy"""
        try:
            altitude_series = self.get_altitude_series()
            if not altitude_series or "error" in altitude_series[0]:
                return {"error": "No valid altitude data found"}
            
            altitudes = [point["altitude_m"] for point in altitude_series]
            max_alt = max(altitudes)
            avg_alt = sum(altitudes) / len(altitudes)
            
            # Find the time when max altitude occurred
            max_alt_time = next(point["time_s"] for point in altitude_series 
                              if point["altitude_m"] == max_alt)
            
            return {
                "highest_altitude_m": max_alt,
                "average_altitude_m": round(avg_alt, 2),
                "max_altitude_time_s": max_alt_time,
                "total_gps_readings": len(altitude_series)
            }
        except Exception as e:
            return {"error": f"Failed to analyze altitude: {str(e)}"}
    
    def detect_gps_issues(self) -> Dict[str, Any]:
        """Enhanced GPS issue detection with detailed analysis"""
        try:
            gps_series = self.get_gps_coords_series()
            if not gps_series or "error" in gps_series[0]:
                return {"error": "No GPS data found"}
            
            poor_signal_events = []
            signal_loss_events = []
            
            for point in gps_series:
                if point["hdop"] > 3.0:  # Poor accuracy
                    poor_signal_events.append({
                        "time_s": point["time_s"],
                        "hdop": point["hdop"],
                        "satellites": point["satellites"]
                    })
                
                if point["fix_type"] < 3:  # No 3D fix
                    signal_loss_events.append({
                        "time_s": point["time_s"],
                        "fix_type": point["fix_type"],
                        "satellites": point["satellites"]
                    })
            
            return {
                "total_gps_readings": len(gps_series),
                "poor_signal_events": len(poor_signal_events),
                "signal_loss_events": len(signal_loss_events),
                "first_poor_signal_time_s": poor_signal_events[0]["time_s"] if poor_signal_events else None,
                "first_signal_loss_time_s": signal_loss_events[0]["time_s"] if signal_loss_events else None,
                "poor_signal_details": poor_signal_events[:5],  # First 5 events
                "signal_loss_details": signal_loss_events[:5]   # First 5 events
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
    
    def list_logs(self) -> List[Dict[str, Any]]:
        """List all stored logs with metadata"""
        logs_info = []
        for log_id, analyzer in self.analyzers.items():
            summary = analyzer.get_summary()
            if "error" not in summary:
                logs_info.append({
                    "log_id": log_id,
                    "duration_seconds": summary["duration_seconds"],
                    "total_messages": summary["total_messages"],
                    "message_types_count": len(summary["message_types"]),
                    "log_file": summary["log_file"]
                })
        return logs_info
    
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