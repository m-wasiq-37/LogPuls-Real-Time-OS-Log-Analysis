import win32evtlog
import win32api
import sys
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

def read_windows_logs_fast():
    log_names = ['Application', 'System', 'Setup', 'Windows PowerShell']
    
    logs = []

    for log_name in log_names:
        try:
            h_log = win32evtlog.OpenEventLog(None, log_name)
        except win32api.error as e:
            continue

        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

        try:
            while True:
                events = win32evtlog.ReadEventLog(h_log, flags, 0, 100)
                
                if not events:
                    break

                for event in events:
                    event_time_object = event.TimeGenerated 
                    
                    if event.EventType in (1, 2, 3):
                        level_display = {
                            1: 'Critical', 
                            2: 'Error', 
                            3: 'Warning'
                        }.get(event.EventType, 'Unknown')

                        message = event.StringInserts[0].splitlines()[0] if event.StringInserts and event.StringInserts[0] else 'No Message'
                        
                        log_entry = {
                            "timestamp": event_time_object.strftime('%Y-%m-%dT%H:%M:%S'),
                            "event_id": event.EventID & 0xFFFF,
                            "level": level_display,
                            "log_name": log_name,
                            "provider": event.SourceName,
                            "message": message,
                            "machine_name": "Unknown",
                            "collected_at": datetime.now().isoformat()
                        }
                        logs.append(log_entry)

        finally:
            win32evtlog.CloseEventLog(h_log)

    return logs

class CollectorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/collect':
            try:
                logs = read_windows_logs_fast()
                response = json.dumps(logs).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(response)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response)
            except Exception as e:
                error_msg = json.dumps({"error": str(e)}).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_msg)
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    port = int(os.getenv('COLLECTOR_PORT', '5001'))
    server = HTTPServer(('0.0.0.0', port), CollectorHandler)
    print(f"Windows Log Collector Server started on port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()

