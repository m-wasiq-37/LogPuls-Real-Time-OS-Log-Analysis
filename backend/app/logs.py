import sys
import os
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.agent import get_logs_filtered
from backend.app.db import db
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from collections import Counter
import re


class LogAnalyzer:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        self.error_keywords = [
            'error', 'failed', 'failure', 'exception', 'critical', 
            'fatal', 'crash', 'timeout', 'denied', 'unauthorized',
            'corrupted', 'invalid', 'missing', 'not found'
        ]
        self.warning_keywords = [
            'warning', 'caution', 'deprecated', 'slow', 'retry',
            'timeout', 'degraded', 'unavailable'
        ]
    
    def analyze_logs(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        
        if not logs:
            return {
                "warnings": [],
                "anomalies": [],
                "summary": {
                    "total": 0,
                    "errors": 0,
                    "warnings": 0,
                    "info": 0
                }
            }
        
        warnings = []
        anomalies = []
        
        
        level_counts = Counter(log.get("level", "Unknown") for log in logs)
        error_count = level_counts.get("Error", 0) + level_counts.get("Critical", 0)
        warning_count = level_counts.get("Warning", 0)
        info_count = level_counts.get("Information", 0)
        
        
        total = len(logs)
        error_rate = (error_count / total * 100) if total > 0 else 0
        
        if error_rate > 10:
            warnings.append({
                "type": "High Error Rate",
                "message": f"Error rate is {error_rate:.1f}% ({error_count} errors out of {total} logs)",
                "severity": "high"
            })
        
        
        error_logs = [log for log in logs if log.get("level") in ["Error", "Critical"]]
        error_messages = [log.get("message", "") for log in error_logs]
        
        
        error_patterns = self._find_error_patterns(error_messages)
        for pattern, count in error_patterns.items():
            if count > 5:
                warnings.append({
                    "type": "Repeated Error Pattern",
                    "message": f"Error pattern '{pattern}' occurred {count} times",
                    "severity": "medium"
                })
        
        
        security_logs = [log for log in logs if "Security" in log.get("log_name", "") or 
                        any(keyword in log.get("message", "").lower() for keyword in ["unauthorized", "denied", "failed login"])]
        if len(security_logs) > 10:
            warnings.append({
                "type": "Security Alert",
                "message": f"High number of security-related events: {len(security_logs)}",
                "severity": "high"
            })
        
        
        if len(logs) > 20:
            anomalies = self._detect_anomalies(logs)
        
        return {
            "warnings": warnings,
            "anomalies": anomalies[:5],  
            "summary": {
                "total": total,
                "errors": error_count,
                "warnings": warning_count,
                "info": info_count
            }
        }
    
    def _find_error_patterns(self, messages: List[str]) -> Dict[str, int]:
        
        patterns = Counter()
        
        for message in messages:
            
            
            service_match = re.search(r'([A-Z][a-z]+)\s+(?:service|process)', message, re.IGNORECASE)
            if service_match:
                patterns[f"Service Error: {service_match.group(1)}"] += 1
            
            
            code_match = re.search(r'error\s+code\s+(\d+)', message, re.IGNORECASE)
            if code_match:
                patterns[f"Error Code: {code_match.group(1)}"] += 1
        
        return patterns
    
    def _detect_anomalies(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        
        try:
            
            messages = [log.get("message", "")[:200] for log in logs]  
            
            if not messages or all(not msg for msg in messages):
                return []
            
            
            try:
                X = self.vectorizer.fit_transform(messages)
            except:
                return []
            
            
            clustering = DBSCAN(eps=0.5, min_samples=3)
            labels = clustering.fit_predict(X.toarray())
            
            
            anomalies = []
            for idx, label in enumerate(labels):
                if label == -1:  
                    log = logs[idx]
                    anomalies.append({
                        "timestamp": log.get("timestamp"),
                        "level": log.get("level"),
                        "message": log.get("message", "")[:100],  
                        "log_name": log.get("log_name"),
                        "reason": "Unusual log pattern detected"
                    })
            
            return anomalies[:10]  
            
        except Exception as e:
            print(f"Error in anomaly detection: {e}")
            return []



analyzer = LogAnalyzer()