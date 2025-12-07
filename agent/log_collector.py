import subprocess
import json
import sys
import os
from datetime import datetime
from typing import List, Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
import tempfile


class LogCollectorHandler(BaseHTTPRequestHandler):
    
    def do_POST(self):
        if self.path == '/collect':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                log_type = data.get('log_type', 'All')
                hours = data.get('hours', 24)
                max_events = data.get('max_events', 1000)
                
                logs = self.collect_windows_logs(log_type, hours, max_events)
                
                response = json.dumps(logs).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(response)))
                self.end_headers()
                self.wfile.write(response)
                
            except Exception as e:
                error_msg = json.dumps({"error": str(e)}).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(error_msg)))
                self.end_headers()
                self.wfile.write(error_msg)
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass
    
    def collect_windows_logs(self, log_type: str, hours: int, max_events: int) -> List[Dict[str, Any]]:
        try:
            if log_type == "All":
                ps_script = f"""
$ErrorActionPreference = 'Stop'
try {{
    $events = Get-WinEvent -FilterHashtable @{{LogName='System','Application','Security'}} -MaxEvents {max_events} -ErrorAction SilentlyContinue | 
        Where-Object {{$_.TimeCreated -ge (Get-Date).AddHours(-{hours})}} | 
        Select-Object -First {max_events} TimeCreated, Id, LevelDisplayName, LogName, ProviderName, Message, MachineName
    if ($events) {{
        $events | ConvertTo-Json -Depth 10 -Compress
    }} else {{
        '[]'
    }}
}} catch {{
    '[]'
}}
"""
            else:
                ps_script = f"""
$ErrorActionPreference = 'Stop'
try {{
    $events = Get-WinEvent -FilterHashtable @{{LogName='{log_type}'}} -MaxEvents {max_events} -ErrorAction SilentlyContinue | 
        Where-Object {{$_.TimeCreated -ge (Get-Date).AddHours(-{hours})}} | 
        Select-Object -First {max_events} TimeCreated, Id, LevelDisplayName, LogName, ProviderName, Message, MachineName
    if ($events) {{
        $events | ConvertTo-Json -Depth 10 -Compress
    }} else {{
        '[]'
    }}
}} catch {{
    '[]'
}}
"""
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False) as f:
                    f.write(ps_script)
                    temp_script = f.name
                
                try:
                    docker_cmd = [
                        "docker", "run", "--rm",
                        "-v", f"{temp_script}:/script.ps1:ro",
                        "mcr.microsoft.com/powershell:lts-nanoserver-1809",
                        "powershell", "-ExecutionPolicy", "Bypass", "-File", "/script.ps1"
                    ]
                    
                    result = subprocess.run(
                        docker_cmd,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        output = result.stdout.strip()
                        try:
                            events = json.loads(output)
                            if not isinstance(events, list):
                                events = [events] if events else []
                            os.unlink(temp_script)
                            return self._normalize_logs(events)
                        except json.JSONDecodeError as je:
                            print(f"JSON decode error: {je}. Output: {output[:500]}", file=sys.stderr)
                    else:
                        print(f"Docker PowerShell failed: {result.stderr[:500]}", file=sys.stderr)
                finally:
                    if os.path.exists(temp_script):
                        os.unlink(temp_script)
                        
            except FileNotFoundError:
                print("Docker command not found. Trying alternative methods...", file=sys.stderr)
            except subprocess.TimeoutExpired:
                print("PowerShell command timed out", file=sys.stderr)
            except Exception as e:
                print(f"Error with Docker method: {e}", file=sys.stderr)
            
            try:
                powershell_paths = [
                    "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
                    "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/pwsh.exe",
                ]
                
                for ps_path in powershell_paths:
                    if os.path.exists(ps_path):
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False) as f:
                            f.write(ps_script)
                            temp_script = f.name
                        
                        try:
                            result = subprocess.run(
                                [ps_path, "-ExecutionPolicy", "Bypass", "-File", temp_script],
                                capture_output=True,
                                text=True,
                                timeout=120
                            )
                            
                            if result.returncode == 0 and result.stdout.strip():
                                output = result.stdout.strip()
                                try:
                                    events = json.loads(output)
                                    if not isinstance(events, list):
                                        events = [events] if events else []
                                    os.unlink(temp_script)
                                    return self._normalize_logs(events)
                                except json.JSONDecodeError:
                                    print(f"Invalid JSON from PowerShell: {output[:200]}", file=sys.stderr)
                        finally:
                            if os.path.exists(temp_script):
                                os.unlink(temp_script)
            except Exception as e:
                print(f"Error with WSL method: {e}", file=sys.stderr)
            
            error_msg = (
                "Warning: Could not execute PowerShell to collect Windows logs. "
                "This is expected if running in a Linux container without Windows container support. "
                "To collect logs, you need either:\n"
                "1. Docker Desktop with Windows container support enabled, OR\n"
                "2. WSL installed with access to Windows PowerShell, OR\n"
                "3. A separate Windows service/script running on the host"
            )
            print(error_msg, file=sys.stderr)
            return []
            
        except Exception as e:
            print(f"Error collecting logs: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return []
    
    def _normalize_logs(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized_logs = []
        for event in events:
            try:
                timestamp = event.get("TimeCreated")
                if timestamp:
                    if isinstance(timestamp, str) and timestamp.startswith("/Date("):
                        import re
                        match = re.search(r'/Date\((\d+)', timestamp)
                        if match:
                            timestamp = datetime.fromtimestamp(int(match.group(1)) / 1000).isoformat()
                    elif not isinstance(timestamp, str):
                        timestamp = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
                else:
                    timestamp = datetime.now().isoformat()
                
                log_entry = {
                    "timestamp": timestamp,
                    "event_id": int(event.get("Id", 0)) if event.get("Id") else 0,
                    "level": str(event.get("LevelDisplayName", "Information")),
                    "log_name": str(event.get("LogName", "Unknown")),
                    "provider": str(event.get("ProviderName", "Unknown")),
                    "message": str(event.get("Message", "")),
                    "machine_name": str(event.get("MachineName", "Unknown")),
                    "collected_at": datetime.now().isoformat()
                }
                normalized_logs.append(log_entry)
            except Exception as e:
                print(f"Error processing event: {e}", file=sys.stderr)
                continue
        
        return normalized_logs


def run_server(port=5000):
    server = HTTPServer(('0.0.0.0', port), LogCollectorHandler)
    print(f"Log Collector Server started on port {port}")
    print("Waiting for requests...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


if __name__ == "__main__":
    port = int(os.getenv('LOG_COLLECTOR_PORT', '5000'))
    run_server(port)
