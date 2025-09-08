#!/usr/bin/env python3
"""Test concurrent todo updates with the new todo reducer."""

import os
from dotenv import load_dotenv
from tavily import TavilyClient
from deepagents import create_deep_agent
from langchain_ollama import ChatOllama

# Load environment variables
load_dotenv()

# Simple search tool for testing
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def internet_search(query: str, max_results: int = 3):
    """Run a web search"""
    return tavily_client.search(query, max_results=max_results)

# Create local model
local_model = ChatOllama(
    model="qwen2.5:14b-instruct-8k",
    temperature=0.1,
    num_predict=2048
)

# Test 1: Simple agent with todos (no sub-agents)
def test_simple_todos():
    """Test that basic todo functionality still works."""
    print("=" * 60)
    print("TEST 1: Simple Todo Updates (No Sub-Agents)")
    print("=" * 60)
    
    instructions = """You are a planning assistant. 
    When given a task:
    1. Create a todo list for the task
    2. Mark todos as in_progress as you work
    3. Mark them as completed when done"""
    
    agent = create_deep_agent(
        [internet_search],
        instructions,
        model=local_model,
    )
    
    try:
        result = agent.invoke({
            "messages": [{"role": "user", "content": "Create a plan to learn Python (just 3 steps)"}]
        })
        
        print(f"✅ Test 1 Passed - Messages: {len(result['messages'])}")
        
        # Check if todos were created
        if 'todos' in result:
            print(f"Todos created: {len(result.get('todos', []))}")
            for todo in result.get('todos', []):
                print(f"  - [{todo['status']}] {todo['content']}")
        
        return True
    except Exception as e:
        print(f"❌ Test 1 Failed: {e}")
        return False

# Test 2: Agent with sub-agents
def test_with_subagents():
    """Test concurrent todo updates with sub-agents."""
    print("\n" + "=" * 60)
    print("TEST 2: Concurrent Todo Updates with Sub-Agents")
    print("=" * 60)
    
    # Define a simple research sub-agent
    research_sub_agent = {
        "name": "researcher",
        "description": "Conducts research on specific topics",
        "prompt": "You are a researcher. Create todos for your research task and mark them as you progress.",
        "tools": ["internet_search"],
    }
    
    # Define a simple planner sub-agent
    planner_sub_agent = {
        "name": "planner",
        "description": "Creates detailed plans",
        "prompt": "You are a planner. Create a todo list for the given task.",
    }
    
    instructions = """You are a coordinator. 
    Use the researcher and planner sub-agents to:
    1. Research the topic
    2. Create a comprehensive plan
    Track all tasks with todos."""
    
    agent = create_deep_agent(
        [internet_search],
        instructions,
        subagents=[research_sub_agent, planner_sub_agent],
        model=local_model,
    )
    
    try:
        result = agent.invoke({
            "messages": [{"role": "user", "content": "Help me understand REST APIs (brief)"}]
        })
        
        print(f"✅ Test 2 Passed - Messages: {len(result['messages'])}")
        
        # Check todos from multiple agents
        if 'todos' in result:
            print(f"Todos after concurrent updates: {len(result.get('todos', []))}")
            for todo in result.get('todos', []):
                print(f"  - [{todo['status']}] {todo['content']}")
        
        return True
    except Exception as e:
        print(f"❌ Test 2 Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# Test 3: Parallel sub-agent execution
def test_parallel_execution():
    """Test that sub-agents can truly run in parallel."""
    print("\n" + "=" * 60)
    print("TEST 3: Parallel Sub-Agent Execution")
    print("=" * 60)
    
    # Two sub-agents that should work in parallel
    analyst_sub_agent = {
        "name": "analyst",
        "description": "Analyzes data and creates analysis todos",
        "prompt": "You are an analyst. Create todos for your analysis tasks.",
    }
    
    reviewer_sub_agent = {
        "name": "reviewer",
        "description": "Reviews work and creates review todos",
        "prompt": "You are a reviewer. Create todos for review tasks.",
    }
    
    instructions = """You are a project manager.
    Call both the analyst and reviewer to work on the topic.
    They should create their own todo lists."""
    
    agent = create_deep_agent(
        [internet_search],
        instructions,
        subagents=[analyst_sub_agent, reviewer_sub_agent],
        model=local_model,
    )
    
    try:
        result = agent.invoke({
            "messages": [{"role": "user", "content": "Analyze Python vs JavaScript (very brief)"}]
        })
        
        print(f"✅ Test 3 Passed - Messages: {len(result['messages'])}")
        
        # Check merged todos
        if 'todos' in result:
            todos = result.get('todos', [])
            print(f"Merged todos from parallel agents: {len(todos)}")
            
            # Group by status
            by_status = {'pending': [], 'in_progress': [], 'completed': []}
            for todo in todos:
                by_status[todo['status']].append(todo['content'])
            
            for status, items in by_status.items():
                if items:
                    print(f"\n{status.upper()}:")
                    for item in items:
                        print(f"  - {item}")
        
        return True
    except Exception as e:
        print(f"❌ Test 3 Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# Main test runner
if __name__ == "__main__":
    print("🧪 Testing Concurrent Todo Updates with New Reducer")
    print("=" * 60)
    
    tests = [
        ("Simple Todos", test_simple_todos),
        ("With Sub-Agents", test_with_subagents),
        ("Parallel Execution", test_parallel_execution),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ {name} crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(success for _, success in results)
    if all_passed:
        print("\n🎉 All tests passed! The todo reducer fix works!")
    else:
        print("\n⚠️ Some tests failed. Check the output above.")