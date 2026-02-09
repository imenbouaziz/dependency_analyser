# MCP Integration Guide

## Overview

The Dependency Analyzer now uses the **Model Context Protocol (MCP)** to provide tools to the AI agent. This creates a standardized interface between the agent and the dependency analysis functions.

## Architecture

```
┌─────────────────┐
│  Streamlit UI   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  AI Agent       │────▶│  SimpleMCPClient │
└─────────────────┘     └────────┬─────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │  MCP Server Functions │
                     │  - artifact_impact    │
                     │  - recommendations    │
                     │  - export_sbom        │
                     └───────────────────────┘
```

## Components

### 1. MCP Client (`mcp_server/client.py`)

**SimpleMCPClient** - In-process MCP client that wraps MCP tools:
- `artifact_impact(artifact_coord)` - Analyze which modules depend on an artifact
- `artifact_recommendation(artifact_coord, policy)` - Get upgrade recommendations
- `export_sbom(project_name)` - Generate CycloneDX SBOM

**MCPClient** (Advanced) - Full subprocess-based client:
- Communicates with MCP server via stdio (JSON-RPC)
- Suitable for remote/distributed setups
- Currently not used in Streamlit app (SimpleMCPClient is sufficient)

### 2. MCP Server (`mcp_server/server.py`)

FastMCP server that exposes tools:
```python
@mcp.tool()
def artifact_impact(artifact_coord: str) -> Dict:
    """Return which modules depend on the given artifact."""
    ...
```

Can be run standalone:
```bash
python -m mcp_server.server --repo /path/to/repo
```

### 3. Agent Integration (`app.py`)

The AI agent registers MCP tools during initialization:
```python
def init_agent():
    mcp = st.session_state.mcp_client
    
    agent.register_tool(
        "artifact_impact",
        lambda artifact_coord: mcp.artifact_impact(artifact_coord),
        "Analyze which modules depend on a specific artifact"
    )
```

## Usage in Streamlit

1. **Repository Scan** - When you analyze a repository:
   - Dependency graph is built
   - MCP client is initialized with the graph
   - Agent tools are connected to MCP client

2. **AI Chat** - When you ask questions:
   - Agent decides which tools to use
   - Tools call MCP client methods
   - MCP client executes graph analysis functions
   - Results are returned to agent → formatted response

## Example Agent Interactions

### Question: "Which modules use spring-core?"

**Agent thinks:**
1. Need to analyze artifact impact
2. Calls `artifact_impact("org.springframework:spring-core:*")`
3. MCP client queries dependency graph
4. Returns list of dependent modules
5. Agent formats natural language response

### Question: "Should I upgrade log4j?"

**Agent thinks:**
1. Need upgrade recommendation
2. Calls `artifact_recommendation("org.apache.logging.log4j:log4j-core:2.14.0")`
3. MCP client checks for newer versions
4. Returns recommendation (e.g., "latest_patch: 2.14.1")
5. Agent provides advice

## Benefits of MCP Integration

✅ **Standardized Protocol** - Tools follow MCP specification
✅ **Discoverable** - Agent can list available tools
✅ **Extensible** - Easy to add new analysis tools
✅ **Stateful** - MCP client maintains graph state
✅ **Testable** - Tools can be tested independently

## Connection Status

The UI shows MCP connection status:
- **Sidebar** - Under "Project Info": "🔌 MCP Client: Connected"
- **AI Chat Tab** - Top right: "🔌 MCP Connected" badge

## Advanced: Full MCP Server (Optional)

For distributed setups, you can use the full subprocess-based MCPClient:

```python
from mcp_server.client import MCPClient

# Start MCP server in subprocess
client = MCPClient()
client.start(repo_path="/path/to/repo")

# Call tools via JSON-RPC
result = client.artifact_impact("org.springframework:spring-core:5.3.0")

# Stop server
client.stop()
```

## Troubleshooting

**"MCP Client: Not initialized"**
- Repository not scanned yet
- Run analysis first from sidebar

**"No MCP client"** in AI Chat
- Graph not loaded
- Scan a repository to initialize

**Agent not using tools**
- Check Ollama is running
- Verify tool descriptions are clear
- Check agent prompts in `agent/prompts.py`
