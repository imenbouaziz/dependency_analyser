"""
Agent package for intelligent dependency analysis using Ollama.
"""

from agent.llm import OllamaLLM, create_ollama_client, OLLAMA_MODELS
from agent.agent_runner import DependencyAgent, create_agent_with_mcp_tools
from agent.prompts import (
    SYSTEM_PROMPT,
    TOOL_INSTRUCTIONS,
    QUERY_TEMPLATES,
    RESPONSE_TEMPLATES,
    ERROR_MESSAGES,
)

__all__ = [
    "OllamaLLM",
    "create_ollama_client",
    "OLLAMA_MODELS",
    "DependencyAgent",
    "create_agent_with_mcp_tools",
    "SYSTEM_PROMPT",
    "TOOL_INSTRUCTIONS",
    "QUERY_TEMPLATES",
    "RESPONSE_TEMPLATES",
    "ERROR_MESSAGES",
]
