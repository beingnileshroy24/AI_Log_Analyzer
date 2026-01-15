import re
import pandas as pd
from .base_tool import BaseLogTool
from dateutil import parser
from datetime import datetime

class TimeAnalysisTool(BaseLogTool):
    def analyze_timeline(self, query):
        """
        Extracts timestamps and provides a distribution analysis.
        """
        # Extract filename (simple heuristic)
        query = query.strip()
        for phrase in ["time distribution of ", "timeline of ", "when did ", "timestamps in "]:
            if query.lower().startswith(phrase):
                query = query[len(phrase):]
        filename = query.strip()

        content, error = self._get_content(filename)
        if error:
            return f"❌ {error}"

        if not isinstance(content, str):
            # If DataFrame, try to find a date column
            if isinstance(content, pd.DataFrame):
                # Simple check for date/time columns
                date_cols = [c for c in content.columns if 'date' in c.lower() or 'time' in c.lower()]
                if not date_cols:
                    return "This appears to be a structured file but no obvious Date/Time columns were found."
                
                # Analyze first found date col
                col = date_cols[0]
                try:
                    content[col] = pd.to_datetime(content[col])
                    min_date = content[col].min()
                    max_date = content[col].max()
                    return f"**📅 Timeline Analysis for {filename} (Column: {col})**\n- **Start:** {min_date}\n- **End:** {max_date}\n- **Total Entries:** {len(content)}"
                except:
                    return f"Found column '{col}' but failed to parse dates."

            return "Time analysis is currently optimized for unstructured text logs."

        # Text Log Analysis
        lines = content.splitlines()
        timestamps = []
        
        # Common Log Date Formats
        # 1. ISO8601: 2024-01-15 14:32:49
        # 2. Syslog: Jan 15 14:32:49
        # 3. Common: 15/Jan/2024:14:32:49
        
        # Regex for generic date capturing (YYYY-MM-DD or MMM DD)
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})', # 2024-01-01 10:00:00
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', # ISO T
            r'([A-Z][a-z]{2}\s+\d{1,2}\s\d{2}:\d{2}:\d{2})', # Jan 01 10:00:00
            r'(\d{2}/[A-Z][a-z]{2}/\d{4}:\d{2}:\d{2}:\d{2})' # 01/Jan/2024:10:00:00
        ]
        
        combined_regex = "|".join(date_patterns)
        
        for line in lines:
            match = re.search(combined_regex, line)
            if match:
                # Find which group matched
                ts_str = next(g for g in match.groups() if g is not None)
                try:
                    # Fuzzy parse
                    dt = parser.parse(ts_str.replace(":", " ", 1) if "Jan" in ts_str else ts_str, fuzzy=True)
                    timestamps.append(dt)
                except:
                    pass
        
        if not timestamps:
            return "❌ No recognizable timestamps found in the log file."

        timestamps.sort()
        start = timestamps[0]
        end = timestamps[-1]
        duration = end - start
        
        # Hourly Distribution
        hours = [t.hour for t in timestamps]
        peak_hour = max(set(hours), key=hours.count)
        
        stats = f"**📅 Timeline Analysis for: {filename}**\n"
        stats += f"- **Range:** {start} to {end}\n"
        stats += f"- **Duration:** {duration}\n"
        stats += f"- **Total Events:** {len(timestamps)}\n"
        stats += f"- **Peak Activity Hour:** {peak_hour}:00 - {peak_hour+1}:00\n"
        
        return stats
