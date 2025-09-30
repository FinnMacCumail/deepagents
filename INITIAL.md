# Feature Request Template

## FEATURE:
We want to devlop our existing deepagent application to be able to handle cross domain queries.
We need to use netbox_agent.py as a starting point and develop the application to handle  handle cross domain queries as well as Simple and Intermediate Queries.
Using the deepagent frameworks existing planning architecture, develop the application to also handle cross domain netbox queries. This will implemented via a combination of four things: a **planning tool**, **sub agents**, access to a **file system**, and a **detailed prompt**.

# Current NetBox Agent Architecture Analysis
The current NetBox agent includes substantial static context that gets sent with every API call:

1. **Enhanced Instructions** 
   - Agent role and goals
   - Tool categories and descriptions
   - Tool selection strategies

2. **Tool Definitions**
   - 64 dynamically read only generated tool descriptions
   - Parameter specifications for each tool
   - Tool discovery functions

3. **Conversation History** (Variable, grows with each turn)
   - Previous messages and tool calls
   - Context accumulation over time

4. **Handles Simple Queries & Intermediate Queries**
   - Show me all sites in NetBox
   - Show me information about site JBB Branch 104

5. **Caching Strategy**
   - The following components are cached, system_prompt, tool_definitions, netbox_categories

# Cross Domain Implementation Strategy
### 1. When to determine that Cross Domain planning is required
We need to devlop the existing agent to act as a supervisor.
We need to improve the existing query handler to be able to distinguish cross domain queries. This MUST ONLY be done through clear and concise prompting.
Ensure that the existing logic for handling simple and intermediate queries remain.
### 2. Planning
   - We will use TODOs to keep track of tasks.
   - The deepagent built tools to manage the todo list will be utilised when necessary    
### 3. Sub Agent Delegation
   - We will delegate netbox doamin tasks to sub-agents for context isolation.
   - Sub Agent delegation will be passed the appropriate mcp netbox tool for it's task
   - Tools will use the LangGraph Command to update both the virtual file system,used in planning, and messages
### 4. Strategic Thinking ( think tool ):
   - We will give our main (supervisor) agent a think tool to rrovides a structured reflection mechanism for the agent to analyze findings, assess gaps, and plan next steps in the workflow.


## EXAMPLES:
A list of Simple and Intermediate example netbox queries can be found here - /home/ola/dev/netboxdev/netbox-mcp-docs/netbox-queries
A list of Cross Domain Queries that are relevant for this development can be found here - /home/ola/dev/netboxdev/netbox-mcp-docs/Cross-Domain-Queries.md
MUST refer to https://github.com/langchain-ai/deep-agents-from-scratch/blob/main/notebooks/4_full_agent.ipynb for guidance 


## DOCUMENTATION:
- Information regarding the deepagents application code base currently developed can be found here - url:https://blog.langchain.com/deep-agents/ & https://docs.langchain.com/labs/deep-agents/overview
- Information which will help can be found here - https://files.cdn.thinkific.com/file_uploads/967498/attachments/e77/0b3/5ef/Deep_Agents.pdf
The netbox mcp server application used can be located here - /home/ola/dev/netboxdev/netbox-mcp
This is the information regarding The NetBox Dynamic Agent - (examples/netbox/NETBOX_AGENT_TECHNICAL_REPORT.md)

# The netbox mcp server provides READ ONLY netbox api tools.
# Do NOT make any changes to the codebase in /home/ola/dev/netboxdev/netbox-mcp