# LangSmith MCP Server - Project-Only Configuration ✅

## Status: Configured for This Project Only

The LangSmith MCP Server has been reconfigured to be **project-scoped** (local to this deepagents project only).

## Configuration Details

- **Scope**: Local config (private to you in this project)
- **Location**: `/home/ola/dev/rnd/deepagents/`
- **Status**: ✓ Connected
- **Transport**: stdio
- **Command**: `langsmith-mcp-server`

## What This Means

### Available:
✅ **Inside this project** (`/home/ola/dev/rnd/deepagents/`)
- Claude Code sessions in this directory have LangSmith MCP tools
- You can analyze traces when working on this project
- All LangSmith tools accessible: `fetch_trace`, `get_project_runs_stats`, etc.

### NOT Available:
❌ **Outside this project** (other directories)
- LangSmith MCP tools won't be available in other projects
- Keeps your global Claude Code configuration clean
- Other projects won't see LangSmith tools

## Verification

### From This Project:
```bash
cd /home/ola/dev/rnd/deepagents
claude mcp list
# Shows: langsmith: langsmith-mcp-server - ✓ Connected
```

### From Another Directory:
```bash
cd /tmp
claude mcp list
# Shows: No MCP servers configured
```

### Back to This Project:
```bash
cd /home/ola/dev/rnd/deepagents
claude mcp list
# Shows: langsmith: langsmith-mcp-server - ✓ Connected (works again!)
```

## Configuration Storage

The local scope configuration is stored in:
- **File**: `/home/ola/.claude.json`
- **Section**: Project-specific settings for `/home/ola/dev/rnd/deepagents`
- **Not in**: `.claude/mcp_servers.json` (that's for project scope, not local scope)

## Difference: Local vs Project Scope

### Local Scope (what you have now):
- **Visibility**: Only you in this project
- **Stored**: In your personal `~/.claude.json` file
- **Git**: Not checked in (private configuration)
- **Team**: Other developers don't get it automatically

### Project Scope (alternative):
- **Visibility**: Everyone working on this project
- **Stored**: In `.claude/mcp_servers.json` at project root
- **Git**: Can be checked in for team sharing
- **Team**: Other developers get the same MCP configuration

## Usage in Future Sessions

When working in this project:

### Example 1: Analyze Trace
```
You: "Analyze trace a7bce16c-5f9f-4e13-93ed-ae7c30776699"
Claude: *uses LangSmith MCP fetch_trace tool*
Claude: "Trace Analysis: 67.8s execution, 130K tokens, 0% cache hit..."
```

### Example 2: Get Project Stats
```
You: "Show netbox-agent project statistics"
Claude: *uses LangSmith MCP get_project_runs_stats tool*
Claude: "Project stats: 47 runs, avg 2.1s latency..."
```

### Example 3: In Another Project
```
You: *Opens Claude Code in /tmp/some-other-project*
You: "Analyze trace abc123"
Claude: "I don't have access to LangSmith MCP tools in this project."
```

## How to Share with Team (Optional)

If you want team members to have LangSmith too:

### Option 1: Document in README
Add to project README:
```markdown
## LangSmith MCP Setup (Optional)

For trace analysis capabilities:
```bash
pip install langsmith-mcp-server
claude mcp add --transport stdio --scope local langsmith \
  --env LANGSMITH_API_KEY=your-key-here \
  -- langsmith-mcp-server
```
```

### Option 2: Convert to Project Scope
Create `.claude/mcp_servers.json` for team:
```json
{
  "mcpServers": {
    "langsmith": {
      "command": "langsmith-mcp-server",
      "args": [],
      "env": {
        "LANGSMITH_API_KEY": "${LANGSMITH_API_KEY}"
      }
    }
  }
}
```
Then commit: `git add .claude/mcp_servers.json`

## Modifying Configuration

### To Remove:
```bash
claude mcp remove langsmith -s local
```

### To Change Back to Global:
```bash
# Remove local
claude mcp remove langsmith -s local

# Add global
claude mcp add --transport stdio --scope user langsmith \
  --env LANGSMITH_API_KEY=$LANGSMITH_API_KEY \
  -- langsmith-mcp-server
```

### To Update API Key:
```bash
# Remove and re-add with new key
claude mcp remove langsmith -s local
claude mcp add --transport stdio --scope local langsmith \
  --env LANGSMITH_API_KEY=new-key-here \
  -- langsmith-mcp-server
```

## Benefits of Local Scope

1. **Project Isolation**: LangSmith tools only where needed
2. **Clean Global Config**: Doesn't clutter your user-level MCP servers
3. **Privacy**: API key not checked into git accidentally
4. **Flexibility**: Easy to remove or change per-project

## What Got Changed

### Removed:
- ❌ User scope (global) LangSmith MCP configuration
- ❌ Availability in all projects

### Added:
- ✅ Local scope (project-only) LangSmith MCP configuration
- ✅ Availability only in `/home/ola/dev/rnd/deepagents/`

### Files Modified:
- `/home/ola/.claude.json` - Added local-scope configuration for this project

## Testing Checklist

- [x] LangSmith MCP removed from global config
- [x] LangSmith MCP added to local config
- [x] Server shows "✓ Connected" in this project
- [x] Server NOT available in `/tmp` (verified)
- [x] Server available back in project directory (verified)
- [x] Scope confirmed as "Local config (private to you in this project)"

## Next Steps

The setup is complete! You can now:

1. **Work in this project** and ask me to analyze LangSmith traces
2. **Work in other projects** without LangSmith MCP tools available
3. **Run netbox_agent.py** and traces will be sent to LangSmith
4. **Ask for trace analysis** and I'll use the LangSmith MCP tools

---

**Configuration completed on**: 2025-10-12
**Scope**: Local (project-only)
**Status**: Ready to use! 🎉