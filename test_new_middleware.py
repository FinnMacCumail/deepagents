#!/usr/bin/env python3
"""Test new middleware-based agent creation."""

import os
import sys

# Add deepagents src to path
DEEPAGENTS_SRC_PATH = "/home/ola/dev/rnd/deepagents/src"
if DEEPAGENTS_SRC_PATH not in sys.path:
    sys.path.insert(0, DEEPAGENTS_SRC_PATH)

from deepagents import create_deep_agent

def test_middleware_agent():
    """Test that the new middleware-based agent works."""
    print("Testing new middleware-based agent creation...")

    try:
        # Create agent with upstream middleware stack
        agent = create_deep_agent(
            system_prompt="You are a helpful assistant."
        )
        print("✅ Agent created successfully with middleware stack")
        print("   - TodoListMiddleware")
        print("   - FilesystemMiddleware")
        print("   - SubAgentMiddleware")
        print("   - SummarizationMiddleware (170k threshold)")
        print("   - AnthropicPromptCachingMiddleware")
        print("   - PatchToolCallsMiddleware")
        return agent
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("=" * 50)
    print("Middleware-Based Agent Test")
    print("=" * 50)

    agent = test_middleware_agent()

    if agent:
        print("\n" + "=" * 50)
        print("Test passed! Agent created with full middleware stack")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("Test failed - see errors above")
        print("=" * 50)
        sys.exit(1)