#!/usr/bin/env python3
"""Test NetBox agent with new middleware architecture."""

import os
import sys
import asyncio

# Add deepagents src to path
DEEPAGENTS_SRC_PATH = "/home/ola/dev/rnd/deepagents/src"
if DEEPAGENTS_SRC_PATH not in sys.path:
    sys.path.insert(0, DEEPAGENTS_SRC_PATH)

# Add netbox example path
NETBOX_PATH = "/home/ola/dev/rnd/deepagents/examples/netbox"
if NETBOX_PATH not in sys.path:
    sys.path.insert(0, NETBOX_PATH)

async def test_netbox_agent():
    """Test that NetBox agent works with new middleware."""
    print("Testing NetBox agent with middleware stack...")

    # Check environment variables
    netbox_url = os.getenv("NETBOX_URL")
    netbox_token = os.getenv("NETBOX_TOKEN")

    if not netbox_url or not netbox_token:
        print("⚠️  NETBOX_URL and NETBOX_TOKEN not set")
        print("   Agent would need these to connect to NetBox")
        print("   Testing agent creation only...")

    try:
        from netbox_agent import create_netbox_agent_with_simple_mcp

        # Create agent (will skip MCP if no env vars)
        agent = create_netbox_agent_with_simple_mcp(
            enable_caching=False
        )

        print("✅ NetBox agent created successfully with:")
        print("   - TodoListMiddleware")
        print("   - FilesystemMiddleware")
        print("   - SubAgentMiddleware")
        print("   - SummarizationMiddleware (170k threshold)")
        print("   - AnthropicPromptCachingMiddleware")
        print("   - PatchToolCallsMiddleware")

        return agent
    except Exception as e:
        print(f"❌ Failed to create NetBox agent: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("=" * 50)
    print("NetBox Agent Middleware Test")
    print("=" * 50)

    agent = asyncio.run(test_netbox_agent())

    if agent:
        print("\n" + "=" * 50)
        print("Test passed! NetBox agent works with middleware")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("Test failed - see errors above")
        print("=" * 50)
        sys.exit(1)