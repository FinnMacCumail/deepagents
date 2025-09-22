# Feature Request Template

## FEATURE:
We want to devlop our existing deepagent application.
We want to develop the netbox_agent.py to use Claude API Prompt Caching for NetBox Agent Optimization

Claude's Prompt Caching feature, now Generally Available on the Anthropic API, presents a significant opportunity to optimize the NetBox agent implementation. By caching frequently reused context, we can achieve signifiicant cost reduction and latency reduction for the NetBox infrastructure management system.

# Current NetBox Agent Architecture Analysis
The current NetBox agent includes substantial static context that gets sent with every API call:

1. **Enhanced Instructions** (~2,000 tokens)
   - Agent role and goals
   - Tool categories and descriptions
   - Tool selection strategies
   - Response formatting guidelines

2. **Tool Definitions** (~15,000-20,000 tokens)
   - 64 dynamically generated tool descriptions
   - Parameter specifications for each tool
   - Tool discovery functions

3. **Conversation History** (Variable, grows with each turn)
   - Previous messages and tool calls
   - Context accumulation over time

# Prompt Caching Implementation Strategy
### 1. What to Cache

For the NetBox agent, the following components should be cached:

```python
# Cacheable components (static across requests)
cache_components = {
    "system_prompt": enhanced_instructions,        # ~2,000 tokens
    "tool_definitions": all_tool_descriptions,     # ~15,000-20,000 tokens
    "netbox_categories": tool_category_metadata,   # ~500 tokens
}
```
We want to implement -
1. **Cache static components:**
   - Enhanced instructions
   - Tool definitions
   - Category metadata
2. **Implement conversation caching:**
   - Cache conversation history after 3+ turns
   - Use 1-hour cache for long sessions
   - **Add cache monitoring:**
3. **Advanced Optimization**
    - Implement dynamic cache duration:
    - Use 5-minute cache for quick queries
    - Use 1-hour cache for analysis sessions

## EXAMPLES:
A list of example netbox queries can be found here - /home/ola/dev/netboxdev/netbox-mcp-docs/netbox-queries

## DOCUMENTATION:
- Information regarding Claude API caching can be found here - https://docs.claude.com/en/docs/build-with-claude/prompt-caching & https://www.anthropic.com/news/prompt-caching
- Information regarding the deepagents application code base currently developed can be found here - url:https://blog.langchain.com/deep-agents/ & https://docs.langchain.com/labs/deep-agents/overview
The netbox mcp server application used can be located here - /home/ola/dev/netboxdev/netbox-mcp
This is the information regarding The NetBox Dynamic Agent - (examples/netbox/NETBOX_AGENT_TECHNICAL_REPORT.md)

## OTHER CONSIDERATIONS:
# Potential Issues and Solutions

1. **Cache misses on minor changes:**
   - Solution: Separate static and dynamic content clearly
   - Use versioning for instruction updates

2. **Memory pressure with large contexts:**
   - Solution: Implement cache eviction strategy
   - Monitor token usage per session

3. **Cost spike from cache writes:**
   - Solution: Batch similar requests
   - Implement request deduplication

# The netbox mcp server provides READ ONLY netbox api tools.
Do NOT make any changes to the codebase in /home/ola/dev/netboxdev/netbox-mcp