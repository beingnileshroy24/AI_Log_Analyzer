from langchain_core.tools import Tool
from .stats_tool import LogStatisticsTool
from .time_tool import TimeAnalysisTool
from .pattern_tool import PatternMatchingTool

def get_agent_tools():
    """
    Returns a list of LangChain Tool objects for the agent.
    """
    # Initialize Engines
    stats_engine = LogStatisticsTool()
    time_engine = TimeAnalysisTool()
    pattern_engine = PatternMatchingTool()

    tools = [
        Tool(
            name="GetLogDuplicateCount",
            func=stats_engine.get_stats,
            description="Useful for finding how many duplicate entries constitute a file. Input: filename."
        ),
        Tool(
            name="GetLogTimeDistribution",
            func=time_engine.analyze_timeline,
            description="Useful for understanding when events happened, the duration of logs, or peak activity times. Input: filename."
        ),
        Tool(
            name="ExtractLogPatterns",
            func=pattern_engine.extract_patterns,
            description="Useful for extracting IP addresses, emails, URLs, or error codes from log files. Input: 'find [pattern] in [filename]'."
        )
    ]
    
    return tools
