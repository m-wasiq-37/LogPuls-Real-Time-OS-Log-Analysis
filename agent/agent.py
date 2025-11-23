import os
import platform
import subprocess
import time
import socket
import json
from typing import List

import requests

AGENT_TARGET = os.getenv('AGENT_TARGET', 'http://backend:8000/api/logs/ingest')
AGENT_TOKEN = os.getenv('AGENT_TOKEN', '')
AGENT_LINES = int(os.getenv('AGENT_LINES', '10'))
SLEEP_SECONDS = float(os.getenv('AGENT_SLEEP', '5'))


def read_windows_lines(max_lines: int) -> (List[str], bool, str):
    """Attempt to gather recent Windows event/sys logs as plain text lines.
    Returns (lines, truncated_flag, source_identifier)
    """
    desktop_log = os.path.expanduser('~') + "\\Desktop\\WindowsUpdate.log"
    if os.path.exists(desktop_log):
        with open(desktop_log, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            truncated = len(all_lines) > max_lines
            return [l.rstrip('\n') for l in all_lines[:max_lines]], truncated, desktop_log

    
    try:
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Get-WinEvent -LogName System -MaxEvents {max_lines * 5} | Format-List -Property TimeCreated,LevelDisplayName,Message"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        text = result.stdout or result.stderr or ''
        lines = [ln for ln in text.splitlines() if ln.strip()]
        truncated = len(lines) > max_lines
        return lines[:max_lines], truncated, 'Windows:SystemEvent'
    except Exception:
        return [], False, 'windows'


def read_linux_lines(max_lines: int) -> (List[str], bool, str):
    possible_logs = ['/var/log/syslog', '/var/log/messages', '/var/log/kern.log']
    for path in possible_logs:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    all_lines = f.readlines()
                    truncated = len(all_lines) > max_lines
                    return [l.rstrip('\n') for l in all_lines[:max_lines]], truncated, path
            except Exception:
                continue
    try:
        result = subprocess.run(['journalctl', '-n', str(max_lines), '--no-pager', '--output=short'], capture_output=True, text=True, timeout=5)
        lines = [ln for ln in (result.stdout or '').splitlines() if ln.strip()]
        truncated = False
        return lines[:max_lines], truncated, 'journalctl'
    except Exception:
        return [], False, 'linux'


def send_batch(lines: List[str], source: str, truncated: bool):
    if not lines:
        return False
    payload = {
        'lines': lines,
        'source': source,
        'agent': socket.gethostname(),
        'truncated': bool(truncated),
        'timestamp': None
    }
    headers = {'Content-Type': 'application/json'}
    if AGENT_TOKEN:
        headers['Authorization'] = 'Bearer ' + AGENT_TOKEN

    try:
        resp = requests.post(AGENT_TARGET, json=payload, headers=headers, timeout=5)
        return resp.ok
    except Exception:
        return False


def main_loop():
    current_os = platform.system().lower()
    while True:
        if current_os == 'windows':
            lines, truncated, src = read_windows_lines(AGENT_LINES)
        elif current_os == 'linux':
            lines, truncated, src = read_linux_lines(AGENT_LINES)
        else:
            lines, truncated, src = [], False, 'unsupported'

        if lines:
            success = send_batch(lines, src, truncated)
            if not success:
                time.sleep(1)
                send_batch(lines, src, truncated)

        time.sleep(SLEEP_SECONDS)


if __name__ == '__main__':
    main_loop()
