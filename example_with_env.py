import os
from typing import Literal
from dotenv import load_dotenv

from tavily import TavilyClient
from deepagents import create_deep_agent

# Load environment variables from .env file
load_dotenv()

# Initialize Tavily client with API key from .env
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# Search tool to use to do research
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

# Prompt prefix to steer the agent to be an expert researcher
research_instructions = """You are an expert researcher. Your job is to conduct thorough research, and then write a polished report.

You have access to a few tools.

## `internet_search`

Use this to run an internet search for a given query. You can specify the number of results, the topic, and whether raw content should be included.
"""

# Create the agent
agent = create_deep_agent(
    [internet_search],
    research_instructions,
)

# Invoke the agent
if __name__ == "__main__":
    result = agent.invoke({"messages": [{"role": "user", "content": "what is langgraph?"}]})
    
    # Print just the final AI response
    final_message = result["messages"][-1]
    print("\n" + "="*50)
    print("FINAL RESPONSE:")
    print("="*50)
    print(final_message.content)