# Dependency Analyzer MCP Server

A Model Context Protocol (MCP) server for analyzing software dependencies across multiple ecosystems, **powered by AWS Bedrock AI**.

## Features

- **Multi-ecosystem support**: Maven, Gradle, Node.js, Python (Maven implemented, others planned)
- **Auto-detection**: Automatically detects project type from repository structure
- **Local & Remote**: Works with both local repositories and GitHub URLs
- **Dependency Graph**: Builds in-memory dependency graphs for analysis
- **Impact Analysis**: Identifies which modules use specific artifacts
- **SBOM Generation**: Exports minimal CycloneDX-compatible SBOMs
- **Upgrade Recommendations**: Suggests version upgrades based on policies
- **🤖 AI Agent**: Natural language queries powered by AWS Bedrock (Claude, Titan)
- **🎨 Streamlit UI**: Beautiful web interface for interactive analysis

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure AWS credentials (for Bedrock agent)
aws configure
```

## Quick Start

### Option 1: Web UI (Recommended)

```bash
streamlit run app.py
```

Open browser to `http://localhost:8501` and start analyzing!

### Option 2: Command Line

**Analyze a Repository:**

```bash
# Local Maven project
python -m mcp_server.server --repo /path/to/local/maven/project

# GitHub repository
python -m mcp_server.server --repo https://github.com/apache/commons-lang
```

**Ask Questions with AI Agent:**

```bash
# Interactive mode
python agent_integration.py --interactive

# Single query
python agent_integration.py --query "Which modules use log4j?"
```

## Usage

### MCP Server (Programmatic)

```bash
python -m mcp_server.server --repo /path/to/local/maven/project
```

### 2. Analyze a GitHub Repository

```bash
python -m mcp_server.server --repo https://github.com/apache/commons-lang
```

### 3. Run MCP Server (Manual Mode)

```bash
python -m mcp_server.server
```

Then use MCP tools to manually:
- Call `build_dependency_graph` with parsed modules
- Call `artifact_impact` to analyze dependencies
- Call `artifact_recommendation` for upgrade suggestions
- Call `export_sbom` to generate SBOMs

### AI Agent (Natural Language)

The agent uses AWS Bedrock to understand natural language queries and automatically call the right tools.

```bash
# Interactive chat
python agent_integration.py --interactive

# Examples:
🤔 You: Which modules depend on Spring Framework?
🤖 Agent: [Uses artifact_impact tool and provides analysis]

🤔 You: What's the safest way to upgrade log4j?
🤖 Agent: [Uses artifact_recommendation and provides upgrade strategy]

🤔 You: Generate an SBOM for compliance
🤖 Agent: [Uses export_sbom and explains usage]
```

**Single query mode:**
```bash
python agent_integration.py --query "Analyze the security impact of outdated dependencies"
```

See [AGENT_GUIDE.md](AGENT_GUIDE.md) for detailed agent documentation.

## What Goes in Utils?

The `mcp_server/utils/` package contains **shared utility functions** used across multiple components:

### `exec.py` - Command Execution
- `run_command()` - Execute shell commands (mvn, gradle, npm, etc.)
- `run_git_clone()` - Clone Git repositories
- `is_git_repo()` - Check if a path is a Git repo
- `clone_to_temp()` - Clone to temporary directory

**Used by**: All scanners that need external tool invocation (future: Gradle, Node, Python scanners)

### `filesystem.py` - File Operations
- `find_files()` - Search for files by pattern
- `read_xml_safe()` - Safe XML parsing with error handling
- `xml_text()` - Extract text from XML elements
- `detect_ecosystem()` - Auto-detect Maven/Gradle/Node/Python
- `clone_or_use_local()` - Handle both local paths and Git URLs
- `get_project_name()` - Extract project name from path

**Used by**: 
- Scanners (maven_scanner.py, gradle_scanner.py, etc.) - for XML parsing and file detection
- Parsers (maven_parser.py, etc.) - for safe XML reading
- Server (server.py) - for repository handling and ecosystem detection

## Architecture

```
dependency_analyser_tool/
├── agent/                      # 🤖 AI Agent (Bedrock-powered)
│   ├── __init__.py
│   ├── llm.py                 # AWS Bedrock client
│   ├── prompts.py             # System prompts & templates
│   └── agent_runner.py        # Agent orchestration
├── mcp_server/                # MCP Server & Tools
│   ├── server.py              # Main MCP server with CLI
│   ├── utils/                 # Shared utilities
│   │   ├── exec.py           # Command execution, Git ops
│   │   └── filesystem.py     # File ops, ecosystem detection
│   ├── scanners/             # Repository scanners
│   │   ├── maven_scanner.py
│   │   ├── gradle_scanner.py
│   │   ├── node_scanner.py
│   │   └── python_scanner.py
│   ├── parsers/              # Dependency parsers
│   │   ├── maven_parser.py
│   │   ├── gradle_parser.py
│   │   ├── node_parser.py
│   │   └── python_parser.py
│   └── graph/                # Graph analysis
│       ├── graph_builder.py
│       ├── impact_analysis.py
│       ├── recommendations.py
│       └── sbom_generator.py
├── agent_integration.py       # Agent CLI interface
├── requirements.txt
├── README.md
└── AGENT_GUIDE.md            # Detailed agent documentation
```

## Example Output

```bash
$ python -m mcp_server.server --repo https://github.com/apache/commons-lang

[INFO] Processing repository: https://github.com/apache/commons-lang
[INFO] Repository path: C:\Users\...\Temp\dep_analyzer_xyz\commons-lang
[INFO] (Cloned to temporary directory)
[INFO] Detected ecosystem: maven
[INFO] Scan complete: Maven single-module project.
[INFO] Parsing module: commons-lang3
[INFO] Successfully parsed 1 module(s)
[SUCCESS] Dependency graph built successfully!
  - Nodes: 45
  - Edges: 12

[INFO] Repository loaded. Starting MCP server...
```

## Extending to Other Ecosystems

To add support for a new ecosystem (e.g., Gradle):

1. **Implement scanner** in `scanners/gradle_scanner.py`
2. **Implement parser** in `parsers/gradle_parser.py`
3. **Reuse utils** from `utils/exec.py` and `utils/filesystem.py`
4. **Update** `detect_ecosystem()` in `utils/filesystem.py`
5. **Add** ecosystem handling in `server.py`'s `auto_scan_and_build()`

## License

[Your License Here]
