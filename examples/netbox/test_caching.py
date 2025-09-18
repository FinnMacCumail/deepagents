import asyncio
from netbox_agent import create_netbox_agent_with_all_tools, process_netbox_query, cache_monitor

# Global agent instance
netbox_agent = None

async def test_cache_performance():
    """Test cache performance with repeated queries"""

    # Test queries from netbox-queries file
    test_queries = [
        "Show me all sites in NetBox",
        "List all devices in site DM-Binghamton",
        "Get detailed information about device dmi01-akron-pdu01"
    ]

    print("🧪 Testing Cache Performance\n")

    # Run each query twice to test cache hits
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")

        # First run (cache write)
        print("\n📝 Run 1 (Cache Write):")
        await process_netbox_query(query)

        # Second run (cache read)
        print("\n📖 Run 2 (Cache Read):")
        await process_netbox_query(query)

    # Display final metrics
    print(f"\n{'='*60}")
    print("📊 Final Cache Metrics:")
    print(f"{'='*60}")
    metrics = cache_monitor.get_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    # Create agent with caching enabled
    netbox_agent = create_netbox_agent_with_all_tools(
        enable_caching=True,
        cache_ttl="1h"
    )

    # Make it available for process_netbox_query
    import netbox_agent as agent_module
    agent_module.netbox_agent = netbox_agent

    # Run tests
    asyncio.run(test_cache_performance())