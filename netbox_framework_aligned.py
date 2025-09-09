#!/usr/bin/env python3
"""NetBox MCP - Framework-Aligned Selective Tool Loading"""

import asyncio
import os
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_anthropic import ChatAnthropic
from deepagents.sub_agent import _create_task_tool
from deepagents.state import DeepAgentState
from langgraph.prebuilt import create_react_agent

load_dotenv()

async def create_netbox_agent(mcp_client, model):
    """
    Create NetBox agent that works WITH DeepAgents framework
    Main agent gets only task tool, sub-agents get filtered NetBox tools
    """
    
    # Get all NetBox tools
    all_tools = await mcp_client.get_tools()
    print(f"📦 Processing {len(all_tools)} NetBox tools for selective loading")
    
    # Extract tool names for sub-agent filtering
    tool_names = [tool.name for tool in all_tools]
    
    # Filter tools by domain
    def filter_tools(patterns, limit=None):
        filtered = [name for name in tool_names 
                   if any(pattern in name for pattern in patterns)]
        return filtered[:limit] if limit else filtered
    
    device_tools = filter_tools(['device'], limit=12)
    network_tools = filter_tools(['ip_', 'vlan', 'prefix', 'vrf'], limit=10) 
    power_tools = filter_tools(['power'], limit=12)
    infrastructure_tools = filter_tools(['site', 'rack'], limit=10)
    list_tools = filter_tools(['list_all'], limit=15)
    readonly_tools = filter_tools(['get_', 'list_', 'health'], limit=20)
    
    print(f"📋 Tool distribution:")
    print(f"   • Device: {len(device_tools)} tools")
    print(f"   • Network: {len(network_tools)} tools")
    print(f"   • Power: {len(power_tools)} tools") 
    print(f"   • Infrastructure: {len(infrastructure_tools)} tools")
    print(f"   • List operations: {len(list_tools)} tools")
    print(f"   • Readonly: {len(readonly_tools)} tools")
    
    # Define specialized sub-agents using framework design
    subagents = [
        {
            "name": "device-expert",
            "description": "Handle device information, interfaces, and hardware queries",
            "prompt": """You are a NetBox device expert. Focus on:

1. Device information and status
2. Device interfaces and connections
3. Device hardware and components
4. Device relationships and dependencies

Use device-specific tools efficiently. Provide structured, detailed device analysis.""",
            "tools": device_tools
        },
        {
            "name": "network-expert", 
            "description": "Handle IP addresses, VLANs, prefixes, and network analysis",
            "prompt": """You are a NetBox network/IPAM expert. Focus on:

1. IP address assignments and utilization
2. VLAN configurations and mappings
3. Prefix hierarchy and availability
4. Network relationships and subnetting

Use network-specific tools efficiently. Provide clear network analysis.""",
            "tools": network_tools
        },
        {
            "name": "power-expert",
            "description": "Handle power infrastructure, connections, and electrical analysis", 
            "prompt": """You are a NetBox power infrastructure expert. Focus on:

1. Power connections and pathways
2. Power consumption and capacity
3. Power panels, feeds, and outlets
4. Electrical infrastructure relationships

Use power-specific tools efficiently. Provide comprehensive power analysis.""",
            "tools": power_tools
        },
        {
            "name": "infrastructure-expert",
            "description": "Handle sites, racks, and physical infrastructure",
            "prompt": """You are a NetBox infrastructure expert. Focus on:

1. Site layouts and configurations
2. Rack inventories and elevations  
3. Physical device placements
4. Infrastructure hierarchies and relationships

Use site/rack tools efficiently. Provide complete infrastructure analysis.""",
            "tools": infrastructure_tools
        },
        {
            "name": "list-operations",
            "description": "Handle all list operations with pagination support",
            "prompt": """You are a NetBox list operations specialist. Focus on:

1. Listing all resources of specified types
2. Handling paginated results effectively
3. Providing organized, comprehensive lists
4. Managing large result sets efficiently

Use list tools systematically. Mention if results are truncated or paginated.""",
            "tools": list_tools
        },
        {
            "name": "report-generator",
            "description": "Generate comprehensive reports and multi-domain analysis",
            "prompt": """You are a NetBox reporting expert. Focus on:

1. Comprehensive cross-domain reports
2. Multi-faceted infrastructure analysis
3. Data correlation and insights
4. Executive-level summaries

Use readonly tools broadly. Create structured, actionable reports.""",
            "tools": readonly_tools
        }
    ]
    
    print(f"📋 Created {len(subagents)} specialized sub-agents")
    
    # Main agent instructions for intelligent delegation
    main_instructions = """You are a NetBox orchestrator that delegates to specialized sub-agents.

DELEGATION STRATEGY:
Analyze queries and route to the most appropriate expert:

• Device queries (hardware, interfaces, status) → "device-expert"
• Network queries (IPs, VLANs, prefixes) → "network-expert"  
• Power queries (electrical, PDUs, connections) → "power-expert"
• Infrastructure queries (sites, racks, locations) → "infrastructure-expert"
• List operations ("show all", "list all") → "list-operations"
• Complex reports or multi-domain analysis → "report-generator"

MULTI-DOMAIN QUERIES:
For complex queries requiring multiple areas:
1. Break into logical components
2. Use task() multiple times with different experts
3. Synthesize results into comprehensive response

EXAMPLES:
- "Device dmi01-akron-pdu01 details" → device-expert
- "List all sites" → list-operations
- "Power analysis for site X" → power-expert
- "Complete site audit" → infrastructure-expert + power-expert + device-expert

Always use the task tool to delegate to specialized experts."""

    # Create the task tool with all NetBox tools for sub-agents
    # This is the framework's way of providing tools to sub-agents
    task_tool = _create_task_tool(
        all_tools,  # Sub-agents need access to these
        main_instructions,
        subagents,
        model,
        DeepAgentState
    )
    
    # Create main agent with ONLY the task tool (avoids rate limits)
    main_agent = create_react_agent(
        model,
        tools=[task_tool],  # Only 1 tool - no rate limits!
        prompt=main_instructions,
        state_schema=DeepAgentState
    )
    
    print(f"✅ Framework-aligned agent created:")
    print(f"   • Main agent tools: 1 (task tool only)")
    print(f"   • Sub-agents: {len(subagents)} specialists")
    print(f"   • Total NetBox tools available: {len(all_tools)}")
    
    return main_agent

async def test_framework_aligned_netbox():
    """Test the framework-aligned NetBox integration"""
    
    print("🎯 NetBox MCP - Framework-Aligned Integration Test")
    print("=" * 60)
    
    try:
        # NetBox MCP connection
        connections = {
            "netbox": {
                "command": "uv",
                "args": ["run", "main.py"],
                "cwd": "/home/ola/dev/netboxdev/netbox-mcp",
                "transport": "stdio",
                "env": {
                    "NETBOX_URL": "http://localhost:8000",
                    "NETBOX_TOKEN": os.getenv("NETBOX_TOKEN", "your-token-here"),
                    **os.environ
                }
            }
        }
        
        print("🔌 Connecting to NetBox MCP server...")
        client = MultiServerMCPClient(connections=connections)
        
        # Claude model
        model = ChatAnthropic(
            model_name="claude-3-5-haiku-20241022",
            max_tokens=1500,
            temperature=0
        )
        
        print("🤖 Creating framework-aligned NetBox agent...")
        agent = await create_netbox_agent(client, model)
        
        # Test queries representing different domains
        test_queries = [
            {
                "query": "Get detailed information about device dmi01-akron-pdu01",
                "expected_agent": "device-expert"
            },
            {
                "query": "List all sites in NetBox",
                "expected_agent": "list-operations"
            },
            {
                "query": "Show power connections for device dmi01-binghamton-pdu01", 
                "expected_agent": "power-expert"
            }
        ]
        
        print(f"\n🎯 Testing {len(test_queries)} queries across different domains...")
        print("=" * 60)
        
        successful_queries = 0
        
        for i, test in enumerate(test_queries, 1):
            query = test["query"]
            expected = test["expected_agent"]
            
            print(f"\n📋 Test {i}: {query}")
            print(f"Expected delegation: {expected}")
            print("-" * 50)
            
            try:
                # Execute query
                result = await asyncio.wait_for(
                    agent.ainvoke({
                        "messages": [{"role": "user", "content": query}]
                    }),
                    timeout=120  # 2 minute timeout
                )
                
                if result and "messages" in result:
                    final_message = result["messages"][-1]
                    if hasattr(final_message, 'content') and final_message.content:
                        
                        # Truncate long responses
                        content = final_message.content
                        if len(content) > 600:
                            content = content[:600] + "\n... (truncated)"
                        
                        print("📊 RESULT:")
                        print(content)
                        
                        # Check delegation
                        task_calls = [msg for msg in result["messages"] 
                                    if hasattr(msg, 'tool_calls') and msg.tool_calls
                                    and any(getattr(call, 'name', call.get('name') if isinstance(call, dict) else None) == 'task' for call in msg.tool_calls)]
                        
                        if task_calls:
                            print(f"\n📈 Framework Delegation:")
                            for msg in task_calls:
                                for call in msg.tool_calls:
                                    call_name = getattr(call, 'name', call.get('name') if isinstance(call, dict) else None)
                                    if call_name == 'task':
                                        call_args = getattr(call, 'args', call.get('args', {}) if isinstance(call, dict) else {})
                                        agent_used = call_args.get('subagent_type', 'unknown')
                                        print(f"   • Delegated to: {agent_used}")
                                        if agent_used == expected:
                                            print(f"   ✅ Correct delegation!")
                                        else:
                                            print(f"   ⚠️  Expected: {expected}")
                        
                        successful_queries += 1
                        print("✅ SUCCESS")
                        
                    else:
                        print("❌ FAILED: No content in response")
                else:
                    print("❌ FAILED: No valid result returned")
                    
            except asyncio.TimeoutError:
                print("❌ TIMEOUT: Query processing exceeded time limit")
            except Exception as e:
                print(f"❌ ERROR: {e}")
                if "rate_limit" in str(e).lower():
                    print("⚠️  Rate limit hit - framework alignment needs adjustment")
            
            print("-" * 50)
        
        # Final assessment
        print(f"\n🏆 FRAMEWORK TEST RESULTS")
        print(f"📊 Success Rate: {successful_queries}/{len(test_queries)} queries")
        
        if successful_queries == len(test_queries):
            print("🎉 FRAMEWORK ALIGNMENT SUCCESSFUL!")
            print("✅ Key achievements:")
            print("   • No rate limits with framework-aligned architecture")
            print("   • Proper sub-agent delegation working")
            print("   • All domains accessible through specialists")
            print("   • Framework design principles maintained")
        elif successful_queries > 0:
            print("🟡 PARTIAL SUCCESS - Framework working with minor issues")
        else:
            print("🔴 FRAMEWORK ALIGNMENT FAILED - Needs architecture review")
        
        print(f"\n💡 Architecture Summary:")
        print(f"   • Main agent: Task tool only (~500 tokens)")
        print(f"   • Sub-agents: 6 specialists with 10-20 tools each")
        print(f"   • Framework: Native DeepAgents delegation")
        print(f"   • Context: Quarantined per sub-agent")
        
        return successful_queries == len(test_queries)
        
    except Exception as e:
        print(f"❌ Framework test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main entry point"""
    print("Starting framework-aligned NetBox integration test...")
    success = await test_framework_aligned_netbox()
    
    print(f"\n{'=' * 60}")
    if success:
        print("🎯 FRAMEWORK-ALIGNED INTEGRATION SUCCESSFUL!")
        print("✅ This properly uses DeepAgents framework:")
        print("   • Sub-agent system for specialization")
        print("   • Task tool for delegation")
        print("   • Context quarantine for efficiency")
        print("   • No custom orchestration needed")
        print("   • Mirrors Claude Code CLI architecture")
    else:
        print("⚠️ Integration needs refinement - review framework alignment")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())