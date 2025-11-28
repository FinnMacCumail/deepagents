# NetBox Infrastructure Chatbot

An AI-powered chatbot for querying and analyzing NetBox infrastructure data. Ask natural language questions about your data centers, devices, IP addresses, racks, and circuits - get instant, accurate answers.

**Powered by the DeepAgents framework + NetBox MCP Server v1.0.0**

## Quick Start

```bash
# Install
git clone https://github.com/yourusername/deepagents.git
cd deepagents
pip install -e .

# Set NetBox credentials
export NETBOX_URL="http://your-netbox-instance:8000"
export NETBOX_TOKEN="your-api-token-here"

# Run the chatbot
cd examples/netbox
python netbox_agent.py
```

**Example queries:**
```
Query: Show all devices at site DM-Scranton with their IP addresses
Query: What racks are available in the Akron data center?
Query: List all active circuits for tenant Dunder Mifflin
Query: Show me the network topology for device core-router-01
```

Type `exit` or `quit` to stop the chatbot.

## Key Features

### **90% Token Reduction**
Field filtering optimization reduces tokens from 5,000 to 500 per query, dramatically lowering costs and improving response times.

###  **MCP Integration**
Uses NetBox MCP Server v1.0.0 with 4 generic tools (`netbox_get_objects`, `netbox_get_object_by_id`, `netbox_get_changelogs`, `netbox_search_objects`) instead of 62 specialized tools.

### **Prompt Caching**
Achieves 84%+ cache hit rate for system prompts and tool schemas, providing 70% cost reduction on cached portions.

### **Interactive CLI**
Async execution with streaming responses provides real-time feedback as the agent processes complex queries.

### **Production-Tested**
Field patterns and optimization strategies validated in real-world infrastructure management scenarios.

## How It Works

The NetBox chatbot combines two key technologies:

### 1. DeepAgents Framework
Provides the "deep agent" architecture with:
- **Planning tool** - Task decomposition and progress tracking
- **Context management** - Message trimming and summarization
- **Tool orchestration** - Intelligent tool selection and execution
- **Semantic understanding** - Natural language query interpretation

### 2. NetBox MCP Server
Exposes NetBox API as Model Context Protocol (MCP) tools with:
- **Field filtering** - Select only needed fields (90% token reduction)
- **Generic tools** - 4 tools instead of 62 (800-1,600 tokens saved)
- **Pagination** - Handle large datasets efficiently
- **Real-time data** - Direct access to NetBox instance

### Architecture Flow

```
User Query → DeepAgents Framework → NetBox MCP Tools → NetBox API
              ↓                        ↓
              Planning                 Field Filtering
              Context Management       Data Retrieval
              ↓                        ↓
              ← Formatted Response ← Processed Data
```

## About DeepAgents Framework

Using an LLM to call tools in a loop is the simplest form of an agent. This architecture, however, can yield agents that are "shallow" and fail to plan and act over longer, more complex tasks. Applications like "Deep Research", "Manus", and "Claude Code" have gotten around this limitation by implementing a combination of four things: a **planning tool**, **sub agents**, access to a **file system**, and a **detailed prompt**.

`deepagents` is a Python package that implements these components in a general-purpose way so that you can easily create a Deep Agent for your application. The NetBox chatbot is a production implementation of this framework.

**Acknowledgements:** This project was primarily inspired by Claude Code, and initially was largely an attempt to see what made Claude Code general purpose, and make it even more so.

### Four Pillars of Deep Agents

1. **Detailed System Prompt** - Complex, nuanced instructions with behavioral examples
2. **Planning Tool** - Maintains focus and tracks progress across long-horizon tasks
3. **Sub-Agents** - Specialized agents with context quarantine for task decomposition
4. **File System Access** - Persistent memory and workspace for collaboration

## Documentation & Resources

### NetBox Chatbot
- **[NetBox Agent Guide](examples/netbox/README.md)** - Complete usage guide and examples
- **[Architecture Reports](examples/netbox/docs/netbox/reports/)** - Design decisions and rationale
  - [NO_SUBAGENTS_RATIONALE.md](examples/netbox/docs/netbox/reports/NO_SUBAGENTS_RATIONALE.md) - Why sub-agents aren't always needed
  - [NETBOX_AGENT_COMPREHENSIVE_REPORT.md](examples/netbox/docs/netbox/reports/NETBOX_AGENT_COMPREHENSIVE_REPORT.md) - Complete architecture analysis
  - [README_CACHING.md](examples/netbox/docs/netbox/reports/README_CACHING.md) - Prompt caching implementation
- **[Performance Analysis](examples/netbox/docs/netbox/analysis/)** - Token optimization and validation
  - [TOOL_REMOVAL_RESULTS.md](examples/netbox/docs/netbox/analysis/TOOL_REMOVAL_RESULTS.md) - Token optimization findings
  - [VALIDATION_RESULTS_SUMMARY.md](examples/netbox/docs/netbox/analysis/VALIDATION_RESULTS_SUMMARY.md) - Performance metrics
- **[Migration Guides](examples/netbox/docs/netbox/migrations/)** - MCP integration and setup
  - [SIMPLEMCP_MIGRATION_COMPLETE.md](examples/netbox/docs/netbox/migrations/SIMPLEMCP_MIGRATION_COMPLETE.md) - MCP integration approach

### DeepAgents Framework
- **[Agent Development Playbook](docs/guides/AGENTS.md)** - Build custom agents with best practices
- **[Context Engineering Report](docs/guides/context-engineering-report.md)** - Optimization strategies and production insights
- **[Framework Development](docs/development/)** - Migration guides and technical reports
  - [initial-langchain-v1-optimization.md](docs/development/initial-langchain-v1-optimization.md) - LangChain v1 migration
  - [MIDDLEWARE_ALIGNMENT_REPORT.md](docs/development/MIDDLEWARE_ALIGNMENT_REPORT.md) - Middleware architecture
  - [FETCH_MCP_USAGE.md](docs/development/FETCH_MCP_USAGE.md) - MCP server setup guide

## Installation

Install the DeepAgents framework:

```bash
pip install deepagents
```

For the NetBox chatbot, clone this repository and install in development mode:

```bash
git clone https://github.com/yourusername/deepagents.git
cd deepagents
pip install -e .
```

## Advanced Usage - Building Custom Deep Agents

The NetBox chatbot demonstrates one application of the DeepAgents framework. You can use the same framework to build agents for other domains.

### Basic Example - Research Agent

(Requires `pip install tavily-python`)

```python
import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# Search tool
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

# Agent instructions
research_instructions = """You are an expert researcher. Your job is to conduct thorough research, and then write a polished report.

You have access to a few tools.

## `internet_search`

Use this to run an internet search for a given query. You can specify the number of results, the topic, and whether raw content should be included.
"""

# Create the agent
agent = create_deep_agent(
    [internet_search],
    research_instructions,
)

# Invoke the agent
result = agent.invoke({"messages": [{"role": "user", "content": "what is langgraph?"}]})
```

See [examples/research/research_agent.py](examples/research/research_agent.py) for a more complex example.

The agent created with `create_deep_agent` is just a LangGraph graph - so you can interact with it (streaming, human-in-the-loop, memory, studio) in the same way you would any LangGraph agent.

### Creating a Custom Deep Agent

There are three parameters you can pass to `create_deep_agent` to create your own custom deep agent.

#### `tools` (Required)

The first argument to `create_deep_agent` is `tools`.
This should be a list of functions or LangChain `@tool` objects.
The agent (and any subagents) will have access to these tools.

#### `instructions` (Required)

The second argument to `create_deep_agent` is `instructions`.
This will serve as part of the prompt of the deep agent.
Note that there is a [built in system prompt](src/deepagents/prompts.py) as well, so this is not the *entire* prompt the agent will see.

#### `subagents` (Optional)

A keyword-only argument to `create_deep_agent` is `subagents`.
This can be used to specify any custom subagents this deep agent will have access to.
You can read more about why you would want to use subagents in the [context quarantine](https://www.dbreunig.com/2025/06/26/how-to-fix-your-context.html#context-quarantine) article.

`subagents` should be a list of dictionaries, where each dictionary follow this schema:

```python
class SubAgent(TypedDict):
    name: str
    description: str
    prompt: str
    tools: NotRequired[list[str]]
    model_settings: NotRequired[dict[str, Any]]

class CustomSubAgent(TypedDict):
    name: str
    description: str
    graph: Runnable
```

**SubAgent fields:**
- **name**: This is the name of the subagent, and how the main agent will call the subagent
- **description**: This is the description of the subagent that is shown to the main agent
- **prompt**: This is the prompt used for the subagent
- **tools**: This is the list of tools that the subagent has access to. By default will have access to all tools passed in, as well as all built-in tools.
- **model_settings**: Optional dictionary for per-subagent model configuration (inherits the main model when omitted).

**CustomSubAgent fields:**
- **name**: This is the name of the subagent, and how the main agent will call the subagent
- **description**: This is the description of the subagent that is shown to the main agent
- **graph**: A pre-built LangGraph graph/agent that will be used as the subagent

##### Using SubAgent

```python
research_subagent = {
    "name": "research-agent",
    "description": "Used to research more in depth questions",
    "prompt": sub_research_prompt,
}
subagents = [research_subagent]
agent = create_deep_agent(
    tools,
    prompt,
    subagents=subagents
)
```

##### Using CustomSubAgent

For more complex use cases, you can provide your own pre-built LangGraph graph as a subagent:

```python
from langchain.agents import create_agent

# Create a custom agent graph
custom_graph = create_agent(
    your_model,
    system_prompt="You are a specialized agent for data analysis...",
    tools=specialized_tools
)

# Use it as a custom subagent
custom_subagent = {
    "name": "data-analyzer",
    "description": "Specialized agent for complex data analysis tasks",
    "graph": custom_graph
}

subagents = [custom_subagent]
agent = create_deep_agent(
    tools,
    prompt,
    subagents=subagents
)
```

#### `model` (Optional)

By default, `deepagents` uses `"claude-sonnet-4-20250514"`. You can customize this by passing any [LangChain model object](https://python.langchain.com/docs/integrations/chat/).

#### `builtin_tools` (Optional)

By default, a deep agent will have access to a number of [built-in tools](#built-in-tools).
You can change this by specifying the tools (by name) that the agent should have access to with this parameter.

Example:
```python
# Only give agent access to todo tool, none of the filesystem tools
builtin_tools = ["write_todos"]
agent = create_deep_agent(..., builtin_tools=builtin_tools, ...)
```

##### Example: Using a Custom Model

Here's how to use a custom model (like OpenAI's `gpt-oss` model via Ollama):

(Requires `pip install langchain` and then `pip install langchain-ollama` for Ollama models)

```python
from deepagents import create_deep_agent

# ... existing agent definitions ...

model = init_chat_model(
    model="ollama:gpt-oss:20b",
)
agent = create_deep_agent(
    tools=tools,
    instructions=instructions,
    model=model,
    ...
)
```

##### Example: Per-subagent model override (optional)

Use a fast, deterministic model for a critique sub-agent, while keeping a different default model for the main agent and others:

```python
from deepagents import create_deep_agent

critique_sub_agent = {
    "name": "critique-agent",
    "description": "Critique the final report",
    "prompt": "You are a tough editor.",
    "model_settings": {
        "model": "anthropic:claude-3-5-haiku-20241022",
        "temperature": 0,
        "max_tokens": 8192
    }
}

agent = create_deep_agent(
    tools=[internet_search],
    instructions="You are an expert researcher...",
    model="claude-sonnet-4-20250514",  # default for main agent and other sub-agents
    subagents=[critique_sub_agent],
)
```

## Deep Agent Components

The below components are built into `deepagents` and helps make it work for deep tasks off-the-shelf.

### System Prompt

`deepagents` comes with a [built-in system prompt](src/deepagents/prompts.py). This is relatively detailed prompt that is heavily based on and inspired by [attempts](https://github.com/kn1026/cc/blob/main/claudecode.md) to [replicate](https://github.com/asgeirtj/system_prompts_leaks/blob/main/Anthropic/claude-code.md)
Claude Code's system prompt. It was made more general purpose than Claude Code's system prompt.
This contains detailed instructions for how to use the built-in planning tool, file system tools, and sub agents.
Note that part of this system prompt [can be customized](#instructions-required)

Without this default system prompt - the agent would not be nearly as successful at going as it is.
The importance of prompting for creating a "deep" agent cannot be understated.

### Planning Tool

`deepagents` comes with a built-in planning tool. This planning tool is very simple and is based on ClaudeCode's TodoWrite tool.
This tool doesn't actually do anything - it is just a way for the agent to come up with a plan, and then have that in the context to help keep it on track.

### File System Tools

`deepagents` comes with four built-in file system tools: `ls`, `edit_file`, `read_file`, `write_file`.
These do not actually use a file system - rather, they mock out a file system using LangGraph's State object.
This means you can easily run many of these agents on the same machine without worrying that they will edit the same underlying files.

Right now the "file system" will only be one level deep (no sub directories).

These files can be passed in (and also retrieved) by using the `files` key in the LangGraph State object.

```python
agent = create_deep_agent(...)

result = agent.invoke({
    "messages": ...,
    # Pass in files to the agent using this key
    # "files": {"foo.txt": "foo", ...}
})

# Access any files afterwards like this
result["files"]
```

### Sub Agents

`deepagents` comes with the built-in ability to call sub agents (based on Claude Code).
It has access to a `general-purpose` subagent at all times - this is a subagent with the same instructions as the main agent and all the tools that is has access to.
You can also specify [custom sub agents](#subagents-optional) with their own instructions and tools.

Sub agents are useful for ["context quarantine"](https://www.dbreunig.com/2025/06/26/how-to-fix-your-context.html#context-quarantine) (to help not pollute the overall context of the main agent)
as well as custom instructions.

### Built In Tools

By default, deep agents come with five built-in tools:

- `write_todos`: Tool for writing todos
- `write_file`: Tool for writing to a file in the virtual filesystem
- `read_file`: Tool for reading from a file in the virtual filesystem
- `ls`: Tool for listing files in the virtual filesystem
- `edit_file`: Tool for editing a file in the virtual filesystem

These can be disabled via the [`builtin_tools`](#builtintools--optional) parameter.

### Human-in-the-Loop

`deepagents` supports human-in-the-loop approval for tool execution. You can configure specific tools to require human approval before execution using the `interrupt_config` parameter, which maps tool names to `HumanInterruptConfig`.

`HumanInterruptConfig` is how you specify what type of human in the loop patterns are supported.
It is a dictionary with four specific keys:

- `allow_ignore`: Whether the user can skip the tool call
- `allow_respond`: Whether the user can add a text response
- `allow_edit`: Whether the user can edit the tool arguments
- `allow_accept`: Whether the user can accept the tool call

Currently, `deepagents` does NOT support `allow_ignore`

Currently, `deepagents` only support interrupting one tool at a time. If multiple tools are called in parallel, each requiring interrupts, then the agent will error.

Instead of specifying a `HumanInterruptConfig` for a tool, you can also just set `True`. This will set `allow_ignore`, `allow_respond`, `allow_edit`, and `allow_accept` to be `True`.

In order to use human in the loop, you need to have a checkpointer attached.
Note: if you are using LangGraph Platform, this is automatically attached.

Example usage:

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver

# Create agent with file operations requiring approval
agent = create_deep_agent(
    tools=[your_tools],
    instructions="Your instructions here",
    interrupt_config={
        # You can specify a dictionary for fine grained control over what interrupt options exist
        "tool_1": {
            "allow_ignore": False,
            "allow_respond": True,
            "allow_edit": True,
            "allow_accept":True,
        },
        # You can specify a boolean for shortcut
        # This is a shortcut for the same functionality as above
        "tool_2": True,
    }
)

checkpointer= InMemorySaver()
agent.checkpointer = checkpointer
```

#### Approve

To "approve" a tool call means the agent will execute the tool call as is.

This flow shows how to approve a tool call (assuming the tool requiring approval is called):

```python
config = {"configurable": {"thread_id": "1"}}
for s in agent.stream({"messages": [{"role": "user", "content": message}]}, config=config):
    print(s)
# If this calls a tool with an interrupt, this will then return an interrupt
for s in agent.stream(Command(resume=[{"type": "accept"}]), config=config):
    print(s)

```

#### Edit

To "edit" a tool call means the agent will execute the new tool with the new arguments. You can change both the tool to call or the arguments to pass to that tool.

The `args` parameter you pass back should be a dictionary with two keys:

- `action`: maps to a string which is the name of the tool to call
- `args`: maps to a dictionary which is the arguments to pass to the tool

This flow shows how to edit a tool call (assuming the tool requiring approval is called):

```python
config = {"configurable": {"thread_id": "1"}}
for s in agent.stream({"messages": [{"role": "user", "content": message}]}, config=config):
    print(s)
# If this calls a tool with an interrupt, this will then return an interrupt
# Replace the `...` with the tool name you want to call, and the arguments
for s in agent.stream(Command(resume=[{"type": "edit", "args": {"action": "...", "args": {...}}}]), config=config):
    print(s)

```

#### Respond

To "respond" to a tool call means that tool is NOT called. Rather, a tool message is appended with the content you respond with, and the updated messages list is then sent back to the model.

The `args` parameter you pass back should be a string with your response.

This flow shows how to respond to a tool call (assuming the tool requiring approval is called):

```python
config = {"configurable": {"thread_id": "1"}}
for s in agent.stream({"messages": [{"role": "user", "content": message}]}, config=config):
    print(s)
# If this calls a tool with an interrupt, this will then return an interrupt
# Replace the `...` with the response to use all the ToolMessage content
for s in agent.stream(Command(resume=[{"type": "response", "args": "..."}]), config=config):
    print(s)

```

## Async

If you are passing async tools to your agent, you will want to `from deepagents import async_create_deep_agent`

## MCP Integration

The `deepagents` library can be ran with MCP tools. This can be achieved by using the [Langchain MCP Adapter library](https://github.com/langchain-ai/langchain-mcp-adapters).

The NetBox chatbot demonstrates production MCP integration. See [examples/netbox/netbox_agent.py](examples/netbox/netbox_agent.py) for complete implementation.

**NOTE:** will want to use `from deepagents import async_create_deep_agent` to use the async version of `deepagents`, since MCP tools are async

(To run the example below, will need to `pip install langchain-mcp-adapters`)

```python
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from deepagents import create_deep_agent

async def main():
    # Collect MCP tools
    mcp_client = MultiServerMCPClient(...)
    mcp_tools = await mcp_client.get_tools()

    # Create agent
    agent = async_create_deep_agent(tools=mcp_tools, ....)

    # Stream the agent
    async for chunk in agent.astream(
        {"messages": [{"role": "user", "content": "what is langgraph?"}]},
        stream_mode="values"
    ):
        if "messages" in chunk:
            chunk["messages"][-1].pretty_print()

asyncio.run(main())
```

## Configurable Agent

Configurable agents allow you to control the agent via a config passed in.

```python
from deepagents import create_configurable_agent

agent_config = {"instructions": "foo", "subagents": []}

build_agent = create_configurable_agent(
    agent_config['instructions'],
    agent_config['subagents'],
    [],
    agent_config={"recursion_limit": 1000}
)
```
You can now use `build_agent` in your `langgraph.json` and deploy it with `langgraph dev`

For async tools, you can use `from deepagents import async_create_configurable_agent`

## Roadmap

### NetBox Chatbot
- [ ] Web UI for chatbot interface
- [ ] Multi-tenant support (multiple NetBox instances)
- [ ] Advanced visualizations (topology diagrams, capacity heatmaps)
- [ ] Batch query processing
- [ ] Export results (PDF, CSV, JSON)

### DeepAgents Framework
- [ ] Allow users to customize full system prompt
- [ ] Code cleanliness (type hinting, docstrings, formating)
- [ ] Allow for more of a robust virtual filesystem
- [ ] Create an example of a deep coding agent built on top of this
- [ ] Benchmark the example of [deep research agent](examples/research/research_agent.py)

## Contributing

Contributions are welcome! The NetBox chatbot demonstrates production patterns for building deep agents. See [docs/guides/AGENTS.md](docs/guides/AGENTS.md) for agent development best practices.

## License

MIT License - See LICENSE file for details
