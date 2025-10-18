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
from langgraph.prebuilt import create_react_agent  # v0 API (deprecated)

# v1 API imports
try:
    from langchain.agents import create_agent
    from langchain.agents.middleware import SummarizationMiddleware
    V1_AVAILABLE = True
except ImportError:
    V1_AVAILABLE = False
    print("[WARNING] LangChain v1 APIs not available. Using v0 fallback.")

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
    """True V1 agent builder using create_agent and SummarizationMiddleware."""

    if not V1_AVAILABLE:
        print("[WARNING] V1 APIs not available. Falling back to v0 implementation.")
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

    # Prepare system prompt (was "prompt" in v0, now "system_prompt" in v1)
    system_prompt = instructions + BASE_AGENT_PROMPT

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

    # Create SummarizationMiddleware for automatic context compression
    summarization_middleware = SummarizationMiddleware(
        model=model,  # Use same model for summarization
        max_tokens_before_summary=15000,  # Trigger at 15k tokens (target reduction from 40k)
        messages_to_keep=20,  # Keep last 20 messages after summarization
        # Optional: Could add custom summary_prompt here
    )

    # Build task tool for subagents
    if not is_async:
        task_tool = _create_sync_task_tool(
            list(tools) + built_in_tools,
            BASE_AGENT_PROMPT,
            subagents or [],
            model,
            state_schema,
            post_model_hook,  # Note: post_model_hook handled differently in v1
        )
    else:
        task_tool = _create_task_tool(
            list(tools) + built_in_tools,
            BASE_AGENT_PROMPT,
            subagents or [],
            model,
            state_schema,
            post_model_hook,
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

    # Handle interrupt_config conversion to v1 format
    interrupt_before = None
    interrupt_after = None
    if interrupt_config:
        # Convert v0 interrupt_config to v1 interrupt_before/after lists
        # In v0, interrupt_config is a dict mapping tool names to configs
        # In v1, we use interrupt_before/interrupt_after lists
        interrupt_before = list(interrupt_config.keys())
        print(f"[INFO] Converted interrupt_config to interrupt_before: {interrupt_before}")

    # Handle config_schema deprecation warning
    if config_schema is not None:
        print("[WARNING] config_schema parameter is not supported in v1 create_agent and will be ignored")

    # Handle post_model_hook deprecation
    if post_model_hook is not None:
        print("[WARNING] post_model_hook is replaced by middleware in v1. Consider implementing custom middleware.")

    # Use v1 create_agent API
    try:
        # Note: state_schema might need adaptation if it's not a TypedDict
        # For now, we'll try to use it as-is and handle errors if they occur
        return create_agent(
            model=model,
            tools=all_tools,
            system_prompt=system_prompt,
            middleware=[summarization_middleware],  # v1 middleware system
            state_schema=state_schema,  # May need adaptation for v1
            checkpointer=checkpointer,
            interrupt_before=interrupt_before,
            interrupt_after=interrupt_after,
            # Note: config_schema removed in v1
            # Note: post_model_hook replaced by middleware
        )
    except Exception as e:
        print(f"[ERROR] Failed to create v1 agent: {e}")
        print("[INFO] Falling back to v0 implementation")
        # Fallback to v0 if v1 fails
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
        if V1_AVAILABLE:
            print("[INFO] Using LangChain v1 core with SummarizationMiddleware")
        else:
            print("[WARNING] V1 requested but not available. Using v0 with message trimming fallback.")
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
