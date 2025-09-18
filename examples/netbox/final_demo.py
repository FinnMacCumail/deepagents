#!/usr/bin/env python3
"""
Final demonstration of Claude API Prompt Caching implementation.
This script tests the complete caching workflow and shows expected performance improvements.
"""

import asyncio
import os
import sys
import time
from typing import Dict, Any

# Add src to path for development
sys.path.insert(0, '/home/ola/dev/rnd/deepagents/src')

# Import after path modification
from netbox_agent import create_netbox_agent_with_all_tools, cache_monitor

async def run_caching_demo():
    """Demonstrate the caching implementation with real queries"""

    print("=" * 70)
    print("🚀 Claude API Prompt Caching Demo - NetBox Agent")
    print("=" * 70)

    # Check if we have the required API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not found in environment")
        print("   Set your API key to test actual caching behavior")
        return

    print("✅ API key found - ready to test real caching")

    # Create agent with caching enabled
    print("\n📦 Creating NetBox agent with caching enabled...")
    start_time = time.time()

    agent = create_netbox_agent_with_all_tools(
        enable_caching=True,
        cache_ttl="1h",
        cache_conversation=True,
        conversation_cache_threshold=2
    )

    creation_time = time.time() - start_time
    print(f"⏱️  Agent creation time: {creation_time:.2f}s")

    # Test queries that should demonstrate caching
    test_queries = [
        "Check NetBox server health",  # Simple query
        "Check NetBox server health",  # Repeat to test cache hit
        "Show me all sites in NetBox", # Different query to test cache effectiveness
    ]

    print(f"\n🧪 Running {len(test_queries)} test queries...")
    print("=" * 50)

    results = []
    for i, query in enumerate(test_queries, 1):
        print(f"\n📋 Query {i}/3: {query}")
        print("-" * 40)

        start_time = time.time()
        try:
            # Make the agent call
            result = await agent.ainvoke({
                "messages": [{"role": "user", "content": query}]
            })

            elapsed = time.time() - start_time

            # Extract basic response info
            response_length = 0
            if result and 'messages' in result:
                for msg in result['messages']:
                    if hasattr(msg, 'content') and msg.content:
                        response_length += len(str(msg.content))

            query_result = {
                "query": query,
                "duration": elapsed,
                "response_length": response_length,
                "success": True
            }

            print(f"✅ Query completed in {elapsed:.2f}s")
            print(f"📝 Response length: {response_length} chars")

        except Exception as e:
            print(f"❌ Query failed: {str(e)}")
            query_result = {
                "query": query,
                "duration": time.time() - start_time,
                "error": str(e),
                "success": False
            }

        results.append(query_result)

        # Show cache metrics after each query
        if cache_monitor.requests:
            latest = cache_monitor.requests[-1]
            cache_activity = latest['cache_read'] > 0 or latest['cache_write'] > 0
            if cache_activity:
                print(f"💾 Cache: Read={latest['cache_read']}, Write={latest['cache_write']}")
            else:
                print("💾 No cache activity detected")

    # Final summary
    print(f"\n{'=' * 70}")
    print("📊 CACHING PERFORMANCE SUMMARY")
    print("=" * 70)

    # Calculate performance metrics
    successful_queries = [r for r in results if r['success']]
    if len(successful_queries) >= 2:
        first_query_time = successful_queries[0]['duration']
        repeat_query_time = next((r['duration'] for r in successful_queries[1:]
                                 if r['query'] == successful_queries[0]['query']), None)

        if repeat_query_time:
            speed_improvement = ((first_query_time - repeat_query_time) / first_query_time) * 100
            print(f"⚡ Speed improvement on repeat query: {speed_improvement:.1f}%")
            print(f"   - First query:  {first_query_time:.2f}s")
            print(f"   - Repeat query: {repeat_query_time:.2f}s")

    # Cache monitor summary
    if cache_monitor.requests:
        metrics = cache_monitor.get_metrics()
        print(f"\n💰 Cache Performance Metrics:")
        print(f"   - Total requests: {metrics['total_requests']}")
        print(f"   - Cache hits: {metrics['cache_hits']}")
        print(f"   - Cache misses: {metrics['cache_misses']}")
        print(f"   - Hit rate: {metrics['cache_hit_rate']}")
        print(f"   - Estimated cost savings: {metrics['estimated_cost_savings']}")
        print(f"   - Cached tokens read: {metrics['cached_tokens_read']}")
        print(f"   - Cached tokens written: {metrics['cached_tokens_written']}")

        # Detailed request analysis
        print(f"\n🔍 Request Details:")
        for i, req in enumerate(cache_monitor.requests, 1):
            cache_desc = "MISS"
            if req['cache_read'] > 0:
                cache_desc = f"HIT (read {req['cache_read']} tokens)"
            elif req['cache_write'] > 0:
                cache_desc = f"WRITE ({req['cache_write']} tokens)"

            print(f"   {i}. {cache_desc} - Input: {req['input_tokens']} tokens")

    else:
        print("⚠️ No cache metrics recorded")

    # Expected vs actual analysis
    print(f"\n🎯 Expected vs Actual Results:")
    print("   Expected behavior with caching:")
    print("   - First query: Should write ~14,000 tokens to cache")
    print("   - Repeat queries: Should read ~14,000 tokens from cache")
    print("   - Cost reduction: 77-90% after cache warm-up")
    print("   - Latency reduction: 50-85% for cached content")

    if cache_monitor.cached_tokens_written > 0:
        print(f"   ✅ Cache writes detected: {cache_monitor.cached_tokens_written} tokens")
    else:
        print("   ⚠️ No cache writes detected - check implementation")

    if cache_monitor.cached_tokens_read > 0:
        print(f"   ✅ Cache reads detected: {cache_monitor.cached_tokens_read} tokens")
    else:
        print("   ⚠️ No cache reads detected - may need repeat queries")

    print(f"\n{'=' * 70}")
    print("✅ Demo completed! Check your Claude API logs to verify caching behavior.")
    print("Look for 'Cache Read' and 'Cache Write' tokens in the usage data.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_caching_demo())