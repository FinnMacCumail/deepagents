# PRP: Cross-Domain NetBox Agent Implementation

## Executive Summary
Extend the existing NetBox agent (`examples/netbox/netbox_agent.py`) to handle cross-domain queries while maintaining current simple and intermediate query handling capabilities. The implementation will leverage the deepagents framework's planning architecture with **planning tools**, **sub-agents**, **virtual file system access**, and **enhanced prompting**.

## Context & Requirements

### Current Architecture
- **NetBox Agent**: Handles 62+ dynamically generated NetBox MCP tools
- **Query Types Currently Supported**:
  - Simple queries (single tool, direct response)
  - Intermediate queries (2-3 tools, basic correlation)
- **Caching Strategy**: System prompts and tool definitions are cached for performance

### New Requirements
- Handle cross-domain queries spanning 2-4 NetBox domains (DCIM, IPAM, Tenancy, Virtualization)
- Maintain existing simple/intermediate query performance
- Implement supervisor pattern with strategic thinking
- Delegate domain-specific tasks to sub-agents with context isolation
- Use planning tools for complex multi-step operations

## Implementation Blueprint

### 1. Create Centralized Prompts Module

```python
# NEW FILE: examples/netbox/prompts.py
"""Centralized prompts for NetBox cross-domain agent"""

THINK_TOOL_DESCRIPTION = """Strategic reflection tool for analyzing current progress and planning next steps.

Use this tool to:
- Assess what information you've gathered
- Identify gaps in your understanding
- Plan your next actions strategically
- Decide when you have enough information to answer

This is CRITICAL for cross-domain queries to maintain strategic oversight."""

NETBOX_SUPERVISOR_INSTRUCTIONS = """You are a NetBox infrastructure query agent with strategic coordination capabilities.

## Query Classification Framework

<Task>
Analyze each query to understand its scope and complexity. Classify queries based on the domains they span and the coordination required.
</Task>

<Query Types>
**SIMPLE QUERIES**:
- Single domain, direct lookup
- No correlation needed between entities
- Example: "Show all sites" → Direct tool use

**INTERMEDIATE QUERIES**:
- Single or adjacent domains with basic correlation
- Related entities that can be queried sequentially
- Example: "Devices in site X with their IPs" → Sequential tool calls

**CROSS-DOMAIN QUERIES**:
- Spans multiple NetBox domains requiring coordination
- Needs synthesis across organizational boundaries
- Requires understanding relationships across infrastructure layers
- Examples:
  - "Show tenant infrastructure across all sites" (Tenancy + DCIM + IPAM)
  - "Network configuration for VM including physical host" (Virtualization + DCIM + IPAM)
  - "Site utilization with tenant breakdown" (DCIM + Tenancy + IPAM)
</Query Types>

## Strategic Execution Pattern

<For Cross-Domain Queries>
1. **STRATEGIC ASSESSMENT**: Use think() to analyze the query scope
   - What domains are involved?
   - What information needs correlation?
   - Can domains be queried in parallel?

2. **PLANNING**: Create structured plan with write_todos()
   - Break down by domain
   - Identify dependencies
   - Mark parallelizable tasks

3. **PARALLEL DELEGATION**: When domains can be queried independently
   Make multiple task() calls in a single response:
   ```
   task(description="Get tenant details and resources", subagent_type="tenancy-specialist")
   task(description="List all physical devices", subagent_type="dcim-specialist")
   task(description="Get IP allocations", subagent_type="ipam-specialist")
   ```

4. **REFLECTION**: After each sub-agent response, use think() with a reflection string that:
   - Summarizes what was gathered
   - Identifies what the original query needs
   - Assesses completeness of information
   - Decides next steps: More delegation OR synthesize results

5. **SYNTHESIS**: Combine cross-domain results into cohesive response
</For Cross-Domain Queries>

## Critical Instructions

**IMPORTANT**: Sub-agents have isolated context. Each task() call must include:
- Complete, standalone instructions
- All necessary context for the task
- Clear specification of what data to return

**PARALLEL EXECUTION**: Identify independent information needs and delegate simultaneously:
- Maximum 3-4 concurrent sub-agents to maintain coordination
- Each sub-agent handles one domain exclusively

**STRATEGIC THINKING**: Use think() tool with comprehensive reflection strings that:
- Include the original query context in your reflection
- Summarize what you've learned so far
- Assess whether you have enough to answer the query
- Identify gaps and decide on next steps
- Not for mechanical tracking, but for strategic decision-making

## Domain Expertise Map
- **DCIM**: Physical infrastructure (devices, racks, sites, cables, power)
- **IPAM**: Network addressing (IPs, prefixes, VLANs, VRFs)
- **Tenancy**: Organizational structure (tenants, groups, ownership)
- **Virtualization**: Virtual infrastructure (VMs, clusters, interfaces)

Remember: Prioritize efficiency for simple queries while leveraging parallel delegation for complex cross-domain analysis."""

SUB_AGENT_PROMPT_TEMPLATE = """You are a {domain} specialist with deep expertise in {expertise_areas}.

<Task>
Execute the specific {domain} operations requested. Focus exclusively on your domain.
Return structured, complete data that can be correlated with other domain results.
</Task>

<Your Expertise>
{detailed_expertise}
</Your Expertise>

<Instructions>
1. Use only the tools provided for your domain
2. Gather comprehensive data within your scope
3. Return results in a structured format
4. Include relevant IDs and references for cross-domain correlation
5. Do not attempt to access information outside your domain
</Instructions>

Remember: You are providing data that will be synthesized with other domain results. Be thorough and precise."""
```

### 2. Enhance Main Agent with Strategic Tools

```python
# Location: examples/netbox/netbox_agent.py

from typing import Optional, List, Dict, Any
from langchain_core.tools import tool

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

# Import necessary modules for optional query storage
from typing import Annotated
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId
from deepagents.state import DeepAgentState

# Import prompts from centralized module
from examples.netbox.prompts import (
    NETBOX_SUPERVISOR_INSTRUCTIONS,
    SUB_AGENT_PROMPT_TEMPLATE,
    THINK_TOOL_DESCRIPTION
)

# Update think tool with proper description
think.__doc__ = THINK_TOOL_DESCRIPTION

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

### 3. Define Precise Domain-Specific Sub-Agents

```python
# Location: examples/netbox/netbox_agent.py (add to existing file)

# Define specialized sub-agents with precise prompts
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

                # Rack management (4 tools)
                "netbox_list_all_racks", "netbox_get_rack_inventory", "netbox_get_rack_elevation",
                "netbox_get_site_info",

                # Site management (2 tools)
                "netbox_list_all_sites", "netbox_get_site_info",

                # Cable management (3 tools)
                "netbox_list_all_cables", "netbox_get_cable_info", "netbox_list_all_power_cables",

                # Power management (10 tools)
                "netbox_list_all_power_outlets", "netbox_get_power_outlet_info",
                "netbox_list_all_power_ports", "netbox_get_power_port_info",
                "netbox_list_all_power_feeds", "netbox_get_power_feed_info",
                "netbox_list_all_power_panels", "netbox_get_power_panel_info",
                "netbox_get_power_connection_info",

                # Module management (7 tools)
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
                # Virtual machine management (3 tools)
                "netbox_list_all_virtual_machines", "netbox_get_virtual_machine_info",
                "netbox_get_vm_interface_info",

                # Cluster management (6 tools)
                "netbox_list_all_clusters", "netbox_get_cluster_info",
                "netbox_list_all_cluster_groups", "netbox_get_cluster_group_info",
                "netbox_list_all_cluster_types", "netbox_get_cluster_type_info",

                # Virtual disk management (2 tools)
                "netbox_list_all_virtual_disks", "netbox_get_virtual_disk_info",

                # Platform management (1 tool)
                "netbox_list_all_platforms"
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

# Use the function to create subagents
NETBOX_SUBAGENTS = create_netbox_subagents()
```

### 4. Integrate Sub-Agents with Enhanced Main Agent

```python
# Location: examples/netbox/netbox_agent.py (modify create_netbox_agent_with_all_tools)

def create_netbox_agent_with_all_tools(
    enable_caching: bool = True,
    cache_ttl: str = "1h",
    cache_conversation: bool = True,
    conversation_cache_threshold: int = 3
):
    """Create NetBox agent with cross-domain support and strategic coordination"""

    # [EXISTING CODE for tool generation...]

    # Create sub-agents with precise domain expertise
    netbox_subagents = create_netbox_subagents()

    # Prepare enhanced instructions combining existing with new strategic patterns
    full_instructions = build_enhanced_instructions(categorized_tools) + "\n\n" + NETBOX_SUPERVISOR_INSTRUCTIONS

    # Add strategic tools to available tools
    tool_list = list(all_tools.values())
    tool_list.extend([list_available_tools, get_tool_details, show_cache_metrics, think])

    # Create agent with strategic capabilities
    # Note: We do NOT restrict main_agent_tools to allow fallback for simple queries
    # Sub-agents still get filtered tool sets for their domains
    agent = async_create_deep_agent(
        tool_list,
        full_instructions,
        model=model,
        subagents=netbox_subagents,  # Domain specialists with precise prompts
        # main_agent_tools parameter omitted - main agent has access to all tools
        # This allows: 1) Direct tool use for simple queries
        #              2) Fallback if sub-agent delegation fails
        #              3) Tools not in sub-agents (discovery tools) remain accessible
    ).with_config({"recursion_limit": 1000})

    return agent
```

### 5. Parallel Execution Patterns for Cross-Domain Queries

```python
# Location: examples/netbox/netbox_agent.py (example patterns to include in documentation)

"""
PARALLEL EXECUTION PATTERNS

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
    reflection="""Retrieved VM details for web-app-02, including cluster and interfaces.
    Now need to trace to physical infrastructure.

    Next parallel queries:
    - Get physical host and rack location from DCIM for the cluster
    - Get IP and VLAN configuration from IPAM for the VM interfaces"""
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
    reflection="""Completed parallel data collection from all 4 domains for site Butler Communications.

    Have gathered:
    - Device inventory and power usage (DCIM)
    - IP utilization and VLAN usage (IPAM)
    - Tenant resource allocation (Tenancy)
    - Virtual machine inventory (Virtualization)

    Next steps: Correlate devices with VMs, map tenants to resources, calculate totals."""
)
"""
```

### 6. Example Cross-Domain Query Flow with Strategic Thinking

```python
# Example: "Show tenant 'Research Lab' infrastructure footprint across all sites"

# 1. Strategic Assessment
await think(
    reflection="""Analyzing query: 'Show tenant Research Lab infrastructure footprint across all sites'
    This spans Tenancy + DCIM + IPAM domains and requires site correlation.

    Information gaps:
    - Need tenant details from tenancy domain
    - Need device inventory from DCIM domain
    - Need network allocations from IPAM domain
    - Need to correlate by site

    Next steps: Execute parallel domain queries, then synthesize results."""
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
    reflection="""Received comprehensive data from 3 parallel domain queries.

    Current state:
    - Have tenant overview and resource reports from tenancy-specialist
    - Have complete device inventory with site/rack details from dcim-specialist
    - Have IP/prefix/VLAN allocations from ipam-specialist

    Gap identified: Need to correlate all resources by site for infrastructure footprint view.

    Final steps: Group resources by site, calculate per-site metrics, format comprehensive report."""
)

# 5. Synthesis and Response
# Agent combines results into cohesive infrastructure footprint report
```

## File References & Patterns

### Core Files to Create/Modify

1. **NEW: `examples/netbox/prompts.py`**
   - Centralized prompt templates
   - Strategic instruction patterns
   - Sub-agent prompt formatting

2. **MODIFY: `examples/netbox/netbox_agent.py`**
   - Lines 467-547: Update agent creation function
   - Add think tool implementation (new)
   - Add create_netbox_subagents function (new)
   - Import prompts module (new)
   - Integrate strategic coordination

### Patterns to Follow
- `src/deepagents/sub_agent.py:38-83` - Sub-agent creation pattern
- `src/deepagents/graph.py:91-96` - Main agent tool filtering
- `examples/research/research_agent.py:36-41` - Sub-agent definition pattern
- `src/deep_agents_from_scratch/prompts.py` - Precise prompting patterns

### External References
- Strategic patterns: https://github.com/langchain-ai/deep-agents-from-scratch/blob/main/src/deep_agents_from_scratch/prompts.py
- Deep agents overview: https://docs.langchain.com/labs/deep-agents/overview
- LangGraph commands: https://blog.langchain.com/deep-agents/

## Implementation Tasks

1. ✅ Create `prompts.py` with strategic prompt templates
2. ✅ Add think tool following deep-agents-from-scratch pattern (simple reflection)
3. ✅ Implement create_netbox_subagents() function with ALL 62 tools
4. ✅ Update agent creation WITHOUT main_agent_tools restriction
5. ✅ Add 5th sub-agent (system-specialist) for complete coverage
6. ✅ Add parallel execution documentation
7. ✅ Add optional query storage pattern
8. ✅ Verify complete tool coverage (62/62 tools assigned)

## Enhanced Validation Strategy

### Query Classification Testing

```python
# Test script: examples/netbox/test_query_classification.py

test_queries = {
    "simple": [
        "Show all sites",
        "List devices",
        "Get rack information for R-201"
    ],
    "intermediate": [
        "Show devices in site DM-Akron with their IPs",
        "Get interfaces for device with assigned VLANs",
        "List racks in site with utilization"
    ],
    "cross_domain": [
        "Show tenant Research Lab infrastructure across all sites",
        "Network configuration for VM web-app-02 including physical host",
        "Complete infrastructure audit for site Butler Communications with tenant breakdown"
    ]
}

# Expected behavior:
# - Simple: Direct tool use, no sub-agents
# - Intermediate: Sequential tools, no sub-agents
# - Cross-domain: Think tool → Todos → Parallel sub-agents
```

### Strategic Reflection Testing

```bash
# Monitor think tool usage
python examples/netbox/netbox_agent.py --debug
# Query: "Analyze tenant infrastructure footprint"

# Expected pattern:
# 1. think() - Strategic assessment
# 2. write_todos() - Planning
# 3. Multiple task() calls - Parallel execution
# 4. think() - Post-execution reflection
# 5. Final synthesis
```

### Parallel Execution Verification

```python
# Test parallel sub-agent execution
import asyncio
from examples.netbox.netbox_agent import netbox_agent

async def test_parallel():
    query = "Show complete infrastructure for tenant DM Network across all sites"

    # Should trigger parallel execution of:
    # - tenancy-specialist
    # - dcim-specialist
    # - ipam-specialist

    result = await netbox_agent.ainvoke({
        "messages": [{"role": "user", "content": query}]
    })

    # Verify parallel execution in logs
    assert "tenancy-specialist" in execution_log
    assert "dcim-specialist" in execution_log
    assert "ipam-specialist" in execution_log
```

## Error Handling Strategy

1. **Query Classification Errors**: If unclear, default to intermediate handling
2. **Sub-Agent Failures**: Main agent retries with direct tool access
3. **Tool Errors**: Existing error handling in wrapper functions applies
4. **Planning Errors**: Think tool helps recover by re-analyzing

## Tool Coverage Summary

### Complete 62-Tool Distribution
- **DCIM Specialist**: 37 tools (devices, racks, sites, cables, power, modules)
- **IPAM Specialist**: 8 tools (IPs, prefixes, VLANs, VRFs)
- **Tenancy Specialist**: 3 tools (tenants, groups, reports)
- **Virtualization Specialist**: 12 tools (VMs, clusters, disks, platforms)
- **System Specialist**: 2 tools (health check, journal entries)
- **Main Agent Access**: ALL tools available for simple queries and fallback

### Key Design Decisions
1. **No main_agent_tools restriction**: Main agent can use any tool directly
2. **Complete coverage**: All 62 NetBox tools are assigned to appropriate specialists
3. **Overlap prevention**: Each tool assigned to exactly one sub-agent
4. **Fallback capability**: Main agent can directly use tools if sub-agent delegation fails

## Performance Considerations

- Sub-agents get focused tool subsets (2-37 tools per specialist)
- Main agent has full tool access for simple queries (avoids unnecessary delegation)
- Cache hit rates remain high due to unchanged base prompts
- Parallel sub-agent execution for independent domain tasks
- Virtual file system prevents real I/O overhead

## Success Metrics

- ✅ Simple queries: < 1 second, single tool call
- ✅ Intermediate queries: < 3 seconds, 2-3 tool calls
- ✅ Cross-domain queries: < 10 seconds, coordinated multi-agent execution
- ✅ Cache hit rate: > 80% after warmup
- ✅ Zero regression on existing query types

## Known Gotchas & Solutions

1. **Tool name conflicts**: Sub-agents use tool name strings, ensure exact matches with TOOL_REGISTRY
2. **Async coordination**: All NetBox tools are async, maintain async/await chain
3. **Context size**: Enhanced prompts increase tokens, but caching mitigates cost
4. **State isolation**: Sub-agents share virtual filesystem through LangGraph state

## Confidence Score: 9/10

**Rationale**:
- Strong foundation with existing NetBox agent (✓)
- Precise prompting patterns from deep-agents-from-scratch (✓)
- Comprehensive strategic coordination framework (✓)
- Clear parallel execution patterns (✓)
- Detailed validation strategy (✓)
- Minor challenge: Testing cross-domain coordination in practice (-1)

## Next Steps After Implementation

1. Create unit tests for query classification
2. Add integration tests for each cross-domain example
3. Profile performance with different query complexities
4. Consider adding domain correlation matrix for optimization
5. Document query patterns for end users