# Quick Start Guide

This guide will get you up and running with the Dependency Analyzer in 5 minutes.

## Prerequisites

- Python 3.8+
- Ollama (for AI agent - optional)
- Git installed

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Launch the UI (Easiest!)

```bash
streamlit run app.py
```

Open your browser to `http://localhost:8501` and you're ready! 🎉

**Skip to Step 5** if using the UI. Continue reading for CLI usage.

## Step 3 (CLI Only): Configure Ollama (for AI Agent)

```bash
# Install Ollama from https://ollama.ai
# Then pull a model:
ollama pull llama2

# Or use a different model:
# ollama pull mistral
# ollama pull codellama
```

**Start Ollama:**
1. Ollama runs automatically on installation
2. Default endpoint: `http://localhost:11434`
3. Verify it's running: `ollama list`

## Step 4 (CLI Only): Analyze a Repository

### Option A: Local Repository

```bash
python -m mcp_server.server --repo C:\path\to\your\maven\project
```

### Option B: GitHub Repository

```bash
python -m mcp_server.server --repo https://github.com/spring-projects/spring-boot
```

You should see:
```
[INFO] Processing repository: ...
[INFO] Detected ecosystem: maven
[INFO] Scan complete: Maven multi-module project with 45 modules.
[SUCCESS] Dependency graph built successfully!
  - Nodes: 234
  - Edges: 456
```

## Step 5: Using the Streamlit UI

### Navigate the Interface

1. **Sidebar**: Enter repository path/URL and click "Analyze Repository"
2. **Overview Tab**: View project stats, browse dependencies, export SBOM
3. **Impact Analysis Tab**: Check which modules use specific artifacts
4. **Recommendations Tab**: Get upgrade suggestions
5. **AI Chat Tab**: Ask questions in natural language (requires Ollama)

### Try Example Repositories

Click any of the example buttons on the home screen:
- Apache Commons Lang
- Spring Boot
- JUnit 5

### Use the AI Assistant

1. Go to "AI Chat" tab
2. Click quick question buttons or type your own:
   - "Which modules use Spring Framework?"
   - "Are there security vulnerabilities?"
   - "Recommend safe upgrades"
   - "Generate an SBOM for compliance"

## Step 6 (CLI Only): Ask Questions with AI

In a **separate terminal**, run:

```bash
python agent_integration.py --interactive
```

**Try these queries:**

```
🤔 You: What dependencies does this project have?
🤔 You: Which modules use Spring Framework?
🤔 You: Are there any security vulnerabilities?
🤔 You: Recommend upgrades for outdated dependencies
🤔 You: Generate an SBOM
```

## Step 5: Single Query Mode

```bash
# Analyze specific artifact
python agent_integration.py --query "What is the impact of upgrading log4j to 2.17.1?"

# Check vulnerabilities
python agent_integration.py --query "List all dependencies with known CVEs"

# Generate SBOM
python agent_integration.py --query "Create a CycloneDX SBOM for compliance"
```

## What Just Happened?

1. **Server loaded your repo** - Cloned/read the repository
2. **Auto-detected ecosystem** - Identified it as Maven/Gradle/Node/Python
3. **Scanned modules** - Found all pom.xml/build.gradle/package.json files
4. **Parsed dependencies** - Extracted all dependencies from each module
5. **Built dependency graph** - Created an in-memory graph of all relationships
6. **Started AI agent** - Connected to Ollama for natural language queries

## Common Use Cases

### 1. Security Audit

```bash
python agent_integration.py --query "Perform a security audit of all dependencies"
```

### 2. Upgrade Planning

```bash
python agent_integration.py --query "Create a safe upgrade plan for Spring Boot 2.x to 3.x"
```

### 3. Impact Analysis

```bash
python agent_integration.py --query "If I remove commons-lang3, what breaks?"
```

### 4. License Compliance

```bash
python agent_integration.py --query "Generate an SBOM and explain license implications"
```

## Troubleshooting

### "No dependency graph loaded"

**Problem:** You didn't run the server first.

**Solution:**
```bash
# Terminal 1: Start server with repo
python -m mcp_server.server --repo /path/to/repo

# Terminal 2: Run agent
python agent_integration.py --interactive
```

### "Could not connect to Ollama"

**Problem:** Ollama not running or not configured.

**Solution:**
1. Install Ollama from https://ollama.ai
2. Run `ollama serve` to start the server
3. Pull a model: `ollama pull llama2`
4. Verify: `curl http://localhost:11434/api/tags`

### "No pom.xml found at repository root"

**Problem:** Not a Maven project or pom.xml in subdirectory.

**Solution:**
- Ensure you're pointing to the root directory
- Check if it's a different ecosystem (Gradle/Node/Python)
- Use `--help` to see options

## Next Steps

- Read [AGENT_GUIDE.md](AGENT_GUIDE.md) for advanced agent features
- Check [README.md](README.md) for architecture details
- Explore different Ollama models for better performance
- Customize prompts in `agent/prompts.py`

## Example Session

```bash
# Terminal 1
$ python -m mcp_server.server --repo https://github.com/apache/commons-lang
[INFO] Processing repository: https://github.com/apache/commons-lang
[INFO] Repository path: C:\Users\...\Temp\dep_analyzer_xyz\commons-lang
[INFO] (Cloned to temporary directory)
[INFO] Detected ecosystem: maven
[INFO] Scan complete: Maven single-module project.
[INFO] Parsing module: commons-lang3
[INFO] Successfully parsed 1 module(s)
[SUCCESS] Dependency graph built successfully!
  - Nodes: 12
  - Edges: 8
[INFO] Repository loaded. Starting MCP server...

# Terminal 2
$ python agent_integration.py --interactive

====================================================================
 Dependency Analyzer Agent - Interactive Mode
====================================================================

Ask questions about your dependencies!
Commands: 'quit' or 'exit' to stop, 'reset' to clear history

📦 Project: commons-lang
📊 Graph: 12 nodes, 8 edges

🤔 You: What are the main dependencies?

🤖 Agent: **Thought:** I need to check the dependency graph to identify the main dependencies.

**Action:** artifact_impact
**Action Input:** {"artifact_coord": "org.apache.commons:commons-lang3:*"}

**Observation:** {...}

Based on the dependency analysis, Apache Commons Lang has the following main dependencies:

1. **JUnit 5** (test scope)
   - junit-jupiter-api
   - junit-jupiter-params
   
2. **Hamcrest** (test scope)
   - hamcrest-all
   
3. **Commons Parent** (parent POM)
   - Provides shared configuration

All dependencies are in test scope, meaning this is a foundational library with minimal runtime dependencies. This is excellent for avoiding dependency conflicts in downstream projects.

🤔 You: exit

👋 Goodbye!
```

## Success!

You now have a fully functional dependency analyzer with AI capabilities! 🎉
```