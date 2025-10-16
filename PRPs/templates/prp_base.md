## Purpose
Template optimized for AI agents to implement features with sufficient context and self-validation capabilities to achieve working code through iterative refinement.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
[What needs to be built - be specific about the end state and desires]

## Why
- [Business value and user impact]
- [Integration with existing features]
- [Problems this solves and for whom]

## What
[User-visible behavior and technical requirements]

### Success Criteria
- [ ] [Specific measurable outcomes]

## All Needed Context

### Documentation & References (list all context needed to implement the feature)
```yaml
# MUST READ - Include these in your context window
- url: https://github.com/langchain-ai/deepagents
  why: This is the repo that the current deep agents code base is cloned from

- url: https://github.com/langchain-ai/deep-agents-from-scratch/blob/main/notebooks/4_full_agent.ipynb
  why: This will provide guidance on how to develop multi domain netbox queries
- dir: /home/ola/dev/netboxdev/

- url: /home/ola/dev/netboxdev/netbox-mcp-docs/Cross-Domain-Queries.md
  why: A list of Cross Domain Queries

  why: This is the location of the netbox mcp server that provides readonly mcp tools to the deep agents application.

- doc: https://github.com/Deployment-Team/netbox-mcp/wiki/Bridget-Auto-Context
  important: This documentation covers a version of the mcp server that covers CRUD tools. The version of this netbox mcp server ONLY handles read only tools.

- doc: examples/netbox/NETBOX_AGENT_TECHNICAL_REPORT.md
  important: This documentation covers the logic governing the NetBox Dynamic Agent Architecture and Operation
```

### V1 Core Context (include if migrating to LangChain v1)
```yaml
# V1 Core Requirements - For v1 migration PRPs
- doc: https://docs.langchain.com/oss/python/releases/langchain-v1
  why: LangChain v1 core features, SummarizationMiddleware, middleware hooks, and migration guide
  important: Official v1 documentation - primary reference for all v1 features

- file: src/deepagents/graph.py
  why: Current v0 architecture using create_react_agent that needs migration to create_agent
  line_reference: Line 97-105 for create_react_agent call

- file: examples/research/research_agent.py
  why: Simpler reference implementation to validate v1 migration patterns

- file: examples/netbox/netbox_agent.py
  why: Complex production agent - primary test case for v1 token optimization

- file: examples/netbox/TOOL_REMOVAL_RESULTS.md
  why: Token usage analysis showing 40k avg prompt tokens, 99.1% prompt vs 0.9% completion
  important: Quantifies the problem v1 middleware should solve

- file: examples/netbox/VALIDATION_RESULTS_SUMMARY.md
  why: Performance metrics and validation approach for testing v1 changes

- file: initial-langchain-v1-optimization.md
  why: Detailed requirements for v1 migration including success criteria
```

## Final validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] Manual test successful: [specific curl/command]
- [ ] Error cases handled gracefully
- [ ] Logs are informative but not verbose
- [ ] Documentation updated if needed

## V1 Migration Validation (if applicable - for LangChain v1 PRPs)
- [ ] V1 alpha packages installed: `pip show langchain langchain-core` shows @alpha version
- [ ] No v0 APIs in new code: `rg "create_react_agent" src/` returns no new usages
- [ ] Middleware configured: SummarizationMiddleware or pre_model_hook with trim_messages present
- [ ] Token measurements recorded: Compare prompt tokens before/after via LangSmith traces
  - [ ] Baseline measurement: Document current token usage (e.g., 40k prompt tokens per call)
  - [ ] Post-migration measurement: Verify 60%+ reduction (target: <20k prompt tokens)
- [ ] Success rate maintained: Run all test queries, verify 100% success rate unchanged
- [ ] LangSmith trace comparison: Document trace IDs showing token reduction
- [ ] Performance impact assessed: Measure LLM calls and duration (should maintain or improve)
- [ ] All pytest tests pass: Existing tests work with v1 changes

---

## Anti-Patterns to Avoid
- ❌ Don't create new patterns when existing ones work
- ❌ Don't skip validation because "it should work"
- ❌ Don't ignore failing tests - fix them
- ❌ Don't use sync functions in async context
- ❌ Don't hardcode values that should be config
- ❌ Don't catch all exceptions - be specific

## V1 Anti-Patterns to Avoid (if applicable - for LangChain v1 PRPs)
- ❌ Don't mix v0 and v1 APIs in same codebase (choose one, commit to it)
- ❌ Don't use recursion_limit when v1 middleware available (use middleware instead)
- ❌ Don't skip message trimming configuration (context still accumulates in v1 without it)
- ❌ Don't assume v0 tool patterns work unchanged in v1 (validate all tool integrations)
- ❌ Don't modify v0 code directly - create v1 versions alongside for comparison
- ❌ Don't deploy v1 changes without LangSmith validation (measure token reduction empirically)
- ❌ Don't trim user queries or system prompts (only trim old tool results and middle messages)
- ❌ Don't over-trim - keep last 2-3 tool calls for context continuity