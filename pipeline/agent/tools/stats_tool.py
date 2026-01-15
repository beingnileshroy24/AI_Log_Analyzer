import pandas as pd
from collections import Counter
from .base_tool import BaseLogTool

class LogStatisticsTool(BaseLogTool):
    def get_stats(self, query):
        """
        Analyzes the file for duplicate entries.
        query: Filename or sentence containing filename.
        """
        # Extract filename
        query = query.strip()
        for phrase in ["in file ", "in ", "check ", "analyze ", "stats for "]:
            if query.lower().startswith(phrase):
                query = query[len(phrase):]
        filename = query.strip()
        
        content, error = self._get_content(filename)
        if error:
            return f"❌ {error}"
            
        try:
            stats = ""
            
            if isinstance(content, pd.DataFrame):
                # Structured Data
                total_rows = len(content)
                duplicates = content[content.duplicated()]
                num_duplicates = len(duplicates)
                unique_entries = total_rows - num_duplicates
                
                stats = f"**📊 Analysis for: {filename}**\n"
                stats += f"- **Total Rows:** {total_rows}\n"
                stats += f"- **Unique Rows:** {unique_entries}\n"
                stats += f"- **Duplicate Rows:** {num_duplicates}\n"
                
                if num_duplicates > 0:
                    dup_counts = content.value_counts().head(5)
                    stats += "\n**Top Duplicates:**\n"
                    stats += dup_counts.to_string()
                    
            elif isinstance(content, str):
                # Unstructured Data
                lines = content.splitlines()
                lines = [line for line in lines if line.strip()]
                
                total_lines = len(lines)
                counts = Counter(lines)
                num_duplicates = sum(count - 1 for count in counts.values() if count > 1)
                unique_lines = len(counts)
                
                stats = f"**📊 Analysis for: {filename}**\n"
                stats += f"- **Total Lines:** {total_lines}\n"
                stats += f"- **Unique Lines:** {unique_lines}\n"
                stats += f"- **Redundant (Duplicate) Lines:** {num_duplicates}\n"
                
                if num_duplicates > 0:
                    stats += "\n**Top Recurring Entries:**\n"
                    top_dups = [item for item in counts.most_common(5) if item[1] > 1]
                    for line, count in top_dups:
                        display_line = (line[:75] + '...') if len(line) > 75 else line
                        stats += f"- `{display_line}` ({count}x)\n"
            
            return stats

        except Exception as e:
            return f"❌ Error analyzing file: {e}"
