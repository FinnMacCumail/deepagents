# PRP: Claude API Prompt Caching Implementation for NetBox Agent

## Executive Summary

Implement Claude API Prompt Caching for the NetBox agent to achieve 90% cost reduction and 85% latency improvement. The agent currently sends ~20,000 tokens per request (2,000 tokens of instructions + 15,000-20,000 tokens of tool definitions), making it an ideal candidate for prompt caching optimization.

## Success Criteria

- [ ] Prompt caching reduces API costs by at least 77%
- [ ] Latency reduced by at least 50% for subsequent queries
- [ ] All 62 NetBox tools remain fully functional
- [ ] Cache monitoring and metrics implemented
- [ ] Backward compatibility maintained
- [ ] Tests pass and code is properly formatted

## Research Context

### Current Implementation Analysis

**File**: `/home/ola/dev/rnd/deepagents/examples/netbox/netbox_agent.py`

The NetBox agent implementation:
- Dynamically generates wrappers for 62 NetBox MCP tools (lines 134-143)
- Creates enhanced instructions with tool categories (lines 163-204)
- Uses `async_create_deep_agent` from deepagents framework (lines 271-275)
- Token usage breakdown:
  - Enhanced instructions: ~2,000 tokens (static)
  - Tool definitions: ~15,000-20,000 tokens (static)
  - Conversation history: Variable (grows over time)

### DeepAgents Framework Integration Points

**Key Files**:
- `/home/ola/dev/rnd/deepagents/src/deepagents/graph.py:91` - Main agent builder
- `/home/ola/dev/rnd/deepagents/src/deepagents/model.py:5` - Model configuration

Current model instantiation:
```python
def get_default_model():
    return ChatAnthropic(model_name="claude-sonnet-4-20250514", max_tokens=64000)
```

### Claude API Caching Documentation

**Documentation URLs**:
- Main docs: https://docs.claude.com/en/docs/build-with-claude/prompt-caching
- Cookbook: https://github.com/anthropics/anthropic-cookbook/blob/main/misc/prompt_caching.ipynb

**Key Requirements**:
- Minimum cacheable content: 1024 tokens (Claude Sonnet/Opus)
- Cache duration: 5 minutes (default) or 1 hour (with `"ttl": "1h"`)
- Cache control: `{"cache_control": {"type": "ephemeral"}}`
- Beta header required: `"anthropic-beta": "prompt-caching-2024-07-31"`

**Pricing Impact**:
- Cache writes: 125% of base input token cost
- Cache reads: 10% of base input token cost (90% discount)
- Break-even: After 2 cache hits

## Implementation Blueprint

### Phase 1: Create Cacheable Model Configuration

Create new file: `src/deepagents/cached_model.py`

```python
from langchain_anthropic import ChatAnthropic
from typing import Optional, Dict, Any, List
import os

class CachedChatAnthropic(ChatAnthropic):
    """Extended ChatAnthropic with prompt caching support"""

    def __init__(
        self,
        model_name: str = "claude-sonnet-4-20250514",
        max_tokens: int = 64000,
        enable_caching: bool = True,
        cache_ttl: str = "default",  # "default" (5min) or "1h"
        **kwargs
    ):
        super().__init__(
            model_name=model_name,
            max_tokens=max_tokens,
            **kwargs
        )
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl

        # Enable caching beta header
        if enable_caching:
            self.client_kwargs = self.client_kwargs or {}
            self.client_kwargs["default_headers"] = {
                "anthropic-beta": "prompt-caching-2024-07-31"
            }

    def _prepare_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add cache control to appropriate message blocks"""
        if not self.enable_caching:
            return messages

        processed = []
        for msg in messages:
            # Check if this is a system message with tool definitions
            if msg.get("role") == "system" and isinstance(msg.get("content"), list):
                # Mark large static content for caching
                for content_block in msg["content"]:
                    if content_block.get("type") == "text":
                        text_len = len(content_block.get("text", ""))
                        # Cache if over 1024 tokens (rough estimate: 4 chars = 1 token)
                        if text_len > 4096:
                            content_block["cache_control"] = {"type": "ephemeral"}
                            if self.cache_ttl == "1h":
                                content_block["cache_control"]["ttl"] = "1h"
            processed.append(msg)

        return processed

def get_cached_model(
    model_name: Optional[str] = None,
    enable_caching: bool = True,
    cache_ttl: str = "default"
) -> CachedChatAnthropic:
    """Factory function for cached model instances"""
    return CachedChatAnthropic(
        model_name=model_name or "claude-sonnet-4-20250514",
        max_tokens=64000,
        enable_caching=enable_caching,
        cache_ttl=cache_ttl
    )
```

### Phase 2: Implement Caching in NetBox Agent

Update `examples/netbox/netbox_agent.py`:

```python
# Add imports at top
from deepagents.cached_model import get_cached_model
import json
import time
from typing import Tuple

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

    def log_request(self, response):
        """Extract and log cache metrics from API response"""
        usage = response.get("usage", {})

        # Track cache performance
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_write = usage.get("cache_creation_input_tokens", 0)

        if cache_read > 0:
            self.cache_hits += 1
            self.cached_tokens_read += cache_read
        else:
            self.cache_misses += 1

        if cache_write > 0:
            self.cached_tokens_written += cache_write

        self.total_input_tokens += usage.get("input_tokens", 0)

        # Store request metadata
        self.requests.append({
            "timestamp": time.time(),
            "cache_read": cache_read,
            "cache_write": cache_write,
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0)
        })

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

# Update create_netbox_agent_with_all_tools function
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

    # Prepare tool definitions for caching
    tool_definitions = []
    for tool_name, tool_func in all_tools.items():
        tool_metadata = TOOL_REGISTRY.get(tool_name, {})
        tool_definitions.append({
            "name": tool_name,
            "description": tool_metadata.get("description", ""),
            "parameters": tool_metadata.get("parameters", [])
        })

    # Create cacheable content blocks
    cacheable_blocks = []

    # Block 1: Enhanced instructions (mark for caching if > 1024 tokens)
    instructions_block = {
        "type": "text",
        "text": enhanced_instructions
    }
    if enable_caching and len(enhanced_instructions) > 4096:  # ~1024 tokens
        instructions_block["cache_control"] = {"type": "ephemeral"}
        if cache_ttl == "1h":
            instructions_block["cache_control"]["ttl"] = "1h"
    cacheable_blocks.append(instructions_block)

    # Block 2: Tool definitions (definitely cache this - it's huge)
    tools_text = f"\n## Available Tools ({len(tool_definitions)} total)\n"
    tools_text += json.dumps(tool_definitions, indent=2)

    tools_block = {
        "type": "text",
        "text": tools_text
    }
    if enable_caching:
        tools_block["cache_control"] = {"type": "ephemeral"}
        if cache_ttl == "1h":
            tools_block["cache_control"]["ttl"] = "1h"
    cacheable_blocks.append(tools_block)

    tool_list = list(all_tools.values())
    tool_list.extend([list_available_tools, get_tool_details])

    print(f"📊 Cache Configuration:")
    print(f"  - Caching Enabled: {enable_caching}")
    print(f"  - Cache TTL: {cache_ttl}")
    print(f"  - Instructions Size: ~{len(enhanced_instructions)//4} tokens")
    print(f"  - Tools Definition Size: ~{len(tools_text)//4} tokens")
    print(f"  - Total Cacheable: ~{(len(enhanced_instructions) + len(tools_text))//4} tokens")

    # Use cached model if caching is enabled
    if enable_caching:
        from deepagents.cached_model import get_cached_model
        model = get_cached_model(
            enable_caching=True,
            cache_ttl=cache_ttl
        )
    else:
        model = None  # Use default model

    # Create agent with model override
    agent = async_create_deep_agent(
        tool_list,
        enhanced_instructions,
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

# Update process_netbox_query to track metrics
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

        # Track cache metrics if enabled
        if track_metrics and hasattr(result, "_raw_response"):
            cache_monitor.log_request(result._raw_response)

        print(f"\n🤖 NetBox Agent Response:")
        print("-" * 60)
        print(response)
        print("-" * 60)
        print(f"📊 Messages: {msg_count} | ⏱️ Time: {elapsed:.2f}s")

        # Show cache metrics periodically
        if track_metrics and cache_monitor.requests and len(cache_monitor.requests) % 5 == 0:
            metrics = cache_monitor.get_metrics()
            print(f"\n💰 Cache Performance:")
            print(f"  - Hit Rate: {metrics['cache_hit_rate']}")
            print(f"  - Cost Savings: {metrics['estimated_cost_savings']}")

    except Exception as e:
        print(f"❌ Query failed: {str(e)}")
        raise

# Add new command to show cache metrics
@tool
async def show_cache_metrics() -> Dict[str, Any]:
    """Display detailed cache performance metrics"""
    return cache_monitor.get_metrics()

# Update initialization with cache configuration
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
```

### Phase 3: Advanced Caching Strategy Implementation

Create `examples/netbox/caching_strategy.py`:

```python
"""
Advanced caching strategies for NetBox agent optimization
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import hashlib
import json

@dataclass
class CacheStrategy:
    """Define caching strategy based on query patterns"""

    # Query type classifications
    SIMPLE_QUERIES = ["list", "show", "get", "check"]  # 5-min cache
    COMPLEX_QUERIES = ["audit", "report", "analyze", "trace"]  # 1-hour cache
    INTERACTIVE_QUERIES = ["explore", "investigate", "debug"]  # 1-hour cache

    @classmethod
    def determine_cache_ttl(cls, query: str) -> str:
        """Determine optimal cache TTL based on query type"""
        query_lower = query.lower()

        # Check for complex/long-running query patterns
        for keyword in cls.COMPLEX_QUERIES:
            if keyword in query_lower:
                return "1h"

        # Check for interactive exploration patterns
        for keyword in cls.INTERACTIVE_QUERIES:
            if keyword in query_lower:
                return "1h"

        # Default to short cache for simple queries
        return "default"

    @classmethod
    def should_cache_conversation(cls, messages: List[Dict], threshold: int = 3) -> bool:
        """Determine if conversation history should be cached"""
        # Cache if conversation has more than threshold turns
        user_messages = [m for m in messages if m.get("role") == "user"]
        return len(user_messages) > threshold

    @classmethod
    def generate_cache_key(cls, content: str) -> str:
        """Generate a cache key for content deduplication"""
        return hashlib.md5(content.encode()).hexdigest()[:8]

class DynamicCacheManager:
    """Manage dynamic caching decisions based on usage patterns"""

    def __init__(self):
        self.query_history = []
        self.cache_keys = {}
        self.session_start = None

    def optimize_caching(self, query: str, session_duration: float) -> Dict[str, Any]:
        """Determine optimal caching parameters for current query"""

        # Determine cache TTL based on query type
        cache_ttl = CacheStrategy.determine_cache_ttl(query)

        # Use longer cache for extended sessions (> 5 minutes)
        if session_duration > 300:
            cache_ttl = "1h"

        # Check if this is a repeated query pattern
        query_key = CacheStrategy.generate_cache_key(query)
        is_repeated = query_key in self.cache_keys

        return {
            "enable_caching": True,
            "cache_ttl": cache_ttl,
            "cache_conversation": session_duration > 180,  # Cache after 3 minutes
            "is_repeated_pattern": is_repeated,
            "optimization_reason": self._get_optimization_reason(query, session_duration, is_repeated)
        }

    def _get_optimization_reason(self, query: str, session_duration: float, is_repeated: bool) -> str:
        """Explain caching decision"""
        reasons = []

        if "report" in query.lower() or "audit" in query.lower():
            reasons.append("Complex query detected - using 1-hour cache")
        elif session_duration > 300:
            reasons.append("Extended session - using 1-hour cache")
        elif is_repeated:
            reasons.append("Repeated query pattern - maximizing cache reuse")
        else:
            reasons.append("Standard query - using 5-minute cache")

        return " | ".join(reasons)

# Example usage in netbox_agent.py
cache_manager = DynamicCacheManager()

def create_optimized_netbox_agent(session_context: Optional[Dict] = None):
    """Create NetBox agent with optimized caching based on context"""

    # Analyze session context
    if session_context:
        query = session_context.get("initial_query", "")
        session_duration = session_context.get("duration", 0)

        # Get optimized cache settings
        cache_config = cache_manager.optimize_caching(query, session_duration)

        print(f"🧠 Cache Optimization: {cache_config['optimization_reason']}")

        return create_netbox_agent_with_all_tools(
            enable_caching=cache_config["enable_caching"],
            cache_ttl=cache_config["cache_ttl"],
            cache_conversation=cache_config["cache_conversation"]
        )

    # Default configuration
    return create_netbox_agent_with_all_tools()
```

## Implementation Tasks

1. **Create cached model wrapper** (`src/deepagents/cached_model.py`)
   - Extend ChatAnthropic with cache_control support
   - Add beta header for prompt caching
   - Implement message preparation with cache markers

2. **Update NetBox agent** (`examples/netbox/netbox_agent.py`)
   - Import and use CachedChatAnthropic
   - Add CacheMonitor class for metrics
   - Update create_netbox_agent_with_all_tools with caching parameters
   - Implement cache configuration via environment variables

3. **Create caching strategy module** (`examples/netbox/caching_strategy.py`)
   - CacheStrategy class for query classification
   - DynamicCacheManager for runtime optimization
   - Helper functions for cache key generation

4. **Add cache testing script** (`examples/netbox/test_caching.py`)
   ```python
   import asyncio
   from netbox_agent import create_netbox_agent_with_all_tools, process_netbox_query, cache_monitor

   async def test_cache_performance():
       """Test cache performance with repeated queries"""

       # Test queries from netbox-queries file
       test_queries = [
           "Show me all sites in NetBox",
           "List all devices in site DM-Binghamton",
           "Get detailed information about device dmi01-akron-pdu01"
       ]

       print("🧪 Testing Cache Performance\n")

       # Run each query twice to test cache hits
       for query in test_queries:
           print(f"\n{'='*60}")
           print(f"Query: {query}")
           print(f"{'='*60}")

           # First run (cache write)
           print("\n📝 Run 1 (Cache Write):")
           await process_netbox_query(query)

           # Second run (cache read)
           print("\n📖 Run 2 (Cache Read):")
           await process_netbox_query(query)

       # Display final metrics
       print(f"\n{'='*60}")
       print("📊 Final Cache Metrics:")
       print(f"{'='*60}")
       metrics = cache_monitor.get_metrics()
       for key, value in metrics.items():
           print(f"  {key}: {value}")

   if __name__ == "__main__":
       # Create agent with caching enabled
       global netbox_agent
       netbox_agent = create_netbox_agent_with_all_tools(
           enable_caching=True,
           cache_ttl="1h"
       )

       # Run tests
       asyncio.run(test_cache_performance())
   ```

5. **Update documentation** (`examples/netbox/README_CACHING.md`)
   - Document cache configuration options
   - Provide performance benchmarks
   - Include troubleshooting guide

## Validation Gates

```bash
# 1. Syntax and style validation
cd /home/ola/dev/rnd/deepagents
ruff check --fix examples/netbox/ src/deepagents/

# 2. Test basic functionality
cd examples/netbox
python -c "from netbox_agent import create_netbox_agent_with_all_tools; agent = create_netbox_agent_with_all_tools(enable_caching=True); print('✅ Agent creation successful')"

# 3. Test caching functionality
python test_caching.py

# 4. Verify cache metrics
python -c "from netbox_agent import cache_monitor, show_cache_metrics; import asyncio; asyncio.run(show_cache_metrics())"

# 5. Run example queries with caching
NETBOX_CACHE=true NETBOX_CACHE_TTL=1h python netbox_agent.py
```

## Error Handling & Edge Cases

1. **Cache misses on tool definition changes**
   - Solution: Version tool definitions, increment on changes
   - Implementation: Add tool_version parameter

2. **Memory pressure with large conversations**
   - Solution: Limit conversation cache to last N turns
   - Implementation: Sliding window for conversation history

3. **API rate limits during cache warming**
   - Solution: Implement gradual cache warming
   - Implementation: Stagger initial requests

4. **Cache invalidation on NetBox data changes**
   - Solution: Not applicable (NetBox MCP is read-only)
   - Note: Document this limitation

## Expected Outcomes

### Performance Improvements
- **Cost Reduction**: 77-90% on repeated queries
- **Latency**: 50-85% reduction after cache warm-up
- **Token Usage**: ~18,000 tokens cached per session

### Monitoring Metrics
```json
{
  "cache_hit_rate": "80%",
  "cost_savings": "77%",
  "average_latency_reduction": "65%",
  "cached_tokens": 18000,
  "session_duration": "15 minutes"
}
```

## Reference Documentation

- Claude Prompt Caching: https://docs.claude.com/en/docs/build-with-claude/prompt-caching
- Anthropic Cookbook: https://github.com/anthropics/anthropic-cookbook/blob/main/misc/prompt_caching.ipynb
- DeepAgents Framework: https://docs.langchain.com/labs/deep-agents/overview
- NetBox MCP Server: `/home/ola/dev/netboxdev/netbox-mcp` (DO NOT MODIFY)

## Implementation Notes

- The NetBox MCP server at `/home/ola/dev/netboxdev/netbox-mcp` is READ-ONLY - do not modify
- Focus all changes in the deepagents repository
- Maintain backward compatibility - caching should be optional
- Use environment variables for configuration flexibility
- Monitor and log cache performance for optimization

## PRP Quality Score: 9/10

**Confidence Level**: Very High - This PRP provides comprehensive context including:
- Complete code examples with exact implementation
- All necessary file paths and references
- Validation gates that can be executed
- Error handling strategies
- Performance metrics and monitoring

The implementation path is clear, with all research included, making one-pass implementation highly achievable.