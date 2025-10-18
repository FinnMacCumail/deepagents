# LangChain v1 Core Optimization PRP

## Purpose
Migrate DeepAgents framework to LangChain v1 core to achieve 60-70% reduction in prompt token usage through SummarizationMiddleware and intelligent message management while maintaining 100% query success rate.

## Core Principles
1. **Context is King**: Include ALL necessary v1 documentation, migration guides, and current architecture
2. **Validation Loops**: Provide executable tests with token measurements via LangSmith
3. **Information Dense**: Use exact code patterns from current codebase and v1 examples
4. **Progressive Success**: Install packages, create v1 builder, test incrementally, measure tokens
5. **Global rules**: Follow all rules in CLAUDE.md, especially v1 migration guidance

---

## Goal
Reduce prompt tokens from 40k to 15k per LLM call (60-70% reduction) using LangChain v1's SummarizationMiddleware while maintaining backward compatibility and 100% query success rate.

## Why
- **Cost Reduction**: $34 → $12-15 per 5,859 runs (65% cost savings)
- **Performance**: Faster LLM calls with smaller context windows
- **Scalability**: Enable longer conversations without hitting token limits
- **Future-Proofing**: Align with LangChain's v1 architecture direction

## What
Implement LangChain v1 core features including:
- SummarizationMiddleware for automatic context compression
- Migration from `create_react_agent` to `create_agent` API
- Message trimming to keep only last 2-3 tool results
- Middleware hooks for fine-grained control
- Environment flag for gradual rollout

### Success Criteria
- [ ] Token reduction: 40k → 15k prompt tokens per call (60%+ reduction)
- [ ] Query success rate: 100% on all test queries
- [ ] All pytest tests pass
- [ ] LangSmith traces show token improvements
- [ ] No accuracy degradation on validation queries

## All Needed Context

### Documentation & References
```yaml
# V1 Core Documentation
- url: https://docs.langchain.com/oss/python/migrate/langchain-v1
  why: Official v1 migration guide with breaking changes

- url: https://colinmcnamara.com/blog/langchain-middleware-v1-alpha-guide
  why: Comprehensive middleware architecture guide with SummarizationMiddleware examples

- url: https://python.langchain.com/docs/how_to/migrate_agent/
  why: Step-by-step agent migration from legacy to v1

- url: https://github.com/langchain-ai/langchain/releases
  why: Latest v1-alpha release notes and versions

# Current Architecture Files
- file: src/deepagents/graph.py
  lines: 97-105
  why: Current create_react_agent implementation that needs migration

- file: examples/netbox/netbox_agent.py
  why: Primary test case - production agent with 40k token usage

- file: examples/research/research_agent.py
  why: Secondary test case - simpler validation target

# Token Analysis
- file: examples/netbox/TOOL_REMOVAL_RESULTS.md
  why: Detailed token metrics and 3 test queries for validation

- file: examples/netbox/VALIDATION_RESULTS_SUMMARY.md
  why: Performance baseline metrics (17.7M tokens across 5,859 runs)

# Configuration Files
- file: CLAUDE.md
  sections: "LangChain v1 Migration Strategy", "Middleware Architecture Patterns"
  why: Project-specific v1 guidance and patterns

- file: initial-langchain-v1-optimization.md
  why: Detailed requirements and constraints for this migration
```

### Current v0 Implementation Pattern
```python
# src/deepagents/graph.py - Current v0 implementation
from langgraph.prebuilt import create_react_agent

def _agent_builder(...):
    # ... tool setup ...

    return create_react_agent(  # v0 API
        model,
        prompt=prompt,
        tools=all_tools,
        state_schema=state_schema,
        post_model_hook=selected_post_model_hook,  # v0 hook
        config_schema=config_schema,
        checkpointer=checkpointer,
    )
```

### Target v1 Implementation Pattern
```python
# Target v1 implementation with SummarizationMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

def _agent_builder_v1(...):
    # Configure middleware for automatic context compression
    middleware = SummarizationMiddleware(
        model=model,  # Use same model for summarization
        max_tokens_before_summary=15000,  # Target token count
        messages_to_keep=3,  # Keep last 3 tool calls
        summary_prompt="Summarize the conversation history, preserving key findings and decisions."
    )

    # Use v1 create_agent API
    return create_agent(
        model=model,  # Must be string or BaseChatModel in v1
        tools=all_tools,
        middleware=[middleware],  # v1 middleware system
        # Note: state_schema handled differently in v1
    )
```

## Implementation Tasks (In Order)

### Phase 1: Environment Setup
1. **Install v1-alpha packages**
   ```bash
   pip install langchain@alpha langchain-core@alpha
   pip show langchain langchain-core  # Verify @alpha versions
   ```

2. **Create feature flag**
   - Add `USE_V1_CORE` environment variable
   - Default to False for backward compatibility
   - Document in .env.example

### Phase 2: Create v1 Builder Function
3. **Implement _agent_builder_v1 in src/deepagents/graph.py**
   - Import v1 APIs (create_agent, SummarizationMiddleware)
   - Handle v1 parameter differences (model must be string)
   - Configure SummarizationMiddleware with 15k token limit
   - Map v0 parameters to v1 equivalents

### Phase 3: Update Agent Creation Functions
4. **Update _agent_builder to route based on USE_V1_CORE**
   ```python
   def _agent_builder(...):
       if os.getenv("USE_V1_CORE", "false").lower() == "true":
           return _agent_builder_v1(...)  # Use v1
       else:
           return _agent_builder_v0(...)  # Use current v0
   ```

5. **Ensure both sync and async versions work**
   - Test create_deep_agent with v1
   - Test async_create_deep_agent with v1
   - Verify MCP tool compatibility

### Phase 4: Testing & Validation
6. **Run existing tests**
   ```bash
   pytest tests/ -v  # All must pass
   ```

7. **Test with NetBox agent**
   ```bash
   cd examples/netbox
   USE_V1_CORE=true python netbox_agent.py
   ```

8. **Validate with 3 test queries** (from TOOL_REMOVAL_RESULTS.md):
   - Query 1: "Show all Dunder-Mifflin sites with device counts, rack allocations, and IP prefix assignments"
   - Query 2: "Show where VLAN 100 is deployed across Jimbob's Banking sites, including devices using this VLAN and IP allocations"
   - Query 3: "For NC State University racks at Butler Communications site, show installed devices with their IP addresses"

### Phase 5: Token Measurement
9. **Measure token reduction via LangSmith**
   - Run queries with USE_V1_CORE=false (baseline)
   - Run queries with USE_V1_CORE=true (v1)
   - Compare prompt tokens (target: 40k → 15k)
   - Document trace IDs

10. **Create validation report**
    - Token measurements before/after
    - Query success rates
    - Performance metrics (LLM calls, duration)
    - Cost analysis

## Validation Gates

### Syntax & Compatibility
```bash
# Verify v1 packages installed
pip show langchain langchain-core | grep Version
# Should show versions with 'a' (alpha) suffix

# Check no v0 APIs in v1 code
rg "create_react_agent" src/deepagents/graph.py
# Should only appear in v0 function
```

### Functional Testing
```bash
# Run all tests with v1
USE_V1_CORE=true pytest tests/ -v

# Run NetBox agent test
cd examples/netbox
USE_V1_CORE=true python netbox_agent.py < test_queries.txt

# Run research agent test
cd examples/research
USE_V1_CORE=true python research_agent.py
```

### Token Validation
```python
# Validation script to measure tokens
import os
os.environ["USE_V1_CORE"] = "true"

# Run agent and capture LangSmith trace
# Verify prompt_tokens < 20000 (target: 15000)
# Verify success rate = 100%
```

## Gotchas & Known Issues

### v1 API Differences
- **Model parameter**: Must be string or BaseChatModel, not dict
- **State schema**: Handled differently than v0, may need adaptation
- **No prompted JSON**: v1 requires schemas (Pydantic/TypedDict) for structured output
- **Middleware order**: Executes in order, place SummarizationMiddleware first

### Migration Risks
- **Tool compatibility**: Some tools may need v1 adaptations
- **Async support**: v1 middleware may have limited async support initially
- **Breaking changes**: v1-alpha may introduce changes before stable release

### Debugging Tips
- Enable LangSmith tracing to see token counts per call
- Use `LANGCHAIN_VERBOSE=true` for detailed middleware execution logs
- Compare v0 and v1 side-by-side with feature flag

## Rollback Plan
If v1 causes issues:
1. Set USE_V1_CORE=false (immediate rollback)
2. Keep v0 code intact until v1 proven stable
3. Document any v1 incompatibilities for future retry

## Final Validation Checklist
- [ ] V1 alpha packages installed: `pip show langchain langchain-core`
- [ ] Feature flag working: USE_V1_CORE toggles between v0/v1
- [ ] All pytest tests pass with v1
- [ ] Token reduction achieved: <20k prompt tokens (target: 15k)
- [ ] Query success rate: 100% on all 3 test queries
- [ ] LangSmith traces documented with token measurements
- [ ] No accuracy degradation compared to v0
- [ ] Performance maintained or improved (LLM calls, duration)
- [ ] Documentation updated with v1 usage instructions

## V1 Migration Validation
- [ ] No v0 APIs in v1 code path: `rg "create_react_agent" src/`
- [ ] SummarizationMiddleware configured: max_tokens=15000
- [ ] Message trimming working: Only last 2-3 tool results kept
- [ ] Cost reduction verified: ~65% reduction in token costs
- [ ] Backward compatibility: v0 still works with USE_V1_CORE=false

---

## Anti-Patterns to Avoid
- ❌ Don't mix v0 and v1 APIs in same function
- ❌ Don't skip the feature flag (need rollback capability)
- ❌ Don't modify v0 code directly (keep it for comparison)
- ❌ Don't assume all tools work unchanged in v1
- ❌ Don't deploy without measuring token reduction
- ❌ Don't trim system prompts or user queries
- ❌ Don't over-trim (keep at least 2-3 tool calls for context)

## Implementation Confidence Score: 8/10

**Rationale**:
- Strong foundation with clear v0 → v1 migration path
- Comprehensive documentation and examples available
- Feature flag enables safe testing and rollback
- Clear validation metrics (token reduction, success rate)
- Some uncertainty around tool compatibility and async support (-2 points)

The implementation should succeed in one pass with careful attention to API differences and thorough testing at each phase.