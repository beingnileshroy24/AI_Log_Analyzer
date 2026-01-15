import re
from collections import Counter
from .base_tool import BaseLogTool

class PatternMatchingTool(BaseLogTool):
    def extract_patterns(self, query):
        """
        Extracts specific patterns like IPs, Emails, and URLs.
        """
        # Determine strictness/target from query if possible, else do all
        query = query.lower()
        target = "all"
        filename = query
        
        if "ip" in query: target = "ip"
        if "email" in query: target = "email"
        if "url" in query or "link" in query: target = "url"
        if "error" in query: target = "error"

        # Cleanup filename from query
        remove_words = ["extract ", "find ", "get ", "ips ", "emails ", "urls ", "patterns ", "from ", "in "]
        for word in remove_words:
            filename = filename.replace(word, "")
        filename = filename.strip()

        content, error = self._get_content(filename)
        if error:
            return f"❌ {error}"
            
        text_content = str(content)
        
        patterns = {
            "ip": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "url": r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*',
            "error_code": r'\b[45]\d{2}\b' # HTTP 4xx 5xx
        }
        
        results = ""
        
        def scan_pattern(name, regex):
            matches = re.findall(regex, text_content)
            if not matches:
                return f"- No {name}s found.\n"
            
            count = len(matches)
            unique = set(matches)
            top = Counter(matches).most_common(5)
            
            out = f"- **Found {count} {name}s** ({len(unique)} unique)\n"
            out += "  Top: " + ", ".join([f"{k} ({v})" for k,v in top]) + "\n"
            return out

        results += f"**🔍 Pattern Matching Report for: {filename}**\n"
        
        if target == "all" or target == "ip":
            results += scan_pattern("IP Address", patterns["ip"])
        if target == "all" or target == "email":
            results += scan_pattern("Email", patterns["email"])
        if target == "all" or target == "url":
            results += scan_pattern("URL", patterns["url"])
            
        return results
