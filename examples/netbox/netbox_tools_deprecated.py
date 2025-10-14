"""
DEPRECATED: Unused NetBox Agent Tools

This file preserves tools that were removed from netbox_agent.py due to zero usage
across validation testing. All 4 tools showed 0 calls across 6 diverse validation traces.

## Reason for Removal

**Evidence**: 0 tool calls across 6 validation traces (before/after refactoring)
**Token Overhead**: Estimated 800-1,600 tokens per request for unused tool schemas
**Cost Impact**: ~$0.0024-0.0048 wasted per request at Claude Sonnet 4 pricing

## Tools Removed

1. **list_available_tools()** - Tool discovery (redundant with prompts)
2. **get_tool_details()** - Parameter documentation (redundant with prompts)
3. **show_cache_metrics()** - Debugging tool (should be external)
4. **store_query()** - Query storage (never used, contradicted prompt guidance)

## Validation Evidence

From REFACTORING_RESULTS.md trace analysis:
- Pair 1: 9 netbox_get_objects calls, 6 write_todos calls, 0 discovery/debug tool calls
- Pair 2: 6 netbox_get_objects calls, 0 write_todos calls, 0 discovery/debug tool calls
- Pair 3: 5 netbox_get_objects calls, 4-5 write_todos calls, 0 discovery/debug tool calls

**Conclusion**: None of these 4 tools were ever called, making them pure overhead.

---

This code is preserved for reference only and should not be used.
"""

from typing import Dict, Any, Annotated
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from deepagents.state import DeepAgentState


# =============================================================================
# TOOL DISCOVERY FUNCTIONS
# =============================================================================

@tool
async def list_available_tools() -> Dict[str, Any]:
    """List the 3 available NetBox MCP tools.

    DEPRECATED: This tool was never used (0 calls in validation).
    All tool information is already provided in SIMPLE_MCP_INSTRUCTIONS prompts.
    Agent doesn't need runtime discovery for 3 simple tools.

    Reason for removal: Redundant with static prompt documentation.
    Token overhead: ~200-300 tokens per request.
    """
    return {
        "total_tools": 3,
        "tools": [
            {
                "name": "netbox_get_objects",
                "description": "Get NetBox objects with optional filtering",
                "parameters": ["object_type (str)", "filters (dict, optional)"]
            },
            {
                "name": "netbox_get_object_by_id",
                "description": "Get detailed information about a specific NetBox object by ID",
                "parameters": ["object_type (str)", "object_id (int)"]
            },
            {
                "name": "netbox_get_changelogs",
                "description": "Get NetBox change audit logs",
                "parameters": ["filters (dict, optional)"]
            }
        ]
    }


@tool
async def get_tool_details(tool_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific NetBox MCP tool.

    DEPRECATED: This tool was never used (0 calls in validation).
    All parameter details and examples are already in:
    1. Tool docstrings (visible to Claude during tool selection)
    2. SIMPLE_MCP_INSTRUCTIONS prompt section

    The tool introspection pattern adds no value for simple 3-tool interface.

    Reason for removal: Redundant with tool docstrings and prompt documentation.
    Token overhead: ~300-400 tokens per request (large nested schema).
    """
    tool_details = {
        "netbox_get_objects": {
            "name": "netbox_get_objects",
            "description": "Generic tool to retrieve ANY NetBox object type with optional filtering",
            "parameters": {
                "object_type": {
                    "type": "str",
                    "required": True,
                    "description": "NetBox object type (devices, sites, racks, ip-addresses, etc.)"
                },
                "filters": {
                    "type": "dict",
                    "required": False,
                    "description": "API filter parameters (site, status, name__ic, etc.)"
                }
            },
            "examples": [
                'netbox_get_objects("sites", {})',
                'netbox_get_objects("devices", {"site": "DM-Akron", "status": "active"})',
                'netbox_get_objects("ip-addresses", {"vrf": "prod"})'
            ]
        },
        "netbox_get_object_by_id": {
            "name": "netbox_get_object_by_id",
            "description": "Get detailed information about a specific NetBox object by its ID",
            "parameters": {
                "object_type": {
                    "type": "str",
                    "required": True,
                    "description": "NetBox object type (devices, sites, etc.)"
                },
                "object_id": {
                    "type": "int",
                    "required": True,
                    "description": "Numeric ID of the object"
                }
            },
            "examples": [
                'netbox_get_object_by_id("devices", 123)',
                'netbox_get_object_by_id("sites", 5)'
            ]
        },
        "netbox_get_changelogs": {
            "name": "netbox_get_changelogs",
            "description": "Get NetBox change audit logs with optional filtering",
            "parameters": {
                "filters": {
                    "type": "dict",
                    "required": False,
                    "description": "Filter criteria (user_id, action, time_before, time_after, etc.)"
                }
            },
            "examples": [
                'netbox_get_changelogs({"time_after": "2025-09-30T00:00:00Z"})',
                'netbox_get_changelogs({"action": "delete"})'
            ]
        }
    }

    if tool_name not in tool_details:
        return {
            "error": f"Tool '{tool_name}' not found",
            "available_tools": list(tool_details.keys())
        }

    return tool_details[tool_name]


# =============================================================================
# DEBUGGING TOOL
# =============================================================================

@tool
async def show_cache_metrics() -> Dict[str, Any]:
    """Display detailed cache performance metrics.

    DEPRECATED: This tool was never used (0 calls in validation).
    This is a debugging/monitoring tool that should be called externally by developers,
    not by the agent during query execution.

    Cache metrics are already tracked and logged by cache_monitor in netbox_agent.py.
    Developers can access metrics through external scripts or monitoring tools.

    Reason for removal: Debugging tool, not execution tool. Should be external.
    Token overhead: ~150-200 tokens per request.
    """
    # Note: cache_monitor is not imported here since this is deprecated
    # If needed, access cache_monitor.get_metrics() directly from netbox_agent module
    return {
        "error": "This tool is deprecated. Access cache metrics externally.",
        "suggestion": "Import cache_monitor from netbox_agent and call cache_monitor.get_metrics()"
    }


# =============================================================================
# QUERY STORAGE TOOL
# =============================================================================

@tool
async def store_query(
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Store the user query in virtual filesystem for reference throughout execution.

    DEPRECATED: This tool was never used (0 calls in validation).

    The prompt explicitly instructed: "Use ONLY when user explicitly requests to save
    the query for future reference (e.g., 'save this query', 'remember this').
    Do not use automatically."

    Since the prompt contradicted the tool's availability (telling agent not to use it),
    and it was never called, it represents pure token overhead with no benefit.

    Reason for removal: Never used, contradicted prompt guidance.
    Token overhead: ~150-200 tokens per request.
    """
    if state.get("messages") and len(state["messages"]) > 0:
        user_query = state["messages"][0].content
        files = state.get("files", {})
        files["query.txt"] = user_query
        return Command(
            update={
                "files": files,
                "messages": [
                    ToolMessage(f"Stored query for reference", tool_call_id=tool_call_id)
                ]
            }
        )
    return Command(update={})


# =============================================================================
# USAGE NOTES
# =============================================================================
"""
If you need to re-enable any of these tools:

1. Copy the function back to netbox_agent.py
2. Add to tool_list in create_netbox_agent_with_simple_mcp()
3. If it's a prompt-visible tool, add guidance to prompts.py
4. Test with validation queries to ensure it's actually used

However, based on empirical evidence, these tools provide no value for
current NetBox query patterns and should remain removed to minimize
token overhead and simplify the agent's tool schema.
"""
