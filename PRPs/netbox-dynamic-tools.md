# PRP: Dynamic NetBox Tool Generation for DeepAgents

## Context

The current NetBox agent implementation at `/home/ola/dev/rnd/deepagents/examples/netbox/netbox_agent.py` has a critical limitation:
- **Only 8 out of 62 available tools** are exposed (13% coverage)
- Tools are manually wrapped one-by-one
- 54 tools remain inaccessible to the agent

### Current Implementation Pattern

```python
# Current manual wrapper pattern (lines 39-57 in netbox_agent.py)
async def netbox_get_device_info(device_name: str, ...):
    client = get_netbox_client()
    tool_func = TOOL_REGISTRY.get('netbox_get_device_info', {}).get('function')
    if not tool_func:
        raise RuntimeError(...)
    return tool_func(client=client, device_name=device_name, ...)
```

### NetBox MCP Architecture

The NetBox MCP server (`/home/ola/dev/netboxdev/netbox-mcp`) uses a decorator-based registry system:

1. **Registry System** (`/home/ola/dev/netboxdev/netbox-mcp/netbox_mcp/registry.py`):
   - `@mcp_tool` decorator automatically registers tools to `TOOL_REGISTRY`
   - Each tool has metadata: name, function, category, description, parameters
   - Tools are organized in categories: dcim, ipam, system, tenancy, extras, virtualization

2. **Tool Loading** (`/home/ola/dev/netboxdev/netbox-mcp/netbox_mcp/tools/__init__.py`):
   - `load_all_tools()` imports all domain packages
   - Tools are discovered via decorator pattern

3. **Tool Structure** (e.g., `/home/ola/dev/netboxdev/netbox-mcp/netbox_mcp/tools/dcim/devices.py`):
   ```python
   @mcp_tool(category="dcim")
   def netbox_get_device_info(client: NetBoxClient, device_name: str, ...):
       # Implementation
   ```

### DeepAgents Framework

The DeepAgents framework (`/home/ola/dev/rnd/deepagents/src/deepagents`) supports:
- `async_create_deep_agent()` for async tools (required for MCP tools)
- Tools passed as sequence of callables
- Sub-agent delegation pattern for large tool sets

## Implementation Blueprint

### Phase 1: Dynamic Wrapper Generator

```python
# netbox_agent.py - Dynamic wrapper generation

def create_async_tool_wrapper(tool_name: str, tool_metadata: dict):
    """
    Create an async wrapper function for a NetBox MCP tool.

    This function generates a wrapper that:
    1. Injects the NetBox client
    2. Calls the actual tool function from registry
    3. Handles errors gracefully
    """
    # Extract parameter info from metadata
    parameters = tool_metadata.get('parameters', [])

    # Build function signature dynamically
    async def wrapper(**kwargs):
        client = get_netbox_client()
        tool_func = tool_metadata.get('function')
        if not tool_func:
            raise RuntimeError(f"Tool '{tool_name}' function not found")

        # Filter out 'client' from kwargs to avoid duplicate
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'client'}

        # Execute tool with client injection
        return tool_func(client=client, **filtered_kwargs)

    # Set proper metadata for LangChain
    wrapper.__name__ = tool_name
    wrapper.__doc__ = tool_metadata.get('description', f"Execute {tool_name}")

    # Add parameter annotations from metadata
    wrapper.__annotations__ = build_annotations_from_metadata(parameters)

    return wrapper

def generate_all_tool_wrappers():
    """Generate wrappers for all tools in TOOL_REGISTRY"""
    from netbox_mcp.registry import TOOL_REGISTRY

    wrapped_tools = {}
    for tool_name, tool_metadata in TOOL_REGISTRY.items():
        wrapped_tools[tool_name] = create_async_tool_wrapper(tool_name, tool_metadata)

    return wrapped_tools
```

### Phase 2: Tool Organization by Category

```python
def organize_tools_by_category(wrapped_tools):
    """Organize tools by their categories for better discovery"""
    from netbox_mcp.registry import TOOL_REGISTRY

    categorized = {
        'system': [],
        'dcim': [],
        'ipam': [],
        'tenancy': [],
        'extras': [],
        'virtualization': []
    }

    for tool_name, wrapper in wrapped_tools.items():
        category = TOOL_REGISTRY.get(tool_name, {}).get('category', 'general')
        if category in categorized:
            categorized[category].append((tool_name, wrapper))

    return categorized
```

### Phase 3: Enhanced Agent Configuration

```python
# Dynamic agent creation with all tools
def create_netbox_agent_with_all_tools():
    # Load all NetBox MCP tools
    load_all_tools()

    # Generate wrappers for all tools
    all_tools = generate_all_tool_wrappers()

    # Organize by category
    categorized_tools = organize_tools_by_category(all_tools)

    # Build enhanced instructions with tool categories
    enhanced_instructions = build_enhanced_instructions(categorized_tools)

    # Create agent with all tools
    return async_create_deep_agent(
        list(all_tools.values()),
        enhanced_instructions,
        subagents=[]  # Can add category-specific subagents later
    ).with_config({"recursion_limit": 1000})
```

### Phase 4: Tool Discovery Capabilities

```python
# Add tool discovery functions
async def list_available_tools(category: Optional[str] = None):
    """List available NetBox tools, optionally filtered by category"""
    from netbox_mcp.registry import TOOL_REGISTRY

    tools = []
    for name, metadata in TOOL_REGISTRY.items():
        if category and metadata.get('category') != category:
            continue
        tools.append({
            'name': name,
            'category': metadata.get('category'),
            'description': metadata.get('description')
        })
    return tools

async def get_tool_details(tool_name: str):
    """Get detailed information about a specific tool"""
    from netbox_mcp.registry import get_tool_by_name

    tool = get_tool_by_name(tool_name)
    if not tool:
        return {'error': f'Tool {tool_name} not found'}

    # Remove function reference for serialization
    details = tool.copy()
    details.pop('function', None)
    return details
```

## Implementation Tasks

1. **Set up environment**
   - Ensure netbox-mcp is importable
   - Verify NetBox client configuration

2. **Implement dynamic wrapper generator**
   - Create `create_async_tool_wrapper()` function
   - Handle parameter annotation building
   - Test with a single tool first

3. **Generate all tool wrappers**
   - Implement `generate_all_tool_wrappers()`
   - Verify all 62 tools are wrapped
   - Handle edge cases and errors

4. **Organize tools by category**
   - Implement category organization
   - Update agent instructions with category info

5. **Update agent configuration**
   - Replace manual tool list with dynamic tools
   - Enhance instructions with tool categories
   - Add tool discovery helpers

6. **Add tool discovery capabilities**
   - Implement `list_available_tools()`
   - Implement `get_tool_details()`
   - Add these as agent tools

7. **Testing and validation**
   - Test with example queries from `/home/ola/dev/netboxdev/netbox-mcp-docs/netbox-queries`
   - Verify all tools are accessible
   - Test error handling

## Key Files to Reference

- **Current Implementation**: `/home/ola/dev/rnd/deepagents/examples/netbox/netbox_agent.py`
- **Registry System**: `/home/ola/dev/netboxdev/netbox-mcp/netbox_mcp/registry.py`
- **Tool Loading**: `/home/ola/dev/netboxdev/netbox-mcp/netbox_mcp/tools/__init__.py`
- **Example Tool**: `/home/ola/dev/netboxdev/netbox-mcp/netbox_mcp/tools/dcim/devices.py`
- **DeepAgents Framework**: `/home/ola/dev/rnd/deepagents/src/deepagents/graph.py`
- **Research Agent Example**: `/home/ola/dev/rnd/deepagents/examples/research/research_agent.py`

## Error Handling Strategy

1. **Tool Not Found**: Return clear error message with available alternatives
2. **Client Connection**: Lazy initialize and cache NetBox client
3. **Parameter Validation**: Use metadata to validate before calling
4. **Rate Limiting**: Consider implementing request throttling
5. **Graceful Degradation**: Fallback to basic tools if dynamic generation fails

## Validation Gates

```bash
# Check Python syntax
python -m py_compile examples/netbox/netbox_agent.py

# Run basic agent test
cd examples/netbox
python -c "
from netbox_agent import create_netbox_agent_with_all_tools
from netbox_mcp.registry import TOOL_REGISTRY
import asyncio

# Verify all tools are accessible
agent = create_netbox_agent_with_all_tools()
print(f'Total tools in registry: {len(TOOL_REGISTRY)}')
print(f'Agent initialized successfully')

# Test basic query
async def test():
    result = await agent.ainvoke({
        'messages': [{'role': 'user', 'content': 'Check NetBox server health'}]
    })
    return result

# Run test
asyncio.run(test())
"

# Verify tool count
python -c "
from netbox_mcp import load_all_tools
from netbox_mcp.registry import TOOL_REGISTRY
load_all_tools()
print(f'Tools loaded: {len(TOOL_REGISTRY)}')
assert len(TOOL_REGISTRY) >= 62, 'Expected at least 62 tools'
"
```

## External Resources

- **Deep Agents Architecture**: https://blog.langchain.com/deep-agents/
- **Deep Agents Documentation**: https://docs.langchain.com/labs/deep-agents/overview
- **MCP Protocol**: Model Context Protocol for tool integration
- **NetBox API Documentation**: Referenced within netbox-mcp implementation

## Success Criteria

- ✅ All 62 NetBox MCP tools are dynamically wrapped and accessible
- ✅ Tools are organized by category for better discovery
- ✅ Agent can list available tools and their details
- ✅ All example queries from netbox-queries work correctly
- ✅ No manual tool wrapping required for new tools
- ✅ Error handling provides useful feedback

## Confidence Score: 9/10

The PRP provides comprehensive context with:
- Exact file paths and line numbers
- Working code patterns from the existing codebase
- Clear implementation pseudocode
- Executable validation gates
- Complete error handling strategy

The only uncertainty is around parameter annotation building which may require minor adjustments during implementation.