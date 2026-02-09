# Streamlit UI Guide

## Running the UI

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Features

### 1. **Repository Analysis**
- Enter a local path or GitHub URL in the sidebar
- Click "Analyze Repository" to scan and build the dependency graph
- Supports Maven (Gradle, Node, Python coming soon)

### 2. **Overview Tab** 📊
- View project statistics
- Browse all dependencies in a searchable table
- Export SBOM (CycloneDX JSON format)

### 3. **Impact Analysis Tab** 🔎
- Enter an artifact coordinate (e.g., `org.springframework:spring-core:5.3.0`)
- See which modules depend on it
- Understand the impact of removing or upgrading

### 4. **Recommendations Tab** 💡
- Get upgrade suggestions for specific artifacts
- Choose upgrade policy: patch, minor, or major
- View recommended versions

### 5. **AI Chat Tab** 🤖
- Ask questions in natural language (requires AWS Bedrock)
- Chat history is maintained during the session
- Quick question buttons for common queries

## Screenshot Tour

### Home Screen
```
📦 Dependency Analyzer
================================

👈 Enter a repository path or URL in the sidebar to get started!

🔍 Auto-Detection           📊 Dependency Analysis      🤖 AI-Powered
Automatically detects       Build dependency graphs,    Ask questions in
Maven, Gradle, Node.js,     analyze impacts, and        natural language using
and Python projects         get recommendations          AWS Bedrock
```

### After Loading a Project
```
Sidebar:
  ⚙️ Configuration
  Repository: [github.com/spring-projects/spring-boot]
  [🔍 Analyze Repository]
  
  📊 Project Info
  Name: spring-boot
  Ecosystem: maven
  Nodes: 456
  Edges: 789

Main Area - Overview Tab:
  ┌─────────────┬──────────────┬──────────────┬──────────────┐
  │ spring-boot │    maven     │     456      │     789      │
  │   Project   │  Ecosystem   │ Dependencies │ Relationships│
  └─────────────┴──────────────┴──────────────┴──────────────┘
  
  📦 All Dependencies
  [Searchable table with Artifact, Type, Module columns]
```

### AI Chat Interface
```
🤖 AI Assistant
💬 Ask questions about your dependencies in natural language!

[Chat bubbles showing conversation]

You: Which modules use Spring Framework?
Assistant: Based on the dependency graph analysis...
  - module-a depends on spring-core:5.3.0
  - module-b depends on spring-web:5.3.0
  ...

[💬 Chat input box]

Quick Questions:
[📋 List all dependencies] [🔐 Check for vulnerabilities]
[📊 Generate SBOM]         [🔄 Suggest upgrades]
```

## Usage Examples

### Example 1: Analyze Apache Commons Lang

1. Enter in sidebar: `https://github.com/apache/commons-lang`
2. Click "Analyze Repository"
3. Wait for scanning (shows progress bar)
4. View results in Overview tab

### Example 2: Check Impact of Upgrade

1. Go to "Impact Analysis" tab
2. Enter: `org.junit.jupiter:junit-jupiter-api:5.8.0`
3. Click "Analyze Impact"
4. See which modules would be affected

### Example 3: Get AI Recommendations

1. Go to "AI Chat" tab
2. Type: "What dependencies should I upgrade for security?"
3. Agent analyzes and provides recommendations
4. Follow up with: "Show me an upgrade plan"

## Keyboard Shortcuts

- **Ctrl + K**: Clear chat (when in chat tab)
- **Enter**: Submit question (in chat input)
- **R**: Rerun app (Streamlit built-in)

## Configuration

### Theme
Edit `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

### AWS Credentials
Set environment variables or use AWS CLI:

```bash
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_REGION="us-east-1"
```

## Deployment

### Streamlit Cloud

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repository
4. Add secrets in Streamlit Cloud dashboard:
   ```
   AWS_ACCESS_KEY_ID = "xxx"
   AWS_SECRET_ACCESS_KEY = "xxx"
   AWS_REGION = "us-east-1"
   ```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:
```bash
docker build -t dependency-analyzer .
docker run -p 8501:8501 dependency-analyzer
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'streamlit'"
```bash
pip install streamlit
```

### "Port 8501 already in use"
```bash
streamlit run app.py --server.port=8502
```

### "AWS credentials not found"
- Run `aws configure`
- Or set environment variables
- Or use IAM roles (if on EC2/ECS)

### App is slow
- Use Claude Haiku instead of Sonnet for faster responses
- Limit max_tokens in agent configuration
- Cache common queries

## Tips

1. **Use Example Repos**: Click the example buttons on home screen to try it out
2. **Download SBOM**: Export and save SBOMs for compliance
3. **Chat History**: Chat is preserved during session, click "Clear" to reset
4. **Quick Questions**: Use the quick question buttons for common queries
5. **Search Dependencies**: Use the table search in Overview tab

## Advanced Features

### Custom Styling

Add to `app.py`:
```python
st.markdown("""
<style>
    /* Your custom CSS */
</style>
""", unsafe_allow_html=True)
```

### Add New Tools

In `app.py`, register more tools with the agent:

```python
agent.register_tool(
    "check_licenses",
    lambda: check_licenses_func(),
    "Check license compatibility"
)
```

### Export Visualizations

Install plotly and create graph visualizations:

```bash
pip install plotly
```

```python
import plotly.graph_objects as go

# Create network graph visualization
st.plotly_chart(fig, use_container_width=True)
```

## Support

For issues or feature requests, check the main [README.md](README.md) and [AGENT_GUIDE.md](AGENT_GUIDE.md).
