# LangChain v1 Core Optimization - Initial Requirements

## FEATURE:
We want to migrate the DeepAgents framework to LangChain v1 core to dramatically reduce prompt token usage by 60-70% through middleware architecture and intelligent message management.

### Current Problem
The current system exhibits severe context accumulation issues:
- **Average 40k prompt tokens per LLM call** (from LangSmith traces)
- **99.1% prompt tokens vs 0.9% completion tokens** - problem is INPUT size, not output
- **17.7M prompt tokens** consumed across 5,859 runs in recent validation
- **$34+ costs** that could be reduced to $12-15 with optimization
- Message history grows unbounded across agent conversations
- Tool results accumulate without trimming
- System prompts and tool schemas repeated each iteration (partially mitigated by caching)

### Target Outcomes
- **Reduce to 15k prompt tokens per LLM call** (60% reduction)
- **Maintain 100% query success rate** (proven in validation)
- **Implement v1 middleware architecture** using SummarizationMiddleware
- **Migrate from v0 to v1 APIs** (create_react_agent → create_agent)
- **Keep last 2-3 tool results only**, trim older context
- **Use v1-alpha packages NOW** (not waiting for October stable release)

### Key Features to Implement

1. **SummarizationMiddleware Integration**
   - Automatic context summarization before model calls
   - Configurable message retention policies
   - Intelligent compression of older conversation history

2. **API Migration**
   - Replace `create_react_agent` with v1 `create_agent` API
   - Update all agent creation in src/deepagents/graph.py
   - Migrate both sync (create_deep_agent) and async (async_create_deep_agent) versions

3. **Message Trimming Strategy**
   - Keep last 2-3 tool calls and results
   - Preserve system prompts (already cached)
   - Summarize or remove older messages beyond threshold
   - Use pre_model_hook or v1 middleware hooks

4. **Middleware Hooks**
   - Implement before_model hook for message trimming
   - Implement after_model hook for response processing
   - Optional: before_tool and after_tool hooks for tool result management

5. **Backward Compatibility**
   - Do not break existing functionality
   - All pytest tests must pass
   - Validate with real-world queries from examples/netbox/

## EXAMPLES & DOCUMENTATION:

### V1 Core Documentation
- **Primary reference**: https://docs.langchain.com/oss/python/releases/langchain-v1
  - SummarizationMiddleware configuration
  - Middleware hooks: before_model, after_model, before_tool, after_tool
  - Migration guide from v0 to v1 APIs
  - create_agent API documentation

### Current Architecture (What Needs Updating)
- **src/deepagents/graph.py**: Main agent builder using create_react_agent (v0)
  - Lines 97-105: create_react_agent call needs migration
  - _agent_builder function needs middleware integration
  - Both sync and async versions need updating

- **examples/netbox/netbox_agent.py**: Production NetBox agent (primary test case)
  - Uses async_create_deep_agent
  - Currently no message management
  - Target for 40k → 15k token reduction

- **examples/research/research_agent.py**: Research agent (secondary test case)
  - Uses create_deep_agent (sync)
  - Simpler than NetBox, good validation case

### Token Usage Analysis
- **examples/netbox/TOOL_REMOVAL_RESULTS.md**:
  - Documents current token usage patterns
  - Shows 3 test queries with metrics
  - Query 1: 7 LLM calls, 60.6s duration
  - Query 2: 6 LLM calls, 33.4s duration (regressed to 10 calls after tool changes)
  - Query 3: 12 LLM calls, 62.8s duration (improved to 10 calls)

- **examples/netbox/VALIDATION_RESULTS_SUMMARY.md**:
  - Comprehensive performance metrics
  - Token distribution analysis
  - Cache hit rates (84.6% - working well)

### LangSmith Traces
- **Project**: NetBox agent optimization traces
- **Key traces** (from TOOL_REMOVAL_RESULTS.md):
  - Query 1 (8 tools): `6ab198c9-1308-4e84-b124-0ac8670be95a`
  - Query 1 (4 tools): `740466c3-ebb5-4864-9954-6fc1fb9085a2`
  - Query 2 (8 tools): `e6046c96-ab11-45fc-9662-073e9d0d1408`
  - Query 2 (4 tools): `d8ad87bd-b09e-4100-bb9f-bd8aa7011655`
  - Query 3 (8 tools): `d2e82487-e103-432c-9634-f0b0f4af3b6f`
  - Query 3 (4 tools): `74ad927e-a634-4a62-b1a9-2bf74fd76af4`

## OTHER CONSIDERATIONS:

### Architecture Constraints
- **NO breaking changes to existing API** - maintain create_deep_agent and async_create_deep_agent signatures
- **NO framework modifications to sub-agents** - focus on main agent message management
- **NO changes to built-in tools** - write_todos, file operations remain unchanged
- **Use v1-alpha packages** - install langchain@alpha and langchain-core@alpha
- **V0 packages reference only** - v0 moves to langchain-classic (don't install)

### Migration Strategy
- **Phase 1**: Install v1-alpha packages alongside v0 (test compatibility)
- **Phase 2**: Update src/deepagents/graph.py to use v1 APIs
- **Phase 3**: Add SummarizationMiddleware or pre_model_hook with trim_messages
- **Phase 4**: Test with NetBox and research agents
- **Phase 5**: Measure token reduction via LangSmith

### Message Management Requirements
Agent must implement intelligent context management:
- **System prompts**: Keep always (already cached by LangGraph)
- **Recent tool calls**: Keep last 2-3 tool calls and results
- **Older messages**: Summarize or remove based on age/relevance
- **Planning messages**: Keep write_todos results (used for coordination)
- **Error messages**: Keep for debugging context
- **Never trim**: User's original query, final response

### Validation Requirements
Before considering this complete:
1. **All pytest tests pass**: `pytest tests/ -v`
2. **Token reduction achieved**: LangSmith shows <20k prompt tokens per call
3. **Query success rate**: 100% success on 3 test queries from TOOL_REMOVAL_RESULTS.md
4. **No accuracy degradation**: Validate responses match quality of v0 version
5. **Performance maintained or improved**: Track LLM calls and duration

### Expected Implementation Structure
Following the PRP framework approach:

```python
# src/deepagents/graph.py - Updated version

from langchain.agents import create_agent  # v1 API
from langchain.middleware import SummarizationMiddleware  # v1 feature
from langchain_core.messages import trim_messages  # For message management

def _agent_builder(...):
    # Configure middleware for context management
    middleware = SummarizationMiddleware(
        max_tokens=15000,  # Target token count
        keep_system_prompt=True,
        keep_last_n_tool_calls=3,
        summarize_older=True
    )

    # Use v1 create_agent API (replaces create_react_agent)
    return create_agent(
        model,
        prompt=prompt,
        tools=all_tools,
        state_schema=state_schema,
        middleware=[middleware],  # v1 middleware system
        config_schema=config_schema,
        checkpointer=checkpointer,
    )
```

### Test Queries for Validation
Use these queries from TOOL_REMOVAL_RESULTS.md to validate:

1. **Query 1** (Dunder-Mifflin Sites - Complex):
   "Show all Dunder-Mifflin sites with device counts, rack allocations, and IP prefix assignments"
   - Baseline: 7 LLM calls, 60.6s
   - Should maintain success, measure token reduction

2. **Query 2** (VLAN 100 - Simple/Regression Risk):
   "Show where VLAN 100 is deployed across Jimbob's Banking sites, including devices using this VLAN and IP allocations"
   - Baseline: 6 LLM calls, 33.4s
   - Watch for over-planning regression (avoid 10 LLM calls)

3. **Query 3** (NC State Racks - Intermediate):
   "For NC State University racks at Butler Communications site, show installed devices with their IP addresses"
   - Baseline: 10 LLM calls, 41.9s
   - Should maintain or improve performance

### Success Criteria
- ✅ V1-alpha packages installed and working
- ✅ No v0 API calls in updated code (no create_react_agent)
- ✅ SummarizationMiddleware or equivalent configured
- ✅ Token reduction: 40k → 15k (60%+) per LLM call
- ✅ Cost reduction: $34 → $12-15 per 5,859 runs
- ✅ 100% query success rate maintained
- ✅ All pytest tests pass
- ✅ LangSmith traces show token improvements
- ✅ No accuracy degradation on test queries

### Anti-Patterns to Avoid
- ❌ Don't mix v0 and v1 APIs in same codebase (choose one)
- ❌ Don't use recursion_limit when middleware available (v1 pattern)
- ❌ Don't skip message trimming configuration (context still accumulates)
- ❌ Don't assume v0 tool patterns work unchanged in v1
- ❌ Don't modify v0 code directly - create v1 versions with fallback
- ❌ Don't trim user queries or critical planning messages
- ❌ Don't deploy without LangSmith validation of token reduction

### Branch Strategy
- **All work on core-v1 branch** (created from current state)
- **Keep main branch stable** (no changes until validation complete)
- **Iterative validation** (test after each phase)
- **Rollback capability** (can revert to main if issues arise)

### Installation Commands
```bash
# Install v1-alpha packages
pip install langchain@alpha langchain-core@alpha

# Verify installation
pip show langchain langchain-core

# Run tests after migration
pytest tests/ -v

# Validate with NetBox agent
cd examples/netbox
python netbox_agent.py
```

### Reference Implementations
- **Official LangChain v1 examples**: Check https://github.com/langchain-ai/langchain for v1 migration examples
- **DeepAgents examples**: Both research and NetBox agents serve as test cases
- **LangSmith MCP**: Already integrated, use for token measurement

## DOCUMENTATION PRIORITIES:
1. **MUST READ FIRST**: https://docs.langchain.com/oss/python/releases/langchain-v1
2. **Current architecture**: src/deepagents/graph.py:91
3. **Token analysis**: examples/netbox/TOOL_REMOVAL_RESULTS.md
4. **Test cases**: examples/netbox/netbox_agent.py and examples/research/research_agent.py
5. **Validation metrics**: examples/netbox/VALIDATION_RESULTS_SUMMARY.md
