"""
MCP Client for connecting to the Dependency Analyzer MCP Server.
"""

import subprocess
import json
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path


class MCPClient:
    """Client for interacting with the MCP server via stdio."""
    
    def __init__(self, server_script: str = None):
        """
        Initialize MCP client.
        
        Args:
            server_script: Path to the MCP server script (default: mcp_server/server.py)
        """
        if server_script is None:
            # Default to the server.py in the same directory
            server_script = str(Path(__file__).parent / "server.py")
        
        self.server_script = server_script
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
    
    def start(self, repo_path: Optional[str] = None) -> bool:
        """
        Start the MCP server process.
        
        Args:
            repo_path: Optional repository path to pre-load
        
        Returns:
            True if server started successfully
        """
        try:
            cmd = [sys.executable, "-m", "mcp_server.server"]
            if repo_path:
                cmd.extend(["--repo", repo_path])
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Wait a moment for server to initialize
            import time
            time.sleep(1)
            
            return self.process.poll() is None
        except Exception as e:
            print(f"Failed to start MCP server: {e}")
            return False
    
    def stop(self):
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call an MCP tool.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
        
        Returns:
            Tool result
        """
        if not self.process or self.process.poll() is not None:
            return {"error": "MCP server not running"}
        
        arguments = arguments or {}
        
        # Build JSON-RPC request
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            # Send request
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()
            
            # Read response
            response_line = self.process.stdout.readline()
            if not response_line:
                return {"error": "No response from server"}
            
            response = json.loads(response_line)
            
            if "error" in response:
                return {"error": response["error"].get("message", "Unknown error")}
            
            return response.get("result", {})
            
        except Exception as e:
            return {"error": f"Tool call failed: {str(e)}"}
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from the MCP server.
        
        Returns:
            List of tool definitions
        """
        if not self.process or self.process.poll() is not None:
            return []
        
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/list"
        }
        
        try:
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()
            
            response_line = self.process.stdout.readline()
            if not response_line:
                return []
            
            response = json.loads(response_line)
            return response.get("result", {}).get("tools", [])
            
        except Exception as e:
            print(f"Failed to list tools: {e}")
            return []
    
    def build_dependency_graph(self, parsed_modules: List[Dict]) -> Dict[str, Any]:
        """Build dependency graph from parsed modules."""
        return self.call_tool("build_dependency_graph", {"parsed_modules": parsed_modules})
    
    def artifact_impact(self, artifact_coord: str) -> Dict[str, Any]:
        """Get impact analysis for an artifact."""
        return self.call_tool("artifact_impact", {"artifact_coord": artifact_coord})
    
    def artifact_recommendation(self, artifact_coord: str, policy: str = "latest_patch") -> Dict[str, Any]:
        """Get upgrade recommendation for an artifact."""
        return self.call_tool("artifact_recommendation", {
            "artifact_coord": artifact_coord,
            "policy": policy
        })
    
    def export_sbom(self, project_name: str = "java-project") -> Dict[str, Any]:
        """Export SBOM for the project."""
        return self.call_tool("export_sbom", {"project_name": project_name})
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


class SimpleMCPClient:
    """
    Simplified MCP client that uses in-process tools instead of subprocess.
    Falls back to direct function calls when MCP server communication fails.
    """
    
    def __init__(self, graph: Dict = None, project_name: str = None, session_state=None):
        """
        Initialize simple MCP client.
        
        Args:
            graph: Pre-loaded dependency graph
            project_name: Project name
            session_state: Streamlit session state object
        """
        # Import the tools directly
        from mcp_server.graph.impact_analysis import impact_summary
        from mcp_server.graph.recommendations import recommend_upgrade
        from mcp_server.graph.sbom_generator import generate_minimal_sbom
        from mcp_server.utils.filesystem import clone_or_use_local, detect_ecosystem, get_project_name
        from mcp_server.scanners.maven_scanner import scan_maven_repo_with_code_analysis
        from mcp_server.parsers.maven_parser import parse_maven_module
        from mcp_server.graph.graph_builder import build_graph
        
        self.graph = graph or {}
        self.project_name = project_name
        self.session_state = session_state
        self._impact_summary = impact_summary
        self._recommend_upgrade = recommend_upgrade
        self._generate_sbom = generate_minimal_sbom
        self._clone_or_use_local = clone_or_use_local
        self._detect_ecosystem = detect_ecosystem
        self._get_project_name = get_project_name
        self._scan_maven = scan_maven_repo_with_code_analysis
        self._parse_maven_module = parse_maven_module
        self._build_graph = build_graph
    
    def artifact_impact(self, artifact_coord: str) -> Dict[str, Any]:
        """Get impact analysis for an artifact."""
        if not self.graph:
            return {"error": "No dependency graph loaded"}
        return self._impact_summary(self.graph, artifact_coord)
    
    def artifact_recommendation(self, artifact_coord: str, policy: str = "latest_patch") -> Dict[str, Any]:
        """Get upgrade recommendation for an artifact."""
        return self._recommend_upgrade(artifact_coord, policy)
    
    def export_sbom(self, project_name: str = None) -> Dict[str, Any]:
        """Export SBOM for the project."""
        if not self.graph:
            return {"error": "No dependency graph loaded"}
        
        sbom = self._generate_sbom(self.graph, project_name or self.project_name)
        
        # Store SBOM in session state for download
        if self.session_state is not None:
            self.session_state.sbom_data = sbom
        
        return sbom
    
    def scan_repository(self, repo_path_or_url: str) -> Dict[str, Any]:
        """
        Scan and analyze a repository.
        
        Args:
            repo_path_or_url: Local path or Git URL
            
        Returns:
            Result dictionary with success/error information
        """
        try:
            # Step 1: Clone or use local
            repo_result = self._clone_or_use_local(repo_path_or_url)
            if not repo_result["success"]:
                return {"error": repo_result.get("error", "Failed to access repository")}
            
            repo_path = repo_result["path"]
            
            # Step 2: Detect ecosystem
            ecosystem = self._detect_ecosystem(repo_path)
            if not ecosystem:
                return {"error": f"Could not detect build system in {repo_path}"}
            
            # Step 3: Scan based on ecosystem
            if ecosystem == "maven":
                scan_result = self._scan_maven(repo_path, analyze_code=True)
            else:
                return {"error": f"{ecosystem.capitalize()} support coming soon!"}
            
            if "error" in scan_result:
                return scan_result
            
            # Step 4: Parse modules
            parsed_modules = []
            modules = scan_result.get("modules", [])
            
            for module in modules:
                module_path = module.get("path")
                if module_path and ecosystem == "maven":
                    parse_result = self._parse_maven_module(module_path)
                    if "error" not in parse_result:
                        parsed_modules.append(parse_result)
            
            if not parsed_modules:
                return {"error": "No modules could be parsed"}
            
            # Step 5: Build graph
            graph = self._build_graph(parsed_modules)
            
            # Update internal state
            self.graph = graph
            self.project_name = self._get_project_name(repo_path)
            
            # Update session state if available
            if self.session_state is not None:
                self.session_state.graph = graph
                self.session_state.project_name = self.project_name
                self.session_state.ecosystem = ecosystem
                self.session_state.repo_path = repo_path
                
                # Store code analysis
                if "code_analysis" in scan_result:
                    self.session_state.code_analysis = scan_result["code_analysis"]
                if "class_dependencies" in scan_result:
                    self.session_state.class_dependencies = scan_result["class_dependencies"]
            
            return {
                "success": True,
                "ecosystem": ecosystem,
                "project_name": self.project_name,
                "modules": len(parsed_modules),
                "nodes": len(graph.get("nodes", [])),
                "edges": len(graph.get("edges", []))
            }
            
        except Exception as e:
            return {"error": f"Scan failed: {str(e)}"}
    
    def update_graph(self, graph: Dict):
        """Update the dependency graph."""
        self.graph = graph
    
    def update_project_name(self, name: str):
        """Update the project name."""
        self.project_name = name
