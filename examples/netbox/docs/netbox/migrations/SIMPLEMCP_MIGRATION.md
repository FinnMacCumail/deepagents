# Simple MCP Server Migration Plan

**Branch**: `simplemcp`
**Base**: Commit 0433a26 (cross-domain implementation baseline)
**Target**: Adapt for simple MCP server (3 tools instead of 62)

## Simple MCP Server Overview

Located at: `/home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server`

### Three Generic Tools

1. **netbox_get_objects(object_type, filters)**
   - List/search any NetBox object type
   - Filters map directly to NetBox API parameters
   - Returns array of objects

2. **netbox_get_object_by_id(object_type, object_id)**
   - Get detailed information about specific object
   - Returns single object with full details

3. **netbox_get_changelogs(filters)**
   - Audit trail / change history
   - Filters for user, time range, action type, etc.

### Object Types (Parameter to tools)

- **DCIM**: devices, sites, racks, cables, interfaces, manufacturers, device-types, power-outlets, etc.
- **IPAM**: ip-addresses, prefixes, vlans, vrfs, asns, aggregates
- **Tenancy**: tenants, tenant-groups, contacts, contact-groups
- **Virtualization**: virtual-machines, clusters, vm-interfaces
- **Circuits**: circuits, providers, circuit-types
- **Wireless**: wireless-lans, wireless-links
- **VPN**: tunnels, l2vpns, ipsec-policies

## Migration Strategy

### Phase 1: Update Imports & Dependencies

**Remove:**
```python
from netbox_mcp import NetBoxClient, load_config
from netbox_mcp.tools import load_all_tools
from netbox_mcp.registry import TOOL_REGISTRY, get_tool_by_name
```

**Add:**
```python
# Simple MCP client using langchain-mcp adapter
from langchain_mcp import MCPClient
# OR direct HTTP connection to simple MCP server
```

### Phase 2: Replace Tool Generation

**Remove entire section:**
- `build_annotations_from_metadata()`
- `create_async_tool_wrapper()`
- `generate_all_tool_wrappers()`
- `organize_tools_by_category()`
- Tool registry operations

**Replace with:**
```python
# Three simple tools wrapping MCP server
@tool
async def netbox_get_objects(object_type: str, filters: dict) -> dict:
    \"\"\"Get NetBox objects with optional filtering.

    Args:
        object_type: NetBox object type (e.g. "devices", "sites", "ip-addresses")
        filters: API filters (e.g. {"site": "DM-Akron", "status": "active"})

    Returns:
        List of matching objects
    \"\"\"
    # Call simple MCP server
    return await mcp_client.call_tool("netbox_get_objects", {
        "object_type": object_type,
        "filters": filters
    })

@tool
async def netbox_get_object_by_id(object_type: str, object_id: int) -> dict:
    \"\"\"Get detailed NetBox object by ID.

    Args:
        object_type: NetBox object type (e.g. "devices", "sites")
        object_id: Numeric ID of the object

    Returns:
        Complete object details
    \"\"\"
    return await mcp_client.call_tool("netbox_get_object_by_id", {
        "object_type": object_type,
        "object_id": object_id
    })

@tool
async def netbox_get_changelogs(filters: dict) -> dict:
    \"\"\"Get NetBox change audit logs.

    Args:
        filters: Filter criteria (user_id, action, time_before, time_after, etc.)

    Returns:
        List of changelog entries
    \"\"\"
    return await mcp_client.call_tool("netbox_get_changelogs", {
        "filters": filters
    })
```

### Phase 3: Simplify Agent Instructions

**Replace `build_enhanced_instructions()`** with simpler version:

```python
SIMPLE_MCP_INSTRUCTIONS = \"\"\"You are a NetBox infrastructure query agent.

## Available Tools (3 generic tools)

You have 3 powerful tools that can access ALL NetBox data:

1. **netbox_get_objects(object_type, filters)**
   - List/search any NetBox object type
   - Use filters to narrow results

2. **netbox_get_object_by_id(object_type, object_id)**
   - Get complete details for a specific object

3. **netbox_get_changelogs(filters)**
   - Query audit trail / change history

## NetBox Object Types by Domain

**DCIM** (Physical Infrastructure):
- devices, sites, racks, cables, interfaces, console-ports
- manufacturers, device-types, device-roles, platforms
- power-outlets, power-ports, power-feeds, power-panels
- modules, module-bays, module-types, locations, regions

**IPAM** (IP Address Management):
- ip-addresses, prefixes, vlans, vlan-groups, vrfs
- asns, asn-ranges, aggregates, ip-ranges, services

**Tenancy** (Organizational):
- tenants, tenant-groups, contacts, contact-groups, contact-roles

**Virtualization**:
- virtual-machines, clusters, cluster-groups, cluster-types
- vm-interfaces (use "virtualization/interfaces" endpoint)

**Circuits**:
- circuits, circuit-types, providers, provider-networks

**VPN**:
- tunnels, l2vpns, ipsec-policies, ike-policies

**Wireless**:
- wireless-lans, wireless-links

## Filter Examples

Filters map directly to NetBox API filtering:
- List devices in site: `{"site": "DM-Akron"}`
- Active devices only: `{"status": "active"}`
- Search by name: `{"name__ic": "switch"}` (case-insensitive contains)
- Multiple filters: `{"site": "HQ", "role": "server", "status": "active"}`

## Query Strategy

**SIMPLE QUERIES**:
- Use netbox_get_objects with appropriate filters
- Example: "List all sites" → netbox_get_objects("sites", {})

**CROSS-DOMAIN QUERIES**:
- Use strategic coordination (think(), task delegation)
- Call multiple specialists in parallel
- Each specialist uses the same 3 tools

Remember: All NetBox objects are accessible through object_type parameter.
\"\"\"
```

### Phase 4: Update Sub-Agent Tool Distribution

All sub-agents get the **same 3 tools**, but with domain-specific guidance in prompts:

```python
def create_netbox_subagents():
    \"\"\"Create domain-specific sub-agents for simple MCP\"\"\"

    # All specialists use same 3 tools
    simple_tools = [
        "netbox_get_objects",
        "netbox_get_object_by_id",
        "netbox_get_changelogs"
    ]

    dcim_prompt = SUB_AGENT_PROMPT_TEMPLATE.format(
        domain="DCIM",
        expertise_areas="physical infrastructure",
        detailed_expertise=\"\"\"
        - Device inventory: servers, switches, routers, PDUs
        - Rack management: layouts, elevations, utilization
        - Site topology: locations, regions, hierarchies
        - Cable management: connections, paths, types
        - Power distribution: outlets, feeds, consumption
        - Physical interfaces: ports, connections, speeds

        **Your object_types**: devices, sites, racks, cables, interfaces,
        manufacturers, device-types, device-roles, platforms, power-outlets,
        power-ports, power-feeds, power-panels, modules, locations

        **Examples**:
        - List devices: netbox_get_objects("devices", {"site": "DM-Akron"})
        - Get device: netbox_get_object_by_id("devices", 123)
        - Find racks: netbox_get_objects("racks", {"location": "Building-A"})
        \"\"\"
    )

    ipam_prompt = SUB_AGENT_PROMPT_TEMPLATE.format(
        domain="IPAM",
        expertise_areas="network addressing",
        detailed_expertise=\"\"\"
        - IP address management: assignments, availability
        - Prefix allocation: subnets, utilization
        - VLAN configuration: IDs, names, groups
        - VRF segmentation: routing domains

        **Your object_types**: ip-addresses, prefixes, vlans, vlan-groups,
        vrfs, asns, aggregates, ip-ranges, services

        **Examples**:
        - Find IPs: netbox_get_objects("ip-addresses", {"vrf": "prod"})
        - Get prefix: netbox_get_object_by_id("prefixes", 45)
        - List VLANs: netbox_get_objects("vlans", {"site": "DM-Akron"})
        \"\"\"
    )

    # Similar for other specialists...

    return [
        {
            "name": "dcim-specialist",
            "description": "Physical infrastructure specialist",
            "prompt": dcim_prompt,
            "tools": simple_tools  # Same 3 tools for all
        },
        {
            "name": "ipam-specialist",
            "description": "Network addressing specialist",
            "prompt": ipam_prompt,
            "tools": simple_tools
        },
        # ... tenancy, virtualization, system specialists
    ]
```

### Phase 5: Update Main Agent Creation

```python
def create_netbox_agent_with_simple_mcp(
    enable_caching: bool = True,
    cache_ttl: str = "1h"
):
    \"\"\"Create NetBox agent using simple MCP server (3 tools)\"\"\"

    # Initialize MCP client connection
    mcp_client = MCPClient(
        server_path="/home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server/server.py"
    )

    # Three simple tools
    tool_list = [
        netbox_get_objects,
        netbox_get_object_by_id,
        netbox_get_changelogs,
        # Strategic tools
        think,
        write_todos,
        list_available_tools  # Lists the 3 tools + strategic ones
    ]

    # Sub-agents with domain-specific prompts
    netbox_subagents = create_netbox_subagents()

    # Combined instructions
    full_instructions = NETBOX_SUPERVISOR_INSTRUCTIONS + "\\n\\n" + SIMPLE_MCP_INSTRUCTIONS

    # Create agent (with or without caching)
    if enable_caching:
        model = get_cached_model(enable_caching=True, cache_ttl=cache_ttl)
    else:
        model = ChatAnthropic(model_name="claude-sonnet-4-20250514", max_tokens=64000)

    agent = async_create_deep_agent(
        tool_list,
        full_instructions,
        model=model,
        subagents=netbox_subagents
    ).with_config({"recursion_limit": 1000})

    return agent
```

## Benefits of Simple MCP Approach

1. **Dramatically Fewer Tools**: 3 vs 62 (95% reduction)
2. **Smaller System Messages**: ~3k tokens vs ~17k tokens
3. **No Caching Issues**: Sub-agents have tiny tool sets
4. **Clearer Mental Model**: object_type + filters pattern
5. **Easier Maintenance**: One pattern for all objects
6. **Same Cross-Domain Power**: Strategic coordination preserved

## Migration Checklist

- [ ] Set up MCP client connection to simple server
- [ ] Replace 62-tool generation with 3-tool definitions
- [ ] Update sub-agent tool lists (all get same 3 tools)
- [ ] Revise prompts with object_type guidance
- [ ] Update main agent creation function
- [ ] Test basic queries (sites, devices)
- [ ] Test cross-domain queries (devices + IPs)
- [ ] Verify strategic delegation works
- [ ] Confirm no caching/timeout issues

## Testing Strategy

### Simple Queries
- "List all sites"
- "Show me device test-device-01"
- "Find all active devices"

### Cross-Domain Queries
- "Show devices with their IP addresses for site DM-Akron"
- "Get virtual machines and their physical hosts"
- "Tenant infrastructure report for Research Lab"

### Expected Behavior
- think() tool called for analysis
- Appropriate sub-agents delegated to
- Sub-agents use object_type pattern correctly
- Results synthesized properly
- No API 500 or timeout errors