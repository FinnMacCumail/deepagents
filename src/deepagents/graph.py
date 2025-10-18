import os
from deepagents.sub_agent import (
    _create_task_tool,
    _create_sync_task_tool,
    SubAgent,
    CustomSubAgent,
)
from deepagents.model import get_default_model
from deepagents.tools import write_todos, write_file, read_file, ls, edit_file
from deepagents.state import DeepAgentState
from typing import Sequence, Union, Callable, Any, TypeVar, Type, Optional
from langchain_core.tools import BaseTool, tool
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import trim_messages
from deepagents.interrupt import create_interrupt_hook, ToolInterruptConfig
from langgraph.types import Checkpointer
from langgraph.prebuilt import create_react_agent
from deepagents.prompts import BASE_AGENT_PROMPT

StateSchema = TypeVar("StateSchema", bound=DeepAgentState)
StateSchemaType = Type[StateSchema]


def _agent_builder_v0(
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    instructions: str,
    model: Optional[Union[str, LanguageModelLike]] = None,
    subagents: list[SubAgent | CustomSubAgent] = None,
    state_schema: Optional[StateSchemaType] = None,
    builtin_tools: Optional[list[str]] = None,
    interrupt_config: Optional[ToolInterruptConfig] = None,
    config_schema: Optional[Type[Any]] = None,
    checkpointer: Optional[Checkpointer] = None,
    post_model_hook: Optional[Callable] = None,
    main_agent_tools: Optional[list[str]] = None,
    is_async: bool = False,
):
    """Original v0 agent builder implementation."""
    prompt = instructions + BASE_AGENT_PROMPT

    all_builtin_tools = [write_todos, write_file, read_file, ls, edit_file]

    if builtin_tools is not None:
        tools_by_name = {}
        for tool_ in all_builtin_tools:
            if not isinstance(tool_, BaseTool):
                tool_ = tool(tool_)
            tools_by_name[tool_.name] = tool_
        # Only include built-in tools whose names are in the specified list
        built_in_tools = [tools_by_name[_tool] for _tool in builtin_tools]
    else:
        built_in_tools = all_builtin_tools

    if model is None:
        model = get_default_model()
    state_schema = state_schema or DeepAgentState

    # Should never be the case that both are specified
    if post_model_hook and interrupt_config:
        raise ValueError(
            "Cannot specify both post_model_hook and interrupt_config together. "
            "Use either interrupt_config for tool interrupts or post_model_hook for custom post-processing."
        )
    elif post_model_hook is not None:
        selected_post_model_hook = post_model_hook
    elif interrupt_config is not None:
        selected_post_model_hook = create_interrupt_hook(interrupt_config)
    else:
        selected_post_model_hook = None

    if not is_async:
        task_tool = _create_sync_task_tool(
            list(tools) + built_in_tools,
            BASE_AGENT_PROMPT,
            subagents or [],
            model,
            state_schema,
            selected_post_model_hook,
        )
    else:
        task_tool = _create_task_tool(
            list(tools) + built_in_tools,
            BASE_AGENT_PROMPT,
            subagents or [],
            model,
            state_schema,
            selected_post_model_hook,
        )
    if main_agent_tools is not None:
        passed_in_tools = []
        for tool_ in tools:
            if not isinstance(tool_, BaseTool):
                tool_ = tool(tool_)
            if tool_.name in main_agent_tools:
                passed_in_tools.append(tool_)
    else:
        passed_in_tools = list(tools)
    all_tools = built_in_tools + passed_in_tools + [task_tool]

    return create_react_agent(
        model,
        prompt=prompt,
        tools=all_tools,
        state_schema=state_schema,
        post_model_hook=selected_post_model_hook,
        config_schema=config_schema,
        checkpointer=checkpointer,
    )


def _agent_builder_v1(
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    instructions: str,
    model: Optional[Union[str, LanguageModelLike]] = None,
    subagents: list[SubAgent | CustomSubAgent] = None,
    state_schema: Optional[StateSchemaType] = None,
    builtin_tools: Optional[list[str]] = None,
    interrupt_config: Optional[ToolInterruptConfig] = None,
    config_schema: Optional[Type[Any]] = None,
    checkpointer: Optional[Checkpointer] = None,
    post_model_hook: Optional[Callable] = None,
    main_agent_tools: Optional[list[str]] = None,
    is_async: bool = False,
):
    """V1 agent builder with message trimming for token reduction."""
    prompt = instructions + BASE_AGENT_PROMPT

    all_builtin_tools = [write_todos, write_file, read_file, ls, edit_file]

    if builtin_tools is not None:
        tools_by_name = {}
        for tool_ in all_builtin_tools:
            if not isinstance(tool_, BaseTool):
                tool_ = tool(tool_)
            tools_by_name[tool_.name] = tool_
        # Only include built-in tools whose names are in the specified list
        built_in_tools = [tools_by_name[_tool] for _tool in builtin_tools]
    else:
        built_in_tools = all_builtin_tools

    if model is None:
        model = get_default_model()
    state_schema = state_schema or DeepAgentState

    # Create a pre_model_hook that trims messages to reduce token usage
    def trim_messages_hook(state):
        """Trim messages to keep only recent context and reduce tokens."""
        messages = state.get("messages", [])

        # Use trim_messages to keep last 15k tokens worth of messages
        # This should reduce from 40k to ~15k tokens
        trimmed = trim_messages(
            messages,
            strategy="last",  # Keep most recent messages
            token_counter=len,  # Simple token counter (can be replaced with tiktoken)
            max_tokens=15000,  # Target token count
            include_system=True,  # Always keep system messages
            start_on="human",  # Start trimming from first human message
        )

        return {"messages": trimmed}

    # Combine trim_messages_hook with existing post_model_hook
    if post_model_hook and interrupt_config:
        raise ValueError(
            "Cannot specify both post_model_hook and interrupt_config together. "
            "Use either interrupt_config for tool interrupts or post_model_hook for custom post-processing."
        )
    elif post_model_hook is not None:
        selected_post_model_hook = post_model_hook
    elif interrupt_config is not None:
        selected_post_model_hook = create_interrupt_hook(interrupt_config)
    else:
        selected_post_model_hook = None

    if not is_async:
        task_tool = _create_sync_task_tool(
            list(tools) + built_in_tools,
            BASE_AGENT_PROMPT,
            subagents or [],
            model,
            state_schema,
            selected_post_model_hook,
        )
    else:
        task_tool = _create_task_tool(
            list(tools) + built_in_tools,
            BASE_AGENT_PROMPT,
            subagents or [],
            model,
            state_schema,
            selected_post_model_hook,
        )
    if main_agent_tools is not None:
        passed_in_tools = []
        for tool_ in tools:
            if not isinstance(tool_, BaseTool):
                tool_ = tool(tool_)
            if tool_.name in main_agent_tools:
                passed_in_tools.append(tool_)
    else:
        passed_in_tools = list(tools)
    all_tools = built_in_tools + passed_in_tools + [task_tool]

    # Use create_react_agent with pre_model_hook for message trimming
    return create_react_agent(
        model,
        prompt=prompt,
        tools=all_tools,
        state_schema=state_schema,
        pre_model_hook=trim_messages_hook,  # Add message trimming before each LLM call
        post_model_hook=selected_post_model_hook,
        config_schema=config_schema,
        checkpointer=checkpointer,
    )


def _agent_builder(
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    instructions: str,
    model: Optional[Union[str, LanguageModelLike]] = None,
    subagents: list[SubAgent | CustomSubAgent] = None,
    state_schema: Optional[StateSchemaType] = None,
    builtin_tools: Optional[list[str]] = None,
    interrupt_config: Optional[ToolInterruptConfig] = None,
    config_schema: Optional[Type[Any]] = None,
    checkpointer: Optional[Checkpointer] = None,
    post_model_hook: Optional[Callable] = None,
    main_agent_tools: Optional[list[str]] = None,
    is_async: bool = False,
):
    """Route to v0 or v1 agent builder based on USE_V1_CORE environment variable."""
    use_v1 = os.getenv("USE_V1_CORE", "false").lower() == "true"

    if use_v1:
        print("[INFO] Using LangChain v1 core with message trimming")
        return _agent_builder_v1(
            tools=tools,
            instructions=instructions,
            model=model,
            subagents=subagents,
            state_schema=state_schema,
            builtin_tools=builtin_tools,
            interrupt_config=interrupt_config,
            config_schema=config_schema,
            checkpointer=checkpointer,
            post_model_hook=post_model_hook,
            main_agent_tools=main_agent_tools,
            is_async=is_async,
        )
    else:
        return _agent_builder_v0(
            tools=tools,
            instructions=instructions,
            model=model,
            subagents=subagents,
            state_schema=state_schema,
            builtin_tools=builtin_tools,
            interrupt_config=interrupt_config,
            config_schema=config_schema,
            checkpointer=checkpointer,
            post_model_hook=post_model_hook,
            main_agent_tools=main_agent_tools,
            is_async=is_async,
        )


def create_deep_agent(
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    instructions: str,
    model: Optional[Union[str, LanguageModelLike]] = None,
    subagents: list[SubAgent | CustomSubAgent] = None,
    state_schema: Optional[StateSchemaType] = None,
    builtin_tools: Optional[list[str]] = None,
    interrupt_config: Optional[ToolInterruptConfig] = None,
    config_schema: Optional[Type[Any]] = None,
    checkpointer: Optional[Checkpointer] = None,
    post_model_hook: Optional[Callable] = None,
    main_agent_tools: Optional[list[str]] = None,
):
    """Create a deep agent.

    This agent will by default have access to a tool to write todos (write_todos),
    and then four file editing tools: write_file, ls, read_file, edit_file.

    Args:
        tools: The additional tools the agent should have access to.
        instructions: The additional instructions the agent should have. Will go in
            the system prompt.
        model: The model to use.
        subagents: The subagents to use. Each subagent should be a dictionary with the
            following keys:
                - `name`
                - `description` (used by the main agent to decide whether to call the sub agent)
                - `prompt` (used as the system prompt in the subagent)
                - (optional) `tools`
                - (optional) `model` (either a LanguageModelLike instance or dict settings)
        state_schema: The schema of the deep agent. Should subclass from DeepAgentState
        builtin_tools: If not provided, all built-in tools are included. If provided,
            only the specified built-in tools are included.
        interrupt_config: Optional Dict[str, HumanInterruptConfig] mapping tool names to interrupt configs.
        config_schema: The schema of the deep agent.
        post_model_hook: Custom post model hook
        checkpointer: Optional checkpointer for persisting agent state between runs.
        main_agent_tools: Optional list of tool names that the main agent should have. If not provided,
            will have access to all tools. Note that built-in tools (for filesystem and todo and subagents) are
            always included - this filtering only applies to passed in tools.
    """
    return _agent_builder(
        tools=tools,
        instructions=instructions,
        model=model,
        subagents=subagents,
        state_schema=state_schema,
        builtin_tools=builtin_tools,
        interrupt_config=interrupt_config,
        config_schema=config_schema,
        checkpointer=checkpointer,
        post_model_hook=post_model_hook,
        main_agent_tools=main_agent_tools,
        is_async=False,
    )


def async_create_deep_agent(
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    instructions: str,
    model: Optional[Union[str, LanguageModelLike]] = None,
    subagents: list[SubAgent | CustomSubAgent] = None,
    state_schema: Optional[StateSchemaType] = None,
    builtin_tools: Optional[list[str]] = None,
    interrupt_config: Optional[ToolInterruptConfig] = None,
    config_schema: Optional[Type[Any]] = None,
    checkpointer: Optional[Checkpointer] = None,
    post_model_hook: Optional[Callable] = None,
    main_agent_tools: Optional[list[str]] = None,
):
    """Create a deep agent.

    This agent will by default have access to a tool to write todos (write_todos),
    and then four file editing tools: write_file, ls, read_file, edit_file.

    Args:
        tools: The additional tools the agent should have access to.
        instructions: The additional instructions the agent should have. Will go in
            the system prompt.
        model: The model to use.
        subagents: The subagents to use. Each subagent should be a dictionary with the
            following keys:
                - `name`
                - `description` (used by the main agent to decide whether to call the sub agent)
                - `prompt` (used as the system prompt in the subagent)
                - (optional) `tools`
                - (optional) `model` (either a LanguageModelLike instance or dict settings)
        state_schema: The schema of the deep agent. Should subclass from DeepAgentState
        builtin_tools: If not provided, all built-in tools are included. If provided,
            only the specified built-in tools are included.
        interrupt_config: Optional Dict[str, HumanInterruptConfig] mapping tool names to interrupt configs.
        config_schema: The schema of the deep agent.
        post_model_hook: Custom post model hook
        checkpointer: Optional checkpointer for persisting agent state between runs.
        main_agent_tools: Optional list of tool names that the main agent should have. If not provided,
            will have access to all tools. Note that built-in tools (for filesystem and todo and subagents) are
            always included - this filtering only applies to passed in tools.
    """
    return _agent_builder(
        tools=tools,
        instructions=instructions,
        model=model,
        subagents=subagents,
        state_schema=state_schema,
        builtin_tools=builtin_tools,
        interrupt_config=interrupt_config,
        config_schema=config_schema,
        checkpointer=checkpointer,
        post_model_hook=post_model_hook,
        main_agent_tools=main_agent_tools,
        is_async=True,
    )
