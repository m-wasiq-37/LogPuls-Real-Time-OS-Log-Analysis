import urllib.request
import urllib.parse
import json
import sys
import os
from datetime import datetime
from typing import List, Dict, Any


def get_windows_logs(log_type: str = "All", hours: int = 24, max_events: int = 1000) -> List[Dict[str, Any]]:
    try:
        collector_host = os.getenv("LOG_COLLECTOR_HOST", "log-collector")
        collector_port = os.getenv("LOG_COLLECTOR_PORT", "5000")
        url = f"http://{collector_host}:{collector_port}/collect"
        
        data = {
            "log_type": log_type,
            "hours": hours,
            "max_events": max_events
        }
        data_json = json.dumps(data).encode('utf-8')
        
        req = urllib.request.Request(url, data=data_json, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=120) as response:
            output = response.read().decode('utf-8')
            events = json.loads(output)
            
            if not isinstance(events, list):
                events = [events] if events else []
            
            return events
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"HTTP Error {e.code}: {error_body}", file=sys.stderr)
        return []
    except urllib.error.URLError as e:
        print(f"URL Error: {e}", file=sys.stderr)
        print(f"Log collector service may not be running at {url}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error fetching logs: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return []


def get_logs_filtered(filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    if filters is None:
        filters = {}
    
    log_type = filters.get("log_type", "All")
    hours = filters.get("hours", 24)
    max_events = filters.get("max_events", 1000)
    
    logs = get_windows_logs(log_type, hours, max_events)
    
    level_filter = filters.get("level")
    event_id_filter = filters.get("event_id")
    
    if level_filter:
        logs = [log for log in logs if log.get("level") == level_filter]
    
    if event_id_filter:
        logs = [log for log in logs if log.get("event_id") == event_id_filter]
    
    return logs


if __name__ == "__main__":
    print("Fetching Windows logs...")
    logs = get_windows_logs(log_type="All", hours=24, max_events=100)
    print(f"Retrieved {len(logs)} log entries")
    if logs:
        print("\nSample log entry:")
        print(json.dumps(logs[0], indent=2))
