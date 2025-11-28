# Recursion Limit Adjustment - From 20 to 50

## Problem Identified

Validation testing revealed that 2 out of 5 queries (Query 3 and Query 4) were failing with "Sorry, need more steps to process this request" despite:
- Zero sub-agent spawns (sub-agent elimination was successful)
- Reasonable tool call counts (10 calls each)
- Reasonable LLM call counts (10 calls each)
- No runaway behavior

## Root Cause

The agent had **two different recursion limits** configured:

1. **Agent creation** ([netbox_agent.py:888](netbox_agent.py#L888)): `recursion_limit: 1000`
2. **Query invocation** ([netbox_agent.py:966](netbox_agent.py#L966)): `recursion_limit: 20` ← **Active limit**

The invocation config **overrides** the agent config, meaning queries were actually limited to **20 steps**, not 1000.

### What is Recursion Limit?

In LangGraph, `recursion_limit` controls the maximum number of **graph execution steps** (node visits) before forcing termination. Each step typically includes:
- One LLM call
- Associated tool executions
- State updates

## Historical Context: Why 20?

The 20 limit was chosen as a **conservative safety mechanism** to prevent:
1. Sub-agent delegation spirals (which caused 20-32+ LLM calls before hitting limits)
2. Token explosion (250K-760K input tokens on failing queries)
3. Runaway costs ($1.60-2.30 per failed query)

This made sense when sub-agents were causing cascading failures.

## Why 20 is Now Too Restrictive

The prompt rewrite **successfully eliminated sub-agent delegation**, fundamentally changing the threat model:

**Before prompt rewrite:**
- Sub-agents caused exponential LLM call growth
- Recursion limits hit due to coordination overhead spirals
- 20 limit acted as circuit breaker for runaway queries

**After prompt rewrite:**
- Zero sub-agent spawns across all queries
- LLM calls grow linearly with query complexity
- 20 limit now blocks legitimate multi-step queries

### Evidence from Validation

| Query | LLM Calls | Status | Notes |
|-------|-----------|--------|-------|
| Query 1 | 7 | SUCCESS | Well under 20 limit |
| Query 2 | 6 | SUCCESS | Well under 20 limit |
| Query 3 | 10 | FAILED | Hit 20 limit, needed ~12-15 steps |
| Query 4 | 10 | FAILED | Hit 20 limit, needed ~12-15 steps |
| Query 5 | 3 | SUCCESS | Very efficient |

**Query 3 and 4 analysis:**
- Both at 50% of 20-step limit when forced to stop
- Both had reasonable execution (no spirals, no sub-agents)
- Both needed slightly more steps to complete (estimated 12-15)
- Planning overhead: 4-5 write_todos() calls contributing to step count

## Solution: Increase to 50

Changed recursion_limit from 20 to 50 at [netbox_agent.py:966](netbox_agent.py#L966).

### Rationale

**50 provides appropriate headroom:**
- 2.5x the current limit
- 3-4x the needs of failing queries (which needed 12-15 steps)
- Still conservative (20x lower than the 1000 maximum)

**Maintains safety:**
- Still catches runaway queries (>50 steps indicates a real problem)
- Fail-fast behavior preserved (vs unlimited execution)
- Limits cost exposure on pathological queries

**Aligns with post-sub-agent architecture:**
- Sub-agent elimination removed the exponential growth threat
- Current queries show linear growth in complexity
- 50 is appropriate for legitimate multi-step reasoning

### Expected Impact

**Success rate improvement:**
- Current: 60% (3/5 queries succeeded)
- Expected: 100% (5/5 queries succeed)

**Query 3 (VLAN 100) fix:**
- Needed: ~12-15 steps
- New limit: 50 steps
- Expected: Complete successfully with proper "VLAN 100 not found for Jimbob's Banking" message

**Query 4 (NC State racks) fix:**
- Needed: ~12-15 steps
- New limit: 50 steps
- Expected: Complete successfully with full rack inventory and device IPs

**No impact on successful queries:**
- Query 1 (7 steps), Query 2 (6 steps), Query 5 (3 steps) well under 50
- No performance degradation expected

## Alternatives Considered

### Option 1: Keep 20, Reduce Planning Overhead
**Approach:** Modify prompts to limit write_todos() to 1-2 calls max

**Pros:**
- Maintains 20 limit as forcing function for efficiency
- Encourages minimal planning overhead
- Forces prompt optimization

**Cons:**
- Requires more prompt iteration and testing
- May not fully address the issue (Query 3/4 at 10 calls each)
- Planning is often beneficial for complex queries

**Verdict:** ❌ Rejected - too much prompt re-engineering for marginal gain

### Option 2: Increase to 100
**Approach:** Much higher safety margin

**Pros:**
- Very unlikely to hit limit on any legitimate query
- Maximum flexibility

**Cons:**
- May hide inefficiencies (no incentive to optimize)
- Higher potential cost on runaway queries
- Less aggressive fail-fast behavior

**Verdict:** ⚠️ Considered but excessive - 50 is sufficient

### Option 3: Remove Override (Use 1000 from Agent Config)
**Approach:** Let agent use its configured 1000 limit

**Pros:**
- No artificial constraints
- Matches original design intent

**Cons:**
- **Too permissive** - runaway queries could consume 1000 steps
- High cost exposure ($10-50 on pathological queries)
- Defeats purpose of fail-fast safety mechanism

**Verdict:** ❌ Rejected - removes important safety guardrail

## Monitoring Recommendations

After deploying the 50-step limit, monitor:

1. **Query completion rates** - should reach 100%
2. **Step counts** - identify queries approaching 50 (indicates need for optimization)
3. **Cost per query** - ensure no unexpected increases
4. **Token usage** - watch for accumulation patterns

If any queries consistently use 40-50 steps, investigate:
- Is the query overly complex?
- Is planning overhead excessive (>5 write_todos calls)?
- Could prompts be optimized for efficiency?

## Commit Message

```
fix: Increase recursion_limit from 20 to 50 to fix Query 3 and 4 failures

After prompt rewrite eliminated sub-agent delegation, the conservative
20-step limit became too restrictive for legitimate multi-step queries.

Problem:
- Query 3 and 4 failing with "Sorry, need more steps" at 10 LLM calls
- Both needed ~12-15 steps to complete (reasonable for complexity)
- 20 limit was originally set to catch sub-agent delegation spirals
- Sub-agents now eliminated, threat model changed

Solution:
- Increase recursion_limit to 50 at query invocation
- Provides 3-4x headroom for failing queries
- Still maintains safety (50 << 1000 maximum)
- Aligns with post-sub-agent architecture

Expected impact:
- Success rate: 60% → 100%
- Query 3: Will complete with proper "not found" handling
- Query 4: Will complete with full rack inventory
- No impact on currently successful queries (well under 50)

The 50 limit still catches runaway queries while allowing legitimate
multi-step reasoning to complete successfully.
```

## Validation Test Plan

To confirm the fix:

1. **Re-run Query 3** (VLAN 100 search):
   - Expected: SUCCESS with "VLAN 100 not found" message
   - Expected steps: 12-15
   - Verify: Clean "not found" handling with alternatives shown

2. **Re-run Query 4** (NC State racks):
   - Expected: SUCCESS with complete rack inventory
   - Expected steps: 12-15
   - Verify: All racks, devices, and IPs displayed

3. **Verify no regressions**:
   - Query 1, 2, 5 should still succeed
   - Step counts should remain similar

4. **Monitor edge cases**:
   - If any query approaches 45-50 steps, investigate
   - May indicate prompt optimization opportunity

## References

- Original validation: [VALIDATION_TEST_SUITE.md](VALIDATION_TEST_SUITE.md)
- Prompt rewrite: [PROMPT_REWRITE_SUMMARY.md](PROMPT_REWRITE_SUMMARY.md)
- Corrected analysis: analyze_traces_compact.py output
