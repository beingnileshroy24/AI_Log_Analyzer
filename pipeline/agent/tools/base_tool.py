import os
import pandas as pd
from ...core.metadata import REPORT_PATH
from ...core.ingestor import UniversalIngestor

class BaseLogTool:
    def __init__(self):
        self.report_path = REPORT_PATH
        self.ingestor = UniversalIngestor(incoming_path="") 

    def _resolve_path(self, filename):
        """
        Finds the actual file path using the master report, following rename chains if necessary.
        """
        if not os.path.exists(self.report_path):
            return None, "Metadata report not found. Has the pipeline run?"

        try:
            df = pd.read_csv(self.report_path)
            if df.empty:
                return None, "Metadata report is empty."

            current_target = filename
            final_row = None
            visited = set()

            while True:
                if current_target in visited:
                    break # Avoid infinite loops
                visited.add(current_target)

                # Try exact match on Original_Filename
                match = df[df['Original_Filename'] == current_target]
                
                # If no exact match, try fuzzy/contains
                if match.empty:
                    match = df[df['Original_Filename'].str.contains(current_target, case=False, na=False)]
                
                if match.empty:
                    # If this was the first iteration, we failed to find anything
                    if len(visited) == 1:
                        return None, f"File '{filename}' not found in metadata records."
                    # Otherwise, the last successful match is our target
                    break
                
                # Get the most recent entry
                row = match.iloc[-1]
                final_row = row
                
                # If this file was re-ingested, its Stored_Filename will appear as Original_Filename in a later record
                next_target = str(row['Stored_Filename'])
                if next_target == "N/A" or next_target == current_target:
                    break
                
                # Check if this stored filename appears as an original filename in any LATER row
                # (Later rows have higher index in our DF usually)
                remaining_df = df.iloc[row.name + 1:] if hasattr(row, 'name') else df
                if next_target in remaining_df['Original_Filename'].values:
                    current_target = next_target
                else:
                    break

            if final_row is None:
                return None, f"File '{filename}' not found in metadata records."

            final_path = final_row['Final_Path']
            raw_path = final_row['Raw_Storage_Path']
            
            # Prefer Final_Path (processed), then Raw_Storage_Path (staging)
            if pd.notna(final_path) and final_path != "Pending" and os.path.exists(final_path):
                return final_path, None
            elif pd.notna(raw_path) and raw_path != "N/A" and os.path.exists(raw_path):
                return raw_path, None
            else:
                return None, f"File record found for '{filename}', but the file object is missing from disk."
                
        except Exception as e:
            return None, f"Error reading metadata: {e}"

    def _get_content(self, filename):
        """
        Helper to resolve path and get content in one step.
        """
        filepath, error = self._resolve_path(filename)
        if error:
            return None, error
        
        try:
            # ingestor.process_file returns (content, file_type)
            result = self.ingestor.process_file(filepath)
            if result is None:
                return None, "System error: Ingestor returned None."
                
            content, _ = result
            
            if content is None:
                return None, "Could not read file content."
            return content, None
        except Exception as e:
            return None, f"Error reading file: {e}"
