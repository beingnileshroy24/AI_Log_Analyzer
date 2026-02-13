import re
import logging
import os
from typing import List, Dict, Any
from .vulnerability_scanner import VulnerabilityScanner

class LogParser:
    """
    Parses log files to extract distinct events (Errors, Warnings, Vulnerabilities).
    """
    
    # Common patterns for log levels
    LEVEL_PATTERNS = {
        "ERROR": re.compile(r'\b(ERROR|CRITICAL|FATAL|FAIL|FAILED|EXCEPTION)\b', re.IGNORECASE),
        "WARN": re.compile(r'\b(WARN|WARNING)\b', re.IGNORECASE)
    }
    
    # Simple timestamp extractor (YYYY-MM-DD HH:MM:SS)
    TIMESTAMP_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}')

    def __init__(self):
        self.vuln_scanner = VulnerabilityScanner()

    def extract_timestamp(self, line: str) -> str:
        """Extracts the first timestamp found in the line."""
        match = self.TIMESTAMP_PATTERN.search(line)
        return match.group(0) if match else None

    def parse_file(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Reads a file line-by-line and extracts interesting events.
        """
        events = []
        filename = os.path.basename(filepath)
        
        if not os.path.exists(filepath):
            logging.error(f"❌ File not found: {filepath}")
            return []

        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                for i, line in enumerate(f):
                    line_idx = i + 1
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 1. Check for Vulnerabilities (Security)
                    vulns = self.vuln_scanner.scan_text(line) 
                    
                    if vulns:
                        for v in vulns:
                            events.append({
                                "FileID": filename,
                                "LogEntryType": "Vulnerability",
                                "LogMessage": f"[{v['type']}] {line[:1000]}",
                                "Resolution": "",
                                "ReferenceURL": "",
                                "LoggedOn": self.extract_timestamp(line),
                            })
                        continue

                    # 2. Check for Errors/Warnings
                    current_level = None
                    for level, pattern in self.LEVEL_PATTERNS.items():
                        if pattern.search(line):
                            current_level = level
                            break
                    
                    if current_level:
                        events.append({
                            "FileID": filename,
                            "LogEntryType": current_level, # ERROR or WARN
                            "LogMessage": line[:1000],
                            "Resolution": "",
                            "ReferenceURL": "",
                            "LoggedOn": self.extract_timestamp(line),
                        })

        except Exception as e:
            logging.error(f"❌ Error parsing {filename}: {e}")
            
        return events
    
    def parse_file_with_vulns(self, filepath: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse file and return vulnerabilities and regular events separately.
        
        Returns:
            {
                "vulnerabilities": [...],  # For Vulnerability_Analysis table
                "events": [...]            # For Log_extraction table
            }
        """
        all_events = self.parse_file(filepath)
        
        vulnerabilities = []
        regular_events = []
        
        for event in all_events:
            if event.get("LogEntryType") == "Vulnerability":
                # Extract vulnerability type from LogMessage
                vuln_type = event["LogMessage"].split("]")[0].replace("[", "").strip()
                
                vulnerabilities.append({
                    "FileID": event["FileID"],
                    "VulnerabilityType": vuln_type,
                    "LogMessage": event["LogMessage"],
                    "LoggedOn": event["LoggedOn"],
                    # These will be filled by VulnerabilityAnalyzer
                    "Severity": None,
                    "Solution": None,
                    "ReferenceURL": None
                })
            else:
                regular_events.append(event)
        
        return {
            "vulnerabilities": vulnerabilities,
            "events": regular_events
        }

