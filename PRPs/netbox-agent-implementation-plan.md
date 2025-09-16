# NetBox Infrastructure Agent - Implementation Plan (PRP)

Generated: 2025-09-15 17:55:15

## Goal
Create a single NetBox infrastructure agent that interprets natural language queries, decomposes them into appropriate MCP tool calls, plans multi-step retrievals, and recovers gracefully from errors - all following the research_agent.py pattern exactly.

## Why (Business Value)
- Enable sophisticated NetBox operations through agent intelligence rather than hardcoded logic
- Provide Claude Code-level NetBox operation capabilities through comprehensive context engineering
- Achieve production-ready infrastructure analysis through single agent with expanded instructions
- Eliminate need for framework modifications or complex sub-agent architectures

## What (Specific Requirements)
- **Architecture**: Single agent following examples/research/research_agent.py structure
- **Tool Access**: All 60+ read-only NetBox MCP tools (netbox_get_*, netbox_list_*)
- **Planning Integration**: Built-in write_todos tool for task decomposition
- **Domain Coverage**: DCIM, IPAM, Tenancy, Virtualization domains
- **Query Handling**: Simple → Intermediate → Complex natural language queries
- **Error Recovery**: Intelligent fallback strategies through reasoning, not hardcoded logic

## Success Criteria
- [ ] Agent structure matches research_agent.py exactly
- [ ] No framework modifications required
- [ ] Handles all documented NetBox query types
- [ ] Demonstrates intelligent tool selection based on context
- [ ] Uses planning tool for complex multi-step operations
- [ ] Recovers gracefully from tool failures
- [ ] Provides structured answers with summaries and examples

## All Needed Context

### Research Agent Pattern Reference
```python
# From examples/research/research_agent.py
agent = create_deep_agent(
    [internet_search],           # Domain tools
    research_instructions,       # Behavioral guidance
    subagents=[critique_sub_agent, research_sub_agent]  # Specialists
).with_config({"recursion_limit": 1000})
```

### NetBox MCP Tool Landscape
- **Get Tools**: netbox_get_device_info, netbox_get_site_info, netbox_get_rack_info, etc.
- **List Tools**: netbox_list_devices, netbox_list_sites, netbox_list_all_manufacturers, etc.
- **Parameters**: device_name, site, tenant, status, role, manufacturer_name, vid, limit
- **Pagination**: interface_limit, cable_limit for controlling result size
- **Filters**: Support for site, tenant, status, role-based filtering

### Known Constraints
- Read-only operations only (no write/mutate tools)
- Tools return structured dictionaries
- Pagination support for large result sets
- Filter parameters for reducing result scope
- Error handling for invalid parameters or empty results

## Implementation Blueprint

### Step 1: Create NetBox Tool Wrapper Functions
```python
# File: examples/netbox/netbox_agent.py

# NetBox MCP tool functions (simple wrappers, no hardcoded logic)
def netbox_get_device_info(device_name: str, site: str = None,
                          interface_limit: int = None, cable_limit: int = None,
                          include_interfaces: bool = True, include_cables: bool = True):
    """Get comprehensive device information from NetBox"""
    # Simple wrapper around MCP tool
    return netbox_mcp_client.get_device_info(
        device_name=device_name, site=site,
        interface_limit=interface_limit, cable_limit=cable_limit,
        include_interfaces=include_interfaces, include_cables=include_cables
    )

def netbox_list_devices(site: str = None, tenant: str = None,
                       status: str = None, role: str = None, limit: int = None):
    """List devices with optional filters"""
    return netbox_mcp_client.list_devices(
        site=site, tenant=tenant, status=status, role=role, limit=limit
    )

# ... Continue for all 60+ NetBox MCP tools
```

### Step 2: Create Comprehensive Agent Instructions
```python
# Comprehensive instructions (following research_instructions pattern)
netbox_instructions = """You are a read-only NetBox infrastructure analyst.

## Role and Goals
- Interpret natural-language queries about NetBox infrastructure
- Plan multi-step retrievals using the write_todos tool
- Choose appropriate netbox_get_* and netbox_list_* tools
- Apply filters to reduce result sets and improve performance
- Recover gracefully from errors through intelligent fallback strategies
- Present concise answers with counts, summaries, and examples

## Tool Selection Strategy

### Specific Object Queries
Use netbox_get_* tools when user names a single object:
- netbox_get_device_info for device lifecycle information
- netbox_get_site_info for site details
- netbox_get_rack_info for rack information
- Include appropriate parameters (site, interface_limit, cable_limit)

### Bulk Queries
Use netbox_list_* tools when user asks for sets:
- netbox_list_devices for "all devices in site X"
- netbox_list_all_manufacturers for manufacturer summaries
- Apply filters: site, tenant, status, role, manufacturer_name, vid, limit

### Multi-Step Relationships
For complex queries requiring aggregation:
1. Use write_todos to plan the retrieval strategy
2. Make sequential tool calls based on plan
3. Perform aggregation and cross-referencing in reasoning
4. Update todos to track progress

## Planning Tool Usage
Always start complex queries with write_todos:

1. **Parse intent** - identify object types, qualifiers, expected output format
2. **Select tools** - choose get vs list based on query specificity
3. **Execute calls** - make sequential MCP calls, document results in plan
4. **Process results** - compute counts, sort, filter in reasoning (not via tools)
5. **Compose answer** - summarize findings with key metrics and examples

## Fallback Strategy
When tool calls fail, apply controlled fallback policy:

1. **Check parameters** - ensure correct case/slug format, try slugified names
2. **Switch tool family** - get_tool fails → try list_tool with filters
3. **Relax filters gradually** - remove specific filters, keep essential ones
4. **Limit attempts** - perform max 3 fallback attempts per step
5. **Never loop indefinitely** - ask for clarification after repeated failures

## Answer Formatting
- Begin with one-sentence summary of findings
- Provide key statistics (counts per site/role, utilization percentages)
- Include bulleted examples (device names, roles, statuses, sites, VIDs, prefixes)
- End with follow-up question offers (refine query, expand details, etc.)

## Example Query Handling Patterns

### Simple Query: "List devices in Amsterdam-DC"
Plan: identify site slug → call netbox_list_devices(site="amsterdam-dc") → if empty, try alternatives → summarize count and list first 10 devices

### Intermediate Query: "What VLANs does switch-01 have?"
Plan: call netbox_get_device_info(device_name="switch-01", include_interfaces=True, include_cables=False) → extract VLAN IDs from interfaces in reasoning → summarize findings

### Complex Query: "Summarize manufacturers by device count"
Plan: call netbox_list_all_manufacturers(limit=100) → for each manufacturer, count devices → aggregate results → return top manufacturers with device counts

You have access to 60+ NetBox MCP tools across DCIM, IPAM, Tenancy, and Virtualization domains. Use your domain knowledge to select appropriate tools, plan complex retrievals, and provide comprehensive infrastructure analysis."""
```

### Step 3: Create Agent Following Research Pattern
```python
# Agent creation (identical to research_agent.py pattern)
netbox_agent = create_deep_agent(
    [
        # All NetBox MCP tools
        netbox_get_device_info, netbox_list_devices, netbox_get_site_info,
        netbox_list_sites, netbox_get_rack_info, netbox_list_racks,
        netbox_list_all_manufacturers, netbox_list_all_device_types,
        # ... continue for all 60+ tools
    ],
    netbox_instructions,  # Comprehensive domain guidance
    subagents=[]  # No sub-agents, single agent approach
).with_config({"recursion_limit": 1000})
```

### Step 4: Create Usage Example
```python
# Example usage
if __name__ == "__main__":
    # Simple query
    result = netbox_agent.invoke({
        "messages": [{"role": "user", "content": "Check NetBox server health"}]
    })

    # Complex query
    result = netbox_agent.invoke({
        "messages": [{"role": "user", "content": "Summarize all manufacturers by device count"}]
    })
```

## Validation Loop

### Structure Validation
```python
def test_agent_structure():
    """Ensure agent follows research_agent.py pattern exactly"""
    assert isinstance(netbox_agent, CompiledStateGraph)
    assert netbox_agent.config["recursion_limit"] == 1000
    # Verify no framework modifications required
```

### Query Handling Tests
```python
def test_simple_queries():
    """Test basic NetBox operations"""
    queries = [
        "Check NetBox server health",
        "List all sites",
        "Show all devices"
    ]
    # Verify direct tool execution without planning overhead

def test_complex_queries():
    """Test multi-step operations with planning"""
    queries = [
        "Summarize manufacturers by device count",
        "What VLANs are used in site Amsterdam-DC?",
        "Show device utilization across all sites"
    ]
    # Verify planning tool usage and multi-step execution
```

### Fallback Strategy Testing
```python
def test_error_recovery():
    """Test graceful error recovery through reasoning"""
    # Test parameter normalization
    # Test tool family switching
    # Test filter relaxation
    # Test attempt limiting
```

## Production Readiness Checklist
- [ ] Agent structure matches research_agent.py exactly
- [ ] All 60+ NetBox MCP tools properly wrapped
- [ ] Comprehensive instructions provide domain expertise
- [ ] Planning tool integrated for complex queries
- [ ] Fallback strategies work through reasoning
- [ ] Answer formatting follows specified structure
- [ ] No hardcoded logic or framework modifications
- [ ] Agent demonstrates intelligent tool selection

---
*This PRP provides comprehensive context for creating a NetBox infrastructure agent that achieves Claude Code-level sophistication through agent intelligence rather than architectural complexity.*
