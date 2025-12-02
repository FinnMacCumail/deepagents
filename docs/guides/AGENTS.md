# DeepAgents Agent Playbook

This document distills how agents in this repository should be built and operated. Use it as the starting point when creating, extending, or debugging agents.

## Architectural Foundations

DeepAgents ships with four pillars that every agent should leverage:
- **Rich system instructions** – combine task framing, behavioural guardrails, and examples.
- **Planning support** – the built-in `write_todos` tool keeps long tasks organised when they truly need planning.
- **Task delegation** – optional sub-agents created with `task` for work that benefits from isolation.
- **Workspace access** – the virtual filesystem lets agents persist intermediate artefacts.

The core implementation lives under `src/deepagents/`:
- `graph.py` – async and sync builders that wire models, tools, and optional sub-agents into LangGraph `create_react_agent`.
- `sub_agent.py` – utilities that spawn specialised delegates with filtered toolsets.
- `prompts.py` – baseline instructions (see `BASE_AGENT_PROMPT`, `TASK_TOOL_DESCRIPTION`, `WRITE_TODOS_TOOL_DESCRIPTION`).
- `tools.py` – default tool implementations; any agent automatically receives `write_todos`, `write_file`, `read_file`, `ls`, `edit_file`, and the `task` delegation tool.

### Execution Flow
1. Compose the instruction block (`BASE_AGENT_PROMPT` + domain-specific guidance).
2. Select tools: prefer a short, high-signal list; rely on planning/delegation sparingly.
3. Instantiate the agent through `create_deep_agent`/`async_create_deep_agent`.
4. Provide an appropriate model (default is `claude-sonnet-4-20250514`; mix in `CachedChatAnthropicFixed` if prompt caching matters).
5. Run, observe, and refine prompts, tool behaviour, and trimming hooks.

## Behavioural Guardrails

### Planning (`write_todos`)
- Treat planning as an opt-in for genuinely complex efforts (multi-phase, ≥4 dependent steps, or >10 entities).
- Skip it for single lookups, short dependency chains, and straightforward searches; excessive planning inflates context and latency.
- Update todos progressively; keep at least one item `in_progress` while work continues.

### Reflection (`think`)
- The `think` tool is available for high-stakes reasoning (policy compliance, multi-path analysis). It is not required for routine data fetches.
- If you add bespoke thinking strategies, include clear criteria in the prompt to avoid reflexive use.

### Sub-Agents
- Create them only when parallel work across truly independent scopes improves throughput.
- Keep each delegate’s tool list tight and reinforce domain boundaries inside the delegate prompt.
- Example of deliberate non-use: `examples/netbox/netbox_agent.py` documents why sub-agents were disabled after validation.

## Designing a New Agent

1. **Understand the domain**
   - Identify the action space (APIs, MCP tools, files to inspect or modify).
   - Capture any compliance or safety constraints the agent must respect.

2. **Author the instruction pack**
   - Start from `CLAUDE.md`’s style: project context, execution tiers, concrete examples, and explicit “when NOT to do X” guidance.
   - Include output expectations (tables vs prose, IDs to report) and failure-handling instructions.

3. **Define tools**
   - Begin with the smallest useful set.
   - Wrap external integrations (REST, MCP) so responses are concise and JSON-friendly.
   - Raise exceptions (`ToolException`) instead of returning error dictionaries so the model surfaces failures immediately (see `examples/netbox/netbox_agent.py:115-152`).

4. **Assemble the agent**
   - Use `async_create_deep_agent` for async toolchains, `create_deep_agent` otherwise.
   - Pass `builtin_tools` if you want to restrict the default file/planning toolbox.
   - Configure recursion limits intentionally; misalignment between base configuration and per-run overrides can truncate work.

5. **Test iteratively**
   - Build a validation script or notebook similar to the NetBox suite in `examples/netbox/`.
   - Track tool-call counts, latency, and error surfaces.
   - Compare behaviour to the guidance sections; adjust instructions when the model over/under-uses planning or reflection.

## Reference Implementations

- **NetBox Agent** (`examples/netbox/netbox_agent.py`)
  - Demonstrates MCP integration, prompt caching, error signalling, and the decision to disable sub-agents after empirical validation.
  - Supplementary analysis lives alongside the agent (e.g., `NO_SUBAGENTS_RATIONALE.md`, `REFACTORING_RESULTS.md`).

- **Research Agent** (`examples/research/research_agent.py`)
  - Smaller footprint showcasing sub-agent delegation (`research_agent.py` plus PRP templates in `.claude/`).

Review these agents before starting new work; mirror their structure while tailoring prompts and tooling to your target domain.

## Operational Best Practices

- **Token management**: trim message history or design tools to return summaries; context bloat dominates cost (see Token Usage section in `CLAUDE.md`).
- **Prompt caching**: when using Anthropic caching betas, surface cache metrics (as done via `CacheMonitor` in the NetBox agent) to validate savings.
- **Documentation**: keep a markdown narrative beside complex agents describing design decisions and regression analyses—future contributors rely on this context.

By following this playbook and the deeper guidance in `CLAUDE.md`, you can develop agents that stay aligned with the repository’s architecture while remaining practical, efficient, and maintainable. When introducing significant new patterns, document them here so the playbook evolves with the codebase.
