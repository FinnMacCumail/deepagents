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

