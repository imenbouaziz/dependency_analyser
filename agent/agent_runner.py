"""
agent_runner.py
Main agent orchestration for dependency analysis with tool calling.
"""

from __future__ import annotations
import re
import json
from typing import Dict, List, Optional, Any, Callable
from agent.llm import OllamaLLM, create_ollama_client
from agent.prompts import SYSTEM_PROMPT, TOOL_INSTRUCTIONS, ERROR_MESSAGES


class DependencyAgent:
    """
    Intelligent agent for dependency analysis using Ollama.
    
    The agent can:
    - Answer questions about dependencies
    - Use MCP tools to analyze the dependency graph
    - Provide recommendations and insights
    - Generate reports and SBOMs
    """
    
    def __init__(
        self,
        llm: Optional[OllamaLLM] = None,
        tools: Optional[Dict[str, Callable]] = None,
        max_iterations: int = 5,
        verbose: bool = True
    ):
        """
        Initialize the dependency agent.
        
        Args:
            llm: OllamaLLM instance (or create default)
            tools: Dictionary of available tools {name: function}
            max_iterations: Maximum tool-calling iterations
            verbose: Whether to print intermediate steps
        """
        self.llm = llm or create_ollama_client()
        self.tools = tools or {}
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.conversation_history: List[Dict] = []
    
    def register_tool(self, name: str, function: Callable, description: str = ""):
        """
        Register a tool for the agent to use.
        
        Args:
            name: Tool name
            function: Callable function
            description: Tool description (optional)
        """
        self.tools[name] = {
            "function": function,
            "description": description
        }
    
    def _extract_tool_call(self, response: str) -> Optional[Dict]:
        """
        Extract tool call from agent response.
        
        Expected format:
        **Action:** tool_name
        **Action Input:** {"param": "value"}
        
        Returns:
            {"tool": "tool_name", "input": {...}} or None
        """
        # Pattern to match Action and Action Input
        action_pattern = r'\*\*Action:\*\*\s*(\w+)'
        input_pattern = r'\*\*Action Input:\*\*\s*({.*?})'
        
        action_match = re.search(action_pattern, response, re.IGNORECASE)
        input_match = re.search(input_pattern, response, re.IGNORECASE | re.DOTALL)
        
        if action_match:
            tool_name = action_match.group(1).strip()
            
            # Try to parse input JSON
            tool_input = {}
            if input_match:
                try:
                    tool_input = json.loads(input_match.group(1))
                except json.JSONDecodeError:
                    # Try to extract as dict string
                    input_str = input_match.group(1).strip()
                    tool_input = {"raw": input_str}
            
            return {
                "tool": tool_name,
                "input": tool_input
            }
        
        return None
    
    def _execute_tool(self, tool_name: str, tool_input: Dict) -> Dict:
        """
        Execute a tool and return the result.
        
        Args:
            tool_name: Name of the tool
            tool_input: Input parameters
        
        Returns:
            Tool execution result
        """
        if tool_name not in self.tools:
            return {
                "error": f"Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}"
            }
        
        try:
            tool_func = self.tools[tool_name]["function"]
            result = tool_func(**tool_input)
            return result
        except Exception as e:
            return {
                "error": f"Tool execution failed: {str(e)}"
            }
    
    def _detect_tool_from_query(self, query: str, context: Optional[Dict] = None) -> Optional[Dict]:
        """
        Detect which tool to call based on query keywords and context.
        Fallback method when LLM is unavailable.
        
        Args:
            query: User query
            context: Additional context
        
        Returns:
            Dict with tool name and input, or None
        """
        query_lower = query.lower()
        
        # Check context action hint first
        if context and "action" in context:
            action = context["action"]
            
            if action == "scan_repository" and "repo_path" in context:
                return {
                    "tool": "scan_repository",
                    "input": {"repo_path_or_url": context["repo_path"]}
                }
            elif action == "artifact_impact" and "artifact" in context:
                return {
                    "tool": "artifact_impact",
                    "input": {"artifact_coord": context["artifact"]}
                }
            elif action == "artifact_recommendation" and "artifact" in context:
                return {
                    "tool": "artifact_recommendation",
                    "input": {
                        "artifact_coord": context["artifact"],
                        "policy": context.get("policy", "latest_patch")
                    }
                }
            elif action == "export_sbom":
                return {
                    "tool": "export_sbom",
                    "input": {"project_name": context.get("project_name")}
                }
        
        # Extract artifact coordinate pattern (group:artifact:version or group:artifact)
        artifact_pattern = r'([a-zA-Z0-9\-_.]+:[a-zA-Z0-9\-_.]+(?::[0-9.]+)?)'
        artifact_match = re.search(artifact_pattern, query)
        
        # Keyword-based detection
        if any(word in query_lower for word in ["scan", "analyze", "repository", "repo"]):
            # Extract repo path from query
            repo_match = re.search(r'(?:repo|repository|path):\s*(\S+)', query, re.IGNORECASE)
            if repo_match:
                return {
                    "tool": "scan_repository",
                    "input": {"repo_path_or_url": repo_match.group(1)}
                }
            # Look for path-like strings
            path_match = re.search(r'(?:[A-Z]:\\|/|https?://)\S+', query)
            if path_match:
                return {
                    "tool": "scan_repository",
                    "input": {"repo_path_or_url": path_match.group(0)}
                }
        
        if any(word in query_lower for word in ["impact", "affected", "depend", "use"]) and artifact_match:
            return {
                "tool": "artifact_impact",
                "input": {"artifact_coord": artifact_match.group(1)}
            }
        
        if any(word in query_lower for word in ["recommend", "upgrade", "update", "version"]) and artifact_match:
            policy = "latest_patch"
            if "major" in query_lower:
                policy = "latest_major"
            elif "minor" in query_lower:
                policy = "latest_minor"
            
            return {
                "tool": "artifact_recommendation",
                "input": {
                    "artifact_coord": artifact_match.group(1),
                    "policy": policy
                }
            }
        
        if any(word in query_lower for word in ["sbom", "export", "cyclonedx", "bill of materials"]):
            return {
                "tool": "export_sbom",
                "input": {"project_name": context.get("project_name") if context else None}
            }
        
        return None

    def run(self, query: str, context: Optional[Dict] = None) -> str:
        """
        Run the agent with a user query.
        First tries to use LLM, falls back to direct tool calling if LLM fails.
        
        Args:
            query: User's question or request
            context: Additional context (e.g., graph state, project info)
        
        Returns:
            Agent's final response
        """
        # Build system prompt
        system_prompt = SYSTEM_PROMPT
        if context:
            system_prompt += f"\n\n**Current Context:**\n{json.dumps(context, indent=2)}"
        
        # Add tool instructions
        system_prompt += f"\n\n{TOOL_INSTRUCTIONS}"
        
        # Initialize conversation with user query
        messages = [{"role": "user", "content": query}]
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Query: {query}")
            print(f"{'='*60}\n")
        
        # Try LLM-based agent loop first
        llm_failed = False
        
        # Agent loop
        for iteration in range(self.max_iterations):
            if self.verbose:
                print(f"[Iteration {iteration + 1}/{self.max_iterations}]")
            
            # Get LLM response
            response = self.llm.invoke(messages, system=system_prompt)
            
            # Check if LLM failed (connection error, etc.)
            if "error" in response:
                if self.verbose:
                    print(f"[LLM Error: {response['error']}]")
                llm_failed = True
                break
            
            content = response["content"]
            
            if self.verbose:
                print(f"\nAgent Response:\n{content}\n")
            
            # Check if agent wants to use a tool
            tool_call = self._extract_tool_call(content)
            
            if tool_call:
                tool_name = tool_call["tool"]
                tool_input = tool_call["input"]
                
                if self.verbose:
                    print(f"[Executing Tool: {tool_name}]")
                    print(f"Input: {json.dumps(tool_input, indent=2)}\n")
                
                # Execute tool
                tool_result = self._execute_tool(tool_name, tool_input)
                
                if self.verbose:
                    print(f"Tool Result:\n{json.dumps(tool_result, indent=2)}\n")
                
                # Add assistant response and tool observation to conversation
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": f"**Observation:** {json.dumps(tool_result, indent=2)}\n\nContinue your analysis."
                })
            else:
                # No tool call - agent is done
                if self.verbose:
                    print("[Agent finished]\n")
                
                return content
        
        # If LLM failed or didn't call tools, try fallback direct tool calling
        if llm_failed or iteration >= self.max_iterations - 1:
            if self.verbose:
                print("[Attempting fallback: Direct tool calling]\n")
            
            detected_tool = self._detect_tool_from_query(query, context)
            
            if detected_tool:
                tool_name = detected_tool["tool"]
                tool_input = detected_tool["input"]
                
                if self.verbose:
                    print(f"[Detected Tool: {tool_name}]")
                    print(f"Input: {json.dumps(tool_input, indent=2)}\n")
                
                # Execute tool directly
                tool_result = self._execute_tool(tool_name, tool_input)
                
                if self.verbose:
                    print(f"Tool Result:\n{json.dumps(tool_result, indent=2)}\n")
                
                # Format result as response
                if "error" in tool_result:
                    return f"❌ Error: {tool_result['error']}"
                else:
                    return f"**Tool:** {tool_name}\n\n**Result:**\n```json\n{json.dumps(tool_result, indent=2)}\n```"
            else:
                # No tool detected, return error or LLM content
                if llm_failed:
                    return f"❌ LLM unavailable and couldn't detect appropriate tool for query: '{query}'\n\nAvailable tools: {list(self.tools.keys())}"
                else:
                    # Return last content from LLM
                    return response.get("content", "") + "\n\n[Note: Maximum iterations reached.]"
        
        # Max iterations reached (normal LLM flow)
        return content + "\n\n[Note: Maximum iterations reached. Response may be incomplete.]"
    
    def chat(self, message: str, reset: bool = False) -> str:
        """
        Interactive chat interface with conversation memory.
        Falls back to direct tool calling if LLM is unavailable.
        
        Args:
            message: User message
            reset: Whether to reset conversation history
        
        Returns:
            Agent response
        """
        if reset:
            self.conversation_history = []
        
        self.conversation_history.append({"role": "user", "content": message})
        
        # Try using LLM
        response = self.llm.invoke(self.conversation_history, system=SYSTEM_PROMPT)
        
        if "error" in response:
            # LLM failed, try fallback
            if self.verbose:
                print(f"[Chat LLM Error: {response['error']}]")
                print("[Attempting fallback: Direct tool calling]\n")
            
            detected_tool = self._detect_tool_from_query(message)
            
            if detected_tool:
                tool_name = detected_tool["tool"]
                tool_input = detected_tool["input"]
                
                if self.verbose:
                    print(f"[Detected Tool: {tool_name}]")
                    print(f"Input: {json.dumps(tool_input, indent=2)}\n")
                
                # Execute tool directly
                tool_result = self._execute_tool(tool_name, tool_input)
                
                # Format result
                if "error" in tool_result:
                    content = f"❌ Error: {tool_result['error']}"
                else:
                    content = f"**Tool:** {tool_name}\n\n**Result:**\n```json\n{json.dumps(tool_result, indent=2)}\n```"
                
                self.conversation_history.append({"role": "assistant", "content": content})
                return content
            else:
                # No tool detected, return error message
                error_msg = f"❌ LLM unavailable: {response.get('error', 'Unknown error')}\n\nCouldn't detect appropriate tool for your message.\n\nAvailable tools: {list(self.tools.keys())}"
                self.conversation_history.append({"role": "assistant", "content": error_msg})
                return error_msg
        
        # LLM succeeded
        content = response["content"]
        self.conversation_history.append({"role": "assistant", "content": content})
        
        return content


def create_agent_with_mcp_tools(
    build_graph_func: Callable,
    impact_func: Callable,
    recommendation_func: Callable,
    sbom_func: Callable,
    **llm_kwargs
) -> DependencyAgent:
    """
    Create an agent with MCP tools registered.
    
    Args:
        build_graph_func: build_dependency_graph function
        impact_func: artifact_impact function
        recommendation_func: artifact_recommendation function
        sbom_func: export_sbom function
        **llm_kwargs: Additional arguments for OllamaLLM
    
    Returns:
        Configured DependencyAgent
    """
    llm = create_ollama_client(**llm_kwargs)
    agent = DependencyAgent(llm=llm)
    
    # Register MCP tools
    agent.register_tool(
        "build_dependency_graph",
        build_graph_func,
        "Build a dependency graph from parsed modules"
    )
    
    agent.register_tool(
        "artifact_impact",
        impact_func,
        "Find which modules use a specific artifact (format: group:artifact:version)"
    )
    
    agent.register_tool(
        "export_sbom",
        sbom_func,
        "Export a CycloneDX SBOM for the project"
    )
    
    return agent


# Example usage
if __name__ == "__main__":
    # This is a placeholder - in real usage, you'd import from mcp_server
    def mock_artifact_impact(artifact_coord: str) -> Dict:
        """Mock impact analysis."""
        return {
            "artifact": artifact_coord,
            "affected_modules": ["module-a", "module-b"],
            "dependency_count": 2
        }
    
    # Create agent
    agent = DependencyAgent()
    agent.register_tool("artifact_impact", mock_artifact_impact, "Analyze artifact impact")
    
    # Run query
    result = agent.run(
        "What is the impact of upgrading log4j-core to version 2.17.1?",
        context={"project": "my-java-app", "ecosystem": "maven"}
    )
    
    print("\n" + "="*60)
    print("Final Answer:")
    print("="*60)
    print(result)
