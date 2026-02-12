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
                    # The scanner returns list of dicts: {"type": "SQLi", "line": line_idx, "content": ...}
                    vulns = self.vuln_scanner.scan_text(line) # scan_text scans a block, but works for line too
                    
                    if vulns:
                        for v in vulns:
                            events.append({
                                "filename": filename,
                                "timestamp": self.extract_timestamp(line),
                                "level": "VULNERABILITY",
                                "type": v['type'],
                                "message": line[:500], # Truncate long lines in DB
                                "line_number": line_idx
                            })
                        # If vulnerable, we might still want to check if it's an error, but usually vuln is specific enough.
                        # Let's continue to next line to avoid double counting if regex overlap (unlikely but safe)
                        continue

                    # 2. Check for Errors/Warnings
                    current_level = None
                    for level, pattern in self.LEVEL_PATTERNS.items():
                        if pattern.search(line):
                            current_level = level
                            break
                    
                    if current_level:
                        events.append({
                            "filename": filename,
                            "timestamp": self.extract_timestamp(line),
                            "level": current_level,
                            "type": "Log Event", # Generic type for grep matches
                            "message": line[:500],
                            "line_number": line_idx
                        })

        except Exception as e:
            logging.error(f"❌ Error parsing {filename}: {e}")
            
        return events
