# NetBox Agent Validation Test Suite

## Purpose

This file contains the 5 cross-domain queries used to validate the prompt rewrite effectiveness. These queries are **NOT included in the system prompts** to avoid data contamination and ensure the agent generalizes the classification principles correctly.

## Test Data Source

NetBox v4.4 Demo Instance: https://demo.netbox.dev/
- 3 primary tenants: Dunder-Mifflin, NC State University, Jimbob's Banking
- ~60 devices, 18 sites, 29 racks

## Baseline Performance (Original Prompts)

| Query | Tool Calls | LLM Calls | Time | Cost | Result |
|-------|-----------|-----------|------|------|--------|
| Query 1 | 75 | 76 | 347s | $2.00 | SUCCESS (but inefficient) |
| Query 2 | 12 | 13 | 58s | $0.51 | SUCCESS |
| Query 3 | 30 | 31 | 162s | $1.60 | FAILED |
| Query 4 | 19 | 20 | 91s | $0.77 | FAILED |
| Query 5 | 41 | 32 | 149s | $2.30 | FAILED |
| **Total** | **177** | **172** | **807s** | **$7.18** | **40% success** |

## Claude Code Performance (Reference)

| Query | Tool Calls | Time | Cost | Result |
|-------|-----------|------|------|--------|
| Query 1 | 3 | 15s | $0.09 | SUCCESS |
| Query 2 | 3 | ~10s | $0.08 | SUCCESS |
| Query 3 | 5 | 15s | $0.12 | SUCCESS |
| Query 4 | 6 | 20s | $0.09 | SUCCESS |
| Query 5 | 9 | 25s | $0.14 | SUCCESS |
| **Total** | **26** | **85s** | **$0.52** | **100% success** |

## Expected Performance (After Prompt Rewrite)

| Query | Expected Tool Calls | Expected Classification | Sub-agents Expected |
|-------|---------------------|------------------------|---------------------|
| Query 1 | 5-8 | TIER 2 - Sequential | NO |
| Query 2 | 2-3 | TIER 1 - Direct | NO |
| Query 3 | 2-3 | TIER 1 - Direct | NO |
| Query 4 | 5-8 | TIER 2 - Sequential | NO |
| Query 5 | 8-12 | TIER 1 - Direct | NO |
| **Total** | **22-34** | - | **ZERO** |

Target metrics:
- Success rate: 100% (all 5 queries complete)
- Total cost: ~$0.50-0.70
- Total time: ~80-100 seconds
- Sub-agent spawns: 0 (critical validation criterion)

---

## Query 1: Tenant Sites Summary

**Query Text**:
```
Show all Dunder-Mifflin sites with device counts, rack allocations, and IP prefix assignments
```

**Expected Classification**: TIER 2 - Sequential Execution

**Why this tests the prompt**:
- Multi-site query spanning 3 domains (Tenancy, DCIM, IPAM)
- Original prompts classified as "CROSS-DOMAIN" → spawned sub-agents
- Has sequential dependencies (tenant_id → sites → devices/racks)
- Should use bulk queries with tenant_id filter, NOT site-by-site iteration

**Expected execution**:
1. Get tenant_id for "Dunder-Mifflin"
2. Bulk query devices (filter by tenant_id), group by site
3. Bulk query racks (filter by tenant_id)
4. Bulk query prefixes (filter by tenant_id)

**Success criteria**:
- ✅ No task() tool calls (no sub-agents)
- ✅ Uses bulk queries (5-8 total calls, not 75)
- ✅ Completes successfully with correct device count (39 devices)
- ✅ Execution time <30s

---

## Query 2: Device Configuration

**Query Text**:
```
For device dmi01-nashua-rtr01, show location details, assigned IP addresses, and tenant ownership
```

**Expected Classification**: TIER 1 - Direct Execution

**Why this tests the prompt**:
- Single device lookup with related data
- Spans 3 domains but very simple (device object contains site/tenant)
- Original had 12 calls due to planning overhead
- Should be 2-3 direct calls

**Expected execution**:
1. Get device by name (includes site, tenant in response)
2. Get IPs for device_id

**Success criteria**:
- ✅ No task() tool calls (no sub-agents)
- ✅ No write_todos() (too simple for planning)
- ✅ 2-3 tool calls total
- ✅ Execution time <15s

---

## Query 3: VLAN Deployment Search

**Query Text**:
```
Show where VLAN 100 is deployed across Jimbob's Banking sites
```

**Expected Classification**: TIER 1 - Direct Execution (negative result handling)

**Why this tests the prompt**:
- **CRITICAL**: VLAN 100 doesn't exist for Jimbob's Banking
- Original prompts caused sub-agent search spiral (30 calls, 162s, FAILED)
- Tests negative result handling
- Should gracefully report "not found" and suggest alternatives

**Expected execution**:
1. Get tenant_id for "Jimbob's Banking"
2. Search VLANs (filter by tenant_id, vid=100)
3. Empty result → Report "VLAN 100 not found, here are existing VLANs..."

**Success criteria**:
- ✅ No task() tool calls (no sub-agents)
- ✅ 2-3 tool calls total (NOT 30)
- ✅ Completes successfully (NOT failure)
- ✅ Gracefully handles negative result
- ✅ Execution time <20s

---

## Query 4: Rack Inventory

**Query Text**:
```
For NC State University racks at Butler Communications site, show installed devices with their IP addresses
```

**Expected Classification**: TIER 2 - Sequential Execution (dependencies)

**Why this tests the prompt**:
- Sequential dependencies: tenant → site → racks → devices → IPs
- Original prompts spawned sub-agents for "parallel" execution (19 calls, FAILED)
- Dependencies prevent true parallelization
- Should execute sequentially in main agent

**Expected execution**:
1. Get tenant_id for "NC State University"
2. Get site_id for "Butler Communications" (filter by tenant_id)
3. Get racks at site (filter by site_id)
4. Get devices (filter by site_id + tenant_id)
5. Get IPs for devices

**Success criteria**:
- ✅ No task() tool calls (no sub-agents)
- ✅ May use write_todos() for planning (acceptable)
- ✅ 5-8 tool calls total (NOT 19)
- ✅ Completes successfully (NOT failure)
- ✅ Execution time <30s

---

## Query 5: Site Comparison

**Query Text**:
```
Compare infrastructure utilization across DM-Nashua, DM-Akron, and DM-Scranton sites
```

**Expected Classification**: TIER 1 - Direct Execution (small dataset)

**Why this tests the prompt**:
- Only 3 sites (small dataset)
- Original prompts spawned sub-agents (41 calls, 149s, FAILED)
- Tests the "<10 entities" anti-pattern
- Should execute sequentially, 3 sites is too small for delegation

**Expected execution**:
1. Get site IDs for the 3 sites
2. For each site: get devices, racks, prefixes (bulk queries)
3. Calculate utilization metrics
4. Format comparison table

**Success criteria**:
- ✅ No task() tool calls (no sub-agents)
- ✅ 8-12 tool calls total (NOT 41)
- ✅ Completes successfully (NOT failure)
- ✅ Execution time <30s

---

## Validation Protocol

### 1. Pre-validation Checks
- [ ] Verify prompts.py does NOT contain specific query text (data contamination check)
- [ ] Verify prompts.py contains anti-patterns and principles
- [ ] Verify netbox_agent.py is using updated prompts.py

### 2. Execution
Run each query and record:
- Tool calls made (list all tool names)
- LLM calls count
- Sub-agent spawns (task() calls) - should be ZERO
- Planning overhead (write_todos(), think() calls)
- Execution time
- Final result (SUCCESS/FAILED)
- Cost

### 3. Analysis
Compare against:
- Baseline performance (original prompts)
- Claude Code reference
- Expected performance targets

### 4. Success Metrics
**PASS criteria** (all must be met):
- ✅ All 5 queries complete successfully (100% success rate)
- ✅ ZERO task() tool calls across all queries (no sub-agent delegation)
- ✅ Total tool calls <40 (vs 177 baseline)
- ✅ Total cost <$1.00 (vs $7.18 baseline)
- ✅ Total time <150s (vs 807s baseline)
- ✅ Each query completes in <30s

**FAIL criteria** (any triggers failure):
- ❌ Any query uses task() tool (sub-agent delegation)
- ❌ Any query hits recursion limit
- ❌ Success rate <100%
- ❌ Query 3 fails or spirals searching (>5 tool calls)
- ❌ Query 1 uses site-by-site iteration (>15 tool calls)

### 5. Root Cause Analysis (if failures occur)
If any query fails or spawns sub-agents, analyze:
- What prompt section guided the decision?
- Was classification correct?
- Did anti-patterns fail to prevent delegation?
- Is prompt language ambiguous?
- Does example set need adjustment?

---

## Notes

**Data Contamination Prevention**:
This test suite is kept separate from prompts.py to ensure the agent generalizes classification principles rather than pattern-matching specific queries.

**LangSmith Trace Analysis**:
When running validation, capture trace IDs for detailed analysis:
```python
# In netbox_agent.py
os.environ["LANGCHAIN_PROJECT"] = "netbox-agent-validation"
```

**Comparison Fairness**:
Claude Code has advantages (tighter integration, better caching). The goal is NOT to match Claude Code exactly, but to:
1. Eliminate failures (40% → 100% success)
2. Prevent sub-agent delegation spirals
3. Achieve reasonable efficiency (closer to Claude Code than baseline)
