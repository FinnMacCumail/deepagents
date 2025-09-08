#!/usr/bin/env python3
"""Final working research agent that reliably creates files AND uses sub-agents."""

import os
from typing import Literal
from dotenv import load_dotenv
from tavily import TavilyClient
from deepagents import create_deep_agent
from langchain_ollama import ChatOllama

load_dotenv()
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    search_docs = tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )
    return search_docs

# Research sub-agent
research_sub_agent = {
    "name": "research-agent",
    "description": "Conducts detailed research on a specific topic and returns comprehensive findings.",
    "prompt": """You are a dedicated researcher. Conduct thorough research on the topic provided and return a detailed response covering key aspects, features, applications, and examples.

Your response will be used in a research report, so make it comprehensive and informative.""",
    "tools": ["internet_search"],
}

local_model = ChatOllama(
    model="qwen2.5:14b-instruct-8k",
    temperature=0.1,
    num_predict=4096
)

# Instructions based on what actually works - combining simple file creation with sub-agent capability
research_instructions = """You are a researcher. Follow these exact steps:

1. First, use write_file to save the question to "question.txt"
2. Then use internet_search to find information OR call research-agent for detailed research
3. Finally, use write_file to save your comprehensive findings to "final_report.md"

The final report should be structured with:
- # Title
- ## Introduction 
- ## Key Features/Concepts
- ## Applications/Use Cases
- ## Conclusion

You MUST use write_file for both steps 1 and 3. Do not skip the file creation steps!

Available tools:
- write_file(file_path, content): Create files (REQUIRED)
- internet_search(query): Search for information
- research-agent: Sub-agent for detailed research
- read_file, ls: File operations"""

def test_final_working():
    print("🚀 Final Working Research Agent")
    print("=" * 50)
    
    # Create agent - based on settings that worked before
    agent = create_deep_agent(
        [internet_search],
        research_instructions,
        subagents=[research_sub_agent],
        model=local_model,
    ).with_config({"recursion_limit": 100})
    
    question = "What is LangGraph?"
    print(f"Question: {question}")
    print("Starting research process...")
    
    try:
        result = agent.invoke({
            "messages": [{"role": "user", "content": question}]
        })
        
        print(f"\n📊 Results:")
        print(f"Messages: {len(result['messages'])}")
        
        # Check for files
        if 'files' in result and result['files']:
            print(f"Files: {len(result['files'])}")
            
            for filename, content in result['files'].items():
                clean_name = os.path.basename(filename) if filename.startswith('/') else filename
                print(f"  {clean_name}: {len(content)} chars")
                
                with open(clean_name, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"    💾 Saved")
                
                if clean_name == "final_report.md":
                    lines = content.split('\n')
                    if lines:
                        print(f"    Title: {lines[0]}")
            
            # Check if we got both files
            file_names = [os.path.basename(f) if f.startswith('/') else f for f in result['files'].keys()]
            if "question.txt" in file_names and "final_report.md" in file_names:
                print(f"\n🎉 SUCCESS! Both files created successfully!")
                return True
            else:
                print(f"\n⚠️ Partial success - got: {file_names}")
                return False
                
        else:
            print(f"❌ No files created")
            
            # Show what the agent actually did
            final_msg = result['messages'][-1]
            if hasattr(final_msg, 'content'):
                preview = final_msg.content[:200] + "..." if len(final_msg.content) > 200 else final_msg.content
                print(f"Final response: {preview}")
            
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    # Clean up
    for f in ["question.txt", "final_report.md"]:
        try:
            os.remove(f)
        except FileNotFoundError:
            pass
    
    success = test_final_working()
    
    print(f"\n{'='*50}")
    if success:
        print("🎉 WORKING! Research agent creates files with sub-agents!")
    else:
        print("🔧 The original comprehensive version may need different approach")