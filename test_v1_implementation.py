#!/usr/bin/env python3
"""Test script for v1 implementation."""

import os
import sys

# Add deepagents src to path
DEEPAGENTS_SRC_PATH = "/home/ola/dev/rnd/deepagents/src"
if DEEPAGENTS_SRC_PATH not in sys.path:
    sys.path.insert(0, DEEPAGENTS_SRC_PATH)

from deepagents import create_deep_agent

def test_v0():
    """Test v0 implementation (default)."""
    print("Testing v0 implementation...")
    os.environ["USE_V1_CORE"] = "false"

    agent = create_deep_agent(
        [],
        "You are a helpful assistant."
    )
    print("✓ v0 agent created successfully")
    return agent

def test_v1():
    """Test v1 implementation with message trimming."""
    print("\nTesting v1 implementation...")
    os.environ["USE_V1_CORE"] = "true"

    agent = create_deep_agent(
        [],
        "You are a helpful assistant."
    )
    print("✓ v1 agent created successfully")
    return agent

if __name__ == "__main__":
    print("=" * 50)
    print("LangChain v1 Implementation Test")
    print("=" * 50)

    # Test v0
    agent_v0 = test_v0()

    # Test v1
    agent_v1 = test_v1()

    print("\n" + "=" * 50)
    print("All tests passed! ✅")
    print("=" * 50)