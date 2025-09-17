# NetBox Interactive CLI Transformation PRP

## Purpose
Transform the existing NetBox agent demo script (`examples/netbox/netbox_agent.py`) from a script with 3 hardcoded examples into a fully interactive CLI that accepts any NetBox query from users while preserving all sophisticated agent capabilities and human-friendly formatting.

## Core Principles
1. **Minimal Changes**: Transform only the main() function and query processing
2. **Backward Compatibility**: Keep all agent logic unchanged
3. **User Experience**: Clear prompts, exit commands, helpful formatting
4. **Error Handling**: Robust error handling prevents CLI crashes
5. **Preserve Capabilities**: All 62 dynamic NetBox tools and agent features intact

---

## Goal

Convert `examples/netbox/netbox_agent.py` from a demo script that runs 3 hardcoded examples sequentially into an interactive CLI application that:

- Accepts any NetBox query from users in a continuous loop
- Provides clear welcome message and usage instructions
- Handles exit commands gracefully (exit, quit, q, Ctrl+C)
- Maintains all existing agent sophistication and tool capabilities
- Preserves human-friendly response formatting with emojis and structure

## Why

- **Flexibility**: Accept any NetBox query instead of 3 fixed examples
- **Interactivity**: Continuous loop for follow-up questions and exploration
- **User-Friendly**: Clear prompts, exit commands, helpful formatting
- **Preservation**: All existing agent sophistication maintained
- **Real-World Usage**: Transform demo into production-ready tool

## What

### Current State (Lines 316-349)
```python
async def main():
    """Main function demonstrating the NetBox agent with human-friendly responses"""

    print("🚀 NetBox Dynamic Agent - Human-Friendly Response Examples")
    print(f"Agent has access to all {len(TOOL_REGISTRY)} NetBox tools!")

    # Example 1: List All Sites
    await run_human_friendly_example(
        "Show me all sites in NetBox",
        "Example 1: Site Inventory Query"
    )

    # Example 2: Specific Site Information
    await run_human_friendly_example(
        "Show me information about site JBB Branch 104",
        "Example 2: Site Details Query"
    )

    # Example 3: Site Device Inventory
    await run_human_friendly_example(
        "Show all devices in site DM-Binghamton",
        "Example 3: Site Device Inventory Query"
    )

    print(f"\n{'='*80}")
    print(" Summary")
    print(f"{'='*80}")
    print("✅ All examples completed successfully!")
```

### Target State
```python
async def main():
    """Interactive NetBox agent CLI with continuous query loop"""

    # Welcome message and instructions
    print("🚀 NetBox Interactive Agent CLI")
    print(f"Agent has access to all {len(TOOL_REGISTRY)} NetBox tools!")
    print("\nAvailable commands:")
    print("  - Type any NetBox query in natural language")
    print("  - 'exit', 'quit', or 'q' to quit")
    print("  - Ctrl+C for immediate exit")
    print(f"\n{'='*60}")

    try:
        while True:
            try:
                # Get user input asynchronously
                query = await get_user_input("\n💬 NetBox Query: ")

                # Handle exit commands
                if query.lower().strip() in ['exit', 'quit', 'q', '']:
                    print("👋 Goodbye!")
                    break

                # Process the query
                await process_netbox_query(query)

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                print("Please try again or type 'exit' to quit.")

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
```

### Success Criteria
- [x] CLI accepts any NetBox query (not just 3 examples)
- [x] Continuous interactive loop with proper exit handling
- [x] Maintains all human-friendly response formatting
- [x] Preserves all 62 dynamic NetBox tools and agent capabilities
- [x] Provides clear user experience with prompts and feedback
- [x] Handles errors gracefully without crashing

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window

- file: examples/netbox/netbox_agent.py
  why: Current implementation with 3 hardcoded examples that needs transformation
  critical_sections:
    - Lines 1-278: Dynamic tool generation logic (PRESERVE COMPLETELY)
    - Lines 280-315: Agent execution functions (PRESERVE COMPLETELY)
    - Lines 316-349: Main function (TRANSFORM TO INTERACTIVE CLI)

- file: examples/netbox/NETBOX_AGENT_TECHNICAL_REPORT.md
  why: Comprehensive documentation of agent architecture and capabilities
  important: Understanding of dynamic tool generation, human-friendly formatting

- url: https://docs.python.org/3/library/asyncio.html#asyncio.to_thread
  why: Preferred method for async user input in Python 3.9+
  pattern: await asyncio.to_thread(input, "prompt")

- url: https://stackoverflow.com/questions/48562893/how-to-gracefully-terminate-an-asyncio-script-with-ctrl-c
  why: Best practices for KeyboardInterrupt handling in asyncio applications
  pattern: try/except KeyboardInterrupt with cleanup

- file: /home/ola/dev/netboxdev/netbox-mcp-docs/netbox-queries
  why: 35 example queries ranging from simple to complex for testing
  examples: "Show me all sites in NetBox", "Generate comprehensive tenant resource report"

- dir: /home/ola/dev/netboxdev/netbox-mcp
  why: NetBox MCP server location (READ ONLY access)
  important: Do NOT make changes to this codebase

- url: https://blog.langchain.com/deep-agents/
  why: DeepAgents framework documentation
  important: Understanding planning tools, sub-agents, virtual filesystem

- url: https://docs.langchain.com/labs/deep-agents/overview
  why: Official DeepAgents documentation
  important: Framework patterns and best practices
```

### Code Patterns to Follow

#### Async Input Pattern (Python 3.9+)
```python
async def get_user_input(prompt: str) -> str:
    """Get user input asynchronously without blocking event loop"""
    return await asyncio.to_thread(input, prompt)
```

#### Error Handling Pattern
```python
try:
    # Process user query
    await process_netbox_query(query)
except KeyboardInterrupt:
    print("\n👋 Goodbye!")
    break
except Exception as e:
    print(f"❌ Error: {str(e)}")
    print("Please try again or type 'exit' to quit.")
```

#### Exit Command Handling
```python
# Normalize and check exit commands
if query.lower().strip() in ['exit', 'quit', 'q', '']:
    print("👋 Goodbye!")
    break
```

### Preserve These Functions Completely
- `get_netbox_client()` (lines 39-45)
- `build_annotations_from_metadata()` (lines 47-79)
- `create_async_tool_wrapper()` (lines 81-132)
- `generate_all_tool_wrappers()` (lines 134-143)
- `organize_tools_by_category()` (lines 145-161)
- `build_enhanced_instructions()` (lines 163-204)
- `list_available_tools()` (lines 207-220)
- `get_tool_details()` (lines 222-252)
- `create_netbox_agent_with_all_tools()` (lines 254-278)
- `extract_agent_response()` (lines 280-289)
- `run_human_friendly_example()` (lines 291-314) - **RENAME** to `process_netbox_query()`

### Implementation Tasks (Sequential Order)

1. **Add async input function** (before main)
   ```python
   async def get_user_input(prompt: str) -> str:
       """Get user input asynchronously without blocking event loop"""
       try:
           return await asyncio.to_thread(input, prompt)
       except EOFError:
           return "exit"  # Handle Ctrl+D
   ```

2. **Rename and adapt run_human_friendly_example()**
   ```python
   async def process_netbox_query(query: str):
       """Process a NetBox query and show human-friendly response"""
       print(f"\n🔄 Processing: {query}")

       try:
           result = await netbox_agent.ainvoke({
               "messages": [{"role": "user", "content": query}]
           }, config={'recursion_limit': 20})

           response, msg_count = extract_agent_response(result)

           print(f"\n🤖 NetBox Agent Response:")
           print("-" * 60)
           print(response)
           print("-" * 60)
           print(f"📊 Messages: {msg_count}")

       except Exception as e:
           print(f"❌ Query failed: {str(e)}")
           raise
   ```

3. **Replace main() function**
   ```python
   async def main():
       """Interactive NetBox agent CLI with continuous query loop"""

       # Welcome message
       print("🚀 NetBox Interactive Agent CLI")
       print(f"Agent has access to all {len(TOOL_REGISTRY)} NetBox tools!")
       print("\nAvailable commands:")
       print("  - Type any NetBox query in natural language")
       print("  - 'exit', 'quit', or 'q' to quit")
       print("  - Ctrl+C for immediate exit")
       print(f"\n{'='*60}")

       try:
           while True:
               try:
                   # Get user input
                   query = await get_user_input("\n💬 NetBox Query: ")

                   # Handle exit commands
                   if query.lower().strip() in ['exit', 'quit', 'q', '']:
                       print("👋 Goodbye!")
                       break

                   # Process the query
                   await process_netbox_query(query)

               except KeyboardInterrupt:
                   print("\n👋 Goodbye!")
                   break
               except Exception as e:
                   print(f"❌ Error: {str(e)}")
                   print("Please try again or type 'exit' to quit.")

       except KeyboardInterrupt:
           print("\n👋 Goodbye!")
   ```

4. **Add signal handling for graceful shutdown** (optional enhancement)
   ```python
   import signal

   def setup_signal_handlers():
       """Setup signal handlers for graceful shutdown"""
       def signal_handler(signum, frame):
           print("\n👋 Received interrupt signal, goodbye!")
           sys.exit(0)

       signal.signal(signal.SIGINT, signal_handler)
       signal.signal(signal.SIGTERM, signal_handler)
   ```

### Testing Strategy

Use example queries from `/home/ola/dev/netboxdev/netbox-mcp-docs/netbox-queries`:

**Simple Queries (Immediate testing)**:
- "Check NetBox server health"
- "Show me all sites in NetBox"
- "List all devices"
- "What manufacturers are configured?"

**Intermediate Queries (Functionality validation)**:
- "Show me information about site JBB Branch 104"
- "Get detailed information about device dmi01-akron-pdu01"
- "Show all devices in site DM-Binghamton"

**Complex Queries (Stress testing)**:
- "Generate a comprehensive tenant resource report for tenant Dunder-Mifflin, Inc."
- "Show me a complete infrastructure audit for site NC State University"

**Error Handling Tests**:
- Invalid site names
- Malformed queries
- Empty input
- Ctrl+C interruption
- Multiple exit commands

## Final Validation Checklist

- [ ] CLI starts with clear welcome message and instructions
- [ ] User can enter any NetBox query and get response
- [ ] Exit commands work: 'exit', 'quit', 'q', empty input
- [ ] Ctrl+C exits gracefully with goodbye message
- [ ] Error handling prevents crashes on bad queries
- [ ] All 62 NetBox tools remain accessible
- [ ] Human-friendly response formatting preserved (emojis, structure)
- [ ] Agent capabilities unchanged (planning, tools, formatting)
- [ ] No errors when testing with example queries
- [ ] Performance unchanged from original implementation

### Specific Test Commands
```bash
# Start the interactive CLI
cd /home/ola/dev/rnd/deepagents/examples/netbox
python netbox_agent.py

# Test basic functionality
> Show me all sites in NetBox
> Check NetBox server health
> List all devices
> exit

# Test error handling
> invalid query with nonsense
> <empty input>
> <Ctrl+C>
```

---

## Anti-Patterns to Avoid

- ❌ Don't modify the dynamic tool generation logic (lines 1-278)
- ❌ Don't change agent creation or configuration
- ❌ Don't alter NetBox client management or error handling patterns
- ❌ Don't use blocking input() function - use asyncio.to_thread
- ❌ Don't ignore KeyboardInterrupt - handle gracefully
- ❌ Don't remove human-friendly formatting features
- ❌ Don't hardcode prompts or responses - keep flexible
- ❌ Don't make changes to /home/ola/dev/netboxdev/netbox-mcp
- ❌ Don't create new dependencies - use stdlib asyncio
- ❌ Don't change the agent's recursion limit or tool access

## Implementation Notes

### Key Benefits of This Approach
1. **Minimal Risk**: Only changes main() and adds helper functions
2. **Preserves Everything**: All agent capabilities remain intact
3. **User-Friendly**: Clear CLI experience with helpful prompts
4. **Robust**: Proper error handling and graceful shutdown
5. **Flexible**: Accepts any NetBox query, not just examples

### Error Scenarios Handled
- Invalid NetBox queries → User-friendly error, continue loop
- Empty input → Treat as exit command
- Ctrl+C/Ctrl+D → Graceful goodbye message
- Agent processing errors → Show error, don't crash
- Network/API errors → Handled by existing error handling

### Backwards Compatibility
- All existing functions preserved unchanged
- Agent behavior identical for any given query
- Tool registry and capabilities unchanged
- Response formatting maintains emojis and structure
- Error handling patterns preserved

This transformation converts the demo script into a production-ready interactive tool while maintaining 100% of the existing sophisticated agent capabilities.

---

## Quality Assessment

### Context Completeness Score: 9/10
- ✅ All necessary documentation URLs provided (Python asyncio, error handling)
- ✅ Critical code sections identified with line numbers
- ✅ Existing patterns documented and preserved
- ✅ Testing strategy with real example queries
- ✅ Implementation tasks in sequential order
- ⚠️ Could include more async CLI examples, but sufficient for implementation

### Validation Gates Quality: 10/10
- ✅ Executable test commands provided
- ✅ Error handling scenarios documented
- ✅ Manual testing with real NetBox queries
- ✅ Performance validation checklist
- ✅ Backwards compatibility verification

### Implementation Blueprint Quality: 10/10
- ✅ Clear pseudocode for all new functions
- ✅ Specific line number references for changes
- ✅ Preservation of all existing functionality
- ✅ Error handling strategy documented
- ✅ Sequential implementation tasks listed

### Self-Validation Capability: 9/10
- ✅ AI agent can run provided test commands
- ✅ Clear success/failure criteria
- ✅ Comprehensive error scenario coverage
- ✅ Iterative refinement possible with validation loop
- ✅ Real-world query examples for testing

### Anti-Pattern Documentation: 10/10
- ✅ Clear warnings about what NOT to change
- ✅ Specific line ranges to preserve
- ✅ Technology constraints documented
- ✅ Risk mitigation strategies provided

## Final PRP Confidence Score: 9.5/10

**Rationale**: This PRP provides comprehensive context, clear implementation steps, and robust validation gates. The AI agent has all necessary information to implement the interactive CLI transformation in a single pass while preserving all sophisticated agent capabilities. The only minor area for improvement would be additional async CLI reference examples, but the provided patterns are sufficient for successful implementation.

**Expected Implementation Success Rate**: 95% - One-pass implementation highly likely given the comprehensive context and minimal-risk approach focusing only on main() function transformation.