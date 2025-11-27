import os
import sys
import asyncio
import json
import time
from typing import Optional, Dict, Any, List, Annotated

# Add deepagents src to path if not already there
DEEPAGENTS_SRC_PATH = "/home/ola/dev/rnd/deepagents/src"
if DEEPAGENTS_SRC_PATH not in sys.path:
    sys.path.insert(0, DEEPAGENTS_SRC_PATH)

from deepagents import create_deep_agent
from deepagents.cached_model import get_cached_model
from deepagents.state import DeepAgentState
from langchain_core.tools import tool
from langchain_core.tools import InjectedToolCallId
from langchain_core.messages import ToolMessage, SystemMessage, BaseMessage
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from typing import Sequence

# MCP Server Integration
# Using langchain-mcp-adapters to connect to simple MCP server
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Simple MCP Server Configuration
# Path to simple netbox-mcp-server (4 tools with v1.0.0)
NETBOX_MCP_SERVER_DIR = "/home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server"

# Import prompts from centralized module
from prompts import (
    NETBOX_SUPERVISOR_INSTRUCTIONS,
    SUB_AGENT_PROMPT_TEMPLATE,
    THINK_TOOL_DESCRIPTION,
    SIMPLE_MCP_INSTRUCTIONS
)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load from current directory
except ImportError:
    # dotenv not available, try to load manually
    env_file = ".env"
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"\'')
    pass

# MCP Client Session Management
# Global MCP session for communicating with simple MCP server
_mcp_session = None
_mcp_stdio_context = None
_mcp_session_context = None

async def get_mcp_session():
    """Get or create MCP client session connected to simple NetBox MCP server"""
    global _mcp_session, _mcp_stdio_context, _mcp_session_context

    if _mcp_session is None:
        # Verify environment variables are set
        netbox_url = os.getenv("NETBOX_URL")
        netbox_token = os.getenv("NETBOX_TOKEN")

        if not netbox_url or not netbox_token:
            raise ValueError("NETBOX_URL and NETBOX_TOKEN environment variables must be set")

        # Create MCP server parameters for stdio communication
        # Using uv run netbox-mcp-server (v1.0.0 command structure)
        server_params = StdioServerParameters(
            command="uv",
            args=[
                "--directory",
                NETBOX_MCP_SERVER_DIR,
                "run",
                "netbox-mcp-server"
            ],
            env={
                **os.environ,  # Pass through all env vars including NETBOX_URL and NETBOX_TOKEN
            }
        )

        # Create stdio client context and enter it
        _mcp_stdio_context = stdio_client(server_params)
        read, write = await _mcp_stdio_context.__aenter__()

        # Create and initialize session
        _mcp_session_context = ClientSession(read, write)
        _mcp_session = await _mcp_session_context.__aenter__()

        # CRITICAL: Initialize the session before making any tool calls
        await _mcp_session.initialize()

    return _mcp_session

async def cleanup_mcp_session():
    """Clean up MCP session and stdio context"""
    global _mcp_session, _mcp_stdio_context, _mcp_session_context

    if _mcp_session_context is not None:
        try:
            await _mcp_session_context.__aexit__(None, None, None)
        except Exception as e:
            print(f"Warning: Error closing MCP session: {e}")
        _mcp_session_context = None
        _mcp_session = None

    if _mcp_stdio_context is not None:
        try:
            await _mcp_stdio_context.__aexit__(None, None, None)
        except Exception as e:
            print(f"Warning: Error closing stdio context: {e}")
        _mcp_stdio_context = None

async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Call a tool on the MCP server and return the result"""
    session = await get_mcp_session()

    try:
        result = await session.call_tool(tool_name, arguments=arguments)

        # MCP returns a CallToolResult object with content array
        if hasattr(result, 'content') and len(result.content) > 0:
            import json

            # Check if we have a single content item (normal case)
            if len(result.content) == 1:
                content = result.content[0]
                if hasattr(content, 'text'):
                    try:
                        return json.loads(content.text)
                    except (json.JSONDecodeError, ValueError) as e:
                        # Return error dict for invalid JSON instead of raising
                        return {"error": f"Invalid JSON response: {content.text[:100] if content.text else 'empty'}"}
                return {"result": str(content)}

            # Multiple content items - each is a separate JSON object in an array
            # Parse each one and combine them into a single array
            all_items = []
            for content in result.content:
                if hasattr(content, 'text'):
                    try:
                        item = json.loads(content.text)
                        all_items.append(item)
                    except json.JSONDecodeError:
                        # If it's not valid JSON, include as string
                        all_items.append({"text": content.text})

            # Return as array if we have multiple items
            return all_items if all_items else {"result": str(result.content)}

        return {"result": str(result)}
    except Exception as e:
        # Return error dict instead of raising ToolException
        # This allows the agent to see the error and continue execution
        # rather than terminating the entire run
        return {"error": f"Tool '{tool_name}' failed: {str(e)}"}


# =============================================================================
# SIMPLE MCP TOOLS (3 generic tools instead of 62 specialized ones)
# =============================================================================

@tool
async def netbox_get_objects(
    object_type: str,
    filters: dict = None,
    fields: list = None,
    brief: bool = False,
    limit: int = 5,
    offset: int = 0,
    ordering: str = None
) -> dict:
    """Get NetBox objects with optional filtering via MCP server.

    This is a generic tool that can retrieve ANY NetBox object type.

    Args:
        object_type: NetBox object type in app.model format. Common types:
            DCIM: dcim.device, dcim.site, dcim.rack, dcim.cable, dcim.interface
                  dcim.manufacturer, dcim.devicetype, dcim.devicerole, dcim.platform
            IPAM: ipam.ipaddress, ipam.prefix, ipam.vlan, ipam.vlangroup, ipam.vrf, ipam.asn
            Tenancy: tenancy.tenant, tenancy.tenantgroup, tenancy.contact
            Virtualization: virtualization.virtualmachine, virtualization.cluster

        filters: Optional dict of API filters. Examples:
            {"site": "DM-Akron"} - Filter by site name
            {"status": "active"} - Filter by status
            {"name__ic": "switch"} - Case-insensitive name contains

        fields: Optional list of fields to return (token optimization).
            Example: ["id", "name", "status"] reduces 5000 → 500 tokens (90%)
            Common patterns:
            - Devices: ["id", "name", "status", "device_type", "site"]
            - IPs: ["id", "address", "status", "dns_name"]
            - Sites: ["id", "name", "status", "region"]

        brief: Return minimal object representation (default: False)

        limit: Maximum results per page (default: 5, max: 100)

        offset: Pagination offset (default: 0)

        ordering: Sort by field(s). Examples: "name", "-created", ["name", "status"]

    Returns:
        List of objects matching the filters

    Examples:
        - List all sites: netbox_get_objects("dcim.site", {})
        - Active devices in site: netbox_get_objects("dcim.device", {"site": "DM-Akron", "status": "active"})
        - Find IPs with minimal data: netbox_get_objects("ipam.ipaddress", {"vrf": "prod"}, fields=["id", "address"])
        - Get 10 devices sorted by name: netbox_get_objects("dcim.device", {}, limit=10, ordering="name")
    """
    filters = filters or {}

    # Build arguments for MCP tool
    arguments = {
        "object_type": object_type,
        "filters": filters,
        "limit": limit,
        "offset": offset,
        "brief": brief
    }

    # Add optional parameters only if provided
    if fields is not None:
        arguments["fields"] = fields
    if ordering is not None:
        arguments["ordering"] = ordering

    # Call the MCP server's netbox_get_objects tool
    result = await call_mcp_tool("netbox_get_objects", arguments)

    return result


@tool
async def netbox_get_object_by_id(
    object_type: str,
    object_id: int,
    fields: list = None,
    brief: bool = False
) -> dict:
    """Get detailed information about a specific NetBox object by its ID via MCP server.

    Args:
        object_type: NetBox object type in app.model format (e.g., "dcim.device", "dcim.site", "ipam.ipaddress")
        object_id: The numeric ID of the object

        fields: Optional list of fields to return (token optimization).
            Example: ["id", "name", "status"] for minimal response
            Leave None for complete object details

        brief: Return minimal object representation (default: False)
            Use for quick ID/name lookups without full details

    Returns:
        Complete object details including all relationships (or filtered if fields specified)

    Examples:
        - Get full device details: netbox_get_object_by_id("dcim.device", 123)
        - Get device name only: netbox_get_object_by_id("dcim.device", 123, fields=["id", "name"])
        - Get brief site info: netbox_get_object_by_id("dcim.site", 5, brief=True)
        - Get IP with specific fields: netbox_get_object_by_id("ipam.ipaddress", 456, fields=["address", "dns_name"])
    """
    # Build arguments for MCP tool
    arguments = {
        "object_type": object_type,
        "object_id": object_id,
        "brief": brief
    }

    # Add optional parameters only if provided
    if fields is not None:
        arguments["fields"] = fields

    # Call the MCP server's netbox_get_object_by_id tool
    result = await call_mcp_tool("netbox_get_object_by_id", arguments)

    return result


@tool
async def netbox_get_changelogs(filters: dict = None) -> dict:
    """Get NetBox change audit logs (changelogs) via MCP server.

    Retrieve object change records to track who modified what and when.

    Args:
        filters: Optional dict of filters:
            user_id: Filter by user ID
            user: Filter by username
            changed_object_type_id: Filter by object type
            changed_object_id: Filter by object ID
            action: Filter by action (created, updated, deleted)
            time_before: Changes before this time (ISO 8601)
            time_after: Changes after this time (ISO 8601)
            q: Search term for object representation

    Returns:
        List of changelog entries with details about changes

    Examples:
        - Recent changes: netbox_get_changelogs({"time_after": "2025-09-30T00:00:00Z"})
        - Changes to device: netbox_get_changelogs({"changed_object_id": 123})
        - Deletions: netbox_get_changelogs({"action": "delete"})
    """
    filters = filters or {}

    # Call the MCP server's netbox_get_changelogs tool
    result = await call_mcp_tool("netbox_get_changelogs", {
        "filters": filters
    })

    return result


@tool
async def netbox_search_objects(
    query: str,
    object_types: list = None,
    fields: list = None,
    limit: int = 5
) -> dict:
    """Search across multiple NetBox object types using natural language query.

    This tool performs global search across NetBox infrastructure, making it ideal
    for exploratory queries where you don't know the exact object type.

    Args:
        query: Search term (e.g., "switch", "192.168", "Cisco")

        object_types: Optional list of object types to search in app.model format. If None, searches common types.
            Example: ["dcim.device", "ipam.ipaddress", "dcim.site"]
            Leave None to search across common types: dcim.device, dcim.site, dcim.rack, ipam.ipaddress, ipam.prefix

        fields: Optional list of fields to return per object type (token optimization)
            Example: ["id", "name", "status"]

        limit: Maximum results per object type (default: 5)

    Returns:
        Dictionary with results grouped by object type

    Examples:
        - Find anything named "core": netbox_search_objects("core")
        - Search devices and sites: netbox_search_objects("DC1", object_types=["dcim.device", "dcim.site"])
        - Search with minimal data: netbox_search_objects("switch", fields=["id", "name"])
        - Find IP addresses: netbox_search_objects("192.168.1", object_types=["ipam.ipaddress"])
    """
    # Build arguments for MCP tool
    arguments = {
        "query": query,
        "limit": limit
    }

    # Add optional parameters only if provided
    if object_types is not None:
        arguments["object_types"] = object_types
    if fields is not None:
        arguments["fields"] = fields

    # Call the MCP server's netbox_search_objects tool
    result = await call_mcp_tool("netbox_search_objects", arguments)

    return result


# =============================================================================
# TOOL DISCOVERY FUNCTIONS REMOVED
# =============================================================================
# list_available_tools() and get_tool_details() have been removed.
# These discovery tools were never used (0 calls across validation traces)
# and were redundant with prompt documentation. Preserved in netbox_tools_deprecated.py.

# Add cache monitoring class
class CacheMonitor:
    """Monitor and report cache performance metrics"""

    def __init__(self):
        self.requests = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_input_tokens = 0
        self.cached_tokens_read = 0
        self.cached_tokens_written = 0
        self.uncached_tokens = 0  # Track non-cached input tokens separately

    def log_request(self, response_data):
        """Extract and log cache metrics from API response or LangChain result"""
        usage = {}

        # Handle different response formats
        if hasattr(response_data, 'response_metadata'):
            # LangChain response format
            usage = response_data.response_metadata.get('usage', {})
        elif isinstance(response_data, dict):
            # Direct API response format
            usage = response_data.get("usage", {})
        else:
            # Try to extract from nested structure
            try:
                if hasattr(response_data, 'usage'):
                    usage = response_data.usage
                else:
                    # Last resort - try to find usage in the object
                    usage = getattr(response_data, 'usage', {})
            except:
                usage = {}

        # Track cache performance
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_write = usage.get("cache_creation_input_tokens", 0)

        if cache_read > 0:
            self.cache_hits += 1
            self.cached_tokens_read += cache_read
            print(f"🟢 Cache HIT: {cache_read} tokens read from cache")
        else:
            self.cache_misses += 1
            if cache_write > 0:
                print(f"🔵 Cache WRITE: {cache_write} tokens written to cache")

        if cache_write > 0:
            self.cached_tokens_written += cache_write

        input_tokens = usage.get("input_tokens", 0)
        self.total_input_tokens += input_tokens

        # Calculate uncached tokens (input tokens that weren't served from cache)
        uncached = input_tokens - cache_read
        self.uncached_tokens += max(0, uncached)  # Ensure non-negative

        # Store request metadata
        request_data = {
            "timestamp": time.time(),
            "cache_read": cache_read,
            "cache_write": cache_write,
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0)
        }
        self.requests.append(request_data)

        # Log cache activity for debugging
        if cache_read > 0 or cache_write > 0:
            print(f"💾 Cache Activity: Read={cache_read}, Write={cache_write}, Input={usage.get('input_tokens', 0)}")

        return request_data

    def get_metrics(self) -> Dict[str, Any]:
        """Calculate and return cache performance metrics"""
        if not self.requests:
            return {"status": "No requests logged"}

        total_requests = len(self.requests)
        cache_hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

        # Calculate costs with corrected formula
        # Claude API pricing: $3.00/M input, $0.30/M cached read (90% discount), $3.75/M cache write (25% premium)

        # What we actually paid (with caching)
        uncached_cost = (self.uncached_tokens / 1_000_000) * 3.00
        cache_read_cost = (self.cached_tokens_read / 1_000_000) * 0.30
        cache_write_cost = (self.cached_tokens_written / 1_000_000) * 3.75
        actual_cost = uncached_cost + cache_read_cost + cache_write_cost

        # What we would have paid (without caching - all tokens at standard rate)
        total_tokens = self.uncached_tokens + self.cached_tokens_read + self.cached_tokens_written
        standard_cost = (total_tokens / 1_000_000) * 3.00

        # Calculate savings percentage
        savings_percentage = ((standard_cost - actual_cost) / standard_cost * 100) if standard_cost > 0 else 0

        return {
            "total_requests": total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "total_input_tokens": self.total_input_tokens,
            "uncached_tokens": self.uncached_tokens,
            "cached_tokens_read": self.cached_tokens_read,
            "cached_tokens_written": self.cached_tokens_written,
            "estimated_cost_savings": f"{savings_percentage:.1f}%",
            "standard_cost": f"${standard_cost:.4f}",
            "actual_cost": f"${actual_cost:.4f}"
        }

# Global cache monitor instance
cache_monitor = CacheMonitor()

# =============================================================================
# Sub-agents disabled - preserved in netbox_subagents_deprecated.py
# =============================================================================
# The create_netbox_subagents() function has been moved to
# netbox_subagents_deprecated.py. Validation testing showed that direct
# sequential execution in the main agent context is more efficient than
# spawning specialized domain sub-agents (0 task() calls across all validation
# queries). See VALIDATION_RESULTS_SUMMARY.md for details.

# =============================================================================
# DEPRECATED: Complex MCP Agent (62 tools) - NO LONGER FUNCTIONAL
# =============================================================================
# The create_netbox_agent_with_all_tools() function has been removed.
# It depended on complex MCP code that was deleted in the simple MCP migration.
#
# Use create_netbox_agent_with_simple_mcp() instead, which provides:
# - 3 generic MCP tools (netbox_get_objects, netbox_get_object_by_id, netbox_get_changelogs)
# - Same cross-domain coordination capabilities
# - Much more efficient prompt caching
# - All NetBox object types accessible via object_type parameter
# =============================================================================


class CachedChatAnthropicFixed(ChatAnthropic):
    """
    Custom ChatAnthropic that properly implements prompt caching.

    Fixes the issue where SystemMessage objects break tool binding in LangGraph.
    This class uses the standard string prompt approach but adds cache_control
    via the generate_prompt override.
    """
    cache_ttl: str = "1h"

    def _generate_with_cache(
        self,
        messages: Sequence[BaseMessage],
        stop: Optional[Sequence[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """Override to add cache_control before calling API"""
        # Add cache_control to kwargs if not present
        if 'cache_control' not in kwargs:
            kwargs['cache_control'] = {"type": "ephemeral", "ttl": self.cache_ttl}

        return super()._generate_with_cache(messages, stop, run_manager, **kwargs)

    async def _agenerate_with_cache(
        self,
        messages: Sequence[BaseMessage],
        stop: Optional[Sequence[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """Async override to add cache_control before calling API"""
        # Add cache_control to kwargs if not present
        if 'cache_control' not in kwargs:
            kwargs['cache_control'] = {"type": "ephemeral", "ttl": self.cache_ttl}

        return await super()._agenerate_with_cache(messages, stop, run_manager, **kwargs)


def create_netbox_agent_with_simple_mcp(
    enable_caching: bool = True,
    cache_ttl: str = "1h"
):
    """
    Create a NetBox agent using simple MCP server (3 generic tools).

    This version connects to the simple NetBox MCP server which provides
    3 generic tools that accept object_type parameters, rather than 62
    specialized tools. Much more efficient for prompt caching.

    Args:
        enable_caching: Enable Claude API prompt caching
        cache_ttl: Cache duration ("default" for 5min or "1h" for 1 hour)
    """
    print(f"🚀 Creating NetBox agent with simple MCP (4 tools)...")

    # Essential tools only (5 total: 4 MCP + 1 strategic)
    tool_list = [
        netbox_get_objects,
        netbox_get_object_by_id,
        netbox_get_changelogs,
        netbox_search_objects,
        think
    ]
    # Removed unused tools (0 calls in validation traces):
    # - list_available_tools (redundant with prompts)
    # - get_tool_details (redundant with prompts)
    # - show_cache_metrics (debugging tool, should be external)
    # - store_query (never used, contradicted prompt guidance)

    # Update think tool description
    think.__doc__ = THINK_TOOL_DESCRIPTION

    # Sub-agents disabled - validation showed direct execution is optimal
    # All cross-domain queries execute more efficiently with sequential tool calls
    # in the main agent context rather than spawning specialized sub-agents
    netbox_subagents = []

    # Combined instructions for simple MCP
    full_instructions = NETBOX_SUPERVISOR_INSTRUCTIONS + "\n\n" + SIMPLE_MCP_INSTRUCTIONS

    print(f"📊 Simple MCP Configuration:")
    print(f"  - Total Tools: {len(tool_list)}")
    print(f"  - NetBox MCP Tools: 4 (get_objects, get_object_by_id, get_changelogs, search_objects)")
    print(f"  - Strategic Tools: 1 (think)")
    print(f"  - Sub-agents: Disabled (direct execution mode)")
    print(f"  - Instructions Size: ~{len(full_instructions)//4} tokens")
    print(f"  - Caching Enabled: {enable_caching}")
    print(f"  - Cache TTL: {cache_ttl}")
    print(f"  - New in v1.0: Field filtering, pagination, search (90% token reduction possible)")

    # Use CachedChatAnthropicFixed for proper caching with tool binding
    if enable_caching:
        model = CachedChatAnthropicFixed(
            model_name="claude-sonnet-4-20250514",
            max_tokens=64000,
            betas=["extended-cache-ttl-2025-04-11"],  # Enable 1-hour cache TTL
            cache_ttl=cache_ttl
        )
        print(f"🔄 Caching enabled with 1-hour TTL on system prompt (~{len(full_instructions)//4} tokens)")
    else:
        model = ChatAnthropic(
            model_name="claude-sonnet-4-20250514",
            max_tokens=64000
        )

    # Create agent with PLAIN STRING (not SystemMessage) to preserve tool binding
    # CachedChatAnthropicFixed will add cache_control internally
    agent = create_deep_agent(
        tools=tool_list,
        system_prompt=full_instructions,  # Plain string to preserve tool binding
        model=model,
        subagents=netbox_subagents
    ).with_config({
        # Base recursion limit (overridden at invocation time)
        # See invocation config for actual limit used
        "recursion_limit": 1000
    })

    # Store caching config
    agent._cache_config = {
        "enabled": enable_caching,
        "ttl": cache_ttl,
        "mcp_mode": "simple"
    }

    print(f"✅ Agent created successfully with simple MCP")

    return agent

# show_cache_metrics() removed - debugging tool should be called externally,
# not by agent during execution. Preserved in netbox_tools_deprecated.py.

# Add strategic think tool (following deep-agents-from-scratch pattern)
@tool
async def think(reflection: str) -> str:
    """Strategic reflection tool for analyzing progress and planning next steps.

    Use this to:
    - Reflect on what information you've gathered
    - Assess whether you have enough to answer the query
    - Identify what's still missing
    - Decide on next steps strategically

    The reflection should include your analysis of the original query
    and your current understanding of what's needed.
    """
    return f"Reflection recorded: {reflection}"

# store_query() removed - never used (0 calls in validation) and contradicted
# prompt guidance. Preserved in netbox_tools_deprecated.py.

# Create the global agent instance (will be initialized in main or when imported)

def extract_agent_response(result):
    """Extract the final agent response in a clean format"""
    try:
        messages = result.get('messages', [])
        for msg in reversed(messages):
            if hasattr(msg, 'content') and hasattr(msg, 'type') and msg.type == 'ai':
                # Skip empty AI messages (can happen when agent has nothing left to say)
                content = msg.content
                if isinstance(content, str) and content.strip():
                    return content, len(messages)
                elif isinstance(content, list) and len(content) > 0:
                    # Check if list has actual text content
                    has_content = any(
                        item.get('type') == 'text' and item.get('text', '').strip()
                        for item in content
                        if isinstance(item, dict)
                    )
                    if has_content:
                        return content, len(messages)
                # If content is empty, continue searching for previous AI message
        return "No response found", len(messages)
    except Exception as e:
        return f"Error extracting response: {e}", 0

async def process_netbox_query(query: str, track_metrics: bool = True, verbose: bool = False):
    """Process a NetBox query with cache tracking

    Args:
        query: The query string to process
        track_metrics: Whether to track and log cache metrics (default: True)
        verbose: Whether to show detailed metrics output (default: False)
    """
    if verbose:
        print(f"\n🔄 Processing: {query}")

    try:
        start_time = time.time()

        result = await netbox_agent.ainvoke({
            "messages": [{"role": "user", "content": query}]
        }, config={
            # Actual recursion limit used (overrides base config)
            # Set to 50 after validation showed queries need 12-15 steps
            # Original limit of 20 caused Query 3 and 4 failures
            'recursion_limit': 50
        })

        elapsed = time.time() - start_time
        response, msg_count = extract_agent_response(result)

        # Enhanced cache metrics logging
        if track_metrics and verbose:
            # First, try to extract detailed cache info from the last AI message
            ai_messages = [msg for msg in result.get('messages', []) if hasattr(msg, 'response_metadata')]
            if ai_messages:
                last_ai_msg = ai_messages[-1]
                usage = last_ai_msg.response_metadata.get('usage', {})

                if usage:
                    total_input = usage.get('input_tokens', 0)
                    cache_create = usage.get('cache_creation_input_tokens', 0)
                    cache_read = usage.get('cache_read_input_tokens', 0)

                    if cache_read > 0 or cache_create > 0:
                        print(f"\n💾 Cache Performance (This Request):")
                        if cache_create > 0:
                            print(f"  ✨ Cache Created: {cache_create:,} tokens (~${cache_create * 0.00375 / 1000:.4f})")
                        if cache_read > 0:
                            cache_hit_rate = (cache_read / total_input * 100) if total_input > 0 else 0
                            savings = (cache_read * 0.003 / 1000) - (cache_read * 0.0003 / 1000)
                            print(f"  📖 Cache Read: {cache_read:,} tokens (saved ~${savings:.4f})")
                            print(f"  📊 Cache Hit Rate: {cache_hit_rate:.1f}%")
                    elif total_input > 0:
                        print(f"\n⚠️ Cache Miss: {total_input:,} input tokens, no cache used")

        # Extract and log cache metrics from the result (original method)
        if track_metrics:
            # Try multiple ways to extract cache metrics
            logged = False

            # Method 1: Check if result has messages with response metadata
            if hasattr(result, 'get') and 'messages' in result:
                for msg in result['messages']:
                    if hasattr(msg, 'response_metadata') and 'usage' in msg.response_metadata:
                        cache_monitor.log_request(msg)
                        logged = True
                        break

            # Method 2: Check direct result format
            if not logged and hasattr(result, 'response_metadata'):
                cache_monitor.log_request(result)
                logged = True

            # Method 3: Try to find any usage data in the result
            if not logged:
                try:
                    # Recursively search for usage data
                    def find_usage(obj, path=""):
                        if isinstance(obj, dict):
                            if 'usage' in obj:
                                print(f"🔍 Found usage at {path}: {obj['usage']}")
                                cache_monitor.log_request(obj)
                                return True
                            for key, value in obj.items():
                                if find_usage(value, f"{path}.{key}"):
                                    return True
                        elif hasattr(obj, '__dict__'):
                            return find_usage(obj.__dict__, f"{path}.__dict__")
                        elif hasattr(obj, 'response_metadata'):
                            return find_usage(obj.response_metadata, f"{path}.response_metadata")
                        return False

                    if not find_usage(result):
                        print("⚠️ No cache metrics found in response")
                except Exception as e:
                    print(f"⚠️ Cache metrics extraction failed: {e}")

        print(f"\n🤖 NetBox Agent Response:")
        print("-" * 60)
        print(response)
        print("-" * 60)
        print(f"📊 Messages: {msg_count} | ⏱️ Time: {elapsed:.2f}s")

        # Show cache metrics summary
        if track_metrics and cache_monitor.requests:
            latest_request = cache_monitor.requests[-1]
            if latest_request['cache_read'] > 0 or latest_request['cache_write'] > 0:
                metrics = cache_monitor.get_metrics()
                print(f"\n💰 Cache Performance Summary:")
                print(f"  - Hit Rate: {metrics['cache_hit_rate']}")
                print(f"  - Cost Savings: {metrics['estimated_cost_savings']}")
                print(f"  - Total Requests: {len(cache_monitor.requests)}")

    except Exception as e:
        print(f"❌ Query failed: {str(e)}")
        raise

async def get_user_input(prompt: str) -> str:
    """Get user input asynchronously without blocking event loop"""
    try:
        return await asyncio.to_thread(input, prompt)
    except EOFError:
        return "exit"  # Handle Ctrl+D

# Example usage with human-friendly responses
async def main():
    """Interactive NetBox agent CLI with continuous query loop"""

    # Welcome message
    print("🚀 NetBox Interactive Agent CLI (v1.0 - Enhanced)")
    print("Agent has access to 4 MCP tools with field filtering:")
    print("  • netbox_get_objects - List/search any NetBox object type")
    print("  • netbox_get_object_by_id - Get detailed object information")
    print("  • netbox_get_changelogs - Query change audit logs")
    print("  • netbox_search_objects - Global search across object types (NEW)")
    print("\n✨ New Features: Field filtering (90% token reduction), pagination, brief mode")
    print("Supports ALL NetBox object types via object_type parameter")
    print("\nAvailable commands:")
    print("  - Type any NetBox query in natural language")
    print("  - 'exit', 'quit', or 'q' to quit")
    print("  - Ctrl+C for immediate exit")
    print(f"\n{'='*60}")

    try:
        while True:
            try:
                # Get user input
                query = await get_user_input("\n💬 NetBox Query: ")

                # Handle exit commands
                if query.lower().strip() in ['exit', 'quit', 'q', '']:
                    print("👋 Goodbye!")
                    break

                # Process the query
                await process_netbox_query(query)

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                print("Please try again or type 'exit' to quit.")

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    finally:
        # Clean up MCP session on exit
        await cleanup_mcp_session()

# Global agent instance
netbox_agent = None

async def async_main():
    """Async entry point for the application"""
    global netbox_agent

    try:
        # Check for cache environment variable
        enable_cache = os.environ.get("NETBOX_CACHE", "true").lower() == "true"
        cache_duration = os.environ.get("NETBOX_CACHE_TTL", "1h")

        print(f"💾 Prompt Caching: {'Enabled' if enable_cache else 'Disabled'}")
        if enable_cache:
            print(f"⏰ Cache Duration: {cache_duration}")

        # Create agent with simple MCP (3 tools)
        netbox_agent = create_netbox_agent_with_simple_mcp(
            enable_caching=enable_cache,
            cache_ttl=cache_duration
        )

        # Run main interactive loop
        await main()
    finally:
        # Always clean up MCP session on exit
        await cleanup_mcp_session()
        print("✅ MCP session cleaned up")

if __name__ == "__main__":
    asyncio.run(async_main())