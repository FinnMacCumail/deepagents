# NetBox Infrastructure Agent - Initial Requirements

## FEATURE:
Single NetBox Infrastructure Agent with Expanded Instructions for Read-Only MCP Operations

## EXAMPLES:
- Mirror `examples/research/research_agent.py` structure exactly (single agent + planning tool)
- Agent interprets natural language queries like "List all devices in Amsterdam-DC" and decomposes into appropriate MCP tool calls
- Uses `write_todos` planning tool for multi-step retrieval strategies and progress tracking
- Handles 60+ read-only NetBox MCP tools across DCIM, IPAM, Tenancy, and Virtualization domains
- Recovers gracefully from tool failures through intelligent fallback strategies (no hardcoded logic)
- Query examples:
  - Simple: "Check NetBox server health" → direct `netbox_get_server_health()` call
  - Intermediate: "What VLANs does switch-01 have?" → plan retrieval, call `netbox_get_device_info` with interfaces, extract VLANs
  - Complex: "Summarize manufacturers by device count" → plan multi-step, list manufacturers, list devices per manufacturer, aggregate in reasoning

## DOCUMENTATION:
- **Primary Template**: `examples/research/research_agent.py` - exact structure to follow
- **DeepAgents API**: `create_deep_agent()` function with no framework modifications
- **NetBox MCP Tools**: Read-only tools documentation showing `netbox_get_*` and `netbox_list_*` functions
- **Tool Parameters**: Filters (site, tenant, status, role, manufacturer_name, vid, limit), pagination (interface_limit, cable_limit)
- **NetBox Domains**: DCIM (devices, racks, sites), IPAM (prefixes, VLANs, IPs), Tenancy (tenants), Virtualization (VMs, clusters)
- **Claude Code API Analysis**: Reference behavior patterns for sophisticated NetBox operations

## OTHER CONSIDERATIONS:

### Architecture Constraints
- **NO sub-agents** - single agent with comprehensive domain knowledge in instructions
- **NO hardcoded error recovery** - agent learns through context and reasoning
- **NO framework modifications** - pure configuration approach using existing DeepAgents API
- **Planning tool integration** - use built-in `write_todos` for task decomposition and progress tracking
- **Read-only operations only** - exclusively `netbox_get_*` and `netbox_list_*` tools

### Tool Selection Intelligence
Agent must learn to:
- Choose `netbox_get_*` tools for specific object queries (single device, rack, prefix)
- Choose `netbox_list_*` tools for bulk queries (all devices in site, all manufacturers)
- Apply appropriate filters to reduce result sets (site, tenant, status, role, manufacturer_name, vid, limit)
- Handle pagination through parameters (interface_limit, cable_limit) or specialized tools

### Fallback Strategy Requirements
Agent should implement intelligent fallbacks through reasoning:
- Check and normalize parameters (correct case/slug format)
- Switch tool families (get tool fails → try list tool with filters)
- Relax filters gradually (remove specific filters, keep essential ones)
- Limit attempts (max 3 fallback attempts per step)
- Never loop indefinitely (ask for clarification after failures)

### Answer Formatting Standards
- Begin with one-sentence summary of findings
- Provide key statistics (counts per site/role, utilization percentages)
- Include bulleted examples (device names, roles, statuses, sites, VIDs, prefixes)
- End with follow-up question offers to refine or expand query

### Expected Agent Structure
Following research_agent.py pattern:
```python
# Tool functions (simple wrappers, no hardcoded logic)
def netbox_get_device_info(device_name, site=None, interface_limit=None, cable_limit=None, include_interfaces=True, include_cables=True): ...
def netbox_list_devices(site=None, tenant=None, status=None, role=None, limit=None): ...
# ... all 60+ NetBox MCP tools

# Comprehensive instructions (like research_instructions)
netbox_instructions = """You are a read-only NetBox infrastructure analyst...
[Expanded domain knowledge and reasoning strategies]
"""

# Agent creation (identical to research_agent.py)
netbox_agent = create_deep_agent(
    [netbox_get_device_info, netbox_list_devices, ...],  # All 60+ tools
    netbox_instructions,  # Comprehensive domain guidance
    subagents=[]  # No sub-agents
).with_config({"recursion_limit": 1000})
```

### Success Criteria
- Agent demonstrates intelligent tool selection based on query specificity
- Uses planning tool for complex multi-step retrievals
- Recovers gracefully from tool failures through context-driven reasoning
- Provides structured answers with summaries and examples
- Follows research_agent.py structure exactly with no framework modifications
- Achieves Claude Code-level NetBox operation sophistication through agent intelligence