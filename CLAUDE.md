# Claude Code Guidance for DeepAgents Repository

This file provides guidance for Claude Code to operate effectively in this repository.

## Project Goals and Motivation

DeepAgents is a framework designed to solve the fundamental limitations of "shallow" AI agents that simply call tools in a loop. The project aims to create agents capable of handling complex, long-horizon tasks by implementing four key architectural components proven successful in advanced agent systems like Claude Code.

### Core Problem Being Solved
Traditional agents struggle with:
- Complex, multi-step tasks requiring sustained attention
- Long-term planning and goal maintenance
- Task decomposition and specialization
- Context management across extended interactions

### Four Pillars of Deep Agents
1. **Detailed System Prompt**: Complex, nuanced instructions with behavioral examples
2. **Planning Tool**: Maintains focus and tracks progress across long-horizon tasks
3. **Sub-Agents**: Specialized agents with context quarantine for task decomposition
4. **File System Access**: Persistent memory and workspace for collaboration

The framework enables agents to "go deeper on topics" by spinning up specialized sub-agents focused on individual tasks, moving beyond shallow tool-calling patterns to sophisticated task execution.

## Build, Lint, and Test Commands

```bash
# Install the package in development mode
pip install -e .

# Run example research agent (requires TAVILY_API_KEY environment variable)
cd examples/research
python research_agent.py

# Test concurrent todo functionality
python test_concurrent_todos.py

# Run specific examples
python example_with_env.py
python research_agent_working_final.py
python test_concurrent_todos.py
```

## High-Level Architecture

DeepAgents is a LangGraph-based framework for creating "deep agents" - LLM agents with planning capabilities, sub-agent spawning, file system access, and detailed prompts. The architecture mirrors Claude Code's approach but in a general-purpose way.

### Core Components (src/deepagents/)

- **graph.py:91** - Main agent builder that creates React agents with task delegation capabilities
- **sub_agent.py:38** - Sub-agent implementation expecting tool names from tools_by_name dictionary
- **builder.py** - Configurable agent factory for deployment scenarios
- **tools.py** - Built-in tools: write_todos, write_file, read_file, ls, edit_file
- **state.py** - DeepAgentState schema for LangGraph state management
- **prompts.py** - System prompts heavily inspired by Claude Code's approach

### Key Patterns

**Task Delegation Pattern**: Main agents use `_create_task_tool()` at src/deepagents/sub_agent.py to create specialized sub-agents with filtered tool sets. Framework handles large tool sets through specialized sub-agents while keeping main agents lightweight with only essential tools.

**Context Quarantine**: Sub-agents isolate specialized work to prevent context pollution of main agent.

### Built-in Tools

All agents get 5 built-in tools by default:
- `write_todos` - Planning and task management
- `write_file`, `read_file`, `ls`, `edit_file` - Virtual filesystem operations
- `task` - Sub-agent delegation (automatically created)

### MCP Integration

Framework supports MCP (Model Context Protocol) tools via langchain-mcp-adapters. Use `async_create_deep_agent` for MCP tools since they're async.

## Important Implementation Details

**Rate Limit Handling**: When working with large tool sets (50+ tools), use the task delegation pattern. Main agent gets only task tool, specialized sub-agents get filtered tool subsets.

**Framework Alignment**: Always prefer using built-in `task` tool over custom sub-agent implementations. The framework's `_create_task_tool()` method handles tool distribution automatically.

**Virtual Filesystem**: Built-in file tools use LangGraph state, not real filesystem. Files persist in agent state between invocations.

**Model Configuration**: Default model is "claude-sonnet-4-20250514". Supports per-subagent model override via model_settings.

**Token Management:** Long-running agents accumulate context. Implement message trimming via `pre_model_hook` with `trim_messages` for 50-60% token reduction. See Token Usage & Context Management section below.

**MCP Integration Best Practices:**
- Use simple, generic tools (3-5 tools) over many specialized tools (50+ tools)
- Manage MCP session lifecycle via singleton pattern
- Initialize session before any tool calls
- Clean up sessions on exit
- See `examples/netbox/netbox_agent.py` for reference implementation

## LangChain v1 Migration Strategy

**Status**: The DeepAgents framework is in the process of migrating to LangChain v1 core to achieve 60-70% reduction in prompt token usage through middleware architecture and improved message management.

### Why v1 Now (Not Waiting for Stable)

- **Current problem**: 40k+ prompt tokens per LLM call, 99.1% prompt vs 0.9% completion
- **V1 solution**: SummarizationMiddleware and message management can reduce to 15k tokens
- **Timeline**: Using v1-alpha now (October stable release timeline not acceptable for optimization needs)
- **Risk mitigation**: Extensive validation with NetBox and research agents, all tests must pass

### Breaking Changes from v0 to v1

**API Changes:**
- `create_react_agent` → `create_agent` (new API in langchain.agents)
- `recursion_limit` pattern → middleware-based execution control
- Legacy packages moved to `langchain-classic` (v0 reference only)

**Installation:**
```bash
# Install v1-alpha packages
pip install langchain@alpha langchain-core@alpha

# Verify installation
pip show langchain langchain-core
```

**Key V1 Features:**
1. **SummarizationMiddleware**: Automatic context compression before model calls
2. **Middleware hooks**: before_model, after_model, before_tool, after_tool
3. **Structured output**: Enhanced type safety for agent responses
4. **Message management**: Built-in trimming and summarization strategies

### Migration Path

1. **Phase 1**: Install v1-alpha packages, test compatibility
2. **Phase 2**: Update src/deepagents/graph.py to use create_agent API
3. **Phase 3**: Implement SummarizationMiddleware or pre_model_hook with trim_messages
4. **Phase 4**: Validate with real-world queries (NetBox, research agents)
5. **Phase 5**: Measure token reduction via LangSmith traces

### When to Use v1 vs v0

**Use V1 for:**
- New agent implementations (get token benefits from day one)
- Agents with high token usage (>30k prompt tokens per call)
- Projects requiring long-running conversations
- Production systems where cost optimization matters

**Use V0 (temporary) for:**
- Quick prototypes where token usage not yet measured
- Compatibility testing during migration
- Reference implementations (will be deprecated)

**Reference:** See `initial-langchain-v1-optimization.md` for detailed migration requirements and `examples/netbox/TOOL_REMOVAL_RESULTS.md` for token analysis.

## Middleware Architecture Patterns

LangChain v1 introduces a powerful middleware system for managing agent execution, replacing the recursion_limit pattern with more sophisticated context and execution control.

### SummarizationMiddleware (Primary Pattern)

**Purpose**: Automatically compresses conversation history before each model call, preventing unbounded context growth.

**Configuration:**
```python
from langchain.middleware import SummarizationMiddleware

middleware = SummarizationMiddleware(
    max_tokens=15000,              # Target token count (down from 40k)
    keep_system_prompt=True,       # Always preserve system instructions
    keep_last_n_tool_calls=3,      # Keep recent tool context
    summarize_older=True,          # Compress older messages
    summary_instruction="Concisely summarize the conversation history, preserving key findings and decisions."
)
```

**When to use:**
- Agents with long-running conversations (10+ turns)
- High token usage scenarios (>30k prompt tokens)
- Multi-step tasks requiring context across many tool calls

### Middleware Hooks (Advanced Pattern)

**Available hooks:**
- `before_model`: Executed before each LLM call (trim messages, validate state)
- `after_model`: Executed after each LLM response (process output, update state)
- `before_tool`: Executed before each tool call (validate parameters, log)
- `after_tool`: Executed after each tool response (trim results, extract key data)

**Example - Message Trimming Hook:**
```python
from langchain_core.messages import trim_messages

def before_model_hook(state):
    """Trim messages before sending to LLM."""
    messages = state.get("messages", [])

    # Keep system prompt + last 3 tool calls + current query
    trimmed = trim_messages(
        messages,
        strategy="last",
        token_counter=len,  # Or use actual token counter
        max_tokens=15000,
        include_system=True,
        start_on="human",
    )

    return {"messages": trimmed}
```

**Example - Tool Result Compression Hook:**
```python
def after_tool_hook(state, tool_result):
    """Compress verbose tool results."""
    # For large API responses, keep only essential fields
    if len(str(tool_result)) > 5000:
        # Extract key data, discard verbose details
        return extract_essential_fields(tool_result)
    return tool_result
```

### Pre-Model Hook Pattern (Current v0 Approach)

The current DeepAgents implementation uses `pre_model_hook` with `trim_messages` utility. This pattern works in both v0 and v1, but v1's SummarizationMiddleware is more sophisticated.

**Current pattern:**
```python
from langchain_core.messages import trim_messages

def pre_model_hook(state):
    messages = trim_messages(
        state["messages"],
        strategy="last",
        max_tokens=15000,
        include_system=True,
    )
    return {"messages": messages}

# In agent creation
create_react_agent(  # v0
    model,
    tools=tools,
    pre_model_hook=pre_model_hook,  # Applied before each LLM call
)
```

### When to Use Each Pattern

**SummarizationMiddleware** (v1 recommended):
- Automatic, intelligent context compression
- Preserves semantic meaning through summarization
- Best for long-running, complex conversations
- Requires v1-alpha installation

**Manual trim_messages Hook** (v0 compatible):
- Simple, predictable token reduction
- Keep last N messages strategy
- Works in current stable LangGraph
- Good for straightforward trimming needs

**Custom Middleware** (advanced):
- Domain-specific context management
- Complex state transformations
- Integration with external systems (logging, monitoring)
- Full control over execution flow

### Migration from recursion_limit

**Old pattern (v0):**
```python
agent = create_deep_agent(...).with_config({"recursion_limit": 1000})
```

**New pattern (v1):**
```python
agent = create_agent(
    ...,
    middleware=[
        SummarizationMiddleware(max_tokens=15000),
        ExecutionControlMiddleware(max_steps=100),
    ]
)
```

Middleware provides finer-grained control over execution, separating context management from step limits.

**Reference:** See v1 docs at https://docs.langchain.com/oss/python/releases/langchain-v1 for complete middleware API.

## Token Usage & Context Management

**Critical Finding:** Context accumulation is the primary cost driver in long-running agent loops.

### Token Distribution Pattern
- **Prompt tokens:** 99.1% of total tokens (context/history sent to LLM)
- **Completion tokens:** 0.9% of total tokens (LLM responses)

This means the problem is usually **not** high token generation, but excessive **input size** (context accumulation).

### Root Causes of High Token Usage

1. **Message History Accumulation**
   - Every LLM call receives full conversation history by default
   - Tool results accumulate in state["messages"] without trimming
   - System prompt + tool schemas repeated each iteration
   - Can reach 40k+ prompt tokens per LLM call

2. **Tool Result Verbosity**
   - Large API responses (e.g., NetBox objects) stored in full
   - Old tool results rarely referenced but always sent to LLM
   - Keeping last 2-3 tool results usually sufficient

3. **Over-Planning**
   - Excessive `write_todos` calls add message overhead
   - Balance planning benefits vs token cost

### Optimization Strategies

**1. Message Trimming (Recommended)**
- Use `pre_model_hook` with `trim_messages` utility
- Available in current LangGraph stable release
- Keeps recent context, trims old history
- Expected: 50-60% token reduction
- Example: 40k → 15-20k prompt tokens per call

**2. Prompt Caching (Already Supported)**
- System prompts and tool schemas automatically cached
- Can achieve 80%+ cache hit rate
- Reduces effective cost by ~70% on cached portions
- Use extended-cache-ttl for best results

**3. Tool Design**
- Fewer, generic tools better than many specialized tools
- Example: 3 generic tools vs 62 specialized = 800-1,600 tokens saved
- Design tools to return concise, focused results

**4. Strategic Planning**
- Use `write_todos` for complex tasks (3+ steps)
- Skip planning for simple queries (1-2 steps)
- Monitor planning overhead vs execution efficiency

### Implementation Guide

See `examples/netbox/` for token optimization case study:
- Baseline: 40k avg prompt tokens, 287k total per query
- After tool reduction: Mixed results (2/3 improved, 1/3 regressed)
- Solution: Add message trimming via pre_model_hook
- Expected final: <20k prompt tokens, <150k total per query

**Reference Documents:**
- `examples/netbox/TOOL_REMOVAL_RESULTS.md` - Tool optimization analysis
- `examples/netbox/VALIDATION_RESULTS_SUMMARY.md` - Performance metrics

## Key Files to Understand

### Framework Core
- **src/deepagents/graph.py** - Agent builder, creates React agents with task delegation
- **src/deepagents/sub_agent.py** - Sub-agent implementation and task tool creation
- **src/deepagents/prompts.py** - System prompts, BASE_AGENT_PROMPT template
- **src/deepagents/tools.py** - Built-in tools (write_todos, file operations)
- **README.md** - Comprehensive usage documentation and examples

### Example Implementations

**NetBox Agent (Primary Reference - Most Complex):**
- **examples/netbox/netbox_agent.py** - Production-grade infrastructure query agent
  - MCP integration (3 generic tools)
  - Interactive CLI, async execution
  - Strategic planning and coordination
  - Prompt caching implementation
- **examples/netbox/NETBOX_AGENT_COMPREHENSIVE_REPORT.md** - Complete architecture
- **examples/netbox/TOOL_REMOVAL_RESULTS.md** - Token optimization findings
- **examples/netbox/NO_SUBAGENTS_RATIONALE.md** - Design decisions

**Research Agent (Simpler Reference):**
- **examples/research/research_agent.py** - Research agent with sub-agent delegation
- Demonstrates basic task delegation patterns
- Simpler than NetBox agent, good starting point

**Other Examples:**
- **test_concurrent_todos.py** - Concurrent task handling patterns

## NetBox Agent Example (Primary Reference Implementation)

The NetBox agent (`examples/netbox/netbox_agent.py`) is the most comprehensive reference implementation in the repository, demonstrating advanced agent patterns in a real-world infrastructure management context.

### Key Characteristics

**Complexity:** Production-grade agent with:
- MCP integration (3 generic tools via simple MCP server)
- Interactive CLI with async execution
- Strategic planning and cross-domain coordination
- Prompt caching for cost optimization
- Extensive validation and optimization work

**Documentation:** 15+ markdown files in `examples/netbox/`:
- `NETBOX_AGENT_COMPREHENSIVE_REPORT.md` - Complete architecture analysis
- `TOOL_REMOVAL_RESULTS.md` - Token optimization findings
- `NO_SUBAGENTS_RATIONALE.md` - Design decision rationale
- `VALIDATION_RESULTS_SUMMARY.md` - Performance validation
- `SIMPLEMCP_MIGRATION_COMPLETE.md` - MCP integration approach

### Lessons Learned (Critical for Future Work)

1. **MCP Integration Pattern**
   - Simple 3-tool approach (get_objects, get_object_by_id, get_changelogs) outperforms 62 specialized tools
   - Generic tools reduce token overhead by 800-1,600 tokens per request
   - Session management via singleton pattern with stdio communication

2. **Token Optimization Insights**
   - Context accumulation is the primary cost driver (99.1% prompt tokens, 0.9% completion)
   - Message trimming via `pre_model_hook` can reduce tokens by 50-60%
   - Prompt caching provides 84%+ cache hit rate when properly implemented
   - Tool result verbosity matters - keep last 2-3 results, trim older history

3. **Sub-Agent Usage Patterns**
   - Not always beneficial - removed from NetBox agent (0 usage in validation)
   - Use only when true context isolation needed
   - Avoid for simple data queries (self-contained, no long-horizon dependencies)

4. **Planning Tool Guidelines**
   - `write_todos` valuable for 3+ step tasks
   - Over-planning can regress performance (Query 2: 0→5 write_todos = +73% duration)
   - Balance between planning overhead and execution efficiency

### When to Study NetBox Agent

- **Building MCP-integrated agents** - Study MCP session management, tool design
- **Production deployment** - Study error handling, async patterns, CLI design
- **Token optimization** - Study caching strategy, tool reduction rationale
- **Complex domain agents** - Study cross-domain coordination, strategic planning

## Development Notes

This repository implements the open-source `deepagents` package, making advanced agent patterns accessible for building domain-specific applications. The project was primarily inspired by Claude Code and represents an attempt to understand and generalize Claude Code's sophisticated agent architecture.

### Research and Validation
The framework has been validated through complex real-world scenarios:
- **Large-Scale Tool Integration**: Successfully handles complex tool sets through intelligent delegation patterns
- **Rate Limit Mitigation**: Demonstrates how task delegation prevents API rate limits
- **Context Quarantine**: Proves sub-agents can isolate specialized work without polluting main agent context

### Framework Philosophy
DeepAgents makes sophisticated agent capabilities accessible by providing generalized implementations of patterns that previously required custom engineering. The goal is enabling developers to create specialized "deep" agents for their specific domains without rebuilding core agent infrastructure.

Available in both Python and JavaScript/TypeScript, the framework represents a bridge between simple tool-calling agents and sophisticated task execution systems.

### 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Organize code into clearly separated modules**, grouped by feature or responsibility.  
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use python_dotenv and load_env()** for environment variables.

### 🧪 Testing & Reliability
- **Always create Pytest unit tests for new features** (functions, classes, routes, etc).
- **After updating any logic**, check whether existing unit tests need to be updated. If so, do it.
- **Tests should live in a `/tests` folder** mirroring the main app structure.
  - Include at least:
    - 1 test for expected use
    - 1 edge case
    - 1 failure case

### 📎 Style & Conventions
- **Use Python** as the primary language.
- **Follow PEP8**, use type hints, and format with `black`.
- Use `FastAPI` for APIs and `SQLAlchemy` or `SQLModel` for ORM if applicable.
- Write **docstrings for every function** using the Google style:
  ```python
  def example():
      """
      Brief summary.

      Args:
          param1 (type): Description.

      Returns:
          type: Description.
      """
  ```

### 📚 Documentation & Explainability
- **Update `README.md`** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.
- When writing complex logic, **add an inline `# Reason:` comment** explaining the why, not just the what.

### 🧠 AI Behavior Rules
- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified Python packages.
- **Always confirm file paths and module names** exist before referencing them in code or tests.
- **Never delete or overwrite existing code** unless explicitly instructed to.

