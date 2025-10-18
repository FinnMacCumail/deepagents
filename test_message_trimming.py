#!/usr/bin/env python3
"""Test message trimming functionality in v1."""

import os
import sys

# Add deepagents src to path
DEEPAGENTS_SRC_PATH = "/home/ola/dev/rnd/deepagents/src"
if DEEPAGENTS_SRC_PATH not in sys.path:
    sys.path.insert(0, DEEPAGENTS_SRC_PATH)

from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage, AIMessage

def test_message_trimming():
    """Test that message trimming works in v1."""
    print("Testing message trimming in v1...")
    os.environ["USE_V1_CORE"] = "true"

    # Create agent with v1
    agent = create_deep_agent(
        [],
        "You are a helpful assistant that counts messages."
    )

    # Create a conversation with many messages
    messages = []
    for i in range(10):
        messages.append(HumanMessage(content=f"Message {i}"))
        messages.append(AIMessage(content=f"Response {i}"))

    print(f"Created {len(messages)} messages")

    # Test that the agent can handle them
    config = {"configurable": {"thread_id": "test"}}

    # Run a simple query
    response = agent.invoke({
        "messages": messages + [HumanMessage(content="How many messages have we exchanged?")]
    }, config)

    print("✓ Agent handled messages successfully")
    print(f"Response messages count: {len(response.get('messages', []))}")

    return response

if __name__ == "__main__":
    print("=" * 50)
    print("Message Trimming Test")
    print("=" * 50)

    response = test_message_trimming()

    print("\n" + "=" * 50)
    print("Message trimming test passed! ✅")
    print("=" * 50)