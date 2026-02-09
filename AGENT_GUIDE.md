# Agent Implementation Guide

## Overview

The `agent/` folder contains a complete AWS Bedrock-powered AI agent for intelligent dependency analysis. The agent can understand natural language queries, use MCP tools, and provide insightful recommendations.

## Architecture

```
agent/
├── __init__.py          # Package exports
├── llm.py              # AWS Bedrock LLM client
├── prompts.py          # System prompts and templates
└── agent_runner.py     # Agent orchestration and tool calling
```

## Components

### 1. `llm.py` - AWS Bedrock Integration

**BedrockLLM Class:**
- Supports multiple Bedrock models (Claude, Titan, etc.)
- Handles API authentication via AWS credentials
- Provides both standard and streaming invocation
- Auto-detects model family and formats requests appropriately

**Supported Models:**
```python
BEDROCK_MODELS = {
    "claude-3.5-sonnet": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "titan-express": "amazon.titan-text-express-v1",
    "titan-lite": "amazon.titan-text-lite-v1",
}
```

**Usage:**
```python
from agent.llm import create_bedrock_client

# Default (Claude 3.5 Sonnet)
llm = create_bedrock_client()

# Custom model
llm = create_bedrock_client(
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    region_name="us-west-2"
)

# Invoke
response = llm.invoke([
    {"role": "user", "content": "Explain dependency injection"}
])
print(response["content"])
```

### 2. `prompts.py` - Prompt Engineering

**Components:**
- `SYSTEM_PROMPT`: Core agent personality and capabilities
- `TOOL_INSTRUCTIONS`: How to use tools in responses
- `QUERY_TEMPLATES`: Pre-built query templates for common tasks
- `RESPONSE_TEMPLATES`: Formatted response structures
- `ERROR_MESSAGES`: Standardized error handling

**Key Templates:**
- Impact analysis
- Vulnerability checking
- Upgrade strategies
- Dependency conflicts
- SBOM generation

### 3. `agent_runner.py` - Agent Orchestration

**DependencyAgent Class:**
- Manages conversation with Bedrock LLM
- Parses tool calls from agent responses
- Executes MCP tools and feeds results back
- Handles multi-turn reasoning (up to max_iterations)

**Tool Calling Protocol:**
The agent uses a specific format to call tools:

```
**Thought:** I need to check which modules use log4j
**Action:** artifact_impact
**Action Input:** {"artifact_coord": "org.apache.logging.log4j:log4j-core:2.14.1"}
```

The agent then receives an observation and continues reasoning.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

The agent needs AWS credentials to access Bedrock. Set up using any of these methods:

**Option A: AWS CLI**
```bash
aws configure
```

**Option B: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-east-1"
```

**Option C: IAM Role** (if running on EC2/ECS/Lambda)
- Attach an IAM role with Bedrock permissions

### 3. Enable Bedrock Models

In AWS Console:
1. Go to Amazon Bedrock
2. Navigate to "Model access"
3. Request access to desired models (e.g., Claude 3.5 Sonnet)
4. Wait for approval (usually instant for Claude models)

### 4. Set Environment Variables (Optional)

```bash
# Choose your preferred model
export BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0"

# Set region
export AWS_REGION="us-east-1"
```

## Usage Examples

### Example 1: Single Query

```python
from agent import DependencyAgent, create_bedrock_client
from mcp_server.server import STATE

# Assume graph is already loaded in STATE

llm = create_bedrock_client()
agent = DependencyAgent(llm=llm)

# Register tools
agent.register_tool("artifact_impact", lambda artifact_coord: {...})

# Run query
response = agent.run("What dependencies does module-a have?")
print(response)
```

### Example 2: Interactive Chat

```bash
# First, load a repository
python -m mcp_server.server --repo /path/to/repo

# Then run the agent in interactive mode
python agent_integration.py --interactive
```

### Example 3: Integration with MCP Server

```python
from agent_integration import run_agent_query

# Query the loaded dependency graph
result = run_agent_query(
    "Which modules would be affected if I upgrade Spring Boot to 3.2.0?"
)
print(result)
```

## Common Use Cases

### 1. Impact Analysis

```bash
python agent_integration.py --query "What is the impact of removing log4j-core?"
```

The agent will:
1. Use `artifact_impact` tool to find affected modules
2. Analyze the dependency relationships
3. Provide a risk assessment
4. Suggest mitigation strategies

### 2. Upgrade Planning

```bash
python agent_integration.py --query "Create an upgrade plan for Spring Framework 5.x to 6.x"
```

The agent will:
1. Check current versions using the graph
2. Use `artifact_recommendation` for upgrade paths
3. Identify breaking changes
4. Suggest testing strategies

### 3. Vulnerability Assessment

```bash
python agent_integration.py --query "Are there any vulnerable dependencies in this project?"
```

The agent will:
1. Analyze dependency versions
2. Check for known vulnerabilities
3. Prioritize by severity
4. Recommend patches

### 4. SBOM Generation

```bash
python agent_integration.py --query "Generate an SBOM for compliance"
```

The agent will:
1. Use `export_sbom` tool
2. Explain SBOM contents
3. Suggest use cases for the SBOM

## Advanced Configuration

### Custom Model Selection

```python
from agent.llm import BedrockLLM

# Use Claude 3 Haiku (faster, cheaper)
llm = BedrockLLM(
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    temperature=0.5,  # More deterministic
    max_tokens=2048
)
```

### Streaming Responses

```python
from agent.llm import create_bedrock_client

llm = create_bedrock_client()

for chunk in llm.stream_invoke([{"role": "user", "content": "Explain..."}]):
    print(chunk, end="", flush=True)
```

### Custom Tools

```python
agent = DependencyAgent()

# Add custom tool
def check_licenses(artifact_coord: str):
    # Your implementation
    return {"license": "Apache-2.0", "compatible": True}

agent.register_tool(
    "check_licenses",
    check_licenses,
    "Check license compatibility for an artifact"
)
```

## Cost Considerations

**Bedrock Pricing (approximate, verify with AWS):**
- Claude 3.5 Sonnet: ~$3 per 1M input tokens, ~$15 per 1M output tokens
- Claude 3 Haiku: ~$0.25 per 1M input tokens, ~$1.25 per 1M output tokens
- Titan Express: ~$0.20 per 1M input/output tokens

**Tips to reduce costs:**
1. Use Claude Haiku for simple queries
2. Set lower `max_tokens` limits
3. Use `temperature=0` for deterministic outputs (reduces retries)
4. Cache common queries
5. Implement rate limiting for production use

## Troubleshooting

### Error: "Could not connect to Bedrock"

**Check:**
- AWS credentials are configured
- Region supports Bedrock (us-east-1, us-west-2, etc.)
- IAM permissions include `bedrock:InvokeModel`

### Error: "Model access denied"

**Solution:**
- Go to AWS Bedrock console
- Request model access
- Wait for approval (usually instant)

### Error: "Throttling exception"

**Solution:**
- Implement exponential backoff
- Request quota increase in AWS Service Quotas
- Use Haiku for high-volume scenarios

### Agent not calling tools correctly

**Check:**
- Tool names match exactly
- System prompt includes tool descriptions
- Agent response parsing is working
- Increase `max_iterations` if needed

## Best Practices

1. **Always validate tool outputs** before using in production
2. **Use verbose=True during development** to debug agent reasoning
3. **Set reasonable max_iterations** (3-5) to prevent infinite loops
4. **Cache frequent queries** to reduce API costs
5. **Monitor Bedrock usage** in AWS CloudWatch
6. **Test with different models** to find the best cost/performance balance
7. **Implement proper error handling** for production deployments

## Security Notes

- Never commit AWS credentials to version control
- Use IAM roles when possible
- Implement rate limiting for public-facing deployments
- Sanitize user inputs before passing to tools
- Use AWS CloudTrail to audit Bedrock API calls

## Next Steps

1. **Extend tool set**: Add more MCP tools for richer analysis
2. **Add caching**: Implement response caching for common queries
3. **Build UI**: Create a web interface for the agent
4. **Add memory**: Implement long-term conversation memory
5. **Multi-agent**: Coordinate multiple specialized agents

## Support

For issues:
- Check AWS Bedrock documentation
- Review CloudWatch logs
- Enable verbose mode for debugging
- Test with simple queries first
