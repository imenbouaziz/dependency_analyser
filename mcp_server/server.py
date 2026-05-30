
# mcp_server/server.py
import argparse
import sys
from fastmcp import FastMCP
from typing import Dict, List

from mcp_server.graph.graph_builder import build_graph
from mcp_server.graph.impact_analysis import impact_summary
from mcp_server.graph.sbom_generator import generate_minimal_sbom
from mcp_server.utils.filesystem import clone_or_use_local, detect_ecosystem, get_project_name
from mcp_server.scanners.maven_scanner import scan_maven_repo
from mcp_server.parsers.maven_parser import parse_maven_module

mcp = FastMCP("DependencyAnalyserServer")

# Keep a tiny in-memory graph state (MVP)
STATE = {"graph": None, "project_name": None, "repo_path": None}

@mcp.tool()
def build_dependency_graph(parsed_modules: List[Dict]) -> Dict:
    """
    Build an in-memory dependency graph from parsed Maven/Gradle modules.
    """
    g = build_graph(parsed_modules)
    STATE["graph"] = g
    return {"stats": g.get("stats", {}), "node_count": len(g["nodes"]), "edge_count": len(g["edges"])}

@mcp.tool()
def artifact_impact(artifact_coord: str) -> Dict:
    """
    Return which modules directly use the given artifact.
    """
    if not STATE["graph"]:
        return {"error": "Graph not built yet. Call build_dependency_graph first."}
    return impact_summary(STATE["graph"], artifact_coord)

@mcp.tool()
def export_sbom(project_name: str = "java-project") -> Dict:
    """
    Export a minimal CycloneDX-like SBOM (JSON).
    """
    if not STATE["graph"]:
        return {"error": "Graph not built yet. Call build_dependency_graph first."}
    # Use loaded project name if available
    proj_name = STATE.get("project_name") or project_name
    return generate_minimal_sbom(STATE["graph"], proj_name)


def auto_scan_and_build(repo_path_or_url: str) -> Dict:
    """
    Automatically scan a repository (local or GitHub) and build the dependency graph.
    
    Args:
        repo_path_or_url: Local filesystem path or Git repository URL
    
    Returns:
        Status dictionary with success/error information
    """
    print(f"[INFO] Processing repository: {repo_path_or_url}")
    
    # Step 1: Clone or use local path
    repo_result = clone_or_use_local(repo_path_or_url)
    if not repo_result["success"]:
        return {"error": repo_result.get("error", "Failed to access repository")}
    
    repo_path = repo_result["path"]
    is_temp = repo_result["is_temp"]
    
    print(f"[INFO] Repository path: {repo_path}")
    if is_temp:
        print("[INFO] (Cloned to temporary directory)")
    
    # Step 2: Detect ecosystem
    ecosystem = detect_ecosystem(repo_path)
    if not ecosystem:
        return {"error": f"Could not detect build system (Maven/Gradle/Node/Python) in {repo_path}"}
    
    print(f"[INFO] Detected ecosystem: {ecosystem}")
    
    # Step 3: Scan repository based on ecosystem
    if ecosystem == "maven":
        scan_result = scan_maven_repo(repo_path)
    elif ecosystem == "gradle":
        return {"error": "Gradle support not yet implemented"}
    elif ecosystem == "node":
        return {"error": "Node.js support not yet implemented"}
    elif ecosystem == "python":
        return {"error": "Python support not yet implemented"}
    else:
        return {"error": f"Unsupported ecosystem: {ecosystem}"}
    
    if "error" in scan_result:
        return scan_result
    
    print(f"[INFO] Scan complete: {scan_result.get('summary', '')}")
    
    # Step 4: Parse modules
    parsed_modules = []
    modules = scan_result.get("modules", [])
    
    for module in modules:
        module_path = module.get("path")
        if not module_path:
            continue
        
        print(f"[INFO] Parsing module: {module.get('name', 'unknown')}")
        
        if ecosystem == "maven":
            parse_result = parse_maven_module(module_path)
            if "error" not in parse_result:
                parsed_modules.append(parse_result)
            else:
                print(f"[WARN] Failed to parse {module_path}: {parse_result['error']}")
    
    if not parsed_modules:
        return {"error": "No modules could be parsed successfully"}
    
    print(f"[INFO] Successfully parsed {len(parsed_modules)} module(s)")
    
    # Step 5: Build dependency graph
    graph = build_graph(parsed_modules)
    STATE["graph"] = graph
    STATE["project_name"] = get_project_name(repo_path)
    STATE["repo_path"] = repo_path
    
    print(f"[SUCCESS] Dependency graph built successfully!")
    print(f"  - Nodes: {len(graph.get('nodes', []))}")
    print(f"  - Edges: {len(graph.get('edges', []))}")
    
    return {
        "success": True,
        "ecosystem": ecosystem,
        "project_name": STATE["project_name"],
        "modules_parsed": len(parsed_modules),
        "nodes": len(graph.get("nodes", [])),
        "edges": len(graph.get("edges", []))
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Dependency Analyzer MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a local repository
  python -m mcp_server.server --repo /path/to/local/repo
  
  # Analyze a GitHub repository
  python -m mcp_server.server --repo https://github.com/user/repo
  
  # Run MCP server without auto-scanning
  python -m mcp_server.server
        """
    )
    
    parser.add_argument(
        "--repo",
        type=str,
        help="Repository path (local directory) or URL (GitHub/Git) to analyze"
    )
    
    args = parser.parse_args()
    
    # Auto-scan if --repo is provided
    if args.repo:
        result = auto_scan_and_build(args.repo)
        if "error" in result:
            print(f"\n[ERROR] {result['error']}")
            sys.exit(1)
        print(f"\n[INFO] Repository loaded. Starting MCP server...\n")
    
    # Start MCP server
    mcp.run()
