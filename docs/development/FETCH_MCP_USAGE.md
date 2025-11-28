# Fetch MCP Server - Quick Reference Guide

## Configuration Complete ✅

The Fetch MCP server has been added to this project's Claude Code configuration.

**File:** `/home/ola/dev/rnd/deepagents/.mcp.json`
**Server:** `@tokenizin/mcp-npx-fetch` (via npx)
**Status:** ✅ Committed to git (7fb0f49)

---

## Important: Restart Required

**You MUST restart your Claude Code session to activate the fetch server!**

### How to Restart

**Method 1 - Exit and Re-enter Chat:**
1. Type `/exit` or close this chat session
2. Start a new Claude Code chat session in this project
3. The fetch server will be loaded automatically

**Method 2 - Restart Claude Code:**
1. Fully quit Claude Code application
2. Reopen Claude Code
3. Open this project

---

## First Use - Server Approval

When you first try to use the fetch server, Claude Code will prompt:

```
Project-scoped MCP server detected: fetch
Source: /home/ola/dev/rnd/deepagents/.mcp.json

Do you want to allow this server to run?
[Allow Once] [Always Allow for this Project] [Deny]
```

**Action:** Click **"Always Allow for this Project"** (recommended)

**Why:** This is a security feature to prevent malicious MCP servers from executing automatically.

---

## Available Tools (4 Total)

### 1. `fetch_markdown` - Convert HTML to Markdown

**Best for:** Documentation, blog posts, articles, tutorials

**Example:**
```
User: "Fetch https://python.langchain.com/docs/how_to/trim_messages/ as markdown and summarize the key points"

Expected: Claude fetches the page, converts to markdown, and summarizes
```

**Use Cases:**
- Reading documentation
- Researching blog posts
- Analyzing tutorials
- Comparing implementations

---

### 2. `fetch_html` - Raw HTML Content

**Best for:** When you need the complete HTML structure

**Example:**
```
User: "Fetch the HTML from https://github.com/langchain-ai/langgraph and extract all the links"

Expected: Claude gets raw HTML and processes it
```

**Use Cases:**
- Web scraping (respectful)
- Extracting specific elements
- Analyzing page structure
- Finding links/resources

---

### 3. `fetch_json` - Parse JSON APIs

**Best for:** API data retrieval and analysis

**Example:**
```
User: "Fetch JSON from https://api.github.com/repos/langchain-ai/langgraph/releases/latest"

Expected: Claude fetches and parses the JSON response
```

**Use Cases:**
- GitHub API queries
- Public API data
- Configuration files
- JSON endpoints

---

### 4. `fetch_text` - Plain Text Extraction

**Best for:** When you only need text content (strips HTML tags)

**Example:**
```
User: "Fetch https://www.example.com as plain text"

Expected: Claude extracts only the text, no HTML
```

**Use Cases:**
- Text-only content
- Simple reading
- Content analysis
- When HTML formatting doesn't matter

---

## Quick Test Commands

After restarting Claude Code, try these to verify it's working:

### Test 1: Basic Fetch
```
"Fetch https://www.example.com in markdown format"
```
**Expected:** Returns example.com content as markdown

---

### Test 2: LangGraph Documentation
```
"Fetch the LangGraph documentation on pre_model_hook from
https://langchain-ai.github.io/langgraph/how-tos/create-react-agent-manage-message-history/
and explain how to use it"
```
**Expected:** Fetches docs and provides explanation

---

### Test 3: GitHub API
```
"Get the latest LangGraph release info from GitHub API"
```
**Expected:** Fetches from https://api.github.com/repos/langchain-ai/langgraph/releases/latest

---

### Test 4: List MCP Servers
```
Type in chat: /mcp
```
**Expected Output:**
```
Available MCP servers:
- langsmith (project) - ✅ Active
- fetch (project) - ✅ Active
```

---

## Powerful Combined Workflows

### Workflow 1: Research + Analysis

**Scenario:** Compare documentation vs. implementation

```
User: "Fetch the official LangGraph documentation on message trimming,
       then analyze our NetBox agent traces to see if we're implementing it correctly"

Claude will:
1. Use fetch_markdown to get LangGraph docs
2. Use mcp__langsmith__fetch_trace to get our traces
3. Compare implementation vs. best practices
4. Provide recommendations
```

---

### Workflow 2: Token Optimization Research

**Scenario:** Stay current with latest optimization strategies

```
User: "Fetch Anthropic's engineering blog posts about context management
       and compare their recommendations to our token usage stats"

Claude will:
1. Use fetch to get Anthropic blog posts
2. Use mcp__langsmith__get_project_runs_stats for our stats
3. Compare approaches
4. Suggest improvements
```

---

### Workflow 3: Framework Updates

**Scenario:** Check for new LangGraph features

```
User: "Fetch the LangGraph changelog and check if there are any
       new features relevant to our message trimming implementation"

Claude will:
1. Use fetch_markdown to get changelog
2. Identify relevant features
3. Suggest adoption strategies
```

---

### Workflow 4: Competitive Analysis

**Scenario:** Compare MCP implementations

```
User: "Fetch examples of MCP server implementations from GitHub
       and compare their session management patterns with our LangSmith setup"

Claude will:
1. Use fetch to get GitHub repository examples
2. Analyze patterns
3. Compare with our implementation
4. Identify improvements
```

---

## Troubleshooting

### Issue: "fetch server not found" or "tools not available"

**Cause:** Claude Code hasn't loaded the new configuration

**Solution:**
1. ✅ Fully restart Claude Code session
2. ✅ Exit and start new chat
3. ✅ Type `/mcp` to verify server is loaded

---

### Issue: "Server requires approval" prompt

**Cause:** First-time use of project-scoped server (security feature)

**Solution:**
1. ✅ Click "Always Allow for this Project"
2. ✅ This is normal and expected behavior
3. ✅ Only need to approve once per project

---

### Issue: "Fetch failed" or "Network error"

**Possible Causes:**
- URL is unreachable
- Network connectivity issue
- Website blocking requests
- Invalid URL

**Solutions:**
1. ✅ Verify URL works: `curl <URL>`
2. ✅ Check URL spelling
3. ✅ Try a different URL to test
4. ✅ Check if website allows bot access

---

### Issue: "First npx run is slow"

**Cause:** npx downloads the package on first use

**Solution:**
- ✅ Wait for initial download (30-60 seconds)
- ✅ Subsequent runs will be fast (cached)
- ✅ Pre-install if preferred: `npm install -g @tokenizin/mcp-npx-fetch`

---

## Configuration Details

### Current `.mcp.json`

```json
{
  "mcpServers": {
    "langsmith": {
      "type": "stdio",
      "command": "langsmith-mcp-server",
      "args": [],
      "env": {
        "LANGSMITH_API_KEY": "YOUR_LANGSMITH_API_KEY_HERE"
      }
    },
    "fetch": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@tokenizin/mcp-npx-fetch"],
      "env": {}
    }
  }
}
```

### What Each Server Provides

**LangSmith (`langsmith`):**
- ✅ Trace analysis
- ✅ Project statistics
- ✅ Dataset management
- ✅ Performance metrics

**Fetch (`fetch`):**
- ✅ Web content retrieval
- ✅ API data fetching
- ✅ Documentation access
- ✅ Research capabilities

---

## Best Practices

### 1. Be Respectful of Websites

- ✅ Don't scrape at scale
- ✅ Respect robots.txt when possible
- ✅ Don't hammer servers with requests
- ✅ Follow website terms of service

### 2. Choose the Right Tool

- **fetch_markdown:** Most documentation and articles
- **fetch_json:** API responses
- **fetch_html:** When you need structure
- **fetch_text:** When you only need text

### 3. Combine with LangSmith

- Use fetch for external research
- Use LangSmith for internal analysis
- Combine both for comprehensive insights

### 4. Verify URLs

- Test URLs work before asking Claude to fetch
- Use `curl <URL>` to verify accessibility
- Check for typos in URLs

---

## Example Use Cases for This Project

### Use Case 1: Token Optimization Research

```
"Fetch the latest articles about LLM context management and token optimization,
 then compare the strategies with our netbox-agent performance data"
```

**Why:** Combines external research with internal metrics

---

### Use Case 2: LangGraph Updates

```
"Check the LangGraph GitHub releases for any updates related to pre_model_hook
 or message trimming that we should adopt"
```

**Why:** Stay current with framework improvements

---

### Use Case 3: MCP Best Practices

```
"Fetch examples of successful MCP server integrations and compare their
 patterns with our LangSmith and Fetch setup"
```

**Why:** Learn from other implementations

---

### Use Case 4: Documentation Verification

```
"Fetch the official Anthropic documentation on Claude API caching and
 verify our implementation in netbox_agent.py matches best practices"
```

**Why:** Ensure compliance with official guidance

---

## Reset Server Approvals (If Needed)

If you want to reset your approval choices for project-scoped servers:

```bash
claude mcp reset-project-choices
```

This will prompt for approval again next time you use the server.

---

## References

**Fetch MCP Server:**
- Package: https://www.npmjs.com/package/@tokenizin/mcp-npx-fetch
- GitHub: https://github.com/tokenizin-agency/mcp-npx-fetch

**MCP Documentation:**
- Official: https://docs.claude.com/en/docs/claude-code/mcp
- Protocol: https://modelcontextprotocol.io/

**Project Configuration:**
- File: `/home/ola/dev/rnd/deepagents/.mcp.json`
- Commit: 7fb0f49 (2025-10-14)

---

## Summary

**Status:** ✅ Fetch MCP server configured and committed

**Next Step:** Restart Claude Code session to activate

**Tools Available:** 4 fetch tools (markdown, HTML, JSON, text)

**Integration:** Works alongside LangSmith for research + analysis workflows

**Scope:** Project-specific (only active in this repository)

---

**Created:** 2025-10-14
**Last Updated:** 2025-10-14
**Status:** Ready for use after session restart
