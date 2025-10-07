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

from deepagents import async_create_deep_agent
from deepagents.cached_model import get_cached_model
from deepagents.state import DeepAgentState
from langchain_core.tools import tool
from langchain_core.tools import InjectedToolCallId
from langchain_core.messages import ToolMessage
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

# MCP Server Integration
# Using langchain-mcp-adapters to connect to simple MCP server
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Simple MCP Server Configuration
# Path to simple netbox-mcp-server (3 tools instead of 62)
SIMPLE_MCP_SERVER_PATH = "/home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server/server.py"

# Import prompts from centralized module
from prompts import (
    NETBOX_SUPERVISOR_INSTRUCTIONS,
    SUB_AGENT_PROMPT_TEMPLATE,
    THINK_TOOL_DESCRIPTION,
    SIMPLE_MCP_INSTRUCTIONS
)

"""
PARALLEL EXECUTION PATTERNS FOR CROSS-DOMAIN QUERIES

Pattern 1: Independent Domain Analysis
When domains can be queried without dependencies, execute in parallel:

# Example: Tenant infrastructure analysis
async def analyze_tenant_infrastructure(tenant_name: str):
    # PARALLEL execution - all three run simultaneously
    await asyncio.gather(
        task(
            description=f"Get complete details for tenant '{tenant_name}' including groups and contacts",
            subagent_type="tenancy-specialist"
        ),
        task(
            description=f"List all devices assigned to tenant '{tenant_name}' with rack and site information",
            subagent_type="dcim-specialist"
        ),
        task(
            description=f"Get all IP addresses and VLANs allocated to tenant '{tenant_name}'",
            subagent_type="ipam-specialist"
        )
    )
    # After parallel execution, use think() to assess and synthesize

Pattern 2: VM Network Topology
When tracing relationships across domains:

# Step 1: Get VM details (single domain)
vm_info = await task(
    description="Get virtual machine 'web-app-02' details including cluster and interfaces",
    subagent_type="virtualization-specialist"
)

# Step 2: Think and identify next parallel queries
await think(
    reflection='''Retrieved VM details for web-app-02, including cluster and interfaces.
    Now need to trace to physical infrastructure.

    Next parallel queries:
    - Get physical host and rack location from DCIM for the cluster
    - Get IP and VLAN configuration from IPAM for the VM interfaces'''
)

# Step 3: Parallel queries for related information
await asyncio.gather(
    task(
        description=f"Get physical host and rack location for cluster {vm_info['cluster']}",
        subagent_type="dcim-specialist"
    ),
    task(
        description=f"Get IP and VLAN configuration for VM interfaces {vm_info['interfaces']}",
        subagent_type="ipam-specialist"
    )
)

Pattern 3: Site Utilization with Multi-Domain Metrics
For comprehensive analysis requiring all domains:

# MAXIMUM parallel execution (all 4 domains)
site_data = await asyncio.gather(
    task(
        description="Get complete device inventory for site 'Butler Communications' with power usage",
        subagent_type="dcim-specialist"
    ),
    task(
        description="Calculate IP utilization and VLAN usage for site 'Butler Communications'",
        subagent_type="ipam-specialist"
    ),
    task(
        description="List all tenants with resources at site 'Butler Communications'",
        subagent_type="tenancy-specialist"
    ),
    task(
        description="Get all virtual machines hosted at site 'Butler Communications'",
        subagent_type="virtualization-specialist"
    )
)

# Strategic reflection after parallel execution
await think(
    reflection='''Completed parallel data collection from all 4 domains for site Butler Communications.

    Have gathered:
    - Device inventory and power usage (DCIM)
    - IP utilization and VLAN usage (IPAM)
    - Tenant resource allocation (Tenancy)
    - Virtual machine inventory (Virtualization)

    Next steps: Correlate devices with VMs, map tenants to resources, calculate totals.'''
)

Example Cross-Domain Query Flow with Strategic Thinking:
# Query: "Show tenant 'Research Lab' infrastructure footprint across all sites"

# 1. Strategic Assessment
await think(
    reflection='''Analyzing query: 'Show tenant Research Lab infrastructure footprint across all sites'
    This spans Tenancy + DCIM + IPAM domains and requires site correlation.

    Information gaps:
    - Need tenant details from tenancy domain
    - Need device inventory from DCIM domain
    - Need network allocations from IPAM domain
    - Need to correlate by site

    Next steps: Execute parallel domain queries, then synthesize results.'''
)

# 2. Planning
await write_todos([
    {"content": "Get Research Lab tenant information", "status": "in_progress"},
    {"content": "Query devices, IPs, VLANs in parallel", "status": "pending"},
    {"content": "Correlate resources by site", "status": "pending"},
    {"content": "Generate infrastructure footprint report", "status": "pending"}
])

# 3. Parallel Domain Delegation (single response, multiple task calls)
results = await asyncio.gather(
    task(
        description="Get complete information for tenant 'Research Lab' including all resource reports",
        subagent_type="tenancy-specialist"
    ),
    task(
        description="List all devices assigned to tenant 'Research Lab' with site, rack, and type details",
        subagent_type="dcim-specialist"
    ),
    task(
        description="Get all IP addresses, prefixes, and VLANs allocated to tenant 'Research Lab'",
        subagent_type="ipam-specialist"
    )
)

# 4. Strategic Reflection
await think(
    reflection='''Received comprehensive data from 3 parallel domain queries.

    Current state:
    - Have tenant overview and resource reports from tenancy-specialist
    - Have complete device inventory with site/rack details from dcim-specialist
    - Have IP/prefix/VLAN allocations from ipam-specialist

    Gap identified: Need to correlate all resources by site for infrastructure footprint view.

    Final steps: Group resources by site, calculate per-site metrics, format comprehensive report.'''
)

# 5. Synthesis and Response
# Agent combines results into cohesive infrastructure footprint report
"""

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
_mcp_client = None

async def get_mcp_session():
    """Get or create MCP client session connected to simple NetBox MCP server"""
    global _mcp_session, _mcp_client

    if _mcp_session is None:
        # Verify environment variables are set
        netbox_url = os.getenv("NETBOX_URL")
        netbox_token = os.getenv("NETBOX_TOKEN")

        if not netbox_url or not netbox_token:
            raise ValueError("NETBOX_URL and NETBOX_TOKEN environment variables must be set")

        # Create MCP server parameters for stdio communication
        server_params = StdioServerParameters(
            command="python",
            args=[SIMPLE_MCP_SERVER_PATH],
            env={
                **os.environ,  # Pass through all env vars including NETBOX_URL and NETBOX_TOKEN
            }
        )

        # Create stdio client context
        stdio = stdio_client(server_params)
        _mcp_client = stdio.__aenter__()  # Enter the async context
        read, write = await _mcp_client

        # Create session
        _mcp_session = ClientSession(read, write)
        await _mcp_session.__aenter__()  # Initialize session

    return _mcp_session

async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Call a tool on the MCP server and return the result"""
    session = await get_mcp_session()

    try:
        result = await session.call_tool(tool_name, arguments=arguments)

        # MCP returns a CallToolResult object with content array
        if hasattr(result, 'content') and len(result.content) > 0:
            # Extract the text content from the result
            content = result.content[0]
            if hasattr(content, 'text'):
                # Parse the JSON string response
                import json
                return json.loads(content.text)
            return {"result": str(content)}

        return {"result": str(result)}
    except Exception as e:
        return {"error": str(e), "tool": tool_name, "arguments": arguments}


# =============================================================================
# SIMPLE MCP TOOLS (3 generic tools instead of 62 specialized ones)
# =============================================================================

@tool
async def netbox_get_objects(object_type: str, filters: dict = None) -> dict:
    """Get NetBox objects with optional filtering via MCP server.

    This is a generic tool that can retrieve ANY NetBox object type.

    Args:
        object_type: NetBox object type. Common types include:
            DCIM: devices, sites, racks, cables, interfaces, manufacturers,
                  device-types, device-roles, power-outlets, power-ports
            IPAM: ip-addresses, prefixes, vlans, vlan-groups, vrfs, asns
            Tenancy: tenants, tenant-groups, contacts
            Virtualization: virtual-machines, clusters, vm-interfaces

        filters: Optional dict of API filters. Examples:
            {"site": "DM-Akron"} - Filter by site name
            {"status": "active"} - Filter by status
            {"name__ic": "switch"} - Case-insensitive name contains

    Returns:
        List of objects matching the filters

    Examples:
        - List all sites: netbox_get_objects("sites", {})
        - Active devices in site: netbox_get_objects("devices", {"site": "DM-Akron", "status": "active"})
        - Find IPs in VRF: netbox_get_objects("ip-addresses", {"vrf": "prod"})
    """
    filters = filters or {}

    # Call the MCP server's netbox_get_objects tool
    result = await call_mcp_tool("netbox_get_objects", {
        "object_type": object_type,
        "filters": filters
    })

    return result


@tool
async def netbox_get_object_by_id(object_type: str, object_id: int) -> dict:
    """Get detailed information about a specific NetBox object by its ID via MCP server.

    Args:
        object_type: NetBox object type (e.g., "devices", "sites", "ip-addresses")
        object_id: The numeric ID of the object

    Returns:
        Complete object details including all relationships

    Examples:
        - Get device details: netbox_get_object_by_id("devices", 123)
        - Get site info: netbox_get_object_by_id("sites", 5)
        - Get IP details: netbox_get_object_by_id("ip-addresses", 456)
    """
    # Call the MCP server's netbox_get_object_by_id tool
    result = await call_mcp_tool("netbox_get_object_by_id", {
        "object_type": object_type,
        "object_id": object_id
    })

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


# =============================================================================
# SIMPLE MCP TOOL DISCOVERY
# =============================================================================

@tool
async def list_available_tools() -> Dict[str, Any]:
    """List the 3 available NetBox MCP tools."""
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
    """Get detailed information about a specific NetBox MCP tool."""
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

def create_netbox_subagents():
    """Create domain-specific sub-agents for simple MCP (3 tools each)"""

    # All specialists use the same 3 simple MCP tools
    simple_tools = [
        "netbox_get_objects",
        "netbox_get_object_by_id",
        "netbox_get_changelogs"
    ]

    # Format sub-agent prompts with object_type guidance
    dcim_prompt = SUB_AGENT_PROMPT_TEMPLATE.format(
        domain="DCIM",
        expertise_areas="physical infrastructure management",
        detailed_expertise="""
        - Device inventory: servers, switches, routers, PDUs
        - Rack management: layouts, elevations, utilization
        - Site topology: locations, regions, hierarchies
        - Cable management: connections, paths, types
        - Power distribution: outlets, feeds, consumption
        - Physical interfaces: ports, connections, speeds

        **Your object_types**: devices, sites, racks, cables, interfaces,
        manufacturers, device-types, device-roles, platforms, power-outlets,
        power-ports, power-feeds, power-panels, modules, locations,
        console-ports, console-server-ports, front-ports, inventory-items

        **Examples**:
        - List devices: netbox_get_objects("devices", {"site": "DM-Akron"})
        - Get device: netbox_get_object_by_id("devices", 123)
        - Find racks: netbox_get_objects("racks", {"location": "Building-A"})
        - List sites: netbox_get_objects("sites", {})"""
    )

    ipam_prompt = SUB_AGENT_PROMPT_TEMPLATE.format(
        domain="IPAM",
        expertise_areas="network addressing and allocation",
        detailed_expertise="""
        - IP address management: assignments, availability, conflicts
        - Prefix allocation: subnets, utilization, hierarchies
        - VLAN configuration: IDs, names, groups, assignments
        - VRF segmentation: routing domains, isolation
        - Address resolution: DNS, DHCP reservations
        - Network services: NAT pools, anycast addresses

        **Your object_types**: ip-addresses, prefixes, vlans, vlan-groups,
        vrfs, asns, asn-ranges, aggregates, ip-ranges, services, roles,
        route-targets, rirs, fhrp-groups

        **Examples**:
        - Find IPs: netbox_get_objects("ip-addresses", {"vrf": "prod"})
        - Get prefix: netbox_get_object_by_id("prefixes", 45)
        - List VLANs: netbox_get_objects("vlans", {"site": "DM-Akron"})
        - Get VRF: netbox_get_objects("vrfs", {"name": "management"})"""
    )

    tenancy_prompt = SUB_AGENT_PROMPT_TEMPLATE.format(
        domain="Tenancy",
        expertise_areas="organizational structure and ownership",
        detailed_expertise="""
        - Tenant management: organizations, departments, customers
        - Resource ownership: device assignments, IP allocations
        - Contact information: technical, administrative, billing
        - Organizational hierarchy: parent-child relationships
        - Resource quotas: limits, allocations, usage
        - Multi-tenancy boundaries: isolation, sharing

        **Your object_types**: tenants, tenant-groups, contacts,
        contact-groups, contact-roles

        **Examples**:
        - List tenants: netbox_get_objects("tenants", {})
        - Get tenant: netbox_get_object_by_id("tenants", 7)
        - Find contacts: netbox_get_objects("contacts", {"role": "admin"})"""
    )

    virtualization_prompt = SUB_AGENT_PROMPT_TEMPLATE.format(
        domain="Virtualization",
        expertise_areas="virtual infrastructure management",
        detailed_expertise="""
        - Virtual machines: instances, configurations, states
        - Cluster management: hosts, resources, availability
        - Virtual interfaces: vNICs, configurations, attachments
        - VM-to-host mapping: placement, migration, affinity
        - Resource allocation: CPU, memory, storage
        - Virtual networking: vSwitches, port groups, overlays

        **Your object_types**: virtual-machines, clusters, cluster-groups,
        cluster-types, vm-interfaces

        **Examples**:
        - List VMs: netbox_get_objects("virtual-machines", {"cluster": "prod-cluster"})
        - Get VM: netbox_get_object_by_id("virtual-machines", 89)
        - Find clusters: netbox_get_objects("clusters", {"site": "DM-Akron"})"""
    )

    system_prompt = SUB_AGENT_PROMPT_TEMPLATE.format(
        domain="System",
        expertise_areas="system monitoring and metadata",
        detailed_expertise="""
        - Change audit logs
        - System status and diagnostics
        - Historical tracking

        **Your tools**:
        - netbox_get_changelogs: Get change audit logs with filters
        - netbox_get_objects: Access any NetBox object type

        **Examples**:
        - Recent changes: netbox_get_changelogs({"time_after": "2025-09-30T00:00:00Z"})
        - Deletions: netbox_get_changelogs({"action": "delete"})"""
    )

    return [
        {
            "name": "dcim-specialist",
            "description": "Physical infrastructure specialist. Handles devices, racks, sites, cables, and power. Returns structured DCIM data.",
            "prompt": dcim_prompt,
            "tools": simple_tools
        },
        {
            "name": "ipam-specialist",
            "description": "Network addressing specialist. Handles IPs, prefixes, VLANs, and VRFs. Returns structured IPAM data.",
            "prompt": ipam_prompt,
            "tools": simple_tools
        },
        {
            "name": "tenancy-specialist",
            "description": "Organizational structure specialist. Handles tenants, ownership, and contacts. Returns structured tenancy data.",
            "prompt": tenancy_prompt,
            "tools": simple_tools
        },
        {
            "name": "virtualization-specialist",
            "description": "Virtual infrastructure specialist. Handles VMs, clusters, and virtual interfaces. Returns structured virtualization data.",
            "prompt": virtualization_prompt,
            "tools": simple_tools
        },
        {
            "name": "system-specialist",
            "description": "System monitoring and metadata specialist. Handles changelogs and system queries.",
            "prompt": system_prompt,
            "tools": simple_tools
        }
    ]

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
    print(f"🚀 Creating NetBox agent with simple MCP (3 tools)...")

    # Three simple MCP tools
    tool_list = [
        netbox_get_objects,
        netbox_get_object_by_id,
        netbox_get_changelogs,
        # Strategic/discovery tools
        list_available_tools,
        get_tool_details,
        show_cache_metrics,
        think,
        store_query
    ]

    # Update think tool description
    think.__doc__ = THINK_TOOL_DESCRIPTION

    # Create sub-agents with simple MCP tools
    netbox_subagents = create_netbox_subagents()

    # Combined instructions for simple MCP
    full_instructions = NETBOX_SUPERVISOR_INSTRUCTIONS + "\n\n" + SIMPLE_MCP_INSTRUCTIONS

    print(f"📊 Simple MCP Configuration:")
    print(f"  - Total Tools: {len(tool_list)}")
    print(f"  - NetBox MCP Tools: 3 (netbox_get_objects, netbox_get_object_by_id, netbox_get_changelogs)")
    print(f"  - Strategic Tools: 5 (list_available_tools, get_tool_details, show_cache_metrics, think, store_query)")
    print(f"  - Sub-agents: {len(netbox_subagents)} domain specialists")
    print(f"  - Instructions Size: ~{len(full_instructions)//4} tokens")
    print(f"  - Caching Enabled: {enable_caching}")
    print(f"  - Cache TTL: {cache_ttl}")

    # Use cached model if caching is enabled
    if enable_caching:
        model = get_cached_model(
            enable_caching=True,
            cache_ttl=cache_ttl
        )
    else:
        model = ChatAnthropic(
            model_name="claude-sonnet-4-20250514",
            max_tokens=64000
        )

    # Create agent with simple MCP tools
    agent = async_create_deep_agent(
        tool_list,
        full_instructions,
        model=model,
        subagents=netbox_subagents
    ).with_config({"recursion_limit": 1000})

    # Store caching config
    agent._cache_config = {
        "enabled": enable_caching,
        "ttl": cache_ttl,
        "mcp_mode": "simple"
    }

    print(f"✅ Agent created successfully with simple MCP")

    return agent

# Add new command to show cache metrics
@tool
async def show_cache_metrics() -> Dict[str, Any]:
    """Display detailed cache performance metrics"""
    return cache_monitor.get_metrics()

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

# Optional: Store query in virtual file system for reference
@tool
async def store_query(
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Store the user query in virtual filesystem for reference throughout execution."""
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

# Create the global agent instance (will be initialized in main or when imported)

def extract_agent_response(result):
    """Extract the final agent response in a clean format"""
    try:
        messages = result.get('messages', [])
        for msg in reversed(messages):
            if hasattr(msg, 'content') and hasattr(msg, 'type') and msg.type == 'ai':
                return msg.content, len(messages)
        return "No response found", len(messages)
    except Exception as e:
        return f"Error extracting response: {e}", 0

async def process_netbox_query(query: str, track_metrics: bool = True):
    """Process a NetBox query with cache tracking"""
    print(f"\n🔄 Processing: {query}")

    try:
        start_time = time.time()

        result = await netbox_agent.ainvoke({
            "messages": [{"role": "user", "content": query}]
        }, config={'recursion_limit': 20})

        elapsed = time.time() - start_time
        response, msg_count = extract_agent_response(result)

        # Extract and log cache metrics from the result
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
    print("🚀 NetBox Interactive Agent CLI (Simple MCP)")
    print("Agent has access to 3 generic MCP tools:")
    print("  • netbox_get_objects - List/search any NetBox object type")
    print("  • netbox_get_object_by_id - Get detailed object information")
    print("  • netbox_get_changelogs - Query change audit logs")
    print("\nSupports ALL NetBox object types via object_type parameter")
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

# Global agent instance
netbox_agent = None

if __name__ == "__main__":
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

    asyncio.run(main())