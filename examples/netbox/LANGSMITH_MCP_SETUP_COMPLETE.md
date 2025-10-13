# LangSmith MCP Server Setup - COMPLETE ✅

## Status: Successfully Configured

The LangSmith MCP Server has been installed and configured for Claude Code.

## Installation Details

- **Package**: `langsmith-mcp-server` v0.0.7
- **Installed via**: `pipx` (isolated environment)
- **Location**: Global (`~/.local/bin/langsmith-mcp-server`)
- **Configuration**: User scope (available in all projects)
- **Status**: ✓ Connected

## Configuration

```
Server Name: langsmith
Transport: stdio
Command: langsmith-mcp-server
Scope: User config
Environment:
  LANGSMITH_API_KEY: YOUR_LANGSMITH_API_KEY_HERE
```

## Available Tools

The following LangSmith MCP tools are now available in all Claude Code sessions:

### Core Tools:
1. **fetch_trace** - Fetch and analyze trace details
   - Parameters: `project_name`, `trace_id`
   - Use for: Detailed trace analysis, debugging

2. **get_project_runs_stats** - Get project statistics
   - Parameters: `project_name`
   - Use for: Overall performance metrics

3. **list_prompts** - List prompts in LangSmith
   - Use for: Viewing available prompts

4. **get_thread_history** - Get conversation history
   - Parameters: `thread_id`
   - Use for: Analyzing conversation threads

5. **list_datasets** - List evaluation datasets
   - Use for: Dataset management

Additional tools may include:
- `read_dataset`
- `read_example`
- `list_examples`

## Usage Examples

### Example 1: Analyze a Specific Trace
```
You: "Analyze trace abc123-xyz-789 from the netbox-agent project"

Claude Code will:
1. Extract trace ID from your message
2. Call: fetch_trace("netbox-agent", "abc123-xyz-789")
3. Parse the trace data
4. Provide analysis including:
   - Execution time breakdown
   - Token usage (cached vs uncached)
   - Tool calls made
   - Sub-agent delegation pattern
   - Cache hit rates
   - Bottlenecks or errors
5. Suggest optimizations if applicable
```

### Example 2: Get Project Statistics
```
You: "Show me statistics for the netbox-agent project"

Claude Code will:
1. Call: get_project_runs_stats("netbox-agent")
2. Display:
   - Total number of runs
   - Average execution time
   - Error rate
   - Total token usage
   - Most recent activity
```

### Example 3: Analyze from URL
```
You: "Analyze this trace: https://smith.langchain.com/o/015e8a69-0b20-49e2-99d7-db9177929abc/projects/p/e3c6aaec-73f9-41bc-90de-b2befa160fe7/r/abc123"

Claude Code will:
1. Extract trace ID: "abc123"
2. Fetch trace details
3. Provide comprehensive analysis
```

### Example 4: Compare Traces
```
You: "Compare trace abc123 with xyz789"

Claude Code will:
1. Fetch both traces
2. Compare:
   - Execution times
   - Token usage
   - Cache efficiency
   - Tool call patterns
   - Success/failure status
3. Identify which approach is more efficient
4. Explain differences
```

### Example 5: Debug Failed Query
```
You: "Why did trace abc123 fail?"

Claude Code will:
1. Fetch the trace
2. Identify the failure point
3. Show error messages
4. Analyze context leading to failure
5. Suggest fixes
```

## Verification Commands

To verify the setup in a new Claude Code session:

1. **Check MCP Status**:
   ```
   /mcp
   ```
   Should show LangSmith server and tools

2. **List Available Tools**:
   ```
   You: "What LangSmith tools do you have access to?"
   ```

3. **Test Basic Functionality**:
   ```
   You: "Get statistics for the netbox-agent project"
   ```

## Integration with netbox_agent.py

### Current Setup:
- ✅ netbox_agent.py is already configured to send traces to LangSmith
- ✅ Environment variables set in `.env` file:
  - `LANGSMITH_API_KEY`
  - `LANGCHAIN_TRACING_V2=true`
  - `LANGCHAIN_PROJECT=netbox-agent`

### Workflow:
1. You run netbox_agent.py
2. Query executes normally
3. Trace automatically sent to LangSmith
4. You can view in LangSmith web UI OR
5. Ask Claude Code to analyze the trace

### No Code Changes Required:
- netbox_agent.py - No modifications needed
- prompts.py - No changes
- All existing code works as before

## Troubleshooting

### If MCP server doesn't show up:
```bash
# Check configuration
claude mcp list

# Should show:
# langsmith: langsmith-mcp-server  - ✓ Connected
```

### If tools aren't available:
1. Restart Claude Code session
2. Run `/mcp` to verify server is loaded
3. Check server health: `claude mcp get langsmith`

### To remove (if needed):
```bash
claude mcp remove langsmith -s user
```

### To reinstall:
```bash
pipx install langsmith-mcp-server --force
claude mcp add --transport stdio --scope user langsmith \
  --env LANGSMITH_API_KEY=YOUR_LANGSMITH_API_KEY_HERE \
  -- langsmith-mcp-server
```

## What This Enables

### For NetBox Agent Development:
- **Performance Optimization**: Identify slow sub-agents
- **Cache Tuning**: Analyze cache hit rates, optimize prompt caching
- **Cost Tracking**: Monitor token usage per query type
- **Debugging**: Investigate failed queries and tool errors
- **Pattern Analysis**: Compare different query strategies
- **Sub-Agent Efficiency**: Measure cross-domain coordination overhead

### General Benefits:
- Works with any LangChain/LangGraph code using LangSmith tracing
- No need to manually check LangSmith web UI
- Programmatic analysis and comparisons
- Historical performance trends
- Automated debugging assistance

## Cost Information

### LangSmith Free Tier:
- 5,000 base traces/month - FREE
- 14-day retention
- Full API access (no restrictions)
- MCP server fully supported

### Current Usage:
You're already using LangSmith for tracing, so no additional costs. The MCP server just provides programmatic access to the same data.

## Files Modified

- `~/.claude.json` - Added LangSmith MCP server configuration
- No other files changed

## Next Steps

1. **Start a new Claude Code session**
2. **Verify with**: `/mcp` command
3. **Test with**: "Get stats for netbox-agent project"
4. **Run some netbox queries** to generate traces
5. **Ask Claude Code to analyze** the traces

## Success Criteria ✅

- [x] langsmith-mcp-server installed (v0.0.7)
- [x] MCP server configured in Claude Code
- [x] Server shows "✓ Connected" status
- [x] Available in user scope (all projects)
- [x] API key configured
- [ ] Verified in new Claude Code session (test this next!)
- [ ] Successfully fetched and analyzed a trace (test this next!)

## Documentation

- Official Repo: https://github.com/langchain-ai/langsmith-mcp-server
- LangSmith Docs: https://docs.smith.langchain.com
- Claude Code MCP Guide: https://docs.claude.com/en/docs/claude-code/mcp

---

**Setup completed on**: 2025-10-12
**By**: Claude Code
**Status**: Ready for use in future sessions! 🎉