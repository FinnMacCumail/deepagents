import os
import sys
import asyncio
import inspect
from typing import Optional, Dict, Any, List, Callable
from deepagents import async_create_deep_agent
from langchain_core.tools import tool

# Add netbox-mcp to path if not already there
NETBOX_MCP_PATH = "/home/ola/dev/netboxdev/netbox-mcp"
if NETBOX_MCP_PATH not in sys.path:
    sys.path.insert(0, NETBOX_MCP_PATH)

from netbox_mcp import NetBoxClient, load_config
from netbox_mcp.tools import load_all_tools
from netbox_mcp.registry import TOOL_REGISTRY, get_tool_by_name

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

    instructions = f"""You are a NetBox infrastructure analyst with real-time NetBox MCP integration.

## Role and Goals
- Interpret natural-language queries about NetBox infrastructure
- Plan multi-step retrievals using the write_todos tool when needed
- Choose appropriate tools from {len(TOOL_REGISTRY)} available NetBox tools
- Present clear, human-friendly responses with good formatting
- Use emojis and structured formatting for better readability

## Available Tool Categories ({len(TOOL_REGISTRY)} total tools)
{chr(10).join(tool_summary)}

### Response Formatting Guidelines
- Use emojis to make responses more engaging (✅ ❌ 🔧 📊 🏢 etc.)
- Structure responses with clear sections and bullet points
- Include key statistics and summaries
- Make technical information accessible to humans
- End responses with helpful follow-up suggestions

## Tool Selection Strategy
- Use get_* tools for specific objects (devices, sites, etc.)
- Use list_* tools for inventory and bulk queries
- Use tool discovery functions to explore capabilities
- Plan complex queries with write_todos when needed

## Quick Reference
- Use `list_available_tools()` to see all available tools
- Use `get_tool_details(tool_name)` for detailed tool information
- All tools connect to live NetBox API and return real data"""

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

def create_netbox_agent_with_all_tools():
    """Create a NetBox agent with all dynamically generated tools."""
    if len(TOOL_REGISTRY) == 0:
        load_all_tools()

    print(f"Generating wrappers for {len(TOOL_REGISTRY)} NetBox tools...")
    all_tools = generate_all_tool_wrappers()
    print(f"Successfully wrapped {len(all_tools)} tools")

    categorized_tools = organize_tools_by_category(all_tools)
    enhanced_instructions = build_enhanced_instructions(categorized_tools)

    tool_list = list(all_tools.values())
    tool_list.extend([list_available_tools, get_tool_details])

    print(f"Creating agent with {len(tool_list)} tools (including discovery tools)")

    return async_create_deep_agent(
        tool_list,
        enhanced_instructions,
        subagents=[]
    ).with_config({"recursion_limit": 1000})

# Create the global agent instance
netbox_agent = create_netbox_agent_with_all_tools()

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

async def process_netbox_query(query: str):
    """Process a NetBox query and show human-friendly response"""
    print(f"\n🔄 Processing: {query}")

    try:
        result = await netbox_agent.ainvoke({
            "messages": [{"role": "user", "content": query}]
        }, config={'recursion_limit': 20})

        response, msg_count = extract_agent_response(result)

        print(f"\n🤖 NetBox Agent Response:")
        print("-" * 60)
        print(response)
        print("-" * 60)
        print(f"📊 Messages: {msg_count}")

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

if __name__ == "__main__":
    asyncio.run(main())