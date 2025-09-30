import os
import sys
import asyncio
import inspect
import json
import time
from typing import Optional, Dict, Any, List, Callable, Tuple, Annotated

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
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

# Add netbox-mcp to path if not already there
NETBOX_MCP_PATH = "/home/ola/dev/netboxdev/netbox-mcp"
if NETBOX_MCP_PATH not in sys.path:
    sys.path.insert(0, NETBOX_MCP_PATH)

from netbox_mcp import NetBoxClient, load_config
from netbox_mcp.tools import load_all_tools
from netbox_mcp.registry import TOOL_REGISTRY, get_tool_by_name

# Import prompts from centralized module
from prompts import (
    NETBOX_SUPERVISOR_INSTRUCTIONS,
    SUB_AGENT_PROMPT_TEMPLATE,
    THINK_TOOL_DESCRIPTION
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

# Initialize NetBox client and load tools
load_all_tools()  # Load all NetBox MCP tools

# Get NetBox client instance
netbox_client = None

def get_netbox_client():
    """Get or create NetBox client instance"""
    global netbox_client
    if netbox_client is None:
        config = load_config()
        netbox_client = NetBoxClient(config)
    return netbox_client

def build_annotations_from_metadata(parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build function annotations from parameter metadata."""
    annotations = {}
    type_mapping = {
        'str': str, 'int': int, 'bool': bool, 'float': float,
        'dict': dict, 'list': list, 'Dict[str, Any]': Dict[str, Any],
        'Optional[str]': Optional[str], 'Optional[int]': Optional[int],
        'Optional[bool]': Optional[bool], 'List[str]': List[str],
        'List[Dict[str, Any]]': List[Dict[str, Any]],
    }

    for param in parameters:
        param_name = param.get('name')
        if param_name == 'client':
            continue

        param_type = param.get('type', 'Any')
        param_required = param.get('required', True)

        if param_type in type_mapping:
            actual_type = type_mapping[param_type]
        elif 'Optional' in param_type:
            actual_type = Optional[Any]
        else:
            actual_type = Any

        if not param_required and not param_type.startswith('Optional'):
            actual_type = Optional[actual_type]

        annotations[param_name] = actual_type

    annotations['return'] = Dict[str, Any]
    return annotations

def create_async_tool_wrapper(tool_name: str, tool_metadata: Dict[str, Any]) -> Callable:
    """Create an async wrapper function for a NetBox MCP tool."""
    parameters = tool_metadata.get('parameters', [])
    description = tool_metadata.get('description', f"Execute {tool_name}")

    async def wrapper(**kwargs):
        try:
            client = get_netbox_client()
            tool_func = tool_metadata.get('function')
            if not tool_func:
                raise RuntimeError(f"Tool '{tool_name}' function not found in registry")

            filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'client'}
            result = tool_func(client=client, **filtered_kwargs)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "tool_name": tool_name
            }

    wrapper.__name__ = tool_name
    wrapper.__doc__ = description
    wrapper.__annotations__ = build_annotations_from_metadata(parameters)

    sig_params = []
    for param in parameters:
        if param['name'] == 'client':
            continue

        if param.get('required', True):
            sig_params.append(
                inspect.Parameter(
                    param['name'],
                    inspect.Parameter.KEYWORD_ONLY,
                    annotation=wrapper.__annotations__.get(param['name'], Any)
                )
            )
        else:
            sig_params.append(
                inspect.Parameter(
                    param['name'],
                    inspect.Parameter.KEYWORD_ONLY,
                    default=param.get('default'),
                    annotation=wrapper.__annotations__.get(param['name'], Any)
                )
            )

    wrapper.__signature__ = inspect.Signature(parameters=sig_params)
    return wrapper

def generate_all_tool_wrappers() -> Dict[str, Callable]:
    """Generate wrappers for all tools in TOOL_REGISTRY."""
    wrapped_tools = {}
    for tool_name, tool_metadata in TOOL_REGISTRY.items():
        try:
            wrapped_tools[tool_name] = create_async_tool_wrapper(tool_name, tool_metadata)
        except Exception as e:
            print(f"Warning: Failed to wrap tool {tool_name}: {e}")
            continue
    return wrapped_tools

def organize_tools_by_category(wrapped_tools: Dict[str, Callable]) -> Dict[str, List[tuple]]:
    """Organize tools by their categories for better discovery."""
    categorized = {
        'system': [], 'dcim': [], 'ipam': [],
        'tenancy': [], 'extras': [], 'virtualization': []
    }

    for tool_name, wrapper in wrapped_tools.items():
        category = TOOL_REGISTRY.get(tool_name, {}).get('category', 'general')
        if category in categorized:
            categorized[category].append((tool_name, wrapper))
        else:
            if 'general' not in categorized:
                categorized['general'] = []
            categorized['general'].append((tool_name, wrapper))

    return categorized

def build_enhanced_instructions(categorized_tools: Dict[str, List[tuple]]) -> str:
    """Build enhanced agent instructions with tool category information."""
    category_counts = {}
    for category, tools in categorized_tools.items():
        if tools:
            category_counts[category] = len(tools)

    tool_summary = []
    for category, count in category_counts.items():
        tool_summary.append(f"- **{category.upper()}**: {count} tools")

    instructions = f"""You are a NetBox infrastructure query agent optimized for SPEED and EFFICIENCY.

## 🎯 CRITICAL: Query Classification (DO THIS FIRST!)

Analyze the user query and classify it as either SIMPLE or COMPLEX:

**SIMPLE QUERIES (90% of cases):**
- Requests ONE specific piece of information
- Keywords: "show", "get", "list", "what", "check"
- Examples: "show all sites", "get device info", "list VLANs", "what manufacturers"

**COMPLEX QUERIES (10% of cases):**
- Explicitly requests MULTIPLE data types or comprehensive analysis
- Keywords: "comprehensive", "audit", "report", "topology", "complete", "all...with", "analysis"
- Examples: "comprehensive tenant report", "infrastructure audit", "topology with connections"

## ⚡ FOR SIMPLE QUERIES - STRICT MINIMALIST RULES

**MANDATORY: Use EXACTLY ONE tool call and STOP**

### Direct Tool Mapping (NO EXPLORATION):
```
Query Pattern → Tool to Use (ONLY)
─────────────────────────────────────
"device <name>" → netbox_get_device_basic_info
"all devices" or "list devices" → netbox_list_devices
"devices in site <X>" → netbox_list_devices (with site filter)

"site <name>" → netbox_get_site_info
"all sites" or "list sites" → netbox_list_all_sites

"rack <name>" → netbox_get_rack_info
"all racks" or "list racks" → netbox_list_racks
"racks in site <X>" → netbox_list_racks (with site filter)

"IP <address>" → netbox_get_ip_address_info
"prefix <prefix>" → netbox_get_prefix_info
"all IPs" or "list IPs" → netbox_list_ip_addresses

"VLAN <id/name>" → netbox_get_vlan_info
"all VLANs" or "list VLANs" → netbox_list_vlans

"interfaces for <device>" → netbox_get_device_interfaces
"cables for <device>" → netbox_get_device_cables
"power for <device>" → netbox_list_all_power_outlets

"manufacturers" → netbox_list_all_manufacturers
"device types" → netbox_list_all_device_types
"device roles" → netbox_list_all_device_roles
"tenants" → netbox_list_all_tenants

"health" or "status" → netbox_health_check
```

### SIMPLE QUERY EXECUTION RULES:
1. **ONE TOOL ONLY** - Call exactly one tool based on the mapping above
2. **NO ENRICHMENT** - Do not gather additional "helpful" information
3. **NO EXPLORATION** - Never use list_available_tools or get_tool_details
4. **FAIL FAST** - If tool returns AttributeError, try the _basic_info variant ONCE, then stop
5. **RETURN IMMEDIATELY** - After first successful tool call, return the data
6. **MINIMAL FORMATTING** - Return raw data or simple list, no elaborate formatting

### FORBIDDEN for Simple Queries:
❌ DO NOT call multiple list_* tools to "provide context"
❌ DO NOT call get_site_info after getting device info "for completeness"
❌ DO NOT use write_todos for single tool operations
❌ DO NOT add emojis or formatting unless data is unreadable
❌ DO NOT suggest follow-up queries

## 📊 FOR COMPLEX QUERIES - MULTI-TOOL APPROACH

**Indicators that query is COMPLEX:**
- Contains words: "comprehensive", "complete", "audit", "report", "analysis", "topology"
- Explicitly asks for multiple data types: "show devices AND their IPs AND power usage"
- Requests correlation: "find all duplicate IPs across VRFs with recommendations"

### COMPLEX QUERY EXECUTION:
1. **USE write_todos** - Plan the multi-step operation
2. **BATCH OPERATIONS** - Execute related tools in parallel when possible
3. **SYNTHESIZE RESULTS** - Combine data into requested format
4. **FORMAT OUTPUT** - Use structured formatting for complex reports

### Complex Query Examples with Plans:
- "Comprehensive tenant report for X":
  → Plan: get tenant info, list tenant devices, list tenant IPs, list tenant VLANs

- "Infrastructure audit for site Y":
  → Plan: get site info, list site racks, list site devices, get power utilization

- "Network topology for site Z":
  → Plan: list devices, get all interfaces, trace cable connections, map VLANs

## 🚫 UNIVERSAL FORBIDDEN ACTIONS

1. **NEVER** use tool discovery (list_available_tools, get_tool_details) for standard queries
2. **NEVER** retry the same tool or similar variants more than once
3. **NEVER** add unrequested data "to be helpful"
4. **NEVER** call more tools after answering the user's question

## 📋 Error Handling Strategy

For ANY tool error:
1. If AttributeError on get_X_info → Try get_X_basic_info ONCE
2. If still failing → Return error message with what was attempted
3. DO NOT explore alternative tools or approaches

## 🎯 Response Guidelines

**For SIMPLE queries:**
- Direct data output
- No formatting unless data is unstructured
- No emojis
- No follow-up suggestions

**For COMPLEX queries:**
- Structured report format
- Section headers for clarity
- Tables for comparative data
- Summary at end if requested

## Available Tool Categories ({len(TOOL_REGISTRY)} total tools)
{chr(10).join(tool_summary)}

Remember: SPEED is critical. Most queries need ONE tool call. When in doubt, use the minimalist approach."""

    return instructions

# Tool discovery functions
@tool
async def list_available_tools(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List available NetBox tools, optionally filtered by category."""
    tools = []
    for name, metadata in TOOL_REGISTRY.items():
        if category and metadata.get('category') != category:
            continue
        tools.append({
            'name': name,
            'category': metadata.get('category', 'unknown'),
            'description': metadata.get('description', 'No description available')
        })
    tools.sort(key=lambda x: (x['category'], x['name']))
    return tools

@tool
async def get_tool_details(tool_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific NetBox tool."""
    tool = get_tool_by_name(tool_name)
    if not tool:
        return {'error': f'Tool {tool_name} not found', 'available_tools': list(TOOL_REGISTRY.keys())[:10]}

    details = {
        'name': tool.get('name'),
        'category': tool.get('category'),
        'description': tool.get('description'),
        'parameters': []
    }

    for param in tool.get('parameters', []):
        if param.get('name') == 'client':
            continue

        param_info = {
            'name': param.get('name'),
            'type': param.get('type', 'Any'),
            'required': param.get('required', True),
            'description': f"{'Required' if param.get('required', True) else 'Optional'} parameter"
        }

        if 'default' in param:
            param_info['default'] = param['default']

        details['parameters'].append(param_info)

    return details

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
    """Create domain-specific sub-agents with precise instructions"""

    # Format sub-agent prompts from template
    dcim_prompt = SUB_AGENT_PROMPT_TEMPLATE.format(
        domain="DCIM",
        expertise_areas="physical infrastructure management",
        detailed_expertise="""
        - Device inventory: servers, switches, routers, PDUs
        - Rack management: layouts, elevations, utilization
        - Site topology: locations, regions, hierarchies
        - Cable management: connections, paths, types
        - Power distribution: outlets, feeds, consumption
        - Physical interfaces: ports, connections, speeds"""
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
        - Network services: NAT pools, anycast addresses"""
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
        - Multi-tenancy boundaries: isolation, sharing"""
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
        - Virtual networking: vSwitches, port groups, overlays"""
    )

    return [
        {
            "name": "dcim-specialist",
            "description": "Physical infrastructure specialist. Handles devices, racks, sites, cables, and power. Returns structured DCIM data.",
            "prompt": dcim_prompt,
            "tools": [
                # Device management (11 tools)
                "netbox_list_all_devices", "netbox_get_device_info", "netbox_get_device_basic_info",
                "netbox_get_device_interfaces", "netbox_get_device_cables", "netbox_list_device_inventory",
                "netbox_list_all_device_types", "netbox_get_device_type_info", "netbox_list_all_device_roles",
                "netbox_list_all_manufacturers", "netbox_list_inventory_item_templates_for_device_type",

                # Rack management (3 tools)
                "netbox_list_all_racks", "netbox_get_rack_inventory", "netbox_get_rack_elevation",

                # Site management (2 tools)
                "netbox_list_all_sites", "netbox_get_site_info",

                # Cable management (3 tools)
                "netbox_list_all_cables", "netbox_get_cable_info", "netbox_list_all_power_cables",

                # Power management (9 tools)
                "netbox_list_all_power_outlets", "netbox_get_power_outlet_info",
                "netbox_list_all_power_ports", "netbox_get_power_port_info",
                "netbox_list_all_power_feeds", "netbox_get_power_feed_info",
                "netbox_list_all_power_panels", "netbox_get_power_panel_info",
                "netbox_get_power_connection_info",

                # Module management (9 tools)
                "netbox_list_all_modules", "netbox_get_module_info", "netbox_get_module_bay_info",
                "netbox_list_device_modules", "netbox_list_device_module_bays",
                "netbox_list_all_module_types", "netbox_get_module_type_info",
                "netbox_list_all_module_type_profiles", "netbox_get_module_type_profile_info"
            ]  # Total: 37 DCIM tools
        },
        {
            "name": "ipam-specialist",
            "description": "Network addressing specialist. Handles IPs, prefixes, VLANs, and VRFs. Returns structured IPAM data.",
            "prompt": ipam_prompt,
            "tools": [
                # IP management (3 tools)
                "netbox_find_available_ip", "netbox_find_duplicate_ips", "netbox_get_ip_usage",

                # Prefix management (2 tools)
                "netbox_list_all_prefixes", "netbox_get_prefix_utilization",

                # VLAN management (2 tools)
                "netbox_list_all_vlans", "netbox_find_available_vlan_id",

                # VRF management (1 tool)
                "netbox_list_all_vrfs"
            ]  # Total: 8 IPAM tools
        },
        {
            "name": "tenancy-specialist",
            "description": "Organizational structure specialist. Handles tenants, ownership, and contacts. Returns structured tenancy data.",
            "prompt": tenancy_prompt,
            "tools": [
                "netbox_list_all_tenants",
                "netbox_list_all_tenant_groups",
                "netbox_get_tenant_resource_report"
            ]  # Total: 3 Tenancy tools
        },
        {
            "name": "virtualization-specialist",
            "description": "Virtual infrastructure specialist. Handles VMs, clusters, and virtual interfaces. Returns structured virtualization data.",
            "prompt": virtualization_prompt,
            "tools": [
                # Virtual machine management (4 tools)
                "netbox_list_all_virtual_machines", "netbox_get_virtual_machine_info",
                "netbox_get_vm_interface_info", "netbox_list_all_vm_interfaces",

                # Cluster management (6 tools)
                "netbox_list_all_clusters", "netbox_get_cluster_info",
                "netbox_list_all_cluster_groups", "netbox_get_cluster_group_info",
                "netbox_list_all_cluster_types", "netbox_get_cluster_type_info",

                # Virtual disk management (2 tools)
                "netbox_list_all_virtual_disks", "netbox_get_virtual_disk_info"
            ]  # Total: 12 Virtualization tools
        },
        {
            "name": "system-specialist",
            "description": "System monitoring and metadata specialist. Handles health checks and journal entries.",
            "prompt": SUB_AGENT_PROMPT_TEMPLATE.format(
                domain="System",
                expertise_areas="system monitoring and metadata",
                detailed_expertise="""
                - System health monitoring
                - Journal entries and audit logs
                - System status and diagnostics"""
            ),
            "tools": [
                "netbox_health_check",
                "netbox_list_all_journal_entries"
            ]  # Total: 2 System/Extras tools
        }
    ]

def create_netbox_agent_with_all_tools(
    enable_caching: bool = True,
    cache_ttl: str = "1h",  # Use 1-hour cache for long sessions
    cache_conversation: bool = True,
    conversation_cache_threshold: int = 3  # Cache after 3 turns
):
    """
    Create a NetBox agent with all dynamically generated tools and prompt caching.

    Args:
        enable_caching: Enable Claude API prompt caching
        cache_ttl: Cache duration ("default" for 5min or "1h" for 1 hour)
        cache_conversation: Whether to cache conversation history
        conversation_cache_threshold: Number of turns before caching conversation
    """
    if len(TOOL_REGISTRY) == 0:
        load_all_tools()

    print(f"🚀 Generating wrappers for {len(TOOL_REGISTRY)} NetBox tools...")
    all_tools = generate_all_tool_wrappers()
    print(f"✅ Successfully wrapped {len(all_tools)} tools")

    categorized_tools = organize_tools_by_category(all_tools)
    enhanced_instructions = build_enhanced_instructions(categorized_tools)

    # Prepare tool definitions for system message
    tool_definitions = []
    for tool_name, tool_func in all_tools.items():
        tool_metadata = TOOL_REGISTRY.get(tool_name, {})
        tool_definitions.append({
            "name": tool_name,
            "description": tool_metadata.get("description", ""),
            "parameters": tool_metadata.get("parameters", [])
        })

    # Create comprehensive system message that will be automatically cached
    tools_text = f"\n## Available Tools ({len(tool_definitions)} total)\n"
    tools_text += json.dumps(tool_definitions, indent=2)

    # Create sub-agents with precise domain expertise
    netbox_subagents = create_netbox_subagents()

    # Prepare enhanced instructions combining existing with new strategic patterns
    full_instructions = enhanced_instructions + "\n\n" + NETBOX_SUPERVISOR_INSTRUCTIONS + tools_text

    # Add strategic tools to available tools
    tool_list = list(all_tools.values())
    tool_list.extend([list_available_tools, get_tool_details, show_cache_metrics, think, store_query])

    # Update think tool with proper description
    think.__doc__ = THINK_TOOL_DESCRIPTION

    print(f"📊 Cache Configuration:")
    print(f"  - Caching Enabled: {enable_caching}")
    print(f"  - Cache TTL: {cache_ttl}")
    print(f"  - Instructions Size: ~{len(enhanced_instructions)//4} tokens")
    print(f"  - Tools Definition Size: ~{len(tools_text)//4} tokens")
    print(f"  - Total System Message: ~{len(full_instructions)//4} tokens")
    print(f"  - Will be cached: {'✅ YES' if enable_caching and len(full_instructions) > 4096 else '❌ NO'}")
    print(f"  - Sub-agents configured: {len(netbox_subagents)} domain specialists")

    # Use cached model if caching is enabled
    if enable_caching:
        model = get_cached_model(
            enable_caching=True,
            cache_ttl=cache_ttl
        )
    else:
        model = None  # Use default model

    # Create agent with strategic capabilities
    # Note: We do NOT restrict main_agent_tools to allow fallback for simple queries
    # Sub-agents still get filtered tool sets for their domains
    agent = async_create_deep_agent(
        tool_list,
        full_instructions,
        model=model,
        subagents=netbox_subagents  # Domain specialists with precise prompts
        # main_agent_tools parameter omitted - main agent has access to all tools
        # This allows: 1) Direct tool use for simple queries
        #              2) Fallback if sub-agent delegation fails
        #              3) Tools not in sub-agents (discovery tools) remain accessible
    ).with_config({"recursion_limit": 1000})

    # Store caching config on agent for reference
    agent._cache_config = {
        "enabled": enable_caching,
        "ttl": cache_ttl,
        "conversation_caching": cache_conversation,
        "conversation_threshold": conversation_cache_threshold
    }

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
    print("🚀 NetBox Interactive Agent CLI")
    print(f"Agent has access to all {len(TOOL_REGISTRY)} NetBox tools!")
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

    # Create agent with caching
    netbox_agent = create_netbox_agent_with_all_tools(
        enable_caching=enable_cache,
        cache_ttl=cache_duration,
        cache_conversation=True,
        conversation_cache_threshold=3
    )

    asyncio.run(main())