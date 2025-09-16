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

## Key Files to Understand

- **examples/research/research_agent.py** - Complete research agent with sub-agent delegation
- **src/deepagents/graph.py** - Core agent construction logic
- **test_concurrent_todos.py** - Example of concurrent task handling
- **README.md** - Comprehensive usage documentation and examples

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

