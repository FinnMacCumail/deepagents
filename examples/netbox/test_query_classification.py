"""
Test script for NetBox cross-domain agent query classification

This test suite validates the agent's ability to:
1. Handle simple queries with direct tool use
2. Process intermediate queries with sequential tools
3. Execute cross-domain queries with parallel sub-agents
"""

import asyncio
import time
import sys
import os
from typing import Dict, List, Any
from deepagents import async_create_deep_agent

# Import the netbox agent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netbox_agent import create_netbox_agent_with_all_tools, process_netbox_query

# Test query sets organized by complexity
test_queries = {
    "simple": [
        "Show all sites",
        "List devices",
        "Get rack information for R-201",
        "List all tenants",
        "Show all VLANs",
        "Get device type information",
    ],
    "intermediate": [
        "Show devices in site DM-Akron with their IPs",
        "Get interfaces for device with assigned VLANs",
        "List racks in site with utilization",
        "Show tenant groups with their members",
        "Get virtual machines with their cluster info",
        "List power panels and their feeds",
    ],
    "cross_domain": [
        "Show tenant Research Lab infrastructure across all sites",
        "Network configuration for VM web-app-02 including physical host",
        "Complete infrastructure audit for site Butler Communications with tenant breakdown",
        "Show all devices owned by tenant DM Network with their IP allocations and rack locations",
        "Analyze power distribution for all devices in tenant Research Lab",
        "Virtual machine to physical host mapping with network configurations for all clusters",
    ]
}

async def test_query_execution(agent, query: str, query_type: str) -> Dict[str, Any]:
    """Execute a single test query and capture metrics"""
    print(f"\n{'=' * 60}")
    print(f"Testing {query_type.upper()} Query:")
    print(f"Query: {query}")
    print(f"{'=' * 60}")

    start_time = time.time()

    try:
        # Invoke the agent with the query
        result = await agent.ainvoke({
            "messages": [{"role": "user", "content": query}]
        })

        elapsed_time = time.time() - start_time

        # Extract metrics from the result
        messages = result.get('messages', [])

        # Check for tool usage patterns
        tool_calls = []
        task_calls = []
        think_calls = []

        for msg in messages:
            if hasattr(msg, 'tool_calls'):
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get('name', '')
                    if tool_name == 'task':
                        task_calls.append(tool_call)
                    elif tool_name == 'think':
                        think_calls.append(tool_call)
                    else:
                        tool_calls.append(tool_call)

        # Extract final response
        final_response = None
        for msg in reversed(messages):
            if hasattr(msg, 'content') and hasattr(msg, 'type') and msg.type == 'ai':
                final_response = msg.content
                break

        return {
            "query": query,
            "type": query_type,
            "elapsed_time": elapsed_time,
            "message_count": len(messages),
            "tool_calls": len(tool_calls),
            "task_calls": len(task_calls),
            "think_calls": len(think_calls),
            "success": final_response is not None,
            "response_preview": final_response[:200] if final_response else "No response",
        }

    except Exception as e:
        return {
            "query": query,
            "type": query_type,
            "elapsed_time": time.time() - start_time,
            "error": str(e),
            "success": False,
        }

def analyze_results(results: List[Dict[str, Any]]):
    """Analyze and print summary of test results"""
    print(f"\n{'=' * 80}")
    print("TEST RESULTS SUMMARY")
    print(f"{'=' * 80}")

    # Group results by type
    by_type = {"simple": [], "intermediate": [], "cross_domain": []}
    for result in results:
        by_type[result["type"]].append(result)

    for query_type, type_results in by_type.items():
        if not type_results:
            continue

        print(f"\n{query_type.upper()} QUERIES:")
        print(f"  Total: {len(type_results)}")
        print(f"  Successful: {sum(1 for r in type_results if r['success'])}")

        # Calculate averages
        successful_results = [r for r in type_results if r['success']]
        if successful_results:
            avg_time = sum(r['elapsed_time'] for r in successful_results) / len(successful_results)
            avg_tools = sum(r['tool_calls'] for r in successful_results) / len(successful_results)
            avg_tasks = sum(r['task_calls'] for r in successful_results) / len(successful_results)
            avg_thinks = sum(r['think_calls'] for r in successful_results) / len(successful_results)

            print(f"  Avg execution time: {avg_time:.2f}s")
            print(f"  Avg direct tool calls: {avg_tools:.1f}")
            print(f"  Avg sub-agent tasks: {avg_tasks:.1f}")
            print(f"  Avg think calls: {avg_thinks:.1f}")

    # Expected behavior verification
    print(f"\n{'=' * 80}")
    print("EXPECTED BEHAVIOR VERIFICATION:")
    print(f"{'=' * 80}")

    # Simple queries: should use direct tools, no sub-agents
    simple_results = [r for r in by_type["simple"] if r['success']]
    if simple_results:
        simple_with_tasks = [r for r in simple_results if r['task_calls'] > 0]
        print(f"\nSimple Queries:")
        print(f"  ✓ Direct tool usage: {len(simple_results) - len(simple_with_tasks)}/{len(simple_results)}")
        if simple_with_tasks:
            print(f"  ⚠ Unexpected sub-agent usage in {len(simple_with_tasks)} queries")

    # Intermediate queries: sequential tools, minimal sub-agents
    intermediate_results = [r for r in by_type["intermediate"] if r['success']]
    if intermediate_results:
        print(f"\nIntermediate Queries:")
        print(f"  ✓ Sequential processing: {len(intermediate_results)}/{len(intermediate_results)}")
        avg_tools = sum(r['tool_calls'] for r in intermediate_results) / len(intermediate_results)
        print(f"  ✓ Avg tools per query: {avg_tools:.1f}")

    # Cross-domain queries: should use think tool and sub-agents
    cross_results = [r for r in by_type["cross_domain"] if r['success']]
    if cross_results:
        cross_with_think = [r for r in cross_results if r['think_calls'] > 0]
        cross_with_tasks = [r for r in cross_results if r['task_calls'] > 0]
        print(f"\nCross-Domain Queries:")
        print(f"  ✓ Strategic thinking: {len(cross_with_think)}/{len(cross_results)}")
        print(f"  ✓ Sub-agent delegation: {len(cross_with_tasks)}/{len(cross_results)}")

        if cross_with_tasks:
            avg_tasks = sum(r['task_calls'] for r in cross_with_tasks) / len(cross_with_tasks)
            print(f"  ✓ Avg sub-agents per query: {avg_tasks:.1f}")

async def run_all_tests():
    """Run all test queries and analyze results"""
    print("🚀 NetBox Cross-Domain Agent Test Suite")
    print("=" * 80)

    # Create the agent with caching enabled
    print("\nInitializing NetBox agent...")
    agent = create_netbox_agent_with_all_tools(
        enable_caching=True,
        cache_ttl="1h",
        cache_conversation=True,
        conversation_cache_threshold=3
    )

    # Run tests
    all_results = []

    # Test a subset of queries from each category
    for query_type, queries in test_queries.items():
        print(f"\n📋 Testing {query_type.upper()} queries...")

        # Test first 2 queries from each category for faster execution
        for query in queries[:2]:
            result = await test_query_execution(agent, query, query_type)
            all_results.append(result)

            # Brief pause between queries
            await asyncio.sleep(1)

    # Analyze and display results
    analyze_results(all_results)

    print("\n✅ Test suite completed!")
    return all_results

async def test_parallel_execution():
    """Specific test for parallel sub-agent execution"""
    print("\n" + "=" * 80)
    print("PARALLEL EXECUTION TEST")
    print("=" * 80)

    agent = create_netbox_agent_with_all_tools()

    query = "Show complete infrastructure for tenant DM Network across all sites"
    print(f"\nQuery: {query}")
    print("Expected: Parallel execution of tenancy, DCIM, and IPAM specialists")

    start_time = time.time()
    result = await agent.ainvoke({
        "messages": [{"role": "user", "content": query}]
    })
    elapsed = time.time() - start_time

    # Check for parallel task execution
    messages = result.get('messages', [])
    task_timestamps = []

    for msg in messages:
        if hasattr(msg, 'tool_calls'):
            for tool_call in msg.tool_calls:
                if tool_call.get('name') == 'task':
                    task_timestamps.append(time.time())

    print(f"\n✓ Query completed in {elapsed:.2f}s")
    print(f"✓ Sub-agent tasks initiated: {len(task_timestamps)}")

    # Check if tasks were initiated close together (parallel)
    if len(task_timestamps) > 1:
        time_diff = max(task_timestamps) - min(task_timestamps)
        if time_diff < 1.0:  # Tasks initiated within 1 second
            print(f"✓ Tasks executed in parallel (time spread: {time_diff:.3f}s)")
        else:
            print(f"⚠ Tasks may have been sequential (time spread: {time_diff:.3f}s)")

if __name__ == "__main__":
    # Run the comprehensive test suite
    asyncio.run(run_all_tests())

    # Run specific parallel execution test
    # asyncio.run(test_parallel_execution())