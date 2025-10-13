import time, os
from sample_logs import sample_stream
import requests
target = os.getenv('AGENT_TARGET', 'http://backend:8000/api/logs/ingest')
token = os.getenv('AGENT_TOKEN','')
for e in sample_stream():
    headers = {'Content-Type':'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    try:
        requests.post(target, json=e, headers=headers, timeout=3)
    except:
        pass
    time.sleep(2)
