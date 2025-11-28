# NetBox Infrastructure Query Agent

A production-grade AI agent for querying and analyzing NetBox infrastructure data using the DeepAgents framework with MCP (Model Context Protocol) integration.

## Overview

This agent demonstrates advanced patterns for building efficient, context-aware infrastructure management agents. It uses semantic understanding of network relationships to answer complex queries about data centers, devices, IP addresses, and other NetBox objects.

### Key Features

- **90% Token Reduction**: Field filtering optimization reduces tokens from 5,000 to 500 per query
- **MCP Integration**: Uses NetBox MCP Server v1.0.0 with 4 generic tools
- **Prompt Caching**: 84%+ cache hit rate for system prompts and tool schemas
- **Interactive CLI**: Async execution with streaming responses
- **Production-Tested**: Field patterns validated in real-world infrastructure scenarios

## Requirements

### NetBox Instance

You need access to a NetBox instance with:
- NetBox API endpoint URL
- API token with read permissions

### Environment Setup

```bash
# Set NetBox credentials
export NETBOX_URL="http://your-netbox-instance:8000"
export NETBOX_TOKEN="your-api-token-here"

# Optional: Set Anthropic API key (if not using default)
export ANTHROPIC_API_KEY="your-key-here"
```

### Dependencies

The agent requires:
- Python 3.10+
- DeepAgents framework
- NetBox MCP Server v1.0.0
- LangChain v1.0+ (for SummarizationMiddleware)

Install from repository root:
```bash
pip install -e .
```

## Usage

### Interactive Mode

```bash
cd examples/netbox
python netbox_agent.py
```

The agent will start an interactive CLI where you can ask questions like:

```
Query: Show all devices at site DM-Scranton with their IP addresses
Query: What racks are available in the Akron data center?
Query: List all active circuits for tenant Dunder Mifflin
Query: Show me the network topology for device core-router-01
```

Type `exit` or `quit` to stop.

### Example Queries

**Device Information:**
```
Show device sw-floor2-001 with its interfaces and IP addresses
```

**Site Analysis:**
```
What's the rack utilization at site DM-Buffalo?
```

**IP Address Management:**
```
Find all available IP addresses in prefix 10.1.5.0/24
```

**Cross-Domain Queries:**
```
Show infrastructure summary for tenant Dunder Mifflin across all sites
```

## Architecture Highlights

### Token Optimization Strategy

The agent implements multiple optimization layers:

1. **Field Filtering** (90% reduction):
   ```python
   # Only request needed fields, not full objects
   fields=["id", "name", "status", "device_type", "site"]
   ```

2. **Generic Tools** (800-1,600 tokens saved):
   - 4 tools instead of 62 specialized ones
   - `netbox_get_objects`, `netbox_get_object_by_id`, `netbox_get_changelogs`, `netbox_search_objects`

3. **Message Trimming** (50-60% reduction):
   - Keeps recent context, trims old history
   - Target: 15-20k prompt tokens per call (down from 40k+)

4. **Prompt Caching** (70% cost reduction):
   - System prompts cached with 1-hour TTL
   - 84%+ cache hit rate in production

### MCP Integration Pattern

The agent uses a singleton MCP session with stdio communication:
```python
mcp_server = MCPServer(
    command="uv",
    args=["--directory", NETBOX_MCP_SERVER_DIR, "run", "netbox-mcp-server"],
    env={
        "NETBOX_URL": os.getenv("NETBOX_URL"),
        "NETBOX_TOKEN": os.getenv("NETBOX_TOKEN"),
    }
)
```

Session lifecycle:
1. Initialize before any tool calls
2. Maintain persistent connection during agent lifecycle
3. Clean up on exit

### Design Decisions

**No Sub-Agents**: The agent uses direct sequential execution instead of sub-agent delegation because:
- NetBox queries are self-contained (no long-horizon dependencies)
- No benefit from parallel exploration (linear data retrieval)
- Context pollution not occurring (tool results naturally focused)

See `/docs/netbox/reports/NO_SUBAGENTS_RATIONALE.md` for detailed analysis.

**Strategic Planning**: Uses `write_todos` tool only for complex multi-step tasks (3+ steps) to balance planning overhead vs execution efficiency.

## Project Structure

```
examples/netbox/
├── netbox_agent.py          # Main agent implementation
├── prompts.py               # System prompts and instructions
├── README.md                # This file
└── venv/                    # Virtual environment
```

## Documentation

Comprehensive documentation available in `/docs/netbox/`:

- **reports/** - Architecture and design analysis
  - `NETBOX_AGENT_COMPREHENSIVE_REPORT.md` - Complete architecture
  - `NO_SUBAGENTS_RATIONALE.md` - Design decision rationale
  - `README_CACHING.md` - Prompt caching implementation

- **analysis/** - Performance and optimization studies
  - `TOOL_REMOVAL_RESULTS.md` - Token optimization findings
  - `VALIDATION_RESULTS_SUMMARY.md` - Performance validation
  - `REFACTORING_RESULTS.md` - Code refactoring outcomes

- **migrations/** - Integration and setup guides
  - `SIMPLEMCP_MIGRATION_COMPLETE.md` - MCP integration approach
  - `LANGSMITH_MCP_SETUP_COMPLETE.md` - LangSmith observability setup

## Performance Metrics

**Token Usage:**
- Baseline: 40k+ prompt tokens per LLM call
- Optimized: 15-20k prompt tokens (50-60% reduction)
- Cache hit rate: 84%+ on repeated queries

**Query Performance:**
- Simple queries: 2-4 tool calls, 5-15 seconds
- Complex cross-domain queries: 5-10 tool calls, 15-45 seconds
- Multi-site aggregation: Bulk queries instead of iteration (75 calls → 5 calls)

## Troubleshooting

### MCP Server Connection Issues

If you see errors about MCP server connection:
1. Verify NetBox credentials are set correctly
2. Check NetBox instance is accessible
3. Ensure NetBox MCP Server is installed: `uv sync` in MCP server directory

### Invalid Field Errors (400 Bad Request)

If you see errors about invalid field names:
- The agent may be hallucinating field names not in NetBox schema
- Check `/docs/netbox/analysis/` for validated field patterns
- Report persistent issues (this helps improve the agent)

### High Token Usage

If token usage remains high:
- Check LangSmith traces for message accumulation
- Verify prompt caching is working (look for cache hits)
- Consider adjusting message trimming thresholds

## Contributing

This agent is part of the DeepAgents framework research project. Lessons learned:

1. **Context engineering is primary optimization lever** (not model choice)
2. **Generic tools > Specialized tools** (reduces token overhead)
3. **Field filtering is non-negotiable** (90% token reduction)
4. **Sub-agents aren't always beneficial** (use when truly needed)
5. **Prompt caching requires deterministic prompts** (stable prefixes)

See `/home/ola/dev/rnd/deepagents/context-engineering-report.md` for comprehensive findings.

## License

Part of the DeepAgents open-source project.
