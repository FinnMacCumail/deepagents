import os
import sys
import asyncio
import inspect
import json
import time
from typing import Optional, Dict, Any, List, Callable, Tuple
from deepagents import async_create_deep_agent
from deepagents.cached_model import get_cached_model
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

        self.total_input_tokens += usage.get("input_tokens", 0)

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

        # Calculate cost savings (assuming $3/million input tokens)
        standard_cost = (self.total_input_tokens / 1_000_000) * 3.0
        cache_read_cost = (self.cached_tokens_read / 1_000_000) * 0.30  # 90% discount
        cache_write_cost = (self.cached_tokens_written / 1_000_000) * 3.75  # 25% premium
        actual_cost = standard_cost - (self.cached_tokens_read / 1_000_000 * 2.70) + (cache_write_cost - standard_cost)
        savings_percentage = ((standard_cost - actual_cost) / standard_cost * 100) if standard_cost > 0 else 0

        return {
            "total_requests": total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "total_input_tokens": self.total_input_tokens,
            "cached_tokens_read": self.cached_tokens_read,
            "cached_tokens_written": self.cached_tokens_written,
            "estimated_cost_savings": f"{savings_percentage:.1f}%",
            "standard_cost": f"${standard_cost:.4f}",
            "actual_cost": f"${actual_cost:.4f}"
        }

# Global cache monitor instance
cache_monitor = CacheMonitor()

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

    # Combine instructions with tool definitions for caching
    # The CachedChatAnthropic will automatically add cache_control markers
    full_instructions = enhanced_instructions + tools_text

    tool_list = list(all_tools.values())
    tool_list.extend([list_available_tools, get_tool_details, show_cache_metrics])

    print(f"📊 Cache Configuration:")
    print(f"  - Caching Enabled: {enable_caching}")
    print(f"  - Cache TTL: {cache_ttl}")
    print(f"  - Instructions Size: ~{len(enhanced_instructions)//4} tokens")
    print(f"  - Tools Definition Size: ~{len(tools_text)//4} tokens")
    print(f"  - Total System Message: ~{len(full_instructions)//4} tokens")
    print(f"  - Will be cached: {'✅ YES' if enable_caching and len(full_instructions) > 4096 else '❌ NO'}")

    # Use cached model if caching is enabled
    if enable_caching:
        model = get_cached_model(
            enable_caching=True,
            cache_ttl=cache_ttl
        )
    else:
        model = None  # Use default model

    # Create agent with model override
    # Use the full_instructions that includes tool definitions for caching
    agent = async_create_deep_agent(
        tool_list,
        full_instructions,
        model=model,
        subagents=[]
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